"""
Repository for Candidate Claims and Evidence Graph persistence.
"""

from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from backend.models.resume_claim import CandidateClaimModel


class ClaimRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_candidate(self, candidate_id: str) -> List[CandidateClaimModel]:
        stmt = (
            select(CandidateClaimModel)
            .where(CandidateClaimModel.candidate_id == candidate_id)
            .order_by(CandidateClaimModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_by_id(self, claim_id: str) -> Optional[CandidateClaimModel]:
        stmt = select(CandidateClaimModel).where(CandidateClaimModel.id == claim_id)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create_batch(self, claims: List[CandidateClaimModel]) -> List[CandidateClaimModel]:
        for claim in claims:
            self.session.add(claim)
        await self.session.flush()
        return claims

    async def delete_by_resume(self, resume_id: str) -> None:
        stmt = delete(CandidateClaimModel).where(CandidateClaimModel.resume_id == resume_id)
        await self.session.execute(stmt)
        await self.session.flush()

    async def find_matching_claims(self, candidate_id: str, topic_or_skill: str) -> List[CandidateClaimModel]:
        term = f"%{topic_or_skill.lower()}%"
        stmt = (
            select(CandidateClaimModel)
            .where(CandidateClaimModel.candidate_id == candidate_id)
            .where(
                (CandidateClaimModel.skill_name.ilike(term)) |
                (CandidateClaimModel.claim_text.ilike(term))
            )
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
