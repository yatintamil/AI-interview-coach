"""
Transfer-Aware Coaching Orchestrator Module (Phase 4).
Coordinates Transfer Generation, Failure Diagnosis, Targeted Coaching Policy,
Scaffold Fading, and Unassisted Independent Transfer.
"""

from ai.coaching_orchestrator.state_machine import (
    CoachingState,
    CoachingStateMachine,
    StateTransitionRecord,
    VALID_TRANSITIONS,
)
from ai.coaching_orchestrator.schemas import (
    CoachingSessionConfig,
    TrainingContext,
    CandidateStepInput,
    OrchestratorStepResult,
    ResearchTelemetryRecord,
)
from ai.coaching_orchestrator.interfaces import (
    ICoachingStateMachine,
    ICoachingOrchestrator,
)
from ai.coaching_orchestrator.validators import CoachingOrchestrationValidator
from ai.coaching_orchestrator.orchestrator import CoachingOrchestrator

__all__ = [
    "CoachingState",
    "CoachingStateMachine",
    "StateTransitionRecord",
    "VALID_TRANSITIONS",
    "CoachingSessionConfig",
    "TrainingContext",
    "CandidateStepInput",
    "OrchestratorStepResult",
    "ResearchTelemetryRecord",
    "ICoachingStateMachine",
    "ICoachingOrchestrator",
    "CoachingOrchestrationValidator",
    "CoachingOrchestrator",
]
