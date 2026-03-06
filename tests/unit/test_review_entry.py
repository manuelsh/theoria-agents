"""Unit tests for the review-entry feature.

Tests the ability to load an existing entry and run only the reviewer agent
to improve it, without going through the full generation pipeline.
"""

import json
from pathlib import Path

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from pydantic import ValidationError

from src.models import TheoriaEntry, ReviewResult


@pytest.fixture
def sample_entry_dict():
    """Create a sample entry dict for testing."""
    return {
        "result_id": "test_entry",
        "result_name": "Test Entry",
        "result_equations": [{"id": "eq1", "equation": "E = m c^2"}],
        "explanation": "A test entry for review.",
        "definitions": [{"symbol": "E", "definition": "Energy"}],
        "assumptions": ["conservation_of_energy"],
        "depends_on": [],
        "derivation": [{"step": 1, "description": "Start", "equation": "E = m c^2"}],
        "programmatic_verification": {
            "language": "Python 3.11.12",
            "library": "sympy 1.13.1",
            "code": ["# verification code"],
        },
        "domain": "physics.gen-ph",
        "theory_status": "current",
        "references": [{"id": "R1", "citation": "Test citation"}],
        "contributors": [{"full_name": "Test", "identifier": "test"}],
        "review_status": "draft",
    }


@pytest.fixture
def sample_entry_file(tmp_path, sample_entry_dict):
    """Create a temporary entry file for testing."""
    entry_path = tmp_path / "test_entry.json"
    entry_path.write_text(json.dumps(sample_entry_dict, indent=2))
    return entry_path


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {
        "agent_models": {"reviewer": "best"},
        "models": {"fast": "mock-fast-model", "best": "mock-best-model"},
        "theoria_dataset_path": "/mock/dataset/path",
        "aws_region": "us-east-1",
        "reviewer": {"max_correction_loops": 3},
    }


