"""Tests for Pydantic models."""

import pytest
from src.models import (
    TheoriaEntry,
    Equation,
    Definition,
    DerivationStep,
    ProgrammaticVerification,
    Reference,
    Contributor,
)


def test_equation_model():
    """Test Equation model validation."""
    eq = Equation(id="eq1", equation="E = m*c^2", equation_title="Mass-energy equivalence")
    assert eq.id == "eq1"
    assert eq.equation_title == "Mass-energy equivalence"


def test_definition_model():
    """Test Definition model validation."""
    defn = Definition(symbol="c", definition="Speed of light in vacuum")
    assert defn.symbol == "c"


def test_derivation_step_model():
    """Test DerivationStep model validation."""
    step = DerivationStep(
        step=1,
        description="Start from first principles",
        equation="F = m*a",
        assumptions=["newtons_laws"],
    )
    assert step.step == 1
    assert "newtons_laws" in step.assumptions


def test_programmatic_verification_model():
    """Test ProgrammaticVerification model validation."""
    pv = ProgrammaticVerification(
        language="Python 3.11.12",
        library="sympy 1.13.1",
        code=["import sympy as sp", "x = sp.Symbol('x')"],
    )
    assert len(pv.code) == 2


def test_minimal_entry():
    """Test minimal valid TheoriaEntry."""
    entry = TheoriaEntry(
        result_id="test_entry",
        result_name="Test Entry",
        result_equations=[Equation(id="eq1", equation="x = 1")],
        explanation="A test entry for validation.",
        definitions=[Definition(symbol="x", definition="A variable")],
        assumptions=[],
        depends_on=[],
        derivation=[
            DerivationStep(step=1, description="Define x", equation="x = 1")
        ],
        programmatic_verification=ProgrammaticVerification(
            language="Python 3.11.12",
            library="sympy 1.13.1",
            code=["x = 1", "assert x == 1"],
        ),
        domain="math-ph",
        theory_status="current",
        references=[Reference(id="R1", citation="Test (2024). Test Paper.")],
        contributors=[Contributor(full_name="Test", identifier="test@test.com")],
        review_status="draft",
    )
    assert entry.result_id == "test_entry"
    assert entry.review_status == "draft"
