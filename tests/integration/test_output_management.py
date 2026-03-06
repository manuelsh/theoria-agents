"""Integration tests for output management system.

Tests that the complete pipeline properly logs and saves outputs.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.orchestrator import PipelineOrchestrator
from src.utils.output_manager import OutputManager


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {
        "agent_models": {},
        "models": {"fast": "mock-fast", "best": "mock-best"},
        "theoria_dataset_path": "/mock/dataset",
        "theoria_output_path": None,
    }


@pytest.fixture
def mock_dataset_loader():
    """Create a mock DatasetLoader."""
    loader = MagicMock()
    loader.dataset_path = Path("/mock/dataset")
    return loader


@pytest.fixture
def temp_output_manager(tmp_path):
    """Create OutputManager with temporary directory."""
    output_dir = tmp_path / "output"
    return OutputManager(output_path=str(output_dir))


@pytest.fixture
def orchestrator_with_temp_output(temp_output_manager, mock_config, mock_dataset_loader):
    """Create orchestrator with temporary output directory."""
    return PipelineOrchestrator(
        config=mock_config,
        dataset_loader=mock_dataset_loader,
        output_manager=temp_output_manager,
    )


@pytest.mark.integration
class TestOutputManagementIntegration:
    """Integration tests for output management in the pipeline."""

    def test_output_directories_created(self, temp_output_manager):
        """Test that output directories are created on initialization."""
        assert temp_output_manager.output_path.exists()
        assert temp_output_manager.logs_path.exists()
        assert temp_output_manager.entries_path.exists()

    def test_run_folder_creation_with_topic(self, temp_output_manager):
        """Test that run folder is created with proper naming."""
        topic = "Schrödinger equation"
        run_id = "abc12345"

        run_folder = temp_output_manager.create_run_folder(topic, run_id)

        assert run_folder.exists()
        assert "schrodinger_equation" in run_folder.name
        assert run_id in run_folder.name
        assert len(list(temp_output_manager.logs_path.iterdir())) == 1

    def test_agent_logs_are_written(self, temp_output_manager):
        """Test that agent logs are properly written to disk."""
        run_folder = temp_output_manager.create_run_folder("Test Topic", "test123")

        # Simulate agent execution log
        log_data = {
            "agent_name": "test_agent",
            "timestamp_start": "2026-03-05T14:30:45.123Z",
            "timestamp_end": "2026-03-05T14:30:52.456Z",
            "duration_seconds": 7.333,
            "model": "test-model",
            "input": {"messages": [{"role": "user", "content": "test"}]},
            "output": {"content": "test response"},
            "status": "success",
            "error": None,
        }

        temp_output_manager.log_agent_execution("test_agent", log_data, 1)

        # Verify log file exists and is valid JSON
        log_file = run_folder / "01_test_agent.json"
        assert log_file.exists()

        with open(log_file) as f:
            loaded = json.load(f)
            assert loaded["agent_name"] == "test_agent"
            assert loaded["status"] == "success"

    def test_run_metadata_saved(self, temp_output_manager):
        """Test that run metadata is saved correctly."""
        run_folder = temp_output_manager.create_run_folder("Test", "test123")

        metadata = {
            "run_id": "test123",
            "topic": "Test",
            "final_status": "success",
            "agents_executed": ["agent1", "agent2"],
        }

        temp_output_manager.save_run_metadata(metadata)

        metadata_file = run_folder / "run_metadata.json"
        assert metadata_file.exists()

        with open(metadata_file) as f:
            loaded = json.load(f)
            assert loaded["run_id"] == "test123"
            assert loaded["final_status"] == "success"

    def test_entry_and_assumptions_saved(self, temp_output_manager):
        """Test that entries and assumptions are saved correctly."""
        entry_data = {
            "name": "test_entry",
            "result_id": "test_id",
            "title": "Test Entry",
        }

        assumptions = [
            {
                "id": "A001",
                "assumption": "Test assumption",
                "source": "test_agent",
                "justification": "For testing",
                "timestamp": "2026-03-05T14:31:02.123Z",
            }
        ]

        # Save entry and assumptions
        temp_output_manager.save_entry(entry_data)
        temp_output_manager.save_assumptions("test_entry", "run123", assumptions)

        # Verify entry folder and files
        entry_folder = temp_output_manager.entries_path / "test_entry"
        assert entry_folder.exists()

        entry_file = entry_folder / "test_entry.json"
        assert entry_file.exists()

        assump_file = entry_folder / "test_entry_assump.json"
        assert assump_file.exists()

        # Verify assumptions content
        with open(assump_file) as f:
            assump_data = json.load(f)
            assert assump_data["entry_name"] == "test_entry"
            assert assump_data["run_id"] == "run123"
            assert len(assump_data["assumptions"]) == 1
            assert assump_data["statistics"]["total_assumptions"] == 1

    def test_empty_assumptions_handling(self, temp_output_manager):
        """Test that entries with no assumptions are handled correctly."""
        temp_output_manager.save_assumptions("empty_entry", "run123", [])

        assump_file = (
            temp_output_manager.entries_path / "empty_entry" / "empty_entry_assump.json"
        )
        assert assump_file.exists()

        with open(assump_file) as f:
            data = json.load(f)
            assert data["assumptions"] == []
            assert "note" in data
            assert "no assumptions" in data["note"].lower()

    def test_multiple_runs_create_separate_folders(self, temp_output_manager):
        """Test that multiple runs create separate log folders."""
        run1 = temp_output_manager.create_run_folder("Topic 1", "run001")
        run2 = temp_output_manager.create_run_folder("Topic 2", "run002")

        assert run1 != run2
        assert run1.exists()
        assert run2.exists()
        assert len(list(temp_output_manager.logs_path.iterdir())) == 2


@pytest.mark.integration
class TestOrchestratorOutputIntegration:
    """Test orchestrator integration with output management."""

    def test_orchestrator_initializes_with_output_manager(
        self, temp_output_manager, mock_config, mock_dataset_loader
    ):
        """Test that orchestrator accepts and uses OutputManager."""
        orchestrator = PipelineOrchestrator(
            config=mock_config,
            dataset_loader=mock_dataset_loader,
            output_manager=temp_output_manager,
        )

        assert orchestrator.output_manager == temp_output_manager

    def test_orchestrator_creates_output_manager_from_config(
        self, tmp_path, mock_config, mock_dataset_loader
    ):
        """Test that orchestrator creates OutputManager from config."""
        output_path = tmp_path / "output"
        mock_config["theoria_output_path"] = str(output_path)

        orchestrator = PipelineOrchestrator(
            config=mock_config, dataset_loader=mock_dataset_loader
        )

        assert orchestrator.output_manager is not None
        assert orchestrator.output_manager.output_path == output_path

    def test_orchestrator_handles_missing_output_path_gracefully(
        self, mock_config, mock_dataset_loader
    ):
        """Test that orchestrator continues without output manager if path not set."""
        # Remove output path from config
        mock_config.pop("theoria_output_path", None)

        orchestrator = PipelineOrchestrator(
            config=mock_config, dataset_loader=mock_dataset_loader
        )

        # Should initialize without error
        assert orchestrator.output_manager is None
