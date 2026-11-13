"""
Transfer-Aware Coaching Application Service.
Coordinates persistence and transaction lifecycles for the Coaching Orchestrator.
Strictly decoupled: does NOT implement diagnosis, coaching policy, or transfer generation logic.
"""

import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from fastapi import HTTPException, status
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import flag_modified

from backend.domain.transfer.skill_mapping import normalize_skill, extract_core_invariants
from backend.models.candidate import CandidateModel

from backend.models.interview import (
    InterviewSessionModel,
    QuestionModel,
    AnswerModel,
    EvaluationModel,
)
from backend.models.transfer_task import TransferTaskModel, TransferAttemptModel
from backend.models.transfer_diagnosis import TransferDiagnosisModel
from backend.models.coaching_event import CoachingInterventionEventModel
from backend.models.skill_state import CandidateSkillStateModel

from backend.repositories.transfer_task_repository import (
    TransferTaskRepository,
    TransferAttemptRepository,
)
from backend.repositories.transfer_diagnosis_repository import TransferDiagnosisRepository
from backend.repositories.coaching_event_repository import CoachingInterventionRepository
from backend.repositories.skill_state_repository import CandidateSkillStateRepository
from backend.repositories.interview_repository import (
    InterviewSessionRepository,
    QuestionRepository,
    AnswerRepository,
    EvaluationRepository,
)
from backend.repositories.candidate_repository import CandidateRepository

from backend.domain.transfer.coaching_types import (
    ScaffoldLevel,
    CoachingLoopOutcome,
)
from ai.coaching_orchestrator.state_machine import CoachingState
from ai.coaching_orchestrator.orchestrator import CoachingOrchestrator
from ai.coaching_orchestrator.schemas import (
    CoachingSessionConfig,
    TrainingContext,
    CandidateStepInput,
    OrchestratorStepResult,
    ResearchTelemetryRecord,
)

logger = logging.getLogger(__name__)


