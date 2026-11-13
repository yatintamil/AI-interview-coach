"""
Coaching Policy Engine Orchestrator.
Converts diagnosed transfer failures into minimum effective coaching interventions,
tracks scaffold fading, and produces explainable pedagogical audit trails.
"""

from typing import Optional
from backend.domain.transfer.coaching_types import CoachingInterventionType, ScaffoldLevel
from backend.domain.transfer.schemas import CoachingInterventionDecisionDTO
from ai.coaching_engine.interfaces import (
    ICoachingPolicy,
    IScaffoldManager,
    IInterventionSelector,
    ICoachingValidator,
)
from ai.coaching_engine.schemas import (
    CoachingPolicyInput,
    CoachingPolicyDecision,
    CoachingDecisionRationale,
    ScaffoldState,
)
from ai.coaching_engine.scaffold_manager import ScaffoldManager
from ai.coaching_engine.intervention_selector import InterventionSelector
from ai.coaching_engine.validators import CoachingValidator


class CoachingPolicy(ICoachingPolicy):
    """
    Transparent, deterministic coaching policy implementing the transfer-aware coaching loop:
    Diagnosis + History + Current Scaffold -> Minimum Effective Intervention + Scaffold Fading
    """

    def __init__(
        self,
        scaffold_manager: Optional[IScaffoldManager] = None,
        intervention_selector: Optional[IInterventionSelector] = None,
        validator: Optional[ICoachingValidator] = None,
        policy_version: str = "1.0.0",
    ):
        self.scaffold_manager = scaffold_manager or ScaffoldManager()
        self.intervention_selector = intervention_selector or InterventionSelector()
        self.validator = validator or CoachingValidator()
        self.policy_version = policy_version

    def decide(self, input_data: CoachingPolicyInput) -> CoachingPolicyDecision:
        """
        Computes the minimum effective coaching intervention and determines scaffold state.
        """
        # 1. Compute Scaffold Level Transition & Assistance Dependency Index
        scaffold_state: ScaffoldState = self.scaffold_manager.compute_scaffold_transition(
            current_level=input_data.current_scaffold_level,
            last_outcome=input_data.last_outcome,
            history=input_data.history,
        )

        # 2. Select Minimum Effective Intervention
        intervention_type, pedagogical_intent = self.intervention_selector.select_intervention(
            input_data=input_data,
            target_scaffold=scaffold_state.current_level,
        )

        # 3. Generate Actionable Coaching Content
        content = self.intervention_selector.generate_content(
            intervention=intervention_type,
            skill_id=input_data.diagnosis.affected_skill,
            failure_type=input_data.diagnosis.failure_type,
            scaffold_level=scaffold_state.current_level,
        )

        # 4. Determine Retry Requirement
        # Non-retry actions: Advancing to next challenge or neutral waiting
        retry_required = intervention_type not in (
            CoachingInterventionType.TRANSFER_CHALLENGE,
            CoachingInterventionType.WAIT,
        )

        # 5. Formulate Explainable Rationale
        if scaffold_state.is_faded:
            escalation_status = "FADED"
        elif scaffold_state.is_escalated:
            escalation_status = "ESCALATED"
        else:
            escalation_status = "NONE"

        confidence_category = "HIGH" if input_data.diagnosis.confidence >= 0.60 else "LOW"

        audit_trail = (
            f"Diagnosed failure: {input_data.diagnosis.failure_type.value} "
            f"(confidence={input_data.diagnosis.confidence}, category={confidence_category}). "
            f"Preceding outcome: {input_data.last_outcome or 'None'}. "
            f"Scaffold transitioned: {scaffold_state.previous_level.value} -> {scaffold_state.current_level.value} "
            f"(ADI={scaffold_state.assistance_dependency_index}). "
            f"Selected intervention: {intervention_type.value} under {scaffold_state.current_level.value}. "
            f"Intent: {pedagogical_intent}"
        )

        rationale = CoachingDecisionRationale(
            target_failure=input_data.diagnosis.failure_type,
            confidence_category=confidence_category,
            escalation_status=escalation_status,
            pedagogical_intent=pedagogical_intent,
            audit_trail=audit_trail,
        )

        # 6. Construct Domain Decision DTO
        decision_dto = CoachingInterventionDecisionDTO(
            intervention_type=intervention_type,
            scaffold_level=scaffold_state.current_level,
            content=content,
            pedagogical_intent=pedagogical_intent,
            is_faded=scaffold_state.is_faded,
            retry_required=retry_required,
        )

        policy_decision = CoachingPolicyDecision(
            decision=decision_dto,
            scaffold_state=scaffold_state,
            rationale=rationale,
            policy_version=self.policy_version,
        )

        # 7. Validate Decision Constraints
        validation = self.validator.validate_decision(input_data, policy_decision)
        if not validation.is_valid:
            raise ValueError(
                f"Coaching policy decision failed validation: {'; '.join(validation.failure_reasons)}"
            )

        return policy_decision
