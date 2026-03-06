# Agent Guidelines for theoria-agents

This document provides guidance for AI agents (like Claude Code) working on the theoria-agents repository.

## General Requirements

- Read the content of CONTRIBUTING.md and README.md and take into account what is mentioned there always.
- If what is mentioned there is in conflict with what the user request, bring the conflict to the user (explain and ask).
- Do not duplicate context or documentation. Keep things in the right place and only there. If it should be in another .md file, refer to the original file where the information is.
- When doing a change review the documentation and update it.

## Specifications files

- The specs to build anything new should be in the .specs file. They should be enumerated sequentially.
- On top of the specs file you should add:

```
**Status:** Draft/Completed/Deprecated
**Created:** YYYY-MM-DD
**Purpose:** one sentence explanation of what it does
```

- When a spec is completed, update the status to "Completed" and add a completion date:

```
**Status:** Completed
**Created:** YYYY-MM-DD
**Completed:** YYYY-MM-DD
**Purpose:** one sentence explanation of what it does
```

### Completed Specifications

- **[3-output-management-system.md](.specs/3-output-management-system.md)** - Structured logging and artifact storage for all agent runs with LLM traceability (Completed: 2026-03-05)

## Testing Requirements

**Always test using Docker.** This ensures tests run in a consistent, isolated environment.

### Pre-Test Check

Before running tests, verify Docker is available:

```bash
docker --version
```

If Docker is not running or not installed, **remind the user to start Docker**.
