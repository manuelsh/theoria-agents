# Output Management System Specification

**Status:** Completed
**Created:** 2026-03-05
**Completed:** 2026-03-05
**Purpose:** Define structured logging and artifact storage for all agent runs with LLM traceability

## Overview

This specification defines an output management system for `theoria-agents` that provides structured logging and artifact storage for all agent runs. The system will capture LLM interactions and store generated entries with their assumptions in an organized folder structure.

## Goals

1. **Traceability**: Capture all LLM inputs and outputs for debugging and auditing
2. **Organization**: Store output artifacts in a logical, time-based folder structure
3. **Transparency**: Make assumptions explicit and easily accessible
4. **Configurability**: Allow users to specify custom output locations via environment variables

## Requirements

### 1. Environment Configuration

**Environment Variable**: `THEORIA_OUTPUT_PATH`

- **Type**: Absolute path to output directory
- **Required**: Yes (validation should fail if not set)
- **Example**: `/Users/manuel.sanchez.herna/code/theoria-project/output`
- **Validation**:
  - Must be an absolute path
  - Directory must be writable
  - Will be created if it doesn't exist

**Configuration Location**: `.env` file in repository root

```bash
# .env
THEORIA_DATASET_PATH=/path/to/theoria-dataset
THEORIA_OUTPUT_PATH=/Users/manuel.sanchez.herna/code/theoria-project/output
```

### 2. Directory Structure

```
{THEORIA_OUTPUT_PATH}/
├── logs/
│   └── {YYYY-MM-DD_HH-MM-SS}_{topic_slug}_{run_id}/
│       ├── run_metadata.json
│       ├── 01_information_gatherer.json
│       ├── 02_metadata_filler.json
│       ├── 03_assumptions_dependencies.json
│       ├── 04_equations_symbols.json
│       ├── 05_derivation.json
│       ├── 06_verifier.json
│       ├── 07_assembler.json
│       └── 08_reviewer.json
└── entries/
    └── {entry_name}/
        ├── {entry_name}.json
        └── {entry_name}_assump.json
```

#### Directory Descriptions

##### `logs/` Directory

- **Purpose**: Store detailed logs of each pipeline run
- **Folder Naming**: `{YYYY-MM-DD_HH-MM-SS}_{topic_slug}_{run_id}`
  - `YYYY-MM-DD_HH-MM-SS`: ISO 8601 timestamp (local time)
  - `topic_slug`: URL-safe version of topic (e.g., `schrodinger_equation`)
  - `run_id`: Short unique identifier (first 8 chars of UUID4)
  - Example: `2026-03-05_14-30-45_schrodinger_equation_a7b3c9d1`

##### `entries/` Directory

- **Purpose**: Store final generated entries and their assumptions
- **Folder Naming**: `{entry_name}` - the `name` field from the generated entry
  - Example: `schrodinger_equation_time_dependent`

### 3. Log File Format

Each agent's log file should contain:

```json
{
  "agent_name": "information_gatherer",
  "timestamp_start": "2026-03-05T14:30:45.123Z",
  "timestamp_end": "2026-03-05T14:30:52.456Z",
  "duration_seconds": 7.333,
  "model": "bedrock/arn:aws:bedrock:us-east-1:...:inference-profile/us.anthropic.claude-sonnet-4-20250514-v1:0",
  "input": {
    "messages": [
      {
        "role": "system",
        "content": "You are an expert physics research assistant..."
      },
      {
        "role": "user",
        "content": "Gather information about: Schrödinger equation"
      }
    ],
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "output": {
    "content": "{\"topic_understanding\": \"...\", ...}",
    "parsed": {
      "topic_understanding": "The Schrödinger equation is...",
      "domain": "quantum_mechanics"
    }
  },
  "status": "success",
  "error": null
}
```

#### Log File Fields

- **agent_name**: Name of the agent (matches `BaseAgent.agent_name`)
- **timestamp_start**: ISO 8601 timestamp when agent started
- **timestamp_end**: ISO 8601 timestamp when agent completed
- **duration_seconds**: Time taken for agent execution
- **model**: Full model identifier used for this agent
- **input**: Complete input sent to LLM
  - `messages`: Array of message objects (system, user, assistant)
  - `temperature`: Temperature parameter
  - `max_tokens`: Max tokens parameter
  - Additional LLM parameters as needed
- **output**: LLM response
  - `content`: Raw string response from LLM
  - `parsed`: Parsed JSON object (if applicable)
