"""Prompt loading and management system.

This module provides centralized prompt loading for all agents,
replacing hardcoded prompt_template strings with external markdown files.
"""

from prompts.loader import PromptLoader
from prompts.registry import PromptRegistry

__all__ = ["PromptLoader", "PromptRegistry"]
