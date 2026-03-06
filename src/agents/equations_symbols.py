"""EquationsSymbols Agent - Defines result equations and symbols.

This agent is responsible for:
- Identifying the main result equations
- Writing equations in AsciiMath format
- Generating equation IDs (eq1, eq2, etc.)
- Defining ALL symbols used in equations
- Ensuring AsciiMath notation correctness
"""

from src.agents.base import BaseAgent
from src.models import (
    AssumptionsDependenciesOutput,
    EquationsSymbolsOutput,
    InformationGatheringOutput,
    MetadataOutput,
)


class EquationsSymbolsAgent(BaseAgent):
    """Agent that defines result equations and symbols."""

    agent_name = "equations_symbols"

    prompt_template = """You are an expert physics curator defining equations and symbols for a theoretical physics dataset.

Your task is to:
1. Identify the main result equations
2. Write them in correct AsciiMath notation
3. Define EVERY symbol used

AsciiMath Notation Rules (CRITICAL):
- **Fractions**: Use parentheses: `(numerator)/(denominator)` NOT `numerator/denominator`
  - Example: `(dx)/(dt)` NOT `dx/dt`
  - Example: `(1)/(2)` NOT `1/2`
- **Partial derivatives**: `(del f)/(del x)` NOT `del f/del x`
- **Subscripts (single char)**: `E_k` is OK
- **Subscripts (multi-char)**: Use parentheses: `E_(kinetic)` NOT `E_kinetic`
- **Avoid reserved words**: Never use `_to`, `_in`, etc. as subscripts (they render as arrows/operators)
  - Use `_0`, `_1`, `_initial`, `_final` instead
- **Superscripts**: `x^2`, `x^(n+1)`
- **Summation**: `sum_(i=1)^n x_i`
- **Square roots**: `sqrt(x)`
- **Greek letters**: `alpha`, `beta`, `gamma`, etc.

Output Format:
Return a JSON object:
{{{{
  "result_equations": [
    {{{{
      "id": "eq1",
      "equation": "F = m a",
      "equation_title": "Newton's Second Law"
    }}}}
  ],
  "definitions": [
    {{{{
      "symbol": "F",
      "definition": "Force applied to the object (in newtons)"
    }}}},
    {{{{
      "symbol": "m",
      "definition": "Mass of the object (in kilograms)"
    }}}},
    {{{{
      "symbol": "a",
      "definition": "Acceleration of the object (in meters per second squared)"
    }}}}
  ]
}}}}

IMPORTANT:
- At least one equation required
- At least one definition required
- Define EVERY symbol that appears in equations
- Use correct AsciiMath notation (parentheses in fractions!)
- Symbol definitions should be clear and include units when applicable
- Math in definitions should use backticks + AsciiMath
- equation_title is optional for equations
"""

    async def run(
        self,
        info_output: InformationGatheringOutput,
        metadata_output: MetadataOutput,
        assumptions_deps_output: AssumptionsDependenciesOutput,
    ) -> EquationsSymbolsOutput:
        """Define equations and symbols for a physics entry.

        Args:
            info_output: Output from InformationGathererAgent
            metadata_output: Output from MetadataFillerAgent
            assumptions_deps_output: Output from AssumptionsDependenciesAgent

        Returns:
            EquationsSymbolsOutput with equations and symbol definitions

        Raises:
            Exception: If equation/symbol definition fails
        """
        # Build user message with context
        user_message = f"""Entry: {metadata_output.result_name} (ID: {metadata_output.result_id})

Domain: {metadata_output.domain}

Explanation:
{metadata_output.explanation}

Web Context:
{info_output.web_context}

Assumptions:
{assumptions_deps_output.assumptions}

Please define the result equations and all symbols using correct AsciiMath notation.
"""

        # Get LLM response
        messages = self.build_messages(user_message, self.prompt_template)

        response = await self.llm_client.complete_json(messages)

        # Parse JSON response into Pydantic model
        result = await self.parse_json_response(response, EquationsSymbolsOutput)

        return result
