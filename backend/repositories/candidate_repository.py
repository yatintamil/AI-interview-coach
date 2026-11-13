"""
Candidate & CandidateProfile Repository.
"""

from typing import Optional, List, Union
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from backend.models.candidate import CandidateModel, CandidateProfileModel
from backend.repositories.base import BaseRepository
from backend.schemas.candidate_profile import CandidateProfile


class CandidateRepository(BaseRepository[CandidateModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(CandidateModel, session)

    async def get_by_email(self, email: str) -> Optional[CandidateModel]:
        stmt = select(CandidateModel).where(CandidateModel.email == email).options(selectinload(CandidateModel.resumes), selectinload(CandidateModel.profile))
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_with_details(self, candidate_id: str) -> Optional[CandidateModel]:
        stmt = select(CandidateModel).where(CandidateModel.id == str(candidate_id)).options(
            selectinload(CandidateModel.resumes),
            selectinload(CandidateModel.profile)
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_all_candidates(self, skip: int = 0, limit: int = 100) -> List[CandidateModel]:
        stmt = select(CandidateModel).options(
            selectinload(CandidateModel.resumes),
            selectinload(CandidateModel.profile)
        ).offset(skip).limit(limit).order_by(CandidateModel.created_at.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_profile(self, candidate_id: Union[UUID, str]) -> Optional[CandidateProfileModel]:
        stmt = select(CandidateProfileModel).where(CandidateProfileModel.candidate_id == str(candidate_id))
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def save_profile(self, candidate_id: Union[UUID, str], resume_id: str, profile: CandidateProfile) -> CandidateProfileModel:
        # Also sync CandidateModel identity with extracted profile
        cand = await self.get(str(candidate_id))
        if cand:
            if profile.full_name and profile.full_name.strip() and profile.full_name.strip().lower() not in ["candidate", "unknown candidate", "extracted candidate", "candidate (auto-created)"]:
                cand.full_name = profile.full_name.strip()
            if profile.email and "@" in profile.email:
                clean_email = profile.email.strip().lower()
                existing_email_cand = await self.get_by_email(clean_email)
                if not existing_email_cand or str(existing_email_cand.id) == str(cand.id):
                    cand.email = clean_email

        existing = await self.get_profile(candidate_id)
        profile_dict = profile.model_dump()
        
        skills_flat = [s["name"] for s in profile_dict.get("skills", [])]
        domains_flat = profile_dict.get("domains", [])
        total_exp = profile_dict.get("total_years_experience", 0.0)

        if existing:
            existing.resume_id = str(resume_id)
            existing.profile_data = profile_dict
            existing.skills_flat = skills_flat
            existing.domains_flat = domains_flat
            existing.total_years_exp = total_exp
            await self.session.flush()
            return existing
        else:
            new_profile = CandidateProfileModel(
                candidate_id=str(candidate_id),
                resume_id=str(resume_id),
                profile_data=profile_dict,
                skills_flat=skills_flat,
                domains_flat=domains_flat,
                total_years_exp=total_exp,
            )
            self.session.add(new_profile)
            await self.session.flush()
            return new_profile
