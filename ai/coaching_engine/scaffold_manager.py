"""
Scaffold Manager and Assistance Dependency Tracker.
Implements systematic scaffold fading, controlled escalation,
and deterministic Assistance Dependency Index (ADI) calculation.
"""

from typing import List, Optional
from backend.domain.transfer.coaching_types import ScaffoldLevel
from ai.coaching_engine.interfaces import IScaffoldManager
from ai.coaching_engine.schemas import CoachingHistoryEntry, ScaffoldState

# Engineering weights representing assistance intensity per scaffold tier
SCAFFOLD_INTENSITY_WEIGHTS = {
    ScaffoldLevel.HIGH_ASSISTANCE: 1.0,
    ScaffoldLevel.MEDIUM_ASSISTANCE: 0.66,
    ScaffoldLevel.LOW_ASSISTANCE: 0.33,
    ScaffoldLevel.INDEPENDENT: 0.0,
}

# Ladder transitions
LADDER_UP = {
    ScaffoldLevel.INDEPENDENT: ScaffoldLevel.LOW_ASSISTANCE,
    ScaffoldLevel.LOW_ASSISTANCE: ScaffoldLevel.MEDIUM_ASSISTANCE,
    ScaffoldLevel.MEDIUM_ASSISTANCE: ScaffoldLevel.HIGH_ASSISTANCE,
    ScaffoldLevel.HIGH_ASSISTANCE: ScaffoldLevel.HIGH_ASSISTANCE,
}

LADDER_DOWN = {
    ScaffoldLevel.HIGH_ASSISTANCE: ScaffoldLevel.MEDIUM_ASSISTANCE,
    ScaffoldLevel.MEDIUM_ASSISTANCE: ScaffoldLevel.LOW_ASSISTANCE,
    ScaffoldLevel.LOW_ASSISTANCE: ScaffoldLevel.INDEPENDENT,
    ScaffoldLevel.INDEPENDENT: ScaffoldLevel.INDEPENDENT,
}


class ScaffoldManager(IScaffoldManager):
    """
    Manages scaffold level transitions and tracks assistance dependency.
    Fosters autonomous transfer by systematically fading assistance upon recovery,
    while stabilizing transitions to prevent abrupt HIGH <-> LOW oscillations.
    """

    def __init__(self, history_window: int = 10, escalation_threshold: int = 2):
        self.history_window = history_window
        self.escalation_threshold = escalation_threshold

    def calculate_assistance_dependency_index(
        self, history: List[CoachingHistoryEntry]
    ) -> float:
        """
        Calculates the operational Assistance Dependency Index (ADI) in [0.0, 1.0].

        Formula:
        For a recency-weighted window of the last W entries:
          turn_cost = 0.7 * scaffold_weight + 0.3 * min(1.0, hints_requested * 0.25)
          ADI = sum(recency_weight_i * turn_cost_i) / sum(recency_weight_i)

        Note: ADI is an engineering metric operationalizing research hypothesis H3,
        not a validated psychometric or cognitive scale.
        """
        if not history:
            return 0.0

        window = history[-self.history_window:]
        total_weight = 0.0
        weighted_cost = 0.0

        for idx, entry in enumerate(window):
            # Recency multiplier gives higher weight to recent turns
            recency_multiplier = 1.0 + 0.1 * idx
            scaffold_cost = SCAFFOLD_INTENSITY_WEIGHTS.get(entry.scaffold_level, 0.0)
            hint_cost = min(1.0, entry.hints_requested * 0.25)

            combined_turn_cost = 0.7 * scaffold_cost + 0.3 * hint_cost

            weighted_cost += recency_multiplier * combined_turn_cost
            total_weight += recency_multiplier

        if total_weight == 0.0:
            return 0.0

        adi = weighted_cost / total_weight
        return round(max(0.0, min(1.0, adi)), 3)

    def compute_scaffold_transition(
        self,
        current_level: ScaffoldLevel,
        last_outcome: Optional[str],
        history: List[CoachingHistoryEntry],
    ) -> ScaffoldState:
        """
        Determines the next scaffold level according to controlled pedagogical rules:
        - SUCCESS -> Step down scaffold by one level (fading).
        - FAILURE from INDEPENDENT -> Step up to LOW_ASSISTANCE.
        - FAILURE from LOW/MEDIUM -> Step up only if consecutive failures >= escalation_threshold.
        - Initial turn / None -> Maintain current level.
        """
        adi = self.calculate_assistance_dependency_index(history)
        previous_level = current_level

        if last_outcome == "SUCCESS":
            next_level = LADDER_DOWN[current_level]
            is_faded = next_level != current_level
            is_escalated = False
            reason = (
                f"Candidate achieved success on previous turn. "
                f"Fading scaffold from {current_level.value} to {next_level.value} to foster autonomy."
            )
            return ScaffoldState(
                current_level=next_level,
                previous_level=previous_level,
                is_faded=is_faded,
                is_escalated=is_escalated,
                assistance_dependency_index=adi,
                transition_reason=reason,
            )

        elif last_outcome == "FAILURE":
            # Count consecutive failures at the current scaffold level
            consecutive_failures = 0
            for entry in reversed(history):
                if entry.outcome == "FAILURE" and entry.scaffold_level == current_level:
                    consecutive_failures += 1
                else:
                    break

            if current_level == ScaffoldLevel.INDEPENDENT:
                next_level = ScaffoldLevel.LOW_ASSISTANCE
                is_escalated = True
                reason = "Transfer failure detected in independent mode. Introducing LOW_ASSISTANCE scaffolding."
            elif consecutive_failures >= self.escalation_threshold:
                next_level = LADDER_UP[current_level]
                is_escalated = next_level != current_level
                reason = (
                    f"Candidate experienced {consecutive_failures} consecutive failures at {current_level.value}. "
                    f"Controlled escalation to {next_level.value}."
                )
            else:
                next_level = current_level
                is_escalated = False
                reason = (
                    f"First failure at {current_level.value} (consecutive={consecutive_failures}). "
                    f"Maintaining level to try alternative horizontal intervention before escalating."
                )

            return ScaffoldState(
                current_level=next_level,
                previous_level=previous_level,
                is_faded=False,
                is_escalated=is_escalated,
                assistance_dependency_index=adi,
                transition_reason=reason,
            )

        # Initial turn or neutral continuation
        return ScaffoldState(
            current_level=current_level,
            previous_level=previous_level,
            is_faded=False,
            is_escalated=False,
            assistance_dependency_index=adi,
            transition_reason=f"Initial or continuous session state. Maintaining {current_level.value}.",
        )
