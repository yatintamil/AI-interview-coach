"""
Pydantic Schemas for Transfer Failure Diagnosis operations, request parameters,
deterministic telemetry signals, and validation reports.
"""

from typing import Optional, List, Dict, Any
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, ConfigDict

from backend.domain.transfer.schemas import TransferTaskDefinitionDTO


class DiagnosisRequest(BaseModel):
    """
    Specification submitted to the Transfer Failure Diagnosis Engine containing
    the transfer task, candidate response, existing evaluation metrics,
    telemetry metadata, and longitudinal context.
    """
    model_config = ConfigDict(extra="forbid")

    task: TransferTaskDefinitionDTO = Field(..., description="The transfer evaluation task.")
    candidate_answer: str = Field(..., description="Verbatim response submitted by the candidate.")
    evaluation: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Evaluation output containing overall_score, sub-scores, missing_concepts, weaknesses."
    )
    attempt_metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Attempt telemetry (e.g., hints_requested_count, scaffold_level_applied, response_time_seconds, attempt_number)."
    )
    parent_task_context: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Training task context (surface_context, domain_keywords, prompt) to detect surface pattern leakage."
    )
    candidate_history: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Candidate longitudinal state (recurring_failure_types, past_attempts_count, mastery_estimate)."
    )


class DeterministicSignals(BaseModel):
    """
    Objective, empirical signals extracted deterministically from candidate response,
    evaluation scores, and attempt telemetry without LLM hallucinations.
    """
    model_config = ConfigDict(extra="forbid")

    is_refusal: bool = Field(default=False, description="Whether candidate explicitly declined to answer.")
    is_too_short: bool = Field(default=False, description="Whether response word count is below threshold.")
    word_count: int = Field(default=0, ge=0, description="Word count of candidate response.")
    response_time_seconds: float = Field(default=0.0, ge=0.0, description="Elapsed response time in seconds.")

    concept_coverage_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of expected concepts mentioned.")
    covered_concepts: List[str] = Field(default_factory=list, description="Expected concepts detected in response.")
    missing_expected_concepts: List[str] = Field(default_factory=list, description="Expected concepts omitted.")

    invariants_addressed_ratio: float = Field(default=0.0, ge=0.0, le=1.0, description="Ratio of core invariants addressed.")
    addressed_invariants: List[str] = Field(default_factory=list, description="Core invariants addressed.")
    missing_invariants: List[str] = Field(default_factory=list, description="Core invariants omitted.")

    parent_surface_keyword_hits: List[str] = Field(default_factory=list, description="Parent domain keywords detected.")
    surface_pattern_leakage_detected: bool = Field(default=False, description="Whether candidate relied on training domain keywords.")

    hints_requested_count: int = Field(default=0, ge=0, description="Number of hints or scaffolds requested.")
    scaffold_level_applied: str = Field(default="INDEPENDENT", description="Scaffold level active during attempt.")
    is_scaffold_dependent: bool = Field(default=False, description="Flag indicating excessive assistance requirement.")

    overall_score: float = Field(default=0.0, ge=0.0, le=100.0, description="Normalized overall evaluation score.")
    sub_scores: Dict[str, float] = Field(default_factory=dict, description="Rubric sub-scores (correctness, reasoning, etc.).")

    ambiguity_clarification_detected: bool = Field(default=False, description="Whether candidate sought to clarify unstated parameters in L4.")
    historical_recurring_failures: List[str] = Field(default_factory=list, description="Historical failure patterns for candidate.")


class DiagnosisValidationResult(BaseModel):
    """
    Output of the diagnosis validator ensuring evidence grounding, score bounds,
    and taxonomy compliance.
    """
    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(..., description="Whether diagnosis meets all verification standards.")
    failure_reasons: List[str] = Field(default_factory=list, description="Specific criteria failures if invalid.")
    verbatim_basis_verified: bool = Field(default=True, description="Whether all evidence quotations exist verbatim in the response.")
    confidence_in_bounds: bool = Field(default=True, description="Whether confidence is in [0.0, 1.0].")
    skill_aligned: bool = Field(default=True, description="Whether affected_skill is aligned with task competency.")
