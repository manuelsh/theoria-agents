# Theoria Agents Prompts

This directory contains all agent prompts for the theoria-agents system. Prompts are stored as markdown files and loaded dynamically at runtime.

## Directory Structure

```
prompts/
├── README.md                 # This file
├── __init__.py              # Prompt loading exports
├── loader.py                # PromptLoader implementation
├── registry.py              # PromptRegistry implementation
├── base/                    # Shared prompt components
│   ├── asciimath_rules.md
│   ├── derivation_quality.md
│   ├── assumptions_guidelines.md
│   └── verification_standards.md
└── agents/                  # Agent-specific prompts
    ├── information_gatherer.md
    ├── metadata_filler.md
    ├── assumptions_dependencies.md
    └── equations_symbols.md
```

## Prompt File Format

Each agent prompt follows this structure:

```markdown
# Agent: [Name]
**Version:** X.Y.Z
**Last Updated:** YYYY-MM-DD

## Role
[Agent's role description]

## System Prompt
[Main system prompt]

## Guidelines
[Agent-specific guidelines]

@include base/shared_component.md

## Output Format
[Expected JSON structure]

## Important Notes
[Additional notes]
```

## Shared Components

Shared components in `base/` contain reusable prompt fragments:

- **asciimath_rules.md** - AsciiMath notation standards (fractions, derivatives, subscripts)
- **derivation_quality.md** - Derivation completeness and quality standards
- **assumptions_guidelines.md** - Logical independence and precision rules for assumptions
- **verification_standards.md** - Programmatic verification requirements

### Using Shared Components

Include shared components with the `@include` directive:

```markdown
@include base/asciimath_rules.md
```

The `PromptLoader` will automatically resolve and insert the component content.

## Agent Prompts

### Phase 1: Research & Foundation

1. **information_gatherer** - Gathers web context and historical information
2. **metadata_filler** - Fills entry metadata fields
3. **assumptions_dependencies** - Identifies assumptions and dependencies
4. **equations_symbols** - Defines equations and symbols

### Phase 2: Derivation & Verification

5. **derivation** - Uses dynamic prompts from `dataset.get_full_guidelines()`
6. **verifier** - Uses dynamic prompts from `dataset.get_full_guidelines()`
7. **assembler** - Combines outputs (minimal prompting)
8. **reviewer** - Quality checking with dynamic guidelines

## How Prompts Are Loaded

1. **BaseAgent** initializes a `PromptRegistry` (lazy loaded)
2. When `build_messages()` is called, it calls `get_prompt()`
3. `get_prompt()` loads the prompt from `prompts/agents/{agent_name}.md`
4. `PromptLoader` resolves any `@include` directives
5. The complete prompt is cached for performance
6. Fallback to `prompt_template` attribute if file doesn't exist (backward compatibility)

## Adding a New Agent Prompt

1. Create `prompts/agents/new_agent.md` following the format above
2. Include shared components with `@include` where applicable
3. The agent will automatically load it via `get_prompt()`
4. Remove any hardcoded `prompt_template` from the agent class

## Modifying Prompts

**Important:** Changes to prompt files take effect immediately on next agent initialization (no code changes needed).

1. Edit the relevant `.md` file
2. Test locally or rebuild Docker image
3. Shared component changes affect all agents that include them

## Guidelines for Avoiding Duplication

**DO NOT duplicate content from `theoria-dataset/CONTRIBUTING.md` or `AI_guidance.md`.**

- Dataset schema rules belong in `theoria-dataset`
- Agent-specific instructions belong here
- Reference dataset guidelines with `dataset.get_full_guidelines()` in code

## Testing Prompts

Run prompt validation tests:

```bash
pytest tests/test_prompt_loading.py
```

Validate all prompts load correctly:

```python
from prompts.registry import PromptRegistry

registry = PromptRegistry()
results = registry.validate_all()
print(results)  # All should be True
```

## Version History

- **1.0.0** (2026-03-05) - Initial migration from hardcoded `prompt_template` strings
  - Migrated: information_gatherer, metadata_filler, assumptions_dependencies, equations_symbols
  - Created shared components: asciimath_rules, derivation_quality, assumptions_guidelines, verification_standards
