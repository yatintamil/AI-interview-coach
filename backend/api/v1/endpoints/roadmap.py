"""
Personalized Roadmap and Skill Gap Analysis REST API Endpoints.
Provides deterministic, role-anchored gap analysis and personalized milestone tracking.
"""

from typing import Optional, List, Dict, Any
import logging
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status, Query, Body

logger = logging.getLogger(__name__)
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

from backend.dependencies.database import get_db_session
from backend.core.security import get_authenticated_candidate_id, verify_candidate_access
from backend.services.roadmap_service import RoadmapService
from backend.domain.roadmap.models import (
    SkillGapAnalysisResult,
    PersonalizedRoadmapDTO,
    GenerateRoadmapRequest,
    StartCoachingFromRoadmapResponse,
)

router = APIRouter(prefix="/roadmap", tags=["Personalized Roadmap & Skill Gaps"])


@router.get(
    "/roles",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Curated Target Engineering Roles & Competencies",
)
async def list_curated_roles():
    """
    Returns curated target engineering roles with descriptions, competencies,
    knowledge areas, and foundational invariants from the Role Intelligence registry.
    """
    from ai.interview_engine.role_intelligence import CURATED_ROLE_PROFILES
    roles = []
    for role_key, data in CURATED_ROLE_PROFILES.items():
        roles.append({
            "key": role_key,
            "display_name": data.get("display_name", role_key),
            "aliases": data.get("aliases", []),
            "description": data.get("description", ""),
            "responsibilities": data.get("responsibilities", []),
            "knowledge_areas": data.get("knowledge_areas", []),
            "is_generic_template": True,
            "candidate_evidence_attached": False,
            "competencies": [
                {
                    "identifier": c.get("identifier"),
                    "name": c.get("name"),
                    "description": c.get("description"),
                    "importance": str(c.get("importance", "CORE")),
                    "core_invariants": c.get("core_invariants", []),
                    "expected_concepts": c.get("expected_concepts", []),
                }
                for c in data.get("competencies", [])
            ],
        })
    return roles


