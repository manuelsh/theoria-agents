"""Dataset loading and management utilities."""

import json
from pathlib import Path
from typing import Any

from src.llm.config import get_dataset_path


class DatasetLoader:
    """Loader for theoria-dataset resources."""

    def __init__(self, dataset_path: Path | None = None):
        """Initialize the dataset loader.

        Args:
            dataset_path: Path to theoria-dataset. Uses THEORIA_DATASET_PATH if not provided.
        """
        self.dataset_path = dataset_path or get_dataset_path()
        self._assumptions: list[dict[str, Any]] | None = None
        self._entries: dict[str, dict[str, Any]] | None = None
        self._schema: dict[str, Any] | None = None
        self._contributing_md: str | None = None
        self._ai_guidance_md: str | None = None

    @property
    def assumptions(self) -> list[dict[str, Any]]:
        """Load and cache global assumptions."""
        if self._assumptions is None:
            assumptions_path = self.dataset_path / "globals" / "assumptions.json"
            with open(assumptions_path) as f:
                data = json.load(f)
                self._assumptions = data.get("assumptions", [])
        return self._assumptions

    @property
    def assumption_ids(self) -> list[str]:
        """Get list of all assumption IDs."""
        return [a["id"] for a in self.assumptions]

    @property
    def entry_ids(self) -> list[str]:
        """Get list of all entry IDs in the dataset."""
        entries_dir = self.dataset_path / "entries"
        return [f.stem for f in entries_dir.glob("*.json")]

    @property
    def schema(self) -> dict[str, Any]:
        """Load and cache the entry schema."""
        if self._schema is None:
            schema_path = self.dataset_path / "schemas" / "entry.schema.json"
            with open(schema_path) as f:
                self._schema = json.load(f)
        return self._schema

    @property
    def contributing_guidelines(self) -> str:
        """Load and cache CONTRIBUTING.md."""
        if self._contributing_md is None:
            contributing_path = self.dataset_path / "CONTRIBUTING.md"
            if contributing_path.exists():
                self._contributing_md = contributing_path.read_text()
            else:
                self._contributing_md = ""
        return self._contributing_md

    @property
    def ai_guidance(self) -> str:
        """Load and cache AI_guidance.md."""
        if self._ai_guidance_md is None:
            guidance_path = self.dataset_path / "AI_guidance.md"
            if guidance_path.exists():
                self._ai_guidance_md = guidance_path.read_text()
            else:
                self._ai_guidance_md = ""
        return self._ai_guidance_md

    def get_full_guidelines(self) -> str:
        """Get combined guidelines from CONTRIBUTING.md and AI_guidance.md.

        Returns:
            Combined guidelines text for agent prompts.
        """
        parts = []

        if self.contributing_guidelines:
            parts.append("# CONTRIBUTING GUIDELINES\n\n" + self.contributing_guidelines)

        if self.ai_guidance:
            parts.append("# AI QUALITY GUIDANCE\n\n" + self.ai_guidance)

        return "\n\n---\n\n".join(parts)

    def load_entry(self, entry_id: str) -> dict[str, Any]:
        """Load a specific entry by ID.

        Args:
            entry_id: The entry's result_id.

        Returns:
            The entry data as a dict.

        Raises:
            FileNotFoundError: If entry doesn't exist.
        """
        entry_path = self.dataset_path / "entries" / f"{entry_id}.json"
        with open(entry_path) as f:
            return json.load(f)

    def load_example_entry(self) -> dict[str, Any]:
        """Load the Schrödinger equation entry as a gold standard example."""
        return self.load_entry("schrodinger_equation")

    def get_assumption_by_id(self, assumption_id: str) -> dict[str, Any] | None:
        """Get a specific assumption by ID.

        Args:
            assumption_id: The assumption ID.

        Returns:
            The assumption dict, or None if not found.
        """
        for assumption in self.assumptions:
            if assumption["id"] == assumption_id:
                return assumption
        return None

    def format_assumptions_for_prompt(self) -> str:
        """Format all assumptions for inclusion in a prompt.

        Returns:
            Formatted string describing all available assumptions with full details.
        """
        lines = ["# Available Global Assumptions"]
        lines.append("Use existing assumptions when possible. Only propose new ones if truly needed.\n")

        # Group by type
        by_type: dict[str, list[dict[str, Any]]] = {}
        for a in self.assumptions:
            atype = a.get("type", "unknown")
            if atype not in by_type:
                by_type[atype] = []
            by_type[atype].append(a)

        for atype in ["principle", "empirical", "approximation"]:
            if atype not in by_type:
                continue
            assumptions = by_type[atype]
            lines.append(f"\n## {atype.title()} Assumptions\n")
            for a in assumptions:
                lines.append(f"### {a['id']}")
                lines.append(f"**Title**: {a['title']}")
                lines.append(f"**Description**: {a['text']}")
                if a.get("mathematical_expressions"):
                    lines.append(f"**Math**: {', '.join(a['mathematical_expressions'])}")
                lines.append("")

        return "\n".join(lines)

    def format_entries_for_prompt(self) -> str:
        """Format existing entries for inclusion in a prompt.

        Returns:
            Formatted string listing all existing entries.
        """
        lines = ["# Existing Dataset Entries\n"]
        lines.append("These entries can be referenced in `depends_on`:\n")

        for entry_id in sorted(self.entry_ids):
            try:
                entry = self.load_entry(entry_id)
                name = entry.get("result_name", entry_id)
                domain = entry.get("domain", "")
                lines.append(f"- **{entry_id}**: {name} ({domain})")
            except Exception:
                lines.append(f"- **{entry_id}**")

        return "\n".join(lines)
