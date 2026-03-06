"""Unit tests for EquationsSymbolsAgent.

Tests the equations and symbols agent in isolation with mocked dependencies.
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.equations_symbols import EquationsSymbolsAgent
from src.models import (
    AssumptionsDependenciesOutput,
    Definition,
    Equation,
    EquationsSymbolsOutput,
    InformationGatheringOutput,
    MetadataOutput,
)
from tests.fixtures.expected_outputs import (
    NEWTONS_SECOND_LAW_INFO,
    NEWTONS_SECOND_LAW_METADATA,
    NEWTONS_SECOND_LAW_ASSUMPTIONS_DEPS,
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
        mock_instance.complete_json = AsyncMock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def agent_with_mocks(mock_config, mock_dataset_loader, mock_llm_client):
    """Create an EquationsSymbolsAgent with mocked dependencies."""
    with patch("src.agents.base.load_config", return_value=mock_config):
        with patch("src.agents.base.get_model", return_value="mock-best-model"):
            agent = EquationsSymbolsAgent()
            return agent


class TestEquationsSymbolsInitialization:
    """Test EquationsSymbolsAgent initialization."""

    def test_equations_symbols_initialization(self, agent_with_mocks):
        """Verify agent inherits from BaseAgent and initializes correctly."""
        agent = agent_with_mocks

        # Check agent_name is set correctly
        assert agent.agent_name == "equations_symbols"

        # Check it has required attributes from BaseAgent
        assert hasattr(agent, "llm_client")
        assert hasattr(agent, "config")
        assert hasattr(agent, "dataset")

    def test_model_assignment_is_best(self, mock_config):
        """Verify model assignment is 'best'."""
        with patch("src.agents.base.load_config", return_value=mock_config):
            with patch("src.agents.base.get_model") as mock_get_model:
                with patch("src.agents.base.DatasetLoader"):
                    mock_get_model.return_value = "best-model-arn"
                    agent = EquationsSymbolsAgent()

                    # Verify get_model was called with correct agent name
                    mock_get_model.assert_called_once()
                    call_args = mock_get_model.call_args[0]
                    assert call_args[0] == "equations_symbols"


class TestDefineEquations:
    """Test defining result equations."""

    @pytest.mark.asyncio
    async def test_define_single_equation(self, agent_with_mocks):
        """Test defining a single result equation."""
        agent = agent_with_mocks

        info_output = NEWTONS_SECOND_LAW_INFO
        metadata_output = NEWTONS_SECOND_LAW_METADATA
        assumptions_deps_output = NEWTONS_SECOND_LAW_ASSUMPTIONS_DEPS

        mock_llm_response = {
            "result_equations": [{"id": "eq1", "equation": "F = m a", "equation_title": "Newton's Second Law"}],
            "definitions": [
                {"symbol": "F", "definition": "Force applied to the object (in newtons)"},
                {"symbol": "m", "definition": "Mass of the object (in kilograms)"},
                {"symbol": "a", "definition": "Acceleration of the object (in meters per second squared)"},
            ],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(
            info_output=info_output, metadata_output=metadata_output, assumptions_deps_output=assumptions_deps_output
        )

        # Verify output structure
        assert isinstance(result, EquationsSymbolsOutput)
        assert len(result.result_equations) == 1
        assert result.result_equations[0].id == "eq1"
        assert result.result_equations[0].equation == "F = m a"

    @pytest.mark.asyncio
    async def test_define_multiple_equations(self, agent_with_mocks):
        """Test defining multiple result equations."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Energy conservation", historical_context=None, suggested_references=[]
        )
        metadata_output = MetadataOutput(
            result_id="energy_conservation",
            result_name="Energy Conservation",
            explanation="Test",
            domain="physics.class-ph",
            theory_status="current",
            references=[],
            contributor_name="Test",
            contributor_id="test",
            review_status="draft",
        )
        assumptions_deps_output = AssumptionsDependenciesOutput(
            assumptions=[], new_assumptions=[], depends_on=[], missing_dependencies=[]
        )

        mock_llm_response = {
            "result_equations": [
                {"id": "eq1", "equation": "E_(kinetic) = (1)/(2) m v^2", "equation_title": "Kinetic Energy"},
                {
                    "id": "eq2",
                    "equation": "E_(potential) = m g h",
                    "equation_title": "Gravitational Potential Energy",
                },
            ],
            "definitions": [
                {"symbol": "E_(kinetic)", "definition": "Kinetic energy"},
                {"symbol": "E_(potential)", "definition": "Potential energy"},
                {"symbol": "m", "definition": "Mass"},
                {"symbol": "v", "definition": "Velocity"},
                {"symbol": "g", "definition": "Gravitational acceleration"},
                {"symbol": "h", "definition": "Height"},
            ],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(
            info_output=info_output, metadata_output=metadata_output, assumptions_deps_output=assumptions_deps_output
        )

        # Verify multiple equations
        assert len(result.result_equations) >= 2
        assert all(isinstance(eq, Equation) for eq in result.result_equations)


class TestAsciiMathNotation:
    """Test AsciiMath notation correctness."""

    @pytest.mark.asyncio
    async def test_fraction_notation(self, agent_with_mocks):
        """Test that fractions use proper parentheses."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test", historical_context=None, suggested_references=[]
        )
        metadata_output = MetadataOutput(
            result_id="test",
            result_name="Test",
            explanation="Test",
            domain="physics.gen-ph",
            theory_status="current",
            references=[],
            contributor_name="Test",
            contributor_id="test",
            review_status="draft",
        )
        assumptions_deps_output = AssumptionsDependenciesOutput(
            assumptions=[], new_assumptions=[], depends_on=[], missing_dependencies=[]
        )

        mock_llm_response = {
            "result_equations": [
                {"id": "eq1", "equation": "v = (dx)/(dt)", "equation_title": "Velocity"}  # Correct fraction notation
            ],
            "definitions": [
                {"symbol": "v", "definition": "Velocity"},
                {"symbol": "x", "definition": "Position"},
                {"symbol": "t", "definition": "Time"},
            ],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(
            info_output=info_output, metadata_output=metadata_output, assumptions_deps_output=assumptions_deps_output
        )

        # Check fraction format
        equation = result.result_equations[0].equation
        assert "(" in equation and ")" in equation  # Should have parentheses
        assert "(dx)/(dt)" in equation  # Correct format

    @pytest.mark.asyncio
    async def test_subscript_notation(self, agent_with_mocks):
        """Test that multi-character subscripts use parentheses."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test", historical_context=None, suggested_references=[]
        )
        metadata_output = MetadataOutput(
            result_id="test",
            result_name="Test",
            explanation="Test",
            domain="physics.gen-ph",
            theory_status="current",
            references=[],
            contributor_name="Test",
            contributor_id="test",
            review_status="draft",
        )
        assumptions_deps_output = AssumptionsDependenciesOutput(
            assumptions=[], new_assumptions=[], depends_on=[], missing_dependencies=[]
        )

        mock_llm_response = {
            "result_equations": [
                {"id": "eq1", "equation": "E_(kinetic) = (1)/(2) m v^2", "equation_title": "Kinetic Energy"}
            ],
            "definitions": [
                {"symbol": "E_(kinetic)", "definition": "Kinetic energy"},
                {"symbol": "m", "definition": "Mass"},
                {"symbol": "v", "definition": "Velocity"},
            ],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(
            info_output=info_output, metadata_output=metadata_output, assumptions_deps_output=assumptions_deps_output
        )

        # Check subscript format
        equation = result.result_equations[0].equation
        assert "E_(kinetic)" in equation  # Multi-char subscript with parentheses

    @pytest.mark.asyncio
    async def test_no_reserved_words_in_subscripts(self, agent_with_mocks):
        """Test that subscripts don't use reserved words like 'to'."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test", historical_context=None, suggested_references=[]
        )
        metadata_output = MetadataOutput(
            result_id="test",
            result_name="Test",
            explanation="Test",
            domain="physics.gen-ph",
            theory_status="current",
            references=[],
            contributor_name="Test",
            contributor_id="test",
            review_status="draft",
        )
        assumptions_deps_output = AssumptionsDependenciesOutput(
            assumptions=[], new_assumptions=[], depends_on=[], missing_dependencies=[]
        )

        mock_llm_response = {
            "result_equations": [{"id": "eq1", "equation": "E_0 = m c^2", "equation_title": "Rest Energy"}],
            "definitions": [
                {"symbol": "E_0", "definition": "Rest energy"},
                {"symbol": "m", "definition": "Rest mass"},
                {"symbol": "c", "definition": "Speed of light"},
            ],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(
            info_output=info_output, metadata_output=metadata_output, assumptions_deps_output=assumptions_deps_output
        )

        # Check no reserved words
        equation = result.result_equations[0].equation
        assert "_to" not in equation  # Should not use "to" in subscripts


class TestDefineSymbols:
    """Test defining symbols used in equations."""

    @pytest.mark.asyncio
    async def test_define_all_symbols(self, agent_with_mocks):
        """Test that all symbols in equations are defined."""
        agent = agent_with_mocks

        info_output = NEWTONS_SECOND_LAW_INFO
        metadata_output = NEWTONS_SECOND_LAW_METADATA
        assumptions_deps_output = NEWTONS_SECOND_LAW_ASSUMPTIONS_DEPS

        mock_llm_response = {
            "result_equations": [{"id": "eq1", "equation": "F = m a", "equation_title": "Newton's Second Law"}],
            "definitions": [
                {"symbol": "F", "definition": "Force applied to the object"},
                {"symbol": "m", "definition": "Mass of the object"},
                {"symbol": "a", "definition": "Acceleration of the object"},
            ],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(
            info_output=info_output, metadata_output=metadata_output, assumptions_deps_output=assumptions_deps_output
        )

        # Verify all symbols are defined
        assert len(result.definitions) >= 3
        symbols_defined = [d.symbol for d in result.definitions]
        assert "F" in symbols_defined
        assert "m" in symbols_defined
        assert "a" in symbols_defined

    @pytest.mark.asyncio
    async def test_definitions_have_descriptions(self, agent_with_mocks):
        """Test that symbol definitions have meaningful descriptions."""
        agent = agent_with_mocks

        info_output = NEWTONS_SECOND_LAW_INFO
        metadata_output = NEWTONS_SECOND_LAW_METADATA
        assumptions_deps_output = NEWTONS_SECOND_LAW_ASSUMPTIONS_DEPS

        mock_llm_response = {
            "result_equations": [{"id": "eq1", "equation": "F = m a", "equation_title": "Newton's Second Law"}],
            "definitions": [
                {"symbol": "F", "definition": "Force applied to the object (in newtons)"},
                {"symbol": "m", "definition": "Mass of the object (in kilograms)"},
                {"symbol": "a", "definition": "Acceleration of the object (in meters per second squared)"},
            ],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(
            info_output=info_output, metadata_output=metadata_output, assumptions_deps_output=assumptions_deps_output
        )

        # Verify definitions are meaningful
        for defn in result.definitions:
            assert isinstance(defn, Definition)
            assert len(defn.definition) > 5  # More than just "Force"
            assert defn.symbol is not None


class TestOutputValidation:
    """Test output validation and structure."""

    @pytest.mark.asyncio
    async def test_output_is_valid_pydantic_model(self, agent_with_mocks):
        """Test that output is a valid Pydantic model."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test", historical_context=None, suggested_references=[]
        )
        metadata_output = MetadataOutput(
            result_id="test",
            result_name="Test",
            explanation="Test",
            domain="physics.gen-ph",
            theory_status="current",
            references=[],
            contributor_name="Test",
            contributor_id="test",
            review_status="draft",
        )
        assumptions_deps_output = AssumptionsDependenciesOutput(
            assumptions=[], new_assumptions=[], depends_on=[], missing_dependencies=[]
        )

        mock_llm_response = {
            "result_equations": [{"id": "eq1", "equation": "E = m c^2", "equation_title": "Mass-Energy Equivalence"}],
            "definitions": [
                {"symbol": "E", "definition": "Energy"},
                {"symbol": "m", "definition": "Mass"},
                {"symbol": "c", "definition": "Speed of light"},
            ],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(
            info_output=info_output, metadata_output=metadata_output, assumptions_deps_output=assumptions_deps_output
        )

        # Should be valid Pydantic model
        assert isinstance(result, EquationsSymbolsOutput)

        # Should be serializable
        result_dict = result.model_dump()
        assert "result_equations" in result_dict
        assert "definitions" in result_dict

    @pytest.mark.asyncio
    async def test_requires_at_least_one_equation(self, agent_with_mocks):
        """Test that at least one equation is required."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test", historical_context=None, suggested_references=[]
        )
        metadata_output = MetadataOutput(
            result_id="test",
            result_name="Test",
            explanation="Test",
            domain="physics.gen-ph",
            theory_status="current",
            references=[],
            contributor_name="Test",
            contributor_id="test",
            review_status="draft",
        )
        assumptions_deps_output = AssumptionsDependenciesOutput(
            assumptions=[], new_assumptions=[], depends_on=[], missing_dependencies=[]
        )

        mock_llm_response = {
            "result_equations": [{"id": "eq1", "equation": "F = m a", "equation_title": "Newton's Second Law"}],
            "definitions": [{"symbol": "F", "definition": "Force"}],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(
            info_output=info_output, metadata_output=metadata_output, assumptions_deps_output=assumptions_deps_output
        )

        # At least one equation required
        assert len(result.result_equations) >= 1

    @pytest.mark.asyncio
    async def test_requires_at_least_one_definition(self, agent_with_mocks):
        """Test that at least one symbol definition is required."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test", historical_context=None, suggested_references=[]
        )
        metadata_output = MetadataOutput(
            result_id="test",
            result_name="Test",
            explanation="Test",
            domain="physics.gen-ph",
            theory_status="current",
            references=[],
            contributor_name="Test",
            contributor_id="test",
            review_status="draft",
        )
        assumptions_deps_output = AssumptionsDependenciesOutput(
            assumptions=[], new_assumptions=[], depends_on=[], missing_dependencies=[]
        )

        mock_llm_response = {
            "result_equations": [{"id": "eq1", "equation": "F = m a", "equation_title": "Newton's Second Law"}],
            "definitions": [{"symbol": "F", "definition": "Force"}],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(
            info_output=info_output, metadata_output=metadata_output, assumptions_deps_output=assumptions_deps_output
        )

        # At least one definition required
        assert len(result.definitions) >= 1


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_handles_llm_error_gracefully(self, agent_with_mocks):
        """Test that agent handles LLM errors gracefully."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test", historical_context=None, suggested_references=[]
        )
        metadata_output = MetadataOutput(
            result_id="test",
            result_name="Test",
            explanation="Test",
            domain="physics.gen-ph",
            theory_status="current",
            references=[],
            contributor_name="Test",
            contributor_id="test",
            review_status="draft",
        )
        assumptions_deps_output = AssumptionsDependenciesOutput(
            assumptions=[], new_assumptions=[], depends_on=[], missing_dependencies=[]
        )

        agent.llm_client.complete_json = AsyncMock(side_effect=Exception("LLM error"))

        # Should raise exception
        with pytest.raises(Exception):
            await agent.run(
                info_output=info_output,
                metadata_output=metadata_output,
                assumptions_deps_output=assumptions_deps_output,
            )
