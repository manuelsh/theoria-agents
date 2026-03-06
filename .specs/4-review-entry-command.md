# Review Entry Command Specification

**Status:** Draft
**Created:** 2026-03-06
**Purpose:** Add a CLI subcommand to review and improve existing dataset entries using only the reviewer agent

## Overview

This specification defines a `review` subcommand for the unified `theoria-agent` CLI that allows users to run the reviewer agent on an existing entry file to check quality and apply corrections, without going through the full generation pipeline.

This also renames the existing `theoria-generate` command to `theoria-agent generate`.

## Motivation

Currently, the only way to use the reviewer agent is through the full `theoria-generate` pipeline. However, there are scenarios where users need to:

1. Review manually created entries before submission
2. Re-review entries after manual edits
3. Improve entries that were generated previously but may have issues
4. Batch-review multiple entries without regenerating them

## Goals

1. **Unified CLI**: Single `theoria-agent` command with subcommands
2. **Standalone Review**: Run the reviewer agent independently of the full pipeline
3. **Flexible Input**: Accept entry path or entry ID (resolved from dataset)
4. **Configurable Output**: Save to custom path or overwrite original
5. **Dry Run Support**: Preview changes without modifying files
6. **Consistent Behavior**: Use same reviewer logic and configuration as the pipeline

## Requirements

### 1. CLI Structure

**Command Name**: `theoria-agent`

**Subcommands**:
- `generate` - Generate a new entry (existing functionality)
- `review` - Review and improve an existing entry (new)

**Usage**:
```bash
# Generate (existing functionality, new syntax)
theoria-agent generate "Schrödinger equation"
theoria-agent generate "Klein-Gordon equation" --domain quant-ph

# Review entry from explicit file path
theoria-agent review path/to/entry.json

# Review entry by ID (resolves from THEORIA_DATASET_PATH/entries/)
theoria-agent review schrodinger_equation

# Save to different location
theoria-agent review entry.json --output improved_entry.json

# Preview without saving
theoria-agent review entry.json --dry-run

# Custom correction loops
theoria-agent review entry.json --max-loops 5
```

### 2. Review Subcommand

**Arguments**:

| Argument | Type | Required | Description |
|----------|------|----------|-------------|
| `entry` | positional | Yes | Entry file path OR entry ID |

**Options**:

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--output` | `-o` | string | None | Output file path (overwrites input if not specified) |
| `--max-loops` | | int | None | Max correction iterations (uses config default if not specified) |

### 3. Generate Subcommand (Existing)

The existing `theoria-generate` functionality moves under `theoria-agent generate` with the same options:

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `topic` | | positional | Required | Physics topic to generate |
| `--domain` | | string | None | Suggested arXiv category |
| `--depends-on` | | string[] | None | Suggested dependency entry IDs |
| `--output` | `-o` | string | None | Custom output directory |
| `--contributor-name` | | string | "Theoria Agents" | Contributor name |
| `--contributor-id` | | string | "https://github.com/theoria-agents" | Contributor identifier |
| `--validate` | | flag | False | Run validation after generation |
| `--dry-run` | | flag | False | Print entry without saving |

### 4. Entry Path Resolution

The `entry` argument should be resolved as follows:

```
Is entry argument a file path? (contains / or \ or ends with .json)
├── Yes → Use path directly
│   └── File exists?
│       ├── Yes → Load entry
│       └── No → Raise FileNotFoundError
└── No → Treat as entry ID
    └── THEORIA_DATASET_PATH set?
        ├── Yes → Look for {THEORIA_DATASET_PATH}/entries/{entry_id}.json
        │   └── File exists?
        │       ├── Yes → Load entry
        │       └── No → Raise FileNotFoundError
        └── No → Raise ValueError("THEORIA_DATASET_PATH not set")
```

### 5. Review Flow

```
1. Load entry from resolved path
2. Validate entry against TheoriaEntry model
3. Initialize ReviewerAgent with config
4. Run reviewer.run(entry)
5. Report results:
   - Pass/fail status
   - Issues found
   - Whether corrections were made
6. Handle output:
   - If --dry-run: Print corrected entry JSON to stdout
   - If corrections made:
     - Save corrected entry to output path (or input path)
   - If no corrections:
     - Keep original file unchanged
```

### 6. Output Behavior

| Scenario | `--output` | `--dry-run` | Behavior |
|----------|------------|-------------|----------|
| Pass, no corrections | Not set | False | No file changes |
| Pass, with corrections | Not set | False | Overwrite input file |
| Pass, with corrections | Set | False | Write to output path |
| Fail, partial corrections | Not set | False | Overwrite input file |
| Any | Any | True | Print to stdout only |

### 7. Console Output

```
============================================================
Theoria Review - Reviewing: path/to/entry.json
============================================================

Loading entry: schrodinger_equation
Entry ID: schrodinger_equation
Entry Name: Schrödinger Equation

[1/3] Reviewing entry...
[2/3] Found 2 issues:
      - Explanation exceeds 800 characters
      - Missing definition for symbol 'psi'
[3/3] Applying corrections...

============================================================
Review Complete!
============================================================
Status: PASSED (after corrections)
Issues Found: 2
Corrections Applied: Yes
Output: path/to/entry.json

