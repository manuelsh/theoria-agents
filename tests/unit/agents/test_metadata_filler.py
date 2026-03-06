"""Unit tests for MetadataFillerAgent.

Tests the metadata filling agent in isolation with mocked dependencies.
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.metadata_filler import MetadataFillerAgent
from src.models import InformationGatheringOutput, MetadataOutput, HistoricalContext, Reference
from tests.fixtures.expected_outputs import NEWTONS_SECOND_LAW_INFO


@pytest.fixture
def mock_config():
    """Create a mock configuration."""
    return {
        "agent_models": {
            "information_gatherer": "fast",
            "metadata_filler": "fast",
            "assumptions_dependencies": "best",
            "equations_symbols": "best",
        },
        "models": {"fast": "mock-fast-model", "best": "mock-best-model"},
        "theoria_dataset_path": "/mock/dataset/path",
        "aws_region": "us-east-1",
    }


@pytest.fixture
def mock_dataset_loader():
    """Create a mock DatasetLoader."""
    with patch("src.agents.base.DatasetLoader") as mock_loader:
        mock_instance = MagicMock()
        mock_loader.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def mock_llm_client():
    """Create a mock LLM client."""
    with patch("src.agents.base.LLMClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.complete_json = AsyncMock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def agent_with_mocks(mock_config, mock_dataset_loader, mock_llm_client):
    """Create a MetadataFillerAgent with mocked dependencies."""
    with patch("src.agents.base.load_config", return_value=mock_config):
        with patch("src.agents.base.get_model", return_value="mock-fast-model"):
            agent = MetadataFillerAgent()
            return agent


class TestMetadataFillerInitialization:
    """Test MetadataFillerAgent initialization."""

    def test_metadata_filler_initialization(self, agent_with_mocks):
        """Verify agent inherits from BaseAgent and initializes correctly."""
        agent = agent_with_mocks

        # Check agent_name is set correctly
        assert agent.agent_name == "metadata_filler"

        # Check it has required attributes from BaseAgent
        assert hasattr(agent, "llm_client")
        assert hasattr(agent, "config")
        assert hasattr(agent, "dataset")

    def test_model_assignment_is_fast(self, mock_config):
        """Verify model assignment is 'fast'."""
        with patch("src.agents.base.load_config", return_value=mock_config):
            with patch("src.agents.base.get_model") as mock_get_model:
                with patch("src.agents.base.DatasetLoader"):
                    mock_get_model.return_value = "fast-model-arn"
                    agent = MetadataFillerAgent()

                    # Verify get_model was called with correct agent name
                    mock_get_model.assert_called_once()
                    call_args = mock_get_model.call_args[0]
                    assert call_args[0] == "metadata_filler"


class TestFillMetadata:
    """Test filling metadata fields."""

    @pytest.mark.asyncio
    async def test_fill_basic_metadata(self, agent_with_mocks):
        """Test filling basic metadata fields."""
        agent = agent_with_mocks

        info_output = NEWTONS_SECOND_LAW_INFO

        mock_llm_response = {
            "result_id": "newtons_second_law",
            "result_name": "Newton's Second Law",
            "explanation": (
                "Newton's second law states that the force acting on an object equals the product of "
                "its mass and acceleration (`F = m a`). This fundamental principle describes "
                "the relationship between force, mass, and motion."
            ),
            "domain": "physics.class-ph",
            "theory_status": "current",
            "references": [
                {"id": "R1", "citation": "Newton, I. (1687). Philosophiæ Naturalis Principia Mathematica. London: Royal Society."}
            ],
            "contributor_name": "Test Contributor",
            "contributor_id": "test_id",
            "review_status": "draft",
            "historical_context": {
                "importance": "Foundation of classical mechanics",
                "development_period": "1687",
                "key_insights": ["Quantitative description of force and motion"],
            },
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, topic="Newton's Second Law")

        # Verify output structure
        assert isinstance(result, MetadataOutput)
        assert result.result_id == "newtons_second_law"
        assert result.result_name == "Newton's Second Law"
        assert len(result.explanation) > 0
        assert result.domain == "physics.class-ph"
        assert result.theory_status == "current"

    @pytest.mark.asyncio
    async def test_result_id_format(self, agent_with_mocks):
        """Test that result_id follows conventions (lowercase, underscores)."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Special relativity...", historical_context=None, suggested_references=[]
        )

        mock_llm_response = {
            "result_id": "special_relativity",
            "result_name": "Special Relativity",
            "explanation": "Special relativity describes spacetime relationships.",
            "domain": "physics.gen-ph",
            "theory_status": "current",
            "references": [],
            "contributor_name": "Test",
            "contributor_id": "test",
            "review_status": "draft",
            "historical_context": None,
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, topic="Special Relativity")

        # Check result_id format
        assert result.result_id == result.result_id.lower()
        assert " " not in result.result_id
        assert all(c.isalnum() or c == "_" for c in result.result_id)

    @pytest.mark.asyncio
    async def test_explanation_length_constraint(self, agent_with_mocks):
        """Test that explanation respects character limit (max 800)."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test context", historical_context=None, suggested_references=[]
        )

        mock_llm_response = {
            "result_id": "test_topic",
            "result_name": "Test Topic",
            "explanation": "A" * 750,  # Within limit
            "domain": "physics.gen-ph",
            "theory_status": "current",
            "references": [],
            "contributor_name": "Test",
            "contributor_id": "test",
            "review_status": "draft",
            "historical_context": None,
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, topic="Test Topic")

        # The agent should produce explanation within limits
        assert len(result.explanation) <= 800

    @pytest.mark.asyncio
    async def test_result_name_length_constraint(self, agent_with_mocks):
        """Test that result_name respects character limit (max 100)."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test context", historical_context=None, suggested_references=[]
        )

        mock_llm_response = {
            "result_id": "test_topic",
            "result_name": "Test Topic Name",
            "explanation": "Test explanation",
            "domain": "physics.gen-ph",
            "theory_status": "current",
            "references": [],
            "contributor_name": "Test",
            "contributor_id": "test",
            "review_status": "draft",
            "historical_context": None,
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, topic="Test Topic")

        assert len(result.result_name) <= 100

    @pytest.mark.asyncio
    async def test_domain_is_valid_arxiv_category(self, agent_with_mocks):
        """Test that domain uses valid arXiv taxonomy."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Quantum mechanics content", historical_context=None, suggested_references=[]
        )

        mock_llm_response = {
            "result_id": "quantum_mechanics",
            "result_name": "Quantum Mechanics",
            "explanation": "Quantum mechanics describes atomic-scale phenomena.",
            "domain": "quant-ph",
            "theory_status": "current",
            "references": [],
            "contributor_name": "Test",
            "contributor_id": "test",
            "review_status": "draft",
            "historical_context": None,
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, topic="Quantum Mechanics")

        # Check that domain is a valid arXiv category
        valid_domains = [
            "physics.class-ph",
            "physics.gen-ph",
            "quant-ph",
            "gr-qc",
            "hep-th",
            "hep-ph",
            "cond-mat",
            "astro-ph",
        ]
        assert any(result.domain.startswith(d) for d in valid_domains)

    @pytest.mark.asyncio
    async def test_theory_status_is_valid(self, agent_with_mocks):
        """Test that theory_status is one of allowed values."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Classical mechanics", historical_context=None, suggested_references=[]
        )

        mock_llm_response = {
            "result_id": "classical_mechanics",
            "result_name": "Classical Mechanics",
            "explanation": "Classical mechanics describes macroscopic motion.",
            "domain": "physics.class-ph",
            "theory_status": "current",
            "references": [],
            "contributor_name": "Test",
            "contributor_id": "test",
            "review_status": "draft",
            "historical_context": None,
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, topic="Classical Mechanics")

        valid_statuses = ["current", "historical", "approximation", "limiting_case", "generalized"]
        assert result.theory_status in valid_statuses

    @pytest.mark.asyncio
    async def test_references_from_info_output(self, agent_with_mocks):
        """Test that references are properly carried over from InformationGatheringOutput."""
        agent = agent_with_mocks

        info_output = NEWTONS_SECOND_LAW_INFO

        mock_llm_response = {
            "result_id": "newtons_second_law",
            "result_name": "Newton's Second Law",
            "explanation": "Newton's second law describes force and motion.",
            "domain": "physics.class-ph",
            "theory_status": "current",
            "references": [
                {"id": "R1", "citation": "Newton, I. (1687). Philosophiæ Naturalis Principia Mathematica. London: Royal Society."}
            ],
            "contributor_name": "Test",
            "contributor_id": "test",
            "review_status": "draft",
            "historical_context": None,
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, topic="Newton's Second Law")

        # Should have at least one reference
        assert len(result.references) >= 1
        assert all(isinstance(ref, Reference) for ref in result.references)

    @pytest.mark.asyncio
    async def test_historical_context_preserved(self, agent_with_mocks):
        """Test that historical_context from InformationGatheringOutput is preserved."""
        agent = agent_with_mocks

        info_output = NEWTONS_SECOND_LAW_INFO

        mock_llm_response = {
            "result_id": "newtons_second_law",
            "result_name": "Newton's Second Law",
            "explanation": "Newton's second law describes force and motion.",
            "domain": "physics.class-ph",
            "theory_status": "current",
            "references": [],
            "contributor_name": "Test",
            "contributor_id": "test",
            "review_status": "draft",
            "historical_context": {
                "importance": "Foundation of classical mechanics",
                "development_period": "1687",
                "key_insights": ["Quantitative description of force and motion"],
            },
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, topic="Newton's Second Law")

        assert result.historical_context is not None
        assert isinstance(result.historical_context, HistoricalContext)
        assert result.historical_context.importance is not None
        assert result.historical_context.development_period is not None


