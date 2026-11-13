"""
Domain Data Transfer Objects and Contracts for Transfer-Aware AI Coaching.

All schemas enforce strict Pydantic validation, explicit typing, boundary checks,
and clean serialization.
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, ConfigDict

from backend.domain.transfer.taxonomy import TransferLevel
from backend.domain.transfer.diagnosis_types import TransferFailureType
from backend.domain.transfer.coaching_types import CoachingInterventionType, ScaffoldLevel


class SessionPhase(str, Enum):
    """
    Experimental and operational phases of an interview coaching lifecycle.
    Enables empirical distinction between pre-test baselines, guided training,
    transfer testing, and delayed retention.
    """
    PRETEST = "PRETEST"
    """Baseline assessment prior to any coaching interventions."""

    TRAINING = "TRAINING"
    """Guided practice and skill acquisition with interactive scaffolding."""

    POSTTEST = "POSTTEST"
    """Evaluation of trained task mastery under standard conditions."""

    TRANSFER_TEST = "TRANSFER_TEST"
    """Novel unseen transfer challenge evaluating autonomous generalization."""

    TARGETED_RETRAINING = "TARGETED_RETRAINING"
    """Cause-specific remediation triggered immediately upon transfer failure."""

    TRANSFER_RETEST = "TRANSFER_RETEST"
    """Subsequent transfer test assessing whether retraining recovered transfer competence."""

    DELAYED_RETENTION = "DELAYED_RETENTION"
    """Follow-up assessment across elapsed time to test long-term retention (H4)."""


class EvidenceItemDTO(BaseModel):
    """Grounding evidence item connecting a claim to verbatim candidate response material."""
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(..., min_length=1, description="Diagnostic observation or assertion.")
    basis: str = Field(..., min_length=1, description="Verbatim quote or concrete empirical basis.")


class TransferTaskDefinitionDTO(BaseModel):
    """
    Defines a transfer evaluation task with controlled invariant and surface transformations.
    """
    model_config = ConfigDict(extra="forbid")

    id: str = Field(..., min_length=1, description="Unique identifier for the transfer task.")
    parent_task_id: Optional[str] = Field(default=None, description="Identifier of the baseline/training task this task was derived from.")
    skill_id: str = Field(..., min_length=1, description="Competency or concept key evaluated by this task.")
    transfer_level: TransferLevel = Field(..., description="Project domain transfer distance rank (L0 to L5).")
    surface_context: str = Field(..., min_length=1, description="Domain context framing the problem (e.g., 'Financial Clearinghouse').")
    core_invariants: List[str] = Field(..., min_length=1, description="Structural principles that remain unchanged across transfer.")
    surface_distractors: List[str] = Field(default_factory=list, description="Incidental surface variations introduced to test abstraction.")
    expected_concepts: List[str] = Field(..., min_length=1, description="Mandatory architectural or algorithmic concepts required.")
    rubric_id: Optional[str] = Field(default=None, description="Evaluation rubric identifier.")
    prompt_template: Optional[str] = Field(default=None, description="The concrete prompt or question text presented to the candidate.")
    transfer_distance: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Situational transfer distance metric D from training domain.")


class TransferFailureDiagnosisDTO(BaseModel):
    """
    Structured, validated diagnosis of transfer failure combining deterministic features,
    rubric scores, and structured reasoning.
    """
    model_config = ConfigDict(extra="forbid")

    failure_type: TransferFailureType = Field(..., description="Hypothesized root cause of transfer failure.")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated confidence score of the diagnosis.")
    affected_skill: str = Field(..., min_length=1, description="Specific skill or invariant impaired.")
    deterministic_signals: Dict[str, Any] = Field(default_factory=dict, description="Objective metrics: refusal flag, concept coverage ratio, latency, retry count.")
    evidence: List[EvidenceItemDTO] = Field(default_factory=list, description="Verbatim evidence items grounding the diagnosis.")
    recommended_intervention: CoachingInterventionType = Field(..., description="Minimum effective coaching intervention selected.")
    diagnostic_reasoning: str = Field(..., min_length=1, description="Explainable audit justification explaining why this cause was determined.")


class CoachingInterventionDecisionDTO(BaseModel):
    """
    Structured specification of an intervention administered by the coaching policy.
    """
    model_config = ConfigDict(extra="forbid")

    intervention_type: CoachingInterventionType = Field(..., description="Selected action from the 13-tier intervention taxonomy.")
    scaffold_level: ScaffoldLevel = Field(..., description="Assistance intensity category.")
    content: str = Field(..., min_length=1, description="Exact coaching dialogue, nudge, or question presented to candidate.")
    pedagogical_intent: str = Field(..., min_length=1, description="Pedagogical objective (e.g., 'Address surface-pattern bias via counterexample').")
    is_faded: bool = Field(default=False, description="Flag indicating if scaffold intensity was stepped down relative to previous turn.")
    retry_required: bool = Field(default=False, description="Whether candidate must re-attempt the task under reduced scaffolding.")


class CandidateSkillStateDTO(BaseModel):
    """
    Longitudinal representation of candidate skill competence over time.

    Uncertainty Notice:
    `mastery_uncertainty` represents an uncertainty representation for the current engineering
    model, bounded to [0.0, 1.0]. It is not a statistical confidence interval.
    """
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., min_length=1, description="Candidate foreign identifier.")
    skill_name: str = Field(..., min_length=1, description="Canonical skill identifier.")
    mastery_estimate: float = Field(..., ge=0.0, le=1.0, description="Latent skill mastery estimate in [0.0, 1.0].")
    mastery_uncertainty: float = Field(..., ge=0.0, le=1.0, description="Uncertainty representation for current engineering model in [0.0, 1.0].")
    highest_transfer_level: TransferLevel = Field(default=TransferLevel.L0_RECALL, description="Highest transfer distance validated.")
    assistance_dependency_index: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of assisted turns to independent completions (H3).")
    recurring_failure_types: List[TransferFailureType] = Field(default_factory=list, description="Historical diagnostic pattern frequencies.")
    total_attempts: int = Field(default=0, ge=0, description="Total evaluation attempts for this competency.")
    last_assessed_at: Optional[datetime] = Field(default=None, description="Timestamp of most recent assessment.")