@router.post(
    "/roles/research",
    status_code=status.HTTP_200_OK,
    summary="Trigger or Retrieve Web-Research-Driven Role Intelligence (Roadmap Alias)",
)
async def roadmap_research_role(
    spec: Dict[str, Any] = Body(...),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    from backend.domain.role.models import RoleResearchSpecification
    from backend.api.v1.endpoints.roles import research_role as roles_research_role
    typed_spec = RoleResearchSpecification.model_validate(spec)
    return await roles_research_role(typed_spec, authenticated_candidate_id)


@router.get(
    "/roles/research/{role_name}",
    status_code=status.HTTP_200_OK,
    summary="Get Researched Role Intelligence Profile by Role Name (Roadmap Alias)",
)
async def roadmap_get_role_research(
    role_name: str,
    experience_level: Optional[str] = Query("Mid"),
    force_refresh: bool = Query(False),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    from backend.api.v1.endpoints.roles import get_role_research as roles_get_role_research
    return await roles_get_role_research(role_name, experience_level, force_refresh, authenticated_candidate_id)


@router.post(
    "/roles/match",
    status_code=status.HTTP_200_OK,
    summary="Evaluate Candidate Match Against Researched Role Requirements (Roadmap Alias)",
)
async def roadmap_evaluate_candidate_role_match(
    payload: Dict[str, Any] = Body(...),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    from backend.api.v1.endpoints.roles import evaluate_candidate_role_match as roles_evaluate_match, RoleMatchRequest
    typed_payload = RoleMatchRequest.model_validate(payload)
    return await roles_evaluate_match(typed_payload, authenticated_candidate_id, db)


@router.get(
    "/roles/recommendations",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Evidence-Grounded Role Recommendations for Candidate",
)
async def get_candidate_role_recommendations(
    candidate_id: str = Query(..., description="Target candidate identifier"),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Computes evidence-grounded role recommendations for a candidate based on verified
    skills, domain experience, and projects extracted from their processed resume.
    If no resume has been processed, returns an explicit not-ready structure.
    """
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    from backend.repositories.candidate_repository import CandidateRepository
    from ai.interview_engine.role_intelligence import CURATED_ROLE_PROFILES

    repo = CandidateRepository(db)
    cand = await repo.get(candidate_id)
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

    prof = await repo.get_profile(candidate_id)
    if not prof or not prof.profile_data:
        return {
            "candidate_id": candidate_id,
            "has_resume_evidence": False,
            "readiness_state": "NO_RESUME",
            "message": "Resume evidence required for personalized recommendations. Upload your resume to benchmark your verified experience.",
            "recommendations": [],
        }

    profile_dict = dict(prof.profile_data)
    skills = [s.lower() for s in (prof.skills_flat or [sk.get("name", "") for sk in profile_dict.get("skills", [])]) if s]
    domains = [d.lower() for d in (prof.domains_flat or profile_dict.get("domains", [])) if d]
    total_exp = float(prof.total_years_exp or 0.0)
    ai_recommended = [r.lower() for r in profile_dict.get("recommended_roles", []) if r]

    recommendations = []
    for role_key, data in CURATED_ROLE_PROFILES.items():
        role_display = data.get("display_name", role_key)
        role_desc = data.get("description", "")
        role_knowledge = [k.lower() for k in data.get("knowledge_areas", []) if k]
        role_comps = data.get("competencies", [])

        # Collect expected concepts
        expected_concepts = []
        for c in role_comps:
            for ec in c.get("expected_concepts", []):
                expected_concepts.append(ec)

        # Match skills against concepts or knowledge areas
        verified_matched = []
        for sk in skills:
            if any(sk in ec.lower() or ec.lower() in sk for ec in expected_concepts) or \
               any(sk in ka or ka in sk for ka in role_knowledge) or \
               sk in role_desc.lower() or sk in role_display.lower():
                verified_matched.append(sk.title())

        # Deduplicate verified_matched
        verified_matched = list(dict.fromkeys(verified_matched))

        # Check domain alignment
        domain_matched = any(
            d in role_display.lower() or d in role_desc.lower() or any(d in ka for ka in role_knowledge)
            for d in domains
        )

        # AI extracted direct recommendation flag
        is_direct_ai_rec = any(role_display.lower() in ar or ar in role_display.lower() for ar in ai_recommended)

        # Calculate empirical match score
        total_evaluable = max(len(expected_concepts), 5)
        raw_score = (len(verified_matched) / total_evaluable) * 0.65
        if domain_matched:
            raw_score += 0.20
        if is_direct_ai_rec:
            raw_score += 0.15
        if total_exp >= 3.0:
            raw_score += 0.05

        match_score = min(round(raw_score, 2), 0.98)

        # Distinguish verified skills from unverified concepts
        unverified = [
            ec for ec in expected_concepts[:5]
            if not any(sk in ec.lower() for sk in skills)
        ]

        if match_score >= 0.20 or is_direct_ai_rec:
            recommendations.append({
                "role_key": role_key,
                "display_name": role_display,
                "match_score": match_score,
                "match_percentage": int(match_score * 100),
                "is_recommended": True,
                "recommendation_rationale": (
                    f"Aligned with {total_exp:.1f} years experience and {len(verified_matched)} verified skill(s) including "
                    f"{', '.join(verified_matched[:3]) if verified_matched else 'core domain foundations'}."
                ),
                "supporting_evidence": [f"Verified skill: {s}" for s in verified_matched[:4]],
                "unverified_concepts": unverified[:3],
                "uncertainty_note": "Expected competencies not explicitly found in resume are treated as unverified rather than absent; candidate may possess them from unlisted experience.",
            })

    # Sort descending by match score
    recommendations.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "candidate_id": candidate_id,
        "has_resume_evidence": True,
        "readiness_state": "PROFILE_READY",
        "total_recommendations": len(recommendations),
        "recommendations": recommendations,
    }


class StartCoachingFromItemRequest(BaseModel):
    candidate_id: str = Field(..., min_length=1)


@router.get(
    "/gaps",
    response_model=SkillGapAnalysisResult,
    status_code=status.HTTP_200_OK,
    summary="Compute Role-Aware Skill Gaps for Candidate",
)
async def calculate_skill_gaps(
    candidate_id: str = Query(..., description="Target candidate identifier"),
    target_role: Optional[str] = Query(default=None, description="Target engineering role (e.g. Distributed Systems Engineer)"),
    role_name: Optional[str] = Query(default=None, description="Alias for target_role"),
    seniority: Optional[str] = Query(default="Mid", description="Target seniority tier"),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Computes deterministic competency gaps by comparing candidate skill states
    against target role requirements, incorporating transfer deficits and failure patterns.
    """
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    role = target_role or role_name
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="target_role or role_name query parameter is required",
        )
    try:
        service = RoadmapService(session=db)
        return await service.calculate_gaps(
            candidate_id=candidate_id,
            target_role=role,
            seniority=seniority or "Mid",
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning("Invalid roadmap generation request: %s", ve)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to calculate skill gaps: {str(e)}",
        )


@router.post(
    "/generate",
    response_model=PersonalizedRoadmapDTO,
    status_code=status.HTTP_200_OK,
    summary="Generate or Refresh Personalized Learning Roadmap",
)
async def generate_personalized_roadmap(
    payload: GenerateRoadmapRequest,
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generates a sequenced, actionable personalized roadmap grounded in empirical skill gaps.
    Preserves ongoing milestone progress across regenerations.
    """
    verify_candidate_access(payload.candidate_id, authenticated_candidate_id)
    try:
        service = RoadmapService(session=db)
        target_role = payload.target_role or payload.role_name
        return await service.generate_or_update_roadmap(
            candidate_id=payload.candidate_id,
            target_role=target_role,
            seniority=payload.seniority or "Mid",
        )
    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning("Invalid roadmap generation request: %s", ve)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        logger.exception("Failed to generate personalized roadmap: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate personalized roadmap: {str(e)}",
        )


@router.get(
    "/candidate/{candidate_id}",
    response_model=PersonalizedRoadmapDTO,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Active Personalized Roadmap for Candidate",
)
async def get_candidate_roadmap(
    candidate_id: str,
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Fetches the candidate's active roadmap with all sequenced milestones and progress metrics.
    """
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    try:
        service = RoadmapService(session=db)
        roadmap = await service.get_roadmap_for_candidate(candidate_id)
        if not roadmap:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No active personalized roadmap found for candidate '{candidate_id}'.",
            )
        return roadmap
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve candidate roadmap: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while retrieving the roadmap: {str(e)}",
        )


@router.post(
    "/items/{item_id}/start-coaching",
    response_model=StartCoachingFromRoadmapResponse,
    status_code=status.HTTP_200_OK,
    summary="Launch AI Coaching Session Anchored on Roadmap Milestone",
)
async def start_coaching_for_item(
    item_id: str,
    payload: Optional[StartCoachingFromItemRequest] = None,
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Bridges a roadmap milestone into the Transfer Coaching Studio,
    initializing a CoachingOrchestrator session anchored on the item's invariants.
    """
    cand_id = payload.candidate_id if payload else None
    if cand_id:
        verify_candidate_access(cand_id, authenticated_candidate_id)
    try:
        service = RoadmapService(session=db)
        res = await service.start_coaching_for_item(
            item_id=item_id,
            candidate_id=cand_id,
        )
        return res
    except HTTPException:
        raise
    except ValueError as ve:
        logger.warning("Invalid roadmap generation request: %s", ve)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to launch coaching session for roadmap item: {str(e)}",
        )


@router.post(
    "/candidate/{candidate_id}/sync-progress",
    response_model=PersonalizedRoadmapDTO,
    status_code=status.HTTP_200_OK,
    summary="Synchronize Roadmap Progress with Empirical Skill State",
)
async def sync_roadmap_progress(
    candidate_id: str,
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Evaluates latest transfer attempts and updates milestone statuses to COMPLETED if L5 criteria are met.
    """
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    service = RoadmapService(session=db)
    roadmap = await service.sync_roadmap_progress(candidate_id)
    if not roadmap:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active roadmap found to sync for candidate '{candidate_id}'.",
        )
    return roadmap
