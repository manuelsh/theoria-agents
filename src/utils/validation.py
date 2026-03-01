"""Validation utilities using theoria-dataset's existing test infrastructure."""

import subprocess
from pathlib import Path

from src.llm.config import get_dataset_path


def run_dataset_validation(entry_id: str, dataset_path: Path | None = None) -> tuple[bool, str]:
    """Run theoria-dataset's validation on an entry.

    This calls `make validate FILE=<entry_id>` in the dataset directory,
    which runs schema validation via ajv-cli.

    Args:
        entry_id: The entry's result_id (without .json extension).
        dataset_path: Path to theoria-dataset. Uses THEORIA_DATASET_PATH if not provided.

    Returns:
        Tuple of (success, output_message).
    """
    dataset_path = dataset_path or get_dataset_path()

    try:
        result = subprocess.run(
            ["make", "validate", f"FILE={entry_id}"],
            cwd=dataset_path,
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return True, result.stdout or "Validation passed"
        else:
            return False, result.stderr or result.stdout or "Validation failed"

    except subprocess.TimeoutExpired:
        return False, "Validation timed out"
    except FileNotFoundError:
        return False, "Make command not found. Ensure make is installed."
    except Exception as e:
        return False, f"Validation error: {e}"


def run_full_test(entry_id: str, dataset_path: Path | None = None) -> tuple[bool, str]:
    """Run full test suite on an entry (schema + SymPy verification).

    This calls `make test-entry FILE=<entry_id>` in the dataset directory.
    Requires Docker to be running.

    Args:
        entry_id: The entry's result_id (without .json extension).
        dataset_path: Path to theoria-dataset. Uses THEORIA_DATASET_PATH if not provided.

    Returns:
        Tuple of (success, output_message).
    """
    dataset_path = dataset_path or get_dataset_path()

    try:
        result = subprocess.run(
            ["make", "test-entry", f"FILE={entry_id}"],
            cwd=dataset_path,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minutes for Docker-based tests
        )

        if result.returncode == 0:
            return True, result.stdout or "All tests passed"
        else:
            return False, result.stderr or result.stdout or "Tests failed"

    except subprocess.TimeoutExpired:
        return False, "Test timed out (5 minute limit)"
    except FileNotFoundError:
        return False, "Make command not found. Ensure make is installed."
    except Exception as e:
        return False, f"Test error: {e}"


def check_docker_running() -> bool:
    """Check if Docker daemon is running.

    Returns:
        True if Docker is available, False otherwise.
    """
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=10,
        )
        return result.returncode == 0
    except Exception:
        return False
