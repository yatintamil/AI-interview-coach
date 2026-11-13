"""
Intervention Selector for Transfer Coaching Policy.
Selects minimum effective interventions based on root-cause diagnosis,
scaffold level, history, and confidence bounds.
"""

from typing import Tuple, List, Dict, Optional
from backend.domain.transfer.diagnosis_types import TransferFailureType
from backend.domain.transfer.coaching_types import CoachingInterventionType, ScaffoldLevel
from ai.coaching_engine.interfaces import IInterventionSelector
from ai.coaching_engine.schemas import CoachingPolicyInput, CoachingHistoryEntry

# Configurable mapping from (TransferFailureType, ScaffoldLevel) to ordered intervention candidates
INTERVENTION_LADDER: Dict[TransferFailureType, Dict[ScaffoldLevel, List[CoachingInterventionType]]] = {
    TransferFailureType.SURFACE_PATTERN_DEPENDENCE: {
        ScaffoldLevel.INDEPENDENT: [CoachingInterventionType.TRANSFER_CHALLENGE, CoachingInterventionType.RETRY],
        ScaffoldLevel.LOW_ASSISTANCE: [CoachingInterventionType.REFLECTION, CoachingInterventionType.SOCRATIC_QUESTION],
        ScaffoldLevel.MEDIUM_ASSISTANCE: [CoachingInterventionType.COUNTEREXAMPLE, CoachingInterventionType.ANALOGY],
        ScaffoldLevel.HIGH_ASSISTANCE: [CoachingInterventionType.EXPLANATION, CoachingInterventionType.WORKED_EXAMPLE],
    },
    TransferFailureType.MISSING_CONCEPTUAL_MODEL: {
        ScaffoldLevel.INDEPENDENT: [CoachingInterventionType.RETRY, CoachingInterventionType.WAIT],
        ScaffoldLevel.LOW_ASSISTANCE: [CoachingInterventionType.MINIMAL_HINT, CoachingInterventionType.SOCRATIC_QUESTION],
        ScaffoldLevel.MEDIUM_ASSISTANCE: [CoachingInterventionType.DECOMPOSITION, CoachingInterventionType.ANALOGY],
        ScaffoldLevel.HIGH_ASSISTANCE: [CoachingInterventionType.EXPLANATION, CoachingInterventionType.WORKED_EXAMPLE],
    },
    TransferFailureType.WEAK_REQUIREMENT_ANALYSIS: {
        ScaffoldLevel.INDEPENDENT: [CoachingInterventionType.RETRY, CoachingInterventionType.WAIT],
        ScaffoldLevel.LOW_ASSISTANCE: [CoachingInterventionType.CLARIFICATION, CoachingInterventionType.SOCRATIC_QUESTION],
        ScaffoldLevel.MEDIUM_ASSISTANCE: [CoachingInterventionType.COUNTEREXAMPLE, CoachingInterventionType.DECOMPOSITION],
        ScaffoldLevel.HIGH_ASSISTANCE: [CoachingInterventionType.EXPLANATION, CoachingInterventionType.WORKED_EXAMPLE],
    },
    TransferFailureType.POOR_ABSTRACTION: {
        ScaffoldLevel.INDEPENDENT: [CoachingInterventionType.RETRY, CoachingInterventionType.WAIT],
        ScaffoldLevel.LOW_ASSISTANCE: [CoachingInterventionType.SOCRATIC_QUESTION, CoachingInterventionType.REFLECTION],
        ScaffoldLevel.MEDIUM_ASSISTANCE: [CoachingInterventionType.ANALOGY, CoachingInterventionType.DECOMPOSITION],
        ScaffoldLevel.HIGH_ASSISTANCE: [CoachingInterventionType.WORKED_EXAMPLE, CoachingInterventionType.EXPLANATION],
    },
    TransferFailureType.REASONING_FAILURE: {
        ScaffoldLevel.INDEPENDENT: [CoachingInterventionType.RETRY, CoachingInterventionType.WAIT],
        ScaffoldLevel.LOW_ASSISTANCE: [CoachingInterventionType.SOCRATIC_QUESTION, CoachingInterventionType.PROMPT],
        ScaffoldLevel.MEDIUM_ASSISTANCE: [CoachingInterventionType.COUNTEREXAMPLE, CoachingInterventionType.DECOMPOSITION],
        ScaffoldLevel.HIGH_ASSISTANCE: [CoachingInterventionType.WORKED_EXAMPLE, CoachingInterventionType.EXPLANATION],
    },
    TransferFailureType.COMMUNICATION_BREAKDOWN: {
        ScaffoldLevel.INDEPENDENT: [CoachingInterventionType.RETRY, CoachingInterventionType.WAIT],
        ScaffoldLevel.LOW_ASSISTANCE: [CoachingInterventionType.PROMPT, CoachingInterventionType.REFLECTION],
        ScaffoldLevel.MEDIUM_ASSISTANCE: [CoachingInterventionType.DECOMPOSITION],
        ScaffoldLevel.HIGH_ASSISTANCE: [CoachingInterventionType.WORKED_EXAMPLE],
    },
    TransferFailureType.COGNITIVE_OVERLOAD: {
        ScaffoldLevel.INDEPENDENT: [CoachingInterventionType.WAIT, CoachingInterventionType.RETRY],
        ScaffoldLevel.LOW_ASSISTANCE: [CoachingInterventionType.MINIMAL_HINT, CoachingInterventionType.PROMPT],
        ScaffoldLevel.MEDIUM_ASSISTANCE: [CoachingInterventionType.DECOMPOSITION],
        ScaffoldLevel.HIGH_ASSISTANCE: [CoachingInterventionType.WORKED_EXAMPLE],
    },
    TransferFailureType.EXCESSIVE_SCAFFOLD_DEPENDENCY: {
        ScaffoldLevel.INDEPENDENT: [CoachingInterventionType.RETRY, CoachingInterventionType.WAIT],
        ScaffoldLevel.LOW_ASSISTANCE: [CoachingInterventionType.REFLECTION, CoachingInterventionType.MINIMAL_HINT],
        ScaffoldLevel.MEDIUM_ASSISTANCE: [CoachingInterventionType.DECOMPOSITION],
        ScaffoldLevel.HIGH_ASSISTANCE: [CoachingInterventionType.EXPLANATION],
    },
    TransferFailureType.NONE: {
        ScaffoldLevel.INDEPENDENT: [CoachingInterventionType.TRANSFER_CHALLENGE, CoachingInterventionType.WAIT],
        ScaffoldLevel.LOW_ASSISTANCE: [CoachingInterventionType.TRANSFER_CHALLENGE, CoachingInterventionType.WAIT],
        ScaffoldLevel.MEDIUM_ASSISTANCE: [CoachingInterventionType.RETRY, CoachingInterventionType.TRANSFER_CHALLENGE],
        ScaffoldLevel.HIGH_ASSISTANCE: [CoachingInterventionType.RETRY],
    },
}