class TestResolveEntryPath:
    """Tests for resolve_entry_path function."""

    def test_resolves_explicit_file_path(self, sample_entry_file):
        """Test resolving an explicit file path."""
        from src.review_entry import resolve_entry_path

        resolved = resolve_entry_path(str(sample_entry_file))

        assert resolved == sample_entry_file

    def test_resolves_path_object(self, sample_entry_file):
        """Test resolving a Path object passed as string."""
        from src.review_entry import resolve_entry_path

        resolved = resolve_entry_path(str(sample_entry_file))

        assert resolved == sample_entry_file

    def test_resolves_entry_id_from_dataset(self, tmp_path, sample_entry_dict):
        """Test resolving entry ID from THEORIA_DATASET_PATH."""
        from src.review_entry import resolve_entry_path

        # Create mock dataset structure
        entries_dir = tmp_path / "entries"
        entries_dir.mkdir()
        entry_path = entries_dir / "test_entry.json"
        entry_path.write_text(json.dumps(sample_entry_dict, indent=2))

        mock_config = {"theoria_dataset_path": str(tmp_path)}

        with patch("src.review_entry.load_config", return_value=mock_config):
            resolved = resolve_entry_path("test_entry")

        assert resolved == entry_path

    def test_raises_on_nonexistent_file_path(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        from src.review_entry import resolve_entry_path

        with pytest.raises(FileNotFoundError):
            resolve_entry_path("/nonexistent/path/entry.json")

    def test_raises_on_nonexistent_entry_id(self, tmp_path):
        """Test that FileNotFoundError is raised for non-existent entry ID."""
        from src.review_entry import resolve_entry_path

        entries_dir = tmp_path / "entries"
        entries_dir.mkdir()

        mock_config = {"theoria_dataset_path": str(tmp_path)}

        with patch("src.review_entry.load_config", return_value=mock_config):
            with pytest.raises(FileNotFoundError):
                resolve_entry_path("nonexistent_entry")

    def test_raises_when_no_dataset_path_for_entry_id(self):
        """Test that ValueError is raised when entry ID given but no dataset path."""
        from src.review_entry import resolve_entry_path

        mock_config = {"theoria_dataset_path": None}

        with patch("src.review_entry.load_config", return_value=mock_config):
            with pytest.raises(ValueError, match="THEORIA_DATASET_PATH"):
                resolve_entry_path("some_entry_id")

    def test_detects_file_path_with_extension(self, sample_entry_file):
        """Test that .json extension is detected as file path."""
        from src.review_entry import resolve_entry_path

        resolved = resolve_entry_path(str(sample_entry_file))
        assert resolved == sample_entry_file

    def test_detects_file_path_with_separator(self, tmp_path, sample_entry_dict):
        """Test that path separator is detected as file path."""
        from src.review_entry import resolve_entry_path

        entry_path = tmp_path / "subdir" / "entry.json"
        entry_path.parent.mkdir(parents=True)
        entry_path.write_text(json.dumps(sample_entry_dict))

        resolved = resolve_entry_path(str(entry_path))
        assert resolved == entry_path


class TestLoadEntryForReview:
    """Tests for load_entry_for_review function."""

    def test_loads_valid_entry(self, sample_entry_file):
        """Test loading a valid entry file."""
        from src.review_entry import load_entry_for_review

        entry = load_entry_for_review(sample_entry_file)

        assert isinstance(entry, TheoriaEntry)
        assert entry.result_id == "test_entry"
        assert entry.result_name == "Test Entry"

    def test_loads_entry_from_string_path(self, sample_entry_file):
        """Test loading entry from string path."""
        from src.review_entry import load_entry_for_review

        entry = load_entry_for_review(str(sample_entry_file))

        assert isinstance(entry, TheoriaEntry)
        assert entry.result_id == "test_entry"

    def test_raises_on_nonexistent_file(self):
        """Test that FileNotFoundError is raised for non-existent file."""
        from src.review_entry import load_entry_for_review

        with pytest.raises(FileNotFoundError):
            load_entry_for_review("/nonexistent/path/entry.json")

    def test_raises_on_invalid_json(self, tmp_path):
        """Test that JSONDecodeError is raised for invalid JSON."""
        from src.review_entry import load_entry_for_review

        invalid_file = tmp_path / "invalid.json"
        invalid_file.write_text("not valid json {")

        with pytest.raises(json.JSONDecodeError):
            load_entry_for_review(invalid_file)

    def test_raises_on_invalid_entry_schema(self, tmp_path):
        """Test that ValidationError is raised for invalid entry schema."""
        from src.review_entry import load_entry_for_review

        invalid_entry = tmp_path / "invalid_entry.json"
        invalid_entry.write_text(json.dumps({"result_id": "test"}))  # Missing required fields

        with pytest.raises(ValidationError):
            load_entry_for_review(invalid_entry)


class TestReviewEntry:
    """Tests for review_entry function."""

    @pytest.mark.asyncio
    async def test_returns_review_result(self, sample_entry_file, mock_config):
        """Test that review_entry returns a ReviewResult."""
        from src.review_entry import review_entry

        mock_review_result = ReviewResult(passed=True, issues=[], corrected_entry=None)

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_review_result)
                mock_reviewer.return_value = mock_instance

                result = await review_entry(sample_entry_file)

        assert isinstance(result, ReviewResult)
        assert result.passed is True

    @pytest.mark.asyncio
    async def test_returns_corrected_entry_when_issues_found(
        self, sample_entry_file, sample_entry_dict, mock_config
    ):
        """Test that review_entry returns corrected entry when issues found."""
        from src.review_entry import review_entry

        corrected_dict = sample_entry_dict.copy()
        corrected_dict["explanation"] = "Improved explanation."
        corrected_entry = TheoriaEntry.model_validate(corrected_dict)

        mock_review_result = ReviewResult(
            passed=True,
            issues=["Explanation too short"],
            corrected_entry=corrected_entry,
        )

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_review_result)
                mock_reviewer.return_value = mock_instance

                result = await review_entry(sample_entry_file)

        assert result.corrected_entry is not None
        assert result.corrected_entry.explanation == "Improved explanation."

    @pytest.mark.asyncio
    async def test_uses_config_max_loops_by_default(self, sample_entry_file, mock_config):
        """Test that review_entry uses max_correction_loops from config."""
        from src.review_entry import review_entry

        mock_review_result = ReviewResult(passed=True, issues=[], corrected_entry=None)

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_review_result)
                mock_reviewer.return_value = mock_instance

                await review_entry(sample_entry_file)

                # Verify max_correction_loops was passed from config
                mock_reviewer.assert_called_once()
                call_kwargs = mock_reviewer.call_args[1]
                assert call_kwargs.get("max_correction_loops") == 3

    @pytest.mark.asyncio
    async def test_uses_custom_max_loops(self, sample_entry_file, mock_config):
        """Test that review_entry accepts custom max_correction_loops."""
        from src.review_entry import review_entry

        mock_review_result = ReviewResult(passed=True, issues=[], corrected_entry=None)

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_review_result)
                mock_reviewer.return_value = mock_instance

                await review_entry(sample_entry_file, max_correction_loops=5)

                call_kwargs = mock_reviewer.call_args[1]
                assert call_kwargs.get("max_correction_loops") == 5

    @pytest.mark.asyncio
    async def test_reports_all_issues(self, sample_entry_file, mock_config):
        """Test that review_entry reports all issues found."""
        from src.review_entry import review_entry

        mock_review_result = ReviewResult(
            passed=False,
            issues=["Issue 1", "Issue 2", "Issue 3"],
            corrected_entry=None,
        )

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_review_result)
                mock_reviewer.return_value = mock_instance

                result = await review_entry(sample_entry_file)

        assert len(result.issues) == 3
        assert "Issue 1" in result.issues


