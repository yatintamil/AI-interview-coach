"""
Pydantic schemas for Interview Creation, Sessions, Questions, Answers, Evaluations, and Reports.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class InterviewCreateRequest(BaseModel):
    candidate_id: str
    resume_id: Optional[str] = None
    target_role: Optional[str] = Field(default="Adaptive Omnirole / Universal Software Engineering", description="Target job role or adaptive universal track")
    target_roles: Optional[List[str]] = Field(default=None, description="Multiple target roles for multi-role assessment")
    custom_role_description: Optional[str] = Field(default=None, description="Optional custom user description of target role")
    seniority: Optional[str] = Field(default=None, description="Junior, Mid, Senior, Staff, Principal")
    interview_type: str = Field(default="TECHNICAL", description="TECHNICAL, BEHAVIORAL, or MIXED")
    difficulty_level: str = Field(default="MEDIUM", description="EASY, MEDIUM, or HARD")
    target_question_count: int = Field(default=5, ge=1, le=25)
    coaching_mode: str = Field(default="COACHING", description="COACHING (interactive guidance & hints) or SIMULATION (strict exam)")


class QuestionResponse(BaseModel):
    id: str
    session_id: str
    question_index: int
    question_text: str
    category: str
    topic: str
    difficulty: str
    stage_name: str = Field(default="Foundational Orientation", description="Lifecycle stage of question")
    stage_index: int = Field(default=1, description="Current stage index")
    total_stages: int = Field(default=5, description="Total lifecycle stages")
    target_competency: Optional[str] = Field(default=None, description="Structured role competency evaluated by this question")
    assessment_objective: Optional[str] = Field(default=None, description="Objective and evidence target for this question")
    is_followup: bool = Field(default=False, description="True if this question is an adaptive follow-up probe")
    followup_target_concept: Optional[str] = Field(default=None, description="Specific concept probed if follow-up")
    resume_evidence: Optional[str] = None
    expected_concepts: List[str] = []
    coach_lead_in: Optional[str] = Field(default=None, description="Warm conversational bridge from interviewer")
    researched_skill: Optional[str] = Field(default=None, description="Web-researched skill being evaluated")
    created_at: datetime


class AnswerSubmitRequest(BaseModel):
    answer_text: str = Field(..., min_length=1)
    response_time_seconds: float = Field(default=0.0, ge=0.0)


class EvidenceItem(BaseModel):
    claim: str = Field(..., description="Observation about candidate response")
    basis: str = Field(..., description="Direct quote or specific evidence from candidate answer")


class InterviewDiagnosticEvidence(BaseModel):
    """
    Structured diagnostic evidence produced for evaluated interview responses.
    Captures competencies, shortcomings, mastery signals, and recommended follow-up depth.
    """
    candidate_id: str
    session_id: str
    question_id: str
    competency: str
    skill: str
    score: float
    mastery_signal: str = Field(default="PARTIAL_UNDERSTANDING", description="WEAKNESS_DIAGNOSED, PARTIAL_UNDERSTANDING, PRACTICAL_COMPETENCE, ADVANCED_PROFICIENCY")
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    confidence: float = Field(default=0.85, ge=0.0, le=1.0)
    recommended_followup_depth: str = Field(default="PRACTICAL", description="FOUNDATION, PRACTICAL, FOLLOW_UP, ADVANCED")


class TurnEvaluationResponse(BaseModel):
    id: str
    answer_id: str
    question_id: str
    session_id: str
    overall_score: float = Field(..., ge=0.0, le=10.0)
    correctness: float = Field(default=0.0, ge=0.0, le=10.0)
    completeness: float = Field(default=0.0, ge=0.0, le=10.0)
    relevance: float = Field(default=0.0, ge=0.0, le=10.0)
    technical_depth: float = Field(default=0.0, ge=0.0, le=10.0)
    reasoning: float = Field(default=0.0, ge=0.0, le=10.0)
    strengths: List[str] = []
    weaknesses: List[str] = []
    missing_concepts: List[str] = []
    evidence: List[EvidenceItem] = []
    recommendations: List[str] = []
    exemplar_answer: Optional[str] = Field(default=None, description="Staff Engineer exemplar model response")
    coach_note: Optional[str] = Field(default=None, description="Encouraging Socratic coach feedback")
    detected_feeling: Optional[str] = Field(default=None, description="Candidate emotional state detected by coach")
    coach_conversational_response: Optional[str] = Field(default=None, description="Conversational coach chatbot dialogue")
    socratic_scaffold: Optional[str] = Field(default=None, description="Socratic scaffolding guidance")
    diagnostic_evidence: Optional[InterviewDiagnosticEvidence] = Field(default=None, description="Structured role-aware diagnostic evidence")
    created_at: datetime


class CoachHintRequest(BaseModel):
    partial_answer: Optional[str] = Field(default=None, description="Candidate's partial draft or thoughts")


class CoachHintResponse(BaseModel):
    question_id: str
    hint_text: str
    pedagogical_nudge: str
    key_concept_to_consider: str


class ConcludeInterviewRequest(BaseModel):
    reason: Optional[str] = Field(default="CANDIDATE_REQUESTED", description="Reason for concluding interview")


class TurnAnswerResultResponse(BaseModel):
    evaluation: TurnEvaluationResponse
    next_question: Optional[QuestionResponse] = None
    is_completed: bool = False
    current_question_index: int
    total_questions: int
    active_competency_status: Optional[str] = Field(default=None, description="UNASSESSED, INITIAL_EVIDENCE, PARTIALLY_ASSESSED, SUFFICIENT_EVIDENCE, CONFLICTING_EVIDENCE")
    role_competency_profile: Optional[Dict[str, Any]] = Field(default=None, description="Aggregated role competency profile if completed")
    is_followup_probe: bool = Field(default=False, description="True if next question is a follow-up probe on the same competency")
    diagnostic_evidence: Optional[InterviewDiagnosticEvidence] = Field(default=None, description="Diagnostic evidence from turn")
    completion_reason: Optional[str] = Field(default=None, description="Reason if interview completed: COMPETENCY_COVERAGE_SATISFIED, CANDIDATE_REQUESTED, etc.")
    evidence_coverage_ratio: float = Field(default=0.0, description="Overall evidence coverage ratio (0.0 to 1.0)")
    competencies_assessed_count: int = Field(default=0, description="Number of unique role competencies assessed so far")
    total_competencies_count: int = Field(default=0, description="Total number of core competencies in target role blueprint")
    timing_breakdown: Optional[Dict[str, float]] = Field(default=None, description="Stage-by-stage latency in seconds")


class QuestionTurnHistory(BaseModel):
    question: QuestionResponse
    answer: Optional[Dict[str, Any]] = None
    evaluation: Optional[TurnEvaluationResponse] = None


class SessionReportResponse(BaseModel):
    id: str
    session_id: str
    final_score: float
    technical_score: float
    behavioral_score: float
    communication_score: float
    summary_strengths: List[str] = []
    summary_weaknesses: List[str] = []
    key_recommendations: List[str] = []
    role_competency_profile: Optional[Dict[str, Any]] = Field(default=None, description="Role Competency Profile breakdown")
    generated_at: datetime


class InterviewSessionResponse(BaseModel):
    id: str
    candidate_id: str
    resume_id: Optional[str] = None
    target_role: str
    target_roles: Optional[List[str]] = None
    custom_role_description: Optional[str] = None
    active_competency: Optional[str] = None
    interview_type: str
    difficulty_level: str
    coaching_mode: str = "COACHING"
    status: str
    target_question_count: int
    current_question_index: int
    completion_reason: Optional[str] = None
    evidence_coverage_ratio: float = 0.0
    competencies_assessed_count: int = 0
    total_competencies_count: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    created_at: datetime
    current_question: Optional[QuestionResponse] = None
    history: List[QuestionTurnHistory] = []
    report: Optional[SessionReportResponse] = None


class InterviewSessionListResponse(BaseModel):
    sessions: List[InterviewSessionResponse]
    total: int


class WeaknessRemediationItem(BaseModel):
    question_id: str
    topic: str
    category: str
    skill_id: str
    is_canonical_skill: bool
    overall_score: float
    weaknesses: List[str] = []
    missing_concepts: List[str] = []
    recommendations: List[str] = []
    training_context: Dict[str, Any]


class InterviewWeaknessesResponse(BaseModel):
    session_id: str
    candidate_id: str
    total_weaknesses: int
    weaknesses: List[WeaknessRemediationItem]

