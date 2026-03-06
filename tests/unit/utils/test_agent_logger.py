"""Unit tests for AgentLogger.

Tests the agent logging wrapper that captures LLM inputs/outputs.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from src.utils.agent_logger import AgentLogger


@pytest.fixture
def mock_output_manager():
    """Create a mock OutputManager."""
    manager = MagicMock()
    manager.current_run_folder = MagicMock()
    return manager


@pytest.fixture
def agent_logger(mock_output_manager):
    """Create an AgentLogger instance."""
    return AgentLogger(
        agent_name="test_agent",
        output_manager=mock_output_manager,
        sequence_number=1,
    )


class TestAgentLoggerInitialization:
    """Test AgentLogger initialization."""

    def test_init_with_required_params(self, mock_output_manager):
        """Test initialization with required parameters."""
        logger = AgentLogger(
            agent_name="test_agent",
            output_manager=mock_output_manager,
            sequence_number=1,
        )

        assert logger.agent_name == "test_agent"
        assert logger.output_manager == mock_output_manager
        assert logger.sequence_number == 1

    def test_init_sets_model_to_none(self, mock_output_manager):
        """Test that model is initially None."""
        logger = AgentLogger("test", mock_output_manager, 1)
        assert logger.model is None

    def test_init_with_model(self, mock_output_manager):
        """Test initialization with model parameter."""
        logger = AgentLogger(
            agent_name="test",
            output_manager=mock_output_manager,
            sequence_number=1,
            model="bedrock/test-model",
        )
        assert logger.model == "bedrock/test-model"


class TestContextManager:
    """Test AgentLogger as context manager."""

    def test_context_manager_enter_records_start_time(self, agent_logger):
        """Test that entering context records start timestamp."""
        with patch("src.utils.agent_logger.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2026, 3, 5, 14, 30, 45, 123000)

            with agent_logger as logger:
                pass

            # Check that start time was recorded
            assert logger.timestamp_start is not None

    def test_context_manager_exit_records_end_time(self, agent_logger):
        """Test that exiting context records end timestamp."""
        with patch("src.utils.agent_logger.datetime") as mock_datetime:
            start_time = datetime(2026, 3, 5, 14, 30, 45, 123000)
            end_time = datetime(2026, 3, 5, 14, 30, 52, 456000)
            mock_datetime.utcnow.side_effect = [start_time, end_time]

            with agent_logger as logger:
                pass

            assert logger.timestamp_end is not None
            assert logger.duration_seconds is not None

    def test_context_manager_calculates_duration(self, agent_logger):
        """Test that duration is calculated correctly."""
        with patch("src.utils.agent_logger.datetime") as mock_datetime:
            start_time = datetime(2026, 3, 5, 14, 30, 45, 123000)
            end_time = datetime(2026, 3, 5, 14, 30, 52, 456000)

            # Mock the now().astimezone() chain
            mock_start = MagicMock()
            mock_start.isoformat.return_value = start_time.isoformat()
            mock_end = MagicMock()
            mock_end.isoformat.return_value = end_time.isoformat()

            mock_datetime.now.return_value.astimezone.side_effect = [mock_start, mock_end]
            # Mock fromisoformat for duration calculation
            mock_datetime.fromisoformat.side_effect = [start_time, end_time]

            with agent_logger:
                pass

            # Duration should be ~7.333 seconds
            assert 7.0 < agent_logger.duration_seconds < 8.0

    def test_context_manager_calls_save_log(self, agent_logger, mock_output_manager):
        """Test that exiting context saves the log."""
        with patch("src.utils.agent_logger.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2026, 3, 5, 14, 30, 45)

            with agent_logger:
                agent_logger.log_llm_call(
                    input_data={"messages": []},
                    output_data={"content": "test"},
                    model="test-model",
                )

        # Verify that output_manager.log_agent_execution was called
        mock_output_manager.log_agent_execution.assert_called_once()

    def test_context_manager_handles_exceptions(self, agent_logger):
        """Test that context manager handles exceptions gracefully."""
        try:
            with agent_logger:
                raise ValueError("Test error")
        except ValueError:
            pass

        # Logger should still have recorded error status
        assert agent_logger.status == "error"
        assert agent_logger.error is not None


class TestLLMCallLogging:
    """Test logging of LLM calls."""

    def test_log_llm_call_stores_input(self, agent_logger):
        """Test that LLM input is stored."""
        input_data = {
            "messages": [{"role": "user", "content": "test"}],
            "temperature": 0.7,
            "max_tokens": 4096,
        }

        agent_logger.log_llm_call(
            input_data=input_data,
            output_data={"content": "response"},
            model="test-model",
        )

        assert agent_logger.input_data == input_data

    def test_log_llm_call_stores_output(self, agent_logger):
        """Test that LLM output is stored."""
        output_data = {
            "content": "test response",
            "parsed": {"key": "value"},
        }

        agent_logger.log_llm_call(
            input_data={"messages": []},
            output_data=output_data,
            model="test-model",
        )

        assert agent_logger.output_data == output_data

    def test_log_llm_call_stores_model(self, agent_logger):
        """Test that model identifier is stored."""
        agent_logger.log_llm_call(
            input_data={"messages": []},
            output_data={"content": "test"},
            model="bedrock/arn:aws:bedrock:us-east-1:...",
        )

        assert agent_logger.model == "bedrock/arn:aws:bedrock:us-east-1:..."

    def test_log_llm_call_updates_existing_model(self, mock_output_manager):
        """Test that model can be updated by subsequent calls."""
        logger = AgentLogger("test", mock_output_manager, 1, model="initial-model")

        logger.log_llm_call(
            input_data={"messages": []},
            output_data={"content": "test"},
            model="updated-model",
        )

        assert logger.model == "updated-model"


class TestErrorLogging:
    """Test error and exception logging."""

    def test_log_error_sets_status(self, agent_logger):
        """Test that logging error sets status to error."""
        agent_logger.log_error(Exception("Test error"))
        assert agent_logger.status == "error"

    def test_log_error_stores_message(self, agent_logger):
        """Test that error message is stored."""
        error = ValueError("Test validation error")
        agent_logger.log_error(error)
        assert "Test validation error" in agent_logger.error

    def test_log_error_includes_exception_type(self, agent_logger):
        """Test that error includes exception type."""
        error = ValueError("Test error")
        agent_logger.log_error(error)
        assert "ValueError" in agent_logger.error


class TestRetryLogging:
    """Test retry attempt logging."""

    def test_log_retry_increments_counter(self, agent_logger):
        """Test that logging retry increments counter."""
        agent_logger.log_retry(attempt=1, error="Test error")
        agent_logger.log_retry(attempt=2, error="Test error")

        assert agent_logger.retries == 2

    def test_log_retry_stores_details(self, agent_logger):
        """Test that retry details are stored."""
        with patch("src.utils.agent_logger.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2026, 3, 5, 14, 30, 45)

            agent_logger.log_retry(attempt=1, error="Connection timeout")

        assert len(agent_logger.retry_details) == 1
        assert agent_logger.retry_details[0]["attempt"] == 1
        assert "Connection timeout" in agent_logger.retry_details[0]["error"]

    def test_log_retry_does_not_change_status(self, agent_logger):
        """Test that logging retry doesn't set error status."""
        agent_logger.log_retry(attempt=1, error="Retry error")
        # Status should remain success unless explicitly errored
        assert agent_logger.status == "success"


