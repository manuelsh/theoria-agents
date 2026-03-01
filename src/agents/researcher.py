"""Researcher agent for gathering context, dependencies, and assumptions."""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.models import ResearchOutput
from src.utils.web_search import search_derivation_context


class ResearcherAgent(BaseAgent):
    """Agent that researches a physics topic and gathers context."""

    agent_name = "researcher"

    async def run(self, topic: str, hints: dict[str, Any] | None = None) -> ResearchOutput:
        """Research a physics topic.

        Args:
            topic: The topic name (e.g., "Schrödinger equation").
            hints: Optional hints like suggested domain or dependencies.

        Returns:
            ResearchOutput with dependencies, assumptions, references, etc.
        """
        hints = hints or {}

        # Gather web context
        web_context = await search_derivation_context(topic)

        # Build the prompt
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(topic, web_context, hints)

        messages = self.build_messages(user_prompt, system_prompt)
        response = await self.llm_client.complete_json(messages)

        # Parse and return
        result = await self.parse_json_response(response, ResearchOutput)

        # Ensure web_context is included
        if not result.web_context:
            result.web_context = web_context

        return result

    def _build_system_prompt(self) -> str:
        """Build the system prompt with dataset context and guidelines."""
        # Load guidelines dynamically from theoria-dataset
        guidelines = self.get_guidelines()

        # Add dataset context
        assumptions_context = self.dataset.format_assumptions_for_prompt()
        entries_context = self.dataset.format_entries_for_prompt()

        return f"""You are preparing research for a theoria-dataset entry.

{guidelines}

{assumptions_context}

{entries_context}"""

    def _build_user_prompt(
        self, topic: str, web_context: str, hints: dict[str, Any]
    ) -> str:
        """Build the user prompt with topic context only."""
        return f"""Research this physics topic for creating a dataset entry.

## Topic
{topic}

## Web Research Context
{web_context[:8000]}

## Hints (if provided)
- Suggested domain: {hints.get('domain', 'Not specified')}
- Suggested dependencies: {hints.get('depends_on', 'Not specified')}

## Required Output
- Select `assumptions` from the existing global assumptions list above
- If a required assumption doesn't exist, add it to `new_assumptions`
- Select `depends_on` from existing entries if this derivation builds on them

```json
{{
  "result_id": "...",
  "result_name": "...",
  "depends_on": ["existing_entry_id"],
  "assumptions": ["existing_assumption_id"],
  "new_assumptions": [
    {{
      "id": "new_assumption_id",
      "title": "Short Title",
      "text": "Description of the assumption",
      "type": "principle|empirical|approximation",
      "mathematical_expressions": ["optional math"],
      "symbol_definitions": [{{"symbol": "x", "definition": "..."}}]
    }}
  ],
  "references": [{{"id": "R1", "citation": "APA format"}}],
  "domain": "quant-ph",
  "theory_status": "current",
  "historical_context": {{...}},
  "web_context": "Summary of key derivation information"
}}
```
"""

