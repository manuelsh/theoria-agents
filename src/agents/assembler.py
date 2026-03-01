"""Assembler agent for combining outputs into a complete entry."""

from src.agents.base import BaseAgent
from src.models import (
    DerivationOutput,
    ResearchOutput,
    TheoriaEntry,
    VerifierOutput,
    Contributor,
)


class AssemblerAgent(BaseAgent):
    """Agent that assembles a complete theoria-dataset entry."""

    agent_name = "assembler"

    async def run(
        self,
        research: ResearchOutput,
        derivation: DerivationOutput,
        verification: VerifierOutput,
        contributor_name: str = "Theoria Agents",
        contributor_id: str = "https://github.com/theoria-agents",
    ) -> TheoriaEntry:
        """Assemble all outputs into a complete entry.

        Args:
            research: Output from Researcher agent.
            derivation: Output from Derivation agent.
            verification: Output from Verifier agent.
            contributor_name: Name of the contributor.
            contributor_id: Contributor identifier (ORCID, website, etc.).

        Returns:
            Complete TheoriaEntry ready for validation.
        """
        # Assemble the entry directly (no LLM needed for this step)
        entry = TheoriaEntry(
            result_id=research.result_id,
            result_name=research.result_name,
            result_equations=derivation.result_equations,
            explanation=derivation.explanation,
            definitions=derivation.definitions,
            assumptions=research.assumptions,
            depends_on=research.depends_on,
            derivation=derivation.derivation,
            programmatic_verification=verification.programmatic_verification,
            domain=research.domain,
            theory_status=research.theory_status,
            historical_context=research.historical_context,
            references=research.references,
            contributors=[
                Contributor(full_name=contributor_name, identifier=contributor_id)
            ],
            review_status="draft",
        )

        return entry

    def to_json(self, entry: TheoriaEntry, indent: int = 2) -> str:
        """Convert entry to JSON string.

        Args:
            entry: The entry to serialize.
            indent: JSON indentation level.

        Returns:
            JSON string representation.
        """
        return entry.model_dump_json(indent=indent, exclude_none=True)

    def save_entry(self, entry: TheoriaEntry, output_path: str) -> None:
        """Save entry to a JSON file.

        Args:
            entry: The entry to save.
            output_path: Path to save the JSON file.
        """
        with open(output_path, "w") as f:
            f.write(self.to_json(entry))
