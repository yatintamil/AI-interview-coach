"""
Candidate Management Application Service.
Handles candidate lifecycle, validation, and resume associations.
"""

import uuid
from typing import List, Optional
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status

from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.resume_repository import ResumeRepository
from backend.models.candidate import CandidateModel
from backend.schemas.candidate import (
    CandidateCreateRequest,
    CandidateUpdateRequest,
    CandidateResponse,
    CandidateListResponse,
    ResumeSummaryResponse,
)


class CandidateService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.candidate_repo = CandidateRepository(session)
        self.resume_repo = ResumeRepository(session)

    def _to_response(self, candidate: CandidateModel) -> CandidateResponse:
        resumes_summary = []
        if candidate.resumes:
            for r in candidate.resumes:
                resumes_summary.append(
                    ResumeSummaryResponse(
                        id=r.id,
                        file_name=r.file_name,
                        file_type=r.file_type,
                        file_size_bytes=r.file_size_bytes,
                        processing_status=r.processing_status,
                        is_active=getattr(r, "is_active", True),
                        created_at=r.created_at,
                    )
                )

        has_profile = bool(candidate.profile and candidate.profile.profile_data)
        skills = candidate.profile.skills_flat if candidate.profile else []
        total_exp = candidate.profile.total_years_exp if candidate.profile else 0.0

        readiness_state = "NO_RESUME"
        if resumes_summary:
            completed_resumes = [r for r in resumes_summary if r.processing_status == "COMPLETED" and r.is_active]
            if completed_resumes and has_profile:
                readiness_state = "PROFILE_READY"
            else:
                readiness_state = "RESUME_PROCESSING"

        return CandidateResponse(
            id=candidate.id,
            email=candidate.email,
            full_name=candidate.full_name,
            created_at=candidate.created_at,
            resumes=resumes_summary,
            has_profile=has_profile,
            skills_summary=skills,
            total_years_exp=total_exp,
            readiness_state=readiness_state,
            target_role=getattr(candidate, "target_role", None),
        )

    async def create_candidate(self, payload: CandidateCreateRequest) -> CandidateResponse:
        existing = await self.candidate_repo.get_by_email(payload.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Candidate with email '{payload.email}' already exists."
            )

        password_hash = None
        if payload.password:
            from backend.core.security import hash_password
            password_hash = hash_password(payload.password)

        candidate = CandidateModel(
            id=str(uuid.uuid4()),
            email=payload.email,
            full_name=payload.full_name,
            password_hash=password_hash,
        )
        created = await self.candidate_repo.create(candidate)
        # Fetch with details
        loaded = await self.candidate_repo.get_with_details(created.id)
        return self._to_response(loaded or created)

    async def get_candidate(self, candidate_id: str) -> CandidateResponse:
        candidate = await self.candidate_repo.get_with_details(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found."
            )
        return self._to_response(candidate)

    async def list_candidates(self, skip: int = 0, limit: int = 100) -> CandidateListResponse:
        candidates = await self.candidate_repo.list_all_candidates(skip=skip, limit=limit)
        items = [self._to_response(c) for c in candidates]
        return CandidateListResponse(candidates=items, total=len(items))

    async def update_candidate(self, candidate_id: str, payload: CandidateUpdateRequest) -> CandidateResponse:
        candidate = await self.candidate_repo.get_with_details(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found."
            )

        if payload.email and payload.email != candidate.email:
            existing = await self.candidate_repo.get_by_email(payload.email)
            if existing and existing.id != candidate_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Email '{payload.email}' is already in use."
                )
            candidate.email = payload.email

        if payload.full_name:
            candidate.full_name = payload.full_name

        if payload.target_role is not None:
            candidate.target_role = payload.target_role.strip() if payload.target_role.strip() else None

        await self.session.flush()
        await self.session.commit()
        return self._to_response(candidate)

    async def delete_candidate(self, candidate_id: str) -> dict:
        candidate = await self.candidate_repo.get(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found."
            )

        # 1. Delete associated claims
        try:
            from backend.models.resume_claim import CandidateClaimModel
            # pyrefly: ignore [missing-import]
            from sqlalchemy import delete
            await self.session.execute(
                delete(CandidateClaimModel).where(CandidateClaimModel.candidate_id == candidate_id)
            )
        except Exception:
            pass

        # 2. Delete associated interview sessions
        try:
            from backend.models.interview import InterviewSessionModel
            # pyrefly: ignore [missing-import]
            from sqlalchemy.future import select
            sessions_res = await self.session.execute(
                select(InterviewSessionModel).where(InterviewSessionModel.candidate_id == candidate_id)
            )
            for s in sessions_res.scalars().all():
                await self.session.delete(s)
        except Exception:
            pass

        await self.candidate_repo.delete(candidate_id)
        return {"status": "deleted", "id": candidate_id}

    async def list_candidate_resumes(self, candidate_id: str) -> List[ResumeSummaryResponse]:
        await self.get_candidate(candidate_id) # ensure exists
        resumes = await self.resume_repo.list_by_candidate(candidate_id)
        return [
            ResumeSummaryResponse(
                id=r.id,
                file_name=r.file_name,
                file_type=r.file_type,
                file_size_bytes=r.file_size_bytes,
                processing_status=r.processing_status,
                is_active=getattr(r, "is_active", True),
                created_at=r.created_at,
            )
            for r in resumes
        ]

    async def activate_resume(self, candidate_id: str, resume_id: str) -> ResumeSummaryResponse:
        await self.get_candidate(candidate_id)
        resume = await self.resume_repo.get(resume_id)
        if not resume or resume.candidate_id != candidate_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume with ID '{resume_id}' not found for candidate '{candidate_id}'."
            )
        updated = await self.resume_repo.set_active_resume(candidate_id, resume_id)
        return ResumeSummaryResponse(
            id=updated.id,
            file_name=updated.file_name,
            file_type=updated.file_type,
            file_size_bytes=updated.file_size_bytes,
            processing_status=updated.processing_status,
            is_active=updated.is_active,
            created_at=updated.created_at,
        )

    async def delete_resume(self, resume_id: str) -> dict:
        resume = await self.resume_repo.get(resume_id)
        if not resume:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Resume with ID '{resume_id}' not found."
            )
        candidate_id = resume.candidate_id

        # 1. Delete associated RAG vector chunks
        try:
            from backend.models.embedding import ResumeChunkModel
            from sqlalchemy import delete
            await self.session.execute(
                delete(ResumeChunkModel).where(ResumeChunkModel.resume_id == resume_id)
            )
        except Exception:
            pass

        # 2. Delete associated atomic claims
        try:
            from backend.models.resume_claim import CandidateClaimModel
            from sqlalchemy import delete
            await self.session.execute(
                delete(CandidateClaimModel).where(CandidateClaimModel.resume_id == resume_id)
            )
        except Exception:
            pass

        # 3. Check remaining candidate resumes
        remaining_resumes = await self.resume_repo.list_by_candidate(candidate_id)
        other_resumes = [r for r in remaining_resumes if r.id != resume_id]

        if not other_resumes:
            # Invalidate dependent candidate profile
            try:
                from backend.models.candidate import CandidateProfileModel
                from sqlalchemy import delete
                await self.session.execute(
                    delete(CandidateProfileModel).where(CandidateProfileModel.candidate_id == candidate_id)
                )
            except Exception:
                pass

            # Invalidate dependent personalized roadmaps
            try:
                from backend.models.roadmap import PersonalizedRoadmapModel, RoadmapItemModel
                from sqlalchemy import delete, select
                roadmaps_res = await self.session.execute(
                    select(PersonalizedRoadmapModel).where(PersonalizedRoadmapModel.candidate_id == candidate_id)
                )
                for rm in roadmaps_res.scalars().all():
                    await self.session.execute(
                        delete(RoadmapItemModel).where(RoadmapItemModel.roadmap_id == rm.id)
                    )
                    await self.session.delete(rm)
            except Exception:
                pass
        else:
            # If the deleted resume was the active one, activate another completed resume if available
            if getattr(resume, "is_active", False) and other_resumes:
                other_resumes[0].is_active = True

        # 4. Delete resume record
        await self.resume_repo.delete(resume_id)
        await self.session.commit()
        return {"status": "deleted", "id": resume_id}

