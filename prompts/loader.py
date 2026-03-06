"""PromptLoader - Loads and composes prompts from markdown files."""

import re
from pathlib import Path
from typing import Dict, Set


class PromptLoader:
    """Loads and composes prompts from markdown files with @include support."""

    def __init__(self, prompts_dir: Path | None = None):
        """Initialize the prompt loader.

        Args:
            prompts_dir: Root directory containing prompts. Defaults to prompts/ in project root.
        """
        if prompts_dir is None:
            # Default to prompts/ directory relative to this file
            prompts_dir = Path(__file__).parent

        self.prompts_dir = Path(prompts_dir)
        self.base_dir = self.prompts_dir / "base"
        self.agents_dir = self.prompts_dir / "agents"
        self._cache: Dict[str, str] = {}

    def load_agent_prompt(self, agent_name: str, use_cache: bool = True) -> str:
        """Load and compose an agent's full prompt.

        Args:
            agent_name: Name of the agent (e.g., "information_gatherer")
            use_cache: Whether to use cached result if available

        Returns:
            Complete prompt string with @include directives resolved

        Raises:
            FileNotFoundError: If agent prompt file doesn't exist
            RecursionError: If circular @include dependencies detected
        """
        cache_key = f"agent:{agent_name}"

        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        prompt_file = self.agents_dir / f"{agent_name}.md"

        if not prompt_file.exists():
            raise FileNotFoundError(
                f"Prompt file not found for agent '{agent_name}' at {prompt_file}"
            )

        # Load and process with include resolution
        prompt = self._load_and_process(prompt_file, visited=set())

        self._cache[cache_key] = prompt
        return prompt

    def load_base_component(self, component_name: str, use_cache: bool = True) -> str:
        """Load a shared base component.

        Args:
            component_name: Name of the component (e.g., "asciimath_rules")
            use_cache: Whether to use cached result if available

        Returns:
            Component content

        Raises:
            FileNotFoundError: If component file doesn't exist
        """
        cache_key = f"base:{component_name}"

        if use_cache and cache_key in self._cache:
            return self._cache[cache_key]

        # Support both with and without .md extension
        if not component_name.endswith(".md"):
            component_name = f"{component_name}.md"

        component_file = self.base_dir / component_name

        if not component_file.exists():
            raise FileNotFoundError(
                f"Base component not found: '{component_name}' at {component_file}"
            )

        content = component_file.read_text(encoding="utf-8")

        self._cache[cache_key] = content
        return content

    def clear_cache(self) -> None:
        """Clear the prompt cache."""
        self._cache.clear()

    def _load_and_process(self, file_path: Path, visited: Set[Path]) -> str:
        """Load a file and process @include directives recursively.

        Args:
            file_path: Path to the file to load
            visited: Set of already visited files (for circular dependency detection)

        Returns:
            Processed file content with includes resolved

        Raises:
            RecursionError: If circular dependency detected
        """
        if file_path in visited:
            raise RecursionError(
                f"Circular @include dependency detected: {file_path} already visited"
            )

        visited = visited | {file_path}

        content = file_path.read_text(encoding="utf-8")

        # Process @include directives
        # Format: @include base/component_name.md
        include_pattern = r'^@include\s+(.+)$'

        def resolve_include(match: re.Match) -> str:
            include_path = match.group(1).strip()

            # Resolve relative to base_dir for base/ includes
            if include_path.startswith("base/"):
                target_file = self.prompts_dir / include_path
            else:
                # Relative to current file
                target_file = file_path.parent / include_path

            if not target_file.exists():
                raise FileNotFoundError(
                    f"@include target not found: {include_path} (resolved to {target_file})"
                )

            # Recursively load and process the included file
            return self._load_and_process(target_file, visited)

        # Replace all @include directives
        processed = re.sub(include_pattern, resolve_include, content, flags=re.MULTILINE)

        return processed
