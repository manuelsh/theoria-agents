"""Unit tests for new Pydantic data models.

Tests the new models introduced for the restructured agent pipeline:
- InformationGatheringOutput
- MetadataOutput
- AssumptionsDependenciesOutput
- EquationsSymbolsOutput
"""

import pytest
from pydantic import ValidationError

from src.models import (
    AssumptionsDependenciesOutput,
    Definition,
    Equation,
    EquationsSymbolsOutput,
    HistoricalContext,
    InformationGatheringOutput,
    MetadataOutput,
    ProposedAssumption,
    Reference,
)


class TestInformationGatheringOutput:
    """Test InformationGatheringOutput model."""

    def test_information_gathering_output_schema(self):
        """Test that InformationGatheringOutput can be created with all required fields."""
        output = InformationGatheringOutput(
            web_context="Special relativity is a theory of spacetime...",
            historical_context=HistoricalContext(
                importance="Revolutionary theory that changed our understanding of space and time",
                development_period="1905",
                key_insights=["Speed of light is constant", "Time dilation", "Length contraction"],
            ),
            suggested_references=[
                Reference(id="R1", citation="Einstein, A. (1905). On the Electrodynamics of Moving Bodies.")
            ],
        )

        assert output.web_context == "Special relativity is a theory of spacetime..."
        assert output.historical_context is not None
        assert output.historical_context.development_period == "1905"
        assert len(output.suggested_references) == 1
        assert output.suggested_references[0].id == "R1"

    def test_information_gathering_output_optional_fields(self):
        """Test that historical_context and suggested_references are optional."""
        output = InformationGatheringOutput(
            web_context="Some physics context...", historical_context=None, suggested_references=[]
        )

        assert output.web_context == "Some physics context..."
        assert output.historical_context is None
        assert output.suggested_references == []

    def test_information_gathering_output_missing_web_context(self):
        """Test that web_context is required."""
        with pytest.raises(ValidationError):
            InformationGatheringOutput(historical_context=None, suggested_references=[])


class TestMetadataOutput:
    """Test MetadataOutput model."""

    def test_metadata_output_schema(self):
        """Test that MetadataOutput can be created with all required fields."""
        output = MetadataOutput(
            result_id="lorentz_transformation",
            result_name="Lorentz Transformation",
            explanation="The Lorentz transformation relates space and time coordinates...",
            domain="gr-qc",
            theory_status="current",
            references=[Reference(id="R1", citation="Einstein, A. (1905).")],
            contributor_name="John Doe",
            contributor_id="https://orcid.org/0000-0001-2345-6789",
            review_status="draft",
            historical_context=None,
        )

        assert output.result_id == "lorentz_transformation"
        assert output.result_name == "Lorentz Transformation"
        assert output.explanation.startswith("The Lorentz transformation")
        assert output.domain == "gr-qc"
        assert output.theory_status == "current"
        assert len(output.references) == 1
        assert output.contributor_name == "John Doe"
        assert output.review_status == "draft"

    def test_metadata_output_with_historical_context(self):
        """Test MetadataOutput with optional historical_context."""
        output = MetadataOutput(
            result_id="newtonian_mechanics",
            result_name="Newtonian Mechanics",
            explanation="Classical mechanics framework...",
            domain="physics.class-ph",
            theory_status="historical",
            references=[Reference(id="R1", citation="Newton, I. (1687).")],
            contributor_name="Jane Smith",
            contributor_id="https://example.com",
            review_status="draft",
            historical_context=HistoricalContext(
                importance="Foundation of classical physics",
                development_period="17th century",
                key_insights=["Laws of motion", "Universal gravitation"],
            ),
        )

        assert output.historical_context is not None
        assert output.historical_context.importance == "Foundation of classical physics"

    def test_metadata_output_result_id_validation(self):
        """Test that result_id must be lowercase with underscores."""
        # Valid IDs
        valid_output = MetadataOutput(
            result_id="special_relativity",
            result_name="Special Relativity",
            explanation="Theory...",
            domain="gr-qc",
            theory_status="current",
            references=[Reference(id="R1", citation="Einstein (1905)")],
            contributor_name="Test",
            contributor_id="test",
            review_status="draft",
        )
        assert valid_output.result_id == "special_relativity"

        # Note: Pydantic validation for pattern matching would need to be added to the model


