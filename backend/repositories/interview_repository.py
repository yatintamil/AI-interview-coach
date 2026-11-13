"""
Repositories for Interview Sessions, Questions, Answers, Evaluations, and Reports.
"""

from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from backend.models.interview import (
    InterviewSessionModel,
    QuestionModel,
    AnswerModel,
    EvaluationModel,
    SessionReportModel,
)
from backend.repositories.base import BaseRepository


class InterviewSessionRepository(BaseRepository[InterviewSessionModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(InterviewSessionModel, session)

    async def get_with_full_history(self, session_id: str) -> Optional[InterviewSessionModel]:
        stmt = (
            select(InterviewSessionModel)
            .where(InterviewSessionModel.id == session_id)
            .options(
                selectinload(InterviewSessionModel.questions).selectinload(QuestionModel.answer).selectinload(AnswerModel.evaluation),
                selectinload(InterviewSessionModel.report),
                selectinload(InterviewSessionModel.candidate),
                selectinload(InterviewSessionModel.resume),
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_candidate(self, candidate_id: str, skip: int = 0, limit: int = 100) -> List[InterviewSessionModel]:
        stmt = (
            select(InterviewSessionModel)
            .where(InterviewSessionModel.candidate_id == candidate_id)
            .options(
                selectinload(InterviewSessionModel.questions).selectinload(QuestionModel.answer).selectinload(AnswerModel.evaluation),
                selectinload(InterviewSessionModel.report),
            )
            .order_by(InterviewSessionModel.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class QuestionRepository(BaseRepository[QuestionModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(QuestionModel, session)

    async def get_by_session_and_index(self, session_id: str, question_index: int) -> Optional[QuestionModel]:
        stmt = (
            select(QuestionModel)
            .where(
                QuestionModel.session_id == session_id,
                QuestionModel.question_index == question_index
            )
            .options(
                selectinload(QuestionModel.answer).selectinload(AnswerModel.evaluation)
            )
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_session(self, session_id: str) -> List[QuestionModel]:
        stmt = (
            select(QuestionModel)
            .where(QuestionModel.session_id == session_id)
            .options(
                selectinload(QuestionModel.answer).selectinload(AnswerModel.evaluation)
            )
            .order_by(QuestionModel.question_index.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class AnswerRepository(BaseRepository[AnswerModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(AnswerModel, session)

    async def get_by_question(self, question_id: str) -> Optional[AnswerModel]:
        stmt = (
            select(AnswerModel)
            .where(AnswerModel.question_id == question_id)
            .options(selectinload(AnswerModel.evaluation))
        )
        res = await self.session.execute(stmt)
        return res.scalars().first()


class EvaluationRepository(BaseRepository[EvaluationModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(EvaluationModel, session)

    async def get_by_answer(self, answer_id: str) -> Optional[EvaluationModel]:
        stmt = select(EvaluationModel).where(EvaluationModel.answer_id == answer_id)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_session(self, session_id: str) -> List[EvaluationModel]:
        stmt = select(EvaluationModel).where(EvaluationModel.session_id == session_id).order_by(EvaluationModel.created_at.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())


class SessionReportRepository(BaseRepository[SessionReportModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(SessionReportModel, session)

    async def get_by_session(self, session_id: str) -> Optional[SessionReportModel]:
        stmt = select(SessionReportModel).where(SessionReportModel.session_id == session_id)
        res = await self.session.execute(stmt)
        return res.scalars().first()
