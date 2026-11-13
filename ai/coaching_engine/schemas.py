"""
Pydantic Schemas for Coaching Intervention Policy and Scaffold Fading Engine.
Enforces strict validation, typed telemetry tracking, and explainable audit trails.
"""

from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from typing import Optional, List, Dict, Any
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, ConfigDict

from backend.domain.transfer.taxonomy import TransferLevel
from backend.domain.transfer.diagnosis_types import TransferFailureType
from backend.domain.transfer.coaching_types import CoachingInterventionType, ScaffoldLevel
from backend.domain.transfer.schemas import (
    TransferFailureDiagnosisDTO,
    CandidateSkillStateDTO,
    CoachingInterventionDecisionDTO,
)


class CoachingHistoryEntry(BaseModel):
    """
    Historical log of a coaching intervention and subsequent candidate outcome.
    Used by policy engine to track assistance dependency and prevent ineffective loops.
    """
    model_config = ConfigDict(extra="forbid")

    intervention_type: CoachingInterventionType = Field(..., description="Administered intervention type.")
    scaffold_level: ScaffoldLevel = Field(..., description="Scaffold level active during turn.")
    failure_type: Optional[TransferFailureType] = Field(default=None, description="Diagnosed failure cause if applicable.")
    outcome: str = Field(default="FAILURE", description="Outcome: 'SUCCESS', 'FAILURE', 'PARTIAL', 'IN_PROGRESS'.")
    hints_requested: int = Field(default=0, ge=0, description="Number of hints requested during that attempt.")
    score: Optional[float] = Field(default=None, ge=0.0, le=10.0, description="Normalized score attained.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of event.")


class CoachingPolicyInput(BaseModel):
    """
    Complete context provided to the Coaching Policy to determine the next action.
    """
    model_config = ConfigDict(extra="forbid")

    diagnosis: TransferFailureDiagnosisDTO = Field(..., description="Root-cause diagnostic assessment from Phase 2B.")
    candidate_state: Optional[CandidateSkillStateDTO] = Field(default=None, description="Longitudinal candidate skill state.")
    current_scaffold_level: ScaffoldLevel = Field(
        default=ScaffoldLevel.LOW_ASSISTANCE,
        description="Scaffold level currently active prior to decision."
    )
    history: List[CoachingHistoryEntry] = Field(
        default_factory=list,
        description="Chronological record of recent coaching events."
    )
    transfer_level: Optional[TransferLevel] = Field(default=None, description="Current transfer task distance rank.")
    retry_count: int = Field(default=0, ge=0, description="Number of consecutive retries on current task.")
    last_outcome: Optional[str] = Field(
        default=None,
        description="Outcome of immediately preceding attempt: 'SUCCESS', 'FAILURE', or None."
    )


class ScaffoldState(BaseModel):
    """
    Result of scaffold transition analysis and assistance dependency tracking.
    """
    model_config = ConfigDict(extra="forbid")

    current_level: ScaffoldLevel = Field(..., description="Decided scaffold level for next turn.")
    previous_level: ScaffoldLevel = Field(..., description="Preceding scaffold level.")
    is_faded: bool = Field(default=False, description="True if scaffold stepped down towards independence.")
    is_escalated: bool = Field(default=False, description="True if scaffold stepped up due to repeated failure.")
    assistance_dependency_index: float = Field(
        default=0.0, ge=0.0, le=1.0,
        description="Deterministic operational metric of candidate assistance dependency."
    )
    transition_reason: str = Field(..., min_length=1, description="Justification for the scaffold level transition.")


class CoachingDecisionRationale(BaseModel):
    """
    Transparent, explainable reasoning justifying why this intervention was selected.
    """
    model_config = ConfigDict(extra="forbid")

    target_failure: TransferFailureType = Field(..., description="Addressed failure category.")
    confidence_category: str = Field(..., description="'HIGH' (>=0.6) or 'LOW' (<0.6).")
    escalation_status: str = Field(..., description="'NONE', 'ESCALATED', 'DE_ESCALATED', 'FADED'.")
    pedagogical_intent: str = Field(..., min_length=1, description="Goal of the selected intervention.")
    audit_trail: str = Field(..., min_length=1, description="Human-readable decision explanation.")


class CoachingPolicyDecision(BaseModel):
    """
    Top-level output of the Coaching Policy Engine.
    Combines domain decision DTO, scaffold metrics, and explainability rationale.
    """
    model_config = ConfigDict(extra="forbid")

    decision: CoachingInterventionDecisionDTO = Field(..., description="Domain DTO ready for persistence and delivery.")
    scaffold_state: ScaffoldState = Field(..., description="Telemetry and transition state of the scaffold.")
    rationale: CoachingDecisionRationale = Field(..., description="Explainable justification for auditability.")
    policy_version: str = Field(default="1.0.0", description="Policy version identifier.")


class CoachingValidationResult(BaseModel):
    """
    Output of the policy decision validator.
    """
    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(..., description="Whether decision satisfies all pedagogical and schema constraints.")
    failure_reasons: List[str] = Field(default_factory=list, description="Validation failure details if invalid.")