class TestLogDataGeneration:
    """Test generation of final log data structure."""

    def test_get_log_data_structure(self, agent_logger):
        """Test that log data has correct structure."""
        with patch("src.utils.agent_logger.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2026, 3, 5, 14, 30, 45)

            agent_logger.timestamp_start = "2026-03-05T14:30:45.123Z"
            agent_logger.timestamp_end = "2026-03-05T14:30:52.456Z"
            agent_logger.duration_seconds = 7.333

            agent_logger.log_llm_call(
                input_data={"messages": []},
                output_data={"content": "test"},
                model="test-model",
            )

            log_data = agent_logger.get_log_data()

        assert "agent_name" in log_data
        assert "timestamp_start" in log_data
        assert "timestamp_end" in log_data
        assert "duration_seconds" in log_data
        assert "model" in log_data
        assert "input" in log_data
        assert "output" in log_data
        assert "status" in log_data
        assert "error" in log_data

    def test_get_log_data_includes_retries_when_present(self, agent_logger):
        """Test that retry info is included when retries occurred."""
        agent_logger.log_retry(attempt=1, error="Test error")

        log_data = agent_logger.get_log_data()

        assert "retries" in log_data
        assert "retry_details" in log_data
        assert log_data["retries"] == 1

    def test_get_log_data_excludes_retries_when_absent(self, agent_logger):
        """Test that retry info is excluded when no retries."""
        with patch("src.utils.agent_logger.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2026, 3, 5, 14, 30, 45)

            agent_logger.timestamp_start = "2026-03-05T14:30:45.123Z"
            agent_logger.timestamp_end = "2026-03-05T14:30:52.456Z"
            agent_logger.duration_seconds = 7.333

            log_data = agent_logger.get_log_data()

        assert "retries" not in log_data
        assert "retry_details" not in log_data


class TestGracefulDegradation:
    """Test graceful degradation when logging fails."""

    def test_save_log_handles_output_manager_failure(
        self, agent_logger, mock_output_manager, capsys
    ):
        """Test that save_log handles OutputManager failures gracefully."""
        mock_output_manager.log_agent_execution.side_effect = IOError("Disk full")

        with patch("src.utils.agent_logger.datetime") as mock_datetime:
            mock_datetime.utcnow.return_value = datetime(2026, 3, 5, 14, 30, 45)

            # Should not raise exception
            with agent_logger:
                pass

        # Error should be logged to stderr
        captured = capsys.readouterr()
        assert "Failed to save log" in captured.err or "Disk full" in captured.err

    def test_context_manager_exit_handles_exceptions_during_save(
        self, agent_logger, mock_output_manager
    ):
        """Test that context exit handles exceptions during save."""
        mock_output_manager.log_agent_execution.side_effect = Exception("Save failed")

        # Should not raise exception
        with agent_logger:
            agent_logger.log_llm_call(
                input_data={"messages": []},
                output_data={"content": "test"},
                model="test-model",
            )
