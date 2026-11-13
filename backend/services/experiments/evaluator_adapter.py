"""
Application-level Evaluator Adapter implementing EvaluationPort.
Ensures identical evaluation rubric and scoring engine across all three experimental conditions.
"""

from typing import List, Dict, Any, Optional
from ai.evaluation_engine.evaluator import AIEvaluator
from backend.domain.experiments.ports import EvaluationPort


class EvaluatorAdapter(EvaluationPort):
    """
    Adapter delegating to AIEvaluator while satisfying the pure domain EvaluationPort protocol.
    Guarantees that evaluation scoring and feedback generation remain constant across conditions.
    """

    def __init__(self, evaluator: Optional[AIEvaluator] = None):
        self.evaluator = evaluator or AIEvaluator()

    async def evaluate_answer(
        self,
        target_role: str,
        interview_type: str,
        topic: str,
        question_text: str,
        expected_concepts: List[str],
        resume_evidence: str,
        candidate_answer: str,
        response_time_seconds: float = 0.0,
    ) -> Dict[str, Any]:
        """
        Executes uniform evaluation across all conditions.
        """
        return await self.evaluator.evaluate_answer(
            target_role=target_role,
            interview_type=interview_type,
            topic=topic,
            question_text=question_text,
            expected_concepts=expected_concepts,
            resume_evidence=resume_evidence,
            candidate_answer=candidate_answer,
            response_time_seconds=response_time_seconds,
        )
