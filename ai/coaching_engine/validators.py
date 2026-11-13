"""
Validators for Coaching Intervention Decisions.
Enforces pedagogical integrity, scaffold consistency, independence constraints,
and schema validation.
"""

from typing import List
from backend.domain.transfer.coaching_types import CoachingInterventionType, ScaffoldLevel
from ai.coaching_engine.interfaces import ICoachingValidator
from ai.coaching_engine.schemas import (
    CoachingPolicyInput,
    CoachingPolicyDecision,
    CoachingValidationResult,
)
from ai.coaching_engine.scaffold_manager import SCAFFOLD_INTENSITY_WEIGHTS


class CoachingValidator(ICoachingValidator):
    """
    Validates that coaching decisions adhere to pedagogical contracts and avoid
    illicit assistance during independent evaluation turns.
    """

    def validate_decision(
        self, input_data: CoachingPolicyInput, decision: CoachingPolicyDecision
    ) -> CoachingValidationResult:
        failure_reasons: List[str] = []
        d = decision.decision
        s = decision.scaffold_state

        # 1. Validate intervention_type enum
        if not isinstance(d.intervention_type, CoachingInterventionType):
            try:
                CoachingInterventionType(d.intervention_type)
            except ValueError:
                failure_reasons.append(f"Invalid intervention_type: {d.intervention_type}")

        # 2. Validate scaffold_level enum
        if not isinstance(d.scaffold_level, ScaffoldLevel):
            try:
                ScaffoldLevel(d.scaffold_level)
            except ValueError:
                failure_reasons.append(f"Invalid scaffold_level: {d.scaffold_level}")

        # 3. Content and Pedagogical Intent non-emptiness
        if not d.content or len(d.content.strip()) < 10:
            failure_reasons.append("Coaching content must be at least 10 characters.")

        if not d.pedagogical_intent or len(d.pedagogical_intent.strip()) < 5:
            failure_reasons.append("Pedagogical intent must be at least 5 characters.")

        # 4. Independent Mode Integrity
        if d.scaffold_level == ScaffoldLevel.INDEPENDENT:
            if d.intervention_type in (
                CoachingInterventionType.EXPLANATION,
                CoachingInterventionType.WORKED_EXAMPLE,
                CoachingInterventionType.MINIMAL_HINT,
            ):
                failure_reasons.append(
                    f"Intervention {d.intervention_type.value} violates INDEPENDENT scaffold constraint: "
                    "no hints or instructional explanations may be supplied."
                )

        # 5. Scaffold Transition Direction Consistency
        prev_weight = SCAFFOLD_INTENSITY_WEIGHTS.get(s.previous_level, 0.0)
        curr_weight = SCAFFOLD_INTENSITY_WEIGHTS.get(s.current_level, 0.0)

        if s.is_faded and curr_weight >= prev_weight and s.previous_level != s.current_level:
            failure_reasons.append(
                f"Inconsistent fading: is_faded=True but scaffold intensity did not decrease "
                f"({s.previous_level.value} -> {s.current_level.value})."
            )

        if s.is_escalated and curr_weight <= prev_weight and s.previous_level != s.current_level:
            failure_reasons.append(
                f"Inconsistent escalation: is_escalated=True but scaffold intensity did not increase "
                f"({s.previous_level.value} -> {s.current_level.value})."
            )

        # 6. ADI Bounds Check
        if s.assistance_dependency_index < 0.0 or s.assistance_dependency_index > 1.0:
            failure_reasons.append(
                f"Assistance dependency index {s.assistance_dependency_index} out of bounds [0.0, 1.0]."
            )

        is_valid = len(failure_reasons) == 0
        return CoachingValidationResult(is_valid=is_valid, failure_reasons=failure_reasons)