- **status**: `"success"` | `"error"` | `"retry"`
- **error**: Error message if status is "error", otherwise null
- **retries**: (Optional) Number of retries attempted
- **retry_details**: (Optional) Array of retry attempts with timestamps

### 4. Run Metadata File

`run_metadata.json` in each log folder:

```json
{
  "run_id": "a7b3c9d1",
  "timestamp_start": "2026-03-05T14:30:45.123Z",
  "timestamp_end": "2026-03-05T14:32:15.789Z",
  "duration_seconds": 90.666,
  "topic": "Schrödinger equation",
  "topic_slug": "schrodinger_equation",
  "hints": {
    "domain": "quantum_mechanics"
  },
  "contributor_name": "Theoria Agents",
  "contributor_id": "https://github.com/theoria-agents",
  "pipeline_version": "1.0.0",
  "config": {
    "dataset_path": "/path/to/theoria-dataset",
    "output_path": "/path/to/output",
    "models": {
      "information_gatherer": "sonnet-4",
      "metadata_filler": "sonnet-4"
    }
  },
  "agents_executed": [
    "information_gatherer",
    "metadata_filler",
    "assumptions_dependencies",
    "equations_symbols",
    "derivation",
    "verifier",
    "assembler",
    "reviewer"
  ],
  "final_status": "success",
  "entry_name": "schrodinger_equation_time_dependent",
  "validation_passed": true,
  "errors": []
}
```

### 5. Entry Files Format

#### Entry File: `{entry_name}.json`

- **Content**: Complete validated entry matching `entry.schema.json`
- **Format**: Pretty-printed JSON with 2-space indentation
- **Source**: Output from `AssemblerAgent` after validation

#### Assumptions File: `{entry_name}_assump.json`

Contains all assumptions collected during the pipeline:

```json
{
  "entry_name": "schrodinger_equation_time_dependent",
  "timestamp": "2026-03-05T14:32:15.789Z",
  "run_id": "a7b3c9d1",
  "assumptions": [
    {
      "id": "A001",
      "assumption": "Non-relativistic regime (v << c)",
      "justification": "Required for the standard time-dependent Schrödinger equation",
      "source": "assumptions_dependencies",
      "timestamp": "2026-03-05T14:31:02.123Z"
    },
    {
      "id": "A002",
      "assumption": "Single particle system",
      "justification": "Multi-particle extension requires different formulation",
      "source": "derivation",
      "timestamp": "2026-03-05T14:31:45.456Z"
    }
  ],
  "statistics": {
    "total_assumptions": 2,
    "by_agent": {
      "assumptions_dependencies": 1,
      "derivation": 1
    }
  }
}
```

**Special Case - No Assumptions**:

```json
{
  "entry_name": "simple_example",
  "timestamp": "2026-03-05T14:32:15.789Z",
  "run_id": "a7b3c9d1",
  "assumptions": [],
  "statistics": {
    "total_assumptions": 0,
    "by_agent": {}
  },
  "note": "No assumptions were required for this entry."
}
```

## Implementation Plan

### Phase 1: Core Infrastructure

1. **Config Module Updates** (`src/llm/config.py`)
   - Add `THEORIA_OUTPUT_PATH` to environment variable loading
   - Add validation for output path
   - Create output directories if they don't exist

2. **Output Manager Module** (`src/utils/output_manager.py`)
   - `OutputManager` class to handle all output operations
   - Methods:
     - `create_run_folder()`: Create timestamped run folder
     - `log_agent_execution()`: Write agent log file
     - `save_run_metadata()`: Write run metadata
     - `save_entry()`: Save final entry JSON
     - `save_assumptions()`: Save assumptions JSON
     - Helper methods for path generation and topic slugification

3. **Logger Wrapper** (`src/utils/agent_logger.py`)
   - `AgentLogger` class to capture LLM inputs/outputs
   - Context manager for timing agent execution
   - Integration with `LLMClient` for automatic logging

### Phase 2: Agent Integration

4. **BaseAgent Updates** (`src/agents/base.py`)
   - Add `AgentLogger` instance to base class
   - Wrap `run()` method with logging context
   - Capture all LLM calls automatically

5. **LLMClient Updates** (`src/llm/client.py`)
   - Add optional callback for logging
   - Pass input/output to logger if callback provided
   - Maintain backward compatibility

### Phase 3: Orchestrator Integration