class TestReviewAndSave:
    """Tests for review_and_save function."""

    @pytest.mark.asyncio
    async def test_saves_to_output_path(
        self, sample_entry_file, sample_entry_dict, tmp_path, mock_config
    ):
        """Test that review_and_save saves to specified output path."""
        from src.review_entry import review_and_save

        corrected_dict = sample_entry_dict.copy()
        corrected_dict["explanation"] = "Corrected explanation."
        corrected_entry = TheoriaEntry.model_validate(corrected_dict)

        mock_review_result = ReviewResult(
            passed=True,
            issues=["Fixed issue"],
            corrected_entry=corrected_entry,
        )

        output_path = tmp_path / "output" / "test_entry.json"

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_review_result)
                mock_reviewer.return_value = mock_instance

                result_path = await review_and_save(
                    sample_entry_file,
                    output_path=output_path,
                )

        assert result_path.exists()
        saved_entry = json.loads(result_path.read_text())
        assert saved_entry["explanation"] == "Corrected explanation."

    @pytest.mark.asyncio
    async def test_overwrites_input_when_no_output_path(
        self, sample_entry_file, sample_entry_dict, mock_config
    ):
        """Test that review_and_save overwrites input file when no output specified."""
        from src.review_entry import review_and_save

        corrected_dict = sample_entry_dict.copy()
        corrected_dict["explanation"] = "Overwritten explanation."
        corrected_entry = TheoriaEntry.model_validate(corrected_dict)

        mock_review_result = ReviewResult(
            passed=True,
            issues=[],
            corrected_entry=corrected_entry,
        )

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_review_result)
                mock_reviewer.return_value = mock_instance

                result_path = await review_and_save(sample_entry_file)

        assert result_path == sample_entry_file
        saved_entry = json.loads(sample_entry_file.read_text())
        assert saved_entry["explanation"] == "Overwritten explanation."

    @pytest.mark.asyncio
    async def test_keeps_original_when_no_corrections(
        self, sample_entry_file, sample_entry_dict, mock_config
    ):
        """Test that original file is unchanged when no corrections are made."""
        from src.review_entry import review_and_save

        mock_review_result = ReviewResult(passed=True, issues=[], corrected_entry=None)

        original_content = sample_entry_file.read_text()

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_review_result)
                mock_reviewer.return_value = mock_instance

                result_path = await review_and_save(sample_entry_file)

        assert result_path == sample_entry_file
        # Content should be unchanged
        current_content = json.loads(sample_entry_file.read_text())
        original_parsed = json.loads(original_content)
        assert current_content == original_parsed

    @pytest.mark.asyncio
    async def test_creates_output_directory_if_needed(
        self, sample_entry_file, sample_entry_dict, tmp_path, mock_config
    ):
        """Test that output directory is created if it doesn't exist."""
        from src.review_entry import review_and_save

        corrected_dict = sample_entry_dict.copy()
        corrected_dict["explanation"] = "New explanation."
        corrected_entry = TheoriaEntry.model_validate(corrected_dict)

        mock_review_result = ReviewResult(
            passed=True,
            issues=[],
            corrected_entry=corrected_entry,
        )

        output_path = tmp_path / "new" / "nested" / "dir" / "entry.json"

        with patch("src.review_entry.load_config", return_value=mock_config):
            with patch("src.review_entry.ReviewerAgent") as mock_reviewer:
                mock_instance = MagicMock()
                mock_instance.run = AsyncMock(return_value=mock_review_result)
                mock_reviewer.return_value = mock_instance

                result_path = await review_and_save(
                    sample_entry_file,
                    output_path=output_path,
                )

        assert result_path.exists()
        assert result_path.parent.exists()


