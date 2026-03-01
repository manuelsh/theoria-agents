"""Orchestrator for the theoria-agents pipeline."""

import json
from pathlib import Path
from typing import Any

from src.agents import (
    ResearcherAgent,
    DerivationAgent,
    VerifierAgent,
    AssemblerAgent,
    ReviewerAgent,
)
from src.dataset import DatasetLoader
from src.llm.config import load_config
from src.models import TheoriaEntry


class PipelineOrchestrator:
    """Coordinates the multi-agent pipeline for generating dataset entries."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        dataset_loader: DatasetLoader | None = None,
    ):
        """Initialize the orchestrator.

        Args:
            config: Configuration dict. Loads from env/yaml if not provided.
            dataset_loader: Dataset loader instance. Creates one if not provided.
        """
        self.config = config or load_config()
        self.dataset = dataset_loader or DatasetLoader()

        # Initialize agents with shared dataset loader
        self.researcher = ResearcherAgent(
            config=self.config, dataset_loader=self.dataset
        )
        self.derivation = DerivationAgent(
            config=self.config, dataset_loader=self.dataset
        )
        self.verifier = VerifierAgent(
            config=self.config, dataset_loader=self.dataset
        )
        self.assembler = AssemblerAgent(
            config=self.config, dataset_loader=self.dataset
        )

        # Get reviewer settings
        reviewer_config = self.config.get("reviewer", {})
        max_loops = reviewer_config.get("max_correction_loops", 3)
        self.reviewer = ReviewerAgent(
            config=self.config,
            dataset_loader=self.dataset,
            max_correction_loops=max_loops,
        )

    async def generate_entry(
        self,
        topic: str,
        hints: dict[str, Any] | None = None,
        contributor_name: str = "Theoria Agents",
        contributor_id: str = "https://github.com/theoria-agents",
    ) -> tuple[TheoriaEntry, dict[str, Any]]:
        """Generate a complete dataset entry for a physics topic.

        Args:
            topic: The physics topic (e.g., "Schrödinger equation").
            hints: Optional hints like suggested domain or dependencies.
            contributor_name: Name for the contributor field.
            contributor_id: Identifier for the contributor.

        Returns:
            Tuple of (final entry, metadata dict with pipeline info).
        """
        metadata: dict[str, Any] = {
            "topic": topic,
            "phases": {},
        }

        # Phase 1: Research
        print(f"[1/5] Researching topic: {topic}")
        research_output = await self.researcher.run(topic, hints)

        # Track new assumptions if any were proposed
        new_assumptions_count = len(research_output.new_assumptions)
        metadata["phases"]["research"] = {
            "result_id": research_output.result_id,
            "assumptions_count": len(research_output.assumptions),
            "new_assumptions_count": new_assumptions_count,
            "dependencies_count": len(research_output.depends_on),
        }

        print(f"      Found {len(research_output.assumptions)} existing assumptions, {len(research_output.depends_on)} dependencies")
        if new_assumptions_count > 0:
            print(f"      Proposed {new_assumptions_count} NEW assumptions:")
            for na in research_output.new_assumptions:
                print(f"        - {na.id}: {na.title}")
            metadata["new_assumptions"] = [a.model_dump() for a in research_output.new_assumptions]

        # Phase 2: Derivation
        print(f"[2/5] Generating derivation for: {research_output.result_name}")
        derivation_output = await self.derivation.run(research_output)
        metadata["phases"]["derivation"] = {
            "equations_count": len(derivation_output.result_equations),
            "steps_count": len(derivation_output.derivation),
            "definitions_count": len(derivation_output.definitions),
        }
        print(f"      Generated {len(derivation_output.derivation)} derivation steps")

        # Phase 3: Verification
        print("[3/5] Generating SymPy verification code")
        verification_output = await self.verifier.run(derivation_output)
        metadata["phases"]["verification"] = {
            "execution_success": verification_output.execution_success,
            "code_lines": len(verification_output.programmatic_verification.code),
        }

        if not verification_output.execution_success:
            print(f"      Warning: Verification code failed: {verification_output.execution_output}")
        else:
            print(f"      Verification code passed ({len(verification_output.programmatic_verification.code)} lines)")

        # Phase 4: Assembly
        print("[4/5] Assembling entry")
        entry = await self.assembler.run(
            research_output,
            derivation_output,
            verification_output,
            contributor_name,
            contributor_id,
        )
        metadata["phases"]["assembly"] = {"status": "complete"}

        # Phase 5: Review and self-correction
        print("[5/5] Reviewing and correcting entry")
        review_result = await self.reviewer.run(entry)
        metadata["phases"]["review"] = {
            "passed": review_result.passed,
            "issues_found": len(review_result.issues),
            "corrected": review_result.corrected_entry is not None,
        }

        if review_result.passed:
            print("      Entry passed review")
        else:
            print(f"      Found {len(review_result.issues)} issues")
            if review_result.corrected_entry:
                print("      Applied corrections")
                entry = review_result.corrected_entry
            else:
                print("      Could not auto-correct all issues")

        metadata["issues"] = review_result.issues

        return entry, metadata

    def save_entry(
        self,
        entry: TheoriaEntry,
        output_dir: Path | str | None = None,
    ) -> Path:
        """Save an entry to the dataset entries directory.

        Args:
            entry: The entry to save.
            output_dir: Output directory. Uses dataset entries dir if not provided.

        Returns:
            Path to the saved file.
        """
        if output_dir is None:
            output_dir = self.dataset.dataset_path / "entries"
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{entry.result_id}.json"

        with open(output_path, "w") as f:
            f.write(entry.model_dump_json(indent=2, exclude_none=True))

        return output_path

    def save_new_assumptions(
        self,
        new_assumptions: list[dict[str, Any]],
        entry_id: str,
    ) -> bool:
        """Add new assumptions to the dataset's assumptions.json.

        Args:
            new_assumptions: List of new assumption dicts to add.
            entry_id: The entry ID that uses these assumptions (for used_in field).

        Returns:
            True if assumptions were saved, False otherwise.
        """
        if not new_assumptions:
            return False

        assumptions_path = self.dataset.dataset_path / "globals" / "assumptions.json"

        # Load current assumptions
        with open(assumptions_path) as f:
            data = json.load(f)

        existing_ids = {a["id"] for a in data["assumptions"]}

        # Add new assumptions
        added = []
        for new_a in new_assumptions:
            if new_a["id"] not in existing_ids:
                # Add used_in field
                new_a["used_in"] = [entry_id]
                data["assumptions"].append(new_a)
                added.append(new_a["id"])

        if added:
            # Save updated assumptions
            with open(assumptions_path, "w") as f:
                json.dump(data, f, indent=2)
            print(f"      Added {len(added)} new assumptions to assumptions.json: {', '.join(added)}")
            return True

        return False
