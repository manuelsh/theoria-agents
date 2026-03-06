# Markdown Log Format Specification

**Status:** Completed
**Created:** 2026-03-06
**Completed:** 2026-03-06
**Purpose:** Replace JSON agent logs with human-readable Markdown format

## Overview

The current JSON log format for agent executions is hard to read due to escaped newlines (`\n`) in content fields. This specification defines a Markdown-based format that preserves all information while being significantly more readable.

## Goals

1. **Readability**: Logs should be easy to scan and understand at a glance
2. **Completeness**: All existing log data must be preserved
3. **Consistency**: Predictable structure across all agent logs
4. **Searchability**: Text-based format remains grep-friendly

## Current Format (JSON)

```json
{
  "agent_name": "information_gatherer",
  "timestamp_start": "2026-03-06T22:37:21.740535+01:00",
  "timestamp_end": "2026-03-06T22:37:29.051873+01:00",
  "duration_seconds": 7.311338,
  "model": "bedrock/converse/arn:aws:bedrock:eu-west-1:...",
  "input": {
    "messages": [
      {
        "role": "system",
        "content": "# Agent: Information Gatherer\n**Version:** 1.0.0\n..."
      },
      {
        "role": "user",
        "content": "Topic: Newton's laws of motion\n..."
      }
    ],
    "temperature": 0.3,
    "max_tokens": 4096
  },
  "output": {
    "content": "```json\n{\"web_context\": \"Newton's laws...\n..."
  },
  "status": "success",
  "error": null
}
```

**Problems:**
- Escaped newlines (`\n`) make content unreadable
- Nested JSON structure is visually dense
- Difficult to quickly scan for relevant information

## New Format (Markdown)

### File Naming

Change file extension from `.json` to `.md`:
- Before: `01_information_gatherer.json`
- After: `01_information_gatherer.md`

### Template Structure

```markdown
# {agent_name}

| Field | Value |
|-------|-------|
| Status | {status_emoji} {status} |
| Started | {timestamp_start} |
| Ended | {timestamp_end} |
| Duration | {duration_seconds}s |
| Model | {model} |

## Parameters

| Parameter | Value |
|-----------|-------|
| temperature | {temperature} |
| max_tokens | {max_tokens} |

## Input Messages

### System

{system_content}

### User

{user_content}

## Output

{output_content}

## Error

{error_or_none}
```

### Status Indicators

| Status | Emoji | Display |
|--------|-------|---------|
| success | `[OK]` | `[OK] success` |
| error | `[ERR]` | `[ERR] error` |

### Complete Example

```markdown
# information_gatherer

| Field | Value |
|-------|-------|
| Status | [OK] success |
| Started | 2026-03-06T22:37:21.740535+01:00 |
| Ended | 2026-03-06T22:37:29.051873+01:00 |
| Duration | 7.31s |
| Model | bedrock/converse/arn:aws:bedrock:eu-west-1:490863270076:application-inference-profile/bltyu2vsdhmt |

## Parameters

| Parameter | Value |
|-----------|-------|
| temperature | 0.3 |
| max_tokens | 4096 |

## Input Messages

### System

# Agent: Information Gatherer
**Version:** 1.0.0
**Last Updated:** 2026-03-04

## Role
Expert physics researcher gathering information for a theoretical physics dataset.

## System Prompt
Your task is to gather comprehensive, graduate-level information about a physics topic from the provided web content.

## Guidelines
- Extract factual, graduate-level physics content
- Focus on the core concepts, principles, and applications
- Identify historical context if available (who developed it, when, key insights)
- Suggest 1-3 authoritative academic references if mentioned in the content
- Keep the web_context concise but informative (aim for 2-4 paragraphs)
- Prioritize accuracy and clarity

## Output Format
Return a JSON object with the following structure:
...

### User

Topic: Newton's laws of motion

Web Content:
No Wikipedia content found for: Newton's laws of motion

Please extract and organize the key information about this physics topic according to the guidelines.

## Output

```json
{
  "web_context": "Newton's laws of motion are three fundamental principles that form the foundation of classical mechanics, describing the relationship between the motion of objects and the forces acting upon them. The first law, the law of inertia, states that an object at rest stays at rest and an object in motion stays in motion with constant velocity unless acted upon by a net external force. The second law establishes the quantitative relationship F = ma, where the net force on an object equals its mass times its acceleration, providing a precise mathematical framework for predicting motion. The third law states that for every action there is an equal and opposite reaction, meaning forces always occur in pairs acting on different objects.

These laws are applicable to macroscopic objects moving at speeds much slower than the speed of light and form the basis for understanding everything from projectile motion to planetary orbits. They provide the framework for analyzing mechanical systems, from simple pendulums to complex engineering structures. While superseded by relativistic mechanics at high speeds and quantum mechanics at atomic scales, Newton's laws remain extraordinarily accurate and practical for everyday applications and continue to be essential tools in physics and engineering education and practice.",
  "historical_context": {
    "importance": "Newton's laws revolutionized physics by providing the first comprehensive mathematical framework for understanding motion and forces, unifying terrestrial and celestial mechanics and establishing the foundation for classical physics that dominated scientific thought for over two centuries.",
    "development_period": "1687",
    "key_insights": [
      "Motion does not require a force to maintain it, only to change it - overturning Aristotelian physics",
      "Force, mass, and acceleration are quantitatively related through a simple mathematical equation",
      "Forces are interactions between objects that always occur in pairs"
    ]
  },
  "suggested_references": []
}
```

