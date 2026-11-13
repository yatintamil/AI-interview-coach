"""
Pydantic Schemas for Transfer-Aware Coaching Orchestrator.
Defines session configurations, turn step inputs, results, and research telemetry records.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, ConfigDict

from backend.domain.transfer.taxonomy import TransferLevel
from backend.domain.transfer.coaching_types import (
    CoachingInterventionType,
    ScaffoldLevel,
    CoachingLoopOutcome,
)
from backend.domain.transfer.schemas import (
    TransferTaskDefinitionDTO,
    TransferFailureDiagnosisDTO,
    CoachingInterventionDecisionDTO,
    CandidateSkillStateDTO,
)
from ai.coaching_engine.schemas import ScaffoldState, CoachingHistoryEntry
from ai.coaching_orchestrator.state_machine import CoachingState, StateTransitionRecord


class CoachingSessionConfig(BaseModel):
    """
    Configuration parameters governing retry thresholds, transfer distance, and pass criteria.
    """
    model_config = ConfigDict(extra="forbid")

    max_retries: int = Field(default=2, ge=1, le=5, description="Maximum consecutive remediation retries allowed.")
    transfer_level: TransferLevel = Field(default=TransferLevel.L2_NEAR_TRANSFER, description="Initial transfer distance level.")
    independent_level: TransferLevel = Field(default=TransferLevel.L5_INDEPENDENT_TRANSFER, description="Distance level for unassisted post-coaching challenge.")
    pass_threshold: float = Field(default=7.0, ge=1.0, le=10.0, description="Normalized score threshold required to pass a routine turn.")
    independent_pass_threshold: float = Field(default=8.5, ge=8.5, le=10.0, description="Canonical score threshold strictly required for L5 Independent Transfer. Cannot be lowered below 8.5.")
    min_independent_distance: float = Field(default=0.70, ge=0.70, le=1.0, description="Canonical minimum transfer distance D required for L5 Independent Transfer. Cannot be lowered below 0.70.")
    policy_version: str = Field(default="1.0.0", description="Policy engine version identifier.")


class TrainingContext(BaseModel):
    """
    Specification of the training problem that anchors invariant preservation during transfer.
    """
    model_config = ConfigDict(extra="forbid")

    task_id: str = Field(..., min_length=1, description="Unique identifier of training question/task.")
    question_text: str = Field(..., min_length=1, description="Verbatim question prompt of the training task.")
    skill_id: str = Field(..., min_length=1, description="Target competency evaluated (e.g., 'distributed_caching').")
    core_invariants: List[str] = Field(..., min_length=1, description="Structural principles that must transfer.")
    base_surface_context: str = Field(..., min_length=1, description="Original training surface domain (e.g., 'URL Shortener').")
    base_expected_concepts: List[str] = Field(..., min_length=1, description="Technical mechanisms required in the baseline.")
    topic: Optional[str] = Field(default=None, description="Broad category/topic label.")
    target_role: Optional[str] = Field(default=None, description="Target role evaluated against.")
    weakness: Optional[str] = Field(default=None, description="Diagnosed weakness from interview.")
    evidence: Optional[List[str]] = Field(default=None, description="Evidence citations from interview.")
    current_mastery: Optional[float] = Field(default=None, description="Current mastery level (0.0 to 1.0).")
    transfer_level: Optional[str] = Field(default=None, description="Current validated transfer level.")
    role_importance: Optional[str] = Field(default=None, description="Role importance tier (e.g., CORE, IMPORTANT).")
    learning_objective: Optional[str] = Field(default=None, description="Target pedagogical learning objective.")
    teaching_lesson: Optional[str] = Field(default=None, description="Structured teaching lesson (explain, example, check).")


class CandidateStepInput(BaseModel):
    """
    Candidate response payload submitted for evaluation at a given turn.
    """
    model_config = ConfigDict(extra="forbid")

    candidate_answer: str = Field(..., description="Candidate verbatim answer text.")
    response_time_seconds: float = Field(default=0.0, ge=0.0, description="Elapsed response time in seconds.")
    hints_requested_count: int = Field(default=0, ge=0, description="Number of hints requested by candidate during attempt.")


class OrchestratorStepResult(BaseModel):
    """
    Comprehensive result of an orchestrated coaching turn.
    Contains evaluation, diagnostics, active intervention, scaffold telemetry, and lifecycle state.
    """
    model_config = ConfigDict(extra="forbid")

    state: CoachingState = Field(..., description="Current lifecycle state after processing.")
    outcome: CoachingLoopOutcome = Field(..., description="Classified outcome of this turn.")
    task: Optional[TransferTaskDefinitionDTO] = Field(default=None, description="Active task definition.")
    evaluation: Optional[Dict[str, Any]] = Field(default=None, description="Evaluation score, sub-scores, strengths, weaknesses.")
    diagnosis: Optional[TransferFailureDiagnosisDTO] = Field(default=None, description="Root-cause diagnostic assessment.")
    intervention: Optional[CoachingInterventionDecisionDTO] = Field(default=None, description="Administered intervention decision.")
    scaffold_state: Optional[ScaffoldState] = Field(default=None, description="Scaffold fading and assistance dependency state.")
    retry_count: int = Field(default=0, ge=0, description="Consecutive retry count for current task.")
    retry_limit_reached: bool = Field(default=False, description="Flag indicating whether max retry limit was reached.")
    candidate_state: Optional[CandidateSkillStateDTO] = Field(default=None, description="Updated longitudinal candidate skill state.")
    training_context: Optional[TrainingContext] = Field(default=None, description="Anchor training context.")
    session_id: Optional[str] = Field(default=None, description="Coaching session ID.")
    candidate_id: Optional[str] = Field(default=None, description="Candidate ID.")
    transition_reason: Optional[str] = Field(default=None, description="Reason for the last state transition.")


class ResearchTelemetryRecord(BaseModel):
    """
    Complete audit trail of the candidate's transfer coaching journey.
    Preserves all experimental data points required to validate transfer hypotheses.
    """
    model_config = ConfigDict(extra="forbid")

    candidate_id: str = Field(..., min_length=1, description="Candidate ID.")
    session_id: str = Field(..., min_length=1, description="Interview session ID.")
    skill_id: str = Field(..., min_length=1, description="Competency key.")
    training_context: TrainingContext = Field(..., description="Anchor training task context.")
    transfer_task_id: Optional[str] = Field(default=None, description="First transfer task ID.")
    transfer_level: TransferLevel = Field(..., description="Transfer distance level.")
    independent_task_id: Optional[str] = Field(default=None, description="Independent transfer task ID.")
    
    attempts_history: List[Dict[str, Any]] = Field(default_factory=list, description="Chronological log of attempt evaluations.")
    coaching_history: List[CoachingHistoryEntry] = Field(default_factory=list, description="History of coaching interventions.")
    state_transitions: List[StateTransitionRecord] = Field(default_factory=list, description="Audit of all state machine transitions.")
    
    final_outcome: CoachingLoopOutcome = Field(..., description="Overall terminal outcome of the coaching loop.")
    final_mastery_estimate: float = Field(default=0.0, ge=0.0, le=1.0, description="Final mastery estimate.")
    final_mastery_uncertainty: float = Field(default=1.0, ge=0.0, le=1.0, description="Final mastery uncertainty.")
    assistance_dependency_index: float = Field(default=0.0, ge=0.0, le=1.0, description="Final ADI metric.")
    
    policy_version: str = Field(default="1.0.0", description="Policy version used.")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Record creation timestamp.")
