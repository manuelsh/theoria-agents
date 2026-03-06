"""Agent implementations for the theoria-agents pipeline."""

from .base import BaseAgent
from .information_gatherer import InformationGathererAgent
from .metadata_filler import MetadataFillerAgent
from .assumptions_dependencies import AssumptionsDependenciesAgent
from .equations_symbols import EquationsSymbolsAgent
from .researcher import ResearcherAgent  # Legacy - to be removed
from .derivation import DerivationAgent
from .verifier import VerifierAgent
from .assembler import AssemblerAgent
from .reviewer import ReviewerAgent

__all__ = [
    "BaseAgent",
    "InformationGathererAgent",
    "MetadataFillerAgent",
    "AssumptionsDependenciesAgent",
    "EquationsSymbolsAgent",
    "ResearcherAgent",  # Legacy
    "DerivationAgent",
    "VerifierAgent",
    "AssemblerAgent",
    "ReviewerAgent",
]
