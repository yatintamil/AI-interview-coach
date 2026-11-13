"""
Role Intelligence & Web Research REST API Endpoints.
Provides endpoints for dynamic role research, evidence-grounded candidate matching,
and intelligent role competency discovery.
"""

import logging
from typing import Optional, List, Dict, Any
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

from backend.dependencies.database import get_db_session
from backend.core.security import get_authenticated_candidate_id, verify_candidate_access
from backend.domain.role.models import (
    RoleResearchSpecification,
    RoleProfile,
    CandidateRoleMatchAssessment,
    RoleSpecification,
)
from ai.interview_engine.role_intelligence import (
    RoleIntelligenceService,
    CURATED_ROLE_PROFILES,
    _ROLE_CACHE,
)
from ai.interview_engine.role_research_engine import RoleCandidateMatcher
from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.skill_state_repository import CandidateSkillStateRepository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/roles", tags=["Role Intelligence & Dynamic Research"])


class RoleMatchRequest(BaseModel):
    candidate_id: str = Field(..., description="Target candidate identifier")
    role_name: str = Field(..., description="Target role name to evaluate against")
    experience_level: Optional[str] = Field("Mid", description="Seniority or experience level")
    force_refresh: bool = Field(False, description="Whether to force live web re-research")


@router.get(
    "",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Available Target Engineering Roles (Curated and Researched)",
)
async def list_roles():
    """
    Returns available target engineering roles with descriptions, competencies,
    knowledge areas, and research indicators.
    """
    roles = []
    # 1. Curated profiles
    for role_key, data in CURATED_ROLE_PROFILES.items():
        # Check if dynamic research exists in cache for this role
        cached_spec = RoleResearchSpecification(role_name=data.get("display_name", role_key))
        cache_key = _ROLE_CACHE.compute_cache_key(cached_spec)
        cached_profile, is_stale = _ROLE_CACHE.get(cache_key, allow_stale=True)

        if cached_profile:
            roles.append({
                "key": role_key,
                "display_name": cached_profile.display_name,
                "aliases": cached_profile.aliases,
                "description": cached_profile.description,
                "responsibilities": cached_profile.daily_responsibilities or data.get("responsibilities", []),
                "knowledge_areas": cached_profile.problems_solved or data.get("knowledge_areas", []),
                "is_generic_template": False,
                "candidate_evidence_attached": False,
                "research_status": cached_profile.research_status.value,
                "research_freshness_timestamp": cached_profile.research_freshness_timestamp,
                "is_cached": True,
                "is_stale": is_stale,
                "source_count": len(cached_profile.source_evidence or []),
                "competencies": [
                    {
                        "identifier": c.identifier,
                        "name": c.name,
                        "description": c.description,
                        "importance": str(c.importance.value if hasattr(c.importance, "value") else c.importance),
                        "core_invariants": c.core_invariants,
                        "expected_concepts": c.expected_concepts,
                        "requirement_classification": c.requirement_classification.value,
                    }
                    for c in cached_profile.competencies
                ],
            })
        else:
            roles.append({
                "key": role_key,
                "display_name": data.get("display_name", role_key),
                "aliases": data.get("aliases", []),
                "description": data.get("description", ""),
                "responsibilities": data.get("responsibilities", []),
                "knowledge_areas": data.get("knowledge_areas", []),
                "is_generic_template": True,
                "candidate_evidence_attached": False,
                "research_status": "NOT_STARTED",
                "research_freshness_timestamp": None,
                "is_cached": False,
                "is_stale": False,
                "source_count": 0,
                "competencies": [
                    {
                        "identifier": c.get("identifier"),
                        "name": c.get("name"),
                        "description": c.get("description"),
                        "importance": str(c.get("importance", "CORE")),
                        "core_invariants": c.get("core_invariants", []),
                        "expected_concepts": c.get("expected_concepts", []),
                        "requirement_classification": "CORE_MANDATORY",
                    }
                    for c in data.get("competencies", [])
                ],
            })
    return roles


