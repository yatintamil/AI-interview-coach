"""
Interfaces and Protocols for Transfer-Aware Coaching Orchestration.
Enforces clean decoupling between orchestrator, state machine, and engine providers.
"""

from typing import Protocol, Optional, runtime_checkable
from ai.coaching_orchestrator.schemas import (
    CoachingSessionConfig,
    TrainingContext,
    CandidateStepInput,
    OrchestratorStepResult,
    ResearchTelemetryRecord,
)
from ai.coaching_orchestrator.state_machine import CoachingState, StateTransitionRecord


@runtime_checkable
class ICoachingStateMachine(Protocol):
    """Protocol for managing coaching lifecycle state transitions."""

    @property
    def current_state(self) -> CoachingState:
        ...

    def can_transition_to(self, target_state: CoachingState) -> bool:
        ...

    def transition_to(self, target_state: CoachingState, reason: str) -> StateTransitionRecord:
        ...

    def fail(self, reason: str) -> StateTransitionRecord:
        ...


@runtime_checkable
class ICoachingOrchestrator(Protocol):
    """
    Protocol for the Transfer-Aware Coaching Orchestrator coordinating
    engines across the complete end-to-end loop.
    """

    async def initialize_session(
        self,
        candidate_id: str,
        session_id: str,
        training_context: TrainingContext,
        config: Optional[CoachingSessionConfig] = None,
    ) -> OrchestratorStepResult:
        """Initializes a new coaching session and begins in TRAINING state."""
        ...

    async def submit_step(
        self,
        step_input: CandidateStepInput,
    ) -> OrchestratorStepResult:
        """Submits candidate answer for current state and advances the coaching loop."""
        ...

    def get_telemetry_record(self) -> ResearchTelemetryRecord:
        """Returns the compiled research telemetry record of the candidate journey."""
        ...

    def export_state_snapshot(self) -> dict:
        """Exports a serializable state snapshot of the active coaching orchestrator."""
        ...

    def hydrate_from_snapshot(self, snapshot: dict) -> None:
        """Hydrates orchestrator state from a persisted snapshot."""
        ...

