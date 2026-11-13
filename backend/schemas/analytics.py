"""
Pydantic Schemas for Analytics Dashboard, Performance History, and Knowledge Gaps.
"""

from datetime import datetime
from typing import List, Dict, Optional
from pydantic import BaseModel, Field


class PerformanceTrendPoint(BaseModel):
    session_id: str
    date: datetime
    target_role: str
    interview_type: str
    overall_score: float
    technical_score: float
    behavioral_score: float
    communication_score: float


class PerformanceHistoryResponse(BaseModel):
    candidate_id: str
    trends: List[PerformanceTrendPoint] = []
    total_completed_interviews: int = 0


class KnowledgeGapItem(BaseModel):
    concept: str
    occurrences: int
    topic: str
    recommendation: str


class SkillsAnalyticsResponse(BaseModel):
    candidate_id: str
    topic_scores: Dict[str, float] = {}
    knowledge_gaps: List[KnowledgeGapItem] = []


class AnalyticsOverviewResponse(BaseModel):
    candidate_id: str
    total_interviews: int = 0
    completed_interviews: int = 0
    overall_average_score: float = 0.0
    technical_average_score: float = 0.0
    behavioral_average_score: float = 0.0
    communication_average_score: float = 0.0
    top_strengths: List[str] = []
    common_weaknesses: List[str] = []
    key_recommendations: List[str] = []
    latest_session: Optional[PerformanceTrendPoint] = None
