# Spec: Prompt Consolidation and Architecture

**Status:** Draft
**Created:** 2026-03-04
**Purpose:** Consolidate all agent prompts into a single source of truth

---

## Problem Analysis

### Current State

The current architecture has **scattered prompt definitions** across multiple locations:

1. **guide.md** (123 lines)
   - General physics entry quality improvement guidelines
   - AsciiMath notation rules
   - Derivation completeness requirements
   - Assumptions independence rules
   - Planning prompt for creating entries

2. **Individual Agent Files** (8 agents)
   - Each agent has `prompt_template` hardcoded as string literal
   - Duplicated guidelines and rules across agents
   - Example agents:
     - `information_gatherer.py`: Lines 21-55 (prompt_template)
     - `metadata_filler.py`: Lines 24-100 (prompt_template)
     - `assumptions_dependencies.py`: Lines 21-76 (prompt_template)
     - `derivation.py`: Uses dynamic system prompt building
     - `reviewer.py`: Builds prompts dynamically from guidelines

3. **Dataset Guidelines** (external dependency)
   - `base.py` calls `dataset.get_full_guidelines()` which reads:
     - `CONTRIBUTING.md`
     - `AI_guidance.md`
   - Used by `derivation.py` and `reviewer.py`

### Issues

1. **Duplication:** Rules about AsciiMath, derivation quality, assumptions appear in multiple places
2. **Inconsistency:** Different agents may have slightly different phrasing of the same rule
3. **Maintenance burden:** Updating a guideline requires changes in multiple files
4. **Unclear source of truth:** Is it guide.md? Agent prompt_template? Dataset guidelines?
5. **Mixed concerns:** guide.md contains both agent-specific prompts AND general quality guidelines
6. **Versioning:** No way to track which version of prompts produced which entries

---

## Proposed Architecture

### Core Principle

**Single Source of Truth (SSoT):** All prompts live in one structured location, loaded dynamically by agents.

### Directory Structure

```
theoria-agents/
├── prompts/                          # NEW: Centralized prompt directory
│   ├── __init__.py                   # Prompt loader utilities
│   ├── registry.py                   # Prompt registry and versioning
│   ├── base/                         # Shared prompt components
│   │   ├── asciimath_rules.md
│   │   ├── derivation_quality.md
│   │   ├── assumptions_guidelines.md
│   │   ├── output_format_rules.md
│   │   └── dataset_schema.md
│   ├── agents/                       # Agent-specific prompts
│   │   ├── information_gatherer.md
│   │   ├── metadata_filler.md
│   │   ├── assumptions_dependencies.md
│   │   ├── equations_symbols.md
│   │   ├── derivation.md
│   │   ├── verifier.md
│   │   ├── assembler.md
│   │   └── reviewer.md
│   └── versions/                     # Versioned prompt snapshots (optional)
│       └── v1.0.0/
├── src/
│   └── agents/
│       ├── base.py                   # UPDATED: Load prompts from registry
│       ├── information_gatherer.py   # UPDATED: Remove prompt_template
│       └── ...
└── guide.md                          # DEPRECATED or becomes high-level docs
```

### Prompt File Format

Each agent prompt file follows this structure:

```markdown
# Agent: [Name]

**Version:** 1.0.0
**Last Updated:** 2026-03-04

## Role

[Agent's role description]

## System Prompt

[Main system prompt that defines the agent's task]

## Guidelines

[Agent-specific guidelines]

## Shared Components

- @include base/asciimath_rules.md
- @include base/assumptions_guidelines.md

## Output Format

[Expected JSON structure]

## Examples

[Optional examples]
```

### Implementation Components

#### 1. Prompt Loader (`prompts/__init__.py`)

```python
from pathlib import Path
from typing import Dict, Optional

class PromptLoader:
    """Loads and composes prompts from markdown files."""

    def __init__(self, prompts_dir: Path):
        self.prompts_dir = prompts_dir
        self.base_dir = prompts_dir / "base"
        self.agents_dir = prompts_dir / "agents"
        self._cache: Dict[str, str] = {}

    def load_agent_prompt(self, agent_name: str) -> str:
        """Load and compose an agent's full prompt."""
        # Read agent prompt file
        # Process @include directives
        # Return composed prompt
        pass

    def load_base_component(self, component_name: str) -> str:
        """Load a shared prompt component."""
        pass

    def get_prompt_version(self, agent_name: str) -> str:
        """Get the version of a prompt."""
        pass
```

#### 2. Prompt Registry (`prompts/registry.py`)

```python
from dataclasses import dataclass
from typing import Dict

@dataclass
class PromptMetadata:
    version: str
    last_updated: str
    agent_name: str
    shared_components: list[str]

class PromptRegistry:
    """Central registry of all prompts with versioning."""

    def __init__(self):
        self.loader = PromptLoader(...)
        self._metadata: Dict[str, PromptMetadata] = {}

    def get_prompt(self, agent_name: str, version: Optional[str] = None) -> str:
        """Get an agent prompt, optionally by version."""
        pass

    def list_agents(self) -> list[str]:
        """List all available agent prompts."""
        pass

    def validate_all(self) -> Dict[str, bool]:
        """Validate all prompts can be loaded."""
        pass
```

#### 3. Updated BaseAgent

