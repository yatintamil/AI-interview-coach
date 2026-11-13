"""
Domain ports and interfaces for the experimental framework.
Pure abstract interfaces using typing.Protocol to enforce Dependency Inversion.
"""

from typing import Protocol, List, Dict, Any, Optional
from backend.domain.experiments.enums import ExperimentPhase, TaskDifficulty


class EvaluationPort(Protocol):
    """
    Application-level abstraction for answer evaluation.
    Enforces identical evaluation rubric and scoring engine across all conditions.
    """
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
        ...


class TaskSetProvider(Protocol):
    """
    Domain protocol for reproducible task set retrieval.
    Provides identical task pools to all three experimental conditions.
    """
    def get_task(
        self,
        task_set_id: str,
        phase: ExperimentPhase,
        difficulty: Optional[TaskDifficulty] = None,
        seed: int = 42,
        form_order: Optional[str] = "FORM_AB",
    ) -> Dict[str, Any]:
        ...

    def list_available_task_sets(self) -> List[str]:
        ...


class ExperimentConditionStrategy(Protocol):
    """
    Strategy protocol governing execution under a specific experimental condition.
    Implemented by concrete application-level condition strategies.
    """
    async def initialize(
        self,
        session_id: str,
        candidate_id: str,
        skill: str,
        task_set_id: str,
        config_dict: Dict[str, Any],
    ) -> Any:  # Returns ExperimentStepResult
        ...

    async def execute_step(
        self,
        candidate_answer: str,
        hints_requested: int = 0,
        response_time_seconds: float = 0.0,
    ) -> Any:  # Returns ExperimentStepResult
        ...

    def get_trials(self) -> List[Any]:  # Returns List[ExperimentTrialRaw]
        ...
