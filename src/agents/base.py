"""Base agent class for the theoria-agents pipeline."""

import json
from abc import ABC, abstractmethod
from typing import Any, TypeVar

from pydantic import BaseModel

from src.dataset import DatasetLoader
from src.llm.client import LLMClient
from src.llm.config import get_model, load_config

T = TypeVar("T", bound=BaseModel)


class BaseAgent(ABC):
    """Abstract base class for all agents in the pipeline."""

    # Override in subclasses
    agent_name: str = "base"

    def __init__(
        self,
        llm_client: LLMClient | None = None,
        config: dict[str, Any] | None = None,
        dataset_loader: DatasetLoader | None = None,
    ):
        """Initialize the agent.

        Args:
            llm_client: LLM client instance. Creates one if not provided.
            config: Configuration dict. Loads from env/yaml if not provided.
            dataset_loader: Dataset loader for accessing guidelines and data.
        """
        self.config = config or load_config()
        self.dataset = dataset_loader or DatasetLoader()

        if llm_client is None:
            model = get_model(self.agent_name, self.config)
            self.llm_client = LLMClient(default_model=model)
        else:
            self.llm_client = llm_client

    def get_guidelines(self) -> str:
        """Get the combined guidelines from theoria-dataset.

        Returns:
            Combined CONTRIBUTING.md and AI_guidance.md content.
        """
        return self.dataset.get_full_guidelines()

    def build_messages(
        self,
        user_content: str,
        system_content: str | None = None,
    ) -> list[dict[str, str]]:
        """Build the messages list for the LLM.

        Args:
            user_content: The user message content.
            system_content: Optional system message. Uses prompt_template if not provided.

        Returns:
            List of message dicts for the LLM.
        """
        system = system_content or self.prompt_template
        messages = []

        if system:
            messages.append({"role": "system", "content": system})

        messages.append({"role": "user", "content": user_content})

        return messages

    async def parse_json_response(self, response: str, model_class: type[T]) -> T:
        """Parse a JSON response into a Pydantic model.

        Args:
            response: Raw response string from LLM.
            model_class: Pydantic model class to parse into.

        Returns:
            Parsed Pydantic model instance.

        Raises:
            ValueError: If response is not valid JSON or doesn't match schema.
        """
        # Try to extract JSON from markdown code blocks if present
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            response = response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            response = response[start:end].strip()

        try:
            data = json.loads(response)
            return model_class.model_validate(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            raise ValueError(f"Failed to parse response: {e}")

    @abstractmethod
    async def run(self, **kwargs: Any) -> Any:
        """Execute the agent's task.

        Subclasses must implement this method.

        Returns:
            Agent-specific output (usually a Pydantic model).
        """
        pass
