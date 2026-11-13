"""
Domain Models, Enums, and Data Transfer Objects for Skill Gap Analysis
and Personalized Learning Roadmaps.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, ConfigDict

from backend.domain.role.models import CompetencyImportance
from backend.domain.transfer.taxonomy import TransferLevel


class SkillGapPriority(str, Enum):
    """Deterministic urgency classification for identified competency gaps."""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    SATISFIED = "SATISFIED"


class RoadmapItemStatus(str, Enum):
    """Lifecycle progression states for individual roadmap milestone items."""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PRACTICING = "PRACTICING"
    COMPLETED = "COMPLETED"


class RoadmapStatus(str, Enum):
    """Overall status of a candidate's personalized roadmap."""
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class CandidateProficiencyState(str, Enum):
    """Evidence-grounded proficiency classification for a role competency."""
    DEMONSTRATED_COMPETENCY = "DEMONSTRATED_COMPETENCY"
    PARTIALLY_DEMONSTRATED = "PARTIALLY_DEMONSTRATED"
    DEMONSTRATED_WEAKNESS = "DEMONSTRATED_WEAKNESS"
    NOT_ASSESSED = "NOT_ASSESSED"
    NO_EVIDENCE = "NO_EVIDENCE"


class SkillGapDTO(BaseModel):
    """
    Structured domain representation of an empirical skill gap.
    Integrates candidate latent mastery, role importance, transfer performance deficit,
    recurring failure patterns, and assistance dependency.
    """
    model_config = ConfigDict(extra="ignore")

    skill_id: str = Field(..., description="Canonical or normalized skill identifier")
    skill_name: str = Field(..., description="Human-readable title")
    role_importance: CompetencyImportance = Field(default=CompetencyImportance.CORE)

    candidate_mastery: float = Field(..., ge=0.0, le=1.0, description="Latent mastery estimate [0.0, 1.0]")
    mastery_uncertainty: float = Field(default=1.0, ge=0.0, le=1.0, description="Epistemic uncertainty [0.1, 1.0]")
    required_mastery: float = Field(..., ge=0.0, le=1.0, description="Proficiency expected by target role tier")
    raw_gap: float = Field(..., ge=0.0, le=1.0, description="max(0, required_mastery - candidate_mastery)")

    highest_transfer_level: TransferLevel = Field(
        default=TransferLevel.L0_RECALL,
        description="Highest transfer distance level demonstrated by candidate"
    )
    transfer_deficit: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Transfer gap penalty representing inability to apply skill in unseen contexts"
    )
    effective_gap: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Composite gap: raw mastery gap plus transfer deficit"
    )
    assistance_dependency: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Assistance Dependency Index (ADI) from coaching scaffold history"
    )
    recurring_failure_types: List[str] = Field(
        default_factory=list,
        description="Diagnosed failure types that occur repeatedly"
    )

    priority_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Deterministic composite score driving priority ranking"
    )
    priority: SkillGapPriority = Field(..., description="Categorical priority level")
    priority_rank: int = Field(default=1, ge=1, description="Sequential ordering rank")
    proficiency_state: CandidateProficiencyState = Field(
        default=CandidateProficiencyState.NOT_ASSESSED,
        description="Evidence-grounded proficiency classification"
    )
    is_measured_proficiency: bool = Field(
        default=False,
        description="True if evidence was derived from assessed interview attempts, False for estimated default priors"
    )

    reasoning: str = Field(..., description="Explainable diagnostic justification for priority")
    learning_objective: str = Field(..., description="Concrete, actionable pedagogical target")
    core_invariants: List[str] = Field(default_factory=list, description="Non-negotiable architectural invariants")
    actionable_steps: List[str] = Field(default_factory=list, description="Targeted practice recommendations")

    @property
    def priority_reason(self) -> str:
        return self.reasoning

    @property
    def transfer_deficit_penalty(self) -> float:
        return self.transfer_deficit

    @property
    def l5_independent_transferred(self) -> bool:
        return self.highest_transfer_level == TransferLevel.L5_INDEPENDENT_TRANSFER