6. **PipelineOrchestrator Updates** (`src/orchestrator.py`)
   - Initialize `OutputManager` in constructor
   - Create run folder at pipeline start
   - Pass logger to each agent
   - Collect assumptions from all agents
   - Save all outputs at pipeline completion

7. **CLI Updates** (`src/cli.py`)
   - Validate output path on startup
   - Display output location to user
   - Add `--output-path` optional override flag

### Phase 4: Testing

8. **Unit Tests**
   - Test `OutputManager` methods
   - Test path generation and slugification
   - Test JSON serialization
   - Mock file system operations

9. **Integration Tests**
   - End-to-end pipeline test with output validation
   - Verify all files are created correctly
   - Verify JSON formats match specifications

### Phase 5: Documentation

10. **README Updates**
    - Document `THEORIA_OUTPUT_PATH` variable
    - Explain output structure
    - Provide examples

11. **CONTRIBUTING.md Updates**
    - Add output management to development workflow
    - Explain how to inspect logs for debugging

## Technical Considerations

### Path Handling

- Use `pathlib.Path` for all path operations
- Normalize paths to absolute
- Handle symlinks appropriately
- Validate write permissions before execution

### Topic Slugification

```python
def slugify_topic(topic: str) -> str:
    """Convert topic to URL-safe slug.

    Examples:
        "Schrödinger equation" -> "schrodinger_equation"
        "Newton's 2nd Law" -> "newtons_2nd_law"
        "E=mc²" -> "e_mc2"
    """
    # Remove/replace special characters
    # Convert to lowercase
    # Replace spaces with underscores
    # Remove consecutive underscores
    # Strip leading/trailing underscores
```

### Timestamp Format

- Use UTC for all timestamps
- Format: ISO 8601 (`YYYY-MM-DDTHH:MM:SS.sssZ`)
- Use `datetime.utcnow().isoformat() + 'Z'`
- For folder names: `datetime.now().strftime('%Y-%m-%d_%H-%M-%S')`

### Error Handling

- Graceful degradation: if logging fails, pipeline should continue and an output should be given that logs are not being stored
- Log errors to stderr
- Don't fail pipeline due to logging issues
- Capture partial results even on agent failure

### Performance Considerations

- Write logs asynchronously when possible
- Buffer writes to reduce I/O
- Don't block agent execution on logging
- Consider log rotation for large runs

## Future Enhancements (Out of Scope)

- Log compression (`.gz` for old logs)
- Log retention policies
- Web UI for browsing logs
- Real-time log streaming during execution
- Log aggregation and search
- Metrics and analytics dashboard
- Export to monitoring tools (Prometheus, etc.)

## Success Criteria

1. All LLM inputs/outputs are captured in structured JSON logs
2. Each pipeline run creates a unique, timestamped log folder
3. Final entries are saved with their assumptions
4. Entries without assumptions have clear messaging
5. Output path is configurable via environment variable
6. System fails gracefully if output directory is not writable
7. All tests pass with 100% coverage of new code
8. Documentation is complete and accurate

## Breaking Changes

None - this is a new feature that doesn't modify existing behavior.

## Migration Path

1. Add `THEORIA_OUTPUT_PATH` to `.env` file
2. Update `.env.example` with new variable
3. Run pipeline - output directory will be created automatically
4. No code changes required in existing workflows

## Dependencies

- No new external dependencies required
- Uses standard library: `pathlib`, `json`, `datetime`, `uuid`
- Integrates with existing: `pydantic`, `litellm`

## Security Considerations

- Validate that output path doesn't escape allowed directories
- Ensure logs don't contain sensitive credentials
- Set appropriate file permissions (644 for files, 755 for directories)
- Don't log AWS credentials or API keys
- Sanitize topic names to prevent path traversal attacks

## Appendix: Example Complete Run

```
/Users/manuel.sanchez.herna/code/theoria-project/output/
├── logs/
│   └── 2026-03-05_14-30-45_schrodinger_equation_a7b3c9d1/
│       ├── run_metadata.json
│       ├── 01_information_gatherer.json
│       ├── 02_metadata_filler.json
│       ├── 03_assumptions_dependencies.json
│       ├── 04_equations_symbols.json
│       ├── 05_derivation.json
│       ├── 06_verifier.json
│       ├── 07_assembler.json
│       └── 08_reviewer.json
└── entries/
    └── schrodinger_equation_time_dependent/
        ├── schrodinger_equation_time_dependent.json
        └── schrodinger_equation_time_dependent_assump.json
```

All files are properly formatted JSON, timestamped, and cross-referenced by `run_id`.
