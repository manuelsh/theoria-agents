"""Schema-based validation using theoria-dataset's JSON schema.

This module validates entries against the canonical JSON schema from theoria-dataset,
following the Single Source of Truth principle.
"""

import json
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
