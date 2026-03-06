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

Web Context (Full):
{info_output.raw_web_content}

Assumptions:
{assumptions_deps_output.assumptions}

Please define the result equations and all symbols using correct AsciiMath notation.
"""

        # Build prompt with guidelines from theoria-dataset
        guidelines = self.get_guidelines()
        prompt = self.get_prompt().format(guidelines=guidelines)

        # Get LLM response
        messages = self.build_messages(user_message, prompt)

        response = await self.llm_client.complete_json(messages)

        # Parse JSON response into Pydantic model
        result = await self.parse_json_response(response, EquationsSymbolsOutput)

        return result
