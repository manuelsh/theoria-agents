"""Derivation agent for generating step-by-step mathematical derivations."""

import json

from src.agents.base import BaseAgent
from src.models import DerivationOutput, ResearchOutput


class DerivationAgent(BaseAgent):
    """Agent that generates complete step-by-step derivations."""

    agent_name = "derivation"

    async def run(self, research: ResearchOutput) -> DerivationOutput:
        """Generate a derivation based on research output.

        Args:
            research: Output from the Researcher agent.

        Returns:
            DerivationOutput with equations, explanation, definitions, and derivation steps.
        """
        system_prompt = self._build_system_prompt(research)
        user_prompt = self._build_user_prompt(research)

        messages = self.build_messages(user_prompt, system_prompt)
        response = await self.llm_client.complete_json(messages)

        return await self.parse_json_response(response, DerivationOutput)

    def _build_system_prompt(self, research: ResearchOutput) -> str:
        """Build the system prompt with derivation guidelines from theoria-dataset."""
        # Load guidelines dynamically
        guidelines = self.get_guidelines()

        # Load example entry for reference
        example = self.dataset.load_example_entry()
        example_derivation = json.dumps(example["derivation"][:3], indent=2)
        example_definitions = json.dumps(example["definitions"][:4], indent=2)

        return f"""You are creating a theoria-dataset entry.

{guidelines}

## Example (from Schrödinger equation entry)
Derivation steps:
```json
{example_derivation}
```

Definitions:
```json
{example_definitions}
```"""

    def _build_user_prompt(self, research: ResearchOutput) -> str:
        """Build the user prompt with topic context only."""
        # Get relevant assumptions text
        assumptions_text = []
        for aid in research.assumptions:
            assumption = self.dataset.get_assumption_by_id(aid)
            if assumption:
                assumptions_text.append(f"- {aid}: {assumption.get('title', '')}")

        return f"""Generate the derivation fields for this physics entry.

## Topic
- result_id: {research.result_id}
- result_name: {research.result_name}
- domain: {research.domain}

## Research Context
{research.web_context[:6000]}

## Assumptions to Use
{chr(10).join(assumptions_text) or 'None specified'}

## Dependencies
{', '.join(research.depends_on) or 'First principles only'}

## Required Output
Generate JSON with these fields: result_equations, explanation, definitions, derivation

Follow ALL requirements from the guidelines above for each field.
```json
{{
  "result_equations": [...],
  "explanation": "...",
  "definitions": [...],
  "derivation": [...]
}}
```
"""

