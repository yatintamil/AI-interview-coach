"""
Explicit Coaching Lifecycle State Machine.
Represents all operational states and transitions across the transfer coaching loop.
"""

from enum import Enum
from typing import List, Dict, Set, Optional
from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, ConfigDict


class CoachingState(str, Enum):
    """
    Explicit lifecycle states for the Transfer-Aware Coaching Loop.
    Guarantees no scattered boolean flags represent candidate progression.
    """
    TRAINING = "TRAINING"
    UNDERSTANDING_CHECK = "UNDERSTANDING_CHECK"
    TRAINING_EVALUATION = "TRAINING_EVALUATION"
    TRANSFER_GENERATION = "TRANSFER_GENERATION"
    TRANSFER_ATTEMPT = "TRANSFER_ATTEMPT"
    TRANSFER_EVALUATION = "TRANSFER_EVALUATION"
    TRANSFER_DIAGNOSIS = "TRANSFER_DIAGNOSIS"
    COACHING_DECISION = "COACHING_DECISION"
    INTERVENTION = "INTERVENTION"
    RETRY = "RETRY"
    RETRY_EVALUATION = "RETRY_EVALUATION"
    TRANSFER_RETEST = "TRANSFER_RETEST"
    INDEPENDENT_TRANSFER = "INDEPENDENT_TRANSFER"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


VALID_TRANSITIONS: Dict[CoachingState, Set[CoachingState]] = {
    CoachingState.TRAINING: {
        CoachingState.UNDERSTANDING_CHECK,
        CoachingState.TRAINING_EVALUATION,
        CoachingState.FAILED,
    },
    CoachingState.UNDERSTANDING_CHECK: {
        CoachingState.TRAINING_EVALUATION,
        CoachingState.TRAINING,
        CoachingState.FAILED,
    },
    CoachingState.TRAINING_EVALUATION: {
        CoachingState.TRANSFER_GENERATION,
        CoachingState.TRAINING,
        CoachingState.UNDERSTANDING_CHECK,
        CoachingState.FAILED,
    },
    CoachingState.TRANSFER_GENERATION: {
        CoachingState.TRANSFER_ATTEMPT,
        CoachingState.FAILED,
    },
    CoachingState.TRANSFER_ATTEMPT: {
        CoachingState.TRANSFER_EVALUATION,
        CoachingState.FAILED,
    },
    CoachingState.TRANSFER_EVALUATION: {
        CoachingState.INDEPENDENT_TRANSFER,  # On direct transfer success
        CoachingState.TRANSFER_DIAGNOSIS,    # On transfer failure
        CoachingState.TRANSFER_RETEST,
        CoachingState.FAILED,
    },
    CoachingState.TRANSFER_DIAGNOSIS: {
        CoachingState.COACHING_DECISION,
        CoachingState.INDEPENDENT_TRANSFER,  # When diagnosis is NONE (success verified)
        CoachingState.FAILED,
    },
    CoachingState.COACHING_DECISION: {
        CoachingState.INTERVENTION,
        CoachingState.INDEPENDENT_TRANSFER,
        CoachingState.COMPLETED,
        CoachingState.FAILED,
    },
    CoachingState.INTERVENTION: {
        CoachingState.RETRY,
        CoachingState.TRANSFER_RETEST,
        CoachingState.INDEPENDENT_TRANSFER,
        CoachingState.COMPLETED,
        CoachingState.FAILED,
    },
    CoachingState.RETRY: {
        CoachingState.RETRY_EVALUATION,
        CoachingState.FAILED,
    },
    CoachingState.RETRY_EVALUATION: {
        CoachingState.TRANSFER_RETEST,       # Improvement verified, re-testing
        CoachingState.INDEPENDENT_TRANSFER,  # Improvement or retry exhaustion proceeding to independent test
        CoachingState.TRANSFER_DIAGNOSIS,    # Retry failed, re-diagnosing next intervention
        CoachingState.COMPLETED,             # Retry limit reached or complete
        CoachingState.FAILED,
    },
    CoachingState.TRANSFER_RETEST: {
        CoachingState.TRANSFER_ATTEMPT,
        CoachingState.TRANSFER_EVALUATION,
        CoachingState.INDEPENDENT_TRANSFER,
        CoachingState.FAILED,
    },
    CoachingState.INDEPENDENT_TRANSFER: {
        CoachingState.COMPLETED,
        CoachingState.FAILED,
    },
    CoachingState.COMPLETED: set(),
    CoachingState.FAILED: set(),
}


class StateTransitionRecord(BaseModel):
    """Immutable audit record of a single state machine transition."""
    model_config = ConfigDict(extra="forbid")

    from_state: CoachingState = Field(..., description="Preceding state.")
    to_state: CoachingState = Field(..., description="Target state.")
    reason: str = Field(..., min_length=1, description="Event or condition motivating transition.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of transition.")


class CoachingStateMachine:
    """
    State machine managing the candidate coaching journey lifecycle.
    Guarantees that transitions adhere strictly to the allowed directed acyclic path.
    """

    def __init__(self, initial_state: CoachingState = CoachingState.TRAINING):
        self._current_state = initial_state
        self._history: List[StateTransitionRecord] = []

    @property
    def current_state(self) -> CoachingState:
        return self._current_state

    @property
    def history(self) -> List[StateTransitionRecord]:
        return list(self._history)

    def can_transition_to(self, target_state: CoachingState) -> bool:
        """Checks whether transitioning to target_state is permitted from current_state."""
        allowed = VALID_TRANSITIONS.get(self._current_state, set())
        return target_state in allowed

    def transition_to(self, target_state: CoachingState, reason: str) -> StateTransitionRecord:
        """
        Executes a validated state transition and records it in history.
        Raises ValueError if the transition is illegal.
        """
        if not self.can_transition_to(target_state):
            raise ValueError(
                f"Illegal state transition from {self._current_state.value} to {target_state.value}. "
                f"Allowed transitions: {[s.value for s in VALID_TRANSITIONS.get(self._current_state, set())]}"
            )

        record = StateTransitionRecord(
            from_state=self._current_state,
            to_state=target_state,
            reason=reason,
        )
        self._current_state = target_state
        self._history.append(record)
        return record

    def fail(self, reason: str) -> StateTransitionRecord:
        """Transitions state machine to FAILED state upon unrecoverable error."""
        return self.transition_to(CoachingState.FAILED, reason=f"Failure: {reason}")
