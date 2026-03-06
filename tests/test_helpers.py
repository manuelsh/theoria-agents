"""Test helpers for prompt migration validation.

Provides utilities for:
- Comparing agent outputs
- Mock LLM clients for deterministic testing
- Performance benchmarking
"""

import json
import time
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock

from pydantic import BaseModel


class DeterministicMockLLM:
    """Mock LLM client that returns deterministic responses."""

    def __init__(self, responses: Dict[str, str]):
        """Initialize with a mapping of agent_name -> response JSON."""
        self.responses = responses
        self.call_count = 0

    async def complete_json(self, messages: list[dict], **kwargs) -> str:
        """Return deterministic JSON response based on agent context."""
        self.call_count += 1

        # Extract agent name from system message
        agent_name = "unknown"
        for msg in messages:
            if msg.get("role") == "system":
                content = msg.get("content", "")
                if "information_gatherer" in content.lower() or "information gathering" in content.lower():
                    agent_name = "information_gatherer"
                elif "metadata" in content.lower():
                    agent_name = "metadata_filler"
                elif "assumptions" in content.lower() or "dependencies" in content.lower():
                    agent_name = "assumptions_dependencies"
                elif "equations" in content.lower() or "symbols" in content.lower():
                    agent_name = "equations_symbols"
                break

        response = self.responses.get(agent_name, '{"error": "No mock response configured"}')
        return response


def compare_agent_outputs(output1: BaseModel, output2: BaseModel, tolerance: float = 0.0) -> tuple[bool, list[str]]:
    """Compare two agent outputs for equivalence.

    Args:
        output1: First output to compare
        output2: Second output to compare
        tolerance: Tolerance for numeric comparisons (0.0 = exact match)

    Returns:
        Tuple of (matches: bool, differences: list[str])
    """
    differences = []

    dict1 = output1.model_dump()
    dict2 = output2.model_dump()

    # Compare keys
    keys1 = set(dict1.keys())
    keys2 = set(dict2.keys())

    if keys1 != keys2:
        missing_in_2 = keys1 - keys2
        missing_in_1 = keys2 - keys1
        if missing_in_2:
            differences.append(f"Keys in output1 but not output2: {missing_in_2}")
        if missing_in_1:
            differences.append(f"Keys in output2 but not output1: {missing_in_1}")

    # Compare values for common keys
    common_keys = keys1 & keys2
    for key in common_keys:
        val1 = dict1[key]
        val2 = dict2[key]

        if type(val1) != type(val2):
            differences.append(f"Key '{key}': type mismatch ({type(val1).__name__} vs {type(val2).__name__})")
        elif val1 != val2:
            differences.append(f"Key '{key}': value mismatch ({val1} vs {val2})")

    return len(differences) == 0, differences


def benchmark_agent_init(agent_class, iterations: int = 100) -> Dict[str, float]:
    """Benchmark agent initialization time.

    Args:
        agent_class: Agent class to benchmark
        iterations: Number of iterations to run

    Returns:
        Dict with timing statistics (mean, min, max, total)
    """
    times = []

    for _ in range(iterations):
        start = time.perf_counter()
        try:
            agent = agent_class()
        except Exception:
            # Might fail without proper config, that's ok for timing
            pass
        end = time.perf_counter()
        times.append((end - start) * 1000)  # Convert to ms

    return {
        "mean_ms": sum(times) / len(times),
        "min_ms": min(times),
        "max_ms": max(times),
        "total_ms": sum(times),
        "iterations": iterations,
    }


def create_mock_config() -> Dict[str, Any]:
    """Create a standard mock configuration for testing."""
    return {
        "agent_models": {
            "information_gatherer": "fast",
            "metadata_filler": "fast",
            "assumptions_dependencies": "best",
            "equations_symbols": "best",
            "derivation": "best",
            "verifier": "best",
            "assembler": "fast",
            "reviewer": "best",
        },
        "models": {
            "fast": "mock-fast-model",
            "best": "mock-best-model",
        },
        "theoria_dataset_path": "/mock/dataset/path",
        "aws_region": "us-east-1",
    }


def create_mock_llm_client(responses: Dict[str, str] | None = None) -> MagicMock:
    """Create a mock LLM client for testing.

    Args:
        responses: Optional dict of agent_name -> JSON response

    Returns:
        Mock LLM client with complete_json method
    """
    mock_client = MagicMock()

    if responses:
        mock_llm = DeterministicMockLLM(responses)
        mock_client.complete_json = mock_llm.complete_json
    else:
        mock_client.complete_json = AsyncMock()

    return mock_client


def assert_valid_prompt(prompt: str) -> list[str]:
    """Validate a prompt string and return list of issues.

    Args:
        prompt: Prompt string to validate

    Returns:
        List of validation issues (empty if valid)
    """
    issues = []

    if not prompt or not prompt.strip():
        issues.append("Prompt is empty")
        return issues

    # Check for common issues
    if len(prompt) < 50:
        issues.append("Prompt suspiciously short (< 50 chars)")

    if "{{" in prompt or "}}" in prompt:
        issues.append("Contains unresolved template variables")

    if "@include" in prompt:
        issues.append("Contains unresolved @include directive")

    # Check for basic structure
    if "task" not in prompt.lower() and "role" not in prompt.lower():
        issues.append("Missing task/role description")

    if "output" not in prompt.lower() and "format" not in prompt.lower():
        issues.append("Missing output format specification")

    return issues
