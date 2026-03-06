"""Output management for theoria-agents pipeline.

Handles structured logging and artifact storage for all agent runs.
"""

import json
import re
import sys
import unicodedata
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any


class OutputManager:
    """Manages output directories and logging for pipeline runs."""

    def __init__(self, output_path: str):
        """Initialize OutputManager with base output path.

        Args:
            output_path: Base path for all output (logs and entries).

        Raises:
            PermissionError: If output_path is not writable.
        """
        self.output_path = Path(output_path).resolve()
        self.logs_path = self.output_path / "logs"
        self.entries_path = self.output_path / "entries"
        self.current_run_folder: Path | None = None

        # Create directory structure
        try:
            self.output_path.mkdir(parents=True, exist_ok=True)
            self.logs_path.mkdir(exist_ok=True)
            self.entries_path.mkdir(exist_ok=True)
        except PermissionError as e:
            raise PermissionError(
                f"Cannot create output directories at {output_path}: {e}"
            ) from e

    def slugify_topic(self, topic: str) -> str:
        """Convert topic to URL-safe slug.

        Args:
            topic: Topic string to slugify.

        Returns:
            URL-safe slug string.

        Examples:
            >>> slugify_topic("Schrödinger equation")
            "schrodinger_equation"
            >>> slugify_topic("Newton's 2nd Law")
            "newtons_2nd_law"
            >>> slugify_topic("E=mc²")
            "e_mc2"
        """
        # Remove apostrophes before other processing
        topic = topic.replace("'", "")
        topic = topic.replace("'", "")  # Also handle curly apostrophe

        # Normalize unicode characters (e.g., ö -> o)
        topic = unicodedata.normalize("NFKD", topic)
        topic = topic.encode("ascii", "ignore").decode("ascii")

        # Convert to lowercase
        topic = topic.lower()

        # Replace spaces and special characters with underscores
        topic = re.sub(r"[^\w\s-]", "_", topic)
        topic = re.sub(r"[\s-]+", "_", topic)

        # Remove consecutive underscores
        topic = re.sub(r"_+", "_", topic)

        # Strip leading/trailing underscores
        topic = topic.strip("_")

        # Prevent path traversal
        topic = topic.replace("..", "")
        topic = topic.replace("/", "_")
        topic = topic.replace("\\", "_")

        return topic

    def generate_run_id(self) -> str:
        """Generate a unique 8-character run ID.

        Returns:
            8-character hexadecimal string.
        """
        return uuid.uuid4().hex[:8]

    def create_run_folder(self, topic: str, run_id: str) -> Path:
        """Create timestamped run folder for logging.

        Args:
            topic: Topic being processed.
            run_id: Unique run identifier.

        Returns:
            Path to created run folder.

        Raises:
            PermissionError: If folder cannot be created.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        topic_slug = self.slugify_topic(topic)
        folder_name = f"{timestamp}_{topic_slug}_{run_id}"

        run_folder = self.logs_path / folder_name

        try:
            run_folder.mkdir(parents=True, exist_ok=True)
            self.current_run_folder = run_folder
            return run_folder
        except PermissionError as e:
            print(
                f"ERROR: Failed to create run folder at {run_folder}: {e}",
                file=sys.stderr,
            )
            raise

    def get_current_run_folder(self) -> Path:
        """Get the current run folder path.

        Returns:
            Path to current run folder.

        Raises:
            RuntimeError: If no run folder has been created yet.
        """
        if self.current_run_folder is None:
            raise RuntimeError(
                "No run folder has been created. Call create_run_folder() first."
            )
        return self.current_run_folder

    def log_agent_execution(
        self,
        agent_name: str,
        log_data: dict[str, Any],
        sequence_number: int,
    ) -> None:
        """Write agent execution log to Markdown file.

        Args:
            agent_name: Name of the agent.
            log_data: Log data dictionary containing all execution details.
            sequence_number: Agent sequence number (1-indexed).

        Raises:
            RuntimeError: If no run folder has been created.
        """
        if self.current_run_folder is None:
            raise RuntimeError(
                "No run folder has been created. Call create_run_folder() first."
            )

        filename = f"{sequence_number:02d}_{agent_name}.md"
        log_file = self.current_run_folder / filename

        markdown_content = self._format_log_as_markdown(log_data)

        try:
            with open(log_file, "w", encoding="utf-8") as f:
                f.write(markdown_content)
        except IOError as e:
            print(
                f"ERROR: Failed to write log for {agent_name}: {e}",
                file=sys.stderr,
            )
            print(
                "WARNING: Pipeline will continue, but logs are not being stored.",
                file=sys.stderr,
            )

    def _blockquote(self, text: str) -> str:
        """Prefix each line with '> ' for blockquote formatting."""
        return "\n".join(f"> {line}" for line in text.split("\n"))

    def _format_log_as_markdown(self, log_data: dict[str, Any]) -> str:
        """Convert log data dictionary to Markdown format.

        Args:
            log_data: Log data dictionary containing all execution details.

        Returns:
            Formatted Markdown string.
        """
        lines: list[str] = []

        # Header
        agent_name = log_data.get("agent_name", "unknown")
        lines.append(f"# {agent_name}")
        lines.append("")

        # Status table
        status = log_data.get("status", "unknown")
        status_indicator = "[OK]" if status == "success" else "[ERR]"
        timestamp_start = log_data.get("timestamp_start", "N/A")
        timestamp_end = log_data.get("timestamp_end", "N/A")
        duration = log_data.get("duration_seconds")
        duration_str = f"{duration:.2f}s" if duration is not None else "N/A"
        model = log_data.get("model", "N/A")

        lines.append("| Field | Value |")
        lines.append("|-------|-------|")
        lines.append(f"| Status | {status_indicator} {status} |")
        lines.append(f"| Started | {timestamp_start} |")
        lines.append(f"| Ended | {timestamp_end} |")
        lines.append(f"| Duration | {duration_str} |")
        lines.append(f"| Model | {model} |")
        lines.append("")

        # Parameters section
        input_data = log_data.get("input") or {}
        temperature = input_data.get("temperature")
        max_tokens = input_data.get("max_tokens")

        if temperature is not None or max_tokens is not None:
            lines.append("## Parameters")
            lines.append("")
            lines.append("| Parameter | Value |")
            lines.append("|-----------|-------|")
            if temperature is not None:
                lines.append(f"| temperature | {temperature} |")
            if max_tokens is not None:
                lines.append(f"| max_tokens | {max_tokens} |")
            lines.append("")

        # Input Messages section
        messages = input_data.get("messages", [])
        if messages:
            lines.append("## Input Messages")
            lines.append("")

            for msg in messages:
                role = msg.get("role", "unknown")
                content = msg.get("content", "")
                lines.append(f"### {role.capitalize()}")
                lines.append("")
                lines.append(self._blockquote(content))
                lines.append("")

        # Output section
        lines.append("## Output")
        lines.append("")
        output_data = log_data.get("output") or {}
        output_content = output_data.get("content", "")
        if output_content:
            lines.append(self._blockquote(output_content))
        else:
            lines.append("None")
        lines.append("")

        # Error section
        lines.append("## Error")
        lines.append("")
        error = log_data.get("error")
        if error:
            lines.append(self._blockquote(error))
        else:
            lines.append("None")
        lines.append("")

        # Retries section (only if retries occurred)
        retries = log_data.get("retries", 0)
        if retries > 0:
            lines.append("## Retries")
            lines.append("")
            lines.append(f"**Total retries:** {retries}")
            lines.append("")

            retry_details = log_data.get("retry_details", [])
            if retry_details:
                lines.append("| Attempt | Timestamp | Error |")
                lines.append("|---------|-----------|-------|")
                for detail in retry_details:
                    attempt = detail.get("attempt", "?")
                    timestamp = detail.get("timestamp", "N/A")
                    retry_error = detail.get("error", "Unknown")
                    lines.append(f"| {attempt} | {timestamp} | {retry_error} |")
                lines.append("")

        return "\n".join(lines)

    def save_run_metadata(self, metadata: dict[str, Any]) -> None:
        """Save run metadata to run_metadata.json.

        Args:
            metadata: Run metadata dictionary.

        Raises:
            RuntimeError: If no run folder has been created.
        """
        if self.current_run_folder is None:
            raise RuntimeError(
                "No run folder has been created. Call create_run_folder() first."
            )

        metadata_file = self.current_run_folder / "run_metadata.json"

        try:
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
        except IOError as e:
            print(
                f"ERROR: Failed to write run metadata: {e}",
                file=sys.stderr,
            )
            print(
                "WARNING: Pipeline will continue, but metadata is not being stored.",
                file=sys.stderr,
            )

    def save_entry(self, entry_data: dict[str, Any]) -> None:
        """Save final entry to entries folder.

        Args:
            entry_data: Complete entry data dictionary.
                Must contain 'name' field.

        Raises:
            ValueError: If entry_data doesn't contain 'name' field.
        """
        if "name" not in entry_data:
            raise ValueError("entry_data must contain 'name' field")

        entry_name = entry_data["name"]
        entry_folder = self.entries_path / entry_name
        entry_file = entry_folder / f"{entry_name}.json"

        try:
            entry_folder.mkdir(parents=True, exist_ok=True)
            with open(entry_file, "w") as f:
                json.dump(entry_data, f, indent=2)
        except IOError as e:
            print(
                f"ERROR: Failed to save entry {entry_name}: {e}",
                file=sys.stderr,
            )
            print(
                "WARNING: Entry was not saved to disk.",
                file=sys.stderr,
            )

    def save_assumptions(
        self,
        entry_name: str,
        run_id: str,
        assumptions: list[dict[str, Any]],
    ) -> None:
        """Save assumptions to {entry_name}_assump.json.

        Args:
            entry_name: Name of the entry.
            run_id: Run identifier.
            assumptions: List of assumption dictionaries.
        """
        entry_folder = self.entries_path / entry_name
        assump_file = entry_folder / f"{entry_name}_assump.json"

        # Calculate statistics
        statistics = {
            "total_assumptions": len(assumptions),
            "by_agent": {},
        }

        for assumption in assumptions:
            source = assumption.get("source", "unknown")
            statistics["by_agent"][source] = (
                statistics["by_agent"].get(source, 0) + 1
            )

        # Build assumptions data
        assump_data = {
            "entry_name": entry_name,
            "timestamp": datetime.now().astimezone().isoformat(),
            "run_id": run_id,
            "assumptions": assumptions,
            "statistics": statistics,
        }

        # Add note if no assumptions
        if len(assumptions) == 0:
            assump_data["note"] = "No assumptions were required for this entry."

        try:
            entry_folder.mkdir(parents=True, exist_ok=True)
            with open(assump_file, "w") as f:
                json.dump(assump_data, f, indent=2)
        except IOError as e:
            print(
                f"ERROR: Failed to save assumptions for {entry_name}: {e}",
                file=sys.stderr,
            )
            print(
                "WARNING: Assumptions were not saved to disk.",
                file=sys.stderr,
            )
