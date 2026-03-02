"""Pydantic models for agent inputs and outputs.

These models are used for structured LLM responses and internal data flow.
Final entry validation happens against theoria-dataset's JSON schema via src/validation.py.
"""

from typing import Any

from pydantic import BaseModel, Field


# === Shared Data Structures ===
# These are used by multiple agents and match theoria-dataset structure.
# They are intentionally minimal - full validation happens via JSON schema.


class Equation(BaseModel):
    """A single equation in the result_equations array."""

    id: str
    equation: str
    equation_title: str | None = None


class Definition(BaseModel):
    """A symbol definition."""

    symbol: str
    definition: str


class DerivationStep(BaseModel):
    """A single step in the derivation."""

    step: int
    description: str
    equation: str
    equation_proven: str | None = None
    assumptions: list[str] | None = None


class ProgrammaticVerification(BaseModel):
    """Python/SymPy verification code."""

    language: str = "Python 3.11.12"
    library: str = "sympy 1.13.1"
    code: list[str]


class Reference(BaseModel):
    """Academic citation."""

    id: str
    citation: str


class Contributor(BaseModel):
    """Entry contributor."""

    full_name: str
    identifier: str


class HistoricalContext(BaseModel):
    """Historical context for the theory."""

    importance: str | None = None
    development_period: str | None = None
    key_insights: list[str] | None = None


# === Agent Output Models ===


class ProposedAssumption(BaseModel):
    """A new assumption proposed by the Researcher agent."""

    id: str = Field(..., description="Unique ID for the assumption")
    title: str = Field(..., description="Short title")
    text: str = Field(..., description="Description of the assumption")
    type: str = Field(..., description="One of: principle, empirical, approximation")
    mathematical_expressions: list[str] | None = None
    symbol_definitions: list[Definition] | None = None


class ResearchOutput(BaseModel):
    """Output from the Researcher agent."""

    result_id: str
    result_name: str
    depends_on: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    new_assumptions: list[ProposedAssumption] = Field(default_factory=list)
    references: list[Reference] = Field(default_factory=list)
    domain: str
    theory_status: str
    historical_context: HistoricalContext | None = None
    web_context: str = Field(..., description="Gathered web research context")


class DerivationOutput(BaseModel):
    """Output from the Derivation agent."""

    result_equations: list[Equation]
    explanation: str
    definitions: list[Definition]
    derivation: list[DerivationStep]


class VerifierOutput(BaseModel):
    """Output from the Verifier agent."""

    programmatic_verification: ProgrammaticVerification
    execution_success: bool
    execution_output: str | None = None


class ReviewResult(BaseModel):
    """Output from the Reviewer agent."""

    passed: bool
    issues: list[str] = Field(default_factory=list)
    corrected_entry: Any | None = None  # TheoriaEntry, avoiding circular import


# === Entry Assembly ===


class TheoriaEntry(BaseModel):
    """Complete theoria-dataset entry for internal assembly.

    This model is used to construct entries from agent outputs.
    Final validation should use EntryValidator from src/validation.py
    which validates against the canonical JSON schema.
    """

    result_id: str
    result_name: str
    result_equations: list[Equation]
    explanation: str
    definitions: list[Definition]
    assumptions: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    derivation: list[DerivationStep]
    programmatic_verification: ProgrammaticVerification
    domain: str
    theory_status: str
    generalized_by: list[str] | None = None
    historical_context: HistoricalContext | None = None
    references: list[Reference]
    contributors: list[Contributor]
    review_status: str = "draft"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for JSON schema validation."""
        return self.model_dump(exclude_none=True)
