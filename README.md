# Theoria Agents

Multi-agent LLM system for generating high-quality theoretical physics dataset entries for [theoria-dataset](https://github.com/theoria-dataset).

## Overview

This project uses a pipeline of specialized LLM agents to generate rigorous physics derivations. The system follows a **single-responsibility principle** where each agent has one focused task:

### Phase 1: Research & Foundation (4 agents)
1. **InformationGatherer** - Searches Wikipedia, gathers context and historical information
2. **MetadataFiller** - Fills entry fields (ID, name, explanation, domain, theory status, etc.)
3. **AssumptionsDependencies** - Consults dataset to select assumptions and identify dependencies
4. **EquationsSymbols** - Defines result equations and symbols with correct AsciiMath notation

### Phase 2: Derivation & Verification (4 agents)
5. **Derivation** - Generates step-by-step mathematical derivations
6. **Verifier** - Creates and executes SymPy code to verify each step
7. **Assembler** - Combines all outputs into a valid dataset entry
8. **Reviewer** - Quality checks with 3-iteration self-correction loop

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

   # Path for pipeline output logs and generated entries (required)
   THEORIA_OUTPUT_PATH=/path/to/output

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

## Output Structure

All pipeline runs generate structured output in `THEORIA_OUTPUT_PATH`:

```
output/
├── logs/                                  # Detailed execution logs
│   └── 2026-03-05_14-30-45_schrodinger_equation_a7b3c9d1/
│       ├── run_metadata.json            # Pipeline configuration and timing
│       ├── 01_information_gatherer.json  # LLM inputs/outputs per agent
│       ├── 02_metadata_filler.json
│       ├── 03_assumptions_dependencies.json
│       ├── 04_equations_symbols.json
│       ├── 05_derivation.json
│       ├── 06_verifier.json
│       ├── 07_assembler.json
│       └── 08_reviewer.json
└── entries/                               # Generated entries and assumptions
    └── schrodinger_equation_time_dependent/
        ├── schrodinger_equation_time_dependent.json         # Final entry
        └── schrodinger_equation_time_dependent_assump.json  # Assumptions metadata
```

### Log Files

Each agent log contains:
- Complete LLM inputs (messages, parameters)
- Complete LLM outputs (raw and parsed)
- Execution timing and duration
- Model identifier used
- Status and any errors
- Retry attempts (if applicable)

### Run Metadata

`run_metadata.json` includes:
- Run ID and timestamps
- Topic and configuration
- All agents executed
- Final status and validation results
- Errors and issues found

This logging enables:
- **Debugging**: Inspect exact LLM calls when issues arise
- **Auditing**: Track what the pipeline did and why
- **Analysis**: Understand agent behavior and improve prompts
- **Reproducibility**: Full record of each generation

## Architecture

```
Phase 1: Research & Foundation
┌──────────────────────┐
│ InformationGatherer  │ ──> Searches Wikipedia, gathers context
└──────────────────────┘
           │
           v
┌──────────────────────┐
│   MetadataFiller     │ ──> Fills entry fields (ID, name, explanation, etc.)
└──────────────────────┘
           │
           v
┌──────────────────────┐
│ AssumptionsDeps      │ ──> Consults dataset for assumptions & dependencies
└──────────────────────┘
           │
           v
┌──────────────────────┐
│  EquationsSymbols    │ ──> Defines equations & symbols (AsciiMath)
└──────────────────────┘

Phase 2: Derivation & Verification
           │
           v
┌──────────────────────┐
│     Derivation       │ ──> Step-by-step mathematical derivation
└──────────────────────┘
           │
           v
┌──────────────────────┐
│      Verifier        │ ──> SymPy code generation & execution
└──────────────────────┘
           │
           v
┌──────────────────────┐
│      Assembler       │ ──> Combines all outputs into entry
└──────────────────────┘
           │
           v
┌──────────────────────┐
│      Reviewer        │ ──> Quality check with 3-iteration self-correction
└──────────────────────┘
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
  # Phase 1: Research & Foundation (4 agents)
  information_gatherer: "fast"
  metadata_filler: "fast"
  assumptions_dependencies: "best"
  equations_symbols: "best"
  # Phase 2: Derivation & Verification (4 agents)
  derivation: "best"
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
