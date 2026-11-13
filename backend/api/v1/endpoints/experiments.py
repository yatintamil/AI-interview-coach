"""
REST API Endpoints for the Experimental Framework & Controlled Baselines.
Minimal API surface to initiate sessions, submit trial turns, inspect sessions, and export telemetry.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field

from backend.dependencies.database import get_db_session
from backend.core.security import get_authenticated_candidate_id, require_researcher_auth
from backend.repositories.experiment_repository import ExperimentRepository
from backend.domain.experiments.schemas import (
    ExperimentConfig,
    ExperimentStepInput,
    ExperimentStepResult,
    ExperimentSessionDTO,
    ExperimentTrialRaw,
    ConsentSubmissionInput,
    ConsentRecordDTO,
    StudyInformationDTO,
    ParticipantWithdrawalInput,
    ParticipantWithdrawalResultDTO,
    RetentionScheduleDTO,
)
from backend.domain.experiments.study_info import DEFAULT_STUDY_INFO
from backend.services.experiment_service import ExperimentService

router = APIRouter(prefix="/experiments", tags=["Experimental Framework"])

# Service instance cache across HTTP requests
_active_services = {}


async def _verify_session_ownership(
    db: AsyncSession, session_id: str, authenticated_candidate_id: Optional[str]
) -> None:
    if not authenticated_candidate_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing or invalid authentication token.",
        )
    repo = ExperimentRepository(db)
    sess = await repo.get(session_id)
    if sess and str(sess.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Experiment session '{session_id}' does not belong to candidate '{authenticated_candidate_id}'.",
        )


class StartExperimentRequest(BaseModel):
    candidate_id: str = Field(..., min_length=1, description="Candidate ID")
    config: ExperimentConfig = Field(..., description="Experimental parameters")
    experiment_name: str = Field(default="Comparative_Trial_v1", description="Experiment trial label")
    session_id: Optional[str] = Field(default=None, description="Optional predetermined session ID")


@router.post(
    "/start",
    response_model=ExperimentStepResult,
    status_code=status.HTTP_201_CREATED,
    summary="Start Experimental Session",
)
async def start_experiment(
    payload: StartExperimentRequest,
    db: AsyncSession = Depends(get_db_session),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Initializes an experimental session for the requested condition and returns the first trial task.
    """
    if authenticated_candidate_id and str(payload.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Cannot start experiment for candidate '{payload.candidate_id}' when authenticated as '{authenticated_candidate_id}'.",
        )

    try:
        service = ExperimentService(session=db)
        result = await service.start_experiment(
            candidate_id=payload.candidate_id,
            config=payload.config,
            experiment_name=payload.experiment_name,
            session_id=payload.session_id,
        )
        _active_services[result.session_id] = service
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start experiment: {str(e)}",
        )


