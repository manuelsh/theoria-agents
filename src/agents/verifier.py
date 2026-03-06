"""Verifier agent for generating and testing SymPy verification code."""

import asyncio
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from src.agents.base import BaseAgent
from src.models import DerivationOutput, VerifierOutput, ProgrammaticVerification


class VerifierAgent(BaseAgent):
    """Agent that generates SymPy verification code for derivations."""

    agent_name = "verifier"

    async def run(self, derivation: DerivationOutput) -> VerifierOutput:
        """Generate verification code for a derivation.

        Args:
            derivation: Output from the Derivation agent.

        Returns:
            VerifierOutput with code and execution results.
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(derivation)

        messages = self.build_messages(user_prompt, system_prompt)
        response = await self.llm_client.complete_json(messages)

        # Parse the response
        data = json.loads(self._extract_json(response))
        code_lines = data.get("code", [])

        if isinstance(code_lines, str):
            code_lines = code_lines.split("\n")

        verification = ProgrammaticVerification(
            language="python 3.11.12",
            library="sympy 1.13.1",
            code=code_lines,
        )

        # Execute the code to verify it works
        success, output = await self._execute_code(code_lines)

        return VerifierOutput(
            programmatic_verification=verification,
            execution_success=success,
            execution_output=output,
        )

    def _extract_json(self, response: str) -> str:
        """Extract JSON from response."""
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            return response[start:end].strip()
        elif "```" in response:
            start = response.find("```") + 3
            end = response.find("```", start)
            return response[start:end].strip()
        return response

    def _build_system_prompt(self) -> str:
        """Build the system prompt with verification guidelines from theoria-dataset."""
        # Load guidelines dynamically
        guidelines = self.get_guidelines()

        # Load example verification code
        example = self.dataset.load_example_entry()
        example_code = example["programmatic_verification"]["code"][:30]

        return f"""You are creating programmatic_verification for a theoria-dataset entry.

{guidelines}

## Example (from Schrödinger equation entry)
```python
{chr(10).join(example_code)}
```"""

    def _build_user_prompt(self, derivation: DerivationOutput) -> str:
        """Build the user prompt with derivation context only."""
        # Format the derivation steps
        steps_text = []
        for step in derivation.derivation:
            steps_text.append(
                f"Step {step.step}: {step.description}\n"
                f"  Equation: {step.equation}"
            )

        return f"""Generate programmatic_verification code for this derivation.

## Result Equations
{json.dumps([eq.model_dump() for eq in derivation.result_equations], indent=2)}

## Definitions
{json.dumps([d.model_dump() for d in derivation.definitions], indent=2)}

## Derivation Steps
{chr(10).join(steps_text)}

## Required Output
Follow the programmatic_verification requirements from the guidelines above.

```json
{{
  "code": [
    "import sympy as sp",
    "# Step 1: ...",
    "..."
  ]
}}
```
"""

    async def _execute_code(self, code_lines: list[str]) -> tuple[bool, str]:
        """Execute the verification code and return results.

        Args:
            code_lines: Lines of Python code to execute.

        Returns:
            Tuple of (success, output_or_error).
        """
        code = "\n".join(code_lines)

        # Write to temp file
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False
        ) as f:
            f.write(code)
            temp_path = f.name

        try:
            # Run the code
            result = await asyncio.to_thread(
                subprocess.run,
                [sys.executable, temp_path],
                capture_output=True,
                text=True,
                timeout=60,
            )

            if result.returncode == 0:
                return True, result.stdout or "Verification passed"
            else:
                return False, result.stderr or result.stdout or "Unknown error"

        except subprocess.TimeoutExpired:
            return False, "Execution timed out (60s limit)"
        except Exception as e:
            return False, str(e)
        finally:
            Path(temp_path).unlink(missing_ok=True)

