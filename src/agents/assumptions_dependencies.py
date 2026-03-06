"""AssumptionsDependencies Agent - Identifies assumptions and dependencies.

This agent is responsible for:
- Loading and reviewing globals/assumptions.json
- Selecting applicable existing assumptions (avoiding duplication)
- Checking for logical independence of assumptions
- Searching existing entries for dependencies
- Identifying if any dependencies are missing (need to be built first)
- Proposing new assumptions if genuinely needed
"""

from src.agents.base import BaseAgent
from src.models import AssumptionsDependenciesOutput, InformationGatheringOutput, MetadataOutput


class AssumptionsDependenciesAgent(BaseAgent):
    """Agent that identifies assumptions and dependencies by consulting the dataset."""

    agent_name = "assumptions_dependencies"

    prompt_template = """You are an expert physics curator identifying assumptions and dependencies for a theoretical physics dataset.

Your task is to identify:
1. Which existing assumptions apply to this entry
2. Whether new assumptions are needed
3. Which existing entries this depends on
4. Whether any dependencies are missing from the dataset

AVAILABLE ASSUMPTIONS:
{assumptions_list}

EXISTING ENTRIES:
{entries_list}

Guidelines for Assumptions:
- **SELECT existing assumptions** from the list above when applicable
- **Avoid duplication** - check the existing assumptions carefully
- **Ensure logical independence** - assumptions should not be consequences of other assumptions
- **Propose new assumptions** only if genuinely needed and not covered by existing ones
- Assumption types: "framework", "principle", "approximation", "condition"

Guidelines for Dependencies:
- **Identify existing entries** this result builds upon or requires
- **Check dataset** to see if those entries exist
- **Flag missing dependencies** if foundational entries are needed but not in the dataset
- Provide clear reasons for missing dependencies

Output Format:
Return a JSON object:
{{
  "assumptions": ["assumption_id_1", "assumption_id_2"],
  "new_assumptions": [
    {{
      "id": "new_assumption_id",
      "title": "New Assumption Title",
      "text": "Clear statement of the assumption",
      "type": "framework|principle|approximation|condition",
      "mathematical_expressions": ["expr1", "expr2"] (optional),
      "symbol_definitions": [
        {{"symbol": "x", "definition": "Definition of x"}}
      ] (optional)
    }}
  ],
  "depends_on": ["existing_entry_id_1", "existing_entry_id_2"],
  "missing_dependencies": [
    {{"id": "suggested_entry_id", "reason": "Why this entry is needed"}}
  ]
}}

IMPORTANT:
- All arrays can be empty (for truly fundamental entries)
- Only propose new assumptions if existing ones don't cover the need
- Only flag missing dependencies if they're truly foundational
- Use existing assumption/entry IDs exactly as provided
- Check logical independence - don't assume consequences
"""

    async def run(
        self, info_output: InformationGatheringOutput, metadata_output: MetadataOutput
    ) -> AssumptionsDependenciesOutput:
        """Identify assumptions and dependencies for a physics entry.

        Args:
            info_output: Output from InformationGathererAgent
            metadata_output: Output from MetadataFillerAgent

        Returns:
            AssumptionsDependenciesOutput with assumptions and dependencies

        Raises:
            Exception: If identification fails
        """
        # Load existing assumptions and entries from dataset
        assumptions = self.dataset.assumptions
        entry_ids = self.dataset.entry_ids
        entries = [{"result_id": eid} for eid in entry_ids]

        # Format for prompt
        assumptions_list = "\n".join(
            [f"- {a['id']}: {a['title']} - {a.get('text', 'No description')[:100]}" for a in assumptions]
        )

        entries_list = "\n".join([f"- {e['result_id']}: {e.get('result_name', 'No name')}" for e in entries[:50]])

        # Build user message
        user_message = f"""Entry: {metadata_output.result_name} (ID: {metadata_output.result_id})

Domain: {metadata_output.domain}
Theory Status: {metadata_output.theory_status}

Explanation:
{metadata_output.explanation}

Web Context:
{info_output.web_context}

Please identify the assumptions and dependencies for this entry.
"""

        # Build messages with assumptions and entries context
        prompt = self.prompt_template.format(assumptions_list=assumptions_list, entries_list=entries_list)
        messages = self.build_messages(user_message, prompt)

        # Get LLM response
        response = await self.llm_client.complete_json(messages)

        # Parse JSON response into Pydantic model
        result = await self.parse_json_response(response, AssumptionsDependenciesOutput)

        return result