@router.post(
    "/{session_id}/step",
    response_model=ExperimentStepResult,
    status_code=status.HTTP_200_OK,
    summary="Submit Candidate Step and Advance Experiment",
)
async def execute_experiment_step(
    session_id: str,
    payload: ExperimentStepInput,
    db: AsyncSession = Depends(get_db_session),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Submits a candidate answer for the current trial and advances the experimental condition lifecycle.
    """
    await _verify_session_ownership(db, session_id, authenticated_candidate_id)
    service = _active_services.get(session_id)
    if not service:
        service = ExperimentService(session=db)
        _active_services[session_id] = service

    try:
        service.session = db
        service.repo.session = db
        result = await service.execute_step(session_id, payload)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Experiment step failed: {str(e)}",
        )


# =============================================================================
# Phase 9.3: Participant Onboarding, Consent, Withdrawal & Retention Endpoints
# (Declared before dynamic /{session_id} route to avoid FastAPI route shadowing)
# =============================================================================

@router.get(
    "/study-info",
    response_model=StudyInformationDTO,
    summary="Get Configurable Study Information & Protocol",
)
async def get_study_info():
    """
    Returns configurable study metadata, procedures, voluntary participation terms,
    and data handling policy for participant onboarding.
    """
    return DEFAULT_STUDY_INFO


@router.post(
    "/consent",
    response_model=ConsentRecordDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Record Participant Informed Consent",
)
async def submit_consent(
    payload: ConsentSubmissionInput,
    db: AsyncSession = Depends(get_db_session),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Records or updates explicit informed consent on the backend before experiment enrollment.
    """
    if authenticated_candidate_id and str(payload.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Cannot submit consent for candidate '{payload.candidate_id}' when authenticated as '{authenticated_candidate_id}'.",
        )

    if not payload.agreed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Informed consent must be explicitly agreed to participate.",
        )

    repo = ExperimentRepository(db)
    existing = await repo.get_consent(payload.candidate_id)
    if existing and existing.consent_status == "WITHDRAWN":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Candidate '{payload.candidate_id}' has formally withdrawn consent from the study. Re-enrollment after voluntary withdrawal is prohibited.",
        )

    consent = await repo.record_consent(
        candidate_id=payload.candidate_id,
        consent_version=payload.consent_version,
        status="CONSENTED",
        study_title=DEFAULT_STUDY_INFO.title,
        study_metadata=payload.study_metadata,
    )
    return ConsentRecordDTO(
        id=consent.id,
        candidate_id=consent.candidate_id,
        consent_status=consent.consent_status,
        consent_version=consent.consent_version,
        consented_at=consent.consented_at,
        withdrawn_at=consent.withdrawn_at,
        withdrawal_reason=consent.withdrawal_reason,
        study_title=consent.study_title,
    )


