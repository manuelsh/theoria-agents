"""Reviewer agent for quality checking and self-correction."""

import json
import sys
from pathlib import Path
from typing import Any

from src.agents.base import BaseAgent
from src.models import ReviewResult, TheoriaEntry
from src.validation import EntryValidator


class ReviewerAgent(BaseAgent):
    """Agent that reviews entries and makes corrections."""

    agent_name = "reviewer"

    def __init__(self, max_correction_loops: int = 3, **kwargs: Any):
        super().__init__(**kwargs)
        self.max_correction_loops = max_correction_loops
        self.validator = EntryValidator(self.dataset.dataset_path)
        # Track iteration details for logging
        self.iteration_log: list[dict[str, Any]] = []

    async def run(self, entry: TheoriaEntry) -> ReviewResult:
        """Review an entry and correct issues if found.

        Args:
            entry: The entry to review.

        Returns:
            ReviewResult with pass/fail status and potentially corrected entry.
        """
        current_entry = entry
        all_issues: list[str] = []
        self.iteration_log = []
        failure_reason: str | None = None

        for iteration in range(self.max_correction_loops):
            iteration_num = iteration + 1
            self._current_iteration = iteration_num  # Track for LLM logging
            print(f"Review iteration {iteration_num}/{self.max_correction_loops}")

            # 1. LLM-based review
            review = await self._review_entry(current_entry)
            issues = review.get("issues", [])

            # 2. Dataset validation (schema + scripts)
            entry_dict = current_entry.model_dump(exclude_none=True)

            # Schema validation
            schema_errors = self.validator.validate(entry_dict)
            issues.extend([f"[SCHEMA] {e}" for e in schema_errors])

            # Script validation (make test-entry)
            script_ok, script_output = self.validator.run_dataset_validation(entry_dict)
            if not script_ok:
                issues.extend(self._parse_validation_output(script_output))

            # Log iteration details (for internal tracking)
            self.iteration_log.append({
                "iteration": iteration_num,
                "issues_found": len(issues),
                "issues": issues.copy(),
            })

            # Log to AgentLogger for persistence in markdown log
            if self.agent_logger:
                self.agent_logger.log_iteration(
                    iteration=iteration_num,
                    issues_found=len(issues),
                    issues=issues.copy(),
                    corrections_applied=False,  # Updated later if corrections succeed
                )

            if issues:
                print(f"  Found {len(issues)} issues in iteration {iteration_num}")
                for i, issue in enumerate(issues, 1):
                    print(f"    {i}. {issue}")

            # If no issues, we're done
            if not issues:
                self._log_contributing_suggestions(all_issues)
                return ReviewResult(
                    passed=True,
                    issues=all_issues,
                    corrected_entry=current_entry if iteration > 0 else None,
                )

            # Collect issues
            all_issues.extend(issues)

            # 3. Attempt to correct ALL issues (LLM + validation)
            corrected, correction_error = await self._correct_entry(current_entry, issues)
            if corrected:
                print(f"  Applied corrections in iteration {iteration_num}")
                current_entry = corrected
                self.iteration_log[-1]["corrections_applied"] = True
                # Update AgentLogger's iteration metadata
                if self.agent_logger and self.agent_logger.iteration_metadata:
                    self.agent_logger.iteration_metadata[-1]["corrections_applied"] = True

                # Check if stuck (same issues as previous iteration)
                if len(self.iteration_log) >= 2:
                    prev_issues = self.iteration_log[-2]["issues"]
                    is_stuck = await self._check_if_stuck(prev_issues, issues)
                    if is_stuck:
                        print("  No improvement detected (same underlying issues) - stopping review")
                        failure_reason = f"Stuck on same issues after {iteration_num} iterations - no further progress possible"
                        break
            else:
                # Couldn't correct, return with issues
                print(f"  Failed to apply corrections in iteration {iteration_num}: {correction_error}")
                self.iteration_log[-1]["corrections_applied"] = False
                failure_reason = f"Failed to generate valid corrections in iteration {iteration_num}: {correction_error}"
                break

        # Set failure reason if max iterations reached
        if failure_reason is None:
            failure_reason = f"Reached maximum iterations ({self.max_correction_loops}) with {len(self.iteration_log[-1]['issues'])} issues remaining"

        # Max iterations reached or couldn't correct
        self._log_contributing_suggestions(all_issues)
        return ReviewResult(
            passed=False,
            issues=all_issues,
            corrected_entry=current_entry if current_entry != entry else None,
            failure_reason=failure_reason,
            reviewer_state={
                "iteration_log": self.iteration_log,
                "max_correction_loops": self.max_correction_loops,
            },
        )

    def _generate_contributing_suggestions(self, issues: list[str]) -> list[str]:
        """Analyze issues and suggest CONTRIBUTING.md (entry.schema.json) improvements.

        Args:
            issues: List of all issues found during review.

        Returns:
            List of suggestions for improving theoria-dataset documentation.
        """
        suggestions = []

        # Pattern matching for common issues that indicate documentation gaps
        issue_text = " ".join(issues).lower()

        if any(
            ("assumption" in i.lower() and "not exist" in i.lower())
            or ("invalid assumption" in i.lower())
            for i in issues
        ):
            suggestions.append(
                "entry.schema.json suggestion: Ensure the assumptions description "
                "clearly states that all assumption IDs must exist in globals/assumptions.json"
            )

        if any(
            "step" in i.lower() and "after" in i.lower() and "proven" in i.lower()
            for i in issues
        ):
            suggestions.append(
                "entry.schema.json suggestion: Add rule to derivation description "
                "that derivation should end when all equations are proven"
            )

        if any("equation_title" in i.lower() and "missing" in i.lower() for i in issues):
            suggestions.append(
                "entry.schema.json suggestion: Emphasize that equation_title is required "
                "for all result_equations"
            )

        if any("reference" in i.lower() and "original" in i.lower() for i in issues):
            suggestions.append(
                "entry.schema.json suggestion: Add guidance about including seminal/original "
                "references for historical results"
            )

        if "variational_calculus_framework" in issue_text and issue_text.count(
            "variational_calculus_framework"
        ) > 3:
            suggestions.append(
                "entry.schema.json suggestion: Add guidance about using specific assumptions "
                "for each step rather than broad frameworks throughout"
            )

        return suggestions

    def _log_contributing_suggestions(self, all_issues: list[str]) -> None:
        """Log suggestions for improving CONTRIBUTING.md to stderr.

        Args:
            all_issues: All issues found during review.
        """
        suggestions = self._generate_contributing_suggestions(all_issues)
        if suggestions:
            print("\n" + "=" * 60, file=sys.stderr)
            print("CONTRIBUTING.md (entry.schema.json) Improvement Suggestions:", file=sys.stderr)
            print("=" * 60, file=sys.stderr)
            for suggestion in suggestions:
                print(f"  - {suggestion}", file=sys.stderr)
            print("=" * 60 + "\n", file=sys.stderr)

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