# Default pedagogical intents
DEFAULT_PEDAGOGICAL_INTENTS: Dict[CoachingInterventionType, str] = {
    CoachingInterventionType.WAIT: "Provide cognitive pause for autonomous self-correction.",
    CoachingInterventionType.CLARIFICATION: "Direct attention to unstated parameters and operational constraints.",
    CoachingInterventionType.PROMPT: "Prompt focus towards the neglected architectural dimension.",
    CoachingInterventionType.MINIMAL_HINT: "Provide minimal conceptual nudge without revealing solution mechanics.",
    CoachingInterventionType.SOCRATIC_QUESTION: "Guide candidate to discover theoretical invariant through targeted questioning.",
    CoachingInterventionType.DECOMPOSITION: "Break down multi-faceted challenge into tractable sub-problems.",
    CoachingInterventionType.COUNTEREXAMPLE: "Expose flaws in current assumptions via an edge case counterexample.",
    CoachingInterventionType.ANALOGY: "Rebuild intuition by mapping difficult mechanics to a familiar domain.",
    CoachingInterventionType.WORKED_EXAMPLE: "Demonstrate parallel structural solution to ground theoretical invariant.",
    CoachingInterventionType.EXPLANATION: "Provide direct instructional explanation of the missing conceptual model.",
    CoachingInterventionType.REFLECTION: "Prompt candidate to critically evaluate design trade-offs and invariants.",
    CoachingInterventionType.RETRY: "Request candidate re-attempt the transfer challenge under reduced assistance.",
    CoachingInterventionType.TRANSFER_CHALLENGE: "Advance candidate to higher transfer distance to test independent mastery.",
}


