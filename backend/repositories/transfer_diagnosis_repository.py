"""
Transfer Failure Diagnosis Repository.
Manages storage, retrieval, and filtering of structured diagnostic audit records.
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.transfer_diagnosis import TransferDiagnosisModel
from backend.models.transfer_task import TransferAttemptModel
from backend.repositories.base import BaseRepository


class TransferDiagnosisRepository(BaseRepository[TransferDiagnosisModel]):
    """
    Repository managing failure diagnostic audit records.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(TransferDiagnosisModel, session)

    async def get_with_context(self, diagnosis_id: str) -> Optional[TransferDiagnosisModel]:
        """Retrieve diagnosis with its parent attempt and resulting intervention events."""
        stmt = (
            select(TransferDiagnosisModel)
            .where(TransferDiagnosisModel.id == diagnosis_id)
            .options(
                selectinload(TransferDiagnosisModel.attempt),
                selectinload(TransferDiagnosisModel.interventions),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def get_by_attempt(self, attempt_id: str) -> Optional[TransferDiagnosisModel]:
        """Retrieve diagnosis for a specific transfer attempt (1:1 relation)."""
        stmt = (
            select(TransferDiagnosisModel)
            .where(TransferDiagnosisModel.attempt_id == attempt_id)
            .options(selectinload(TransferDiagnosisModel.interventions))
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_candidate(
        self, candidate_id: str, skip: int = 0, limit: int = 100
    ) -> List[TransferDiagnosisModel]:
        """List all diagnoses associated with a candidate's transfer attempts."""
        stmt = (
            select(TransferDiagnosisModel)
            .join(TransferAttemptModel, TransferDiagnosisModel.attempt_id == TransferAttemptModel.id)
            .where(TransferAttemptModel.candidate_id == candidate_id)
            .options(selectinload(TransferDiagnosisModel.attempt))
            .order_by(TransferDiagnosisModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_failure_type(
        self, failure_type: str, skip: int = 0, limit: int = 100
    ) -> List[TransferDiagnosisModel]:
        """List diagnoses filtered by root-cause classification (e.g. SURFACE_PATTERN_DEPENDENCE)."""
        stmt = (
            select(TransferDiagnosisModel)
            .where(TransferDiagnosisModel.failure_type == failure_type)
            .order_by(TransferDiagnosisModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_affected_skill(
        self, affected_skill: str, skip: int = 0, limit: int = 100
    ) -> List[TransferDiagnosisModel]:
        """List diagnoses targeting a specific technical or conceptual skill."""
        stmt = (
            select(TransferDiagnosisModel)
            .where(TransferDiagnosisModel.affected_skill == affected_skill)
            .order_by(TransferDiagnosisModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