## Error

None
```

### Retry Information (when applicable)

When retries occur, add a section after Error:

```markdown
## Retries

**Total retries:** 2

| Attempt | Timestamp | Error |
|---------|-----------|-------|
| 1 | 2026-03-06T22:37:25.123+01:00 | JSONDecodeError: Expecting value at line 1 |
| 2 | 2026-03-06T22:37:27.456+01:00 | ValidationError: missing required field |
```

## Implementation

### Changes to `output_manager.py`

Modify `log_agent_execution()` to write Markdown instead of JSON:

```python
def log_agent_execution(
    self,
    agent_name: str,
    log_data: dict[str, Any],
    sequence_number: int,
) -> None:
    """Write agent execution log to Markdown file."""
    if self.current_run_folder is None:
        raise RuntimeError(
            "No run folder has been created. Call create_run_folder() first."
        )

    filename = f"{sequence_number:02d}_{agent_name}.md"
    log_file = self.current_run_folder / filename

    markdown_content = self._format_log_as_markdown(log_data)

    try:
        with open(log_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
    except IOError as e:
        print(f"ERROR: Failed to write log for {agent_name}: {e}", file=sys.stderr)
```

### New Method: `_format_log_as_markdown()`

```python
def _format_log_as_markdown(self, log_data: dict[str, Any]) -> str:
    """Convert log data dictionary to Markdown format."""
    # Implementation details in code
```

### Formatting Rules

1. **Duration**: Round to 2 decimal places (e.g., `7.31s`)
2. **Timestamps**: Keep full ISO 8601 format for precision
3. **Model**: Display full model identifier (useful for debugging)
4. **Content blocks**: Preserve original formatting, no escaping needed
5. **JSON in output**: Wrap in triple backticks with `json` language hint
6. **Empty fields**: Display "None" for null/empty values

## Directory Structure Change

```
{THEORIA_OUTPUT_PATH}/
├── logs/
│   └── {YYYY-MM-DD_HH-MM-SS}_{topic_slug}_{run_id}/
│       ├── run_metadata.json          # Keep as JSON (machine-readable)
│       ├── 01_information_gatherer.md # Changed to .md
│       ├── 02_metadata_filler.md
│       ├── 03_assumptions_dependencies.md
│       ├── 04_equations_symbols.md
│       ├── 05_derivation.md
│       ├── 06_verifier.md
│       ├── 07_assembler.md
│       └── 08_reviewer.md
└── entries/
    └── {entry_name}/
        ├── {entry_name}.json          # Keep as JSON (data file)
        └── {entry_name}_assump.json   # Keep as JSON (data file)
```

**Note**: Only agent execution logs change to Markdown. Metadata and entry files remain JSON since they are consumed programmatically.

## Migration

### Backward Compatibility

- No migration needed for existing logs
- Old JSON logs remain readable
- New runs will produce Markdown logs

### Test Updates

Update test assertions to expect `.md` files instead of `.json`:

```python
# Before
assert (run_folder / "01_information_gatherer.json").exists()

# After
assert (run_folder / "01_information_gatherer.md").exists()
```

## Success Criteria

1. Agent logs are written as `.md` files
2. All information from JSON format is preserved
3. Content is displayed without escaped newlines
4. Logs are easy to read in any text editor or IDE
5. Markdown renders correctly in VS Code, GitHub, etc.
6. All existing tests pass after updates
7. `run_metadata.json` and entry files remain JSON

## Test Changes

The following tests in `test_output_manager.py` need updates:

### Tests to Modify

#### `TestAgentLogging.test_log_agent_execution_creates_file`
**Change:** Expect `.md` instead of `.json`
```python
# Before
expected_file = run_folder / "01_information_gatherer.json"

# After
expected_file = run_folder / "01_information_gatherer.md"
```

#### `TestAgentLogging.test_log_agent_execution_json_format`
**Change:** Rename to `test_log_agent_execution_markdown_format` and verify markdown content instead of JSON
```python
# Before
log_file = run_folder / "01_information_gatherer.json"
with open(log_file) as f:
    loaded_data = json.load(f)
assert loaded_data == log_data

# After
log_file = run_folder / "01_information_gatherer.md"
content = log_file.read_text()
assert "# information_gatherer" in content
assert "[OK] success" in content
assert "test-model" in content
```

#### `TestAgentLogging.test_log_agent_execution_sequence_numbers`
**Change:** Expect `.md` extension
```python
# Before
assert (run_folder / "01_agent1.json").exists()
assert (run_folder / "10_agent2.json").exists()

# After
assert (run_folder / "01_agent1.md").exists()
assert (run_folder / "10_agent2.md").exists()
```

### New Tests to Add

#### `test_log_agent_execution_markdown_contains_all_sections`
Verify all required sections are present:
```python
def test_log_agent_execution_markdown_contains_all_sections(self, output_manager):
    """Test that markdown log contains all required sections."""
    run_folder = output_manager.create_run_folder("Test Topic", "abc123")

    log_data = {
        "agent_name": "test_agent",
        "timestamp_start": "2026-03-06T14:30:45.123+01:00",
        "timestamp_end": "2026-03-06T14:30:52.456+01:00",
        "duration_seconds": 7.333,
        "model": "bedrock/test-model",
        "input": {
            "messages": [
                {"role": "system", "content": "System prompt"},
                {"role": "user", "content": "User message"},
            ],
            "temperature": 0.3,
            "max_tokens": 4096,
        },
        "output": {"content": "Output content"},
        "status": "success",
        "error": None,
    }

    output_manager.log_agent_execution("test_agent", log_data, 1)

    log_file = run_folder / "01_test_agent.md"
    content = log_file.read_text()

    # Check all sections exist
    assert "# test_agent" in content
    assert "## Parameters" in content
    assert "## Input Messages" in content
    assert "### System" in content
    assert "### User" in content
    assert "## Output" in content
    assert "## Error" in content
```

#### `test_log_agent_execution_markdown_preserves_newlines`
Verify that content newlines are preserved (the main goal):
```python
def test_log_agent_execution_markdown_preserves_newlines(self, output_manager):
    """Test that markdown preserves newlines in content."""
    run_folder = output_manager.create_run_folder("Test Topic", "abc123")

    multiline_content = "Line 1\nLine 2\nLine 3"
    log_data = {
        "agent_name": "test_agent",
        "input": {
            "messages": [{"role": "system", "content": multiline_content}],
        },
        "output": {"content": "Response"},
        "status": "success",
        "error": None,
    }

    output_manager.log_agent_execution("test_agent", log_data, 1)

    log_file = run_folder / "01_test_agent.md"
    content = log_file.read_text()

    # Content should have actual newlines, not escaped \n
    assert "Line 1\nLine 2\nLine 3" in content
    assert "Line 1\\nLine 2" not in content
```

#### `test_log_agent_execution_markdown_with_retries`
Verify retry section appears when retries occurred:
```python
def test_log_agent_execution_markdown_with_retries(self, output_manager):
    """Test that markdown includes retry section when retries occurred."""
    run_folder = output_manager.create_run_folder("Test Topic", "abc123")

    log_data = {
        "agent_name": "test_agent",
        "status": "success",
        "error": None,
        "retries": 2,
        "retry_details": [
            {"attempt": 1, "timestamp": "2026-03-06T14:30:46.000+01:00", "error": "Timeout"},
            {"attempt": 2, "timestamp": "2026-03-06T14:30:48.000+01:00", "error": "Parse error"},
        ],
    }

    output_manager.log_agent_execution("test_agent", log_data, 1)

    log_file = run_folder / "01_test_agent.md"
    content = log_file.read_text()

    assert "## Retries" in content
    assert "Total retries:** 2" in content
    assert "Timeout" in content
    assert "Parse error" in content
```

#### `test_log_agent_execution_markdown_error_status`
Verify error status formatting:
```python
def test_log_agent_execution_markdown_error_status(self, output_manager):
    """Test that error status is displayed correctly."""
    run_folder = output_manager.create_run_folder("Test Topic", "abc123")

    log_data = {
        "agent_name": "test_agent",
        "status": "error",
        "error": "ValueError: Invalid JSON response",
    }

    output_manager.log_agent_execution("test_agent", log_data, 1)

    log_file = run_folder / "01_test_agent.md"
    content = log_file.read_text()

    assert "[ERR] error" in content
    assert "ValueError: Invalid JSON response" in content
```

### Tests That Remain Unchanged

The following tests don't need changes (they don't interact with agent log files):
- All tests in `TestOutputManagerInitialization`
- All tests in `TestSlugification`
- All tests in `TestRunFolderCreation`
- All tests in `TestRunMetadata` (metadata stays JSON)
- All tests in `TestEntryStorage` (entries stay JSON)
- All tests in `TestUtilityMethods`
- `test_agent_logger.py` - No changes needed (it mocks `OutputManager`)

## Future Considerations (Out of Scope)

- Syntax highlighting for different content types
- Collapsible sections for long content
- HTML export for web viewing
- Side-by-side input/output comparison view
