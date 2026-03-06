"""PromptRegistry - Central registry for all agent prompts."""

import re
from pathlib import Path
from typing import Dict, List, Optional

from prompts.loader import PromptLoader


class PromptMetadata:
    """Metadata for a prompt."""

    def __init__(self, agent_name: str, content: str):
        """Extract metadata from prompt content.

        Args:
            agent_name: Name of the agent
            content: Prompt file content
        """
        self.agent_name = agent_name
        self.version = self._extract_version(content)
        self.last_updated = self._extract_last_updated(content)
        self.shared_components = self._extract_shared_components(content)

    def _extract_version(self, content: str) -> str:
        """Extract version from prompt header."""
        match = re.search(r'\*\*Version:\*\*\s+(.+)', content)
        return match.group(1).strip() if match else "unknown"

    def _extract_last_updated(self, content: str) -> str:
        """Extract last updated date from prompt header."""
        match = re.search(r'\*\*Last Updated:\*\*\s+(.+)', content)
        return match.group(1).strip() if match else "unknown"

    def _extract_shared_components(self, content: str) -> List[str]:
        """Extract list of @include components."""
        matches = re.findall(r'@include\s+(.+)', content)
        return [m.strip() for m in matches]


class PromptRegistry:
    """Central registry of all prompts with metadata and validation."""

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize the registry.

        Args:
            prompts_dir: Root directory containing prompts
        """
        self.loader = PromptLoader(prompts_dir)
        self._metadata_cache: Dict[str, PromptMetadata] = {}

    def get_prompt(self, agent_name: str, version: Optional[str] = None) -> str:
        """Get an agent prompt, optionally by version.

        Args:
            agent_name: Name of the agent
            version: Optional version (not yet implemented)

        Returns:
            Complete prompt string

        Raises:
            FileNotFoundError: If prompt doesn't exist
        """
        if version is not None:
            raise NotImplementedError("Versioning not yet implemented")

        return self.loader.load_agent_prompt(agent_name)

    def list_agents(self) -> List[str]:
        """List all available agent prompts.

        Returns:
            List of agent names that have prompts
        """
        agents_dir = self.loader.agents_dir

        if not agents_dir.exists():
            return []

        agent_files = agents_dir.glob("*.md")
        return [f.stem for f in agent_files]

    def get_metadata(self, agent_name: str) -> PromptMetadata:
        """Get metadata for an agent prompt.

        Args:
            agent_name: Name of the agent

        Returns:
            PromptMetadata object

        Raises:
            FileNotFoundError: If prompt doesn't exist
        """
        if agent_name in self._metadata_cache:
            return self._metadata_cache[agent_name]

        # Load prompt to extract metadata
        prompt_content = self.loader.load_agent_prompt(agent_name, use_cache=False)
        metadata = PromptMetadata(agent_name, prompt_content)

        self._metadata_cache[agent_name] = metadata
        return metadata

    def validate_all(self) -> Dict[str, bool]:
        """Validate all prompts can be loaded successfully.

        Returns:
            Dict mapping agent_name -> success (bool)
        """
        results = {}

        for agent_name in self.list_agents():
            try:
                self.loader.load_agent_prompt(agent_name, use_cache=False)
                results[agent_name] = True
            except Exception as e:
                print(f"Failed to load {agent_name}: {e}")
                results[agent_name] = False

        return results

    def clear_cache(self) -> None:
        """Clear all caches."""
        self.loader.clear_cache()
        self._metadata_cache.clear()
