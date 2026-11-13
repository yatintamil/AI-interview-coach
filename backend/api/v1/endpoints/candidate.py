"""
FastAPI Router for Candidate and Resume Management.
Adheres to RESTful design with proper status codes and Pydantic response models.
"""

import uuid
from typing import List, Optional
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, File, UploadFile, HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db_session
from backend.core.security import (
    get_authenticated_candidate_id,
    require_authenticated_candidate_id,
    verify_candidate_access,
)
from backend.services.candidate_service import CandidateService
from backend.services.resume_service import ResumeService
from backend.schemas.candidate import (
    CandidateCreateRequest,
    CandidateUpdateRequest,
    CandidateResponse,
    CandidateListResponse,
    ResumeSummaryResponse,
)
from backend.schemas.resume import ResumeParseResponse
from backend.schemas.readiness import CandidateReadinessResponse
from backend.services.readiness_service import CandidateReadinessService
from backend.core.exceptions import ResumeParsingError

router = APIRouter(tags=["Candidate & Resume Management"])


@router.post(
    "/candidates",
    response_model=CandidateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new candidate profile",
)
async def create_candidate(
    payload: CandidateCreateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    service = CandidateService(session)
    return await service.create_candidate(payload)


@router.get(
    "/candidates",
    response_model=CandidateListResponse,
    summary="List all candidates",
)
async def list_candidates(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_db_session),
):
    service = CandidateService(session)
    return await service.list_candidates(skip=skip, limit=limit)