class InterventionSelector(IInterventionSelector):
    """
    Selects the minimum effective intervention according to pedagogical ladders,
    avoiding ineffective repeated interventions and clamping low-confidence diagnoses.
    """

    def select_intervention(
        self, input_data: CoachingPolicyInput, target_scaffold: ScaffoldLevel
    ) -> Tuple[CoachingInterventionType, str]:
        failure_type = input_data.diagnosis.failure_type
        confidence = input_data.diagnosis.confidence

        # 1. Low-Confidence Diagnosis Protection
        # When confidence is low (< 0.60), do NOT administer invasive HIGH_ASSISTANCE instruction
        effective_scaffold = target_scaffold
        if confidence < 0.60 and target_scaffold == ScaffoldLevel.HIGH_ASSISTANCE:
            effective_scaffold = ScaffoldLevel.LOW_ASSISTANCE

        # 2. Retrieve Candidate Ladder
        ladder_for_failure = INTERVENTION_LADDER.get(failure_type, INTERVENTION_LADDER[TransferFailureType.NONE])
        candidates = ladder_for_failure.get(effective_scaffold, [CoachingInterventionType.PROMPT])

        # 3. Avoid Repeating Ineffective Interventions
        # Inspect recent history: if the most recent intervention failed, pick the next candidate
        recent_interventions = [
            e.intervention_type for e in input_data.history[-2:] if e.outcome == "FAILURE"
        ]

        rec = input_data.diagnosis.recommended_intervention
        if rec in candidates and rec not in recent_interventions:
            selected_intervention = rec
        else:
            selected_intervention = candidates[0]
            for cand in candidates:
                if cand not in recent_interventions:
                    selected_intervention = cand
                    break
            else:
                selected_intervention = candidates[0]

        # 4. Independent Mode Enforcement: hints and direct solutions are strictly suppressed
        if target_scaffold == ScaffoldLevel.INDEPENDENT:
            if selected_intervention in (
                CoachingInterventionType.EXPLANATION,
                CoachingInterventionType.WORKED_EXAMPLE,
                CoachingInterventionType.MINIMAL_HINT,
            ):
                selected_intervention = (
                    CoachingInterventionType.TRANSFER_CHALLENGE
                    if failure_type == TransferFailureType.NONE
                    else CoachingInterventionType.RETRY
                )

        intent = DEFAULT_PEDAGOGICAL_INTENTS.get(
            selected_intervention, f"Address {failure_type.value} under {target_scaffold.value}."
        )
        return selected_intervention, intent

    def generate_content(
        self,
        intervention: CoachingInterventionType,
        skill_id: str,
        failure_type: TransferFailureType,
        scaffold_level: ScaffoldLevel,
    ) -> str:
        """
        Synthesizes deterministic dialogue content matching the selected intervention type.
        """
        skill_name = skill_id.replace("_", " ").title()

        if intervention == CoachingInterventionType.WAIT:
            return "Take your time to structure your thoughts and proceed when ready."

        elif intervention == CoachingInterventionType.CLARIFICATION:
            return (
                f"Before finalizing your architecture for {skill_name}, consider what assumptions "
                "you are making regarding operational constraints, scale, and SLA requirements."
            )

        elif intervention == CoachingInterventionType.PROMPT:
            return f"Focus on how your design addresses the core invariants of {skill_name}."

        elif intervention == CoachingInterventionType.MINIMAL_HINT:
            return (
                f"Consider how partitioning and invariant preservation in {skill_name} "
                "prevent hot spots during peak traffic."
            )

        elif intervention == CoachingInterventionType.SOCRATIC_QUESTION:
            if failure_type == TransferFailureType.SURFACE_PATTERN_DEPENDENCE:
                return (
                    f"Rather than reusing the surface mechanism from the previous problem, what fundamental invariant governs authoritative consistency in {skill_name}? "
                    "How does your design guarantee this invariant under domain shift?"
                )
            return (
                f"What happens to system invariants in {skill_name} when a cluster node fails unexpectedly? "
                "How does your routing or partition ring respond?"
            )

        elif intervention == CoachingInterventionType.DECOMPOSITION:
            return (
                f"Let's break down this {skill_name} problem into two distinct steps: "
                "first, determine the data partitioning model; second, handle eviction and cache-aside lookup."
            )

        elif intervention == CoachingInterventionType.COUNTEREXAMPLE:
            if failure_type == TransferFailureType.SURFACE_PATTERN_DEPENDENCE:
                return (
                    f"Notice where surface pattern matching breaks down: in this new scenario, applying the previous pattern directly causes authoritative state drift and stale reads. "
                    f"Consider what invariant must hold true regardless of domain: authoritative data changes must reliably invalidate or update cached records. What invariant must your architecture enforce here?"
                )
            return (
                f"Consider a scenario where the scale increases 100x and keys are highly skewed. "
                f"Does relying on the previous domain pattern hold, or does it create severe bottlenecks?"
            )

        elif intervention == CoachingInterventionType.ANALOGY:
            return (
                f"Think of {skill_name} like a regional postal sorting hub: packages are routed based on stable zip code "
                "boundaries so that adding a new local delivery route doesn't require rebuilding the entire nationwide sorting facility."
            )

        elif intervention == CoachingInterventionType.WORKED_EXAMPLE:
            return (
                f"Here is how this invariant operates in practice: keys are mapped to a continuous hash ring, "
                "each node is assigned multiple virtual tokens, and lookups traverse clockwise to locate the responsible replica."
            )

        elif intervention == CoachingInterventionType.EXPLANATION:
            return (
                f"The core mechanism of {skill_name} relies on decoupled structural invariants: "
                "adding or removing resources must only remap K/N keys, maintaining predictable latency without global locks."
            )

        elif intervention == CoachingInterventionType.REFLECTION:
            return (
                f"Review your proposed solution for {skill_name}. "
                "Does it preserve the required invariants under the new transfer conditions?"
            )

        elif intervention == CoachingInterventionType.RETRY:
            return (
                f"Now that we have clarified the underlying invariants, "
                f"please re-attempt your response for {skill_name} independently."
            )

        elif intervention == CoachingInterventionType.TRANSFER_CHALLENGE:
            return (
                f"You have successfully demonstrated invariant transfer for {skill_name}. "
                "Let us advance to an independent challenge at the next transfer level."
            )

        return f"Please proceed with your explanation of {skill_name}."