## Review Checklist

1. **Derivation Steps**: Check each step for correctness, proper assumptions, clear explanations
2. **Programmatic Verification**: Review the SymPy code to ensure:
   - It correctly defines all symbols used in the derivation
   - It actually verifies the key equations/transformations from the derivation
   - The verification logic is mathematically sound
   - The code aligns with what the derivation claims to prove
3. **Metadata**: Check result_id, result_name, domain, explanation, references
4. **Schema Compliance**: Check against ALL requirements in the guidelines above

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

    async def _check_if_stuck(
        self, prev_issues: list[str], current_issues: list[str]
    ) -> bool:
        """Use LLM to determine if the review is stuck on the same issues.

        Args:
            prev_issues: Issues from the previous iteration.
            current_issues: Issues from the current iteration.

        Returns:
            True if the issues are essentially the same (stuck), False if progress was made.
        """
        system_prompt = """You are analyzing review iterations to determine if progress is being made.
Compare the previous issues with the current issues and determine if they are essentially the same
underlying problems (just phrased differently) or if real progress was made (old issues fixed, new different issues found)."""

        user_prompt = f"""Compare these two sets of issues and determine if the review is stuck.

## Previous Iteration Issues
{chr(10).join(f"- {issue}" for issue in prev_issues)}

## Current Iteration Issues
{chr(10).join(f"- {issue}" for issue in current_issues)}

## Instructions
- If the current issues are essentially the same problems as before (even if worded differently), respond with {{"stuck": true}}
- If real progress was made (old issues were fixed and new different issues were found), respond with {{"stuck": false}}

Respond with ONLY a JSON object: {{"stuck": true}} or {{"stuck": false}}"""

        messages = self.build_messages(user_prompt, system_prompt)

        try:
            response = await self.llm_client.complete_json(messages, max_tokens=100)
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            return data.get("stuck", False)
        except Exception:
            # If we can't determine, assume not stuck and continue
            return False

    async def _correct_entry(
        self, entry: TheoriaEntry, issues: list[str]
    ) -> tuple[TheoriaEntry | None, str | None]:
        """Attempt to correct issues in an entry.

        Args:
            entry: Entry to correct.
            issues: List of issues to fix.

        Returns:
            Tuple of (corrected entry, error message). Entry is None if correction failed.
        """
        # Load guidelines for correction context
        guidelines = self.get_guidelines()

        # Get valid assumptions and entries for reference
        valid_assumptions = self.dataset.format_assumptions_for_prompt()
        valid_entries = self.dataset.format_entries_for_prompt()

        # Get schema for structure reference
        schema_json = json.dumps(self.dataset.schema, indent=2)

        system_prompt = f"""You are a physics editor correcting dataset entries.

{guidelines}

Fix issues according to the guidelines. Keep correct content unchanged.

IMPORTANT: Only use assumption IDs and dependency IDs that exist in the lists provided."""

        user_prompt = f"""Fix these issues in the entry, following the guidelines above.

## Entry
```json
{entry.model_dump_json(indent=2, exclude_none=True)}
```

## Issues to Fix
{chr(10).join(f"- {issue}" for issue in issues)}

## Valid Assumptions (only use IDs from this list)
{valid_assumptions}

## Valid Dependencies (only use IDs from this list for depends_on)
{valid_entries}

## JSON Schema Reference
```json
{schema_json}
```

Return ONLY the complete corrected JSON entry.
"""
        messages = self.build_messages(user_prompt, system_prompt)

        try:
            response = await self.llm_client.complete_json(messages, max_tokens=8192)
            json_str = self._extract_json(response)
            data = json.loads(json_str)
            return TheoriaEntry.model_validate(data), None
        except json.JSONDecodeError as e:
            return None, f"LLM returned invalid JSON: {e}"
        except Exception as e:
            return None, f"Entry validation failed: {e}"

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

    def _parse_validation_output(self, output: str) -> list[str]:
        """Extract individual issues from validation script output."""
        issues = []
        for line in output.split("\n"):
            line = line.strip()
            if "[ERROR]" in line or "[WARNING]" in line:
                issues.append(f"[VALIDATION] {line}")
        return issues

    def save_state(self, path: Path | str) -> None:
        """Save review state for later resume.

        Args:
            path: Path to save the state file.
        """
        path = Path(path)
        state = {
            "iterations_completed": len(self.iteration_log),
            "iteration_log": self.iteration_log,
            "last_issues": self.iteration_log[-1]["issues"] if self.iteration_log else [],
            "max_correction_loops": self.max_correction_loops,
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    @staticmethod
    def load_state(path: Path | str) -> dict[str, Any]:
        """Load review state from file.

        Args:
            path: Path to the state file.

        Returns:
            State dictionary with iteration_log and other metadata.
        """
        path = Path(path)
        with open(path, encoding="utf-8") as f:
            return json.load(f)