--- Corrected Entry (dry run) ---
{
  "result_id": "schrodinger_equation",
  ...
}
```

## Implementation Plan

### Phase 1: Core Module

1. **New Module** (`src/review_entry.py`)

   Functions:
   - `resolve_entry_path(entry_or_path: str) -> Path`
   - `load_entry_for_review(path: str | Path) -> TheoriaEntry`
   - `review_entry(path: str, max_correction_loops: int | None = None) -> ReviewResult`
   - `review_and_save(path: str, output_path: str | None = None, dry_run: bool = False) -> Path`

### Phase 2: CLI Refactoring

2. **CLI Restructure** (`src/cli.py`)

   - Rename to unified `theoria-agent` command with subcommands
   - Add `generate` subcommand (move existing functionality)
   - Add `review` subcommand (new functionality)
   - Update entry point in `pyproject.toml`

### Phase 3: Testing

3. **Unit Tests** (`tests/unit/test_review_entry.py`)

   Test classes:
   - `TestReviewEntryLoading` - Entry loading from various sources
   - `TestReviewEntryRunner` - Reviewer execution
   - `TestReviewEntrySaving` - Output file handling
   - `TestReviewEntryDefaultPath` - Path resolution logic
   - `TestCLIIntegration` - Argument parsing

4. **Integration Tests** (`tests/integration/test_review_entry.py`)

   Test classes:
   - `TestReviewEntryEndToEnd` - Full flow with mocked LLM
   - `TestReviewEntryIntegrationWithRealLLM` - Real LLM calls (marked `@pytest.mark.integration`)

### Phase 4: Documentation

5. **README Updates**
   - Rename `theoria-generate` to `theoria-agent generate` throughout
   - Add `theoria-agent review` command documentation
   - Add usage examples for both subcommands
   - Update command-line options tables

## Technical Details

### Module: `src/review_entry.py`

```python
"""Review and improve existing dataset entries."""

import json
from pathlib import Path
from typing import Any

from src.agents.reviewer import ReviewerAgent
from src.dataset import DatasetLoader
from src.llm.config import load_config, get_dataset_path
from src.models import TheoriaEntry, ReviewResult


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
    ...


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
    ...


async def review_entry(
    path: str | Path,
    max_correction_loops: int | None = None,
) -> ReviewResult:
    """Review an entry and return the result.

    Args:
        path: Path to entry file or entry ID.
        max_correction_loops: Override config max loops (optional).

    Returns:
        ReviewResult with pass/fail status and corrections.
    """
    ...


async def review_and_save(
    path: str | Path,
    output_path: str | Path | None = None,
    dry_run: bool = False,
    max_correction_loops: int | None = None,
) -> Path:
    """Review an entry and save the result.

    Args:
        path: Path to entry file or entry ID.
        output_path: Where to save result (overwrites input if None).
        dry_run: If True, print result without saving.
        max_correction_loops: Override config max loops (optional).

    Returns:
        Path where result was saved (or would be saved in dry-run).
    """
    ...
```

### CLI Structure

```python
def main() -> int:
    """Main entry point for theoria-agent CLI."""
    parser = argparse.ArgumentParser(
        prog="theoria-agent",
        description="Multi-agent LLM system for theoria-dataset.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Generate subcommand
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate a new dataset entry",
    )
    _add_generate_arguments(generate_parser)

    # Review subcommand
    review_parser = subparsers.add_parser(
        "review",
        help="Review and improve an existing entry",
    )
    _add_review_arguments(review_parser)

    args = parser.parse_args()

    if args.command == "generate":
        return asyncio.run(run_generate(args))
    elif args.command == "review":
        return asyncio.run(run_review(args))


def _add_review_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the review subcommand."""
    parser.add_argument(
        "entry",
        type=str,
        help="Entry file path or entry ID (resolved from THEORIA_DATASET_PATH)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        help="Output file path (overwrites input if not specified)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print result without saving",
    )
    parser.add_argument(
        "--max-loops",
        type=int,
        help="Maximum correction iterations",
    )
```

### Entry Point Configuration

Update `pyproject.toml`:

```toml
[project.scripts]
theoria-agent = "src.cli:main"

# Keep legacy alias for backward compatibility (optional)
theoria-generate = "src.cli:generate_main"
```

## Error Handling

| Error | Message | Exit Code |
|-------|---------|-----------|
| File not found | `Error: Entry file not found: {path}` | 1 |
| Invalid JSON | `Error: Invalid JSON in entry file: {details}` | 1 |
| Invalid schema | `Error: Entry does not match schema: {details}` | 1 |
| No dataset path | `Error: THEORIA_DATASET_PATH not set. Provide full file path.` | 1 |
| LLM error | `Error: Review failed: {details}` | 1 |
| Write error | `Error: Cannot write to output path: {path}` | 1 |

## Success Criteria

1. `theoria-agent review entry.json` reviews and saves corrections in place
2. `theoria-agent review entry_id` resolves from dataset and reviews
3. `theoria-agent review entry.json --output new.json` saves to new location
4. `theoria-agent review entry.json --dry-run` shows result without saving
5. `theoria-agent review entry.json --max-loops 5` uses custom loop count
6. `theoria-agent generate "topic"` works (existing functionality preserved)
7. All error cases produce clear messages
8. Unit tests achieve 100% coverage of new code
9. Integration tests pass with real LLM

## Dependencies

- No new external dependencies required
- Uses existing: `ReviewerAgent`, `TheoriaEntry`, `load_config`

## Breaking Changes

1. **CLI Renamed**: `theoria-generate` becomes `theoria-agent generate`
   - Migration: Update scripts to use `theoria-agent generate` instead of `theoria-generate`
   - Optional: Keep `theoria-generate` as a legacy alias pointing to `generate_main()`

## Future Enhancements (Out of Scope)

- Batch review of multiple entries
- Review with custom prompts/guidelines
- Diff output showing changes made
- Integration with git for automatic commits
- Review history tracking
