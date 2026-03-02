"""Reviewer agent for quality checking and self-correction."""

import json
from typing import Any

from src.agents.base import BaseAgent
from src.models import ReviewResult, TheoriaEntry


class ReviewerAgent(BaseAgent):
    """Agent that reviews entries and makes corrections."""

    agent_name = "reviewer"

    def __init__(self, max_correction_loops: int = 3, **kwargs: Any):
        super().__init__(**kwargs)
        self.max_correction_loops = max_correction_loops

    async def run(self, entry: TheoriaEntry) -> ReviewResult:
        """Review an entry and correct issues if found.

        Args:
            entry: The entry to review.

        Returns:
            ReviewResult with pass/fail status and potentially corrected entry.
        """
        current_entry = entry
        all_issues: list[str] = []

        for iteration in range(self.max_correction_loops):
            # Review the current entry
            review = await self._review_entry(current_entry)

            if review["passed"]:
                return ReviewResult(
                    passed=True,
                    issues=all_issues,
                    corrected_entry=current_entry if iteration > 0 else None,
                )

            # Collect issues
            issues = review.get("issues", [])
            all_issues.extend(issues)

            # Attempt to correct
            corrected = await self._correct_entry(current_entry, issues)
            if corrected:
                current_entry = corrected
            else:
                # Couldn't correct, return with issues
                break

        # Max iterations reached or couldn't correct
        return ReviewResult(
            passed=False,
            issues=all_issues,
            corrected_entry=current_entry if current_entry != entry else None,
        )

    async def _review_entry(self, entry: TheoriaEntry) -> dict[str, Any]:
        """Review an entry for quality issues.

        Args:
            entry: Entry to review.

        Returns:
            Dict with "passed" bool and "issues" list.
        """
        # Load guidelines dynamically from theoria-dataset
        guidelines = self.get_guidelines()

        system_prompt = f"""You are a rigorous physics peer reviewer.

{guidelines}

Review entries against these guidelines and identify any issues."""

        user_prompt = f"""Review the following theoria-dataset entry for quality issues.

## Entry
```json
{entry.model_dump_json(indent=2)}
```

Check against ALL requirements in the guidelines above.

## Output Format
```json
{{
  "passed": true/false,
  "issues": [
    "Issue 1 description",
    "Issue 2 description"
  ]
}}
```
"""
        messages = self.build_messages(user_prompt, system_prompt)
        response = await self.llm_client.complete_json(messages)

        return json.loads(self._extract_json(response))

    async def _correct_entry(
        self, entry: TheoriaEntry, issues: list[str]
    ) -> TheoriaEntry | None:
        """Attempt to correct issues in an entry.

        Args:
            entry: Entry to correct.
            issues: List of issues to fix.

        Returns:
            Corrected entry, or None if correction failed.
        """
        # Load guidelines for correction context
        guidelines = self.get_guidelines()

        system_prompt = f"""You are a physics editor correcting dataset entries.

{guidelines}

Fix issues according to the guidelines. Keep correct content unchanged."""

        user_prompt = f"""Fix these issues in the entry, following the guidelines above.

## Entry
```json
{entry.model_dump_json(indent=2, exclude_none=True)}
```

## Issues to Fix
{chr(10).join(f"- {issue}" for issue in issues)}

Return ONLY the complete corrected JSON entry.
"""
        messages = self.build_messages(user_prompt, system_prompt)

        try:
            response = await self.llm_client.complete_json(messages, max_tokens=8192)
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            return TheoriaEntry.model_validate(data)
        except Exception:
            return None

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
