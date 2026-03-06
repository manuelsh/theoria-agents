"""Base agent class for the theoria-agents pipeline."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
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
        agent_logger: Any | None = None,  # AgentLogger type
    ):
        """Initialize the agent.

        Args:
            llm_client: LLM client instance. Creates one if not provided.
            config: Configuration dict. Loads from env/yaml if not provided.
            dataset_loader: Dataset loader for accessing guidelines and data.
            agent_logger: Optional AgentLogger for capturing LLM interactions.
        """
        self.config = config or load_config()
        self.dataset = dataset_loader or DatasetLoader()
        self.agent_logger = agent_logger

        if llm_client is None:
            model = get_model(self.agent_name, self.config)
            # Set up log callback if logger is provided
            log_callback = None
            if agent_logger:
                log_callback = self._create_log_callback()
            self.llm_client = LLMClient(default_model=model, log_callback=log_callback)
        else:
            self.llm_client = llm_client

        # Initialize prompt registry (lazy loading)
        self._prompt_registry = None

    def _create_log_callback(self) -> Any:
        """Create a callback function for LLM logging.

        Returns:
            Callback function that logs LLM calls to the agent logger.
        """

        def log_callback(
            input_data: dict[str, Any],
            output_data: dict[str, Any],
            model: str,
        ) -> None:
            if self.agent_logger:
                self.agent_logger.log_llm_call(input_data, output_data, model)

        return log_callback

    def get_guidelines(self) -> str:
        """Get the combined guidelines from theoria-dataset.

        Returns:
            Combined CONTRIBUTING.md and AI_guidance.md content.
        """
        return self.dataset.get_full_guidelines()

    def get_prompt(self) -> str:
        """Get this agent's prompt from the registry.

        Returns:
            Complete prompt string

        Raises:
            FileNotFoundError: If prompt file doesn't exist and no prompt_template fallback
        """
        # Try to load from prompt registry
        try:
            if self._prompt_registry is None:
                # Lazy load the registry
                from prompts.registry import PromptRegistry
                prompts_dir = Path(__file__).parent.parent.parent / "prompts"
                self._prompt_registry = PromptRegistry(prompts_dir)

            return self._prompt_registry.get_prompt(self.agent_name)
        except (FileNotFoundError, ImportError):
            # Fallback to prompt_template if it exists
            if hasattr(self, "prompt_template"):
                return self.prompt_template
            raise

    def build_messages(
        self,
        user_content: str,
        system_content: str | None = None,
    ) -> list[dict[str, str]]:
        """Build the messages list for the LLM.

        Args:
            user_content: The user message content.
            system_content: Optional system message. Uses get_prompt() if not provided.

        Returns:
            List of message dicts for the LLM.
        """
        system = system_content or self.get_prompt()
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
