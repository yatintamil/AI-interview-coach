"""
Transfer Task and Transfer Attempt Repositories.
Manages storage, retrieval, and relational queries for transfer tasks, task hierarchies,
and candidate attempt events.
"""

from typing import Optional, List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.transfer_task import TransferTaskModel, TransferAttemptModel
from backend.repositories.base import BaseRepository


class TransferTaskRepository(BaseRepository[TransferTaskModel]):
    """
    Repository for managing TransferTask definitions and hierarchical variants.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(TransferTaskModel, session)

    async def get_with_hierarchy(self, task_id: str) -> Optional[TransferTaskModel]:
        """Retrieve task along with its parent task and derived child variants."""
        stmt = (
            select(TransferTaskModel)
            .where(TransferTaskModel.id == task_id)
            .options(
                selectinload(TransferTaskModel.parent_task),
                selectinload(TransferTaskModel.derived_tasks),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_skill(
        self, skill_id: str, skip: int = 0, limit: int = 100
    ) -> List[TransferTaskModel]:
        """List tasks evaluating a specific skill concept."""
        stmt = (
            select(TransferTaskModel)
            .where(TransferTaskModel.skill_id == skill_id)
            .order_by(TransferTaskModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_transfer_level(
        self, transfer_level: str, skip: int = 0, limit: int = 100
    ) -> List[TransferTaskModel]:
        """List tasks configured at a specific transfer taxonomy level."""
        stmt = (
            select(TransferTaskModel)
            .where(TransferTaskModel.transfer_level == transfer_level)
            .order_by(TransferTaskModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_child_variants(self, parent_task_id: str) -> List[TransferTaskModel]:
        """Retrieve all derived transfer tasks generated from a base parent task."""
        stmt = (
            select(TransferTaskModel)
            .where(TransferTaskModel.parent_task_id == parent_task_id)
            .order_by(TransferTaskModel.created_at.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_eligible_tasks(
        self,
        skill_id: str,
        transfer_level: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[TransferTaskModel]:
        """Retrieve candidate tasks matching skill and optional transfer level criteria."""
        stmt = select(TransferTaskModel).where(TransferTaskModel.skill_id == skill_id)
        if transfer_level:
            stmt = stmt.where(TransferTaskModel.transfer_level == transfer_level)
        stmt = stmt.order_by(TransferTaskModel.created_at.desc()).offset(skip).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class TransferAttemptRepository(BaseRepository[TransferAttemptModel]):
    """
    Repository for recording and querying candidate transfer attempts.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(TransferAttemptModel, session)

    async def get_with_full_context(self, attempt_id: str) -> Optional[TransferAttemptModel]:
        """
        Retrieves the complete attempt record with answer, evaluation, diagnosis,
        and intervention event history loaded.
        """
        stmt = (
            select(TransferAttemptModel)
            .where(TransferAttemptModel.id == attempt_id)
            .options(
                selectinload(TransferAttemptModel.transfer_task),
                selectinload(TransferAttemptModel.answer),
                selectinload(TransferAttemptModel.evaluation),
                selectinload(TransferAttemptModel.diagnosis),
                selectinload(TransferAttemptModel.intervention_events),
                selectinload(TransferAttemptModel.session),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_candidate(
        self, candidate_id: str, skip: int = 0, limit: int = 100
    ) -> List[TransferAttemptModel]:
        """List all transfer attempts by candidate ordered chronologically."""
        stmt = (
            select(TransferAttemptModel)
            .where(TransferAttemptModel.candidate_id == candidate_id)
            .options(
                selectinload(TransferAttemptModel.transfer_task),
                selectinload(TransferAttemptModel.diagnosis),
            )
            .order_by(TransferAttemptModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_task(
        self, transfer_task_id: str, skip: int = 0, limit: int = 100
    ) -> List[TransferAttemptModel]:
        """List all attempts on a specific transfer task across candidates."""
        stmt = (
            select(TransferAttemptModel)
            .where(TransferAttemptModel.transfer_task_id == transfer_task_id)
            .order_by(TransferAttemptModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_session(self, session_id: str) -> List[TransferAttemptModel]:
        """List all transfer attempts conducted within an interview session."""
        stmt = (
            select(TransferAttemptModel)
            .where(TransferAttemptModel.session_id == session_id)
            .options(
                selectinload(TransferAttemptModel.transfer_task),
                selectinload(TransferAttemptModel.diagnosis),
                selectinload(TransferAttemptModel.intervention_events),
            )
            .order_by(TransferAttemptModel.attempt_number.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_transfer_level(
        self, candidate_id: str, transfer_level: str
    ) -> List[TransferAttemptModel]:
        """List attempts for a candidate filtered by the task's transfer distance level."""
        stmt = (
            select(TransferAttemptModel)
            .join(TransferTaskModel, TransferAttemptModel.transfer_task_id == TransferTaskModel.id)
            .where(
                TransferAttemptModel.candidate_id == candidate_id,
                TransferTaskModel.transfer_level == transfer_level,
            )
            .options(selectinload(TransferAttemptModel.transfer_task))
            .order_by(TransferAttemptModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_outcome(
        self, candidate_id: str, transfer_success: bool
    ) -> List[TransferAttemptModel]:
        """List attempts for a candidate filtered by success or failure outcome."""
        stmt = (
            select(TransferAttemptModel)
            .where(
                TransferAttemptModel.candidate_id == candidate_id,
                TransferAttemptModel.transfer_success == transfer_success,
            )
            .options(
                selectinload(TransferAttemptModel.transfer_task),
                selectinload(TransferAttemptModel.diagnosis),
            )
            .order_by(TransferAttemptModel.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())
