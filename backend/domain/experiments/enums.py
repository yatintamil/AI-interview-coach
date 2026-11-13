"""
Domain enums for the experimental framework.
Strictly decoupled: contains pure domain types.
"""

from enum import Enum


class ExperimentCondition(str, Enum):
    """Experimental conditions representing comparative coaching treatments."""
    CONDITION_A = "CONDITION_A"  # Generic Feedback Baseline
    CONDITION_B = "CONDITION_B"  # Adaptive Difficulty Baseline
    CONDITION_C = "CONDITION_C"  # Proposed Transfer-Aware Coaching


class ExperimentPhase(str, Enum):
    """Phases across the unified experimental lifecycle."""
    PRETEST = "PRETEST"
    TRAINING = "TRAINING"
    POSTTEST = "POSTTEST"
    TRANSFER_TEST = "TRANSFER_TEST"
    TARGETED_RETRAINING = "TARGETED_RETRAINING"
    INDEPENDENT_TRANSFER = "INDEPENDENT_TRANSFER"
    COMPLETED = "COMPLETED"


class ExperimentOutcome(str, Enum):
    """Outcome status for individual trials or sessions."""
    PASS = "PASS"
    FAIL = "FAIL"
    RETRIED = "RETRIED"
    COMPLETED = "COMPLETED"


class TaskDifficulty(str, Enum):
    """Discrete task difficulty tiers for Baseline B adaptation."""
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"