@router.get(
    "/candidates/{candidate_id}",
    response_model=CandidateResponse,
    summary="Get candidate profile by ID",
)
async def get_candidate(
    candidate_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    service = CandidateService(session)
    return await service.get_candidate(candidate_id)


@router.put(
    "/candidates/{candidate_id}",
    response_model=CandidateResponse,
    summary="Update candidate profile",
)
@router.patch(
    "/candidates/{candidate_id}",
    response_model=CandidateResponse,
    summary="Update candidate profile (partial)",
)
async def update_candidate(
    candidate_id: str,
    payload: CandidateUpdateRequest,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    service = CandidateService(session)
    return await service.update_candidate(candidate_id, payload)


@router.delete(
    "/candidates/{candidate_id}",
    summary="Delete candidate and all associated data",
)
async def delete_candidate(
    candidate_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    service = CandidateService(session)
    return await service.delete_candidate(candidate_id)


@router.post(
    "/candidates/{candidate_id}/resumes",
    response_model=ResumeParseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload and associate a resume with candidate",
)
async def upload_candidate_resume(
    candidate_id: str,
    file: UploadFile = File(..., description="PDF or DOCX resume document"),
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    # Validate candidate exists
    cand_service = CandidateService(session)
    await cand_service.get_candidate(candidate_id)

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    resume_service = ResumeService(session)
    try:
        resume_record, profile, chunks_count = await resume_service.process_resume(
            candidate_id=uuid.UUID(candidate_id),
            file_name=file.filename or "resume.pdf",
            file_bytes=content
        )
    except ResumeParsingError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Resume processing error: {str(e)}")

    return ResumeParseResponse(
        candidate_id=uuid.UUID(candidate_id),
        resume_id=resume_record.id,
        status=resume_record.processing_status,
        profile=profile,
        indexed_rag_chunks=chunks_count,
        created_at=resume_record.created_at
    )


@router.get(
    "/candidates/{candidate_id}/resumes",
    response_model=List[ResumeSummaryResponse],
    summary="List all resumes for candidate",
)
async def list_candidate_resumes(
    candidate_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    service = CandidateService(session)
    return await service.list_candidate_resumes(candidate_id)


@router.put(
    "/candidates/{candidate_id}/resumes/{resume_id}/activate",
    response_model=ResumeSummaryResponse,
    summary="Set specific resume as active for candidate",
)
async def activate_candidate_resume(
    candidate_id: str,
    resume_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    service = CandidateService(session)
    return await service.activate_resume(candidate_id, resume_id)


@router.delete(
    "/resumes/{resume_id}",
    summary="Delete resume by ID",
)
async def delete_resume(
    resume_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    service = CandidateService(session)
    return await service.delete_resume(resume_id)


@router.get(
    "/candidates/{candidate_id}/claims",
    response_model=List[dict],
    summary="Get all atomic claims decomposed for candidate",
)
async def get_candidate_claims(
    candidate_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    from backend.repositories.claim_repository import ClaimRepository
    claim_repo = ClaimRepository(session)
    claims = await claim_repo.get_by_candidate(candidate_id)
    return [
        {
            "id": c.id,
            "candidate_id": c.candidate_id,
            "resume_id": c.resume_id,
            "skill_name": c.skill_name,
            "claim_text": c.claim_text,
            "complexity": c.complexity,
            "verification_status": c.verification_status,
            "confidence_score": c.confidence_score,
            "verified_quotes": c.verified_quotes or [],
            "probe_count": c.probe_count,
            "created_at": c.created_at,
        }
        for c in claims
    ]


@router.get(
    "/candidates/{candidate_id}/evidence-graph",
    response_model=dict,
    summary="Get Candidate Evidence Graph summary",
)
async def get_candidate_evidence_graph(
    candidate_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    from backend.repositories.claim_repository import ClaimRepository
    claim_repo = ClaimRepository(session)
    claims = await claim_repo.get_by_candidate(candidate_id)

    total_claims = len(claims)
    verified_count = sum(1 for c in claims if c.verification_status == "VERIFIED")
    probed_count = sum(1 for c in claims if c.verification_status == "PROBED")
    verification_ratio = round((verified_count / total_claims) * 100, 1) if total_claims > 0 else 0.0

    return {
        "candidate_id": candidate_id,
        "total_claims": total_claims,
        "verified_count": verified_count,
        "probed_count": probed_count,
        "overall_verification_ratio": verification_ratio,
        "claims": [
            {
                "id": c.id,
                "candidate_id": c.candidate_id,
                "resume_id": c.resume_id,
                "skill_name": c.skill_name,
                "claim_text": c.claim_text,
                "complexity": c.complexity,
                "verification_status": c.verification_status,
                "confidence_score": c.confidence_score,
                "verified_quotes": c.verified_quotes or [],
                "probe_count": c.probe_count,
                "created_at": c.created_at,
            }
            for c in claims
        ],
    }


@router.get(
    "/candidates/{candidate_id}/readiness",
    response_model=CandidateReadinessResponse,
    summary="Get candidate readiness state and feature gating",
)
async def get_candidate_readiness(
    candidate_id: str,
    target_role: Optional[str] = None,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    service = CandidateReadinessService(session)
    return await service.get_candidate_readiness(candidate_id, target_role_hint=target_role)


@router.get(
    "/candidates/{candidate_id}/dossier",
    response_model=dict,
    summary="Get or dynamically synthesize personalized AI coach dossier for candidate",
)
async def get_candidate_dossier(
    candidate_id: str,
    force_refresh: bool = False,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    from backend.repositories.candidate_repository import CandidateRepository
    from ai.interview_engine.personalized_skill_synthesizer import PersonalizedSkillSynthesizer

    repo = CandidateRepository(session)
    cand = await repo.get_by_id(candidate_id)
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

    prof = await repo.get_profile(candidate_id)
    if not prof or not prof.profile_data:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail="Resume evidence required: Candidate has not uploaded or processed a resume yet. Upload an engineering resume to generate a personalized dossier.",
        )


    profile_dict = dict(prof.profile_data)
    if not force_refresh and "personalized_dossier" in profile_dict and profile_dict["personalized_dossier"]:
        return profile_dict["personalized_dossier"]

    target_role = "Software Engineer"
    if "recommended_roles" in profile_dict and profile_dict["recommended_roles"]:
        target_role = profile_dict["recommended_roles"][0]
    elif prof.domains_flat:
        target_role = f"{prof.domains_flat[0]} Specialist"

    skills = prof.skills_flat or [s.get("name") for s in profile_dict.get("skills", [])]
    projects = profile_dict.get("projects", [])

    dossier = await PersonalizedSkillSynthesizer.synthesize_candidate_dossier(
        candidate_id=cand.id,
        candidate_name=cand.full_name,
        target_role=target_role,
        extracted_skills=skills,
        projects=projects,
    )

    profile_dict["personalized_dossier"] = dossier
    prof.profile_data = profile_dict
    await session.flush()
    return dossier


@router.get(
    "/candidates/{candidate_id}/skill-states",
    summary="List longitudinal skill states and transfer mastery for candidate",
)
async def get_candidate_skill_states(
    candidate_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    from backend.repositories.skill_state_repository import CandidateSkillStateRepository
    from backend.domain.transfer.schemas import CandidateSkillStateDTO
    from backend.domain.transfer.taxonomy import TransferLevel
    from backend.domain.transfer.diagnosis_types import TransferFailureType

    repo = CandidateSkillStateRepository(session)
    states = await repo.list_by_candidate(candidate_id)

    result = []
    for s in states:
        try:
            tl = TransferLevel(s.highest_transfer_level)
        except Exception:
            tl = TransferLevel.L0_RECALL

        recurring_enums = []
        for f in (s.recurring_failure_types or []):
            try:
                recurring_enums.append(TransferFailureType(f))
            except Exception:
                pass

        result.append(
            CandidateSkillStateDTO(
                candidate_id=s.candidate_id,
                skill_name=s.skill_name,
                mastery_estimate=s.mastery_estimate,
                mastery_uncertainty=s.mastery_uncertainty,
                highest_transfer_level=tl,
                assistance_dependency_index=s.assistance_dependency_index,
                recurring_failure_types=recurring_enums,
                total_attempts=s.total_attempts,
                last_assessed_at=s.last_assessed_at,
            )
        )
    return result


