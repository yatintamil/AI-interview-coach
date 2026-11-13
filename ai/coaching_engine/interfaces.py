"""
Interfaces and Protocols for Coaching Intervention Policy and Scaffold Fading components.
Enforces decoupling between scaffold transitions, intervention selection, and policy execution.
"""

from typing import Protocol, Tuple, List, Optional, runtime_checkable
from backend.domain.transfer.coaching_types import CoachingInterventionType, ScaffoldLevel
from ai.coaching_engine.schemas import (
    CoachingPolicyInput,
    CoachingHistoryEntry,
    ScaffoldState,
    CoachingPolicyDecision,
    CoachingValidationResult,
)


@runtime_checkable
class IScaffoldManager(Protocol):
    """Protocol for managing scaffold level transitions and computing assistance dependency."""

    def compute_scaffold_transition(
        self,
        current_level: ScaffoldLevel,
        last_outcome: Optional[str],
        history: List[CoachingHistoryEntry],
    ) -> ScaffoldState:
        """Determines the appropriate scaffold level and tracks fading / escalation."""
        ...

    def calculate_assistance_dependency_index(
        self, history: List[CoachingHistoryEntry]
    ) -> float:
        """Calculates deterministic assistance dependency metric in [0.0, 1.0]."""
        ...


@runtime_checkable
class IInterventionSelector(Protocol):
    """Protocol for selecting minimum effective intervention given diagnosis and scaffold level."""

    def select_intervention(
        self, input_data: CoachingPolicyInput, target_scaffold: ScaffoldLevel
    ) -> Tuple[CoachingInterventionType, str]:
        """Returns the selected intervention type and pedagogical intent string."""
        ...


@runtime_checkable
class ICoachingPolicy(Protocol):
    """Protocol for the top-level coaching policy engine."""

    def decide(self, input_data: CoachingPolicyInput) -> CoachingPolicyDecision:
        """Executes policy logic and returns a validated CoachingPolicyDecision."""
        ...


@runtime_checkable
class ICoachingValidator(Protocol):
    """Protocol for validating that policy decisions satisfy pedagogical constraints."""

    def validate_decision(
        self, input_data: CoachingPolicyInput, decision: CoachingPolicyDecision
    ) -> CoachingValidationResult:
        """Validates that scaffold levels and intervention types are consistent and grounded."""
        ...
