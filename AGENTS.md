# Agent Guidelines for theoria-agents

This document provides guidance for AI agents (like Claude Code) working on the theoria-agents repository.

## General Requirements

- Read the content of CONTRIBUTING.md and README.md and take into account what is mentioned there always.
- If what is mentioned there is in conflict with what the user request, bring the conflict to the user (explain and ask).
- Do not duplicate context or documentation. Keep things in the right place and only there. If it should be in another .md file, refer to the original file where the information is.
- When doing a change review the documentation and update it.

## Specifications files

- We will use md files to define specifications for new features, improvements, or changes to the agentic behaviour. These files will be stored in the .specs directory.
- Spec files should be enumerated sequentially.
- **Always re-read the corresponding spec file before implementing**, as it may have been modified by the user since you last read it. If there are changes but they do not make sense to you, ask the user for clarification.
- At the beginning of each spec file you should add:

```
**Status:** Draft/Completed/Deprecated
**Created:** YYYY-MM-DD
**Purpose:** one sentence explanation of what it does
```

- When a spec is completed, update the status to "Completed" and add a completion date in that spec file:

```
**Status:** Completed
**Created:** YYYY-MM-DD
**Completed:** YYYY-MM-DD
**Purpose:** one sentence explanation of what it does
```

## Testing Requirements

**Always test using Docker.** This ensures tests run in a consistent, isolated environment.

### Pre-Test Check

Before running tests, verify Docker is available:

```bash
docker --version
```

If Docker is not running or not installed, **remind the user to start Docker**.
