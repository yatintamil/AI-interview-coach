"""
Coaching Intervention Event Repository.
Manages storage, retrieval, and research telemetry queries for coaching interventions
and scaffold fading events.
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.coaching_event import CoachingInterventionEventModel
from backend.models.transfer_task import TransferAttemptModel
from backend.repositories.base import BaseRepository


class CoachingInterventionRepository(BaseRepository[CoachingInterventionEventModel]):
    """
    Repository for persisting and querying coaching intervention telemetry events.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(CoachingInterventionEventModel, session)

    async def get_with_context(self, event_id: str) -> Optional[CoachingInterventionEventModel]:
        """Retrieve intervention event with its linked attempt, diagnosis, and session."""
        stmt = (
            select(CoachingInterventionEventModel)
            .where(CoachingInterventionEventModel.id == event_id)
            .options(
                selectinload(CoachingInterventionEventModel.attempt),
                selectinload(CoachingInterventionEventModel.diagnosis),
                selectinload(CoachingInterventionEventModel.session),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_attempt(self, attempt_id: str) -> List[CoachingInterventionEventModel]:
        """List all intervention events administered during a transfer attempt."""
        stmt = (
            select(CoachingInterventionEventModel)
            .where(CoachingInterventionEventModel.attempt_id == attempt_id)
            .order_by(CoachingInterventionEventModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_diagnosis(self, diagnosis_id: str) -> List[CoachingInterventionEventModel]:
        """List interventions triggered by a specific diagnostic decision."""
        stmt = (
            select(CoachingInterventionEventModel)
            .where(CoachingInterventionEventModel.diagnosis_id == diagnosis_id)
            .order_by(CoachingInterventionEventModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_session(
        self, session_id: str, skip: int = 0, limit: int = 100
    ) -> List[CoachingInterventionEventModel]:
        """List all intervention events across an interview session."""
        stmt = (
            select(CoachingInterventionEventModel)
            .where(CoachingInterventionEventModel.session_id == session_id)
            .order_by(CoachingInterventionEventModel.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_candidate(
        self, candidate_id: str, skip: int = 0, limit: int = 100
    ) -> List[CoachingInterventionEventModel]:
        """List all coaching interventions received by a candidate across all attempts."""
        stmt = (
            select(CoachingInterventionEventModel)
            .join(
                TransferAttemptModel,
                CoachingInterventionEventModel.attempt_id == TransferAttemptModel.id,
            )
            .where(TransferAttemptModel.candidate_id == candidate_id)
            .order_by(CoachingInterventionEventModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_intervention_type(
        self, intervention_type: str, skip: int = 0, limit: int = 100
    ) -> List[CoachingInterventionEventModel]:
        """List events filtered by intervention taxonomy action (e.g. COUNTEREXAMPLE)."""
        stmt = (
            select(CoachingInterventionEventModel)
            .where(CoachingInterventionEventModel.intervention_type == intervention_type)
            .order_by(CoachingInterventionEventModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_scaffold_level(
        self, scaffold_level: str, skip: int = 0, limit: int = 100
    ) -> List[CoachingInterventionEventModel]:
        """List events filtered by scaffold intensity tier (e.g. MEDIUM_ASSISTANCE)."""
        stmt = (
            select(CoachingInterventionEventModel)
            .where(CoachingInterventionEventModel.scaffold_level == scaffold_level)
            .order_by(CoachingInterventionEventModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_faded_events(
        self, candidate_id: Optional[str] = None, skip: int = 0, limit: int = 100
    ) -> List[CoachingInterventionEventModel]:
        """
        List intervention events where scaffolding was explicitly faded (is_faded=True),
        supporting empirical testing of Scaffold Fading (H3).
        """
        stmt = select(CoachingInterventionEventModel).where(
            CoachingInterventionEventModel.is_faded == True
        )
        if candidate_id:
            stmt = stmt.join(
                TransferAttemptModel,
                CoachingInterventionEventModel.attempt_id == TransferAttemptModel.id,
            ).where(TransferAttemptModel.candidate_id == candidate_id)

        stmt = stmt.order_by(CoachingInterventionEventModel.created_at.desc()).offset(skip).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
