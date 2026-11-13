"""
Transfer-Aware Condition Adapter (Condition C).
Adapts the Phase 4 Coaching Orchestrator and Transfer Coaching Service into the ExperimentConditionStrategy protocol.
Does NOT duplicate diagnosis, intervention, scaffold fading, or retry logic.
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
from backend.domain.transfer.coaching_types import (
    CoachingLoopOutcome,
    ScaffoldLevel,
)
from ai.coaching_orchestrator.orchestrator import CoachingOrchestrator
from ai.coaching_orchestrator.schemas import (
    CoachingSessionConfig,
    TrainingContext,
    CandidateStepInput,
    OrchestratorStepResult,
)


def _extract_orch_feedback(orch_res: OrchestratorStepResult) -> str:
    if orch_res.evaluation and orch_res.evaluation.get("strengths"):
        return "; ".join(orch_res.evaluation.get("strengths", []))
    if orch_res.transition_reason:
        return orch_res.transition_reason
    return "Turn evaluated."


def _normalize_score(val: float) -> float:
    return round(val / 10.0, 4) if val > 1.0 else round(val, 4)


class TransferAwareConditionAdapter(ExperimentConditionStrategy):
    """
    Condition C Adapter: Coordinates the experimental lifecycle with the Phase 4 CoachingOrchestrator.
    Flow: PRETEST -> TRAINING -> POSTTEST -> NOVEL TRANSFER -> (if failure) TARGETED RETRAINING -> INDEPENDENT TRANSFER.
    """

    def __init__(
        self,
        evaluation_port: EvaluationPort,
        task_set_provider: TaskSetProvider,
        orchestrator: Optional[CoachingOrchestrator] = None,
    ):
        self.evaluation_port = evaluation_port
        self.task_set_provider = task_set_provider
        self.orchestrator = orchestrator or CoachingOrchestrator()

        self.session_id: str = ""
        self.candidate_id: str = ""
        self.skill: str = ""
        self.task_set_id: str = ""
        self.random_seed: int = 42
        self.retry_limit: int = 2

        self.current_phase: ExperimentPhase = ExperimentPhase.PRETEST
        self.current_task: Optional[Dict[str, Any]] = None
        self.trials: List[ExperimentTrialRaw] = []

        # Internal state tracking
        self._pretest_done: bool = False
        self._training_done: bool = False
        self._posttest_done: bool = False
        self._transfer_attempt_done: bool = False
        self._retraining_done: bool = False
        self._independent_done: bool = False

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
        self.retry_limit = self.config_dict.get("retry_limit", 2)
        self.trials = []

        self._pretest_done = False
        self._training_done = False
        self._posttest_done = False
        self._transfer_attempt_done = False
        self._retraining_done = False
        self._independent_done = False

        # Start with PRETEST task
        self.current_phase = ExperimentPhase.PRETEST
        form_order = self.config_dict.get("form_order", "FORM_AB")
        self.current_task = self.task_set_provider.get_task(
            task_set_id=self.task_set_id,
            phase=ExperimentPhase.PRETEST,
            difficulty=TaskDifficulty.MEDIUM,
            seed=self.random_seed,
            form_order=form_order,
        )

        return ExperimentStepResult(
            session_id=self.session_id,
            condition=ExperimentCondition.CONDITION_C,
            phase=self.current_phase,
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
        if self.current_phase == ExperimentPhase.COMPLETED or not self.current_task:
            raise ValueError("Experimental session is already completed.")

        # =========================================================================
        # 1. PRETEST Execution
        # =========================================================================
        if not self._pretest_done:
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
            score = _normalize_score(float(eval_dict.get("overall_score", 0.0)))
            trial = ExperimentTrialRaw(
                trial_id=str(uuid.uuid4()),
                session_id=self.session_id,
                task_id=self.current_task["task_id"],
                phase=ExperimentPhase.PRETEST,
                transfer_level=self.current_task.get("transfer_level"),
                transfer_distance=self.current_task.get("transfer_distance"),
                difficulty=self.current_task.get("difficulty"),
                score=score,
                outcome=ExperimentOutcome.PASS if score >= 0.70 else ExperimentOutcome.FAIL,
                response_time_seconds=response_time_seconds,
                candidate_answer_text=candidate_answer,
                feedback_text=eval_dict.get("strengths", ["Pretest evaluation."])[0],
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
            self._pretest_done = True

            # Prepare TRAINING turn via Orchestrator
            self.current_phase = ExperimentPhase.TRAINING
            training_task_def = self.task_set_provider.get_task(
                task_set_id=self.task_set_id,
                phase=ExperimentPhase.TRAINING,
                difficulty=TaskDifficulty.MEDIUM,
                seed=self.random_seed,
            )
            self.current_task = training_task_def

            training_context = TrainingContext(
                task_id=training_task_def["task_id"],
                skill_id=self.skill,
                question_text=training_task_def["prompt"],
                base_expected_concepts=training_task_def.get("expected_concepts", []),
                base_surface_context=training_task_def.get("topic", "Caching"),
                core_invariants=["hash slots", "consistent hashing", "cache eviction"],
            )
            session_config = CoachingSessionConfig(
                max_retries=self.retry_limit,
            )
            await self.orchestrator.initialize_session(
                candidate_id=self.candidate_id,
                session_id=self.session_id,
                training_context=training_context,
                config=session_config,
            )

            return ExperimentStepResult(
                session_id=self.session_id,
                condition=ExperimentCondition.CONDITION_C,
                phase=ExperimentPhase.PRETEST,
                task_id=trial.task_id,
                task_prompt=training_task_def["prompt"],
                task_difficulty=training_task_def.get("difficulty"),
                transfer_level=training_task_def.get("transfer_level"),
                score=score,
                feedback=trial.feedback_text,
                is_complete=False,
                raw_trial=trial,
            )

        # =========================================================================
        # 2. TRAINING Execution via Orchestrator
        # =========================================================================
        if not self._training_done:
            step_in = CandidateStepInput(
                candidate_answer=candidate_answer,
                hints_requested_count=hints_requested,
                response_time_seconds=response_time_seconds,
            )
            orch_res: OrchestratorStepResult = await self.orchestrator.submit_step(step_in)
            raw_s = float(orch_res.evaluation.get("overall_score", 0.0)) if orch_res.evaluation else 0.0
            score = _normalize_score(raw_s)

            fb = _extract_orch_feedback(orch_res)
            trial = ExperimentTrialRaw(
                trial_id=str(uuid.uuid4()),
                session_id=self.session_id,
                task_id=self.current_task["task_id"],
                phase=ExperimentPhase.TRAINING,
                transfer_level=self.current_task.get("transfer_level"),
                transfer_distance=self.current_task.get("transfer_distance"),
                difficulty=self.current_task.get("difficulty"),
                score=score,
                outcome=ExperimentOutcome.PASS if score >= 0.70 else ExperimentOutcome.FAIL,
                response_time_seconds=response_time_seconds,
                candidate_answer_text=candidate_answer,
                feedback_text=fb,
                hints_requested_count=hints_requested,
                evaluator_provider=orch_res.evaluation.get("evaluator_provider", "GROUNDED_NLP") if isinstance(orch_res.evaluation, dict) else "GROUNDED_NLP",
                evaluator_version="v1.0",
                rubric_version="technical_v1",
                evaluator_fallback=bool(orch_res.evaluation.get("evaluator_fallback", False)) if isinstance(orch_res.evaluation, dict) else False,
                fallback_reason=orch_res.evaluation.get("fallback_reason", None) if isinstance(orch_res.evaluation, dict) else None,
                form_id=self.current_task.get("form_id", "FORM_A"),
                execution_provenance=self.config_dict.get("execution_provenance", "SYNTHETIC"),
                timestamp=datetime.now(timezone.utc),
            )
            self.trials.append(trial)
            self._training_done = True

            # Prepare POSTTEST turn
            self.current_phase = ExperimentPhase.POSTTEST
            form_order = self.config_dict.get("form_order", "FORM_AB")
            posttest_def = self.task_set_provider.get_task(
                task_set_id=self.task_set_id,
                phase=ExperimentPhase.POSTTEST,
                difficulty=TaskDifficulty.MEDIUM,
                seed=self.random_seed,
                form_order=form_order,
            )
            self.current_task = posttest_def

            return ExperimentStepResult(
                session_id=self.session_id,
                condition=ExperimentCondition.CONDITION_C,
                phase=ExperimentPhase.TRAINING,
                task_id=trial.task_id,
                task_prompt=posttest_def["prompt"],
                task_difficulty=posttest_def.get("difficulty"),
                transfer_level=posttest_def.get("transfer_level"),
                score=score,
                feedback=fb,
                is_complete=False,
                raw_trial=trial,
            )

        # =========================================================================
        # 3. POSTTEST Execution
        # =========================================================================
        if not self._posttest_done:
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
            score = _normalize_score(float(eval_dict.get("overall_score", 0.0)))
            trial = ExperimentTrialRaw(
                trial_id=str(uuid.uuid4()),
                session_id=self.session_id,
                task_id=self.current_task["task_id"],
                phase=ExperimentPhase.POSTTEST,
                transfer_level=self.current_task.get("transfer_level"),
                transfer_distance=self.current_task.get("transfer_distance"),
                difficulty=self.current_task.get("difficulty"),
                score=score,
                outcome=ExperimentOutcome.PASS if score >= 0.70 else ExperimentOutcome.FAIL,
                response_time_seconds=response_time_seconds,
                candidate_answer_text=candidate_answer,
                feedback_text=eval_dict.get("strengths", ["Posttest evaluation."])[0],
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
            self._posttest_done = True

            # Prepare NOVEL TRANSFER turn
            # Prompt generated by Phase 4 orchestrator or transfer provider
            self.current_phase = ExperimentPhase.TRANSFER_TEST
            transfer_task_def = self.task_set_provider.get_task(
                task_set_id=self.task_set_id,
                phase=ExperimentPhase.TRANSFER_TEST,
                difficulty=TaskDifficulty.MEDIUM,
                seed=self.random_seed,
            )
            self.current_task = transfer_task_def

            prompt_text = (
                self.orchestrator.current_transfer_task.prompt_template
                if self.orchestrator.current_transfer_task and self.orchestrator.current_transfer_task.prompt_template
                else transfer_task_def["prompt"]
            )

            return ExperimentStepResult(
                session_id=self.session_id,
                condition=ExperimentCondition.CONDITION_C,
                phase=ExperimentPhase.POSTTEST,
                task_id=trial.task_id,
                task_prompt=prompt_text,
                task_difficulty=transfer_task_def.get("difficulty"),
                transfer_level=transfer_task_def.get("transfer_level"),
                score=score,
                feedback=trial.feedback_text,
                is_complete=False,
                raw_trial=trial,
            )

        # =========================================================================
        # 4. TRANSFER TEST Execution via Orchestrator
        # =========================================================================
        if not self._transfer_attempt_done:
            step_in = CandidateStepInput(
                candidate_answer=candidate_answer,
                hints_requested_count=hints_requested,
                response_time_seconds=response_time_seconds,
            )
            orch_res: OrchestratorStepResult = await self.orchestrator.submit_step(step_in)
            raw_s = float(orch_res.evaluation.get("overall_score", 0.0)) if orch_res.evaluation else 0.0
            score = _normalize_score(raw_s)

            evidence_dump = (
                [e.model_dump() for e in orch_res.diagnosis.evidence]
                if orch_res.diagnosis else None
            )

            fb = _extract_orch_feedback(orch_res)
            trial = ExperimentTrialRaw(
                trial_id=str(uuid.uuid4()),
                session_id=self.session_id,
                task_id=self.current_task["task_id"],
                phase=ExperimentPhase.TRANSFER_TEST,
                transfer_level=self.current_task.get("transfer_level"),
                transfer_distance=self.current_task.get("transfer_distance"),
                difficulty=self.current_task.get("difficulty"),
                score=score,
                outcome=ExperimentOutcome.PASS if score >= 0.70 else ExperimentOutcome.FAIL,
                response_time_seconds=response_time_seconds,
                candidate_answer_text=candidate_answer,
                feedback_text=fb,
                intervention_type=orch_res.intervention.intervention_type.value if orch_res.intervention else None,
                scaffold_level="INDEPENDENT",
                hints_requested_count=hints_requested,
                retry_count=orch_res.retry_count,
                evaluator_provider=orch_res.evaluation.get("evaluator_provider", "GROUNDED_NLP") if isinstance(orch_res.evaluation, dict) else "GROUNDED_NLP",
                evaluator_version="v1.0",
                rubric_version="technical_v1",
                evaluator_fallback=bool(orch_res.evaluation.get("evaluator_fallback", False)) if isinstance(orch_res.evaluation, dict) else False,
                fallback_reason=orch_res.evaluation.get("fallback_reason", None) if isinstance(orch_res.evaluation, dict) else None,
                form_id=self.current_task.get("form_id", "FORM_A"),
                execution_provenance=self.config_dict.get("execution_provenance", "SYNTHETIC"),
                diagnosis_type=orch_res.diagnosis.failure_type.value if orch_res.diagnosis else None,
                diagnosis_confidence=orch_res.diagnosis.confidence if orch_res.diagnosis else None,
                affected_skill=orch_res.diagnosis.affected_skill if orch_res.diagnosis else None,
                diagnostic_evidence=evidence_dump,
                timestamp=datetime.now(timezone.utc),
            )
            self.trials.append(trial)
            self._transfer_attempt_done = True

            # If transfer succeeded, skip retraining and proceed directly to INDEPENDENT_TRANSFER
            if score >= 0.70:
                self._retraining_done = True
                self.current_phase = ExperimentPhase.INDEPENDENT_TRANSFER
                indep_def = self.task_set_provider.get_task(
                    task_set_id=self.task_set_id,
                    phase=ExperimentPhase.INDEPENDENT_TRANSFER,
                    difficulty=TaskDifficulty.HARD,
                    seed=self.random_seed,
                )
                self.current_task = indep_def
                prompt_text = (
                    self.orchestrator.current_transfer_task.prompt_template
                    if self.orchestrator.current_transfer_task and self.orchestrator.current_transfer_task.prompt_template
                    else indep_def["prompt"]
                )
                return ExperimentStepResult(
                    session_id=self.session_id,
                    condition=ExperimentCondition.CONDITION_C,
                    phase=ExperimentPhase.TRANSFER_TEST,
                    task_id=trial.task_id,
                    task_prompt=prompt_text,
                    task_difficulty=indep_def.get("difficulty"),
                    transfer_level=indep_def.get("transfer_level"),
                    score=score,
                    feedback=fb,
                    is_complete=False,
                    raw_trial=trial,
                )

            # Transfer failed: advance to TARGETED_RETRAINING turn with delivered intervention
            self.current_phase = ExperimentPhase.TARGETED_RETRAINING
            retrain_def = self.task_set_provider.get_task(
                task_set_id=self.task_set_id,
                phase=ExperimentPhase.TARGETED_RETRAINING,
                difficulty=TaskDifficulty.MEDIUM,
                seed=self.random_seed,
            )
            self.current_task = retrain_def
            retrain_prompt = (
                f"{orch_res.intervention.content}\n\nTask: {retrain_def['prompt']}"
                if orch_res.intervention else retrain_def["prompt"]
            )

            return ExperimentStepResult(
                session_id=self.session_id,
                condition=ExperimentCondition.CONDITION_C,
                phase=ExperimentPhase.TRANSFER_TEST,
                task_id=trial.task_id,
                task_prompt=retrain_prompt,
                task_difficulty=retrain_def.get("difficulty"),
                transfer_level=retrain_def.get("transfer_level"),
                score=score,
                feedback=fb,
                intervention=orch_res.intervention.content if orch_res.intervention else None,
                scaffold_level=trial.scaffold_level,
                is_complete=False,
                raw_trial=trial,
            )

        # =========================================================================
        # 5. TARGETED RETRAINING (Retry under Scaffolding)
        # =========================================================================
        if not self._retraining_done:
            step_in = CandidateStepInput(
                candidate_answer=candidate_answer,
                hints_requested_count=hints_requested,
                response_time_seconds=response_time_seconds,
            )
            orch_res: OrchestratorStepResult = await self.orchestrator.submit_step(step_in)
            if orch_res.evaluation:
                raw_s = float(orch_res.evaluation.get("overall_score", 0.0))
                fb = _extract_orch_feedback(orch_res)
            elif self.orchestrator.attempts_history and self.orchestrator.attempts_history[-1].get("stage") == "RETRY":
                last_att = self.orchestrator.attempts_history[-1]
                raw_s = float(last_att.get("score", 0.0))
                last_eval = last_att.get("evaluation", {})
                fb = "; ".join(last_eval.get("strengths", [])) if last_eval.get("strengths") else orch_res.transition_reason or "Retry evaluated."
            else:
                raw_s = 0.0
                fb = _extract_orch_feedback(orch_res)
            score = _normalize_score(raw_s)

            trial = ExperimentTrialRaw(
                trial_id=str(uuid.uuid4()),
                session_id=self.session_id,
                task_id=self.current_task["task_id"],
                phase=ExperimentPhase.TARGETED_RETRAINING,
                transfer_level=self.current_task.get("transfer_level"),
                transfer_distance=self.current_task.get("transfer_distance"),
                difficulty=self.current_task.get("difficulty"),
                score=score,
                outcome=ExperimentOutcome.PASS if score >= 0.70 else ExperimentOutcome.FAIL,
                response_time_seconds=response_time_seconds,
                candidate_answer_text=candidate_answer,
                feedback_text=fb,
                intervention_type=self.orchestrator.last_intervention.intervention_type.value if self.orchestrator.last_intervention else (orch_res.intervention.intervention_type.value if orch_res.intervention else None),
                scaffold_level=(self.orchestrator.attempts_history[-1]["scaffold_level"] if (self.orchestrator.attempts_history and self.orchestrator.attempts_history[-1].get("scaffold_level")) else "LOW_ASSISTANCE"),
                hints_requested_count=hints_requested,
                retry_count=orch_res.retry_count,
                evaluator_provider=orch_res.evaluation.get("evaluator_provider", "GROUNDED_NLP") if isinstance(orch_res.evaluation, dict) else "GROUNDED_NLP",
                evaluator_version="v1.0",
                rubric_version="technical_v1",
                evaluator_fallback=bool(orch_res.evaluation.get("evaluator_fallback", False)) if isinstance(orch_res.evaluation, dict) else False,
                fallback_reason=orch_res.evaluation.get("fallback_reason", None) if isinstance(orch_res.evaluation, dict) else None,
                form_id=self.current_task.get("form_id", "FORM_A"),
                execution_provenance=self.config_dict.get("execution_provenance", "SYNTHETIC"),
                timestamp=datetime.now(timezone.utc),
            )
            self.trials.append(trial)
            self._retraining_done = True

            # Prepare INDEPENDENT_TRANSFER turn
            self.current_phase = ExperimentPhase.INDEPENDENT_TRANSFER
            indep_def = self.task_set_provider.get_task(
                task_set_id=self.task_set_id,
                phase=ExperimentPhase.INDEPENDENT_TRANSFER,
                difficulty=TaskDifficulty.HARD,
                seed=self.random_seed,
            )
            self.current_task = indep_def
            prompt_text = (
                self.orchestrator.current_transfer_task.prompt_template
                if self.orchestrator.current_transfer_task and self.orchestrator.current_transfer_task.prompt_template
                else indep_def["prompt"]
            )

            return ExperimentStepResult(
                session_id=self.session_id,
                condition=ExperimentCondition.CONDITION_C,
                phase=ExperimentPhase.TARGETED_RETRAINING,
                task_id=trial.task_id,
                task_prompt=prompt_text,
                task_difficulty=indep_def.get("difficulty"),
                transfer_level=indep_def.get("transfer_level"),
                score=score,
                feedback=fb,
                is_complete=False,
                raw_trial=trial,
            )

        # =========================================================================
        # 6. INDEPENDENT TRANSFER Execution
        # =========================================================================
        if not self._independent_done:
            step_in = CandidateStepInput(
                candidate_answer=candidate_answer,
                hints_requested_count=hints_requested,
                response_time_seconds=response_time_seconds,
            )
            orch_res: OrchestratorStepResult = await self.orchestrator.submit_step(step_in)
            raw_s = float(orch_res.evaluation.get("overall_score", 0.0)) if orch_res.evaluation else 0.0
            score = _normalize_score(raw_s)

            fb = _extract_orch_feedback(orch_res)
            trial = ExperimentTrialRaw(
                trial_id=str(uuid.uuid4()),
                session_id=self.session_id,
                task_id=self.current_task["task_id"],
                phase=ExperimentPhase.INDEPENDENT_TRANSFER,
                transfer_level=self.current_task.get("transfer_level"),
                transfer_distance=self.current_task.get("transfer_distance"),
                difficulty=self.current_task.get("difficulty"),
                score=score,
                outcome=ExperimentOutcome.PASS if score >= 0.70 else ExperimentOutcome.FAIL,
                response_time_seconds=response_time_seconds,
                candidate_answer_text=candidate_answer,
                feedback_text=fb,
                intervention_type=None,
                scaffold_level="INDEPENDENT",
                hints_requested_count=hints_requested,
                retry_count=orch_res.retry_count,
                evaluator_provider=orch_res.evaluation.get("evaluator_provider", "GROUNDED_NLP") if isinstance(orch_res.evaluation, dict) else "GROUNDED_NLP",
                evaluator_version="v1.0",
                rubric_version="technical_v1",
                evaluator_fallback=bool(orch_res.evaluation.get("evaluator_fallback", False)) if isinstance(orch_res.evaluation, dict) else False,
                fallback_reason=orch_res.evaluation.get("fallback_reason", None) if isinstance(orch_res.evaluation, dict) else None,
                form_id=self.current_task.get("form_id", "FORM_A"),
                execution_provenance=self.config_dict.get("execution_provenance", "SYNTHETIC"),
                timestamp=datetime.now(timezone.utc),
            )
            self.trials.append(trial)
            self._independent_done = True
            self.current_phase = ExperimentPhase.COMPLETED
            self.current_task = None

            return ExperimentStepResult(
                session_id=self.session_id,
                condition=ExperimentCondition.CONDITION_C,
                phase=ExperimentPhase.INDEPENDENT_TRANSFER,
                task_id=trial.task_id,
                task_prompt="All experimental tasks for Condition C completed.",
                task_difficulty=None,
                transfer_level=None,
                score=score,
                feedback=fb,
                intervention=None,
                scaffold_level="INDEPENDENT",
                is_complete=True,
                raw_trial=trial,
            )

        raise ValueError("Experiment session is in invalid state.")

    def get_trials(self) -> List[ExperimentTrialRaw]:
        return list(self.trials)