```python
class BaseAgent(ABC):
    """Abstract base class for all agents in the pipeline."""

    agent_name: str = "base"

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        config: dict[str, Any] | None = None,
        dataset_loader: DatasetLoader | None = None,
        prompt_registry: PromptRegistry | None = None,  # NEW
    ):
        self.config = config or load_config()
        self.dataset = dataset_loader or DatasetLoader()
        self.prompt_registry = prompt_registry or PromptRegistry()  # NEW

        # ... existing code ...

    def get_prompt(self) -> str:  # NEW
        """Load this agent's prompt from the registry."""
        return self.prompt_registry.get_prompt(self.agent_name)

    def build_messages(
        self,
        user_content: str,
        system_content: str | None = None,
    ) -> list[dict[str, str]]:
        # Use loaded prompt if no system_content provided
        system = system_content or self.get_prompt()
        # ... existing code ...
```

---

## Migration Plan

### Phase 0: Testing Infrastructure (FIRST - Critical)

**Set up comprehensive tests BEFORE making any changes**

- [ ] **Create baseline integration tests**
  - [ ] Test each agent individually with known inputs
  - [ ] Capture current outputs as "golden" reference
  - [ ] Store test fixtures in `tests/fixtures/`

- [ ] **Create prompt comparison tests**
  - [ ] Load prompts both ways (old `prompt_template` vs new `PromptLoader`)
  - [ ] Assert outputs are identical for same inputs
  - [ ] Test all 8 agents with real-world examples

- [ ] **Create prompt validation tests**
  - [ ] Test `@include` directive resolution
  - [ ] Test missing file handling
  - [ ] Test circular dependency detection
  - [ ] Test prompt caching behavior

- [ ] **Add test utilities**
  - [ ] `test_helpers.py` with `compare_agent_outputs()`
  - [ ] Fixture generators for common test cases
  - [ ] Mock LLM client for deterministic testing

---

### Phase 1: Setup Structure

- [ ] Create `prompts/` directory structure
- [ ] Implement `PromptLoader` with basic file reading
- [ ] Implement `PromptRegistry` with caching
- [ ] Run Phase 0 tests to ensure nothing breaks

### Phase 2: Extract Shared Components

- [ ] Create `base/asciimath_rules.md` from guide.md
- [ ] Create `base/derivation_quality.md` from guide.md
- [ ] Create `base/assumptions_guidelines.md` from guide.md
- [ ] Create `base/output_format_rules.md` (general JSON formatting)
- [ ] Run prompt validation tests
- [ ] Validate extraction with comparison tests

### Phase 3: Migrate Agent Prompts ONE BY ONE

**For each agent:**

1. Extract `prompt_template` to `agents/{agent_name}.md`
2. Identify shared components and use `@include`
3. Add version and metadata headers
4. Update agent to use `self.get_prompt()` (keep `prompt_template` as fallback)
5. **RUN FULL TEST SUITE** - must pass before moving to next agent
6. **Compare outputs with golden baseline** - must match exactly
7. Remove `prompt_template` fallback only after tests pass

**Agent Migration Order:**

1. `information_gatherer` (simplest)
2. `metadata_filler`
3. `assumptions_dependencies`
4. `equations_symbols`
5. `derivation`
6. `verifier`
7. `assembler`
8. `reviewer`

### Phase 4: Remove guide.md

**guide.md is redundant - all content moves to prompts/**

- [ ] Verify all content from guide.md is now in `prompts/`
- [ ] Delete guide.md entirely
- [ ] Update all references (README, CONTRIBUTING.md)
- [ ] Add `prompts/README.md` explaining structure

### Phase 5: Versioning (Optional - Future)

- [ ] Implement prompt versioning system
- [ ] Add version tracking to generated entries

---

## Example: Migrated Metadata Filler

### Before (`metadata_filler.py`)

```python
class MetadataFillerAgent(BaseAgent):
    agent_name = "metadata_filler"

    prompt_template = """You are an expert physics curator...
    [100 lines of hardcoded prompt]
    """
```

### After (`metadata_filler.py`)

```python
class MetadataFillerAgent(BaseAgent):
    agent_name = "metadata_filler"
    # No prompt_template - loaded from prompts/agents/metadata_filler.md
```

### New File (`prompts/agents/metadata_filler.md`)

````markdown
# Agent: Metadata Filler

**Version:** 1.0.0
**Last Updated:** 2026-03-04

## Role

Expert physics curator filling metadata for theoretical physics dataset entries.

## System Prompt

Your task is to fill ALL metadata fields for a physics entry based on gathered information.

## Guidelines

### result_id (required)

- Lowercase letters, numbers, and underscores only
- Descriptive and recognizable (e.g., "newtons_second_law")
- Unique within the dataset

### result_name (required, max 100 characters)

- Clear, concise name for the result
- Proper capitalization and formatting

@include base/asciimath_rules.md

### explanation (required, 2-5 sentences, max 800 characters)

- Conceptual overview (no derivation steps)
- Graduate-level audience
- Any math notation in AsciiMath format enclosed in backticks
- Focus on WHAT and WHY, not HOW

[... rest of guidelines ...]

## Output Format

```json
{
  "result_id": "lowercase_with_underscores",
  "result_name": "Proper Name",
  ...
}
```
````

```
---

## Success Criteria

- [ ] **Testing:** Full test suite passes with 100% agent coverage
- [ ] **Testing:** Golden baseline outputs match exactly after migration
- [ ] **Architecture:** All 8 agents load prompts from `prompts/` directory
- [ ] **Architecture:** No duplicated rules across files
- [ ] **Architecture:** All agents use `self.get_prompt()` - no hardcoded `prompt_template`
- [ ] **Cleanup:** `guide.md` completely removed
- [ ] **Cleanup:** All guide.md content migrated to `prompts/base/`
- [ ] **Documentation:** `prompts/README.md` explains structure


```
