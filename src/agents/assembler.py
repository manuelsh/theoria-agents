"""Assembler agent for combining outputs into a complete entry."""

from src.agents.base import BaseAgent
from src.models import (
    AssumptionsDependenciesOutput,
    Contributor,
    DerivationOutput,
    InformationGatheringOutput,
    MetadataOutput,
    TheoriaEntry,
    VerifierOutput,
)


class AssemblerAgent(BaseAgent):
    """Agent that assembles a complete theoria-dataset entry."""

    agent_name = "assembler"

    async def run(
        self,
        info_output: InformationGatheringOutput,
        metadata_output: MetadataOutput,
        assumptions_deps_output: AssumptionsDependenciesOutput,
        derivation: DerivationOutput,
        verification: VerifierOutput,
        contributor_name: str = "Theoria Agents",
        contributor_id: str = "https://github.com/manuelsh/theoria-agents",
    ) -> TheoriaEntry:
        """Assemble all outputs into a complete entry.

        Args:
            info_output: Output from InformationGathererAgent
            metadata_output: Output from MetadataFillerAgent
            assumptions_deps_output: Output from AssumptionsDependenciesAgent
            derivation: Output from DerivationAgent
            verification: Output from VerifierAgent
            contributor_name: Name of the contributor.
            contributor_id: Contributor identifier (ORCID, website, etc.).

        Returns:
            Complete TheoriaEntry ready for validation.
        """
        entry = TheoriaEntry(
            result_id=metadata_output.result_id,
            result_name=metadata_output.result_name,
            result_equations=derivation.result_equations,
            explanation=derivation.explanation,
            definitions=derivation.definitions,
            assumptions=assumptions_deps_output.assumptions,
            depends_on=assumptions_deps_output.depends_on,
            derivation=derivation.derivation,
            programmatic_verification=verification.programmatic_verification,
            domain=metadata_output.domain,
            theory_status=metadata_output.theory_status,
            historical_context=info_output.historical_context,
            references=metadata_output.references,
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
