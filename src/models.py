"""Pydantic models for theoria-dataset entries and agent outputs."""

from pydantic import BaseModel, Field


# === Entry Schema Models ===


class Equation(BaseModel):
    """A single equation in the result_equations array."""

    id: str = Field(..., description="Unique short tag for the equation (e.g., 'eq1')")
    equation: str = Field(..., description="AsciiMath representation of the equation")
    equation_title: str | None = Field(
        None, description="Optional human-readable title (e.g., 'Newton's Second Law')"
    )


class Definition(BaseModel):
    """A symbol definition."""

    symbol: str = Field(..., description="Symbol in AsciiMath format")
    definition: str = Field(..., description="Definition of the symbol")


class DerivationStep(BaseModel):
    """A single step in the derivation."""

    step: int = Field(..., ge=1, description="Step number (sequential)")
    description: str = Field(..., description="Textual rationale for this step")
    equation: str = Field(..., description="AsciiMath equation for this step")
    equation_proven: str | None = Field(
        None, description="ID of equation from result_equations that this step proves"
    )
    assumptions: list[str] | None = Field(
        None, description="Assumption IDs invoked in this step"
    )


class ProgrammaticVerification(BaseModel):
    """Python/SymPy verification code."""

    language: str = Field("Python 3.11.12", pattern=r"^[A-Za-z]+\s\d+\.\d+\.\d+$")
    library: str = Field("sympy 1.13.1", pattern=r"^(none|[A-Za-z0-9_]+\s\d+\.\d+\.\d+)$")
    code: list[str] = Field(..., min_length=1, description="Lines of verification code")


class Reference(BaseModel):
    """Academic citation."""

    id: str = Field(..., description="Reference ID (e.g., 'R1')")
    citation: str = Field(..., description="APA format citation")


class Contributor(BaseModel):
    """Entry contributor."""

    full_name: str
    identifier: str = Field(..., description="ORCID, website, or other identifier")


class HistoricalContext(BaseModel):
    """Historical context for the theory."""

    importance: str | None = None
    development_period: str | None = None
    key_insights: list[str] | None = None


class TheoriaEntry(BaseModel):
    """Complete theoria-dataset entry."""

    result_id: str = Field(..., pattern=r"^[a-z0-9_]+$")
    result_name: str = Field(..., max_length=100)
    result_equations: list[Equation] = Field(..., min_length=1)
    explanation: str = Field(..., max_length=800)
    definitions: list[Definition] = Field(..., min_length=1)
    assumptions: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    derivation: list[DerivationStep] = Field(..., min_length=1)
    programmatic_verification: ProgrammaticVerification
    domain: str = Field(..., pattern=r"^[a-z][a-z\-\.]+$")
    theory_status: str = Field(
        ..., pattern=r"^(current|historical|approximation|limiting_case|generalized)$"
    )
    generalized_by: list[str] | None = None
    historical_context: HistoricalContext | None = None
    references: list[Reference] = Field(..., min_length=1, max_length=3)
    contributors: list[Contributor] = Field(..., min_length=1)
    review_status: str = Field("draft", pattern=r"^(draft|reviewed)$")


# === Agent Output Models ===


class ProposedAssumption(BaseModel):
    """A new assumption proposed by the Researcher agent."""

    id: str = Field(..., pattern=r"^[a-z0-9_]+$", description="Unique ID for the assumption")
    title: str = Field(..., max_length=100, description="Short title")
    text: str = Field(..., max_length=1000, description="Description of the assumption")
    type: str = Field(..., pattern=r"^(principle|empirical|approximation)$")
    mathematical_expressions: list[str] | None = Field(
        None, description="Optional mathematical expressions in AsciiMath"
    )
    symbol_definitions: list[Definition] | None = Field(
        None, description="Required if mathematical_expressions is provided"
    )


class ResearchOutput(BaseModel):
    """Output from the Researcher agent."""

    result_id: str = Field(..., description="Proposed entry ID")
    result_name: str = Field(..., description="Proposed entry name")
    depends_on: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(
        default_factory=list, description="IDs of existing assumptions to use"
    )
    new_assumptions: list[ProposedAssumption] = Field(
        default_factory=list, description="New assumptions that need to be created"
    )
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
    execution_success: bool = Field(..., description="Whether the code executed without errors")
    execution_output: str | None = Field(None, description="Output or error from execution")


class ReviewResult(BaseModel):
    """Output from the Reviewer agent."""

    passed: bool = Field(..., description="Whether the entry passed all quality checks")
    issues: list[str] = Field(default_factory=list, description="List of issues found")
    corrected_entry: TheoriaEntry | None = Field(
        None, description="Corrected entry if issues were found and fixed"
    )
