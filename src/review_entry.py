"""Review and improve existing dataset entries."""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.models import ReviewResult, TheoriaEntry


def _is_file_path(entry_or_path: str) -> bool:
    """Check if the argument looks like a file path vs an entry ID.

    Args:
        entry_or_path: The input string to check.

    Returns:
        True if it looks like a file path, False if it looks like an entry ID.
    """
    return (
        "/" in entry_or_path
        or "\\" in entry_or_path
        or entry_or_path.endswith(".json")
    )


def resolve_entry_path(entry_or_path: str) -> Path:
    """Resolve entry argument to a file path.

    Args:
        entry_or_path: Either a file path or an entry ID.

    Returns:
        Path to the entry file.

    Raises:
        FileNotFoundError: If the entry file doesn't exist.
        ValueError: If entry ID given but THEORIA_DATASET_PATH not set.
    """
    if _is_file_path(entry_or_path):
        path = Path(entry_or_path)
        if not path.exists():
            raise FileNotFoundError(f"Entry file not found: {path}")
        return path

    # Treat as entry ID - resolve from dataset path
    # Import here to avoid litellm import chain at module load
    from src.llm.config import load_config

    config = load_config()
    dataset_path = config.get("theoria_dataset_path")

    if not dataset_path:
        raise ValueError(
            "THEORIA_DATASET_PATH not set. Provide full file path or set the environment variable."
        )

    entry_path = Path(dataset_path) / "entries" / f"{entry_or_path}.json"
    if not entry_path.exists():
        raise FileNotFoundError(f"Entry not found in dataset: {entry_or_path}")

    return entry_path


def load_entry_for_review(path: str | Path) -> TheoriaEntry:
    """Load an entry file and validate it.

    Args:
        path: Path to the entry JSON file.

    Returns:
        Validated TheoriaEntry instance.

    Raises:
        FileNotFoundError: If file doesn't exist.
        json.JSONDecodeError: If file is not valid JSON.
        pydantic.ValidationError: If entry doesn't match schema.
    """
    from src.models import TheoriaEntry

    path = Path(path)

    if not path.exists():
        raise FileNotFoundError(f"Entry file not found: {path}")

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    return TheoriaEntry.model_validate(data)


async def review_entry(
    path: str | Path,
    max_correction_loops: int | None = None,
) -> ReviewResult:
    """Review an entry and return the result.

    Args:
        path: Path to entry file.
        max_correction_loops: Override config max loops (optional).

    Returns:
        ReviewResult with pass/fail status and corrections.
    """
    from src.agents.reviewer import ReviewerAgent
    from src.llm.config import load_config

    config = load_config()

    # Determine max loops
    if max_correction_loops is None:
        reviewer_config = config.get("reviewer", {})
        max_correction_loops = reviewer_config.get("max_correction_loops", 3)

    # Load the entry
    entry = load_entry_for_review(path)

    # Run the reviewer
    reviewer = ReviewerAgent(max_correction_loops=max_correction_loops)
    result = await reviewer.run(entry)

    return result


async def review_and_save(
    path: str | Path,
    output_path: str | Path | None = None,
    max_correction_loops: int | None = None,
) -> Path:
    """Review an entry and save the result.

    Args:
        path: Path to entry file.
        output_path: Where to save result (overwrites input if None).
        max_correction_loops: Override config max loops (optional).

    Returns:
        Path where result was saved.
    """
    input_path = Path(path)

    # Review the entry
    result = await review_entry(input_path, max_correction_loops=max_correction_loops)

    # Determine output path
    if output_path is not None:
        save_path = Path(output_path)
    else:
        save_path = input_path

    # Save if there are corrections
    if result.corrected_entry is not None:
        # Create parent directory if needed
        save_path.parent.mkdir(parents=True, exist_ok=True)

        with open(save_path, "w", encoding="utf-8") as f:
            f.write(result.corrected_entry.model_dump_json(indent=2, exclude_none=True))

    return save_path
