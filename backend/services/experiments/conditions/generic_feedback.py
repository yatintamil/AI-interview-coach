"""
Generic Feedback Condition Strategy (Condition A).
Represents the unguided baseline: evaluation with standard explanatory feedback.
Strictly isolated: ZERO imports or invocations of diagnosis, scaffolding, or transfer engines.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from backend.domain.experiments.enums import (
    ExperimentCondition,
    ExperimentPhase,
    ExperimentOutcome,
    TaskDifficulty,
)
from backend.domain.experiments.ports import (
    ExperimentConditionStrategy,
    EvaluationPort,
    TaskSetProvider,
)
from backend.domain.experiments.schemas import (
    ExperimentTrialRaw,
    ExperimentStepResult,
)


class GenericFeedbackCondition(ExperimentConditionStrategy):
    """
    Condition A: Evaluates answers using the constant EvaluationPort and returns generic feedback.
    Advances linearly through PRETEST -> TRAINING -> POSTTEST -> TRANSFER_TEST -> COMPLETED.
    """

    PHASE_SEQUENCE = [
        ExperimentPhase.PRETEST,
        ExperimentPhase.TRAINING,
        ExperimentPhase.POSTTEST,
        ExperimentPhase.TRANSFER_TEST,
        ExperimentPhase.INDEPENDENT_TRANSFER,
    ]

    def __init__(
        self,
        evaluation_port: EvaluationPort,
        task_set_provider: TaskSetProvider,
    ):
        self.evaluation_port = evaluation_port
        self.task_set_provider = task_set_provider

        self.session_id: str = ""
        self.candidate_id: str = ""
        self.skill: str = ""
        self.task_set_id: str = ""
        self.random_seed: int = 42

        self.current_phase_index: int = 0
        self.current_task: Optional[Dict[str, Any]] = None
        self.trials: List[ExperimentTrialRaw] = []

    async def initialize(
        self,
        session_id: str,
        candidate_id: str,
        skill: str,
        task_set_id: str,
        config_dict: Dict[str, Any],
    ) -> ExperimentStepResult:
        self.session_id = session_id
        self.candidate_id = candidate_id
        self.skill = skill
        self.task_set_id = task_set_id
        self.config_dict = config_dict or {}
        self.execution_provenance = self.config_dict.get("execution_provenance", "SYNTHETIC")
        self.random_seed = self.config_dict.get("random_seed", 42)
        self.current_phase_index = 0
        self.trials = []

        initial_phase = self.PHASE_SEQUENCE[0]
        form_order = self.config_dict.get("form_order", "FORM_AB")
        self.current_task = self.task_set_provider.get_task(
            task_set_id=self.task_set_id,
            phase=initial_phase,
            difficulty=TaskDifficulty.MEDIUM,
            seed=self.random_seed,
            form_order=form_order,
        )

        return ExperimentStepResult(
            session_id=self.session_id,
            condition=ExperimentCondition.CONDITION_A,
            phase=initial_phase,
            task_id=self.current_task["task_id"],
            task_prompt=self.current_task["prompt"],
            task_difficulty=self.current_task.get("difficulty"),
            transfer_level=self.current_task.get("transfer_level"),
            score=None,
            feedback=None,
            intervention=None,
            scaffold_level=None,
            is_complete=False,
            raw_trial=None,
        )

    async def execute_step(
        self,
        candidate_answer: str,
        hints_requested: int = 0,
        response_time_seconds: float = 0.0,
    ) -> ExperimentStepResult:
        if not self.current_task or self.current_phase_index >= len(self.PHASE_SEQUENCE):
            raise ValueError("Experimental session is already completed.")

        current_phase = self.PHASE_SEQUENCE[self.current_phase_index]

        # 1. Constant evaluation via EvaluationPort
        eval_dict = await self.evaluation_port.evaluate_answer(
            target_role="Senior Distributed Systems Engineer",
            interview_type="TECHNICAL",
            topic=self.current_task.get("topic", "Distributed Systems"),
            question_text=self.current_task["prompt"],
            expected_concepts=self.current_task.get("expected_concepts", []),
            resume_evidence="Candidate engineering background.",
            candidate_answer=candidate_answer,
            response_time_seconds=response_time_seconds,
        )

        raw_score = float(eval_dict.get("overall_score", 0.0))
        overall_score = round(raw_score / 10.0, 4) if raw_score > 1.0 else round(raw_score, 4)
        outcome = ExperimentOutcome.PASS if overall_score >= 0.70 else ExperimentOutcome.FAIL

        # 2. Generic explanatory feedback (strengths, weaknesses, recommendations)
        strengths = eval_dict.get("strengths", [])
        weaknesses = eval_dict.get("weaknesses", [])
        recommendations = eval_dict.get("recommendations", [])

        feedback_parts = []
        if strengths:
            feedback_parts.append(f"Strengths: {'; '.join(strengths)}")
        if weaknesses:
            feedback_parts.append(f"Areas for Improvement: {'; '.join(weaknesses)}")
        if recommendations:
            feedback_parts.append(f"Recommendations: {'; '.join(recommendations)}")
        generic_feedback = " | ".join(feedback_parts) if feedback_parts else "Evaluation complete."

        scaffold_lvl = "INDEPENDENT" if current_phase == ExperimentPhase.INDEPENDENT_TRANSFER else None
        hints_count = 0 if current_phase == ExperimentPhase.INDEPENDENT_TRANSFER else hints_requested

        # 3. Persist raw trial observation (all diagnostic fields null)
        trial = ExperimentTrialRaw(
            trial_id=str(uuid.uuid4()),
            session_id=self.session_id,
            task_id=self.current_task["task_id"],
            phase=current_phase,
            transfer_level=self.current_task.get("transfer_level"),
            transfer_distance=self.current_task.get("transfer_distance"),
            difficulty=self.current_task.get("difficulty"),
            attempt_number=1,
            score=overall_score,
            outcome=outcome,
            response_time_seconds=response_time_seconds,
            candidate_answer_text=candidate_answer,
            feedback_text=generic_feedback,
            intervention_type=None,
            scaffold_level=scaffold_lvl,
            hints_requested_count=hints_count,
            retry_count=0,
            diagnosis_type=None,
            diagnosis_confidence=None,
            affected_skill=None,
            diagnostic_evidence=None,
            evaluator_provider=eval_dict.get("evaluator_provider", "GROUNDED_NLP"),
            evaluator_version="v1.0",
            rubric_version="technical_v1",
            evaluator_fallback=bool(eval_dict.get("evaluator_fallback", False)),
            fallback_reason=eval_dict.get("fallback_reason", None),
            form_id=self.current_task.get("form_id", "FORM_A"),
            execution_provenance=self.config_dict.get("execution_provenance", "SYNTHETIC"),
            timestamp=datetime.now(timezone.utc),
        )
        self.trials.append(trial)

        # 4. Advance phase sequence
        self.current_phase_index += 1
        is_complete = self.current_phase_index >= len(self.PHASE_SEQUENCE)

        if not is_complete:
            next_phase = self.PHASE_SEQUENCE[self.current_phase_index]
            task_diff = TaskDifficulty.HARD if next_phase == ExperimentPhase.INDEPENDENT_TRANSFER else TaskDifficulty.MEDIUM
            form_order = self.config_dict.get("form_order", "FORM_AB")
            self.current_task = self.task_set_provider.get_task(
                task_set_id=self.task_set_id,
                phase=next_phase,
                difficulty=task_diff,
                seed=self.random_seed + self.current_phase_index,
                form_order=form_order,
            )
            next_task_id = self.current_task["task_id"]
            next_prompt = self.current_task["prompt"]
            next_diff = self.current_task.get("difficulty")
            next_transfer_lvl = self.current_task.get("transfer_level")
        else:
            self.current_task = None
            next_phase = ExperimentPhase.COMPLETED
            next_task_id = "COMPLETED"
            next_prompt = "All experimental tasks for Condition A completed."
            next_diff = None
            next_transfer_lvl = None

        return ExperimentStepResult(
            session_id=self.session_id,
            condition=ExperimentCondition.CONDITION_A,
            phase=current_phase,
            task_id=trial.task_id,
            task_prompt=next_prompt,
            task_difficulty=next_diff,
            transfer_level=next_transfer_lvl,
            score=overall_score,
            feedback=generic_feedback,
            intervention=None,
            scaffold_level=None,
            is_complete=is_complete,
            raw_trial=trial,
        )

    def get_trials(self) -> List[ExperimentTrialRaw]:
        return list(self.trials)
