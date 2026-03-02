# Contributing to theoria-agents

## Single Source of Truth Principle

**theoria-dataset is the canonical source for all schemas and definitions.**

This is a fundamental design principle for theoria-agents:

1. **Never duplicate** - Do not recreate data structures, schemas, or definitions that already exist in theoria-dataset
2. **Load dynamically** - Always load schemas, guidelines, and configurations from theoria-dataset at runtime
3. **Validate against source** - Use theoria-dataset's validation infrastructure, not local reimplementations

### Why This Matters

- Prevents drift between the agent's understanding and the actual schema
- Ensures updates to theoria-dataset are automatically reflected
- Reduces maintenance burden and potential for bugs
- Keeps the codebase DRY (Don't Repeat Yourself)

### What to Reference from theoria-dataset

| Resource | Location | Usage |
|----------|----------|-------|
| Entry schema | `schemas/entry.schema.json` | Validate generated entries |
| Assumptions schema | `schemas/assumptions.schema.json` | Validate assumption format |
| Global assumptions | `globals/assumptions.json` | Reference existing assumptions |
| Contributing guidelines | `CONTRIBUTING.md` | Agent prompts for entry creation |

### How Validation Works

- `src/models.py` contains minimal Pydantic models for agent I/O and internal data flow
- `src/validation.py` provides `EntryValidator` which validates entries against `entry.schema.json`
- The orchestrator validates entries against the JSON schema before saving

## Development Setup

**All development happens inside Docker containers** - no need to install dependencies locally.

1. Clone both repositories into a shared parent directory:
   ```
   theoria-project/
   ├── theoria-agents/
   └── theoria-dataset/
   ```

2. Configure the dataset path in `.env`:
   ```
   THEORIA_DATASET_PATH=/path/to/theoria-dataset
   ```

3. Run tests via Docker:
   ```bash
   docker build -t theoria-agents .
   docker run --rm \
     -v ~/.aws:/root/.aws:ro \
     -v $(pwd)/.env:/app/.env:ro \
     -v /path/to/theoria-dataset:/theoria-dataset:ro \
     -e THEORIA_DATASET_PATH=/theoria-dataset \
     theoria-agents pytest -v
   ```

## Code Style

- Use type hints for all function signatures
- Follow existing patterns in the codebase
- Keep functions focused and single-purpose
