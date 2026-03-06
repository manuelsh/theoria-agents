"""Derivation agent for generating step-by-step mathematical derivations."""

import json

from src.agents.base import BaseAgent
from src.models import (
    AssumptionsDependenciesOutput,
    DerivationOutput,
    EquationsSymbolsOutput,
    InformationGatheringOutput,
    MetadataOutput,
)


class DerivationAgent(BaseAgent):
    """Agent that generates complete step-by-step derivations."""

    agent_name = "derivation"

    async def run(
        self,
        info_output: InformationGatheringOutput,
        metadata_output: MetadataOutput,
        assumptions_deps_output: AssumptionsDependenciesOutput,
        equations_symbols_output: EquationsSymbolsOutput,
    ) -> DerivationOutput:
        """Generate a derivation based on previous agent outputs.

        Args:
            info_output: Output from InformationGathererAgent
            metadata_output: Output from MetadataFillerAgent
            assumptions_deps_output: Output from AssumptionsDependenciesAgent
            equations_symbols_output: Output from EquationsSymbolsAgent

        Returns:
            DerivationOutput with equations, explanation, definitions, and derivation steps.
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(
            info_output, metadata_output, assumptions_deps_output, equations_symbols_output
        )

        messages = self.build_messages(user_prompt, system_prompt)
        response = await self.llm_client.complete_json(messages)

        return await self.parse_json_response(response, DerivationOutput)

    def _build_system_prompt(self) -> str:
        """Build the system prompt with derivation guidelines from theoria-dataset."""
        guidelines = self.get_guidelines()

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

    def _build_user_prompt(
        self,
        info_output: InformationGatheringOutput,
        metadata_output: MetadataOutput,
        assumptions_deps_output: AssumptionsDependenciesOutput,
        equations_symbols_output: EquationsSymbolsOutput,
    ) -> str:
        """Build the user prompt with topic context."""
        assumptions_text = []
        for aid in assumptions_deps_output.assumptions:
            assumption = self.dataset.get_assumption_by_id(aid)
            if assumption:
                assumptions_text.append(f"- {aid}: {assumption.get('title', '')}")

        equations_text = []
        for eq in equations_symbols_output.result_equations:
            equations_text.append(f"- {eq.id}: {eq.equation}")

        return f"""Generate the derivation fields for this physics entry.

## Topic
- result_id: {metadata_output.result_id}
- result_name: {metadata_output.result_name}
- domain: {metadata_output.domain}

## Research Context
{info_output.raw_web_content}

## Result Equations (already defined)
{chr(10).join(equations_text)}

## Symbol Definitions (already defined)
{json.dumps([d.model_dump() for d in equations_symbols_output.definitions], indent=2)}

## Assumptions to Use
{chr(10).join(assumptions_text) or 'None specified'}

## Dependencies
{', '.join(assumptions_deps_output.depends_on) or 'First principles only'}

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

