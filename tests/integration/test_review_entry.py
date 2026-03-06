"""Integration tests for the review-entry feature.

Tests the full flow of loading, reviewing, and saving entries.
Requires a valid .env file with AWS credentials for LLM tests.
"""

import json
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def valid_entry_dict():
    """Create a valid entry dict that matches theoria-dataset schema."""
    return {
        "result_id": "integration_test_entry",
        "result_name": "Integration Test Entry",
        "result_equations": [
            {"id": "eq1", "equation": "F = m a", "equation_title": "Newton's Second Law"}
        ],
        "explanation": (
            "This is an integration test entry that demonstrates the basic structure "
            "of a theoria-dataset entry. The entry describes Newton's second law "
            "relating force, mass, and acceleration."
        ),
        "definitions": [
            {"symbol": "F", "definition": "Net force acting on the object"},
            {"symbol": "m", "definition": "Mass of the object"},
            {"symbol": "a", "definition": "Acceleration of the object"},
        ],
        "assumptions": ["conservation_of_momentum"],
        "depends_on": [],
        "derivation": [
            {
                "step": 1,
                "description": "Starting from Newton's second law",
                "equation": "F = m a",
            }
        ],
        "programmatic_verification": {
            "language": "Python 3.11.12",
            "library": "sympy 1.13.1",
            "code": [
                "from sympy import symbols, Eq",
                "F, m, a = symbols('F m a')",
                "eq = Eq(F, m * a)",
                "assert eq.lhs == F",
            ],
        },
        "domain": "physics.class-ph",
        "theory_status": "current",
        "references": [
            {
                "id": "R1",
                "citation": "Newton, I. (1687). Philosophiæ Naturalis Principia Mathematica.",
            }
        ],
        "contributors": [{"full_name": "Test Suite", "identifier": "test"}],
        "review_status": "draft",
    }


@pytest.fixture
def valid_entry_file(tmp_path, valid_entry_dict):
    """Create a temporary valid entry file."""
    entry_path = tmp_path / "integration_test_entry.json"
    entry_path.write_text(json.dumps(valid_entry_dict, indent=2))
    return entry_path


class TestReviewEntryEndToEnd:
    """End-to-end tests for review-entry feature."""

    @pytest.mark.asyncio
    async def test_full_review_flow_with_mock_llm(self, valid_entry_file, tmp_path):
        """Test full review flow with mocked LLM responses."""
        from src.review_entry import review_and_save
        from src.models import TheoriaEntry, ReviewResult

        output_path = tmp_path / "reviewed_entry.json"

        # Create a mock that simulates the reviewer finding and fixing an issue
        mock_config = {
            "agent_models": {"reviewer": "best"},
            "models": {"best": "mock-model"},
            "theoria_dataset_path": str(tmp_path),
            "reviewer": {"max_correction_loops": 3},
        }

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer_class:
                # Load the original entry to create a "corrected" version
                original = TheoriaEntry.model_validate(
                    json.loads(valid_entry_file.read_text())
                )
                corrected_dict = original.model_dump()
                corrected_dict["explanation"] = (
                    "This improved explanation provides more detail about Newton's "
                    "second law, which is a foundational principle of classical mechanics "
                    "relating the net force on an object to its mass and acceleration."
                )
                corrected = TheoriaEntry.model_validate(corrected_dict)

                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(
                    return_value=ReviewResult(
                        passed=True,
                        issues=["Explanation could be more detailed"],
                        corrected_entry=corrected,
                    )
                )
                mock_reviewer_class.return_value = mock_instance

                result_path = await review_and_save(
                    valid_entry_file,
                    output_path=output_path,
                )

        # Verify the output
        assert result_path.exists()
        saved = json.loads(result_path.read_text())
        assert "improved explanation" in saved["explanation"].lower()

    @pytest.mark.asyncio
    async def test_review_preserves_entry_structure(self, valid_entry_file, valid_entry_dict):
        """Test that review preserves all entry fields correctly."""
        from src.review_entry import load_entry_for_review
        from src.models import TheoriaEntry

        entry = load_entry_for_review(valid_entry_file)

        # Verify all required fields are present
        assert entry.result_id == valid_entry_dict["result_id"]
        assert entry.result_name == valid_entry_dict["result_name"]
        assert len(entry.result_equations) == len(valid_entry_dict["result_equations"])
        assert len(entry.definitions) == len(valid_entry_dict["definitions"])
        assert len(entry.derivation) == len(valid_entry_dict["derivation"])
        assert entry.domain == valid_entry_dict["domain"]

    def test_resolve_path_with_dataset_structure(self, tmp_path, valid_entry_dict):
        """Test path resolution with actual dataset directory structure."""
        from src.review_entry import resolve_entry_path

        # Create dataset structure
        entries_dir = tmp_path / "entries"
        entries_dir.mkdir()
        (entries_dir / "newtons_second_law.json").write_text(
            json.dumps(valid_entry_dict)
        )

        mock_config = {"theoria_dataset_path": str(tmp_path)}

        with patch("src.review_entry.load_config", return_value=mock_config):
            resolved = resolve_entry_path("newtons_second_law")

        assert resolved.exists()
        assert resolved.name == "newtons_second_law.json"

    @pytest.mark.asyncio
    async def test_review_with_no_issues(self, valid_entry_file, tmp_path):
        """Test review when entry passes without issues."""
        from src.review_entry import review_and_save
        from src.models import ReviewResult

        mock_config = {
            "agent_models": {"reviewer": "best"},
            "models": {"best": "mock-model"},
            "theoria_dataset_path": str(tmp_path),
            "reviewer": {"max_correction_loops": 3},
        }

        original_content = valid_entry_file.read_text()

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer_class:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(
                    return_value=ReviewResult(
                        passed=True,
                        issues=[],
                        corrected_entry=None,
                    )
                )
                mock_reviewer_class.return_value = mock_instance

                result_path = await review_and_save(valid_entry_file)

        # File should be unchanged
        assert json.loads(result_path.read_text()) == json.loads(original_content)

    @pytest.mark.asyncio
    async def test_review_fails_gracefully_on_reviewer_error(self, valid_entry_file, tmp_path):
        """Test that review handles reviewer errors gracefully."""
        from src.review_entry import review_entry

        mock_config = {
            "agent_models": {"reviewer": "best"},
            "models": {"best": "mock-model"},
            "theoria_dataset_path": str(tmp_path),
            "reviewer": {"max_correction_loops": 3},
        }

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer_class:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(side_effect=Exception("LLM error"))
                mock_reviewer_class.return_value = mock_instance

                with pytest.raises(Exception, match="LLM error"):
                    await review_entry(valid_entry_file)