class SkillGapAnalysisResult(BaseModel):
    """
    Complete empirical report of skill gap analysis for a candidate targeting a role.
    """
    model_config = ConfigDict(extra="ignore")

    candidate_id: str
    target_role: str
    seniority: str = "Mid"
    total_competencies_evaluated: int
    satisfied_competencies: int
    gaps_detected: int
    total_role_competencies: int = Field(default=0)
    assessed_competencies_count: int = Field(default=0)
    unassessed_competencies_count: int = Field(default=0)
    excluded_competencies: List[Dict[str, Any]] = Field(default_factory=list)
    gaps: List[SkillGapDTO] = Field(default_factory=list)
    analyzed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RoadmapItemDTO(BaseModel):
    """
    Data transfer object for an actionable milestone item within a personalized roadmap.
    """
    model_config = ConfigDict(extra="ignore")

    id: str
    roadmap_id: str
    skill_id: str
    skill_title: str
    role_importance: str
    priority: SkillGapPriority
    sequence_order: int

    learning_objective: str
    rationale: str

    current_mastery: float
    target_mastery: float
    current_transfer_level: str
    target_transfer_level: str
    assistance_dependency: float

    status: RoadmapItemStatus
    coaching_session_id: Optional[str] = None

    core_invariants: List[str] = Field(default_factory=list)
    recurring_failures: List[str] = Field(default_factory=list)
    actionable_steps: List[str] = Field(default_factory=list)

    # Actionable Milestone details & learning progression
    topics_to_study: List[str] = Field(default_factory=list)
    practical_exercises: List[str] = Field(default_factory=list)
    implementation_task: Dict[str, Any] = Field(default_factory=dict)
    expected_deliverables: List[str] = Field(default_factory=list)
    estimated_duration: str = Field(default="1-2 weeks")
    difficulty_level: str = Field(default="INTERMEDIATE")
    evaluation_criteria: List[str] = Field(default_factory=list)
    evidence_required: Optional[str] = None
    prerequisite_milestone_ids: List[str] = Field(default_factory=list)
    mapping_status: str = Field(default="MAPPED")  # MAPPED, REVIEW_FLAGGED
    is_flagged_for_review: bool = Field(default=False)
    progression_tier: str = Field(default="Tier 1: Assessed, Needs Practice")
    proficiency_state: str = Field(default="NOT_ASSESSED")
    is_measured_proficiency: bool = Field(default=False)

    notes: Optional[str] = None

    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def target_invariants(self) -> List[str]:
        return self.core_invariants


class PersonalizedRoadmapDTO(BaseModel):
    """
    Data transfer object for the complete personalized learning roadmap.
    """
    model_config = ConfigDict(extra="ignore")

    id: str
    candidate_id: str
    target_role: str
    seniority: str
    status: RoadmapStatus

    overall_progress: float = Field(0.0, description="Percentage of roadmap milestones completed [0.0 - 100.0]")
    total_items: int = 0
    completed_items: int = 0
    total_role_competencies: int = 0
    assessed_competencies_count: int = 0
    unassessed_competencies_count: int = 0
    identified_gaps_count: int = 0
    milestones_generated_count: int = 0
    excluded_competencies: List[Dict[str, Any]] = Field(default_factory=list)

    summary: Optional[str] = None
    items: List[RoadmapItemDTO] = Field(default_factory=list)
    meta_info: Dict[str, Any] = Field(default_factory=dict, description="Metadata including web research citations and transfer challenge")

    created_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = Field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_milestones(self) -> int:
        return self.total_items

    @property
    def completed_milestones(self) -> int:
        return self.completed_items

    @property
    def milestones(self) -> List[RoadmapItemDTO]:
        return self.items

    @property
    def seniority_tier(self) -> str:
        return self.seniority


VALID_SENIORITY_TIERS = {"junior": "Junior", "mid": "Mid", "senior": "Senior", "staff": "Staff", "lead": "Lead", "principal": "Principal"}


# API Request/Response Schemas
class GenerateRoadmapRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    candidate_id: str = Field(..., min_length=1)
    target_role: Optional[str] = Field(default=None)
    role_name: Optional[str] = Field(default=None)
    seniority: Optional[str] = Field(default="Mid")

    def model_post_init(self, __context: Any) -> None:
        raw_role = self.target_role or self.role_name
        if not raw_role or not raw_role.strip():
            raise ValueError("Target role is mandatory before generating a roadmap")
        self.target_role = raw_role.strip()
        self.role_name = self.target_role

        sen_key = (self.seniority or "Mid").lower().strip()
        if sen_key not in VALID_SENIORITY_TIERS:
            raise ValueError(f"Invalid seniority tier '{self.seniority}'. Must be one of: Junior, Mid, Senior, Staff, Lead, Principal.")
        self.seniority = VALID_SENIORITY_TIERS[sen_key]


class StartCoachingFromRoadmapResponse(BaseModel):
    item_id: str
    roadmap_id: str
    skill_id: str
    coaching_session_id: str
    orchestrator_state: dict
    training_context: dict
