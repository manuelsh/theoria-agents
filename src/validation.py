"""Schema-based validation using theoria-dataset's JSON schema.

This module validates entries against the canonical JSON schema from theoria-dataset,
following the Single Source of Truth principle.
"""

import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from jsonschema import Draft7Validator, ValidationError

from src.llm.config import get_dataset_path


class EntryValidator:
    """Validates entries against theoria-dataset's JSON schema."""

    def __init__(self, dataset_path: Path | None = None):
        """Initialize the validator.

        Args:
            dataset_path: Path to theoria-dataset. Uses THEORIA_DATASET_PATH if not provided.
        """
        self.dataset_path = dataset_path or get_dataset_path()
        self._schema: dict[str, Any] | None = None
        self._validator: Draft7Validator | None = None

    @property
    def schema(self) -> dict[str, Any]:
        """Load and cache the entry schema from theoria-dataset."""
        if self._schema is None:
            schema_path = self.dataset_path / "schemas" / "entry.schema.json"
            with open(schema_path) as f:
                self._schema = json.load(f)
        return self._schema

    @property
    def validator(self) -> Draft7Validator:
        """Get the JSON Schema validator."""
        if self._validator is None:
            self._validator = Draft7Validator(self.schema)
        return self._validator

    def validate(self, entry: dict[str, Any]) -> list[str]:
        """Validate an entry against the schema.

        Args:
            entry: Entry data as a dict.

        Returns:
            List of validation error messages. Empty list if valid.
        """
        errors = []
        for error in self.validator.iter_errors(entry):
            path = ".".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
            errors.append(f"{path}: {error.message}")
        return errors

    def is_valid(self, entry: dict[str, Any]) -> bool:
        """Check if an entry is valid.

        Args:
            entry: Entry data as a dict.

        Returns:
            True if valid, False otherwise.
        """
        return self.validator.is_valid(entry)

    def validate_or_raise(self, entry: dict[str, Any]) -> None:
        """Validate an entry, raising an exception if invalid.

        Args:
            entry: Entry data as a dict.

        Raises:
            ValidationError: If the entry is invalid.
        """
        errors = self.validate(entry)
        if errors:
            raise ValidationError(f"Entry validation failed:\n" + "\n".join(f"  - {e}" for e in errors))

    def run_dataset_validation(self, entry: dict[str, Any]) -> tuple[bool, str]:
        """Run theoria-dataset's validation scripts on an entry.

        Writes the entry to a temporary file in theoria-dataset/entries/,
        runs `make test-entry FILE=<entry_name>`, then cleans up.

        Args:
            entry: Entry data as a dict.

        Returns:
            Tuple of (success, output). Success is True if validation passes.
        """
        entry_id = entry.get("result_id", "temp_entry")
        entries_dir = self.dataset_path / "entries"
        temp_entry_path = entries_dir / f"{entry_id}.json"

        # Check if file already exists (don't overwrite)
        original_exists = temp_entry_path.exists()
        original_content = None
        if original_exists:
            with open(temp_entry_path) as f:
                original_content = f.read()

        try:
            # Write entry to file
            with open(temp_entry_path, "w") as f:
                json.dump(entry, f, indent=2)

            # Run make test-entry
            result = subprocess.run(
                ["make", "test-entry", f"FILE={entry_id}"],
                cwd=str(self.dataset_path),
                capture_output=True,
                text=True,
                timeout=120,
            )

            output = result.stdout + result.stderr
            success = result.returncode == 0

            return success, output

        except subprocess.TimeoutExpired:
            return False, "Validation timed out (120s limit)"
        except Exception as e:
            return False, f"Validation error: {str(e)}"
        finally:
            # Restore original file or clean up
            if original_exists and original_content is not None:
                with open(temp_entry_path, "w") as f:
                    f.write(original_content)
            elif not original_exists and temp_entry_path.exists():
                temp_entry_path.unlink()
