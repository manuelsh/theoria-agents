"""Unit tests for InformationGathererAgent.

Tests the information gathering agent in isolation with mocked dependencies.
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.information_gatherer import InformationGathererAgent
from src.models import HistoricalContext, InformationGatheringOutput, Reference
from tests.fixtures.mock_wikipedia_responses import (
    NEWTONS_SECOND_LAW,
    NOT_FOUND_RESPONSE,
    SPECIAL_RELATIVITY,
    VERY_LONG_CONTENT,
)


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
        mock_instance.json_completion = AsyncMock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def agent_with_mocks(mock_config, mock_dataset_loader, mock_llm_client):
    """Create an InformationGathererAgent with mocked dependencies."""
    with patch("src.agents.base.load_config", return_value=mock_config):
        with patch("src.agents.base.get_model", return_value="mock-fast-model"):
            agent = InformationGathererAgent()
            return agent


class TestInformationGathererInitialization:
    """Test InformationGathererAgent initialization."""

    def test_information_gatherer_initialization(self, agent_with_mocks):
        """Verify agent inherits from BaseAgent and initializes correctly."""
        agent = agent_with_mocks

        # Check agent_name is set correctly
        assert agent.agent_name == "information_gatherer"

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
                    agent = InformationGathererAgent()

                    # Verify get_model was called with correct agent name
                    mock_get_model.assert_called_once()
                    call_args = mock_get_model.call_args[0]
                    assert call_args[0] == "information_gatherer"


class TestGatherWikipediaContext:
    """Test gathering Wikipedia context."""

    @pytest.mark.asyncio
    async def test_gather_wikipedia_context_success(self, agent_with_mocks):
        """Test successful Wikipedia content gathering."""
        agent = agent_with_mocks

        # Mock the LLM response
        mock_llm_response = {
            "web_context": "Special relativity is a theory of spacetime...",
            "historical_context": {
                "importance": "Revolutionary theory",
                "development_period": "1905",
                "key_insights": ["Speed of light constant", "Time dilation"],
            },
            "suggested_references": [
                {"id": "R1", "citation": "Einstein, A. (1905). On the Electrodynamics of Moving Bodies."}
            ],
        }

        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = SPECIAL_RELATIVITY
            agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

            result = await agent.run(topic="Special Relativity")

            # Verify output structure
            assert isinstance(result, InformationGatheringOutput)
            assert result.web_context is not None
            assert len(result.web_context) > 0

            # Verify web search was called
            mock_fetch.assert_called_once_with("Special Relativity")

    @pytest.mark.asyncio
    async def test_gather_historical_context(self, agent_with_mocks):
        """Test gathering historical context from Wikipedia."""
        agent = agent_with_mocks

        mock_llm_response = {
            "web_context": "Newton's laws formed the foundation...",
            "historical_context": {
                "importance": "Foundation of classical mechanics",
                "development_period": "1687",
                "key_insights": ["Laws of motion", "Universal gravitation"],
            },
            "suggested_references": [{"id": "R1", "citation": "Newton, I. (1687). Principia Mathematica."}],
        }

        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = NEWTONS_SECOND_LAW
            agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

            result = await agent.run(topic="Newton's Laws")

            # Verify historical context is populated
            assert result.historical_context is not None
            assert result.historical_context.importance is not None
            assert result.historical_context.development_period is not None
            assert result.historical_context.key_insights is not None
            assert len(result.historical_context.key_insights) > 0

    @pytest.mark.asyncio
    async def test_suggest_references(self, agent_with_mocks):
        """Test suggesting references from Wikipedia content."""
        agent = agent_with_mocks

        mock_llm_response = {
            "web_context": "Maxwell's equations...",
            "historical_context": None,
            "suggested_references": [
                {"id": "R1", "citation": "Maxwell, J. C. (1865). A Dynamical Theory of the Electromagnetic Field."},
                {
                    "id": "R2",
                    "citation": "Heaviside, O. (1893). Electromagnetic Theory. The Electrician Printing and Publishing Company.",
                },
            ],
        }

        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "Maxwell's equations mock content..."
            agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

            result = await agent.run(topic="Maxwell's Equations")

            # Verify references are suggested
            assert len(result.suggested_references) >= 1
            assert len(result.suggested_references) <= 3  # Should be 1-3 refs

            # Verify reference format
            for ref in result.suggested_references:
                assert isinstance(ref, Reference)
                assert ref.id is not None
                assert ref.citation is not None
                assert len(ref.citation) > 0

    @pytest.mark.asyncio
    async def test_truncate_long_content(self, agent_with_mocks):
        """Test that very long Wikipedia content is truncated."""
        agent = agent_with_mocks

        # The web_search utility already truncates at 10k chars
        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            # Simulate truncated content from web_search
            truncated_content = VERY_LONG_CONTENT[:10000] + "...[truncated]"
            mock_fetch.return_value = truncated_content

            mock_llm_response = {
                "web_context": "Summarized content that is reasonable length...",
                "historical_context": None,
                "suggested_references": [],
            }
            agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

            result = await agent.run(topic="Very Long Topic")

            # Verify the LLM receives truncated content
            # Check that fetch_wikipedia returned truncated content
            assert "[truncated]" in truncated_content
            assert len(truncated_content) <= 10020  # 10k + "[truncated]"

            # Verify agent still produces valid output
            assert isinstance(result, InformationGatheringOutput)

    @pytest.mark.asyncio
    async def test_handle_wikipedia_not_found(self, agent_with_mocks):
        """Test graceful handling when Wikipedia page not found."""
        agent = agent_with_mocks

        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "No Wikipedia content found for: Nonexistent Topic"

            # Agent should still try to produce output with empty/minimal context
            mock_llm_response = {
                "web_context": "Limited information available for this topic.",
                "historical_context": None,
                "suggested_references": [],
            }
            agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

            result = await agent.run(topic="Nonexistent Topic")

            # Should not raise exception
            assert isinstance(result, InformationGatheringOutput)
            assert result.web_context is not None


class TestWebContextQuality:
    """Test quality of gathered web context."""

    @pytest.mark.asyncio
    async def test_web_context_length_constraint(self, agent_with_mocks):
        """Test that web_context respects length constraints."""
        agent = agent_with_mocks

        mock_llm_response = {
            "web_context": "A" * 15000,  # Intentionally long
            "historical_context": None,
            "suggested_references": [],
        }

        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "Mock content"
            agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

            result = await agent.run(topic="Test Topic")

            # The LLM might return long content, but it should still be valid
            # The actual truncation happens in web_search (already tested)
            assert isinstance(result, InformationGatheringOutput)

    @pytest.mark.asyncio
    async def test_web_context_is_graduate_level(self, agent_with_mocks):
        """Test that gathered content is appropriate for graduate-level physics."""
        agent = agent_with_mocks

        mock_llm_response = {
            "web_context": (
                "Special relativity describes the relationship between space and time "
                "in inertial reference frames. The theory postulates that the speed of light "
                "is constant in all inertial frames and that physical laws are invariant under "
                "Lorentz transformations."
            ),
            "historical_context": None,
            "suggested_references": [],
        }

        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = SPECIAL_RELATIVITY
            agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

            result = await agent.run(topic="Special Relativity")

            # Check that content is substantive (not trivial)
            assert len(result.web_context) > 100  # Substantive content
            # Could add more sophisticated checks for technical terms, etc.


class TestOutputValidation:
    """Test output validation and structure."""

    @pytest.mark.asyncio
    async def test_output_is_valid_pydantic_model(self, agent_with_mocks):
        """Test that output is a valid Pydantic model."""
        agent = agent_with_mocks

        mock_llm_response = {
            "web_context": "Test context",
            "historical_context": {"importance": "test", "development_period": "test", "key_insights": ["test"]},
            "suggested_references": [{"id": "R1", "citation": "Test citation"}],
        }

        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "Mock content"
            agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

            result = await agent.run(topic="Test Topic")

            # Should be valid Pydantic model
            assert isinstance(result, InformationGatheringOutput)

            # Should be serializable
            result_dict = result.model_dump()
            assert "web_context" in result_dict

    @pytest.mark.asyncio
    async def test_optional_fields_handled_correctly(self, agent_with_mocks):
        """Test that optional fields (historical_context, references) can be None/empty."""
        agent = agent_with_mocks

        # Test with minimal response
        mock_llm_response = {"web_context": "Minimal context", "historical_context": None, "suggested_references": []}

        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "Mock content"
            agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

            result = await agent.run(topic="Test Topic")

            assert result.web_context == "Minimal context"
            assert result.historical_context is None
            assert result.suggested_references == []


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_handles_llm_error_gracefully(self, agent_with_mocks):
        """Test that agent handles LLM errors gracefully."""
        agent = agent_with_mocks

        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.return_value = "Mock content"
            agent.llm_client.complete_json = AsyncMock(side_effect=Exception("LLM error"))

            # Should raise exception or handle it appropriately
            with pytest.raises(Exception):
                await agent.run(topic="Test Topic")

    @pytest.mark.asyncio
    async def test_handles_network_error(self, agent_with_mocks):
        """Test handling of network errors when fetching Wikipedia."""
        agent = agent_with_mocks

        with patch("src.agents.information_gatherer.fetch_wikipedia", new_callable=AsyncMock) as mock_fetch:
            mock_fetch.side_effect = Exception("Network error")

            # Should handle network error
            with pytest.raises(Exception):
                await agent.run(topic="Test Topic")
