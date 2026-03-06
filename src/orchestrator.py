"""Orchestrator for the theoria-agents pipeline."""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from src.agents import (
    InformationGathererAgent,
    MetadataFillerAgent,
    AssumptionsDependenciesAgent,
    EquationsSymbolsAgent,
    DerivationAgent,
    VerifierAgent,
    AssemblerAgent,
    ReviewerAgent,
)
from src.dataset import DatasetLoader
from src.llm.config import get_output_path, load_config
from src.models import TheoriaEntry
from src.utils.agent_logger import AgentLogger
from src.utils.output_manager import OutputManager
from src.validation import EntryValidator


class PipelineOrchestrator:
    """Coordinates the multi-agent pipeline for generating dataset entries."""

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        dataset_loader: DatasetLoader | None = None,
        output_manager: OutputManager | None = None,
    ):
        """Initialize the orchestrator.

        Args:
            config: Configuration dict. Loads from env/yaml if not provided.
            dataset_loader: Dataset loader instance. Creates one if not provided.
            output_manager: OutputManager instance. Creates one if not provided.
        """
        self.config = config or load_config()
        self.dataset = dataset_loader or DatasetLoader()
        self.validator = EntryValidator(self.dataset.dataset_path)

        # Initialize output manager
        if output_manager is None:
            try:
                output_path = get_output_path(self.config)
                self.output_manager = OutputManager(output_path=str(output_path))
            except (ValueError, PermissionError) as e:
                print(
                    f"WARNING: Output logging is disabled: {e}",
                    file=sys.stderr,
                )
                print(
                    "         Set THEORIA_OUTPUT_PATH in .env to enable logging.",
                    file=sys.stderr,
                )
                self.output_manager = None
        else:
            self.output_manager = output_manager


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
        # Generate run ID and create run folder
        run_id = None
        timestamp_start = datetime.now().astimezone().isoformat()

        if self.output_manager:
            run_id = self.output_manager.generate_run_id()
            try:
                self.output_manager.create_run_folder(topic=topic, run_id=run_id)
                print(f"Logging to: {self.output_manager.get_current_run_folder()}")
            except Exception as e:
                print(
                    f"WARNING: Failed to create run folder: {e}",
                    file=sys.stderr,
                )
                print("         Pipeline will continue without logging.", file=sys.stderr)
                self.output_manager = None

        metadata: dict[str, Any] = {
            "run_id": run_id,
            "timestamp_start": timestamp_start,
            "topic": topic,
            "hints": hints or {},
            "contributor_name": contributor_name,
            "contributor_id": contributor_id,
            "phases": {},
        }

        # Initialize agents with loggers
        def create_agent(agent_class, agent_name, sequence_num, **kwargs):
            """Helper to create agent with optional logger."""
            agent_logger = None
            if self.output_manager:
                agent_logger = AgentLogger(
                    agent_name=agent_name,
                    output_manager=self.output_manager,
                    sequence_number=sequence_num,
                )
            return agent_class(
                config=self.config,
                dataset_loader=self.dataset,
                agent_logger=agent_logger,
                **kwargs,
            )

        async def run_agent_with_logging(agent, *args, **kwargs):
            """Helper to run agent with optional logging context."""
            if agent.agent_logger:
                with agent.agent_logger:
                    return await agent.run(*args, **kwargs)
            else:
                return await agent.run(*args, **kwargs)

        # Track assumptions for later saving
        all_assumptions: list[dict[str, Any]] = []

        # Phase 1: Information Gathering
        print(f"[1/8] Gathering information for topic: {topic}")
        information_gatherer = create_agent(
            InformationGathererAgent, "information_gatherer", 1
        )
        info_output = await run_agent_with_logging(information_gatherer, topic=topic)
        metadata["phases"]["information_gathering"] = {
            "has_historical_context": info_output.historical_context is not None,
            "references_count": len(info_output.suggested_references),
        }
        print(f"      Gathered context with {len(info_output.suggested_references)} suggested references")

        # Phase 2: Metadata Filling
        print(f"[2/8] Filling metadata fields")
        metadata_filler = create_agent(MetadataFillerAgent, "metadata_filler", 2)
        metadata_output = await run_agent_with_logging(
            metadata_filler, info_output=info_output, topic=topic
        )
        metadata["phases"]["metadata_filling"] = {
            "result_id": metadata_output.result_id,
            "result_name": metadata_output.result_name,
            "domain": metadata_output.domain,
        }
        print(f"      Entry ID: {metadata_output.result_id}")

        # Phase 3: Assumptions & Dependencies
        print(f"[3/8] Identifying assumptions and dependencies")
        assumptions_dependencies = create_agent(
            AssumptionsDependenciesAgent, "assumptions_dependencies", 3
        )
        assumptions_deps_output = await run_agent_with_logging(
            assumptions_dependencies,
            info_output=info_output,
            metadata_output=metadata_output,
        )
        new_assumptions_count = len(assumptions_deps_output.new_assumptions)
        metadata["phases"]["assumptions_dependencies"] = {
            "assumptions_count": len(assumptions_deps_output.assumptions),
            "new_assumptions_count": new_assumptions_count,
            "dependencies_count": len(assumptions_deps_output.depends_on),
            "missing_dependencies_count": len(assumptions_deps_output.missing_dependencies),
        }
        print(f"      Found {len(assumptions_deps_output.assumptions)} assumptions, {len(assumptions_deps_output.depends_on)} dependencies")
        if new_assumptions_count > 0:
            print(f"      Proposed {new_assumptions_count} NEW assumptions:")
            for na in assumptions_deps_output.new_assumptions:
                print(f"        - {na.id}: {na.title}")
            metadata["new_assumptions"] = [a.model_dump() for a in assumptions_deps_output.new_assumptions]

        # Check for missing dependencies
        if assumptions_deps_output.missing_dependencies:
            print(f"      Warning: {len(assumptions_deps_output.missing_dependencies)} missing dependencies detected:")
            for md in assumptions_deps_output.missing_dependencies:
                print(f"        - {md['id']}: {md.get('reason', 'No reason provided')}")
            metadata["missing_dependencies"] = assumptions_deps_output.missing_dependencies

        # Phase 4: Equations & Symbols
        print(f"[4/8] Defining equations and symbols")
        equations_symbols = create_agent(
            EquationsSymbolsAgent, "equations_symbols", 4
        )
        equations_symbols_output = await run_agent_with_logging(
            equations_symbols,
            info_output=info_output,
            metadata_output=metadata_output,
            assumptions_deps_output=assumptions_deps_output,
        )
        metadata["phases"]["equations_symbols"] = {
            "equations_count": len(equations_symbols_output.result_equations),
            "definitions_count": len(equations_symbols_output.definitions),
        }
        print(f"      Defined {len(equations_symbols_output.result_equations)} equations, {len(equations_symbols_output.definitions)} symbols")

        # Phase 5: Derivation (to be enhanced with new inputs)
        print(f"[5/8] Generating derivation")
        # TODO: Update DerivationAgent to accept new input structure
        # For now, create a combined research-like output for backward compatibility
        from src.models import ResearchOutput
        legacy_research_output = ResearchOutput(
            result_id=metadata_output.result_id,
            result_name=metadata_output.result_name,
            explanation=metadata_output.explanation,
            domain=metadata_output.domain,
            theory_status=metadata_output.theory_status,
            references=metadata_output.references,
            assumptions=assumptions_deps_output.assumptions,
            new_assumptions=assumptions_deps_output.new_assumptions,
            depends_on=assumptions_deps_output.depends_on,
            result_equations=equations_symbols_output.result_equations,
            definitions=equations_symbols_output.definitions,
            web_context=info_output.web_context,
            historical_context=info_output.historical_context,
        )
        derivation = create_agent(DerivationAgent, "derivation", 5)
        derivation_output = await run_agent_with_logging(
            derivation, legacy_research_output
        )
        metadata["phases"]["derivation"] = {
            "steps_count": len(derivation_output.derivation),
        }
        print(f"      Generated {len(derivation_output.derivation)} derivation steps")

        # Phase 6: Verification
        print("[6/8] Generating SymPy verification code")
        verifier = create_agent(VerifierAgent, "verifier", 6)
        verification_output = await run_agent_with_logging(verifier, derivation_output)
        metadata["phases"]["verification"] = {
            "execution_success": verification_output.execution_success,
            "code_lines": len(verification_output.programmatic_verification.code),
        }

        if not verification_output.execution_success:
            print(f"      Warning: Verification code failed: {verification_output.execution_output}")
        else:
            print(f"      Verification code passed ({len(verification_output.programmatic_verification.code)} lines)")

        # Phase 7: Assembly
        print("[7/8] Assembling entry")
        # TODO: Update AssemblerAgent to accept new input structure
        assembler = create_agent(AssemblerAgent, "assembler", 7)
        entry = await run_agent_with_logging(
            assembler,
            legacy_research_output,
            derivation_output,
            verification_output,
            contributor_name,
            contributor_id,
        )
        metadata["phases"]["assembly"] = {"status": "complete"}

        # Phase 8: Review and self-correction
        print("[8/8] Reviewing and correcting entry")
        reviewer_config = self.config.get("reviewer", {})
        max_loops = reviewer_config.get("max_correction_loops", 3)
        reviewer = create_agent(
            ReviewerAgent, "reviewer", 8, max_correction_loops=max_loops
        )
        review_result = await run_agent_with_logging(reviewer, entry)
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

        # Collect assumptions for saving
        for assumption in assumptions_deps_output.assumptions:
            all_assumptions.append(
                {
                    "id": assumption,
                    "assumption": assumption,  # simplified - actual value would come from lookup
                    "source": "assumptions_dependencies",
                    "justification": "Used in entry",
                    "timestamp": datetime.now().astimezone().isoformat(),
                }
            )

        # Save outputs if output manager is available
        if self.output_manager:
            timestamp_end = datetime.now().astimezone().isoformat()
            duration = (
                datetime.fromisoformat(timestamp_end)
                - datetime.fromisoformat(timestamp_start)
            ).total_seconds()

            # Save run metadata
            run_metadata = {
                "run_id": run_id,
                "timestamp_start": timestamp_start,
                "timestamp_end": timestamp_end,
                "duration_seconds": duration,
                "topic": topic,
                "topic_slug": self.output_manager.slugify_topic(topic),
                "hints": hints or {},
                "contributor_name": contributor_name,
                "contributor_id": contributor_id,
                "pipeline_version": "1.0.0",
                "config": {
                    "dataset_path": str(self.dataset.dataset_path),
                    "output_path": str(self.output_manager.output_path),
                },
                "agents_executed": [
                    "information_gatherer",
                    "metadata_filler",
                    "assumptions_dependencies",
                    "equations_symbols",
                    "derivation",
                    "verifier",
                    "assembler",
                    "reviewer",
                ],
                "final_status": "success" if review_result.passed else "completed_with_issues",
                "entry_name": entry.result_name,
                "validation_passed": len(review_result.issues) == 0,
                "errors": [str(issue) for issue in review_result.issues],
            }

            try:
                self.output_manager.save_run_metadata(run_metadata)

                # Save entry
                entry_dict = entry.model_dump(exclude_none=True)
                self.output_manager.save_entry(entry_dict)

                # Save assumptions
                self.output_manager.save_assumptions(
                    entry_name=entry.result_name,
                    run_id=run_id,
                    assumptions=all_assumptions,
                )

                print(f"\nOutputs saved to: {self.output_manager.get_current_run_folder().parent.parent}")
                print(f"  - Logs: {self.output_manager.get_current_run_folder()}")
                print(f"  - Entry: {self.output_manager.entries_path / entry.result_name}")
            except Exception as e:
                print(f"WARNING: Failed to save outputs: {e}", file=sys.stderr)

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

        # Validate against theoria-dataset's JSON schema before saving
        entry_dict = entry.model_dump(exclude_none=True)
        validation_errors = self.validator.validate(entry_dict)
        if validation_errors:
            print(f"      Warning: Entry has {len(validation_errors)} schema validation issues:")
            for err in validation_errors[:5]:  # Show first 5
                print(f"        - {err}")

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
