"""
Deterministic Score Aggregator for Evaluations and Final Session Reports.
Enforces the strict rule: NO LLM MATH. All scores, weights, and aggregates are computed deterministically in Python.
"""

from typing import List, Dict, Any
from ai.evaluation_engine.rubrics import RubricWeights, get_rubric_for_type


class ScoreAggregator:
    """
    Computes deterministic weighted scores for single turns and aggregates session reports.
    """

    @staticmethod
    def calculate_turn_score(
        sub_scores: Dict[str, float],
        interview_type: str = "TECHNICAL",
        custom_weights: RubricWeights = None,
    ) -> float:
        """
        Calculates the weighted turn score (0.0 - 10.0) from individual sub-metrics.
        """
        weights = custom_weights or get_rubric_for_type(interview_type)
        
        correctness = max(0.0, min(10.0, float(sub_scores.get("correctness", 0.0))))
        completeness = max(0.0, min(10.0, float(sub_scores.get("completeness", 0.0))))
        technical_depth = max(0.0, min(10.0, float(sub_scores.get("technical_depth", 0.0))))
        relevance = max(0.0, min(10.0, float(sub_scores.get("relevance", 0.0))))
        reasoning = max(0.0, min(10.0, float(sub_scores.get("reasoning", 0.0))))

        weighted = (
            correctness * weights.correctness
            + completeness * weights.completeness
            + technical_depth * weights.technical_depth
            + relevance * weights.relevance
            + reasoning * weights.reasoning
        )
        return round(weighted, 2)

    @staticmethod
    def aggregate_session_report(
        evaluations: List[Dict[str, Any]],
        interview_type: str = "TECHNICAL",
    ) -> Dict[str, Any]:
        """
        Aggregates all question evaluations into a comprehensive session report.
        Scores scaled to 0 - 100 for dashboard presentation.
        """
        if not evaluations:
            return {
                "final_score": 0.0,
                "technical_score": 0.0,
                "behavioral_score": 0.0,
                "communication_score": 0.0,
                "summary_strengths": ["No answers submitted."],
                "summary_weaknesses": ["Interview completed without responses."],
                "key_recommendations": ["Complete interview questions to generate feedback."],
            }

        total_turns = len(evaluations)
        avg_overall = sum(e.get("overall_score", 0.0) for e in evaluations) / total_turns
        avg_correctness = sum(e.get("correctness", 0.0) for e in evaluations) / total_turns
        avg_completeness = sum(e.get("completeness", 0.0) for e in evaluations) / total_turns
        avg_tech_depth = sum(e.get("technical_depth", 0.0) for e in evaluations) / total_turns
        avg_relevance = sum(e.get("relevance", 0.0) for e in evaluations) / total_turns
        avg_reasoning = sum(e.get("reasoning", 0.0) for e in evaluations) / total_turns

        # Scale 0-10 -> 0-100
        final_score_100 = round(avg_overall * 10.0, 1)
        tech_score_100 = round(((avg_correctness + avg_tech_depth) / 2.0) * 10.0, 1)
        behav_score_100 = round(((avg_completeness + avg_reasoning) / 2.0) * 10.0, 1)
        comm_score_100 = round(((avg_relevance + avg_reasoning) / 2.0) * 10.0, 1)

        # Aggregate unique strengths, weaknesses, and recommendations
        all_strengths: List[str] = []
        all_weaknesses: List[str] = []
        all_recs: List[str] = []

        for e in evaluations:
            for s in e.get("strengths", []):
                if s and s not in all_strengths:
                    all_strengths.append(s)
            for w in e.get("weaknesses", []):
                if w and w not in all_weaknesses:
                    all_weaknesses.append(w)
            for r in e.get("recommendations", []):
                if r and r not in all_recs:
                    all_recs.append(r)

        return {
            "final_score": final_score_100,
            "technical_score": tech_score_100,
            "behavioral_score": behav_score_100,
            "communication_score": comm_score_100,
            "summary_strengths": all_strengths[:5] or ["Demonstrated consistent engagement."],
            "summary_weaknesses": all_weaknesses[:5] or ["Review missing concepts noted in individual questions."],
            "key_recommendations": all_recs[:5] or ["Continue practicing resume-grounded technical questions."],
        }
