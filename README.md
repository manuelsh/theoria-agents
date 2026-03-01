# Theoria Agents

Multi-agent LLM system for generating high-quality theoretical physics dataset entries for [theoria-dataset](https://github.com/theoria-dataset).

## Overview

This project uses a pipeline of specialized LLM agents to generate rigorous physics derivations:

1. **Researcher** - Searches Wikipedia, identifies dependencies, selects/proposes assumptions
2. **Derivation** - Generates step-by-step mathematical derivations
3. **Verifier** - Creates SymPy code to verify each derivation step
4. **Assembler** - Combines outputs into a valid dataset entry
5. **Reviewer** - Quality checks and auto-corrects issues

All agents dynamically load guidelines from theoria-dataset's `CONTRIBUTING.md` and `AI_guidance.md` files - no hardcoded prompts. This ensures agents always follow the latest requirements.

## Prerequisites

- **Python 3.11+**
- **Docker** (for running theoria-dataset validation tests)
- **AWS credentials** configured for Bedrock access
- **theoria-dataset** cloned locally

## Installation

```bash
# Clone this repository
git clone https://github.com/your-org/theoria-agents.git
cd theoria-agents

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

## Configuration

1. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` with your values:
   ```bash
   # Path to your local theoria-dataset clone (required)
   THEORIA_DATASET_PATH=/path/to/theoria-dataset

   # AWS Bedrock Configuration
   AWS_REGION=us-east-1

   # Model ARNs from AWS Bedrock console
   BEDROCK_MODEL_FAST=arn:aws:bedrock:...
   BEDROCK_MODEL_BEST=arn:aws:bedrock:...
   ```

3. Ensure AWS credentials are configured:
   ```bash
   aws configure
   # Or set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY environment variables
   ```

## Usage

### Generate an Entry

```bash
# Basic usage - just provide a topic
theoria-generate "Schrödinger equation"

# With hints
theoria-generate "Klein-Gordon equation" --domain quant-ph --depends-on special_relativity

# Dry run (print to stdout without saving)
theoria-generate "Heisenberg uncertainty principle" --dry-run

# With validation (requires Docker)
theoria-generate "Dirac equation" --validate
```

### Command-Line Options

| Option | Description |
|--------|-------------|
| `topic` | Physics topic to generate (required) |
| `--domain` | Suggested arXiv category (e.g., `quant-ph`) |
| `--depends-on` | Suggested dependency entry IDs |
| `--output`, `-o` | Custom output directory |
| `--contributor-name` | Name for contributor field |
| `--contributor-id` | ORCID or website for contributor |
| `--validate` | Run validation after generation |
| `--dry-run` | Print entry without saving |

### Programmatic Usage

```python
import asyncio
from src.orchestrator import PipelineOrchestrator

async def main():
    orchestrator = PipelineOrchestrator()

    entry, metadata = await orchestrator.generate_entry(
        topic="Schrödinger equation",
        hints={"domain": "quant-ph"},
    )

    # Save to dataset
    output_path = orchestrator.save_entry(entry)
    print(f"Saved to: {output_path}")

asyncio.run(main())
```

## Architecture

```
┌─────────────┐     ┌─────────────┐     ┌──────────┐     ┌───────────┐     ┌──────────┐
│  Researcher │ ──> │  Derivation │ ──> │ Verifier │ ──> │ Assembler │ ──> │ Reviewer │
└─────────────┘     └─────────────┘     └──────────┘     └───────────┘     └──────────┘
      │                   │                  │                                   │
      │                   │                  │                                   │
      v                   v                  v                                   v
  Web search        Guidelines from      SymPy code          JSON entry      Self-correct
  Wikipedia        CONTRIBUTING.md        execution           assembly         loop (3x)
```

### Quality Assurance

- Guidelines loaded dynamically from theoria-dataset
- SymPy verification code is executed to check correctness
- Reviewer agent performs up to 3 self-correction iterations
- Final validation uses theoria-dataset's own test infrastructure

## Configuration Files

### `config/settings.yaml`

Non-secret settings for agent behavior:

```yaml
agent_models:
  researcher: "fast"    # Uses BEDROCK_MODEL_FAST
  derivation: "best"    # Uses BEDROCK_MODEL_BEST
  verifier: "best"
  assembler: "fast"
  reviewer: "best"

web_search:
  enabled: true
  sources:
    - wikipedia

reviewer:
  max_correction_loops: 3
```

### `.env`

Secret configuration (gitignored):

```bash
THEORIA_DATASET_PATH=/path/to/theoria-dataset
AWS_REGION=us-east-1
BEDROCK_MODEL_FAST=arn:aws:bedrock:...
BEDROCK_MODEL_BEST=arn:aws:bedrock:...
```

## Validation

After generating an entry, validate it using theoria-dataset's tests:

```bash
# From theoria-dataset directory
make test-entry FILE=new_entry_name    # Full validation
make validate FILE=new_entry_name      # Schema only
```

Or use the `--validate` flag when generating.

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Type checking (if using mypy)
mypy src/
```

## License

MIT
