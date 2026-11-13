"""
FastAPI Router for Single AI Interviewer & Interview Sessions.
"""

from typing import List, Optional
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db_session
from backend.core.security import (
    get_authenticated_candidate_id,
    require_authenticated_candidate_id,
    verify_candidate_access,
)
from backend.services.interview_service import InterviewService
from backend.schemas.interview import (
    InterviewCreateRequest,
    InterviewSessionResponse,
    AnswerSubmitRequest,
    TurnAnswerResultResponse,
    CoachHintRequest,
    CoachHintResponse,
    InterviewWeaknessesResponse,
    ConcludeInterviewRequest,
)

router = APIRouter(tags=["AI Interview Engine & Sessions"])


@router.post(
    "/interviews",
    response_model=InterviewSessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new interview session",
)
async def create_interview(
    payload: InterviewCreateRequest,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    if str(payload.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Candidate ID does not match authenticated principal.",
        )
    service = InterviewService(session)
    return await service.create_session(payload)


@router.get(
    "/interviews/{interview_id}",
    response_model=InterviewSessionResponse,
    summary="Get interview session state and history",
)
async def get_interview(
    interview_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    service = InterviewService(session)
    res = await service.get_session(interview_id)
    if str(res.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Interview session '{interview_id}' does not belong to candidate '{authenticated_candidate_id}'.",
        )
    return res


@router.get(
    "/interviews/{interview_id}/weaknesses",
    response_model=InterviewWeaknessesResponse,
    summary="Retrieve identified candidate weaknesses and coaching training contexts from an interview",
)
async def get_interview_weaknesses(
    interview_id: str,
    eligibility_threshold: float = 7.0,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    service = InterviewService(session)
    res = await service.get_session_weaknesses(
        session_id=interview_id, eligibility_threshold=eligibility_threshold
    )
    if str(res.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Interview session '{interview_id}' does not belong to candidate '{authenticated_candidate_id}'.",
        )
    return res



@router.post(
    "/interviews/{interview_id}/start",
    response_model=InterviewSessionResponse,
    summary="Start interview session and generate first resume-grounded question",
)
async def start_interview(
    interview_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    service = InterviewService(session)
    session_obj = await service.session_repo.get(interview_id)
    if not session_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Interview session '{interview_id}' not found.")
    if str(session_obj.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Interview session '{interview_id}' does not belong to candidate '{authenticated_candidate_id}'.",
        )
    return await service.start_session(interview_id)


@router.post(
    "/interviews/{interview_id}/answer",
    response_model=TurnAnswerResultResponse,
    summary="Submit answer for active question, evaluate with evidence, and advance interview",
)
async def answer_question(
    interview_id: str,
    payload: AnswerSubmitRequest,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    service = InterviewService(session)
    session_obj = await service.session_repo.get(interview_id)
    if not session_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Interview session '{interview_id}' not found.")
    if str(session_obj.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Interview session '{interview_id}' does not belong to candidate '{authenticated_candidate_id}'.",
        )
    return await service.submit_answer_and_progress(
        session_id=interview_id,
        answer_text=payload.answer_text,
        response_time_seconds=payload.response_time_seconds,
    )


@router.post(
    "/interviews/{interview_id}/hint",
    response_model=CoachHintResponse,
    summary="Request Socratic Coach Hint & Cognitive Scaffolding for active question",
)
async def get_interview_hint(
    interview_id: str,
    payload: Optional[CoachHintRequest] = None,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    service = InterviewService(session)
    session_obj = await service.session_repo.get(interview_id)
    if not session_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Interview session '{interview_id}' not found.")
    if str(session_obj.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Interview session '{interview_id}' does not belong to candidate '{authenticated_candidate_id}'.",
        )
    partial = payload.partial_answer if payload else None
    return await service.get_coach_hint(session_id=interview_id, partial_answer=partial)


@router.post(
    "/interviews/{interview_id}/complete",
    response_model=InterviewSessionResponse,
    summary="Complete interview session and generate final performance report",
)
async def complete_interview(
    interview_id: str,
    payload: Optional[ConcludeInterviewRequest] = None,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    service = InterviewService(session)
    session_obj = await service.session_repo.get(interview_id)
    if not session_obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Interview session '{interview_id}' not found.")
    if str(session_obj.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Interview session '{interview_id}' does not belong to candidate '{authenticated_candidate_id}'.",
        )
    reason = payload.reason if payload and payload.reason else "CANDIDATE_REQUESTED"
    return await service.complete_session(interview_id, reason=reason)


@router.get(
    "/candidates/{candidate_id}/interviews",
    response_model=List[InterviewSessionResponse],
    summary="List all interview sessions for a candidate",
)
async def list_candidate_interviews(
    candidate_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session),
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    service = InterviewService(session)
    return await service.list_candidate_interviews(candidate_id)