class TestOutputValidation:
    """Test output validation and structure."""

    @pytest.mark.asyncio
    async def test_output_is_valid_pydantic_model(self, agent_with_mocks):
        """Test that output is a valid Pydantic model."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test context", historical_context=None, suggested_references=[]
        )

        mock_llm_response = {
            "result_id": "test",
            "result_name": "Test",
            "explanation": "Test",
            "domain": "physics.gen-ph",
            "theory_status": "current",
            "references": [],
            "contributor_name": "Test",
            "contributor_id": "test",
            "review_status": "draft",
            "historical_context": None,
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, topic="Test")

        # Should be valid Pydantic model
        assert isinstance(result, MetadataOutput)

        # Should be serializable
        result_dict = result.model_dump()
        assert "result_id" in result_dict
        assert "result_name" in result_dict
        assert "explanation" in result_dict

    @pytest.mark.asyncio
    async def test_review_status_defaults_to_draft(self, agent_with_mocks):
        """Test that review_status defaults to 'draft'."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test", historical_context=None, suggested_references=[]
        )

        mock_llm_response = {
            "result_id": "test",
            "result_name": "Test",
            "explanation": "Test",
            "domain": "physics.gen-ph",
            "theory_status": "current",
            "references": [],
            "contributor_name": "Test",
            "contributor_id": "test",
            "review_status": "draft",
            "historical_context": None,
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, topic="Test")

        assert result.review_status == "draft"


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_handles_llm_error_gracefully(self, agent_with_mocks):
        """Test that agent handles LLM errors gracefully."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test", historical_context=None, suggested_references=[]
        )

        agent.llm_client.complete_json = AsyncMock(side_effect=Exception("LLM error"))

        # Should raise exception
        with pytest.raises(Exception):
            await agent.run(info_output=info_output, topic="Test")
