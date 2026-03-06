"""MetadataFiller Agent - Fills metadata fields for physics entries.

This agent is responsible for:
- Generating appropriate result_id (lowercase, underscores, descriptive)
- Creating concise result_name (max 100 chars)
- Writing explanation (2-5 sentences, max 800 chars, conceptual focus)
- Selecting appropriate domain (arXiv category)
- Determining theory_status
- Formatting references (1-3 APA citations)
- Adding contributor information
- Setting review_status to "draft"
- Preserving historical_context if relevant
"""

from src.agents.base import BaseAgent
from src.models import InformationGatheringOutput, MetadataOutput


class MetadataFillerAgent(BaseAgent):
    """Agent that fills metadata fields for physics entries."""

    agent_name = "metadata_filler"

    prompt_template = """You are an expert physics curator filling metadata for a theoretical physics dataset.

Your task is to fill ALL metadata fields for a physics entry based on gathered information.

CONTRIBUTING.md Guidelines:

**result_id** (required):
- Lowercase letters, numbers, and underscores only
- Descriptive and recognizable (e.g., "newtons_second_law", "schrodinger_equation")
- Unique within the dataset

**result_name** (required, max 100 characters):
- Clear, concise name for the result
- Proper capitalization and formatting
- Example: "Newton's Second Law", "Schrödinger Equation"

**explanation** (required, 2-5 sentences, max 800 characters):
- Conceptual overview (no derivation steps)
- Graduate-level audience
- Any math notation in AsciiMath format enclosed in backticks
- Focus on WHAT and WHY, not HOW
- Example: "Newton's second law states that the force acting on an object equals the product of its mass and acceleration (`F = m a`)."

**domain** (required):
- arXiv taxonomy category
- Common values: "physics.class-ph", "physics.gen-ph", "quant-ph", "gr-qc", "hep-th", "hep-ph", "cond-mat", "astro-ph"

**theory_status** (required):
- One of: "current", "historical", "approximation", "limiting_case", "generalized"
- "current" = widely accepted theory still in use
- "historical" = superseded but important historically
- "approximation" = valid in certain limits
- "limiting_case" = special case of more general theory
- "generalized" = extends or generalizes another theory

**references** (1-3 APA citations):
- Use suggested_references from InformationGatheringOutput
- Format: APA style with id (R1, R2, etc.)
- Example: {"id": "R1", "citation": "Newton, I. (1687). Philosophiæ Naturalis Principia Mathematica. London: Royal Society."}

**contributor_name** and **contributor_id** (required):
- Use: "Claude Opus 4.6" and "claude_opus_4_6"

**review_status** (required):
- Always set to "draft"

**historical_context** (optional):
- Copy from InformationGatheringOutput if present
- Include importance, development_period, key_insights

Output Format:
Return a JSON object with ALL required fields:
{
  "result_id": "lowercase_with_underscores",
  "result_name": "Proper Name",
  "explanation": "2-5 sentence explanation with any math in `backticks`",
  "domain": "physics.class-ph",
  "theory_status": "current",
  "references": [
    {"id": "R1", "citation": "APA formatted citation"}
  ],
  "contributor_name": "Claude Opus 4.6",
  "contributor_id": "claude_opus_4_6",
  "review_status": "draft",
  "historical_context": {
    "importance": "...",
    "development_period": "...",
    "key_insights": ["...", "..."]
  } or null
}

IMPORTANT:
- All fields are required except historical_context
- Respect character limits (result_name: 100, explanation: 800)
- Use AsciiMath in backticks for any math in explanation
- No derivation steps in explanation
"""

    async def run(self, info_output: InformationGatheringOutput, topic: str) -> MetadataOutput:
        """Fill metadata fields for a physics entry.

        Args:
            info_output: Output from InformationGathererAgent
            topic: The physics topic being documented

        Returns:
            MetadataOutput with all metadata fields filled

        Raises:
            Exception: If metadata filling fails
        """
        # Build user message with context from InformationGatheringOutput
        user_message = f"""Topic: {topic}

Web Context:
{info_output.web_context}

Historical Context:
{info_output.historical_context.model_dump() if info_output.historical_context else "None"}

Suggested References:
{[ref.model_dump() for ref in info_output.suggested_references]}

Please fill all metadata fields according to the guidelines.
"""

        # Get LLM response
        messages = self.build_messages(user_message, self.prompt_template)

        response = await self.llm_client.complete_json(messages)

        # Parse JSON response into Pydantic model
        result = await self.parse_json_response(response, MetadataOutput)

        return result