@router.post(
    "/research",
    response_model=RoleProfile,
    status_code=status.HTTP_200_OK,
    summary="Trigger or Retrieve Web-Research-Driven Role Intelligence",
)
async def research_role(
    spec: RoleResearchSpecification,
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Conducts live autonomous web research for a target engineering role across industry sources,
    official documentation, engineering career frameworks, and technical job specifications.
    Synthesizes real-world responsibilities, dynamic competencies (>5), and source provenance.
    """
    try:
        profile = await RoleIntelligenceService.research_role(spec, force_refresh=spec.force_refresh)
        return profile
    except Exception as e:
        logger.error(f"Error executing role research for '{spec.role_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to conduct role research: {str(e)}",
        )


@router.get(
    "/research/{role_name}",
    response_model=RoleProfile,
    status_code=status.HTTP_200_OK,
    summary="Get Researched Role Intelligence Profile by Role Name",
)
async def get_role_research(
    role_name: str,
    experience_level: Optional[str] = Query("Mid", description="Seniority tier"),
    force_refresh: bool = Query(False, description="Whether to force live web re-research"),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Retrieves researched role profile from cache or triggers research if not cached.
    """
    spec = RoleResearchSpecification(
        role_name=role_name,
        experience_level=experience_level or "Mid",
        force_refresh=force_refresh,
    )
    try:
        profile = await RoleIntelligenceService.research_role(spec, force_refresh=force_refresh)
        return profile
    except Exception as e:
        logger.error(f"Error fetching role research for '{role_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve role research: {str(e)}",
        )


@router.post(
    "/match",
    response_model=CandidateRoleMatchAssessment,
    status_code=status.HTTP_200_OK,
    summary="Evaluate Candidate Match Against Researched Role Requirements",
)
async def evaluate_candidate_role_match(
    payload: RoleMatchRequest,
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Evaluates candidate readiness against dynamic researched role requirements.
    Preserves non-required candidate skills, does not conflate unassessed skills with zero mastery,
    and isolates verified strengths from genuine deficits.
    """
    verify_candidate_access(payload.candidate_id, authenticated_candidate_id)

    cand_repo = CandidateRepository(db)
    skill_repo = CandidateSkillStateRepository(db)

    cand = await cand_repo.get(payload.candidate_id)
    if not cand:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Candidate with ID '{payload.candidate_id}' not found.",
        )

    # 1. Fetch Candidate Profile & Resumes
    extracted_skills: List[str] = []
    claimed_skills: List[str] = []
    projects: List[Dict[str, Any]] = []

    prof = await cand_repo.get_profile(payload.candidate_id)
    if prof and prof.profile_data:
        p_data = dict(prof.profile_data)
        extracted_skills = prof.skills_flat or [s.get("name", "") for s in p_data.get("skills", [])]
        claimed_skills = p_data.get("claimed_skills", [])
        projects = p_data.get("projects", [])

    # 2. Fetch Interview Longitudinal Skill States
    tracked_states = await skill_repo.list_by_candidate(payload.candidate_id)
    interview_states: Dict[str, Any] = {}
    for s in tracked_states:
        interview_states[s.skill_name] = {
            "mastery": s.mastery_estimate,
            "transfer_level": s.highest_transfer_level,
            "attempts": s.total_attempts,
            "recurring_failures": s.recurring_failure_types,
            "assistance_dependency": s.assistance_dependency_index,
        }

    # 3. Resolve / Research Role Profile
    spec = RoleResearchSpecification(
        role_name=payload.role_name,
        experience_level=payload.experience_level or "Mid",
        force_refresh=payload.force_refresh,
    )
    role_profile = await RoleIntelligenceService.research_role(spec, force_refresh=payload.force_refresh)

    # 4. Run Matcher
    assessment = RoleCandidateMatcher.evaluate_match(
        candidate_id=payload.candidate_id,
        role_profile=role_profile,
        competencies=role_profile.competencies,
        extracted_skills=extracted_skills,
        claimed_skills=claimed_skills,
        projects=projects,
        interview_skill_states=interview_states,
    )

    return assessment

