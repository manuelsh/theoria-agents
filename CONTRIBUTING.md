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

| Resource                | Location                          | Usage                            |
| ----------------------- | --------------------------------- | -------------------------------- |
| Entry schema            | `schemas/entry.schema.json`       | Validate generated entries       |
| Assumptions schema      | `schemas/assumptions.schema.json` | Validate assumption format       |
| Global assumptions      | `globals/assumptions.json`        | Reference existing assumptions   |
| Contributing guidelines | `CONTRIBUTING.md`                 | Agent prompts for entry creation |

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

2. Configure required paths in `.env`:

   ```
   THEORIA_DATASET_PATH=/path/to/theoria-dataset
   THEORIA_OUTPUT_PATH=/path/to/output
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

## Test-Driven Development (TDD)

This project follows a strict TDD approach:

1. **Write tests first** - Before implementing any new agent or feature, write comprehensive unit tests
2. **Red-Green-Refactor** - Write failing tests, make them pass, then refactor
3. **Mock dependencies** - Use pytest fixtures with mocks for LLM clients, dataset loaders, and config

### Testing Strategy

- **Unit tests** - Test each agent in isolation with mocked dependencies
- **Mock patterns** - Consistent fixtures for `mock_config`, `mock_dataset_loader`, `mock_llm_client`
- **AsyncMock for async functions** - Always use `AsyncMock` for `complete_json` and `fetch_wikipedia`
- **Docker-based testing** - All tests run in Docker to ensure consistency

Example test structure:

```python
@pytest.fixture
def mock_llm_client():
    with patch("src.agents.base.LLMClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.complete_json = AsyncMock()
        mock_client.return_value = mock_instance
        yield mock_instance

@pytest.mark.asyncio
async def test_agent_run(agent_with_mocks):
    mock_llm_response = {"field": "value"}
    agent_with_mocks.llm_client.complete_json = AsyncMock(
        return_value=json.dumps(mock_llm_response)
    )
    result = await agent_with_mocks.run(...)
    assert isinstance(result, ExpectedOutputModel)
```

## Code Style

- Use type hints for all function signatures
- Follow existing patterns in the codebase
- Keep functions focused and single-purpose
- Each agent should have one clear responsibility (single-responsibility principle)

### Running Tests

Run tests using the Docker container:

```bash
# Build the Docker image
docker build -t theoria-agents-test .

# Run unit tests (default)
docker run --rm theoria-agents-test

# Run all tests including integration tests
docker run --rm \
  -v ~/.aws:/root/.aws:ro \
  -v ./.env:/app/.env:ro \
  -v /path/to/theoria-dataset:/theoria-dataset:ro \
  -e AWS_PROFILE=claude \
  theoria-agents-test pytest -v
```

## Debugging with Logs

The output management system captures all LLM interactions for debugging:

### Inspecting Agent Logs

Each pipeline run creates a timestamped folder in `$THEORIA_OUTPUT_PATH/logs/`:

```bash
# Find the most recent run
cd $THEORIA_OUTPUT_PATH/logs
ls -lt | head -5

# Inspect a specific agent's log
cat 2026-03-05_14-30-45_schrodinger_equation_a7b3c9d1/03_assumptions_dependencies.json
```

### Log Contents

Each agent log includes:
- **input**: Complete messages sent to LLM with all parameters
- **output**: Raw LLM response and parsed JSON
- **timing**: Start time, end time, duration in seconds
- **model**: Full model identifier (ARN or model ID)
- **status**: `success`, `error`, or `retry`
- **retries**: Retry attempts if LLM call failed initially

### Common Debugging Scenarios

**Agent produces unexpected output:**
1. Check the agent's log file to see exact LLM input/output
2. Verify the prompt being sent (in `input.messages`)
3. Check if parsing failed (compare `output.content` vs `output.parsed`)

**Pipeline fails mid-execution:**
1. Check `run_metadata.json` for error messages
2. Review the last completed agent's log
3. Look for status `"error"` in agent logs

**Entry validation fails:**
1. Check `08_reviewer.json` for issues found
2. Review `run_metadata.json` for validation errors
3. Compare generated entry against schema

### Assumptions Tracking

The `{entry_name}_assump.json` file tracks all assumptions:
- Which assumptions were selected
- Which agent used each assumption
- Statistics by agent
- Timestamps for traceability

This helps debug:
- Why certain assumptions were chosen
- Which agent is producing unnecessary assumptions
- Assumption selection patterns across runs

