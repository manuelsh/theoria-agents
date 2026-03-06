"""Expected outputs for agent testing.

Provides known-good outputs that agents should produce for specific inputs.
"""

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

# Expected InformationGatheringOutput for Newton's Second Law
NEWTONS_SECOND_LAW_INFO = InformationGatheringOutput(
    web_context="""Newton's second law states that force equals mass times acceleration (F = ma).
Formulated by Isaac Newton in 1687 in Principia Mathematica. Fundamental to classical mechanics
and dynamics. Used to analyze motion of objects in various contexts.""",
    historical_context=HistoricalContext(
        importance="Foundation of classical mechanics",
        development_period="1687",
        key_insights=["Quantitative description of force and motion", "Time rate of change of momentum"],
    ),
    suggested_references=[
        Reference(
            id="R1",
            citation="Newton, I. (1687). Philosophiæ Naturalis Principia Mathematica. London: Royal Society.",
        )
    ],
)

# Expected MetadataOutput for Newton's Second Law
NEWTONS_SECOND_LAW_METADATA = MetadataOutput(
    result_id="newtons_second_law",
    result_name="Newton's Second Law",
    explanation=(
        "Newton's second law states that the force acting on an object equals the product of "
        "its mass and acceleration (`F = m a`). This fundamental principle of classical mechanics "
        "provides a quantitative relationship between force, mass, and motion. It is essential "
        "for analyzing dynamics in physics and engineering applications."
    ),
    domain="physics.class-ph",
    theory_status="current",
    references=[
        Reference(
            id="R1",
            citation="Newton, I. (1687). Philosophiæ Naturalis Principia Mathematica. London: Royal Society.",
        )
    ],
    contributor_name="Test Contributor",
    contributor_id="test_id",
    review_status="draft",
    historical_context=HistoricalContext(
        importance="Foundation of classical mechanics",
        development_period="1687",
        key_insights=["Quantitative description of force and motion"],
    ),
)

# Expected AssumptionsDependenciesOutput for Newton's Second Law
NEWTONS_SECOND_LAW_ASSUMPTIONS_DEPS = AssumptionsDependenciesOutput(
    assumptions=["inertial_reference_frame", "classical_mechanics_framework"],
    new_assumptions=[],
    depends_on=[],
    missing_dependencies=[],
)

# Expected AssumptionsDependenciesOutput with missing dependencies
TOPIC_WITH_MISSING_DEPS = AssumptionsDependenciesOutput(
    assumptions=["quantum_mechanics_framework"],
    new_assumptions=[],
    depends_on=["harmonic_oscillator"],  # This doesn't exist
    missing_dependencies=[{"id": "harmonic_oscillator", "reason": "Needed as foundation for quantum version"}],
)

# Expected AssumptionsDependenciesOutput with new assumption
TOPIC_WITH_NEW_ASSUMPTION = AssumptionsDependenciesOutput(
    assumptions=["quantum_mechanics_framework"],
    new_assumptions=[
        ProposedAssumption(
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
    ],
    depends_on=[],
    missing_dependencies=[],
)

# Expected EquationsSymbolsOutput for Newton's Second Law
NEWTONS_SECOND_LAW_EQUATIONS = EquationsSymbolsOutput(
    result_equations=[Equation(id="eq1", equation="F = m a", equation_title="Newton's Second Law")],
    definitions=[
        Definition(symbol="F", definition="Force applied to the object (in newtons)"),
        Definition(symbol="m", definition="Mass of the object (in kilograms)"),
        Definition(symbol="a", definition="Acceleration of the object (in meters per second squared)"),
    ],
)

# Expected EquationsSymbolsOutput with multiple equations
ENERGY_EQUATIONS = EquationsSymbolsOutput(
    result_equations=[
        Equation(id="eq1", equation="E_(kinetic) = (1)/(2) m v^2", equation_title="Kinetic Energy"),
        Equation(id="eq2", equation="E_(potential) = m g h", equation_title="Gravitational Potential Energy"),
    ],
    definitions=[
        Definition(symbol="E_(kinetic)", definition="Kinetic energy of the object"),
        Definition(symbol="E_(potential)", definition="Gravitational potential energy"),
        Definition(symbol="m", definition="Mass of the object"),
        Definition(symbol="v", definition="Velocity of the object"),
        Definition(symbol="g", definition="Gravitational acceleration"),
        Definition(symbol="h", definition="Height above reference point"),
    ],
)

# Expected EquationsSymbolsOutput with correct AsciiMath notation
CORRECT_ASCIIMATH_EXAMPLES = {
    "fraction": "(numerator)/(denominator)",
    "derivative": "(dx)/(dt)",
    "partial": "(del f)/(del x)",
    "subscript_single": "E_k",
    "subscript_multi": "E_(kinetic)",
    "superscript": "x^2",
    "sum": "sum_(i=1)^n x_i",
}

# Expected EquationsSymbolsOutput with incorrect AsciiMath (for validation testing)
INCORRECT_ASCIIMATH_EXAMPLES = {
    "fraction_no_parens": "numerator/denominator",  # Missing parentheses
    "derivative_no_parens": "dx/dt",  # Missing parentheses
    "subscript_to": "E_to",  # "to" renders as arrow
    "subscript_multi_no_parens": "E_kinetic",  # Missing parentheses for multi-char
}


def create_mock_information_gathering_output(topic: str) -> InformationGatheringOutput:
    """Create a mock InformationGatheringOutput for testing.

    Args:
        topic: The physics topic

    Returns:
        Mock InformationGatheringOutput
    """
    return InformationGatheringOutput(
        web_context=f"Mock web context for {topic}...",
        historical_context=HistoricalContext(importance=f"Important for {topic}", development_period="20th century"),
        suggested_references=[Reference(id="R1", citation=f"Reference for {topic}.")],
    )


def create_mock_metadata_output(topic: str, result_id: str) -> MetadataOutput:
    """Create a mock MetadataOutput for testing.

    Args:
        topic: The physics topic
        result_id: The entry ID

    Returns:
        Mock MetadataOutput
    """
    return MetadataOutput(
        result_id=result_id,
        result_name=topic,
        explanation=f"Mock explanation for {topic}.",
        domain="physics.gen-ph",
        theory_status="current",
        references=[Reference(id="R1", citation=f"Reference for {topic}.")],
        contributor_name="Test Contributor",
        contributor_id="test_id",
        review_status="draft",
    )
