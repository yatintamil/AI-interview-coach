"""
REST API Endpoints for Research Evaluation & Analysis.
Provides candidate-level metrics, condition cohort aggregation, cross-condition comparisons,
and CSV/JSON export for empirical analysis.
"""

from typing import List, Optional, Any, Dict
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db_session
from backend.core.security import (
    get_authenticated_candidate_id,
    require_authenticated_candidate_id,
    require_researcher_auth,
)
from backend.domain.experiments.enums import ExperimentCondition
from backend.domain.research.enums import ExportFormat
from backend.domain.research.schemas import (
    CandidateResearchResult,
    ResearchConditionSummary,
    ConditionComparison,
    ParticipantExportRecord,
)
from backend.domain.research.expert_validation import (
    ExpertDiagnosisAnnotation,
    ExpertDiagnosisEvaluationResult,
    evaluate_diagnosis_against_expert_labels,
)
from backend.repositories.experiment_repository import ExperimentRepository
from backend.services.research.evaluation_service import ResearchEvaluationService
from backend.services.research.comparison_service import ResearchComparisonService
from backend.services.research.export_service import ResearchExportService

router = APIRouter(prefix="/research", tags=["Research Evaluation & Analysis"])


@router.get(
    "/session/{session_id}",
    response_model=CandidateResearchResult,
    summary="Get Candidate-Level Research Metrics",
)
async def get_session_metrics(
    session_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Computes complete structured research metrics (performance, learning gains, transfer, recovery,
    assistance, efficiency) for an individual experimental session.
    """
    repo = ExperimentRepository(db)
    sess = await repo.get(session_id)
    if not sess:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Research session '{session_id}' not found.")
    if str(sess.candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Research session '{session_id}' does not belong to candidate '{authenticated_candidate_id}'.",
        )
    service = ResearchEvaluationService(repo)
    try:
        return await service.evaluate_session(session_id)
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(ve))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute candidate research metrics: {str(e)}",
        )


@router.get(
    "/candidate/{candidate_id}",
    response_model=List[CandidateResearchResult],
    summary="Get All Research Session Metrics for a Candidate",
)
async def get_candidate_research_metrics(
    candidate_id: str,
    db: AsyncSession = Depends(get_db_session),
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
):
    """
    Computes candidate-level research metrics across all experimental sessions completed by the candidate.
    """
    if str(candidate_id) != str(authenticated_candidate_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: Cannot access research metrics for candidate '{candidate_id}'.",
        )

    repo = ExperimentRepository(db)
    service = ResearchEvaluationService(repo)
    try:
        sessions = await repo.list_by_candidate(candidate_id)
        results = []
        for s in sessions:
            res = await service.evaluate_session(s.id)
            results.append(res)
        return results
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch candidate research metrics: {str(e)}",
        )


@router.get(
    "/condition/{condition}",
    response_model=ResearchConditionSummary,
    summary="Get Aggregated Condition Cohort Summary",
)
async def get_condition_summary(
    condition: str,
    db: AsyncSession = Depends(get_db_session),
    _researcher: Dict[str, Any] = Depends(require_researcher_auth),
):
    """
    Computes descriptive statistics (mean, median, std dev, min, max) for a specific experimental condition cohort.
    Valid conditions: CONDITION_A, CONDITION_B, CONDITION_C.
    """
    try:
        cond_enum = ExperimentCondition(condition)
    except ValueError:
        valid_opts = [c.value for c in ExperimentCondition]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid condition '{condition}'. Must be one of: {valid_opts}",
        )

    repo = ExperimentRepository(db)
    service = ResearchEvaluationService(repo)
    try:
        return await service.summarize_condition(cond_enum.value)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to summarize condition cohort: {str(e)}",
        )


@router.get(
    "/compare",
    response_model=ConditionComparison,
    summary="Cross-Condition Comparative Analysis",
)
async def compare_conditions(
    db: AsyncSession = Depends(get_db_session),
    _researcher: Dict[str, Any] = Depends(require_researcher_auth),
):
    """
    Generates comparative descriptive evaluation matrix across Condition A, Condition B, and Condition C.
    Strictly descriptive analysis (no inferential hypothesis testing or p-values).
    """
    repo = ExperimentRepository(db)
    service = ResearchComparisonService(repo)
    try:
        return await service.compare_all_conditions()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate cross-condition comparison: {str(e)}",
        )


@router.get(
    "/export",
    summary="Export Research Analysis Dataset",
)
async def export_dataset(
    format: ExportFormat = Query(default=ExportFormat.CSV, description="Export format: csv or json"),
    condition: Optional[str] = Query(default=None, description="Optional condition filter"),
    skill: Optional[str] = Query(default=None, description="Optional skill filter"),
    anonymize: bool = Query(default=False, description="Whether to anonymize participant and session identifiers"),
    include_withdrawn: bool = Query(default=False, description="Whether to include participants who voluntarily withdrew from the study"),
    db: AsyncSession = Depends(get_db_session),
    _researcher: Dict[str, Any] = Depends(require_researcher_auth),
):
    """
    Exports participant-level research records in CSV or JSON format for downstream statistical software.
    Preserves participant/session identity with non-sensitive IDs. Supports cryptographic pseudonymization.
    """
    if condition:
        try:
            ExperimentCondition(condition)
        except ValueError:
            valid_opts = [c.value for c in ExperimentCondition]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid condition filter '{condition}'. Must be one of: {valid_opts}",
            )

    repo = ExperimentRepository(db)
    service = ResearchExportService(repo)
    try:
        exported_data = await service.export_dataset(
            format_type=format,
            condition=condition,
            skill=skill,
            anonymize=anonymize,
            include_withdrawn=include_withdrawn,
        )

        if format == ExportFormat.CSV:
            return Response(
                content=exported_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=research_dataset.csv"},
            )
        else:
            return exported_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export research dataset: {str(e)}",
        )


@router.get(
    "/export/trials",
    summary="Export Trial-Level Research Dataset",
)
async def export_trials_dataset(
    format: ExportFormat = Query(default=ExportFormat.CSV, description="Export format: csv or json"),
    condition: Optional[str] = Query(default=None, description="Optional condition filter"),
    skill: Optional[str] = Query(default=None, description="Optional skill filter"),
    anonymize: bool = Query(default=False, description="Whether to anonymize participant and session identifiers"),
    include_withdrawn: bool = Query(default=False, description="Whether to include participants who voluntarily withdrew from the study"),
    db: AsyncSession = Depends(get_db_session),
    _researcher: Dict[str, Any] = Depends(require_researcher_auth),
):
    """
    Exports granular trial-level research records for longitudinal, mixed-effects, or micro-level analysis.
    Supports cryptographic pseudonymization of participant and session IDs.
    """
    if condition:
        try:
            ExperimentCondition(condition)
        except ValueError:
            valid_opts = [c.value for c in ExperimentCondition]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid condition filter '{condition}'. Must be one of: {valid_opts}",
            )

    repo = ExperimentRepository(db)
    service = ResearchExportService(repo)
    try:
        exported_data = await service.export_trials_dataset(
            format_type=format,
            condition=condition,
            skill=skill,
            anonymize=anonymize,
            include_withdrawn=include_withdrawn,
        )

        if format == ExportFormat.CSV:
            return Response(
                content=exported_data,
                media_type="text/csv",
                headers={"Content-Disposition": "attachment; filename=trials_dataset.csv"},
            )
        else:
            return exported_data
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export trials dataset: {str(e)}",
        )


class ExpertEvaluationRequest(BaseModel):
    session_ids: Optional[List[str]] = Field(default=None, description="Filter trials to specific session IDs")
    annotations: List[ExpertDiagnosisAnnotation] = Field(..., min_length=1, description="List of expert annotations")


@router.post(
    "/expert-evaluations",
    response_model=ExpertDiagnosisEvaluationResult,
    summary="Evaluate System Diagnosis Against Independent Expert Annotations",
)
async def evaluate_expert_annotations(
    payload: ExpertEvaluationRequest,
    db: AsyncSession = Depends(get_db_session),
    _researcher: Dict[str, Any] = Depends(require_researcher_auth),
):
    """
    Accepts independent human expert diagnosis annotations and computes empirical accuracy,
    inter-rater agreement (Cohen's Kappa), and disagreement telemetry.
    """
    repo = ExperimentRepository(db)
    try:
        if payload.session_ids:
            all_trials = []
            for sid in payload.session_ids:
                sess = await repo.get_session_with_trials(sid)
                if sess and sess.trials:
                    all_trials.extend(sess.trials)
        else:
            sessions = await repo.list_all_with_trials(limit=2000)
            all_trials = [t for s in sessions for t in (s.trials or [])]

        return evaluate_diagnosis_against_expert_labels(all_trials, payload.annotations)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate expert annotations: {str(e)}",
        )
