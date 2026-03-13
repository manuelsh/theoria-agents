"""Command-line interface for theoria-agents."""

import argparse
import asyncio
import sys
from pathlib import Path

from src.orchestrator import PipelineOrchestrator
from src.utils.validation import run_full_test, check_docker_running


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser with subcommands.

    Returns:
        Configured argument parser.
    """
    parser = argparse.ArgumentParser(
        prog="theoria-agent",
        description="Multi-agent LLM system for theoria-dataset.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # Generate subcommand
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate a new dataset entry",
    )
    _add_generate_arguments(generate_parser)

    # Review subcommand
    review_parser = subparsers.add_parser(
        "review",
        help="Review and improve an existing entry",
    )
    _add_review_arguments(review_parser)

    return parser


def _add_generate_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the generate subcommand."""
    parser.add_argument(
        "topic",
        type=str,
        help="Physics topic to generate an entry for (e.g., 'Schrödinger equation')",
    )

    parser.add_argument(
        "--domain",
        type=str,
        help="Suggested arXiv domain (e.g., 'quant-ph', 'gr-qc')",
    )

    parser.add_argument(
        "--depends-on",
        type=str,
        nargs="+",
        help="Suggested dependency entry IDs",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output directory for the generated entry (default: agents-output/entries/)",
    )

    parser.add_argument(
        "--save-to-dataset",
        action="store_true",
        help="Save directly to theoria-dataset/entries/ instead of agents-output/",
    )

    parser.add_argument(
        "--contributor-name",
        type=str,
        default="Theoria Agents",
        help="Contributor name for the entry",
    )

    parser.add_argument(
        "--contributor-id",
        type=str,
        default="https://github.com/theoria-agents",
        help="Contributor identifier (ORCID, website, etc.)",
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Run validation after generation (requires Docker)",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the entry to stdout instead of saving",
    )

    parser.add_argument(
        "--max-loops",
        type=int,
        help="Maximum review correction iterations (default: 3)",
    )


def _add_review_arguments(parser: argparse.ArgumentParser) -> None:
    """Add arguments for the review subcommand."""
    parser.add_argument(
        "entry",
        type=str,
        help="Entry file path or entry ID (resolved from THEORIA_DATASET_PATH)",
    )

    parser.add_argument(
        "--output",
        "-o",
        type=str,
        help="Output file path (overwrites input if not specified)",
    )

    parser.add_argument(
        "--max-loops",
        type=int,
        help="Maximum correction iterations",
    )

    parser.add_argument(
        "--resume",
        type=str,
        metavar="STATE_FILE",
        help="Resume review from saved state file",
    )


def main() -> int:
    """Main entry point for theoria-agent CLI."""
    parser = create_parser()
    args = parser.parse_args()

    if args.command == "generate":
        # Build hints from optional arguments
        hints = {}
        if args.domain:
            hints["domain"] = args.domain
        if args.depends_on:
            hints["depends_on"] = args.depends_on
        return asyncio.run(run_generate(args, hints))
    elif args.command == "review":
        return asyncio.run(run_review(args))

    return 1


def generate_main() -> int:
    """Legacy entry point for theoria-generate command."""
    sys.argv.insert(1, "generate")
    return main()