class TestCLIReviewSubcommand:
    """Tests for CLI review subcommand argument parsing."""

    def test_parses_entry_argument(self):
        """Test that CLI parses entry positional argument."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["review", "path/to/entry.json"])

        assert args.command == "review"
        assert args.entry == "path/to/entry.json"

    def test_parses_output_option(self):
        """Test that CLI parses --output option."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["review", "entry.json", "--output", "improved.json"])

        assert args.output == "improved.json"

    def test_parses_output_short_option(self):
        """Test that CLI parses -o short option."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["review", "entry.json", "-o", "improved.json"])

        assert args.output == "improved.json"

    def test_parses_max_loops_option(self):
        """Test that CLI parses --max-loops option."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["review", "entry.json", "--max-loops", "5"])

        assert args.max_loops == 5

    def test_review_defaults(self):
        """Test CLI default values for review subcommand."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["review", "entry.json"])

        assert args.entry == "entry.json"
        assert args.output is None
        assert args.max_loops is None


class TestCLIGenerateSubcommand:
    """Tests for CLI generate subcommand (existing functionality)."""

    def test_parses_topic_argument(self):
        """Test that CLI parses topic positional argument."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["generate", "Schrödinger equation"])

        assert args.command == "generate"
        assert args.topic == "Schrödinger equation"

    def test_parses_domain_option(self):
        """Test that CLI parses --domain option."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["generate", "topic", "--domain", "quant-ph"])

        assert args.domain == "quant-ph"

    def test_parses_depends_on_option(self):
        """Test that CLI parses --depends-on option."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["generate", "topic", "--depends-on", "entry1", "entry2"])

        assert args.depends_on == ["entry1", "entry2"]

    def test_parses_dry_run_flag(self):
        """Test that CLI parses --dry-run flag for generate."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["generate", "topic", "--dry-run"])

        assert args.dry_run is True

    def test_parses_validate_flag(self):
        """Test that CLI parses --validate flag."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["generate", "topic", "--validate"])

        assert args.validate is True

    def test_generate_defaults(self):
        """Test CLI default values for generate subcommand."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["generate", "topic"])

        assert args.topic == "topic"
        assert args.domain is None
        assert args.depends_on is None
        assert args.output is None
        assert args.dry_run is False
        assert args.validate is False


class TestCLIStructure:
    """Tests for overall CLI structure."""

    def test_requires_subcommand(self):
        """Test that CLI requires a subcommand."""
        from src.cli import create_parser

        parser = create_parser()

        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_has_generate_subcommand(self):
        """Test that generate subcommand exists."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["generate", "topic"])

        assert args.command == "generate"

    def test_has_review_subcommand(self):
        """Test that review subcommand exists."""
        from src.cli import create_parser

        parser = create_parser()
        args = parser.parse_args(["review", "entry.json"])

        assert args.command == "review"