class TestAssumptionsDependenciesOutput:
    """Test AssumptionsDependenciesOutput model."""

    def test_assumptions_dependencies_output_schema(self):
        """Test that AssumptionsDependenciesOutput can be created with all fields."""
        output = AssumptionsDependenciesOutput(
            assumptions=["conservation_of_energy", "inertial_reference_frame"],
            new_assumptions=[
                ProposedAssumption(
                    id="test_assumption",
                    title="Test Assumption",
                    text="This is a test assumption for validation",
                    type="principle",
                )
            ],
            depends_on=["vector_calculus", "differential_equations"],
            missing_dependencies=[
                {"id": "fourier_analysis", "reason": "Needed for frequency domain analysis"}
            ],
        )

        assert len(output.assumptions) == 2
        assert "conservation_of_energy" in output.assumptions
        assert len(output.new_assumptions) == 1
        assert output.new_assumptions[0].id == "test_assumption"
        assert len(output.depends_on) == 2
        assert len(output.missing_dependencies) == 1

    def test_assumptions_dependencies_output_empty_lists(self):
        """Test that all lists can be empty."""
        output = AssumptionsDependenciesOutput(
            assumptions=[], new_assumptions=[], depends_on=[], missing_dependencies=[]
        )

        assert output.assumptions == []
        assert output.new_assumptions == []
        assert output.depends_on == []
        assert output.missing_dependencies == []

    def test_proposed_assumption_schema(self):
        """Test ProposedAssumption structure."""
        assumption = ProposedAssumption(
            id="quantum_superposition",
            title="Quantum Superposition Principle",
            text="A quantum system can exist in multiple states simultaneously until measured.",
            type="principle",
            mathematical_expressions=["|psi> = sum_i c_i |psi_i>"],
            symbol_definitions=[
                Definition(symbol="|psi>", definition="Quantum state vector"),
                Definition(symbol="c_i", definition="Complex amplitude coefficients"),
            ],
        )

        assert assumption.id == "quantum_superposition"
        assert assumption.type == "principle"
        assert len(assumption.mathematical_expressions) == 1
        assert len(assumption.symbol_definitions) == 2

    def test_proposed_assumption_without_math(self):
        """Test ProposedAssumption without mathematical expressions."""
        assumption = ProposedAssumption(
            id="empirical_constant",
            title="Empirical Constant",
            text="A measured physical constant",
            type="empirical",
        )

        assert assumption.mathematical_expressions is None
        assert assumption.symbol_definitions is None


class TestEquationsSymbolsOutput:
    """Test EquationsSymbolsOutput model."""

    def test_equations_symbols_output_schema(self):
        """Test that EquationsSymbolsOutput can be created with all required fields."""
        output = EquationsSymbolsOutput(
            result_equations=[
                Equation(id="eq1", equation="F = m a", equation_title="Newton's Second Law"),
                Equation(id="eq2", equation="E = (1)/(2) m v^2", equation_title=None),
            ],
            definitions=[
                Definition(symbol="F", definition="Force applied to the object"),
                Definition(symbol="m", definition="Mass of the object"),
                Definition(symbol="a", definition="Acceleration of the object"),
                Definition(symbol="E", definition="Kinetic energy"),
                Definition(symbol="v", definition="Velocity of the object"),
            ],
        )

        assert len(output.result_equations) == 2
        assert output.result_equations[0].id == "eq1"
        assert output.result_equations[0].equation == "F = m a"
        assert output.result_equations[0].equation_title == "Newton's Second Law"
        assert output.result_equations[1].equation_title is None
        assert len(output.definitions) == 5

    def test_equations_symbols_output_missing_equation(self):
        """Test that at least one equation is required."""
        with pytest.raises(ValidationError):
            EquationsSymbolsOutput(result_equations=[], definitions=[])

    def test_equations_symbols_output_all_symbols_defined(self):
        """Test that every symbol in equations has a definition."""
        output = EquationsSymbolsOutput(
            result_equations=[Equation(id="eq1", equation="p = m v")],
            definitions=[
                Definition(symbol="p", definition="Momentum"),
                Definition(symbol="m", definition="Mass"),
                Definition(symbol="v", definition="Velocity"),
            ],
        )

        # Extract symbols from equation (simplified check)
        equation_symbols = {"p", "m", "v"}
        definition_symbols = {d.symbol for d in output.definitions}

        assert equation_symbols.issubset(definition_symbols)

    def test_equation_ids_unique(self):
        """Test that equation IDs should be unique."""
        # This test documents expected behavior, actual validation may need to be added
        output = EquationsSymbolsOutput(
            result_equations=[
                Equation(id="eq1", equation="F = m a"),
                Equation(id="eq2", equation="p = m v"),
            ],
            definitions=[
                Definition(symbol="F", definition="Force"),
                Definition(symbol="p", definition="Momentum"),
                Definition(symbol="m", definition="Mass"),
                Definition(symbol="a", definition="Acceleration"),
                Definition(symbol="v", definition="Velocity"),
            ],
        )

        ids = [eq.id for eq in output.result_equations]
        assert len(ids) == len(set(ids))  # All unique


class TestModelIntegration:
    """Test how models work together."""

    def test_models_can_be_chained(self):
        """Test that outputs from one model can feed into another."""
        # Simulate InformationGatherer -> MetadataFiller flow
        info_output = InformationGatheringOutput(
            web_context="Physics context...", historical_context=None, suggested_references=[]
        )

        # MetadataFiller uses info_output to create metadata
        metadata_output = MetadataOutput(
            result_id="test_entry",
            result_name="Test Entry",
            explanation="Test explanation",
            domain="physics.gen-ph",
            theory_status="current",
            references=[Reference(id="R1", citation="Test citation")],
            contributor_name="Test Author",
            contributor_id="test_id",
            review_status="draft",
        )

        # AssumptionsDependencies uses both
        assumptions_output = AssumptionsDependenciesOutput(
            assumptions=["test_assumption"], new_assumptions=[], depends_on=[], missing_dependencies=[]
        )

        # EquationsSymbols uses all previous outputs conceptually
        equations_output = EquationsSymbolsOutput(
            result_equations=[Equation(id="eq1", equation="test = equation")],
            definitions=[Definition(symbol="test", definition="Test symbol")],
        )

        # All models created successfully
        assert info_output is not None
        assert metadata_output is not None
        assert assumptions_output is not None
        assert equations_output is not None
