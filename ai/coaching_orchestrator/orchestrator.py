"""
Transfer-Aware Coaching Orchestrator.
Coordinates the end-to-end coaching lifecycle:
Training -> Evaluation -> Transfer Generation -> Transfer Attempt -> Evaluation ->
Diagnosis -> Coaching Policy -> Intervention -> Retry -> Scaffold Fading -> Independent Transfer -> Final Outcome.
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

from backend.domain.transfer.taxonomy import TransferLevel, is_higher_transfer_level
from backend.domain.transfer.diagnosis_types import TransferFailureType
from backend.domain.transfer.coaching_types import (
    CoachingInterventionType,
    ScaffoldLevel,
    CoachingLoopOutcome,
)
from backend.domain.transfer.schemas import (
    TransferTaskDefinitionDTO,
    TransferFailureDiagnosisDTO,
    CoachingInterventionDecisionDTO,
    CandidateSkillStateDTO,
)
from ai.transfer_engine.schemas import TransferGenerationRequest
from ai.transfer_engine.interfaces import ITransferTaskGenerator
from ai.transfer_engine.task_generator import TransferTaskGenerator
from ai.diagnosis_engine.schemas import DiagnosisRequest
from ai.diagnosis_engine.interfaces import ITransferDiagnosisEngine
from ai.diagnosis_engine.diagnosis_engine import TransferDiagnosisEngine
from ai.coaching_engine.schemas import (
    CoachingPolicyInput,
    CoachingHistoryEntry,
    ScaffoldState,
    CoachingPolicyDecision,
)
from ai.coaching_engine.interfaces import ICoachingPolicy
from ai.coaching_engine.policy import CoachingPolicy
from ai.evaluation_engine.evaluator import AIEvaluator

from ai.coaching_orchestrator.state_machine import (
    CoachingState,
    CoachingStateMachine,
    StateTransitionRecord,
)
from ai.coaching_orchestrator.schemas import (
    CoachingSessionConfig,
    TrainingContext,
    CandidateStepInput,
    OrchestratorStepResult,
    ResearchTelemetryRecord,
)
from ai.coaching_orchestrator.interfaces import ICoachingOrchestrator
from ai.coaching_orchestrator.validators import CoachingOrchestrationValidator

logger = logging.getLogger(__name__)


class CoachingOrchestrator(ICoachingOrchestrator):
    """
    Orchestrator for the Transfer-Aware Coaching Loop.
    Maintains clean architecture: depends only on engine interfaces/protocols,
    delegates business logic to specialized engines, and emits structured telemetry.
    """

    def __init__(
        self,
        task_generator: Optional[ITransferTaskGenerator] = None,
        diagnosis_engine: Optional[ITransferDiagnosisEngine] = None,
        coaching_policy: Optional[ICoachingPolicy] = None,
        evaluator: Optional[AIEvaluator] = None,
        config: Optional[CoachingSessionConfig] = None,
        validator: Optional[CoachingOrchestrationValidator] = None,
    ):
        self.task_generator = task_generator or TransferTaskGenerator()
        self.diagnosis_engine = diagnosis_engine or TransferDiagnosisEngine()
        self.coaching_policy = coaching_policy or CoachingPolicy()
        self.evaluator = evaluator or AIEvaluator()
        self.config = config or CoachingSessionConfig()
        self.validator = validator or CoachingOrchestrationValidator()

        # Lifecycle State
        self.state_machine = CoachingStateMachine(initial_state=CoachingState.TRAINING)
        self.candidate_id: str = ""
        self.session_id: str = ""
        self.training_context: Optional[TrainingContext] = None

        # Active tasks & Turn tracking
        self.current_transfer_task: Optional[TransferTaskDefinitionDTO] = None
        self.independent_transfer_task: Optional[TransferTaskDefinitionDTO] = None
        self.current_scaffold_level: ScaffoldLevel = ScaffoldLevel.LOW_ASSISTANCE
        self.retry_count: int = 0
        self.last_diagnosis: Optional[TransferFailureDiagnosisDTO] = None
        self.last_intervention: Optional[CoachingInterventionDecisionDTO] = None

        # Longitudinal Candidate Skill State (engineering representation)
        self.candidate_skill_state: Optional[CandidateSkillStateDTO] = None

        # Research Telemetry
        self.coaching_history: List[CoachingHistoryEntry] = []
        self.attempts_history: List[Dict[str, Any]] = []

    async def initialize_session(
        self,
        candidate_id: str,
        session_id: str,
        training_context: TrainingContext,
        config: Optional[CoachingSessionConfig] = None,
    ) -> OrchestratorStepResult:
        """
        Initializes the candidate coaching session anchored by the baseline training task.
        """
        if config:
            cfg_errors = self.validator.validate_session_config(config)
            if cfg_errors:
                raise ValueError(f"Invalid coaching configuration: {'; '.join(cfg_errors)}")
            self.config = config

        ctx_errors = self.validator.validate_training_context(training_context)
        if ctx_errors:
            raise ValueError(f"Invalid training context: {'; '.join(ctx_errors)}")

        self.candidate_id = candidate_id
        self.session_id = session_id
        self.training_context = training_context
        self.state_machine = CoachingStateMachine(initial_state=CoachingState.TRAINING)
        self.retry_count = 0
        self.coaching_history = []
        self.attempts_history = []
        self.current_scaffold_level = ScaffoldLevel.LOW_ASSISTANCE

        # Initialize Candidate Skill State (engineering model baseline)
        init_m = training_context.current_mastery if training_context.current_mastery is not None else 0.40
        self.candidate_skill_state = CandidateSkillStateDTO(
            candidate_id=candidate_id,
            skill_name=training_context.skill_id,
            mastery_estimate=init_m,
            mastery_uncertainty=0.90,
            highest_transfer_level=TransferLevel.L0_RECALL,
            assistance_dependency_index=0.0,
            recurring_failure_types=[],
            total_attempts=0,
            last_assessed_at=datetime.now(timezone.utc),
        )

        # Construct Initial Teaching Task under HIGH_ASSISTANCE
        task_prompt = self.training_context.teaching_lesson or self.training_context.question_text
        initial_task = TransferTaskDefinitionDTO(
            id=f"teach_{self.training_context.task_id}",
            skill_id=self.training_context.skill_id,
            transfer_level=TransferLevel.L1_DIRECT_APPLICATION,
            prompt_template=task_prompt,
            surface_context=self.training_context.base_surface_context,
            core_invariants=self.training_context.core_invariants,
            expected_concepts=self.training_context.base_expected_concepts,
            surface_distractors=[],
        )
        self.current_transfer_task = initial_task
        self.current_scaffold_level = ScaffoldLevel.HIGH_ASSISTANCE

        return OrchestratorStepResult(
            state=CoachingState.TRAINING,
            outcome=CoachingLoopOutcome.TRAINING_SUCCESS,
            task=initial_task,
            training_context=self.training_context,
            session_id=self.session_id,
            candidate_id=self.candidate_id,
            scaffold_state=ScaffoldState(
                current_level=ScaffoldLevel.HIGH_ASSISTANCE,
                previous_level=ScaffoldLevel.HIGH_ASSISTANCE,
                is_faded=False,
                assistance_dependency_index=0.0,
                transition_reason="Initialized pedagogical coaching loop with HIGH assistance.",
            ),
            retry_count=0,
            candidate_state=self.candidate_skill_state,
            transition_reason="Session initialized with training task.",
        )

    async def submit_step(self, step_input: CandidateStepInput) -> OrchestratorStepResult:
        """
        Primary progression entrypoint: receives candidate answer for the current turn,
        dispatches evaluation and engine coordination, and advances the state machine.
        """
        if self.state_machine.current_state in (CoachingState.COMPLETED, CoachingState.FAILED):
            raise ValueError(f"Cannot submit step in terminal state: {self.state_machine.current_state.value}")

        curr = self.state_machine.current_state

        if curr in (CoachingState.TRAINING, CoachingState.UNDERSTANDING_CHECK):
            return await self._handle_training_step(
                step_input, is_understanding_check=(curr == CoachingState.UNDERSTANDING_CHECK)
            )
        elif curr in (CoachingState.TRANSFER_ATTEMPT, CoachingState.TRANSFER_RETEST):
            return await self._handle_transfer_step(step_input)
        elif curr == CoachingState.RETRY:
            return await self._handle_retry_step(step_input)
        elif curr == CoachingState.INDEPENDENT_TRANSFER:
            return await self._handle_independent_step(step_input)
        else:
            raise ValueError(f"Unsupported submission in state: {curr.value}")

    async def _handle_training_step(
        self, step_input: CandidateStepInput, is_understanding_check: bool = False
    ) -> OrchestratorStepResult:
        """Evaluates training response and checks conceptual understanding before advancing to transfer."""
        self.state_machine.transition_to(
            CoachingState.TRAINING_EVALUATION,
            reason="Candidate submitted training response."
        )

        # 1 & 2. Concurrently evaluate training answer and synthesize invariant-preserving transfer task
        gen_request = TransferGenerationRequest(
            skill_id=self.training_context.skill_id,
            transfer_level=self.config.transfer_level,
            core_invariants=self.training_context.core_invariants,
            base_surface_context=self.training_context.base_surface_context,
            base_expected_concepts=self.training_context.base_expected_concepts,
            parent_task_id=self.training_context.task_id,
            parent_prompt=self.training_context.question_text,
        )

        eval_result, transfer_dto = await asyncio.gather(
            self.evaluator.evaluate_answer(
                target_role="Software Engineer",
                interview_type="TECHNICAL",
                topic=self.training_context.topic or self.training_context.skill_id,
                question_text=self.training_context.question_text,
                expected_concepts=self.training_context.base_expected_concepts,
                resume_evidence="",
                candidate_answer=step_input.candidate_answer,
                response_time_seconds=step_input.response_time_seconds,
            ),
            self.task_generator.generate_transfer_task(gen_request),
        )

        score = float(eval_result.get("overall_score", 0.0))
        understanding_threshold = min(self.config.pass_threshold, 5.0)
        passed = score >= understanding_threshold

        if is_understanding_check and not passed:
            self.retry_count += 1
            # Update Engineering Mastery Estimate for failure
            self._update_skill_state_metrics(
                score=score,
                transfer_level=TransferLevel.L1_DIRECT_APPLICATION,
                failure_type=TransferFailureType.MISSING_CONCEPTUAL_MODEL,
            )

            # Record attempt telemetry
            self.attempts_history.append({
                "stage": "TRAINING",
                "score": score,
                "evaluation": eval_result,
                "response_time_seconds": step_input.response_time_seconds,
                "hints_requested": step_input.hints_requested_count,
                "scaffold_level": self.current_scaffold_level.value,
            })

            # Run diagnosis engine
            diag_req = DiagnosisRequest(
                task=self.current_transfer_task,
                candidate_answer=step_input.candidate_answer,
                evaluation=eval_result,
                attempt_metadata={
                    "hints_requested_count": step_input.hints_requested_count,
                    "scaffold_level_applied": self.current_scaffold_level.value,
                    "response_time_seconds": step_input.response_time_seconds,
                    "attempt_number": self.retry_count,
                },
                parent_task_context={
                    "surface_context": self.training_context.base_surface_context,
                    "prompt": self.training_context.question_text,
                    "core_invariants": self.training_context.core_invariants,
                },
                candidate_history=self._build_candidate_history_dict(),
            )
            diagnosis = await self.diagnosis_engine.diagnose(diag_req)
            self.last_diagnosis = diagnosis

            # Coaching policy intervention
            policy_input = CoachingPolicyInput(
                diagnosis=diagnosis,
                candidate_state=self.candidate_skill_state,
                current_scaffold_level=self.current_scaffold_level,
                history=self.coaching_history,
                transfer_level=self.current_transfer_task.transfer_level if self.current_transfer_task else TransferLevel.L1_DIRECT_APPLICATION,
                retry_count=self.retry_count,
                last_outcome="FAILURE",
            )
            policy_decision: CoachingPolicyDecision = self.coaching_policy.decide(policy_input)
            self.last_intervention = policy_decision.decision
            self.current_scaffold_level = policy_decision.scaffold_state.current_level

            self.coaching_history.append(CoachingHistoryEntry(
                intervention_type=policy_decision.decision.intervention_type,
                scaffold_level=policy_decision.scaffold_state.current_level,
                failure_type=diagnosis.failure_type,
                outcome="IN_PROGRESS",
                hints_requested=step_input.hints_requested_count,
                score=score,
                timestamp=datetime.now(timezone.utc),
            ))

            self.state_machine.transition_to(
                CoachingState.UNDERSTANDING_CHECK,
                reason="Understanding check not yet satisfied. Providing targeted guidance."
            )

            return OrchestratorStepResult(
                state=CoachingState.UNDERSTANDING_CHECK,
                outcome=CoachingLoopOutcome.TRANSFER_FAILURE,
                task=self.current_transfer_task,
                training_context=self.training_context,
                session_id=self.session_id,
                candidate_id=self.candidate_id,
                evaluation=eval_result,
                diagnosis=self.last_diagnosis,
                intervention=self.last_intervention,
                scaffold_state=policy_decision.scaffold_state,
                retry_count=self.retry_count,
                retry_limit_reached=self.retry_count >= self.config.max_retries,
                candidate_state=self.candidate_skill_state,
                transition_reason="Understanding check needs reinforcement. Review guidance and retry.",
            )

        self.current_transfer_task = transfer_dto

        # Update Engineering Mastery Estimate
        self._update_skill_state_metrics(score=score, transfer_level=TransferLevel.L1_DIRECT_APPLICATION, failure_type=None)

        # Record attempt telemetry
        self.attempts_history.append({
            "stage": "TRAINING",
            "score": score,
            "evaluation": eval_result,
            "response_time_seconds": step_input.response_time_seconds,
            "hints_requested": step_input.hints_requested_count,
            "scaffold_level": ScaffoldLevel.LOW_ASSISTANCE.value,
        })

        # Transition directly through generation to TRANSFER_ATTEMPT
        self.state_machine.transition_to(
            CoachingState.TRANSFER_GENERATION,
            reason="Training complete. Synthesizing invariant-preserving transfer task."
        )
        self.state_machine.transition_to(
            CoachingState.TRANSFER_ATTEMPT,
            reason=f"Generated {transfer_dto.transfer_level.value} task '{transfer_dto.id}'."
        )
        self.current_scaffold_level = ScaffoldLevel.LOW_ASSISTANCE

        return OrchestratorStepResult(
            state=CoachingState.TRANSFER_ATTEMPT,
            outcome=CoachingLoopOutcome.TRAINING_SUCCESS,
            task=self.current_transfer_task,
            training_context=self.training_context,
            session_id=self.session_id,
            candidate_id=self.candidate_id,
            evaluation=eval_result,
            candidate_state=self.candidate_skill_state,
            transition_reason="Training passed. Advanced to transfer challenge.",
        )

    async def _handle_transfer_step(self, step_input: CandidateStepInput) -> OrchestratorStepResult:
        """Evaluates transfer attempt; if failed, diagnoses cause and triggers coaching policy."""
        self.state_machine.transition_to(
            CoachingState.TRANSFER_EVALUATION,
            reason="Candidate submitted transfer response."
        )

        # 1. Evaluate Transfer Answer
        eval_result = await self.evaluator.evaluate_answer(
            target_role="Software Engineer",
            interview_type="TECHNICAL",
            topic=self.current_transfer_task.surface_context,
            question_text=self.current_transfer_task.prompt_template or self.current_transfer_task.surface_context,
            expected_concepts=self.current_transfer_task.expected_concepts,
            resume_evidence="",
            candidate_answer=step_input.candidate_answer,
            response_time_seconds=step_input.response_time_seconds,
        )
        score = float(eval_result.get("overall_score", 0.0))

        # Record attempt telemetry
        self.attempts_history.append({
            "stage": "TRANSFER_ATTEMPT",
            "task_id": self.current_transfer_task.id,
            "transfer_level": self.current_transfer_task.transfer_level.value,
            "score": score,
            "evaluation": eval_result,
            "hints_requested": step_input.hints_requested_count,
            "scaffold_level": self.current_scaffold_level.value,
        })

        # 2. Diagnose Performance via Diagnosis Engine
        self.state_machine.transition_to(
            CoachingState.TRANSFER_DIAGNOSIS,
            reason="Dispatching diagnosis request to root-cause diagnosis engine."
        )

        diag_req = DiagnosisRequest(
            task=self.current_transfer_task,
            candidate_answer=step_input.candidate_answer,
            evaluation=eval_result,
            attempt_metadata={
                "hints_requested_count": step_input.hints_requested_count,
                "scaffold_level_applied": self.current_scaffold_level.value,
                "response_time_seconds": step_input.response_time_seconds,
                "attempt_number": 1,
            },
            parent_task_context={
                "surface_context": self.training_context.base_surface_context,
                "prompt": self.training_context.question_text,
                "core_invariants": self.training_context.core_invariants,
            },
            candidate_history=self._build_candidate_history_dict(),
        )
        diagnosis = await self.diagnosis_engine.diagnose(diag_req)
        self.last_diagnosis = diagnosis

        # 3. Check for Successful Transfer (Direct Transfer Success)
        if diagnosis.failure_type == TransferFailureType.NONE and score >= self.config.pass_threshold:
            self._update_skill_state_metrics(
                score=score,
                transfer_level=self.current_transfer_task.transfer_level,
                failure_type=None,
            )
            # Advance directly to unassisted Independent Transfer
            return await self._advance_to_independent_transfer(
                trigger_reason="Transfer passed autonomously without failure."
            )

        # 4. Transfer Failure Path -> Coaching Policy
        self._update_skill_state_metrics(
            score=score,
            transfer_level=self.current_transfer_task.transfer_level,
            failure_type=diagnosis.failure_type,
        )

        self.state_machine.transition_to(
            CoachingState.COACHING_DECISION,
            reason=f"Diagnosed transfer failure: {diagnosis.failure_type.value}."
        )

        policy_input = CoachingPolicyInput(
            diagnosis=diagnosis,
            candidate_state=self.candidate_skill_state,
            current_scaffold_level=self.current_scaffold_level,
            history=self.coaching_history,
            transfer_level=self.current_transfer_task.transfer_level,
            retry_count=self.retry_count,
            last_outcome="FAILURE",
        )
        policy_decision: CoachingPolicyDecision = self.coaching_policy.decide(policy_input)
        self.last_intervention = policy_decision.decision
        self.current_scaffold_level = policy_decision.scaffold_state.current_level

        # Record coaching event in telemetry
        coaching_entry = CoachingHistoryEntry(
            intervention_type=policy_decision.decision.intervention_type,
            scaffold_level=policy_decision.scaffold_state.current_level,
            failure_type=diagnosis.failure_type,
            outcome="IN_PROGRESS",
            hints_requested=step_input.hints_requested_count,
            score=score,
            timestamp=datetime.now(timezone.utc),
        )
        self.coaching_history.append(coaching_entry)

        # 5. Transition to INTERVENTION -> RETRY
        self.state_machine.transition_to(
            CoachingState.INTERVENTION,
            reason=f"Administering {policy_decision.decision.intervention_type.value} intervention."
        )
        self.state_machine.transition_to(
            CoachingState.RETRY,
            reason="Candidate requested to re-attempt task under targeted coaching guidance."
        )

        return OrchestratorStepResult(
            state=CoachingState.RETRY,
            outcome=CoachingLoopOutcome.TRANSFER_FAILURE,
            task=self.current_transfer_task,
            evaluation=eval_result,
            diagnosis=diagnosis,
            intervention=policy_decision.decision,
            scaffold_state=policy_decision.scaffold_state,
            retry_count=self.retry_count,
            retry_limit_reached=False,
            candidate_state=self.candidate_skill_state,
            transition_reason=f"Transfer failure diagnosed as {diagnosis.failure_type.value}. Coaching initiated.",
        )

    async def _handle_retry_step(self, step_input: CandidateStepInput) -> OrchestratorStepResult:
        """Evaluates retry answer. On success, fades scaffold; on failure, re-diagnoses or halts at retry limit."""
        self.state_machine.transition_to(
            CoachingState.RETRY_EVALUATION,
            reason="Candidate submitted retry response."
        )

        # 1. Evaluate Retry Answer
        eval_result = await self.evaluator.evaluate_answer(
            target_role="Software Engineer",
            interview_type="TECHNICAL",
            topic=self.current_transfer_task.surface_context,
            question_text=self.current_transfer_task.prompt_template or self.current_transfer_task.surface_context,
            expected_concepts=self.current_transfer_task.expected_concepts,
            resume_evidence="",
            candidate_answer=step_input.candidate_answer,
            response_time_seconds=step_input.response_time_seconds,
        )
        score = float(eval_result.get("overall_score", 0.0))

        # Record attempt
        self.attempts_history.append({
            "stage": "RETRY",
            "task_id": self.current_transfer_task.id,
            "retry_number": self.retry_count + 1,
            "score": score,
            "evaluation": eval_result,
            "hints_requested": step_input.hints_requested_count,
            "scaffold_level": self.current_scaffold_level.value,
        })

        is_success = score >= self.config.pass_threshold

        # 2. Retry Success Path -> Fade Scaffold -> Progress to Independent Transfer
        if is_success:
            if self.coaching_history:
                self.coaching_history[-1].outcome = "SUCCESS"
                self.coaching_history[-1].score = score

            # Apply Phase 3A Scaffold Fading
            faded_state: ScaffoldState = self.coaching_policy.scaffold_manager.compute_scaffold_transition(
                current_level=self.current_scaffold_level,
                last_outcome="SUCCESS",
                history=self.coaching_history,
            )
            self.current_scaffold_level = faded_state.current_level

            self._update_skill_state_metrics(
                score=score,
                transfer_level=self.current_transfer_task.transfer_level,
                failure_type=None,
            )

            # Advance to Independent Transfer challenge
            return await self._advance_to_independent_transfer(
                trigger_reason=f"Retry success (score={score}). Scaffold faded to {faded_state.current_level.value}."
            )

        # 3. Retry Failure Path
        if self.coaching_history:
            self.coaching_history[-1].outcome = "FAILURE"
            self.coaching_history[-1].score = score

        self.retry_count += 1
        self._update_skill_state_metrics(
            score=score,
            transfer_level=self.current_transfer_task.transfer_level,
            failure_type=self.last_diagnosis.failure_type if self.last_diagnosis else None,
        )

        # 3a. Check Retry Exhaustion
        if self.retry_count >= self.config.max_retries:
            logger.info(f"Max retries ({self.config.max_retries}) reached for candidate {self.candidate_id}.")
            # Halt coaching loop and proceed toward unassisted independent evaluation
            res = await self._advance_to_independent_transfer(
                trigger_reason=f"Retry limit reached ({self.retry_count}/{self.config.max_retries}). Halting coaching loop."
            )
            res.outcome = CoachingLoopOutcome.RETRY_LIMIT_REACHED
            res.retry_limit_reached = True
            return res

        # 3b. Re-diagnose and escalate intervention
        self.state_machine.transition_to(
            CoachingState.TRANSFER_DIAGNOSIS,
            reason=f"Retry failed (attempt {self.retry_count}/{self.config.max_retries}). Re-diagnosing."
        )

        diag_req = DiagnosisRequest(
            task=self.current_transfer_task,
            candidate_answer=step_input.candidate_answer,
            evaluation=eval_result,
            attempt_metadata={
                "hints_requested_count": step_input.hints_requested_count,
                "scaffold_level_applied": self.current_scaffold_level.value,
                "response_time_seconds": step_input.response_time_seconds,
                "attempt_number": self.retry_count + 1,
            },
            parent_task_context={
                "surface_context": self.training_context.base_surface_context,
                "prompt": self.training_context.question_text,
                "core_invariants": self.training_context.core_invariants,
            },
            candidate_history=self._build_candidate_history_dict(),
        )
        diagnosis = await self.diagnosis_engine.diagnose(diag_req)
        self.last_diagnosis = diagnosis

        self.state_machine.transition_to(
            CoachingState.COACHING_DECISION,
            reason=f"Re-diagnosis: {diagnosis.failure_type.value}. Computing escalated intervention."
        )

        policy_input = CoachingPolicyInput(
            diagnosis=diagnosis,
            candidate_state=self.candidate_skill_state,
            current_scaffold_level=self.current_scaffold_level,
            history=self.coaching_history,
            transfer_level=self.current_transfer_task.transfer_level,
            retry_count=self.retry_count,
            last_outcome="FAILURE",
        )
        policy_decision = self.coaching_policy.decide(policy_input)
        self.last_intervention = policy_decision.decision
        self.current_scaffold_level = policy_decision.scaffold_state.current_level

        coaching_entry = CoachingHistoryEntry(
            intervention_type=policy_decision.decision.intervention_type,
            scaffold_level=policy_decision.scaffold_state.current_level,
            failure_type=diagnosis.failure_type,
            outcome="IN_PROGRESS",
            hints_requested=step_input.hints_requested_count,
            score=score,
            timestamp=datetime.now(timezone.utc),
        )
        self.coaching_history.append(coaching_entry)

        self.state_machine.transition_to(
            CoachingState.INTERVENTION,
            reason=f"Administering {policy_decision.decision.intervention_type.value} intervention."
        )
        self.state_machine.transition_to(
            CoachingState.RETRY,
            reason=f"Next retry turn ready (retry {self.retry_count}/{self.config.max_retries})."
        )

        return OrchestratorStepResult(
            state=CoachingState.RETRY,
            outcome=CoachingLoopOutcome.RETRY_FAILURE,
            task=self.current_transfer_task,
            evaluation=eval_result,
            diagnosis=diagnosis,
            intervention=policy_decision.decision,
            scaffold_state=policy_decision.scaffold_state,
            retry_count=self.retry_count,
            retry_limit_reached=False,
            candidate_state=self.candidate_skill_state,
            transition_reason=f"Retry {self.retry_count} failed. Next coaching turn administered.",
        )

    async def _advance_to_independent_transfer(
        self, trigger_reason: str, outcome: Optional[CoachingLoopOutcome] = None
    ) -> OrchestratorStepResult:
        """Generates an unassisted, unseen L5 independent transfer challenge with zero scaffolding."""
        gen_request = TransferGenerationRequest(
            skill_id=self.training_context.skill_id,
            transfer_level=self.config.independent_level,
            core_invariants=self.training_context.core_invariants,
            base_surface_context=self.training_context.base_surface_context,
            base_expected_concepts=self.training_context.base_expected_concepts,
            parent_task_id=None,  # L5 is an independent, unassisted challenge
            parent_prompt=None,
        )
        independent_dto = await self.task_generator.generate_transfer_task(gen_request)
        self.independent_transfer_task = independent_dto

        # Enforce strict independence invariants
        self.current_scaffold_level = ScaffoldLevel.INDEPENDENT

        self.state_machine.transition_to(
            CoachingState.INDEPENDENT_TRANSFER,
            reason=f"{trigger_reason} Advanced to unassisted L5 Independent Transfer."
        )

        decided_outcome = outcome or (
            CoachingLoopOutcome.RETRY_SUCCESS
            if len(self.coaching_history) > 0
            else CoachingLoopOutcome.TRANSFER_SUCCESS
        )

        return OrchestratorStepResult(
            state=CoachingState.INDEPENDENT_TRANSFER,
            outcome=decided_outcome,
            task=self.independent_transfer_task,
            scaffold_state=ScaffoldState(
                current_level=ScaffoldLevel.INDEPENDENT,
                previous_level=self.current_scaffold_level,
                is_faded=True,
                assistance_dependency_index=self.coaching_policy.scaffold_manager.calculate_assistance_dependency_index(self.coaching_history),
                transition_reason="Independent evaluation mode active.",
            ),
            candidate_state=self.candidate_skill_state,
            transition_reason="Unassisted L5 independent transfer task presented.",
        )

    async def _handle_independent_step(self, step_input: CandidateStepInput) -> OrchestratorStepResult:
        """
        Evaluates the unassisted independent transfer task.
        Crucial research constraint: Assisted success != Independent success.
        Results are recorded strictly under ScaffoldLevel.INDEPENDENT with 0 hints.
        """
        task = self.independent_transfer_task or self.current_transfer_task

        # Determine situational transfer distance
        task_distance = getattr(task, "transfer_distance", None)
        if task_distance is None and getattr(task, "transfer_level", None) == TransferLevel.L5_INDEPENDENT_TRANSFER:
            task_distance = 0.90  # Default nominal transfer distance for L5

        # Verify unassisted conditions: strict research requirement (0 hints, INDEPENDENT scaffold, D >= 0.70)
        min_dist = max(float(getattr(self.config, "min_independent_distance", 0.70)), 0.70)
        val_errors = self.validator.validate_independent_conditions(
            scaffold_level=self.current_scaffold_level,
            hints_requested=step_input.hints_requested_count,
            transfer_distance=task_distance,
            min_distance=min_dist,
        )
        if val_errors:
            logger.warning(
                f"Independent transfer disqualified for candidate '{self.candidate_id}': {'; '.join(val_errors)}"
            )
            disqualified_eval = {
                "overall_score": 0.0,
                "correctness": 0.0,
                "completeness": 0.0,
                "relevance": 0.0,
                "technical_depth": 0.0,
                "reasoning": 0.0,
                "strengths": [],
                "weaknesses": [f"Disqualified from Independent Transfer: {err}" for err in val_errors],
                "missing_concepts": ["unassisted_independent_transfer"],
                "recommendations": ["L5 Independent Transfer strictly requires zero hints, transfer distance D >= 0.70, and unassisted execution."],
            }
            outcome = CoachingLoopOutcome.INDEPENDENT_FAILURE
            self._update_skill_state_metrics(
                score=0.0,
                transfer_level=self.config.transfer_level,
                failure_type=TransferFailureType.REASONING_FAILURE,
            )
            self.attempts_history.append({
                "stage": "INDEPENDENT_TRANSFER",
                "task_id": task.id,
                "score": 0.0,
                "evaluation": disqualified_eval,
                "hints_requested": step_input.hints_requested_count,
                "scaffold_level": self.current_scaffold_level.value,
                "independent_success": False,
                "disqualified": True,
                "disqualification_reasons": val_errors,
            })
            self.state_machine.transition_to(
                CoachingState.COMPLETED,
                reason=f"Independent transfer disqualified: {'; '.join(val_errors)}."
            )
            return OrchestratorStepResult(
                state=CoachingState.COMPLETED,
                outcome=outcome,
                task=task,
                evaluation=disqualified_eval,
                candidate_state=self.candidate_skill_state,
                transition_reason=f"Independent transfer disqualified: {'; '.join(val_errors)}.",
            )

        eval_result = await self.evaluator.evaluate_answer(
            target_role="Software Engineer",
            interview_type="TECHNICAL",
            topic=task.surface_context,
            question_text=task.prompt_template or task.surface_context,
            expected_concepts=task.expected_concepts,
            resume_evidence="",
            candidate_answer=step_input.candidate_answer,
            response_time_seconds=step_input.response_time_seconds,
        )
        score = float(eval_result.get("overall_score", 0.0))
        # Canonical research threshold strictly requires score >= 8.5 (or independent_pass_threshold)
        req_threshold = max(float(getattr(self.config, "independent_pass_threshold", 8.5)), 8.5)
        passed = score >= req_threshold

        outcome = CoachingLoopOutcome.INDEPENDENT_SUCCESS if passed else CoachingLoopOutcome.INDEPENDENT_FAILURE

        # Update Skill State
        self._update_skill_state_metrics(
            score=score,
            transfer_level=self.config.independent_level if passed else self.config.transfer_level,
            failure_type=None if passed else TransferFailureType.REASONING_FAILURE,
        )
        if passed and self.candidate_skill_state:
            # Completing unassisted L5 Independent Transfer validates required mastery (at least 0.85)
            self.candidate_skill_state.mastery_estimate = max(0.85, self.candidate_skill_state.mastery_estimate)
            # Assistance dependency is eliminated upon autonomous, unassisted transfer
            self.candidate_skill_state.assistance_dependency_index = 0.0

        # Record independent attempt
        self.attempts_history.append({
            "stage": "INDEPENDENT_TRANSFER",
            "task_id": task.id,
            "score": score,
            "evaluation": eval_result,
            "hints_requested": step_input.hints_requested_count,
            "scaffold_level": ScaffoldLevel.INDEPENDENT.value,
            "independent_success": passed,
        })

        self.state_machine.transition_to(
            CoachingState.COMPLETED,
            reason=f"Independent transfer finished with {outcome.value} (score={score})."
        )

        return OrchestratorStepResult(
            state=CoachingState.COMPLETED,
            outcome=outcome,
            task=task,
            evaluation=eval_result,
            candidate_state=self.candidate_skill_state,
            transition_reason=f"Coaching loop complete. Final outcome: {outcome.value}.",
        )

    def _update_skill_state_metrics(
        self,
        score: float,
        transfer_level: TransferLevel,
        failure_type: Optional[TransferFailureType],
    ):
        """
        Heuristic engineering model for CandidateSkillState updates.
        Does NOT claim Bayesian mastery estimation.
        """
        if not self.candidate_skill_state:
            return

        normalized_score = max(0.0, min(10.0, score)) / 10.0
        current_m = self.candidate_skill_state.mastery_estimate

        # Bounded adjustment based on score
        if normalized_score >= 0.70:
            new_mastery = min(1.0, current_m + 0.15 * normalized_score)
        else:
            new_mastery = max(0.0, current_m - 0.10 * (1.0 - normalized_score))

        # Uncertainty decreases with attempts
        new_uncertainty = max(0.10, round(self.candidate_skill_state.mastery_uncertainty * 0.85, 2))

        # Update highest transfer level if demonstrated
        highest = self.candidate_skill_state.highest_transfer_level
        # General transfer levels (L1-L4) require normalized_score >= 0.70;
        # L5 Independent Transfer strictly requires normalized_score >= 0.85 (score >= 8.5)
        min_score_for_level = 0.85 if transfer_level == TransferLevel.L5_INDEPENDENT_TRANSFER else 0.70
        if normalized_score >= min_score_for_level and is_higher_transfer_level(transfer_level, highest):
            highest = transfer_level

        # Calculate ADI
        adi = self.coaching_policy.scaffold_manager.calculate_assistance_dependency_index(self.coaching_history)

        # Update recurring failures
        recurring = list(self.candidate_skill_state.recurring_failure_types)
        if failure_type and failure_type != TransferFailureType.NONE and failure_type not in recurring:
            recurring.append(failure_type)

        self.candidate_skill_state = CandidateSkillStateDTO(
            candidate_id=self.candidate_id,
            skill_name=self.training_context.skill_id,
            mastery_estimate=round(new_mastery, 2),
            mastery_uncertainty=new_uncertainty,
            highest_transfer_level=highest,
            assistance_dependency_index=round(adi, 2),
            recurring_failure_types=recurring,
            total_attempts=self.candidate_skill_state.total_attempts + 1,
            last_assessed_at=datetime.now(timezone.utc),
        )

    def _build_candidate_history_dict(self) -> Dict[str, Any]:
        """Assembles candidate history dictionary for diagnosis engine."""
        if not self.candidate_skill_state:
            return {}
        return {
            "recurring_failure_types": [f.value for f in self.candidate_skill_state.recurring_failure_types],
            "past_attempts_count": self.candidate_skill_state.total_attempts,
            "mastery_estimate": self.candidate_skill_state.mastery_estimate,
        }

    def get_telemetry_record(self) -> ResearchTelemetryRecord:
        """Compiles the end-to-end research telemetry record."""
        final_outcome = CoachingLoopOutcome.INDEPENDENT_SUCCESS
        if self.attempts_history:
            last_att = self.attempts_history[-1]
            if last_att.get("stage") == "INDEPENDENT_TRANSFER":
                final_outcome = (
                    CoachingLoopOutcome.INDEPENDENT_SUCCESS
                    if last_att.get("independent_success")
                    else CoachingLoopOutcome.INDEPENDENT_FAILURE
                )
            elif self.retry_count >= self.config.max_retries:
                final_outcome = CoachingLoopOutcome.RETRY_LIMIT_REACHED

        return ResearchTelemetryRecord(
            candidate_id=self.candidate_id,
            session_id=self.session_id,
            skill_id=self.training_context.skill_id if self.training_context else "unknown",
            training_context=self.training_context,
            transfer_task_id=self.current_transfer_task.id if self.current_transfer_task else None,
            transfer_level=self.current_transfer_task.transfer_level if self.current_transfer_task else self.config.transfer_level,
            independent_task_id=self.independent_transfer_task.id if self.independent_transfer_task else None,
            attempts_history=self.attempts_history,
            coaching_history=self.coaching_history,
            state_transitions=self.state_machine.history,
            final_outcome=final_outcome,
            final_mastery_estimate=self.candidate_skill_state.mastery_estimate if self.candidate_skill_state else 0.0,
            final_mastery_uncertainty=self.candidate_skill_state.mastery_uncertainty if self.candidate_skill_state else 1.0,
            assistance_dependency_index=self.candidate_skill_state.assistance_dependency_index if self.candidate_skill_state else 0.0,
            policy_version=self.config.policy_version,
            created_at=datetime.now(timezone.utc),
        )

    def get_current_step_result(self) -> OrchestratorStepResult:
        """
        Synthesizes the current OrchestratorStepResult snapshot from authoritative internal state.
        Allows clients and REST endpoints to inspect and hydrate the active turn without state mutation.
        """
        curr_state = self.state_machine.current_state if self.state_machine else CoachingState.TRAINING
        active_task = (
            self.independent_transfer_task
            if curr_state == CoachingState.INDEPENDENT_TRANSFER and self.independent_transfer_task
            else self.current_transfer_task
        )
        if curr_state == CoachingState.COMPLETED:
            outcome = (
                CoachingLoopOutcome.INDEPENDENT_SUCCESS
                if (self.candidate_skill_state and self.candidate_skill_state.mastery_estimate >= 0.70)
                else CoachingLoopOutcome.TRANSFER_SUCCESS
            )
        elif curr_state == CoachingState.FAILED:
            outcome = CoachingLoopOutcome.RETRY_LIMIT_REACHED if self.retry_count >= self.config.max_retries else CoachingLoopOutcome.TRANSFER_FAILURE
        elif curr_state in (CoachingState.TRAINING, CoachingState.UNDERSTANDING_CHECK):
            outcome = CoachingLoopOutcome.TRAINING_SUCCESS
        elif curr_state in (CoachingState.TRANSFER_ATTEMPT, CoachingState.TRANSFER_GENERATION):
            outcome = CoachingLoopOutcome.TRAINING_SUCCESS
        elif curr_state in (CoachingState.INTERVENTION, CoachingState.RETRY):
            outcome = CoachingLoopOutcome.TRANSFER_FAILURE
        elif curr_state == CoachingState.INDEPENDENT_TRANSFER:
            outcome = CoachingLoopOutcome.TRANSFER_SUCCESS
        else:
            outcome = CoachingLoopOutcome.TRAINING_SUCCESS

        scaffold_state = ScaffoldState(
            current_level=self.current_scaffold_level,
            previous_level=self.current_scaffold_level,
            is_faded=self.current_scaffold_level == ScaffoldLevel.INDEPENDENT,
            assistance_dependency_index=(
                self.candidate_skill_state.assistance_dependency_index
                if self.candidate_skill_state
                else 0.0
            ),
            transition_reason=f"Current lifecycle state: {curr_state.value}",
        )

        last_eval = None
        if self.attempts_history:
            last_eval = self.attempts_history[-1].get("evaluation")

        return OrchestratorStepResult(
            state=curr_state,
            outcome=outcome,
            task=active_task,
            training_context=self.training_context,
            session_id=self.session_id,
            candidate_id=self.candidate_id,
            evaluation=last_eval,
            diagnosis=self.last_diagnosis,
            intervention=self.last_intervention,
            scaffold_state=scaffold_state,
            retry_count=self.retry_count,
            retry_limit_reached=self.retry_count >= self.config.max_retries,
            candidate_state=self.candidate_skill_state,
            transition_reason=(
                self.state_machine.history[-1].reason
                if self.state_machine and self.state_machine.history
                else f"Active state: {curr_state.value}"
            ),
        )

    def export_state_snapshot(self) -> Dict[str, Any]:
        """
        Exports a serializable state snapshot of the active coaching orchestrator.
        Enables seamless persistence and hydration across process restarts.
        """
        return {
            "candidate_id": self.candidate_id,
            "session_id": self.session_id,
            "training_context": self.training_context.model_dump(mode="json") if self.training_context else None,
            "config": self.config.model_dump(mode="json") if self.config else None,
            "current_state": self.state_machine.current_state.value if self.state_machine else CoachingState.TRAINING.value,
            "state_history": [
                t.model_dump(mode="json") if hasattr(t, "model_dump") else t
                for t in (self.state_machine.history if self.state_machine else [])
            ],
            "current_transfer_task": self.current_transfer_task.model_dump(mode="json") if self.current_transfer_task else None,
            "independent_transfer_task": self.independent_transfer_task.model_dump(mode="json") if self.independent_transfer_task else None,
            "current_scaffold_level": (
                self.current_scaffold_level.value
                if isinstance(self.current_scaffold_level, ScaffoldLevel)
                else str(self.current_scaffold_level)
            ),
            "retry_count": self.retry_count,
            "last_diagnosis": self.last_diagnosis.model_dump(mode="json") if self.last_diagnosis else None,
            "last_intervention": self.last_intervention.model_dump(mode="json") if self.last_intervention else None,
            "candidate_skill_state": self.candidate_skill_state.model_dump(mode="json") if self.candidate_skill_state else None,
            "coaching_history": [
                h.model_dump(mode="json") if hasattr(h, "model_dump") else h
                for h in self.coaching_history
            ],
            "attempts_history": self.attempts_history,
        }

    def hydrate_from_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """
        Hydrates orchestrator state from a persisted snapshot.
        Restores state machine position, scaffold level, retry count, tasks, and telemetry.
        """
        self.candidate_id = snapshot.get("candidate_id", "")
        self.session_id = snapshot.get("session_id", "")

        tc_data = snapshot.get("training_context")
        if tc_data:
            self.training_context = TrainingContext(**tc_data)

        cfg_data = snapshot.get("config")
        if cfg_data:
            self.config = CoachingSessionConfig(**cfg_data)

        cur_state_str = snapshot.get("current_state", CoachingState.TRAINING.value)
        cur_state = CoachingState(cur_state_str)
        self.state_machine = CoachingStateMachine(initial_state=cur_state)

        hist_data = snapshot.get("state_history", [])
        for h in hist_data:
            if isinstance(h, dict):
                self.state_machine._history.append(StateTransitionRecord(**h))
            elif isinstance(h, StateTransitionRecord):
                self.state_machine._history.append(h)

        cur_task_data = snapshot.get("current_transfer_task")
        if cur_task_data:
            self.current_transfer_task = TransferTaskDefinitionDTO(**cur_task_data)

        indep_task_data = snapshot.get("independent_transfer_task")
        if indep_task_data:
            self.independent_transfer_task = TransferTaskDefinitionDTO(**indep_task_data)

        scaffold_val = snapshot.get("current_scaffold_level")
        if scaffold_val:
            self.current_scaffold_level = ScaffoldLevel(scaffold_val)

        self.retry_count = snapshot.get("retry_count", 0)

        diag_data = snapshot.get("last_diagnosis")
        if diag_data:
            self.last_diagnosis = TransferFailureDiagnosisDTO(**diag_data)

        interv_data = snapshot.get("last_intervention")
        if interv_data:
            self.last_intervention = CoachingInterventionDecisionDTO(**interv_data)

        skill_state_data = snapshot.get("candidate_skill_state")
        if skill_state_data:
            self.candidate_skill_state = CandidateSkillStateDTO(**skill_state_data)

        coach_hist_data = snapshot.get("coaching_history", [])
        self.coaching_history = [
            CoachingHistoryEntry(**ch) if isinstance(ch, dict) else ch
            for ch in coach_hist_data
        ]

        self.attempts_history = snapshot.get("attempts_history", [])

