"""Command-line interface for theoria-agents."""

import argparse
import asyncio
import sys
from pathlib import Path

from src.orchestrator import PipelineOrchestrator
from src.utils.validation import run_full_test, check_docker_running


def main() -> int:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="theoria-generate",
        description="Generate high-quality theoretical physics dataset entries using LLM agents.",
    )

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
        help="Output directory for the generated entry (default: dataset entries folder)",
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

    args = parser.parse_args()

    # Build hints from optional arguments
    hints = {}
    if args.domain:
        hints["domain"] = args.domain
    if args.depends_on:
        hints["depends_on"] = args.depends_on

    # Run the pipeline
    return asyncio.run(run_pipeline(args, hints))


async def run_pipeline(args: argparse.Namespace, hints: dict) -> int:
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

        # Save new assumptions first (so the entry references valid IDs)
        if metadata.get("new_assumptions"):
            orchestrator.save_new_assumptions(metadata["new_assumptions"], entry.result_id)

        # Save the entry
        output_dir = Path(args.output) if args.output else None
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


if __name__ == "__main__":
    sys.exit(main())