class TransferCoachingService:
    """
    Application Service managing the persistence layer for the transfer-aware coaching loop.
    Reuses existing QuestionModel, AnswerModel, EvaluationModel, TransferAttemptModel,
    TransferDiagnosisModel, CoachingInterventionEventModel, and CandidateSkillStateModel.
    """

    def __init__(
        self,
        session: AsyncSession,
        orchestrator: Optional[CoachingOrchestrator] = None,
    ):
        self.orchestrator = orchestrator or CoachingOrchestrator()
        self.session = session
        self._current_question_index = 0

    @property
    def session(self) -> AsyncSession:
        return self._session

    @session.setter
    def session(self, new_session: AsyncSession) -> None:
        self._session = new_session
        self.transfer_task_repo = TransferTaskRepository(new_session)
        self.transfer_attempt_repo = TransferAttemptRepository(new_session)
        self.transfer_diagnosis_repo = TransferDiagnosisRepository(new_session)
        self.coaching_event_repo = CoachingInterventionRepository(new_session)
        self.skill_state_repo = CandidateSkillStateRepository(new_session)
        self.question_repo = QuestionRepository(new_session)
        self.answer_repo = AnswerRepository(new_session)
        self.eval_repo = EvaluationRepository(new_session)
        self.interview_session_repo = InterviewSessionRepository(new_session)
        self.candidate_repo = CandidateRepository(new_session)


    async def start_coaching_loop(
        self,
        candidate_id: str,
        session_id: str,
        training_context: TrainingContext,
        config: Optional[CoachingSessionConfig] = None,
        resume_id: Optional[str] = None,
        target_role: Optional[str] = None,
    ) -> OrchestratorStepResult:
        """
        Initializes the coaching session and registers anchor training task,
        persistent interview_session root record, and skill state.
        """
        # 1. Initialize Orchestrator
        result = await self.orchestrator.initialize_session(
            candidate_id=candidate_id,
            session_id=session_id,
            training_context=training_context,
            config=config,
        )

        # 2. Ensure candidate exists (for relational consistency under PostgreSQL foreign keys)
        candidate = await self.candidate_repo.get(candidate_id)
        if not candidate:
            candidate = CandidateModel(
                id=candidate_id,
                email=f"candidate_{candidate_id[:8]}@example.com",
                full_name="Transfer Coaching Candidate",
            )
            await self.candidate_repo.create(candidate)

        # 3. Ensure InterviewSessionModel root exists for session_id to guarantee FK integrity.
        # If session_id matches an existing interview session (non-coaching mode, whether COMPLETED or IN_PROGRESS),
        # allocate a dedicated coaching session ID to ensure the interview session's question history and lifecycle are preserved.
        existing_session = await self.interview_session_repo.get(session_id)
        origin_interview_id: Optional[str] = None
        if existing_session and existing_session.status == "COMPLETED":
            origin_interview_id = session_id
            session_id = f"coach_{existing_session.id[:8]}_{uuid.uuid4().hex[:6]}"
            self.orchestrator.session_id = session_id
            result.session_id = session_id
            existing_session = None

        if not existing_session:
            coach_session = InterviewSessionModel(
                id=session_id,
                candidate_id=candidate_id,
                resume_id=resume_id,
                target_role=target_role or training_context.topic or training_context.skill_id or "Transfer Coaching",
                interview_type="TECHNICAL",
                difficulty_level=config.transfer_level.value if config else "L2_NEAR_TRANSFER",
                status="IN_PROGRESS",
                coaching_mode="TRANSFER_COACHING",
                assessment_plan={
                    "task_id": training_context.task_id,
                    "skill_id": training_context.skill_id,
                    "origin_interview_id": origin_interview_id,
                },
                competency_state={
                    "orchestrator_state": self.orchestrator.export_state_snapshot(),
                },
                start_time=datetime.now(timezone.utc),
            )
            await self.interview_session_repo.create(coach_session)
        else:
            existing_session.coaching_mode = "TRANSFER_COACHING"
            existing_session.status = "IN_PROGRESS"
            existing_comp = dict(existing_session.competency_state or {})
            existing_comp["orchestrator_state"] = self.orchestrator.export_state_snapshot()
            existing_session.competency_state = existing_comp
            flag_modified(existing_session, "competency_state")
            if resume_id and not existing_session.resume_id:
                existing_session.resume_id = resume_id
            await self.session.flush()

        # 4. Persist Anchor Training Task if not already present
        existing_task = await self.transfer_task_repo.get(training_context.task_id)
        if not existing_task:
            training_task_model = TransferTaskModel(
                id=training_context.task_id,
                parent_task_id=None,
                skill_id=training_context.skill_id,
                transfer_level="L0_RECALL",
                surface_context=training_context.base_surface_context,
                core_invariants=training_context.core_invariants,
                surface_distractors=[],
                expected_concepts=training_context.base_expected_concepts,
                prompt_template=training_context.question_text,
            )
            await self.transfer_task_repo.create(training_task_model)

        # 5. Initialize or synchronize CandidateSkillState
        if result.candidate_state:
            existing_st = await self.skill_state_repo.get_by_candidate_and_skill(candidate_id, training_context.skill_id)
            if existing_st:
                from backend.domain.transfer.taxonomy import TransferLevel
                from backend.domain.transfer.diagnosis_types import TransferFailureType
                from backend.domain.transfer.schemas import CandidateSkillStateDTO

                valid_fails = []
                for f in (existing_st.recurring_failure_types or []):
                    try:
                        valid_fails.append(TransferFailureType(f))
                    except Exception:
                        pass
                try:
                    tl = TransferLevel(existing_st.highest_transfer_level)
                except Exception:
                    tl = TransferLevel.L0_RECALL

                hydrated_dto = CandidateSkillStateDTO(
                    candidate_id=candidate_id,
                    skill_name=training_context.skill_id,
                    mastery_estimate=existing_st.mastery_estimate,
                    mastery_uncertainty=existing_st.mastery_uncertainty,
                    highest_transfer_level=tl,
                    assistance_dependency_index=existing_st.assistance_dependency_index or 0.0,
                    recurring_failure_types=valid_fails,
                    total_attempts=existing_st.total_attempts or 0,
                    last_assessed_at=existing_st.last_assessed_at or datetime.now(timezone.utc),
                )
                self.orchestrator.candidate_skill_state = hydrated_dto
                result.candidate_state = hydrated_dto
            else:
                await self.skill_state_repo.upsert_skill_state(
                    candidate_id=candidate_id,
                    skill_name=training_context.skill_id,
                    mastery_estimate=result.candidate_state.mastery_estimate,
                    mastery_uncertainty=result.candidate_state.mastery_uncertainty,
                    highest_transfer_level=result.candidate_state.highest_transfer_level.value,
                    assistance_dependency_index=result.candidate_state.assistance_dependency_index,
                    recurring_failure_types=[f.value for f in result.candidate_state.recurring_failure_types],
                    assessed_at=result.candidate_state.last_assessed_at,
                )

        await self.session.commit()
        return result

    async def start_coaching_from_interview(
        self,
        candidate_id: str,
        interview_session_id: str,
        question_id: Optional[str] = None,
        session_id: Optional[str] = None,
        config: Optional[CoachingSessionConfig] = None,
    ) -> OrchestratorStepResult:
        """
        Initializes a Transfer-Aware Coaching loop directly anchored on an evaluated interview question.
        Preserves evidence provenance and links the training context to the real interview gap.
        """
        # 1. Validate Candidate
        candidate = await self.candidate_repo.get(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{candidate_id}' not found."
            )

        # 2. Validate Interview Session
        interview_session = await self.interview_session_repo.get_with_full_history(interview_session_id)
        if not interview_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session '{interview_session_id}' not found."
            )

        if str(interview_session.candidate_id) != str(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Interview session '{interview_session_id}' does not belong to candidate '{candidate_id}'."
            )

        # 3. Locate Target Question
        target_q = None
        if question_id:
            for q in interview_session.questions:
                if q.id == question_id:
                    target_q = q
                    break
            if not target_q:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Question '{question_id}' not found in interview session '{interview_session_id}'."
                )
            if not target_q.answer or not target_q.answer.evaluation:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot anchor coaching: Question '{question_id}' has no evaluation record or candidate answer."
                )
        else:
            # Pick the lowest scoring evaluated question
            answered_questions = [
                q for q in interview_session.questions
                if q.answer and q.answer.evaluation
            ]
            if not answered_questions:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Cannot anchor coaching: Interview session '{interview_session_id}' contains no evaluated questions."
                )
            target_q = min(answered_questions, key=lambda q: q.answer.evaluation.overall_score)

        # 4. Extract evaluation evidence and diagnosed shortcomings
        ev = target_q.answer.evaluation
        turn_score = float(ev.overall_score)
        weaknesses_list = ev.weaknesses if ev.weaknesses else []
        missing_concepts_list = ev.missing_concepts if ev.missing_concepts else []
        evidence_list = [e.basis if hasattr(e, "basis") else str(e) for e in (ev.evidence or [])] if ev.evidence else []

        # 5. Normalize Skill and Invariants using question + evaluation signals
        combined_concepts = list(target_q.expected_concepts or []) + list(missing_concepts_list or [])
        if getattr(target_q, "target_competency", None):
            combined_concepts.append(target_q.target_competency)

        skill_id, is_canonical = normalize_skill(
            target_q.topic, target_q.category, combined_concepts
        )
        core_invariants = extract_core_invariants(
            target_q.expected_concepts or missing_concepts_list, target_q.topic, skill_id
        )

        # Concrete weakness string derivation (never inventing synthetic placeholders)
        if weaknesses_list:
            weakness_str = "; ".join(weaknesses_list)
        elif missing_concepts_list:
            weakness_str = f"Missing core concepts: {', '.join(missing_concepts_list)}"
        elif ev.recommendations:
            weakness_str = f"Growth opportunity: {'; '.join(ev.recommendations)}"
        else:
            weakness_str = f"Score deficit in {target_q.topic or target_q.category} (Score: {turn_score:.1f}/10)"

        primary_inv = core_invariants[0] if core_invariants else "Structural consistency and invariant preservation"
        secondary_inv = core_invariants[1] if len(core_invariants) > 1 else primary_inv
        inv_summary = "; ".join(core_invariants[:2]) if core_invariants else primary_inv

        explain_part = (
            f"### 1. Invariant Analysis: {target_q.topic or skill_id}\n"
            f"**Diagnosed Interview Shortcoming:** {weakness_str}.\n\n"
            f"**Core Invariants Required:** {inv_summary}.\n"
            f"When answering problems around {target_q.topic or skill_id}, you must explicitly establish these invariant bounds rather than relying on surface patterns."
        )
        example_part = (
            f"### 2. Invariant-Preserving Pattern\n"
            f"- **Observed Gap:** Overlooking '{primary_inv}' introduces latency spikes or integrity failures under scale.\n"
            f"- **Correct Architecture:** Systematically verifying '{secondary_inv}' guarantees resilient execution across variable workloads."
        )
        check_part = (
            f"### 3. Understanding Verification\n"
            f"Before advancing to novel transfer variations, articulate how enforcing '{primary_inv}' resolves {weakness_str} in your original design."
        )
        teaching_lesson = f"{explain_part}\n\n{example_part}\n\n{check_part}"

        # 6. Build Training Context anchored on the actual interview question & diagnosed gap
        training_context = TrainingContext(
            task_id=f"interview_{target_q.id}",
            question_text=target_q.question_text,
            skill_id=skill_id,
            core_invariants=core_invariants,
            base_surface_context=target_q.topic or "Software Architecture",
            base_expected_concepts=target_q.expected_concepts or [target_q.topic or "Engineering Invariants"],
            topic=target_q.topic or "Engineering Invariants",
            target_role=interview_session.target_role,
            weakness=weakness_str,
            evidence=evidence_list,
            current_mastery=round(turn_score / 10.0, 3) if turn_score is not None else None,
            learning_objective=f"Master {skill_id} invariants and eliminate: {', '.join(weaknesses_list[:2]) or 'shortcomings'}",
            teaching_lesson=teaching_lesson,
        )

        # 7. Generate or use supplied coaching session ID preserving interview provenance
        # Ensure coaching session ID is distinct from interview session ID even if caller passes the interview ID
        if not session_id or session_id == interview_session_id:
            coaching_session_id = f"coach_{interview_session.id[:8]}_{uuid.uuid4().hex[:6]}"
        else:
            coaching_session_id = session_id

        # 8. Start the Coaching Loop using the existing CoachingOrchestrator
        return await self.start_coaching_loop(
            candidate_id=candidate_id,
            session_id=coaching_session_id,
            training_context=training_context,
            config=config,
            resume_id=interview_session.resume_id,
            target_role=interview_session.target_role,
        )

    async def submit_step(
        self,
        step_input: CandidateStepInput,
    ) -> OrchestratorStepResult:
        """
        Coordinates orchestrator turn step and atomically persists resulting
        Question, Answer, Evaluation, TransferAttempt, Diagnosis, Intervention, and Skill State.
        """
        # 1. Run business orchestration
        result = await self.orchestrator.submit_step(step_input)

        # 2. Persist Transfer Task Definition if new
        if result.task:
            existing_task = await self.transfer_task_repo.get(result.task.id)
            if not existing_task:
                task_model = TransferTaskModel(
                    id=result.task.id,
                    parent_task_id=result.task.parent_task_id,
                    skill_id=result.task.skill_id,
                    transfer_level=result.task.transfer_level.value,
                    surface_context=result.task.surface_context,
                    core_invariants=result.task.core_invariants,
                    surface_distractors=result.task.surface_distractors,
                    expected_concepts=result.task.expected_concepts,
                    rubric_id=result.task.rubric_id,
                    prompt_template=result.task.prompt_template,
                )
                await self.transfer_task_repo.create(task_model)

        # 3. Create standard Question, Answer, Evaluation models for auditability
        self._current_question_index += 1
        active_task = result.task
        q_text = (
            active_task.prompt_template
            if active_task and active_task.prompt_template
            else (self.orchestrator.training_context.question_text if self.orchestrator.training_context else "Question")
        )
        topic = active_task.surface_context if active_task else "Technical Architecture"
        concepts = active_task.expected_concepts if active_task else []

        question_model = QuestionModel(
            id=str(uuid.uuid4()),
            session_id=self.orchestrator.session_id,
            question_index=self._current_question_index,
            question_text=q_text,
            category="system_design",
            topic=topic,
            difficulty="medium",
            stage_name="Transfer-Aware Coaching",
            stage_index=self._current_question_index,
            expected_concepts=concepts,
        )
        await self.question_repo.create(question_model)

        answer_model = AnswerModel(
            id=str(uuid.uuid4()),
            question_id=question_model.id,
            session_id=self.orchestrator.session_id,
            answer_text=step_input.candidate_answer,
            response_time_seconds=step_input.response_time_seconds,
        )
        await self.answer_repo.create(answer_model)

        evaluation_model = None
        if result.evaluation:
            evaluation_model = EvaluationModel(
                id=str(uuid.uuid4()),
                answer_id=answer_model.id,
                question_id=question_model.id,
                session_id=self.orchestrator.session_id,
                overall_score=result.evaluation.get("overall_score", 0.0),
                correctness=result.evaluation.get("correctness", 0.0),
                completeness=result.evaluation.get("completeness", 0.0),
                relevance=result.evaluation.get("relevance", 0.0),
                technical_depth=result.evaluation.get("technical_depth", 0.0),
                reasoning=result.evaluation.get("reasoning", 0.0),
                strengths=result.evaluation.get("strengths", []),
                weaknesses=result.evaluation.get("weaknesses", []),
                missing_concepts=result.evaluation.get("missing_concepts", []),
                evidence=result.evaluation.get("evidence", []),
                recommendations=result.evaluation.get("recommendations", []),
                exemplar_answer=result.evaluation.get("exemplar_answer"),
                coach_note=result.evaluation.get("coach_note"),
            )
            await self.eval_repo.create(evaluation_model)

        # 4. If this step represents a transfer attempt, retry, or independent attempt, persist TransferAttempt
        if active_task:
            is_success = result.outcome in (
                CoachingLoopOutcome.TRANSFER_SUCCESS,
                CoachingLoopOutcome.RETRY_SUCCESS,
                CoachingLoopOutcome.INDEPENDENT_SUCCESS,
            )
            scaffold_applied = (
                result.scaffold_state.current_level.value
                if result.scaffold_state
                else self.orchestrator.current_scaffold_level.value
            )

            attempt_model = TransferAttemptModel(
                id=str(uuid.uuid4()),
                candidate_id=self.orchestrator.candidate_id,
                transfer_task_id=active_task.id,
                session_id=self.orchestrator.session_id,
                question_id=question_model.id,
                answer_id=answer_model.id,
                evaluation_id=evaluation_model.id if evaluation_model else None,
                transfer_success=is_success,
                scaffold_level_applied=scaffold_applied,
                hints_requested_count=step_input.hints_requested_count,
                attempt_number=result.retry_count + 1,
            )
            await self.transfer_attempt_repo.create(attempt_model)

            # 4a. Persist Diagnosis if present
            diag_model = None
            if result.diagnosis:
                evidence_raw = [e.model_dump() for e in result.diagnosis.evidence]
                diag_model = TransferDiagnosisModel(
                    id=str(uuid.uuid4()),
                    attempt_id=attempt_model.id,
                    failure_type=result.diagnosis.failure_type.value,
                    confidence=result.diagnosis.confidence,
                    affected_skill=result.diagnosis.affected_skill,
                    deterministic_signals=result.diagnosis.deterministic_signals,
                    evidence=evidence_raw,
                    recommended_intervention=result.diagnosis.recommended_intervention.value,
                    diagnostic_reasoning=result.diagnosis.diagnostic_reasoning,
                )
                await self.transfer_diagnosis_repo.create(diag_model)

            # 4b. Persist Coaching Intervention Event if present
            if result.intervention:
                intervention_model = CoachingInterventionEventModel(
                    id=str(uuid.uuid4()),
                    attempt_id=attempt_model.id,
                    diagnosis_id=diag_model.id if diag_model else None,
                    session_id=self.orchestrator.session_id,
                    intervention_type=result.intervention.intervention_type.value,
                    scaffold_level=result.intervention.scaffold_level.value,
                    content=result.intervention.content,
                    pedagogical_intent=result.intervention.pedagogical_intent,
                    is_faded=result.intervention.is_faded,
                    retry_required=result.intervention.retry_required,
                )
                await self.coaching_event_repo.create(intervention_model)

        # 5. Persist Candidate Skill State
        if result.candidate_state and self.orchestrator.training_context:
            raw_skill = self.orchestrator.training_context.skill_id
            canonical_id, is_canonical = normalize_skill(raw_skill)
            target_skill_key = canonical_id if is_canonical else raw_skill
            await self.skill_state_repo.upsert_skill_state(
                candidate_id=self.orchestrator.candidate_id,
                skill_name=target_skill_key,
                mastery_estimate=result.candidate_state.mastery_estimate,
                mastery_uncertainty=result.candidate_state.mastery_uncertainty,
                highest_transfer_level=result.candidate_state.highest_transfer_level.value,
                assistance_dependency_index=result.candidate_state.assistance_dependency_index,
                recurring_failure_types=[f.value for f in result.candidate_state.recurring_failure_types],
                assessed_at=result.candidate_state.last_assessed_at,
            )

        # 6. Persist Orchestrator State Snapshot in InterviewSessionModel
        interview_session = await self.interview_session_repo.get(self.orchestrator.session_id)
        if interview_session:
            comp_state = dict(interview_session.competency_state or {})
            comp_state["orchestrator_state"] = self.orchestrator.export_state_snapshot()
            interview_session.competency_state = comp_state
            flag_modified(interview_session, "competency_state")
            interview_session.current_question_index = self._current_question_index
            if result.state == CoachingState.COMPLETED:
                interview_session.status = "COMPLETED"
                interview_session.end_time = datetime.now(timezone.utc)
            elif result.state == CoachingState.FAILED:
                interview_session.status = "FAILED"
                interview_session.end_time = datetime.now(timezone.utc)
            await self.session.commit()

        return result

    @classmethod
    async def hydrate_session(
        cls,
        session: AsyncSession,
        session_id: str,
    ) -> Optional["TransferCoachingService"]:
        """
        Reconstructs an active TransferCoachingService and CoachingOrchestrator from persisted database state.
        Enables uninterrupted coaching progression across backend process restarts and multi-worker instances.
        """
        session_repo = InterviewSessionRepository(session)
        interview_session = await session_repo.get(session_id)
        if not interview_session:
            return None

        comp_state = interview_session.competency_state or {}
        snapshot = comp_state.get("orchestrator_state")
        if not snapshot:
            return None

        orchestrator = CoachingOrchestrator()
        orchestrator.hydrate_from_snapshot(snapshot)

        service = cls(session=session, orchestrator=orchestrator)
        service._current_question_index = interview_session.current_question_index or 0
        return service

    def get_telemetry(self) -> ResearchTelemetryRecord:
        """Returns the compiled research telemetry record from orchestrator."""
        return self.orchestrator.get_telemetry_record()

    def get_current_step_result(self) -> OrchestratorStepResult:
        """Returns the current step snapshot from orchestrator."""
        return self.orchestrator.get_current_step_result()

