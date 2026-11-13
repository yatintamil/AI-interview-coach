"""
Candidate Readiness Application Service.
Provides authoritative lifecycle evaluation, prerequisite validation, and feature gating.
Ensures personalized endpoints never fabricate candidate evidence or bypass required milestones.
"""

from typing import Optional, List, Dict, Any
# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from backend.schemas.readiness import (
    CandidateReadinessState,
    CandidateReadinessResponse,
)
from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.resume_repository import ResumeRepository
from backend.repositories.interview_repository import InterviewSessionRepository
from backend.repositories.skill_state_repository import CandidateSkillStateRepository
from backend.repositories.transfer_task_repository import TransferAttemptRepository


class CandidateReadinessService:
    """
    Authoritative service governing candidate lifecycle progression and readiness gates.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.candidate_repo = CandidateRepository(session)
        self.resume_repo = ResumeRepository(session)
        self.interview_repo = InterviewSessionRepository(session)
        self.skill_state_repo = CandidateSkillStateRepository(session)
        self.transfer_attempt_repo = TransferAttemptRepository(session)

    async def get_candidate_readiness(
        self,
        candidate_id: str,
        target_role_hint: Optional[str] = None,
    ) -> CandidateReadinessResponse:
        """
        Evaluates the empirical readiness state of an authenticated candidate.
        Grounded strictly in persistent database records.
        """
        candidate = await self.candidate_repo.get(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found.",
            )

        # 1. Resume Verification
        resumes = await self.resume_repo.list_by_candidate(candidate_id)
        is_resume_uploaded = len(resumes) > 0
        active_resumes = [r for r in resumes if getattr(r, "is_active", True) and r.processing_status == "COMPLETED"]
        processing_resumes = [r for r in resumes if r.processing_status == "PROCESSING"]
        is_resume_processed = len(active_resumes) > 0

        # 2. Profile & Extracted Evidence Verification
        profile = await self.candidate_repo.get_profile(candidate_id)
        is_profile_ready = bool(
            is_resume_processed
            and profile
            and profile.profile_data
            and (profile.skills_flat or profile.profile_data.get("skills"))
        )

        # 3. Role Selection Resolution
        target_role: Optional[str] = target_role_hint
        if not target_role and profile and profile.profile_data:
            target_role = profile.profile_data.get("target_role")
            if not target_role and profile.profile_data.get("recommended_roles"):
                target_role = profile.profile_data["recommended_roles"][0]
        if not target_role and hasattr(candidate, "target_role") and getattr(candidate, "target_role", None):
            target_role = getattr(candidate, "target_role")

        is_role_selected = bool(target_role and target_role.strip())

        # 4. Assessment & Interview Evidence Verification
        sessions = await self.interview_repo.list_by_candidate(candidate_id, limit=200)
        completed_sessions = [
            s for s in sessions if s.status == "COMPLETED" and (getattr(s, "report", None) or s.overall_score is not None)
        ]
        completed_interviews_count = len(completed_sessions)
        is_assessment_ready = completed_interviews_count > 0

        # 5. Longitudinal Skill State & Gap Diagnosis Verification
        skill_states = await self.skill_state_repo.list_by_candidate(candidate_id)
        is_coaching_ready = len(skill_states) > 0 or is_assessment_ready

        # 6. Transfer Eligibility Verification
        transfer_attempts = await self.transfer_attempt_repo.list_by_candidate(candidate_id)
        is_transfer_ready = bool(is_coaching_ready and len(transfer_attempts) > 0)

        # Determine Authoritative Readiness State
        if not is_resume_uploaded:
            state = CandidateReadinessState.NO_RESUME
        elif not is_resume_processed and len(processing_resumes) > 0:
            state = CandidateReadinessState.RESUME_PROCESSING
        elif not is_profile_ready:
            # Uploaded but failed or incomplete profile extraction
            state = CandidateReadinessState.RESUME_PROCESSING
        elif not is_role_selected:
            state = CandidateReadinessState.PROFILE_READY
        elif not is_assessment_ready:
            state = CandidateReadinessState.ROLE_READY
        elif not is_coaching_ready:
            state = CandidateReadinessState.ASSESSMENT_READY
        elif not is_transfer_ready:
            state = CandidateReadinessState.COACHING_READY
        else:
            state = CandidateReadinessState.TRANSFER_READY

        # Allowed vs Blocked Feature Maps
        allowed_features: List[str] = ["platform_overview", "generic_role_catalog", "resume_upload"]
        blocked_features: Dict[str, str] = {}
        next_action: Dict[str, str] = {}

        if state == CandidateReadinessState.NO_RESUME:
            blocked_features = {
                "personalized_profile": "Upload an engineering resume to extract verified skills and experience.",
                "evidence_graph": "Atomic claim decomposition requires parsed resume text.",
                "skill_gap_analysis": "Skill gaps require candidate evidence before comparing against role requirements.",
                "personalized_roadmap": "A personalized roadmap requires verified candidate evidence and target role alignment.",
                "targeted_coaching": "Targeted coaching requires empirical skill gap diagnosis.",
                "transfer_challenge": "Transfer tasks require prior coaching context and diagnosed skill gaps.",
            }
            next_action = {
                "action": "UPLOAD_RESUME",
                "route": "/resume",
                "title": "Upload Engineering Resume",
                "rationale": "Anchor your technical practice and personalized coaching in verifiable document evidence.",
            }
        elif state == CandidateReadinessState.RESUME_PROCESSING:
            blocked_features = {
                "personalized_profile": "Resume document parsing and entity extraction is currently in progress.",
                "skill_gap_analysis": "Skill gaps require parsed resume entities.",
                "personalized_roadmap": "Roadmap generation requires completed resume extraction.",
            }
            next_action = {
                "action": "AWAIT_PROCESSING",
                "route": "/resume",
                "title": "Parsing Resume Evidence",
                "rationale": "Extracting verifiable technical claims and architectural experience from your document.",
            }
        elif state == CandidateReadinessState.PROFILE_READY:
            allowed_features.extend(["personalized_profile", "evidence_graph", "target_role_selection"])
            blocked_features = {
                "skill_gap_analysis": "Select a target engineering role to compare against your verified evidence.",
                "personalized_roadmap": "Select a target engineering role to generate tailored milestones.",
                "targeted_coaching": "Select a target role and complete an assessment to identify focus areas.",
            }
            next_action = {
                "action": "SELECT_ROLE",
                "route": "/roles",
                "title": "Select Target Engineering Role",
                "rationale": "Align your verified resume skills against calibrated competency blueprints.",
            }
        elif state == CandidateReadinessState.ROLE_READY:
            allowed_features.extend([
                "personalized_profile",
                "evidence_graph",
                "target_role_selection",
                "role_requirements",
                "interview_assessment",
            ])
            blocked_features = {
                "calibrated_roadmap": "Complete a baseline interview assessment to calibrate empirical gaps beyond self-reported resume claims.",
                "targeted_coaching": "Take your planned interview assessment to diagnose specific failure modes and invariants.",
            }
            next_action = {
                "action": "START_ASSESSMENT",
                "route": "/interview",
                "title": f"Take Planned Assessment for {target_role or 'Target Role'}",
                "rationale": "Complete an adaptive technical interview gauntlet to reveal true conceptual depth.",
            }
        elif state == CandidateReadinessState.ASSESSMENT_READY:
            allowed_features.extend([
                "personalized_profile",
                "evidence_graph",
                "target_role_selection",
                "role_requirements",
                "interview_assessment",
                "assessment_debrief",
                "skill_gap_analysis",
                "personalized_roadmap",
                "targeted_coaching",
            ])
            next_action = {
                "action": "REVIEW_ROADMAP_OR_COACH",
                "route": "/roadmap",
                "title": "Inspect Personalized Roadmap",
                "rationale": "Review diagnosed skill gaps and initiate targeted Socratic coaching.",
            }
        else: # COACHING_READY or TRANSFER_READY
            allowed_features.extend([
                "personalized_profile",
                "evidence_graph",
                "target_role_selection",
                "role_requirements",
                "interview_assessment",
                "assessment_debrief",
                "skill_gap_analysis",
                "personalized_roadmap",
                "targeted_coaching",
                "transfer_challenge",
            ])
            next_action = {
                "action": "PRACTICE_TRANSFER",
                "route": "/coaching",
                "title": "Engage in Transfer Practice",
                "rationale": "Demonstrate independent invariant reasoning with fading scaffolding.",
            }

        return CandidateReadinessResponse(
            candidate_id=candidate_id,
            readiness_state=state,
            is_resume_uploaded=is_resume_uploaded,
            is_resume_processed=is_resume_processed,
            is_profile_ready=is_profile_ready,
            is_role_selected=is_role_selected,
            target_role=target_role,
            is_assessment_ready=is_assessment_ready,
            completed_interviews_count=completed_interviews_count,
            is_coaching_ready=is_coaching_ready,
            is_transfer_ready=is_transfer_ready,
            allowed_features=allowed_features,
            blocked_features=blocked_features,
            next_action=next_action,
        )

    async def assert_has_processed_resume(
        self,
        candidate_id: str,
        feature_name: str = "This personalized feature",
    ) -> None:
        """
        Enforces that the candidate has an uploaded and completed resume before accessing personalized endpoints.
        Raises HTTP 428 Precondition Required if prerequisite is unmet.
        """
        readiness = await self.get_candidate_readiness(candidate_id)
        if not readiness.is_resume_processed or not readiness.is_profile_ready:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail={
                    "error": "PREREQUISITE_MISSING",
                    "readiness_state": readiness.readiness_state.value,
                    "message": f"{feature_name} requires a processed engineering resume. Candidate evidence has not been grounded yet.",
                    "required_action": "UPLOAD_RESUME",
                    "route": "/resume",
                },
            )

    async def assert_has_candidate_evidence(
        self,
        candidate_id: str,
        feature_name: str = "This personalized feature",
    ) -> None:
        """
        Enforces that the candidate has either a processed resume profile OR real assessment/skill state evidence.
        Raises HTTP 428 Precondition Required if no evidence exists.
        """
        readiness = await self.get_candidate_readiness(candidate_id)
        has_evidence = readiness.is_profile_ready or readiness.is_assessment_ready or readiness.is_coaching_ready
        if not has_evidence:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail=f"Candidate evidence required: {feature_name} requires verified resume claims or assessment evidence. Candidate currently has no grounded evidence.",
            )

    async def assert_has_assessment(
        self,
        candidate_id: str,
        feature_name: str = "This coaching feature",
    ) -> None:
        """
        Enforces that the candidate has completed at least one evaluated interview before accessing assessment-grounded features.
        Raises HTTP 428 Precondition Required if prerequisite is unmet.
        """
        readiness = await self.get_candidate_readiness(candidate_id)
        if not readiness.is_assessment_ready:
            raise HTTPException(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                detail={
                    "error": "ASSESSMENT_REQUIRED",
                    "readiness_state": readiness.readiness_state.value,
                    "message": f"{feature_name} requires completed interview assessment evidence. No evaluated interview sessions found.",
                    "required_action": "START_ASSESSMENT",
                    "route": "/interview",
                },
            )