@router.get(
    "/consent/{candidate_id}",
    response_model=ConsentRecordDTO,
    summary="Get Participant Informed Consent Record",
)
async def get_candidate_consent(
    candidate_id: str,
    db: AsyncSession = Depends(get_db_session),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Retrieves the persisted informed consent record for a candidate.
    """
    if authenticated_candidate_id and str(candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Cannot view consent for candidate '{candidate_id}'.",
        )

    repo = ExperimentRepository(db)
    consent = await repo.get_consent(candidate_id)
    if not consent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No consent record found for candidate '{candidate_id}'.",
        )
    return ConsentRecordDTO(
        id=consent.id,
        candidate_id=consent.candidate_id,
        consent_status=consent.consent_status,
        consent_version=consent.consent_version,
        consented_at=consent.consented_at,
        withdrawn_at=consent.withdrawn_at,
        withdrawal_reason=consent.withdrawal_reason,
        study_title=consent.study_title,
    )


@router.post(
    "/withdraw",
    response_model=ParticipantWithdrawalResultDTO,
    status_code=status.HTTP_200_OK,
    summary="Voluntary Participant Withdrawal",
)
async def withdraw_participant(
    payload: ParticipantWithdrawalInput,
    db: AsyncSession = Depends(get_db_session),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Records voluntary participant withdrawal. Abandons all active sessions,
    blocks future participation, and marks records for research dataset exclusion.
    """
    if authenticated_candidate_id and str(payload.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Cannot withdraw candidate '{payload.candidate_id}' when authenticated as '{authenticated_candidate_id}'.",
        )

    service = ExperimentService(session=db)
    res = await service.withdraw_participant(payload.candidate_id, reason=payload.reason)
    return ParticipantWithdrawalResultDTO(**res)


class ActiveSessionResponse(BaseModel):
    has_active_session: bool
    session: Optional[ExperimentSessionDTO] = None
    current_task_prompt: Optional[str] = None


@router.get(
    "/candidate/{candidate_id}/active",
    response_model=ActiveSessionResponse,
    summary="Get Active Experiment Session for Candidate",
)
async def get_active_candidate_session(
    candidate_id: str,
    db: AsyncSession = Depends(get_db_session),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Checks for an in-progress session to support seamless participant progress restoration.
    """
    if authenticated_candidate_id and str(candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Cannot access active session for candidate '{candidate_id}'.",
        )

    repo = ExperimentRepository(db)
    sessions = await repo.list_by_candidate(candidate_id)
    active = next((s for s in sessions if s.status == "IN_PROGRESS"), None)
    if not active:
        return ActiveSessionResponse(has_active_session=False)

    service = ExperimentService(session=db)
    sess_dto = await service.get_session(active.id)
    cached_strat = service._strategy_cache.get(active.id)
    prompt = None
    if cached_strat and hasattr(cached_strat, "current_task") and cached_strat.current_task:
        prompt = cached_strat.current_task.get("prompt")

    return ActiveSessionResponse(
        has_active_session=True,
        session=sess_dto,
        current_task_prompt=prompt,
    )


@router.get(
    "/retention/due",
    response_model=List[RetentionScheduleDTO],
    summary="List Due Longitudinal Retention Participants",
)
async def list_due_retentions(
    db: AsyncSession = Depends(get_db_session),
    _researcher: Dict[str, Any] = Depends(require_researcher_auth),
):
    """
    Returns participants and sessions currently due or overdue for their 7-day or 14-day
    delayed retention assessment, enabling supervised follow-up.
    """
    repo = ExperimentRepository(db)
    items = await repo.list_due_retentions()
    return [
        RetentionScheduleDTO(
            id=item.id,
            session_id=item.session_id,
            candidate_id=item.candidate_id,
            delay_days=item.delay_days,
            due_date=item.due_date,
            status=item.status,
            retention_session_id=item.retention_session_id,
            created_at=item.created_at,
        )
        for item in items
    ]


# =============================================================================
# Session Inspection & Lifecycle Endpoints
# =============================================================================

@router.get(
    "/{session_id}",
    response_model=ExperimentSessionDTO,
    status_code=status.HTTP_200_OK,
    summary="Get Experiment Session Details with Derived Metrics",
)
async def get_experiment_session(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Retrieves complete experiment session state, trials, and on-demand derived metrics.
    """
    await _verify_session_ownership(db, session_id, authenticated_candidate_id)
    try:
        service = ExperimentService(session=db)
        return await service.get_session(session_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve session: {str(e)}",
        )


@router.get(
    "/{session_id}/telemetry",
    response_model=List[ExperimentTrialRaw],
    status_code=status.HTTP_200_OK,
    summary="Get Raw Experiment Trial Telemetry",
)
async def get_experiment_telemetry(
    session_id: str,
    db: AsyncSession = Depends(get_db_session),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Exports raw observation trials captured during the experimental session for empirical analysis.
    """
    await _verify_session_ownership(db, session_id, authenticated_candidate_id)
    try:
        service = ExperimentService(session=db)
        return await service.get_telemetry(session_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve telemetry: {str(e)}",
        )


class AbandonSessionRequest(BaseModel):
    reason: Optional[str] = Field(default=None, description="Optional qualitative reason for abandonment")


@router.post(
    "/{session_id}/abandon",
    response_model=ExperimentSessionDTO,
    status_code=status.HTTP_200_OK,
    summary="Record Session Abandonment",
)
async def abandon_experiment_session(
    session_id: str,
    payload: AbandonSessionRequest = AbandonSessionRequest(),
    db: AsyncSession = Depends(get_db_session),
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
):
    """
    Formally records an experimental session as abandoned (e.g. dropout, voluntary withdrawal, or timeout)
    while preserving all completed trials for attrition and intention-to-treat analysis.
    """
    await _verify_session_ownership(db, session_id, authenticated_candidate_id)
    try:
        service = ExperimentService(session=db)
        await service.abandon_session(session_id, reason=payload.reason)
        return await service.get_session(session_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to record session abandonment: {str(e)}",
        )
