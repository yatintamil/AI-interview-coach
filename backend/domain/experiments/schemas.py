"""
Domain schemas and Pydantic models for the experimental framework.
Enforces validation, reproducibility configuration, and separation of raw observations from derived metrics.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

from backend.domain.experiments.enums import (
    ExperimentCondition,
    ExperimentPhase,
    ExperimentOutcome,
    TaskDifficulty,
)


class ExperimentConfig(BaseModel):
    """
    Configuration parameters governing an experimental session.
    All parameters are explicit and configurable to ensure scientific reproducibility.
    """
    condition: ExperimentCondition = Field(..., description="Experimental condition/treatment")
    skill: str = Field(default="distributed_caching", description="Target skill under investigation")
    task_set_id: str = Field(default="sysdesign_distributed_cache_v1", description="Standard task set identifier")
    random_seed: int = Field(default=42, description="Seed for deterministic task sampling and ordering")
    retry_limit: int = Field(default=2, ge=0, le=5, description="Maximum retries permitted upon failure")

    # Component versions for strict experimental traceability
    evaluator_version: str = Field(default="v1.0", description="Evaluator engine version")
    coaching_policy_version: str = Field(default="v1.0", description="Coaching policy version")
    transfer_engine_version: str = Field(default="v1.0", description="Transfer task generator version")
    diagnosis_engine_version: str = Field(default="v1.0", description="Diagnosis engine version")

    # Baseline B adaptive difficulty thresholds
    difficulty_threshold_high: float = Field(default=0.75, ge=0.0, le=1.0, description="Threshold for difficulty step-up")
    difficulty_threshold_low: float = Field(default=0.50, ge=0.0, le=1.0, description="Threshold for difficulty step-down")

    # Reproducibility & Longitudinal Trial Metadata
    participant_cohort: Optional[str] = Field(default=None, description="Cohort tag (e.g., 'cohort_2026_q1')")
    session_type: str = Field(default="PRIMARY", description="Session type: 'PRIMARY' or 'DELAYED_RETENTION'")
    parent_session_id: Optional[str] = Field(default=None, description="Linked primary session ID for longitudinal retention")
    delay_days: Optional[float] = Field(default=None, ge=0.0, description="Elapsed days since primary session")

    # Participant Onboarding, Consent & Protocol Controls
    require_consent: bool = Field(default=False, description="Whether verified server-side informed consent is required for enrollment")
    informed_consent_signed: bool = Field(default=False, description="Whether participant acknowledged and signed informed consent")
    consent_version: Optional[str] = Field(default=None, description="Informed consent protocol version tag")
    max_task_duration_seconds: int = Field(default=600, ge=60, description="Time limit per task in seconds")
    standardized_instructions_acknowledged: bool = Field(default=False, description="Participant confirmed reading standardized instructions")
    abandonment_reason: Optional[str] = Field(default=None, description="Reason for session abandonment if incomplete")
    form_order: str = Field(default="FORM_AB", description="Form crossover order: 'FORM_AB' (Form A Pre, Form B Post) or 'FORM_BA' (Form B Pre, Form A Post)")
    execution_provenance: str = Field(default="SYNTHETIC", description="Provenance tag: 'SYNTHETIC', 'HUMAN_PILOT', 'HUMAN_STUDY'")

    model_config = ConfigDict(extra="forbid")


class ConsentSubmissionInput(BaseModel):
    """Input payload for recording participant informed consent."""
    candidate_id: str = Field(..., min_length=1, description="Candidate ID")
    consent_version: str = Field(default="v1.0-feasibility-study", description="Consent document version")
    agreed: bool = Field(default=True, description="Explicit agreement to study terms")
    study_metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional client telemetry or signature metadata")

    model_config = ConfigDict(extra="forbid")


class ConsentRecordDTO(BaseModel):
    """Authoritative DTO representing persisted participant informed consent."""
    id: str
    candidate_id: str
    consent_status: str
    consent_version: str
    consented_at: datetime
    withdrawn_at: Optional[datetime] = None
    withdrawal_reason: Optional[str] = None
    study_title: str


class StudyInformationDTO(BaseModel):
    """Configurable study metadata presented during participant onboarding."""
    study_id: str
    title: str
    principal_investigator: str
    purpose: str
    procedures: str
    risks_and_benefits: str
    voluntary_participation: str
    data_handling: str
    ethics_statement: str
    consent_version: str
    withdrawal_policy: str


class ParticipantWithdrawalInput(BaseModel):
    """Payload for voluntary study withdrawal."""
    candidate_id: str = Field(..., min_length=1, description="Candidate ID requesting withdrawal")
    reason: Optional[str] = Field(default=None, description="Optional qualitative withdrawal rationale")
    data_policy: str = Field(default="EXCLUDE_FROM_ANALYSIS", description="Data handling policy: 'EXCLUDE_FROM_ANALYSIS'")

    model_config = ConfigDict(extra="forbid")


class ParticipantWithdrawalResultDTO(BaseModel):
    """Result returned after recording study withdrawal."""
    candidate_id: str
    status: str
    withdrawn_at: datetime
    sessions_abandoned: int
    retention_schedules_cancelled: int
    message: str


class RetentionScheduleDTO(BaseModel):
    """DTO representing a scheduled longitudinal retention follow-up."""
    id: str
    session_id: str
    candidate_id: str
    delay_days: int
    due_date: datetime
    status: str
    retention_session_id: Optional[str] = None
    created_at: datetime


class ExperimentTrialRaw(BaseModel):
    """
    Immutable raw observation captured during an individual experimental trial.
    Serves as ground truth for all subsequent scientific derivations.
    """
    trial_id: str = Field(..., description="Unique trial identifier")
    session_id: str = Field(..., description="Parent experiment session ID")
    task_id: str = Field(..., description="Evaluated task ID")
    phase: ExperimentPhase = Field(..., description="Current experiment phase")
    transfer_level: Optional[str] = Field(default=None, description="Transfer taxonomy level if applicable")
    transfer_distance: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Situational transfer distance metric D from training domain")
    difficulty: Optional[TaskDifficulty] = Field(default=None, description="Task difficulty tier if applicable")

    attempt_number: int = Field(default=1, ge=1, description="Attempt number for this task")
    score: float = Field(..., ge=0.0, le=1.0, description="Evaluator overall score")
    outcome: ExperimentOutcome = Field(..., description="Trial outcome")
    response_time_seconds: float = Field(default=0.0, ge=0.0, description="Candidate response time")

    feedback_text: Optional[str] = Field(default=None, description="Feedback text delivered to candidate")
    candidate_answer_text: Optional[str] = Field(default=None, description="Exact text answer submitted by candidate")
    intervention_type: Optional[str] = Field(default=None, description="Coaching intervention type if applicable")
    scaffold_level: Optional[str] = Field(default=None, description="Scaffold level if applicable")
    hints_requested_count: int = Field(default=0, ge=0, description="Hints consumed during trial")
    retry_count: int = Field(default=0, ge=0, description="Retry counter at time of trial")

    # Evaluator Traceability & Provenance (Audit requirement)
    evaluator_provider: Optional[str] = Field(default="GROUNDED_NLP", description="Evaluator engine provider (e.g., 'GROUNDED_NLP', 'LLM_MOCK', 'NVIDIA_NIM')")
    evaluator_version: Optional[str] = Field(default="v1.0", description="Evaluator engine version")
    rubric_version: Optional[str] = Field(default="technical_v1", description="Evaluation rubric version")
    evaluator_fallback: bool = Field(default=False, description="True if evaluation fell back from primary engine/LLM")
    fallback_reason: Optional[str] = Field(default=None, description="Reason for evaluator fallback if applicable")
    form_id: Optional[str] = Field(default="FORM_A", description="Task form identifier (e.g. 'FORM_A', 'FORM_B')")
    execution_provenance: str = Field(default="SYNTHETIC", description="Provenance tag: 'SYNTHETIC', 'HUMAN_PILOT', 'HUMAN_STUDY'")

    # Condition C specific diagnostic telemetry (null for baselines)
    diagnosis_type: Optional[str] = Field(default=None, description="Diagnosed transfer failure mode")
    diagnosis_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Diagnostic confidence")
    affected_skill: Optional[str] = Field(default=None, description="Skill dimension diagnosed with deficit")
    diagnostic_evidence: Optional[List[Dict[str, Any]]] = Field(default=None, description="Causal evidence items")

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="UTC timestamp of trial completion")

    model_config = ConfigDict(extra="ignore")


class ExperimentDerivedMetrics(BaseModel):
    """
    Scientifically derived metrics computed on-demand from raw observations.
    Does NOT modify the raw observation ground truth.
    """
    session_id: str
    condition: ExperimentCondition
    pretest_score: Optional[float] = None
    training_mean_score: Optional[float] = None
    posttest_score: Optional[float] = None
    transfer_test_score: Optional[float] = None
    independent_transfer_score: Optional[float] = None

    # Normalized learning gain: (posttest - pretest) / (1.0 - pretest) if pretest < 1.0
    normalized_gain: Optional[float] = None
    transfer_delta: Optional[float] = None  # transfer_test_score - posttest_score

    total_hints_consumed: int = 0
    total_retries: int = 0
    total_interventions: int = 0
    retry_recovery_success: bool = False
    independent_transfer_success: bool = False


class ExperimentStepInput(BaseModel):
    """Candidate input payload for advancing an experimental trial."""
    candidate_answer: str = Field(..., min_length=1, description="Candidate response text")
    hints_requested: int = Field(default=0, ge=0, description="Hints requested for this trial")
    response_time_seconds: float = Field(default=0.0, ge=0.0, description="Response time elapsed")

    model_config = ConfigDict(extra="forbid")



class ExperimentStepResult(BaseModel):
    """Result returned after an experimental step turn."""
    session_id: str
    condition: ExperimentCondition
    phase: ExperimentPhase
    task_id: str
    task_prompt: str
    task_difficulty: Optional[TaskDifficulty] = None
    transfer_level: Optional[str] = None
    score: Optional[float] = None
    feedback: Optional[str] = None
    intervention: Optional[str] = None
    scaffold_level: Optional[str] = None
    is_complete: bool = False
    raw_trial: Optional[ExperimentTrialRaw] = None


class ExperimentSessionDTO(BaseModel):
    """Structured Data Transfer Object representing complete experiment session state."""
    session_id: str
    candidate_id: str
    experiment_name: str
    condition: ExperimentCondition
    skill: str
    task_set_id: str
    config: ExperimentConfig
    current_phase: ExperimentPhase
    status: str
    start_time: datetime
    end_time: Optional[datetime] = None
    trials: List[ExperimentTrialRaw] = Field(default_factory=list)
    derived_metrics: Optional[ExperimentDerivedMetrics] = None
