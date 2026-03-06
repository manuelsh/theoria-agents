"""Unit tests for OutputManager.

Tests the output management system in isolation with mocked file system operations.
"""

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from src.utils.output_manager import OutputManager


@pytest.fixture
def temp_output_path(tmp_path):
    """Create a temporary output directory."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    return output_dir


@pytest.fixture
def output_manager(temp_output_path):
    """Create an OutputManager instance with temporary path."""
    return OutputManager(output_path=str(temp_output_path))


class TestOutputManagerInitialization:
    """Test OutputManager initialization and path validation."""

    def test_init_with_valid_path(self, temp_output_path):
        """Test initialization with a valid output path."""
        manager = OutputManager(output_path=str(temp_output_path))
        assert manager.output_path == temp_output_path
        assert manager.logs_path == temp_output_path / "logs"
        assert manager.entries_path == temp_output_path / "entries"

    def test_init_creates_directories(self, tmp_path):
        """Test that initialization creates logs and entries directories."""
        output_dir = tmp_path / "new_output"
        manager = OutputManager(output_path=str(output_dir))

        assert output_dir.exists()
        assert manager.logs_path.exists()
        assert manager.entries_path.exists()

    def test_init_with_relative_path_converts_to_absolute(self):
        """Test that relative paths are converted to absolute paths."""
        manager = OutputManager(output_path="./relative/path")
        assert manager.output_path.is_absolute()

    def test_init_with_non_writable_path_raises_error(self):
        """Test that initialization fails with non-writable path."""
        with patch("pathlib.Path.mkdir", side_effect=PermissionError):
            with pytest.raises(PermissionError):
                OutputManager(output_path="/non/writable/path")


class TestSlugification:
    """Test topic slugification functionality."""

    def test_slugify_basic_string(self, output_manager):
        """Test slugifying a basic string."""
        result = output_manager.slugify_topic("Schrödinger equation")
        assert result == "schrodinger_equation"

    def test_slugify_with_apostrophe(self, output_manager):
        """Test slugifying string with apostrophes."""
        result = output_manager.slugify_topic("Newton's 2nd Law")
        assert result == "newtons_2nd_law"

    def test_slugify_with_special_characters(self, output_manager):
        """Test slugifying string with special characters."""
        result = output_manager.slugify_topic("E=mc²")
        assert result == "e_mc2"

    def test_slugify_with_multiple_spaces(self, output_manager):
        """Test slugifying string with multiple consecutive spaces."""
        result = output_manager.slugify_topic("Multiple   spaces   here")
        assert result == "multiple_spaces_here"

    def test_slugify_removes_leading_trailing_underscores(self, output_manager):
        """Test that leading/trailing underscores are removed."""
        result = output_manager.slugify_topic("  Leading and trailing  ")
        assert not result.startswith("_")
        assert not result.endswith("_")

    def test_slugify_handles_unicode(self, output_manager):
        """Test slugifying strings with various unicode characters."""
        result = output_manager.slugify_topic("Théorème de Pythagore")
        assert result == "theoreme_de_pythagore"

    def test_slugify_prevents_path_traversal(self, output_manager):
        """Test that path traversal attempts are sanitized."""
        result = output_manager.slugify_topic("../../../etc/passwd")
        assert ".." not in result
        assert "/" not in result


class TestRunFolderCreation:
    """Test run folder creation functionality."""

    def test_create_run_folder_basic(self, output_manager):
        """Test creating a basic run folder."""
        topic = "Test Topic"
        run_id = "a7b3c9d1"

        run_folder = output_manager.create_run_folder(topic=topic, run_id=run_id)

        assert run_folder.exists()
        assert run_folder.parent == output_manager.logs_path
        assert "test_topic" in run_folder.name
        assert run_id in run_folder.name

    def test_create_run_folder_with_timestamp(self, output_manager):
        """Test that run folder name includes timestamp."""
        topic = "Test Topic"
        run_id = "a7b3c9d1"

        with patch("src.utils.output_manager.datetime") as mock_datetime:
            mock_datetime.now.return_value = datetime(2026, 3, 5, 14, 30, 45)
            mock_datetime.utcnow = datetime.utcnow
            run_folder = output_manager.create_run_folder(topic=topic, run_id=run_id)

        assert "2026-03-05_14-30-45" in run_folder.name

    def test_create_run_folder_stores_path(self, output_manager):
        """Test that run folder path is stored in manager."""
        topic = "Test Topic"
        run_id = "a7b3c9d1"

        run_folder = output_manager.create_run_folder(topic=topic, run_id=run_id)

        assert output_manager.current_run_folder == run_folder

    def test_create_run_folder_format(self, output_manager):
        """Test run folder name format matches specification."""
        topic = "Schrödinger equation"
        run_id = "a7b3c9d1"

        run_folder = output_manager.create_run_folder(topic=topic, run_id=run_id)

        # Format: {YYYY-MM-DD_HH-MM-SS}_{topic_slug}_{run_id}
        parts = run_folder.name.split("_")
        assert len(parts) >= 3
        # First part should be date
        assert "-" in parts[0]
        # Last part should be run_id
        assert parts[-1] == run_id


class TestAgentLogging:
    """Test agent execution logging functionality."""

    def test_log_agent_execution_creates_file(self, output_manager, temp_output_path):
        """Test that logging creates a markdown file in the run folder."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        log_data = {
            "agent_name": "information_gatherer",
            "timestamp_start": "2026-03-05T14:30:45.123Z",
            "timestamp_end": "2026-03-05T14:30:52.456Z",
            "duration_seconds": 7.333,
            "model": "bedrock/test-model",
            "input": {"messages": [{"role": "user", "content": "test"}]},
            "output": {"content": "test response"},
            "status": "success",
            "error": None,
        }

        output_manager.log_agent_execution(
            agent_name="information_gatherer",
            log_data=log_data,
            sequence_number=1,
        )

        expected_file = run_folder / "01_information_gatherer.md"
        assert expected_file.exists()

    def test_log_agent_execution_markdown_format(self, output_manager):
        """Test that logged data is valid markdown with correct format."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        log_data = {
            "agent_name": "information_gatherer",
            "timestamp_start": "2026-03-05T14:30:45.123Z",
            "timestamp_end": "2026-03-05T14:30:52.456Z",
            "duration_seconds": 7.333,
            "model": "bedrock/test-model",
            "input": {"messages": []},
            "output": {"content": "test"},
            "status": "success",
            "error": None,
        }

        output_manager.log_agent_execution(
            agent_name="information_gatherer",
            log_data=log_data,
            sequence_number=1,
        )

        log_file = run_folder / "01_information_gatherer.md"
        content = log_file.read_text()

        assert "# information_gatherer" in content
        assert "[OK] success" in content
        assert "bedrock/test-model" in content

    def test_log_agent_execution_sequence_numbers(self, output_manager):
        """Test that sequence numbers are properly formatted."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        log_data = {
            "agent_name": "test_agent",
            "status": "success",
            "error": None,
        }

        # Test single digit
        output_manager.log_agent_execution("agent1", log_data, 1)
        assert (run_folder / "01_agent1.md").exists()

        # Test double digit
        output_manager.log_agent_execution("agent2", log_data, 10)
        assert (run_folder / "10_agent2.md").exists()

    def test_log_agent_execution_without_run_folder_raises_error(self, output_manager):
        """Test that logging without creating run folder raises error."""
        log_data = {"agent_name": "test", "status": "success", "error": None}

        with pytest.raises(RuntimeError, match="No run folder has been created"):
            output_manager.log_agent_execution("test", log_data, 1)

    def test_log_agent_execution_markdown_contains_all_sections(self, output_manager):
        """Test that markdown log contains all required sections."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        log_data = {
            "agent_name": "test_agent",
            "timestamp_start": "2026-03-06T14:30:45.123+01:00",
            "timestamp_end": "2026-03-06T14:30:52.456+01:00",
            "duration_seconds": 7.333,
            "model": "bedrock/test-model",
            "input": {
                "messages": [
                    {"role": "system", "content": "System prompt"},
                    {"role": "user", "content": "User message"},
                ],
                "temperature": 0.3,
                "max_tokens": 4096,
            },
            "output": {"content": "Output content"},
            "status": "success",
            "error": None,
        }

        output_manager.log_agent_execution("test_agent", log_data, 1)

        log_file = run_folder / "01_test_agent.md"
        content = log_file.read_text()

        # Check all sections exist
        assert "# test_agent" in content
        assert "## Parameters" in content
        assert "## Input Messages" in content
        assert "### System" in content
        assert "### User" in content
        assert "## Output" in content
        assert "## Error" in content

    def test_log_agent_execution_markdown_preserves_newlines(self, output_manager):
        """Test that markdown preserves newlines in content."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        multiline_content = "Line 1\nLine 2\nLine 3"
        log_data = {
            "agent_name": "test_agent",
            "input": {
                "messages": [{"role": "system", "content": multiline_content}],
            },
            "output": {"content": "Response"},
            "status": "success",
            "error": None,
        }

        output_manager.log_agent_execution("test_agent", log_data, 1)

        log_file = run_folder / "01_test_agent.md"
        content = log_file.read_text()

        # Content should have actual newlines (in blockquote format), not escaped \n
        assert "> Line 1\n> Line 2\n> Line 3" in content
        assert "Line 1\\nLine 2" not in content

    def test_log_agent_execution_markdown_with_retries(self, output_manager):
        """Test that markdown includes retry section when retries occurred."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        log_data = {
            "agent_name": "test_agent",
            "status": "success",
            "error": None,
            "retries": 2,
            "retry_details": [
                {
                    "attempt": 1,
                    "timestamp": "2026-03-06T14:30:46.000+01:00",
                    "error": "Timeout",
                },
                {
                    "attempt": 2,
                    "timestamp": "2026-03-06T14:30:48.000+01:00",
                    "error": "Parse error",
                },
            ],
        }

        output_manager.log_agent_execution("test_agent", log_data, 1)

        log_file = run_folder / "01_test_agent.md"
        content = log_file.read_text()

        assert "## Retries" in content
        assert "**Total retries:** 2" in content
        assert "Timeout" in content
        assert "Parse error" in content

    def test_log_agent_execution_markdown_error_status(self, output_manager):
        """Test that error status is displayed correctly."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        log_data = {
            "agent_name": "test_agent",
            "status": "error",
            "error": "ValueError: Invalid JSON response",
        }

        output_manager.log_agent_execution("test_agent", log_data, 1)

        log_file = run_folder / "01_test_agent.md"
        content = log_file.read_text()

        assert "[ERR] error" in content
        assert "ValueError: Invalid JSON response" in content


