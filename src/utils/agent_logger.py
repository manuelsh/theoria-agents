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

        # LLM interaction data
        self.input_data: dict[str, Any] | None = None
        self.output_data: dict[str, Any] | None = None

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
    ) -> None:
        """Log LLM input and output.

        Args:
            input_data: Input sent to LLM (messages, parameters, etc.).
            output_data: Output received from LLM.
            model: Model identifier used for this call.
        """
        self.input_data = input_data
        self.output_data = output_data
        self.model = model

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

    def get_log_data(self) -> dict[str, Any]:
        """Build complete log data structure.

        Returns:
            Dictionary containing all log data.
        """
        log_data = {
            "agent_name": self.agent_name,
            "timestamp_start": self.timestamp_start,
            "timestamp_end": self.timestamp_end,
            "duration_seconds": self.duration_seconds,
            "model": self.model,
            "input": self.input_data,
            "output": self.output_data,
            "status": self.status,
            "error": self.error,
        }

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
