"""
FastAPI Router for Analytics Dashboard & Performance Tracking.
"""

# pyrefly: ignore [missing-import]
from fastapi import APIRouter, Depends, Query, HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db_session
from backend.services.analytics_service import AnalyticsService
from backend.schemas.analytics import (
    AnalyticsOverviewResponse,
    PerformanceHistoryResponse,
    SkillsAnalyticsResponse,
)

router = APIRouter(prefix="/analytics", tags=["Analytics & Performance Dashboard"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get high-level candidate performance overview",
)
async def get_analytics_overview(
    candidate_id: str = Query(..., description="Candidate UUID"),
    session: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(session)
    return await service.get_overview(candidate_id)


@router.get(
    "/history",
    response_model=PerformanceHistoryResponse,
    summary="Get historical performance trends across interview sessions",
)
async def get_performance_history(
    candidate_id: str = Query(..., description="Candidate UUID"),
    session: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(session)
    return await service.get_performance_history(candidate_id)


@router.get(
    "/skills",
    response_model=SkillsAnalyticsResponse,
    summary="Get skill/topic scores and aggregated knowledge gaps",
)
async def get_skills_analytics(
    candidate_id: str = Query(..., description="Candidate UUID"),
    session: AsyncSession = Depends(get_db_session),
):
    service = AnalyticsService(session)
    return await service.get_skills_analytics(candidate_id)