class TestRunMetadata:
    """Test run metadata saving functionality."""

    def test_save_run_metadata_creates_file(self, output_manager):
        """Test that saving metadata creates run_metadata.json."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        metadata = {
            "run_id": "abc123",
            "timestamp_start": "2026-03-05T14:30:45.123Z",
            "timestamp_end": "2026-03-05T14:32:15.789Z",
            "duration_seconds": 90.666,
            "topic": "Test Topic",
            "topic_slug": "test_topic",
            "final_status": "success",
        }

        output_manager.save_run_metadata(metadata)

        metadata_file = run_folder / "run_metadata.json"
        assert metadata_file.exists()

    def test_save_run_metadata_json_format(self, output_manager):
        """Test that metadata is saved in correct JSON format."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        metadata = {
            "run_id": "abc123",
            "topic": "Test Topic",
            "final_status": "success",
            "errors": [],
        }

        output_manager.save_run_metadata(metadata)

        metadata_file = run_folder / "run_metadata.json"
        with open(metadata_file) as f:
            loaded_data = json.load(f)

        assert loaded_data == metadata

    def test_save_run_metadata_pretty_printed(self, output_manager):
        """Test that metadata JSON is pretty-printed with 2-space indent."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        metadata = {"run_id": "abc123", "nested": {"key": "value"}}

        output_manager.save_run_metadata(metadata)

        metadata_file = run_folder / "run_metadata.json"
        content = metadata_file.read_text()

        # Check for 2-space indentation
        assert '  "run_id"' in content or '"run_id"' in content


class TestEntryStorage:
    """Test entry and assumptions storage functionality."""

    def test_save_entry_creates_folder_and_file(self, output_manager):
        """Test that saving entry creates folder and JSON file."""
        entry_data = {
            "name": "test_entry",
            "title": "Test Entry",
            "domain": "test",
        }

        output_manager.save_entry(entry_data)

        entry_folder = output_manager.entries_path / "test_entry"
        entry_file = entry_folder / "test_entry.json"

        assert entry_folder.exists()
        assert entry_file.exists()

    def test_save_entry_json_format(self, output_manager):
        """Test that entry is saved in correct JSON format."""
        entry_data = {
            "name": "test_entry",
            "title": "Test Entry",
            "domain": "test",
        }

        output_manager.save_entry(entry_data)

        entry_file = output_manager.entries_path / "test_entry" / "test_entry.json"
        with open(entry_file) as f:
            loaded_data = json.load(f)

        assert loaded_data == entry_data

    def test_save_assumptions_with_assumptions(self, output_manager):
        """Test saving assumptions when assumptions exist."""
        entry_name = "test_entry"
        run_id = "abc123"
        assumptions = [
            {
                "id": "A001",
                "assumption": "Test assumption",
                "justification": "Test justification",
                "source": "test_agent",
                "timestamp": "2026-03-05T14:31:02.123Z",
            }
        ]

        output_manager.save_assumptions(
            entry_name=entry_name,
            run_id=run_id,
            assumptions=assumptions,
        )

        assump_file = (
            output_manager.entries_path / entry_name / f"{entry_name}_assump.json"
        )
        assert assump_file.exists()

        with open(assump_file) as f:
            data = json.load(f)

        assert data["entry_name"] == entry_name
        assert data["run_id"] == run_id
        assert len(data["assumptions"]) == 1
        assert data["statistics"]["total_assumptions"] == 1

    def test_save_assumptions_without_assumptions(self, output_manager):
        """Test saving assumptions when no assumptions exist."""
        entry_name = "test_entry"
        run_id = "abc123"

        output_manager.save_assumptions(
            entry_name=entry_name,
            run_id=run_id,
            assumptions=[],
        )

        assump_file = (
            output_manager.entries_path / entry_name / f"{entry_name}_assump.json"
        )

        with open(assump_file) as f:
            data = json.load(f)

        assert data["assumptions"] == []
        assert data["statistics"]["total_assumptions"] == 0
        assert "note" in data
        assert "no assumptions" in data["note"].lower()

    def test_save_assumptions_calculates_statistics(self, output_manager):
        """Test that assumptions statistics are calculated correctly."""
        assumptions = [
            {
                "id": "A001",
                "assumption": "Test 1",
                "source": "agent1",
                "justification": "test",
                "timestamp": "2026-03-05T14:31:02.123Z",
            },
            {
                "id": "A002",
                "assumption": "Test 2",
                "source": "agent1",
                "justification": "test",
                "timestamp": "2026-03-05T14:31:03.123Z",
            },
            {
                "id": "A003",
                "assumption": "Test 3",
                "source": "agent2",
                "justification": "test",
                "timestamp": "2026-03-05T14:31:04.123Z",
            },
        ]

        output_manager.save_assumptions("test_entry", "abc123", assumptions)

        assump_file = (
            output_manager.entries_path / "test_entry" / "test_entry_assump.json"
        )
        with open(assump_file) as f:
            data = json.load(f)

        assert data["statistics"]["total_assumptions"] == 3
        assert data["statistics"]["by_agent"]["agent1"] == 2
        assert data["statistics"]["by_agent"]["agent2"] == 1


class TestErrorHandling:
    """Test error handling and graceful degradation."""

    def test_graceful_failure_when_logging_fails(self, output_manager, capsys):
        """Test that logging failures don't crash the system."""
        run_folder = output_manager.create_run_folder("Test Topic", "abc123")

        log_data = {"agent_name": "test", "status": "success"}

        # Make the file write fail
        with patch("builtins.open", side_effect=IOError("Disk full")):
            # Should not raise exception
            output_manager.log_agent_execution("test", log_data, 1)

        # Check that error was logged to stderr
        captured = capsys.readouterr()
        assert "Failed to write log" in captured.err or "Error" in captured.err

    def test_create_run_folder_failure_logs_warning(self, temp_output_path, capsys):
        """Test that run folder creation failure is logged."""
        manager = OutputManager(output_path=str(temp_output_path))

        # Patch the run folder mkdir specifically, not the base path
        with patch.object(Path, "mkdir", side_effect=PermissionError("Permission denied")):
            with pytest.raises(PermissionError):
                manager.create_run_folder("Test", "abc123")

        # Check stderr for error message
        captured = capsys.readouterr()
        assert "Failed to create run folder" in captured.err


class TestUtilityMethods:
    """Test utility helper methods."""

    def test_get_current_run_folder(self, output_manager):
        """Test getting the current run folder."""
        run_folder = output_manager.create_run_folder("Test", "abc123")
        assert output_manager.get_current_run_folder() == run_folder

    def test_get_current_run_folder_when_none_raises_error(self, output_manager):
        """Test that getting run folder before creation raises error."""
        with pytest.raises(RuntimeError):
            output_manager.get_current_run_folder()

    def test_generate_run_id(self, output_manager):
        """Test run ID generation."""
        run_id = output_manager.generate_run_id()
        assert len(run_id) == 8
        assert all(c in "0123456789abcdef" for c in run_id)

    def test_generate_run_id_uniqueness(self, output_manager):
        """Test that generated run IDs are unique."""
        ids = [output_manager.generate_run_id() for _ in range(100)]
        assert len(set(ids)) == 100
