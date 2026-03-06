"""MetadataFiller Agent - Fills metadata fields for physics entries.

This agent is responsible for:
- Generating appropriate result_id (lowercase, underscores, descriptive)
- Creating concise result_name (max 100 chars)
- Writing explanation (2-5 sentences, max 800 chars, conceptual focus)
- Selecting appropriate domain (arXiv category)
- Determining theory_status
- Formatting references (1-3 APA citations)
- Adding contributor information
- Setting review_status to "draft"
- Preserving historical_context if relevant
"""

from src.agents.base import BaseAgent
from src.models import InformationGatheringOutput, MetadataOutput


class MetadataFillerAgent(BaseAgent):
    """Agent that fills metadata fields for physics entries."""

    agent_name = "metadata_filler"

    async def run(self, info_output: InformationGatheringOutput, topic: str) -> MetadataOutput:
        """Fill metadata fields for a physics entry.

        Args:
            info_output: Output from InformationGathererAgent
            topic: The physics topic being documented

        Returns:
            MetadataOutput with all metadata fields filled

        Raises:
            Exception: If metadata filling fails
        """
        # Build user message with context from InformationGatheringOutput
        user_message = f"""Topic: {topic}

Web Context:
{info_output.web_context}

Historical Context:
{info_output.historical_context.model_dump() if info_output.historical_context else "None"}

Suggested References:
{[ref.model_dump() for ref in info_output.suggested_references]}

Please fill all metadata fields according to the guidelines.
"""

        # Build prompt with guidelines from theoria-dataset
        guidelines = self.get_guidelines()
        prompt = self.get_prompt().format(guidelines=guidelines)

        # Get LLM response
        messages = self.build_messages(user_message, prompt)

        response = await self.llm_client.complete_json(messages)

        # Parse JSON response into Pydantic model
        result = await self.parse_json_response(response, MetadataOutput)

        return result
