"""Unit tests for AssumptionsDependenciesAgent.

Tests the assumptions and dependencies agent in isolation with mocked dependencies.
"""

import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.assumptions_dependencies import AssumptionsDependenciesAgent
from src.models import (
    AssumptionsDependenciesOutput,
    InformationGatheringOutput,
    MetadataOutput,
    ProposedAssumption,
    Definition,
)
from tests.fixtures.expected_outputs import (
    NEWTONS_SECOND_LAW_INFO,
    NEWTONS_SECOND_LAW_METADATA,
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
    """Create a mock DatasetLoader with assumptions and entries."""
    with patch("src.agents.base.DatasetLoader") as mock_loader:
        mock_instance = MagicMock()

        # Mock assumptions
        mock_instance.load_assumptions.return_value = [
            {
                "id": "inertial_reference_frame",
                "title": "Inertial Reference Frame",
                "text": "A reference frame in which Newton's first law holds.",
                "type": "framework",
            },
            {
                "id": "classical_mechanics_framework",
                "title": "Classical Mechanics Framework",
                "text": "Framework valid for speeds much less than c and scales much larger than atomic.",
                "type": "framework",
            },
            {
                "id": "quantum_mechanics_framework",
                "title": "Quantum Mechanics Framework",
                "text": "Framework for describing atomic and subatomic phenomena.",
                "type": "framework",
            },
        ]

        # Mock existing entries
        mock_instance.load_entries.return_value = [
            {"result_id": "lorentz_transformation", "result_name": "Lorentz Transformation"},
            {"result_id": "schrodinger_equation", "result_name": "Schrödinger Equation"},
        ]

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
    """Create an AssumptionsDependenciesAgent with mocked dependencies."""
    with patch("src.agents.base.load_config", return_value=mock_config):
        with patch("src.agents.base.get_model", return_value="mock-best-model"):
            agent = AssumptionsDependenciesAgent()
            return agent


class TestAssumptionsDependenciesInitialization:
    """Test AssumptionsDependenciesAgent initialization."""

    def test_assumptions_dependencies_initialization(self, agent_with_mocks):
        """Verify agent inherits from BaseAgent and initializes correctly."""
        agent = agent_with_mocks

        # Check agent_name is set correctly
        assert agent.agent_name == "assumptions_dependencies"

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
                    agent = AssumptionsDependenciesAgent()

                    # Verify get_model was called with correct agent name
                    mock_get_model.assert_called_once()
                    call_args = mock_get_model.call_args[0]
                    assert call_args[0] == "assumptions_dependencies"


class TestSelectAssumptions:
    """Test selecting existing assumptions."""

    @pytest.mark.asyncio
    async def test_select_existing_assumptions(self, agent_with_mocks, mock_dataset_loader):
        """Test selecting existing assumptions from globals."""
        agent = agent_with_mocks

        info_output = NEWTONS_SECOND_LAW_INFO
        metadata_output = NEWTONS_SECOND_LAW_METADATA

        mock_llm_response = {
            "assumptions": ["inertial_reference_frame", "classical_mechanics_framework"],
            "new_assumptions": [],
            "depends_on": [],
            "missing_dependencies": [],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, metadata_output=metadata_output)

        # Verify assumptions were selected
        assert isinstance(result, AssumptionsDependenciesOutput)
        assert len(result.assumptions) == 2
        assert "inertial_reference_frame" in result.assumptions
        assert "classical_mechanics_framework" in result.assumptions

        # Verify dataset was consulted
        mock_dataset_loader.load_assumptions.assert_called_once()

    @pytest.mark.asyncio
    async def test_no_duplicate_assumptions(self, agent_with_mocks):
        """Test that selected assumptions don't duplicate existing ones."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Test context", historical_context=None, suggested_references=[]
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

        mock_llm_response = {
            "assumptions": ["inertial_reference_frame"],
            "new_assumptions": [],
            "depends_on": [],
            "missing_dependencies": [],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, metadata_output=metadata_output)

        # Check no duplicate IDs
        assert len(result.assumptions) == len(set(result.assumptions))


class TestIdentifyDependencies:
    """Test identifying dependencies on existing entries."""

    @pytest.mark.asyncio
    async def test_identify_existing_dependencies(self, agent_with_mocks, mock_dataset_loader):
        """Test identifying dependencies on existing entries."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Builds upon Lorentz transformation", historical_context=None, suggested_references=[]
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

        mock_llm_response = {
            "assumptions": [],
            "new_assumptions": [],
            "depends_on": ["lorentz_transformation"],
            "missing_dependencies": [],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, metadata_output=metadata_output)

        # Verify dependency identified
        assert len(result.depends_on) == 1
        assert "lorentz_transformation" in result.depends_on

        # Verify dataset was consulted
        mock_dataset_loader.load_entries.assert_called_once()

    @pytest.mark.asyncio
    async def test_flag_missing_dependencies(self, agent_with_mocks):
        """Test flagging missing dependencies that need to be built."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Requires harmonic oscillator as foundation", historical_context=None, suggested_references=[]
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

        mock_llm_response = {
            "assumptions": [],
            "new_assumptions": [],
            "depends_on": ["harmonic_oscillator"],
            "missing_dependencies": [
                {"id": "harmonic_oscillator", "reason": "Needed as foundation for quantum harmonic oscillator"}
            ],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, metadata_output=metadata_output)

        # Verify missing dependency flagged
        assert len(result.missing_dependencies) == 1
        assert result.missing_dependencies[0]["id"] == "harmonic_oscillator"
        assert "reason" in result.missing_dependencies[0]


class TestProposeNewAssumptions:
    """Test proposing new assumptions when needed."""

    @pytest.mark.asyncio
    async def test_propose_new_assumption(self, agent_with_mocks):
        """Test proposing a genuinely new assumption."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Quantum superposition is a fundamental principle",
            historical_context=None,
            suggested_references=[],
        )
        metadata_output = MetadataOutput(
            result_id="test",
            result_name="Test",
            explanation="Test",
            domain="quant-ph",
            theory_status="current",
            references=[],
            contributor_name="Test",
            contributor_id="test",
            review_status="draft",
        )

        mock_llm_response = {
            "assumptions": ["quantum_mechanics_framework"],
            "new_assumptions": [
                {
                    "id": "quantum_superposition",
                    "title": "Quantum Superposition Principle",
                    "text": "A quantum system can exist in multiple states simultaneously until measured.",
                    "type": "principle",
                    "mathematical_expressions": ["|psi> = sum_i c_i |psi_i>"],
                    "symbol_definitions": [
                        {"symbol": "|psi>", "definition": "Quantum state vector"},
                        {"symbol": "c_i", "definition": "Complex amplitude coefficients"},
                    ],
                }
            ],
            "depends_on": [],
            "missing_dependencies": [],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, metadata_output=metadata_output)

        # Verify new assumption proposed
        assert len(result.new_assumptions) == 1
        new_assumption = result.new_assumptions[0]
        assert isinstance(new_assumption, ProposedAssumption)
        assert new_assumption.id == "quantum_superposition"
        assert new_assumption.title is not None
        assert new_assumption.text is not None
        assert new_assumption.type in ["framework", "principle", "approximation", "condition"]

    @pytest.mark.asyncio
    async def test_new_assumption_with_symbols(self, agent_with_mocks):
        """Test that new assumptions can include mathematical expressions and symbol definitions."""
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

        mock_llm_response = {
            "assumptions": [],
            "new_assumptions": [
                {
                    "id": "test_assumption",
                    "title": "Test Assumption",
                    "text": "Test text",
                    "type": "principle",
                    "mathematical_expressions": ["E = m c^2"],
                    "symbol_definitions": [
                        {"symbol": "E", "definition": "Energy"},
                        {"symbol": "m", "definition": "Mass"},
                        {"symbol": "c", "definition": "Speed of light"},
                    ],
                }
            ],
            "depends_on": [],
            "missing_dependencies": [],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, metadata_output=metadata_output)

        new_assumption = result.new_assumptions[0]
        assert len(new_assumption.mathematical_expressions) > 0
        assert len(new_assumption.symbol_definitions) > 0
        assert all(isinstance(defn, Definition) for defn in new_assumption.symbol_definitions)


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

        mock_llm_response = {
            "assumptions": ["inertial_reference_frame"],
            "new_assumptions": [],
            "depends_on": [],
            "missing_dependencies": [],
        }

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, metadata_output=metadata_output)

        # Should be valid Pydantic model
        assert isinstance(result, AssumptionsDependenciesOutput)

        # Should be serializable
        result_dict = result.model_dump()
        assert "assumptions" in result_dict
        assert "new_assumptions" in result_dict
        assert "depends_on" in result_dict
        assert "missing_dependencies" in result_dict

    @pytest.mark.asyncio
    async def test_all_fields_can_be_empty(self, agent_with_mocks):
        """Test that all output fields can be empty arrays (for self-contained entries)."""
        agent = agent_with_mocks

        info_output = InformationGatheringOutput(
            web_context="Self-contained fundamental principle", historical_context=None, suggested_references=[]
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

        mock_llm_response = {"assumptions": [], "new_assumptions": [], "depends_on": [], "missing_dependencies": []}

        agent.llm_client.complete_json = AsyncMock(return_value=json.dumps(mock_llm_response))

        result = await agent.run(info_output=info_output, metadata_output=metadata_output)

        # All fields can be empty for truly fundamental entries
        assert result.assumptions == []
        assert result.new_assumptions == []
        assert result.depends_on == []
        assert result.missing_dependencies == []


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

        agent.llm_client.complete_json = AsyncMock(side_effect=Exception("LLM error"))

        # Should raise exception
        with pytest.raises(Exception):
            await agent.run(info_output=info_output, metadata_output=metadata_output)

    @pytest.mark.asyncio
    async def test_handles_dataset_load_error(self, agent_with_mocks, mock_dataset_loader):
        """Test handling of dataset loading errors."""
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

        # Make dataset loading fail
        mock_dataset_loader.load_assumptions.side_effect = Exception("Dataset error")

        # Should handle error appropriately
        with pytest.raises(Exception):
            await agent.run(info_output=info_output, metadata_output=metadata_output)
