"""
Role Domain Contracts, Types, and Models.

Defines provider-independent and persistence-independent data structures
for structured role representation, role competency blueprints,
assessment plans, and competency evidence tracking.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Union
from pydantic import BaseModel, Field, ConfigDict


class RoleProvenance(str, Enum):
    """Provenance tracking for role intelligence data sources."""
    CURATED = "CURATED"
    USER_PROVIDED = "USER_PROVIDED"
    RESEARCHED = "RESEARCHED"
    FALLBACK = "FALLBACK"


class RoleResearchStatus(str, Enum):
    """Dynamic role web-research execution status."""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    PARTIALLY_RESEARCHED = "PARTIALLY_RESEARCHED"
    UNAVAILABLE = "UNAVAILABLE"
    CACHED = "CACHED"


class RequirementClassification(str, Enum):
    """Granular classification of how a skill relates to market demand."""
    REQUIRED = "REQUIRED"
    PREFERRED = "PREFERRED"
    FREQUENT_INDUSTRY = "FREQUENT_INDUSTRY"
    OPTIONAL_SPECIALIZATION = "OPTIONAL_SPECIALIZATION"
    INFERRED = "INFERRED"


class SourceType(str, Enum):
    """Hierarchy of source reliability for web-researched role intelligence."""
    OFFICIAL_CAREER_PAGE = "OFFICIAL_CAREER_PAGE"
    OFFICIAL_DOCUMENTATION = "OFFICIAL_DOCUMENTATION"
    PROFESSIONAL_FRAMEWORK = "PROFESSIONAL_FRAMEWORK"
    REPUTABLE_PUBLICATION = "REPUTABLE_PUBLICATION"
    JOB_POSTING = "JOB_POSTING"
    OTHER = "OTHER"


class ResearchSourceEvidence(BaseModel):
    """Traceable provenance and evidence citation for an extracted role requirement."""
    model_config = ConfigDict(extra="ignore")

    source_title: str
    url: str
    publisher: str
    retrieval_date: str
    publication_date: Optional[str] = None
    extracted_evidence: str
    associated_competency: Optional[str] = None
    source_type: SourceType = Field(default=SourceType.OTHER)
    reliability_score: float = Field(default=0.70, ge=0.0, le=1.0)


class RoleResearchSpecification(BaseModel):
    """
    Input parameters initiating web-grounded role intelligence research.
    """
    model_config = ConfigDict(extra="ignore")

    role_name: str = Field(..., min_length=1, description="Target role title")
    role_category: Optional[str] = Field(default=None, description="e.g. Software Engineering, Systems, ML")
    industry: Optional[str] = Field(default=None, description="e.g. Fintech, Cloud Infrastructure, Healthcare")
    experience_level: Optional[str] = Field(default=None, description="Junior, Mid, Senior, Staff, Principal")
    target_company: Optional[str] = Field(default=None, description="Optional target organization (e.g. Stripe, AWS)")
    target_location: Optional[str] = Field(default=None, description="Optional geographic or remote context")
    candidate_background: Optional[str] = Field(default=None, description="Summary of candidate's relevant background")
    force_refresh: bool = Field(default=False, description="Bypass cache and force fresh web research")


class CompetencyImportance(str, Enum):
    """Hierarchy of importance for competencies within a role."""
    CORE = "CORE"
    SECONDARY = "SECONDARY"
    SPECIALIZED = "SPECIALIZED"
    CROSS_FUNCTIONAL = "CROSS_FUNCTIONAL"


class CompetencyCoverageStatus(str, Enum):
    """Assessment progress status for an individual competency."""
    UNASSESSED = "UNASSESSED"
    INITIAL_EVIDENCE = "INITIAL_EVIDENCE"
    PARTIALLY_ASSESSED = "PARTIALLY_ASSESSED"
    SUFFICIENT_EVIDENCE = "SUFFICIENT_EVIDENCE"
    CONFLICTING_EVIDENCE = "CONFLICTING_EVIDENCE"


class InterviewCompletionReason(str, Enum):
    """Deterministic reason for ending or halting the adaptive interview."""
    COMPETENCY_COVERAGE_SATISFIED = "COMPETENCY_COVERAGE_SATISFIED"
    LOW_INFORMATION_VALUE = "LOW_INFORMATION_VALUE"
    CANDIDATE_REQUESTED = "CANDIDATE_REQUESTED"
    OPERATIONAL_SAFETY_CEILING = "OPERATIONAL_SAFETY_CEILING"
    SESSION_TIMEOUT = "SESSION_TIMEOUT"
    INFERENCE_BUDGET_EXCEEDED = "INFERENCE_BUDGET_EXCEEDED"
    LOOP_DETECTED = "LOOP_DETECTED"
    SESSION_ABORTED = "SESSION_ABORTED"


class RoleSpecification(BaseModel):
    """
    Candidate input specification for interview targeting.
    Supports single role, multi-role selection, custom role descriptions, and seniority.
    """
    model_config = ConfigDict(extra="ignore")

    role_name: str = Field(..., min_length=1, description="Primary target role title")
    target_roles: List[str] = Field(default_factory=list, description="All selected roles for multi-role interviewing")
    custom_role_description: Optional[str] = Field(default=None, description="Optional user-provided role description")
    seniority: Optional[str] = Field(default=None, description="Junior, Mid, Senior, Staff, Principal")
    is_custom: bool = Field(default=False, description="Flag indicating user-defined custom role")

    def get_all_roles(self) -> List[str]:
        roles = []
        if self.role_name.strip():
            roles.append(self.role_name.strip())
        for r in self.target_roles:
            r_clean = r.strip()
            if r_clean and r_clean not in roles:
                roles.append(r_clean)
        return roles


class RoleCompetency(BaseModel):
    """
    A single granular, testable competency required by a role.
    Distinguishes the assessment target from the specific question asked.
    Enhanced with web-research provenance, requirements classification, and evaluation rubrics.
    """
    model_config = ConfigDict(extra="ignore")

    identifier: str = Field(..., description="Unique slug for competency (e.g. vector_indexing_and_ann)")
    name: str = Field(..., description="Human-readable title (e.g. Vector Indexing & Approximate Nearest Neighbor Search)")
    description: str = Field(..., description="Detailed description of what this competency encompasses")
    category: str = Field(default="software_engineering", description="Technical taxonomy category")
    importance: CompetencyImportance = Field(default=CompetencyImportance.CORE)
    requirement_classification: RequirementClassification = Field(default=RequirementClassification.REQUIRED)
    expected_proficiency: str = Field(default="Proficient", description="Expected proficiency level")
    role_relationship: str = Field(default="primary", description="How competency relates to target role (core, supporting, cross-functional)")
    prerequisites: List[str] = Field(default_factory=list, description="Prerequisite concepts")
    associated_technologies: List[str] = Field(default_factory=list, description="Relevant tools and technologies")
    expected_concepts: List[str] = Field(default_factory=list, description="Key mental models, algorithms, or invariants")
    core_invariants: List[str] = Field(default_factory=list, description="Non-negotiable architectural or algorithmic constraints")
    practical_applications: List[str] = Field(default_factory=list, description="Real-world engineering applications")
    assessment_objectives: List[str] = Field(default_factory=list, description="What the interviewer intends to determine")
    evidence_requirements: List[str] = Field(default_factory=list, description="Concrete signals proving candidate competence")
    evaluation_criteria: List[str] = Field(default_factory=list, description="Objective evaluation rubric criteria")
    supporting_references: List[ResearchSourceEvidence] = Field(default_factory=list, description="Citations supporting requirement")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in market requirement validity")
    difficulty_expectations: str = Field(default="medium", description="Baseline difficulty expectations")
    stage_suitability: int = Field(default=1, ge=1, le=5, description="Recommended interview stage (1-5)")
    provenance: RoleProvenance = Field(default=RoleProvenance.CURATED)


class RoleProfile(BaseModel):
    """
    Structured, provider-independent profile of a professional role.
    Supports both curated baselines and dynamic web-researched market intelligence.
    """
    model_config = ConfigDict(extra="ignore")

    role_name: str = Field(..., description="Display title of the role")
    normalized_role_name: str = Field(..., description="Canonical normalized role key")
    aliases: List[str] = Field(default_factory=list, description="Accepted naming variations")
    role_description: str = Field(default="", description="Comprehensive role overview")
    role_category: Optional[str] = Field(default=None, description="Broad category: Systems, ML, Security, etc.")
    industry: Optional[str] = Field(default=None, description="Industry sector: Fintech, Cloud, E-commerce, etc.")
    experience_level: Optional[str] = Field(default=None, description="Seniority or experience level")
    target_company: Optional[str] = Field(default=None, description="Target company or benchmark employer")
    target_location: Optional[str] = Field(default=None, description="Geographic or remote context")
    research_status: RoleResearchStatus = Field(default=RoleResearchStatus.COMPLETED)
    research_freshness_timestamp: Optional[str] = Field(default=None, description="ISO timestamp of research execution")
    is_cached: bool = Field(default=False, description="Whether returned from local cache")
    responsibilities: List[str] = Field(default_factory=list, description="Primary duties and responsibilities")
    daily_responsibilities: List[str] = Field(default_factory=list, description="Day-to-day operational responsibilities")
    problems_solved: List[str] = Field(default_factory=list, description="Typical engineering problems solved")
    systems_worked_with: List[str] = Field(default_factory=list, description="Architectural systems and platforms")
    key_decisions: List[str] = Field(default_factory=list, description="Technical and architectural decisions made")
    expected_deliverables: List[str] = Field(default_factory=list, description="Expected tangible outputs and artifacts")
    common_tasks: List[str] = Field(default_factory=list, description="Typical engineering workflows")
    knowledge_areas: List[str] = Field(default_factory=list, description="Foundational conceptual domains")
    technical_skills: List[str] = Field(default_factory=list, description="Specific technical proficiencies")
    frequently_required_skills: List[str] = Field(default_factory=list, description="Skills appearing across multiple job postings")
    preferred_skills: List[str] = Field(default_factory=list, description="Bonus or preferred skills")
    tools_and_technologies: List[str] = Field(default_factory=list, description="Standard tools, libraries, and frameworks")
    competencies: List[Union[RoleCompetency, str]] = Field(default_factory=list, description="Structured competencies or identifiers associated with this role")
    engineering_workflows: List[str] = Field(default_factory=list, description="Development, testing, and CI/CD processes")
    architecture_patterns: List[str] = Field(default_factory=list, description="Relevant architecture paradigms")
    failure_scenarios: List[str] = Field(default_factory=list, description="Known production failure modes and trade-offs")
    interview_question_categories: List[Dict[str, Any]] = Field(default_factory=list, description="Researched question categories")
    learning_resources: List[Dict[str, Any]] = Field(default_factory=list, description="Authoritative learning resources and docs")
    source_evidence: List[ResearchSourceEvidence] = Field(default_factory=list, description="Provenance citations")
    seniority_expectations: Dict[str, Any] = Field(default_factory=dict, description="Depth expectations across seniority tiers")
    evidence_sources: List[str] = Field(default_factory=list, description="References/sources informing this profile")
    provenance: RoleProvenance = Field(default=RoleProvenance.CURATED, description="Origin of this role profile")

    @property
    def display_name(self) -> str:
        return self.role_name

    @property
    def description(self) -> str:
        return self.role_description or f"Role profile for {self.role_name}"


class RoleCompetencyBlueprint(BaseModel):
    """
    Comprehensive mapping translating a role specification into structured assessment competencies.
    """
    model_config = ConfigDict(extra="ignore")

    role_name: str
    normalized_role_name: str
    competencies: List[RoleCompetency] = Field(default_factory=list)
    stage_suitability: Dict[int, List[str]] = Field(
        default_factory=dict,
        description="Maps stage index (1-5) to recommended competency identifiers"
    )
    common_competencies: List[str] = Field(default_factory=list, description="Competency IDs shared across multiple selected roles")
    role_specific_competencies: Dict[str, List[str]] = Field(default_factory=dict, description="Role-specific competency IDs by role")
    provenance: RoleProvenance = Field(default=RoleProvenance.CURATED)

    def get_competency(self, identifier: str) -> Optional[RoleCompetency]:
        for c in self.competencies:
            if c.identifier == identifier:
                return c
        return None


class AssessmentPlanConfig(BaseModel):
    """Session-level boundaries and adaptive evidence thresholds."""
    min_questions: int = Field(default=1, ge=1)
    target_questions: int = Field(default=5, ge=1, description="Legacy reference; interview dynamically adapts based on evidence")
    max_questions: int = Field(default=20, ge=1, description="Legacy reference alias for safety ceiling")
    safety_max_questions: int = Field(default=20, ge=1, description="Safety backstop ceiling to prevent runaway costs")
    max_session_duration_seconds: int = Field(default=3600, ge=60, description="Session timeout safeguard in seconds")
    max_repeated_concept_probes: int = Field(default=3, ge=1, description="Loop detection limit for repeated probes on a single competency")
    max_questions_per_stage: int = Field(default=4, ge=1)
    max_followups_per_competency: int = Field(default=2, ge=0)
    min_core_coverage_ratio: float = Field(default=0.75, description="Required evidence coverage ratio across core competencies")


class QuestionDepthLevel(str, Enum):
    """Deterministic question depth policy levels."""
    FOUNDATION = "FOUNDATION"
    PRACTICAL = "PRACTICAL"
    FOLLOW_UP = "FOLLOW_UP"
    ADVANCED = "ADVANCED"


class QuestionPlan(BaseModel):
    """
    Traceable plan generated prior to question synthesis.
    Answers: WHY is this question being asked, what competency is targeted,
    what evidence is required, and at what diagnostic depth?
    """
    model_config = ConfigDict(extra="ignore")

    role: str
    competency_id: str
    competency_name: str
    stage_index: int
    stage_name: str
    objective: str
    difficulty: str = "medium"
    depth_level: str = Field(default=QuestionDepthLevel.FOUNDATION.value, description="FOUNDATION, PRACTICAL, FOLLOW_UP, or ADVANCED")
    expected_concepts: List[str] = Field(default_factory=list)
    core_invariants: List[str] = Field(default_factory=list)
    evidence_requirements: List[str] = Field(default_factory=list)
    candidate_context: Dict[str, Any] = Field(default_factory=dict)
    is_followup: bool = Field(default=False)
    followup_target_concept: Optional[str] = Field(default=None)
    previous_turn_score: Optional[float] = Field(default=None)
    interviewer_action: Optional[str] = Field(default=None, description="Pedagogical action: PROBE_DEEPER_TRADEOFF, PROBE_MISSING_CONCEPT, etc.")
    answer_classification: Optional[str] = Field(default=None, description="STRONG, INCOMPLETE, INCORRECT, AMBIGUOUS, OFF_TOPIC, CONTRADICTORY, REPEATED_OR_EVASIVE")
    transition_rationale: Optional[str] = Field(default=None, description="Explainable rationale for action and progression")
    action_directive: Optional[str] = Field(default=None, description="Prompt instruction for question generation")
    preceding_competency: Optional[str] = Field(default=None, description="Preceding competency evaluated, maintained separately for conversational context")
    rubric_snapshot: Optional[Dict[str, Any]] = Field(default=None, description="Persisted QuestionRubric snapshot")


class CompetencyEvidenceRecord(BaseModel):
    """
    Tracks empirical evidence gathered for a specific competency across interview turns.
    Maintains demonstrated concepts, missing concepts, misconceptions, and evidence confidence.
    """
    model_config = ConfigDict(extra="ignore")

    competency_id: str
    competency_name: str
    stage_index: int
    questions_asked: int = Field(default=0)
    scores: List[float] = Field(default_factory=list)
    evidence_items: List[str] = Field(default_factory=list)
    demonstrated_concepts: List[str] = Field(default_factory=list)
    missing_concepts: List[str] = Field(default_factory=list)
    misconceptions: List[str] = Field(default_factory=list)
    question_history: List[str] = Field(default_factory=list)
    evaluation_history: List[Dict[str, Any]] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    evidence_confidence: float = Field(default=0.0, description="0.0 to 1.0 assessment certainty")
    assessment_coverage: float = Field(default=0.0, description="0.0 to 1.0 demonstrated concept coverage")
    last_assessment_timestamp: Optional[str] = Field(default=None)
    coverage_status: CompetencyCoverageStatus = Field(default=CompetencyCoverageStatus.UNASSESSED)


class AssessmentPlan(BaseModel):
    """
    Dynamic assessment plan orchestrating progressive evaluation across the 5 interview stages.
    Continues dynamically until sufficient assessment evidence is collected or explicitly ended.
    """
    model_config = ConfigDict(extra="ignore")

    plan_id: str
    role_name: str
    stages: Dict[int, List[str]] = Field(default_factory=dict, description="Stage index (1-5) -> List of competency IDs")
    current_stage_index: int = Field(default=1)
    current_competency_id: Optional[str] = Field(default=None)
    completed_competency_ids: List[str] = Field(default_factory=list)
    total_questions_asked: int = Field(default=0)
    competency_evidence: Dict[str, CompetencyEvidenceRecord] = Field(default_factory=dict)
    config: AssessmentPlanConfig = Field(default_factory=AssessmentPlanConfig)
    completion_reason: Optional[str] = Field(default=None, description="Explicit deterministic reason for ending interview")
    evidence_coverage_ratio: float = Field(default=0.0, description="Overall evidence coverage across all role competencies (0.0 to 1.0)")
    is_completed: bool = Field(default=False)
    is_halted_by_safeguard: bool = Field(default=False, description="True if stopped prematurely by an emergency operational guard")


class RoleCompetencyProfile(BaseModel):
    """
    Final granular profile of candidate performance across all role competencies.
    """
    model_config = ConfigDict(extra="ignore")

    role_name: str
    competency_records: Dict[str, CompetencyEvidenceRecord] = Field(default_factory=dict)
    overall_coverage_ratio: float = Field(default=0.0)
    sufficient_evidence_count: int = Field(default=0)
    partially_assessed_count: int = Field(default=0)
    unassessed_count: int = Field(default=0)
    summary_strengths: List[str] = Field(default_factory=list)
    summary_weaknesses: List[str] = Field(default_factory=list)


class CandidateEvidenceStrength(str, Enum):
    """Strength of candidate evidence for a competency."""
    STRONG = "STRONG"
    MODERATE = "MODERATE"
    WEAK = "WEAK"
    NONE = "NONE"


class CompetencyMatchDetail(BaseModel):
    """Granular comparison of a candidate's evidence against a role competency."""
    model_config = ConfigDict(extra="ignore")

    competency_id: str
    competency_name: str
    category: str = "software_engineering"
    importance: CompetencyImportance = CompetencyImportance.CORE
    role_requirement_classification: RequirementClassification = RequirementClassification.REQUIRED
    has_candidate_evidence: bool = False
    evidence_strength: CandidateEvidenceStrength = Field(default=CandidateEvidenceStrength.NONE)
    assessment_status: CompetencyCoverageStatus = Field(default=CompetencyCoverageStatus.UNASSESSED)
    current_demonstrated_proficiency: Optional[str] = None
    expected_role_proficiency: str = "Proficient"
    is_skill_gap: bool = False
    skill_gap_severity: Optional[str] = None  # None, "MINOR", "MODERATE", "CRITICAL"
    diagnosis_confidence: float = 0.0
    rationale: str = ""
    candidate_evidence_citations: List[str] = Field(default_factory=list)
    supporting_research_references: List[ResearchSourceEvidence] = Field(default_factory=list)


class CandidateRoleMatchAssessment(BaseModel):
    """
    Comprehensive alignment assessment comparing researched role requirements
    with actual candidate evidence (resume, claimed skills, project skills, and interview capability).
    """
    model_config = ConfigDict(extra="ignore")

    candidate_id: str
    role_name: str
    normalized_role_name: str
    match_score: float = Field(default=0.0, ge=0.0, le=1.0)
    matched_competencies: List[CompetencyMatchDetail] = Field(default_factory=list)
    unmatched_candidate_skills: List[str] = Field(
        default_factory=list,
        description="Preserved candidate skills that are valid but not explicitly required by the target role"
    )
    critical_gaps: List[str] = Field(default_factory=list)
    moderate_gaps: List[str] = Field(default_factory=list)
    verified_strengths: List[str] = Field(default_factory=list)
    overall_assessment_summary: str = ""

