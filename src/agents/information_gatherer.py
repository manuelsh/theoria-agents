"""InformationGatherer Agent - Gathers context and information for physics entries.

This agent is responsible for:
- Performing web searches (Wikipedia) for physics topics
- Extracting relevant context about the topic
- Gathering historical development information
- Finding authoritative references
- Compiling a curated summary
"""

from src.agents.base import BaseAgent
from src.models import InformationGatheringOutput
from src.utils.web_search import fetch_wikipedia


class InformationGathererAgent(BaseAgent):
    """Agent that gathers information from web sources."""

    agent_name = "information_gatherer"

    prompt_template = """You are an expert physics researcher gathering information for a theoretical physics dataset.

Your task is to gather comprehensive, graduate-level information about a physics topic from the provided web content.

Guidelines:
- Extract factual, graduate-level physics content
- Focus on the core concepts, principles, and applications
- Identify historical context if available (who developed it, when, key insights)
- Suggest 1-3 authoritative academic references if mentioned in the content
- Keep the web_context concise but informative (aim for 2-4 paragraphs)
- Prioritize accuracy and clarity

Output Format:
Return a JSON object with the following structure:
{
  "web_context": "Curated summary of the physics concept (2-4 paragraphs)",
  "historical_context": {
    "importance": "Why this theory/concept is important",
    "development_period": "When it was developed (e.g., '1905', '17th century')",
    "key_insights": ["Key insight 1", "Key insight 2"]
  } or null if not applicable,
  "suggested_references": [
    {
      "id": "R1",
      "citation": "Author(s). (Year). Title. Journal/Publisher."
    }
  ] (1-3 references, or empty array)
}

IMPORTANT:
- web_context is required and must be substantive
- historical_context is optional - only include if the topic has significant historical development
- suggested_references should be in APA format
- Do not include derivations or mathematical details - just conceptual overview
"""

    async def run(self, topic: str) -> InformationGatheringOutput:
        """Gather information about a physics topic.

        Args:
            topic: The physics topic to research

        Returns:
            InformationGatheringOutput with gathered information

        Raises:
            Exception: If information gathering fails
        """
        # Fetch Wikipedia content
        web_content = await fetch_wikipedia(topic)

        # Build user message
        user_message = f"""Topic: {topic}

Web Content:
{web_content}

Please extract and organize the key information about this physics topic according to the guidelines.
"""

        # Get LLM response
        messages = self.build_messages(user_message, self.prompt_template)

        response = await self.llm_client.complete_json(messages)

        # Parse JSON response into Pydantic model
        result = await self.parse_json_response(response, InformationGatheringOutput)

        return result
