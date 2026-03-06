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

Web Context (Full):
{info_output.raw_web_content}

Please identify the assumptions and dependencies for this entry.
"""

        # Build messages with guidelines, assumptions and entries context
        guidelines = self.get_guidelines()
        prompt = self.get_prompt().format(
            guidelines=guidelines,
            assumptions_list=assumptions_list,
            entries_list=entries_list,
        )
        messages = self.build_messages(user_message, prompt)

        # Get LLM response
        response = await self.llm_client.complete_json(messages)

        # Parse JSON response into Pydantic model
        result = await self.parse_json_response(response, AssumptionsDependenciesOutput)

        return result