class TestReviewEntryIntegrationWithRealLLM:
    """Integration tests that use real LLM calls.

    These tests require valid AWS credentials and will make actual API calls.
    Skip with: pytest -m "not integration"
    """

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_llm_review(self, valid_entry_file):
        """Test review with actual LLM calls."""
        from src.review_entry import review_entry

        # This test will make actual LLM calls
        result = await review_entry(valid_entry_file)

        # Verify we got a valid result
        assert result is not None
        assert isinstance(result.passed, bool)
        assert isinstance(result.issues, list)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_llm_review_and_save(self, valid_entry_file, tmp_path):
        """Test full review and save with actual LLM calls."""
        from src.review_entry import review_and_save

        output_path = tmp_path / "reviewed_output.json"

        result_path = await review_and_save(
            valid_entry_file,
            output_path=output_path,
        )

        # Verify output was created
        assert result_path.exists()

        # Verify it's valid JSON
        saved = json.loads(result_path.read_text())
        assert "result_id" in saved
        assert "result_name" in saved


class TestCLIReviewIntegration:
    """Integration tests for CLI review command."""

    @pytest.mark.asyncio
    async def test_cli_run_review_function(self, valid_entry_file, tmp_path):
        """Test the run_review CLI function."""
        from src.cli import run_review
        from src.models import ReviewResult
        from argparse import Namespace

        mock_config = {
            "agent_models": {"reviewer": "best"},
            "models": {"best": "mock-model"},
            "theoria_dataset_path": str(tmp_path),
            "reviewer": {"max_correction_loops": 3},
        }

        args = Namespace(
            entry=str(valid_entry_file),
            output=None,
            max_loops=None,
        )

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(
                    return_value=ReviewResult(
                        passed=True,
                        issues=[],
                        corrected_entry=None,
                    )
                )
                mock_reviewer.return_value = mock_instance

                exit_code = await run_review(args)

        assert exit_code == 0

    @pytest.mark.asyncio
    async def test_cli_run_review_with_output(self, valid_entry_file, valid_entry_dict, tmp_path):
        """Test run_review with output path specified."""
        from src.cli import run_review
        from src.models import TheoriaEntry, ReviewResult
        from argparse import Namespace

        output_path = tmp_path / "output.json"

        mock_config = {
            "agent_models": {"reviewer": "best"},
            "models": {"best": "mock-model"},
            "theoria_dataset_path": str(tmp_path),
            "reviewer": {"max_correction_loops": 3},
        }

        corrected_dict = valid_entry_dict.copy()
        corrected_dict["explanation"] = "Improved."
        corrected = TheoriaEntry.model_validate(corrected_dict)

        args = Namespace(
            entry=str(valid_entry_file),
            output=str(output_path),
            max_loops=None,
        )

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(
                    return_value=ReviewResult(
                        passed=True,
                        issues=["Fixed"],
                        corrected_entry=corrected,
                    )
                )
                mock_reviewer.return_value = mock_instance

                exit_code = await run_review(args)

        assert exit_code == 0
        assert output_path.exists()

    @pytest.mark.asyncio
    async def test_cli_run_review_returns_error_on_failure(self, tmp_path):
        """Test that run_review returns error code on file not found."""
        from src.cli import run_review
        from argparse import Namespace

        args = Namespace(
            entry="/nonexistent/file.json",
            output=None,
            max_loops=None,
        )

        exit_code = await run_review(args)

        assert exit_code == 1