async def run_generate(args: argparse.Namespace, hints: dict) -> int:
    """Run the generation pipeline.

    Args:
        args: Parsed command-line arguments.
        hints: Optional hints for the researcher agent.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    print(f"\n{'='*60}")
    print(f"Theoria Agents - Generating entry for: {args.topic}")
    print(f"{'='*60}\n")

    try:
        orchestrator = PipelineOrchestrator()

        entry, metadata = await orchestrator.generate_entry(
            topic=args.topic,
            hints=hints,
            contributor_name=args.contributor_name,
            contributor_id=args.contributor_id,
            max_review_loops=args.max_loops,
        )

        print(f"\n{'='*60}")
        print("Generation Complete!")
        print(f"{'='*60}")
        print(f"Entry ID: {entry.result_id}")
        print(f"Entry Name: {entry.result_name}")
        print(f"Domain: {entry.domain}")
        print(f"Derivation Steps: {len(entry.derivation)}")
        print(f"Review Passed: {metadata['phases']['review']['passed']}")

        if metadata.get("issues"):
            print(f"\nIssues found ({len(metadata['issues'])}):")
            for issue in metadata["issues"]:
                print(f"  - {issue}")

        # Report new assumptions
        if metadata.get("new_assumptions"):
            print(f"\nNew assumptions proposed ({len(metadata['new_assumptions'])}):")
            for na in metadata["new_assumptions"]:
                print(f"  - {na['id']}: {na['title']} ({na['type']})")

        if args.dry_run:
            print("\n--- Entry JSON (dry run) ---\n")
            print(entry.model_dump_json(indent=2, exclude_none=True))
            if metadata.get("new_assumptions"):
                print("\n--- New Assumptions (dry run) ---\n")
                import json
                print(json.dumps(metadata["new_assumptions"], indent=2))
            return 0

        # Determine output directory
        if args.output:
            output_dir = Path(args.output)
        elif args.save_to_dataset:
            output_dir = None  # Uses dataset entries folder
        else:
            # Default: save to agents-output/entries/
            if orchestrator.output_manager:
                output_dir = orchestrator.output_manager.entries_path
            else:
                # Fallback if output manager not available
                output_dir = Path("agents-output/entries")

        # Save new assumptions only if saving to dataset
        if args.save_to_dataset and metadata.get("new_assumptions"):
            orchestrator.save_new_assumptions(metadata["new_assumptions"], entry.result_id)
        elif metadata.get("new_assumptions"):
            print("\n      Note: New assumptions not added to dataset (use --save-to-dataset)")

        # Save the entry
        output_path = orchestrator.save_entry(entry, output_dir)
        print(f"\nEntry saved to: {output_path}")

        # Optionally validate
        if args.validate:
            print("\nRunning validation...")

            if not check_docker_running():
                print("Warning: Docker is not running. Validation requires Docker.")
                print("Skipping validation.")
            else:
                success, output = run_full_test(entry.result_id)
                if success:
                    print("Validation passed!")
                else:
                    print(f"Validation failed:\n{output}")
                    return 1

        return 0

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        return 1


async def run_review(args: argparse.Namespace) -> int:
    """Run the review command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    from src.review_entry import resolve_entry_path, load_entry_for_review, review_entry

    try:
        # Resolve entry path
        entry_path = resolve_entry_path(args.entry)

        print(f"\n{'='*60}")
        print(f"Theoria Review - Reviewing: {entry_path}")
        print(f"{'='*60}\n")

        # Load entry to display info
        entry = load_entry_for_review(entry_path)
        print(f"Entry ID: {entry.result_id}")
        print(f"Entry Name: {entry.result_name}")

        # Load resume state if provided
        resume_state = None
        if args.resume:
            from src.agents.reviewer import ReviewerAgent
            resume_state = ReviewerAgent.load_state(args.resume)
            print(f"Resuming from iteration {resume_state['iterations_completed']}")
            print(f"Previous issues: {len(resume_state['last_issues'])}")

        print("\n[1/2] Reviewing entry...")

        # Run review
        result = await review_entry(
            entry_path,
            max_correction_loops=args.max_loops,
            resume_state=resume_state,
        )

        # Determine output path
        output_path = Path(args.output) if args.output else entry_path

        # Save if there are corrections
        if result.corrected_entry is not None:
            print("[2/2] Applying corrections...")
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(result.corrected_entry.model_dump_json(indent=2, exclude_none=True))
        else:
            print("[2/2] No corrections needed.")

        print(f"\n{'='*60}")
        print("Review Complete!")
        print(f"{'='*60}")

        if result.passed:
            status = "PASSED"
            if result.corrected_entry is not None:
                status += " (after corrections)"
        else:
            status = "FAILED"
            if result.failure_reason:
                status += f" - {result.failure_reason}"

        print(f"Status: {status}")
        print(f"Issues Found: {len(result.issues)}")

        if result.issues:
            print("\nIssues:")
            for issue in result.issues:
                print(f"  - {issue}")

        print(f"Corrections Applied: {'Yes' if result.corrected_entry else 'No'}")
        print(f"Output: {output_path}")

        # Save state for resume if review failed with issues
        if not result.passed and result.issues:
            if hasattr(result, 'reviewer_state') and result.reviewer_state:
                from src.agents.reviewer import ReviewerAgent
                from src.llm.config import get_output_path, load_config

                # Save to output/review_states/ folder
                config = load_config()
                output_base = get_output_path(config)
                review_states_dir = output_base / "review_states"
                review_states_dir.mkdir(parents=True, exist_ok=True)
                state_file = review_states_dir / f"{entry_path.stem}.review_state.json"

                reviewer = ReviewerAgent()
                reviewer.iteration_log = result.reviewer_state.get('iteration_log', [])
                reviewer.max_correction_loops = result.reviewer_state.get('max_correction_loops', 3)
                reviewer.save_state(state_file)
                print(f"\nReview state saved to: {state_file}")
                print(f"To resume: theoria-agent review {args.entry} --resume {state_file}")

        return 0 if result.passed else 1

    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Review failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
