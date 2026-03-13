"""Agent execution logger for capturing LLM interactions.

Provides context manager for timing and logging agent executions.
"""

import sys
from datetime import datetime
from typing import Any


class AgentLogger:
    """Captures and logs agent execution details including LLM calls."""

    def __init__(
        self,
        agent_name: str,
        output_manager: Any,  # OutputManager type
        sequence_number: int,
        model: str | None = None,
    ):
        """Initialize AgentLogger.

        Args:
            agent_name: Name of the agent being logged.
            output_manager: OutputManager instance for saving logs.
            sequence_number: Agent sequence number in pipeline (1-indexed).
            model: Optional model identifier.
        """
        self.agent_name = agent_name
        self.output_manager = output_manager
        self.sequence_number = sequence_number
        self.model = model

        # Execution timing
        self.timestamp_start: str | None = None
        self.timestamp_end: str | None = None
        self.duration_seconds: float | None = None

        # LLM interaction data (supports multiple calls)
        self.llm_calls: list[dict[str, Any]] = []

        # Iteration metadata (for reviewer agent)
        self.iteration_metadata: list[dict[str, Any]] = []

        # Status tracking
        self.status: str = "success"
        self.error: str | None = None

        # Retry tracking
        self.retries: int = 0
        self.retry_details: list[dict[str, Any]] = []

    def __enter__(self) -> "AgentLogger":
        """Enter context manager - record start time."""
        self.timestamp_start = datetime.now().astimezone().isoformat()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        """Exit context manager - record end time and save log.

        Args:
            exc_type: Exception type if exception occurred.
            exc_val: Exception value if exception occurred.
            exc_tb: Exception traceback if exception occurred.

        Returns:
            False to propagate exceptions.
        """
        self.timestamp_end = datetime.now().astimezone().isoformat()

        # Calculate duration
        if self.timestamp_start and self.timestamp_end:
            start_dt = datetime.fromisoformat(self.timestamp_start)
            end_dt = datetime.fromisoformat(self.timestamp_end)
            self.duration_seconds = (end_dt - start_dt).total_seconds()

        # Handle exception if present
        if exc_type is not None:
            self.log_error(exc_val)

        # Save log
        try:
            self._save_log()
        except Exception as e:
            print(
                f"ERROR: Failed to save log for {self.agent_name}: {e}",
                file=sys.stderr,
            )
            print(
                "WARNING: Pipeline will continue, but logs are not being stored.",
                file=sys.stderr,
            )

        # Don't suppress exceptions
        return False

    def log_llm_call(
        self,
        input_data: dict[str, Any],
        output_data: dict[str, Any],
        model: str,
        iteration: int | None = None,
    ) -> None:
        """Log LLM input and output.

        Args:
            input_data: Input sent to LLM (messages, parameters, etc.).
            output_data: Output received from LLM.
            model: Model identifier used for this call.
            iteration: Optional iteration number (for multi-iteration agents).
        """
        self.llm_calls.append({
            "iteration": iteration,
            "model": model,
            "input": input_data,
            "output": output_data,
        })
        self.model = model  # Keep last model for summary

    def log_iteration(
        self,
        iteration: int,
        issues_found: int,
        issues: list[str],
        corrections_applied: bool,
    ) -> None:
        """Log iteration metadata for multi-iteration agents like reviewer.

        Args:
            iteration: Iteration number (1-indexed).
            issues_found: Number of issues found in this iteration.
            issues: List of issue descriptions.
            corrections_applied: Whether corrections were applied.
        """
        self.iteration_metadata.append({
            "iteration": iteration,
            "issues_found": issues_found,
            "issues": issues,
            "corrections_applied": corrections_applied,
        })

    def log_error(self, error: Exception) -> None:
        """Log an error that occurred during execution.

        Args:
            error: Exception that occurred.
        """
        self.status = "error"
        self.error = f"{type(error).__name__}: {str(error)}"

    def log_retry(self, attempt: int, error: str) -> None:
        """Log a retry attempt.

        Args:
            attempt: Retry attempt number (1-indexed).
            error: Error message that triggered retry.
        """
        self.retries += 1
        self.retry_details.append(
            {
                "attempt": attempt,
                "timestamp": datetime.now().astimezone().isoformat(),
                "error": error,
            }
        )

    def get_total_cost(self) -> float:
        """Calculate total cost from all LLM calls.

        Returns:
            Total cost in USD.
        """
        total = 0.0
        for call in self.llm_calls:
            output = call.get("output", {})
            if output:
                total += output.get("cost", 0.0) or 0.0
        return total

    def get_total_tokens(self) -> dict[str, int]:
        """Calculate total tokens from all LLM calls.

        Returns:
            Dict with prompt_tokens, completion_tokens, total_tokens.
        """
        totals = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
        for call in self.llm_calls:
            output = call.get("output", {})
            usage = output.get("usage") if output else None
            if usage:
                totals["prompt_tokens"] += usage.get("prompt_tokens", 0) or 0
                totals["completion_tokens"] += usage.get("completion_tokens", 0) or 0
                totals["total_tokens"] += usage.get("total_tokens", 0) or 0
        return totals

    def get_log_data(self) -> dict[str, Any]:
        """Build complete log data structure.

        Returns:
            Dictionary containing all log data.
        """
        # For backward compatibility, extract first call's input/output if available
        input_data = self.llm_calls[0]["input"] if self.llm_calls else None
        output_data = self.llm_calls[0]["output"] if self.llm_calls else None

        log_data = {
            "agent_name": self.agent_name,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "duration_seconds": self.duration_seconds,
            "model": self.model,
            "input": input_data,
            "output": output_data,
            "status": self.status,
            "error": self.error,
            "total_cost": self.get_total_cost(),
            "total_tokens": self.get_total_tokens(),
        }

        # Include all LLM calls if more than one
        if len(self.llm_calls) > 1:
            log_data["llm_calls"] = self.llm_calls

        # Include iteration metadata if present
        if self.iteration_metadata:
            log_data["iterations"] = self.iteration_metadata

        # Only include retry info if retries occurred
        if self.retries > 0:
            log_data["retries"] = self.retries
            log_data["retry_details"] = self.retry_details

        return log_data

    def _save_log(self) -> None:
        """Save log to output manager."""
        log_data = self.get_log_data()
        self.output_manager.log_agent_execution(
            agent_name=self.agent_name,
            log_data=log_data,
            sequence_number=self.sequence_number,
        )
