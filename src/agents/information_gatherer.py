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
        messages = self.build_messages(user_message)

        response = await self.llm_client.complete_json(messages)

        # Parse JSON response into Pydantic model
        result = await self.parse_json_response(response, InformationGatheringOutput)

        # Preserve raw Wikipedia content for downstream agents
        result.raw_web_content = web_content

        return result
