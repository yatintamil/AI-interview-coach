"""
Coaching Intervention Policy and Scaffold Fading Engine.

Translates transfer failure diagnoses into minimum effective coaching interventions,
tracks scaffold fading transitions, and computes assistance dependency metrics.
"""

from ai.coaching_engine.schemas import (
    CoachingHistoryEntry,
    CoachingPolicyInput,
    ScaffoldState,
    CoachingDecisionRationale,
    CoachingPolicyDecision,
    CoachingValidationResult,
)
from ai.coaching_engine.interfaces import (
    IScaffoldManager,
    IInterventionSelector,
    ICoachingPolicy,
    ICoachingValidator,
)
from ai.coaching_engine.scaffold_manager import (
    ScaffoldManager,
    SCAFFOLD_INTENSITY_WEIGHTS,
)
from ai.coaching_engine.intervention_selector import (
    InterventionSelector,
    INTERVENTION_LADDER,
    DEFAULT_PEDAGOGICAL_INTENTS,
)
from ai.coaching_engine.validators import CoachingValidator
from ai.coaching_engine.policy import CoachingPolicy

__all__ = [
    "CoachingHistoryEntry",
    "CoachingPolicyInput",
    "ScaffoldState",
    "CoachingDecisionRationale",
    "CoachingPolicyDecision",
    "CoachingValidationResult",
    "IScaffoldManager",
    "IInterventionSelector",
    "ICoachingPolicy",
    "ICoachingValidator",
    "ScaffoldManager",
    "SCAFFOLD_INTENSITY_WEIGHTS",
    "InterventionSelector",
    "INTERVENTION_LADDER",
    "DEFAULT_PEDAGOGICAL_INTENTS",
    "CoachingValidator",
    "CoachingPolicy",
]
