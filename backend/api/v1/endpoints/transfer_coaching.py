"""
Transfer-Aware Coaching REST API Endpoints.
Minimal API surface to drive and inspect the end-to-end coaching loop.
"""

from typing import Optional, Dict
# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, HTTPException, status, Query
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field

from backend.dependencies.database import get_db_session
from backend.core.security import get_authenticated_candidate_id, require_authenticated_candidate_id
from backend.services.transfer_coaching_service import TransferCoachingService
from ai.coaching_orchestrator.schemas import (
    CoachingSessionConfig,
    TrainingContext,
    CandidateStepInput,
    OrchestratorStepResult,
    ResearchTelemetryRecord,
)

router = APIRouter(prefix="/coaching", tags=["Transfer-Aware Coaching"])

# Backward-compatible session registry alias for external test suites.
# Endpoints themselves do not depend on this dict, operating request-scoped via hydrate_session.
_active_services: Dict[str, TransferCoachingService] = {}


class StartCoachingLoopRequest(BaseModel):
    candidate_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    training_context: TrainingContext
    config: Optional[CoachingSessionConfig] = None


class StartCoachingFromInterviewRequest(BaseModel):
    candidate_id: str = Field(..., min_length=1)
    interview_session_id: str = Field(..., min_length=1)
    session_id: Optional[str] = None
    question_id: Optional[str] = None
    config: Optional[CoachingSessionConfig] = None


class SubmitCoachingStepRequest(BaseModel):
    session_id: str = Field(..., min_length=1)
    step_input: CandidateStepInput


@router.get(
    "/recommendation",
    summary="Get Autonomous Evidence-Based Coaching Recommendation",
)
async def get_coaching_recommendation(
    candidate_id: str = Query(..., description="ID of the candidate"),
    target_role: Optional[str] = Query(None, description="Target role name"),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Computes an autonomous, evidence-driven coaching recommendation.
    Inspects interview evaluation history, skill gap analysis, ADI, and failure modes.
    Handles cold-start gracefully when no prior evaluation records exist.
    """
    from backend.services.coaching_tutor_service import CoachingTutorService
    tutor_service = CoachingTutorService(db)
    return await tutor_service.get_autonomous_coaching_recommendation(
        candidate_id=candidate_id, target_role=target_role
    )


@router.post(
    "/start-loop",
    response_model=OrchestratorStepResult,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize Transfer-Aware Coaching Loop",
)
async def start_coaching_loop(
    payload: StartCoachingLoopRequest,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Initializes a new transfer-aware coaching loop anchored by a baseline training task.
    """
    if str(payload.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Candidate ID does not match authenticated principal.",
        )
    try:
        service = TransferCoachingService(session=db)
        result = await service.start_coaching_loop(
            candidate_id=payload.candidate_id,
            session_id=payload.session_id,
            training_context=payload.training_context,
            config=payload.config,
        )
        _active_services[payload.session_id] = service
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize coaching loop: {str(e)}"
        )


@router.post(
    "/start-from-interview",
    response_model=OrchestratorStepResult,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize Transfer-Aware Coaching Loop Directly from Interview Weakness",
)
async def start_coaching_from_interview(
    payload: StartCoachingFromInterviewRequest,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Initializes a new transfer-aware coaching loop anchored directly on an evaluated interview question.
    """
    if str(payload.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Candidate ID does not match authenticated principal.",
        )
    try:
        service = TransferCoachingService(session=db)
        result = await service.start_coaching_from_interview(
            candidate_id=payload.candidate_id,
            interview_session_id=payload.interview_session_id,
            question_id=payload.question_id,
            session_id=payload.session_id,
            config=payload.config,
        )
        _active_services[service.orchestrator.session_id] = service
        return result
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize coaching loop from interview: {str(e)}"
        )


@router.post(
    "/submit-step",
    response_model=OrchestratorStepResult,
    status_code=status.HTTP_200_OK,
    summary="Submit Candidate Step and Advance Coaching Loop",
)
@router.post(
    "/step",
    response_model=OrchestratorStepResult,
    status_code=status.HTTP_200_OK,
    include_in_schema=False,
)
async def submit_coaching_step(
    payload: SubmitCoachingStepRequest,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Submits a candidate answer for the current coaching stage and advances the lifecycle.
    Operates with deterministic database session hydration on every request.
    """
    service = _active_services.get(payload.session_id)
    if not service:
        service = await TransferCoachingService.hydrate_session(
            session=db,
            session_id=payload.session_id,
        )
        if not service:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Coaching session '{payload.session_id}' not found.",
            )
        _active_services[payload.session_id] = service
    else:
        service.session = db

    interview_session = await service.interview_session_repo.get(payload.session_id)
    if interview_session and str(interview_session.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Coaching session '{payload.session_id}' does not belong to candidate '{authenticated_candidate_id}'.",
        )

    try:
        result = await service.submit_step(payload.step_input)
        return result
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Coaching loop step failed: {str(e)}"
        )


@router.get(
    "/session/{session_id}",
    response_model=OrchestratorStepResult,
    status_code=status.HTTP_200_OK,
    summary="Retrieve and Hydrate Active Coaching Session State",
)
async def get_coaching_session(
    session_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieves the authoritative current state of an existing coaching session,
    hydrating from database snapshot.
    """
    service = await TransferCoachingService.hydrate_session(
        session=db,
        session_id=session_id,
    )
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Coaching session '{session_id}' not found.",
        )
    _active_services[session_id] = service

    interview_session = await service.interview_session_repo.get(session_id)
    if interview_session and str(interview_session.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Coaching session '{session_id}' does not belong to candidate '{authenticated_candidate_id}'.",
        )

    return service.get_current_step_result()


@router.get(
    "/session/{session_id}/telemetry",
    response_model=ResearchTelemetryRecord,
    status_code=status.HTTP_200_OK,
    summary="Retrieve Research Telemetry Record",
)
async def get_session_telemetry(
    session_id: str,
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Retrieves the complete empirical research telemetry record for a coaching session.
    """
    service = await TransferCoachingService.hydrate_session(
        session=db,
        session_id=session_id,
    )
    if not service:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Active coaching session '{session_id}' not found."
        )
    _active_services[session_id] = service

    if authenticated_candidate_id:
        interview_session = await service.interview_session_repo.get(session_id)
        if interview_session and str(interview_session.candidate_id) != str(authenticated_candidate_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Coaching session '{session_id}' does not belong to candidate '{authenticated_candidate_id}'.",
            )

    return service.get_telemetry()



