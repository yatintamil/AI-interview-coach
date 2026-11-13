"""
Analytics Application Service.
Calculates score aggregations, performance trends, knowledge gaps, and historical metrics.
"""

from collections import Counter
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from backend.repositories.interview_repository import (
    InterviewSessionRepository,
    EvaluationRepository,
)
from backend.repositories.candidate_repository import CandidateRepository
from backend.models.interview import InterviewSessionModel
from backend.schemas.analytics import (
    AnalyticsOverviewResponse,
    PerformanceHistoryResponse,
    PerformanceTrendPoint,
    SkillsAnalyticsResponse,
    KnowledgeGapItem,
)


class AnalyticsService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_repo = InterviewSessionRepository(session)
        self.eval_repo = EvaluationRepository(session)
        self.candidate_repo = CandidateRepository(session)

    async def get_overview(self, candidate_id: str) -> AnalyticsOverviewResponse:
        candidate = await self.candidate_repo.get(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found."
            )

        sessions = await self.session_repo.list_by_candidate(candidate_id, limit=200)
        completed_sessions = [s for s in sessions if s.status == "COMPLETED" and s.report]

        if not completed_sessions:
            return AnalyticsOverviewResponse(
                candidate_id=candidate_id,
                total_interviews=len(sessions),
                completed_interviews=0,
                overall_average_score=0.0,
                technical_average_score=0.0,
                behavioral_average_score=0.0,
                communication_average_score=0.0,
                top_strengths=["Complete an interview session to reveal strengths."],
                common_weaknesses=["Complete an interview session to identify focus areas."],
                key_recommendations=["Start your first AI practice interview."],
                latest_session=None,
            )

        count = len(completed_sessions)
        avg_overall = round(sum(s.report.final_score for s in completed_sessions) / count, 1)
        avg_tech = round(sum(s.report.technical_score for s in completed_sessions) / count, 1)
        avg_behav = round(sum(s.report.behavioral_score for s in completed_sessions) / count, 1)
        avg_comm = round(sum(s.report.communication_score for s in completed_sessions) / count, 1)

        # Aggregate unique strengths and weaknesses
        strengths_counter: Counter = Counter()
        weaknesses_counter: Counter = Counter()
        recs_list: List[str] = []

        for s in completed_sessions:
            for st in (s.report.summary_strengths or []):
                strengths_counter[st] += 1
            for wk in (s.report.summary_weaknesses or []):
                weaknesses_counter[wk] += 1
            for rc in (s.report.key_recommendations or []):
                if rc not in recs_list:
                    recs_list.append(rc)

        top_strengths = [item[0] for item in strengths_counter.most_common(5)]
        common_weaknesses = [item[0] for item in weaknesses_counter.most_common(5)]

        latest = completed_sessions[0]
        latest_point = PerformanceTrendPoint(
            session_id=latest.id,
            date=latest.end_time or latest.created_at,
            target_role=latest.target_role,
            interview_type=latest.interview_type,
            overall_score=latest.report.final_score,
            technical_score=latest.report.technical_score,
            behavioral_score=latest.report.behavioral_score,
            communication_score=latest.report.communication_score,
        )

        return AnalyticsOverviewResponse(
            candidate_id=candidate_id,
            total_interviews=len(sessions),
            completed_interviews=count,
            overall_average_score=avg_overall,
            technical_average_score=avg_tech,
            behavioral_average_score=avg_behav,
            communication_average_score=avg_comm,
            top_strengths=top_strengths or ["Consistent technical responses."],
            common_weaknesses=common_weaknesses or ["Review suggested edge cases."],
            key_recommendations=recs_list[:5] or ["Continue practicing resume-grounded mock interviews."],
            latest_session=latest_point,
        )

    async def get_performance_history(self, candidate_id: str) -> PerformanceHistoryResponse:
        candidate = await self.candidate_repo.get(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found."
            )

        sessions = await self.session_repo.list_by_candidate(candidate_id, limit=100)
        # Order chronologically ascending for trendline plotting
        completed = [s for s in sessions if s.status == "COMPLETED" and s.report]
        completed_sorted = sorted(completed, key=lambda s: s.created_at)

        trends = [
            PerformanceTrendPoint(
                session_id=s.id,
                date=s.end_time or s.created_at,
                target_role=s.target_role,
                interview_type=s.interview_type,
                overall_score=s.report.final_score,
                technical_score=s.report.technical_score,
                behavioral_score=s.report.behavioral_score,
                communication_score=s.report.communication_score,
            )
            for s in completed_sorted
        ]

        return PerformanceHistoryResponse(
            candidate_id=candidate_id,
            trends=trends,
            total_completed_interviews=len(trends),
        )

    async def get_skills_analytics(self, candidate_id: str) -> SkillsAnalyticsResponse:
        candidate = await self.candidate_repo.get(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found."
            )

        sessions = await self.session_repo.list_by_candidate(candidate_id, limit=100)
        topic_scores_accumulator: Dict[str, List[float]] = {}
        missing_concepts_map: Dict[str, Dict[str, Any]] = {}

        for s in sessions:
            for q in s.questions:
                topic = q.topic or "General"
                if q.answer and q.answer.evaluation:
                    ev = q.answer.evaluation
                    # Scale turn score 0-10 -> 0-100
                    turn_score_100 = round(ev.overall_score * 10.0, 1)
                    topic_scores_accumulator.setdefault(topic, []).append(turn_score_100)

                    # Extract missing concepts
                    for mc in (ev.missing_concepts or []):
                        if mc:
                            mc_clean = mc.strip()
                            if mc_clean not in missing_concepts_map:
                                rec = (ev.recommendations[0] if ev.recommendations else f"Study key concepts in {topic}.")
                                missing_concepts_map[mc_clean] = {
                                    "concept": mc_clean,
                                    "occurrences": 1,
                                    "topic": topic,
                                    "recommendation": rec,
                                }
                            else:
                                missing_concepts_map[mc_clean]["occurrences"] += 1

        topic_averages = {
            topic: round(sum(scores) / len(scores), 1)
            for topic, scores in topic_scores_accumulator.items()
        }

        # Sort knowledge gaps by occurrence count descending
        sorted_gaps = sorted(
            missing_concepts_map.values(),
            key=lambda x: x["occurrences"],
            reverse=True,
        )

        knowledge_gap_items = [
            KnowledgeGapItem(
                concept=g["concept"],
                occurrences=g["occurrences"],
                topic=g["topic"],
                recommendation=g["recommendation"],
            )
            for g in sorted_gaps[:10]
        ]

        return SkillsAnalyticsResponse(
            candidate_id=candidate_id,
            topic_scores=topic_averages,
            knowledge_gaps=knowledge_gap_items,
        )
