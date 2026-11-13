"""
Async repository implementation for ExperimentSessionModel and ExperimentTrialModel.
Adheres to the repository pattern and supports eager loading of trials.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import or_

from backend.models.experiment import (
    ExperimentSessionModel,
    ExperimentTrialModel,
    ExperimentParticipantAssignmentModel,
    ExperimentConsentModel,
    ExperimentRetentionScheduleModel,
)
from backend.repositories.base import BaseRepository


class ExperimentRepository(BaseRepository[ExperimentSessionModel]):
    """
    Repository for managing experiment session state and related trial observations.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(ExperimentSessionModel, session)

    async def get_session_with_trials(self, session_id: str) -> Optional[ExperimentSessionModel]:
        """Fetch an experiment session with all its associated trials eagerly loaded."""
        stmt = (
            select(ExperimentSessionModel)
            .where(ExperimentSessionModel.id == session_id)
            .options(selectinload(ExperimentSessionModel.trials))
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_candidate(
        self, candidate_id: str, skip: int = 0, limit: int = 100
    ) -> List[ExperimentSessionModel]:
        """List all experiment sessions for a specific candidate."""
        stmt = (
            select(ExperimentSessionModel)
            .where(ExperimentSessionModel.candidate_id == candidate_id)
            .options(selectinload(ExperimentSessionModel.trials))
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_condition(
        self, condition: str, skip: int = 0, limit: int = 100
    ) -> List[ExperimentSessionModel]:
        """List experiment sessions filtered by experimental condition."""
        stmt = (
            select(ExperimentSessionModel)
            .where(ExperimentSessionModel.condition == condition)
            .options(selectinload(ExperimentSessionModel.trials))
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count_by_condition(self, condition: str) -> int:
        """Count total experiment sessions for a specific condition."""
        from sqlalchemy import func
        stmt = (
            select(func.count())
            .select_from(ExperimentSessionModel)
            .where(ExperimentSessionModel.condition == condition)
        )
        res = await self.session.execute(stmt)
        return int(res.scalar() or 0)

    async def list_all_with_trials(
        self, skip: int = 0, limit: int = 500
    ) -> List[ExperimentSessionModel]:
        """Fetch all experimental sessions with eager trial observations."""
        stmt = (
            select(ExperimentSessionModel)
            .options(selectinload(ExperimentSessionModel.trials))
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def record_trial(self, trial_model: ExperimentTrialModel) -> ExperimentTrialModel:
        """Persist a raw observation trial record."""
        self.session.add(trial_model)
        await self.session.flush()
        return trial_model

    async def get_trials_for_session(self, session_id: str) -> List[ExperimentTrialModel]:
        """Fetch all raw observation trials for a given session ordered by timestamp."""
        stmt = (
            select(ExperimentTrialModel)
            .where(ExperimentTrialModel.session_id == session_id)
            .order_by(ExperimentTrialModel.timestamp)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_participant_assignment(self, candidate_id: str) -> Optional[str]:
        """
        Fetch persistent assigned condition for a candidate if exists.
        Falls back to prior sessions if the dedicated assignment table has not yet recorded it.
        """
        stmt = select(ExperimentParticipantAssignmentModel.condition).where(
            ExperimentParticipantAssignmentModel.candidate_id == candidate_id
        )
        res = await self.session.execute(stmt)
        assigned = res.scalar_one_or_none()
        if assigned:
            return str(assigned)

        # Fallback to existing sessions
        prior = await self.list_by_candidate(candidate_id, limit=1)
        if prior:
            return str(prior[0].condition)
        return None

    async def record_participant_assignment(
        self, candidate_id: str, condition: str
    ) -> str:
        """
        Atomically records participant experimental assignment with uniqueness guarantee.
        If an assignment already exists or is concurrently inserted, returns the existing assignment.
        """
        existing = await self.get_participant_assignment(candidate_id)
        if existing:
            return existing

        try:
            assignment = ExperimentParticipantAssignmentModel(
                candidate_id=candidate_id,
                condition=condition,
            )
            self.session.add(assignment)
            await self.session.flush()
            return condition
        except Exception:
            await self.session.rollback()
            existing_after_rollback = await self.get_participant_assignment(candidate_id)
            if existing_after_rollback:
                return existing_after_rollback
            raise

    # =========================================================================
    # Participant Informed Consent Lifecycle
    # =========================================================================

    async def get_consent(self, candidate_id: str) -> Optional[ExperimentConsentModel]:
        """Retrieve persisted informed consent record for a candidate."""
        stmt = select(ExperimentConsentModel).where(
            ExperimentConsentModel.candidate_id == candidate_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def record_consent(
        self,
        candidate_id: str,
        consent_version: str = "v1.0-feasibility-study",
        status: str = "CONSENTED",
        study_title: str = "Transfer-Aware AI Interview Coaching Feasibility Study",
        study_metadata: Optional[Dict[str, Any]] = None,
    ) -> ExperimentConsentModel:
        """
        Records or updates explicit informed consent for experiment enrollment.
        """
        existing = await self.get_consent(candidate_id)
        now = datetime.now(timezone.utc)
        if existing:
            if existing.consent_status == "WITHDRAWN" and status == "CONSENTED":
                raise ValueError(
                    f"Participant '{candidate_id}' has formally withdrawn consent from the study. "
                    "Re-consenting after voluntary withdrawal is prohibited."
                )
            existing.consent_status = status
            existing.consent_version = consent_version
            existing.consented_at = now
            if status == "CONSENTED":
                existing.withdrawn_at = None
                existing.withdrawal_reason = None
            if study_metadata:
                existing.study_metadata_json = study_metadata
            await self.session.flush()
            return existing

        new_consent = ExperimentConsentModel(
            candidate_id=candidate_id,
            consent_status=status,
            consent_version=consent_version,
            consented_at=now,
            study_title=study_title,
            study_metadata_json=study_metadata,
        )
        self.session.add(new_consent)
        await self.session.flush()
        return new_consent

    async def withdraw_consent(
        self,
        candidate_id: str,
        reason: Optional[str] = None,
    ) -> Optional[ExperimentConsentModel]:
        """
        Records participant voluntary withdrawal. Sets consent status to WITHDRAWN.
        """
        consent = await self.get_consent(candidate_id)
        now = datetime.now(timezone.utc)
        if consent:
            consent.consent_status = "WITHDRAWN"
            consent.withdrawn_at = now
            consent.withdrawal_reason = reason
            await self.session.flush()
            return consent
        else:
            new_withdrawn = ExperimentConsentModel(
                candidate_id=candidate_id,
                consent_status="WITHDRAWN",
                consent_version="v1.0-feasibility-study",
                consented_at=now,
                withdrawn_at=now,
                withdrawal_reason=reason,
            )
            self.session.add(new_withdrawn)
            await self.session.flush()
            return new_withdrawn

    # =========================================================================
    # Longitudinal Delayed Retention Scheduling
    # =========================================================================

    async def schedule_retention(
        self,
        session_id: str,
        candidate_id: str,
        delay_days: int = 7,
    ) -> ExperimentRetentionScheduleModel:
        """
        Idempotently schedules a delayed retention follow-up (e.g. 7-day or 14-day).
        """
        stmt = select(ExperimentRetentionScheduleModel).where(
            ExperimentRetentionScheduleModel.session_id == session_id
        )
        res = await self.session.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            return existing

        now = datetime.now(timezone.utc)
        due = now + timedelta(days=delay_days)
        sched = ExperimentRetentionScheduleModel(
            session_id=session_id,
            candidate_id=candidate_id,
            delay_days=delay_days,
            due_date=due,
            status="PENDING",
            created_at=now,
        )
        self.session.add(sched)
        await self.session.flush()
        return sched

    async def get_retention_schedule(
        self, session_id: str
    ) -> Optional[ExperimentRetentionScheduleModel]:
        """Fetch retention schedule for a session."""
        stmt = select(ExperimentRetentionScheduleModel).where(
            ExperimentRetentionScheduleModel.session_id == session_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_due_retentions(self) -> List[ExperimentRetentionScheduleModel]:
        """
        List all retention assessments that are currently DUE or OVERDUE for supervised follow-up.
        Excludes participants who have voluntarily withdrawn from the study.
        """
        now = datetime.now(timezone.utc)
        stmt = (
            select(ExperimentRetentionScheduleModel)
            .outerjoin(
                ExperimentConsentModel,
                ExperimentRetentionScheduleModel.candidate_id == ExperimentConsentModel.candidate_id,
            )
            .where(
                ExperimentRetentionScheduleModel.status.in_(["PENDING", "DUE", "OVERDUE"]),
                ExperimentRetentionScheduleModel.due_date <= now,
                or_(
                    ExperimentConsentModel.consent_status.is_(None),
                    ExperimentConsentModel.consent_status != "WITHDRAWN",
                ),
            )
            .order_by(ExperimentRetentionScheduleModel.due_date)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def complete_retention(
        self,
        session_id: str,
        retention_session_id: str,
    ) -> Optional[ExperimentRetentionScheduleModel]:
        """Marks a scheduled retention as COMPLETED and links the new session."""
        sched = await self.get_retention_schedule(session_id)
        if sched:
            sched.status = "COMPLETED"
            sched.retention_session_id = retention_session_id
            sched.completed_at = datetime.now(timezone.utc)
            await self.session.flush()
            return sched
        return None

    async def cancel_retention(
        self, session_id: str
    ) -> Optional[ExperimentRetentionScheduleModel]:
        """Cancels a scheduled retention (e.g. upon participant withdrawal)."""
        sched = await self.get_retention_schedule(session_id)
        if sched:
            sched.status = "CANCELLED"
            await self.session.flush()
            return sched
        return None


