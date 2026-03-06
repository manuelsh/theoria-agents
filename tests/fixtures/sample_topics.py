"""Sample physics topics for testing.

Provides various physics topics with different characteristics for comprehensive testing.
"""

from typing import TypedDict


class TopicFixture(TypedDict):
    """Structure for a topic test fixture."""

    name: str
    description: str
    expected_domain: str
    expected_theory_status: str
    has_historical_context: bool
    requires_new_assumptions: bool
    has_missing_dependencies: bool


# Simple topics that should work end-to-end
SIMPLE_TOPICS = {
    "newtons_second_law": TopicFixture(
        name="Newton's Second Law",
        description="Simple, well-known physics law",
        expected_domain="physics.class-ph",
        expected_theory_status="current",
        has_historical_context=True,
        requires_new_assumptions=False,
        has_missing_dependencies=False,
    ),
    "hookes_law": TopicFixture(
        name="Hooke's Law",
        description="Simple spring force law",
        expected_domain="physics.class-ph",
        expected_theory_status="current",
        has_historical_context=True,
        requires_new_assumptions=False,
        has_missing_dependencies=False,
    ),
}

# Topics that should have historical context
HISTORICAL_TOPICS = {
    "newtonian_mechanics": TopicFixture(
        name="Newtonian Mechanics",
        description="Historical framework for classical mechanics",
        expected_domain="physics.class-ph",
        expected_theory_status="historical",
        has_historical_context=True,
        requires_new_assumptions=False,
        has_missing_dependencies=False,
    ),
    "ptolemaic_system": TopicFixture(
        name="Ptolemaic System",
        description="Historical geocentric model",
        expected_domain="physics.hist-ph",
        expected_theory_status="historical",
        has_historical_context=True,
        requires_new_assumptions=False,
        has_missing_dependencies=False,
    ),
}

# Topics that might require new assumptions
TOPICS_WITH_NEW_ASSUMPTIONS = {
    "quantum_entanglement": TopicFixture(
        name="Quantum Entanglement",
        description="Might need quantum-specific assumptions",
        expected_domain="quant-ph",
        expected_theory_status="current",
        has_historical_context=False,
        requires_new_assumptions=True,
        has_missing_dependencies=False,
    ),
}

# Topics that have missing dependencies (need foundational entries first)
TOPICS_WITH_MISSING_DEPS = {
    "quantum_harmonic_oscillator": TopicFixture(
        name="Quantum Harmonic Oscillator",
        description="Depends on harmonic oscillator entry",
        expected_domain="quant-ph",
        expected_theory_status="current",
        has_historical_context=False,
        requires_new_assumptions=False,
        has_missing_dependencies=True,
    ),
    "schwarzschild_metric": TopicFixture(
        name="Schwarzschild Metric",
        description="Depends on general relativity foundations",
        expected_domain="gr-qc",
        expected_theory_status="current",
        has_historical_context=False,
        requires_new_assumptions=False,
        has_missing_dependencies=True,
    ),
}

# Complex topics for integration testing
COMPLEX_TOPICS = {
    "maxwells_equations": TopicFixture(
        name="Maxwell's Equations",
        description="Complete set of electromagnetic equations",
        expected_domain="physics.class-ph",
        expected_theory_status="current",
        has_historical_context=True,
        requires_new_assumptions=False,
        has_missing_dependencies=False,
    ),
    "schrodinger_equation": TopicFixture(
        name="Schrödinger Equation",
        description="Fundamental equation of quantum mechanics",
        expected_domain="quant-ph",
        expected_theory_status="current",
        has_historical_context=True,
        requires_new_assumptions=False,
        has_missing_dependencies=False,
    ),
}

# All topics combined
ALL_TOPICS = {
    **SIMPLE_TOPICS,
    **HISTORICAL_TOPICS,
    **TOPICS_WITH_NEW_ASSUMPTIONS,
    **TOPICS_WITH_MISSING_DEPS,
    **COMPLEX_TOPICS,
}
