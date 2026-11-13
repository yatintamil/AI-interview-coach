"""
Interview Application Orchestration Service.
Coordinates the Single AI Interviewer flow: Setup -> Question Generation (RAG grounded) -> Answer Submission -> Explainable Evaluation -> Progression -> Final Aggregated Report.
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from fastapi import HTTPException, status

from backend.models.interview import (
    InterviewSessionModel,
    QuestionModel,
    AnswerModel,
    EvaluationModel,
    SessionReportModel,
)
from backend.repositories.interview_repository import (
    InterviewSessionRepository,
    QuestionRepository,
    AnswerRepository,
    EvaluationRepository,
    SessionReportRepository,
)
from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.resume_repository import ResumeRepository
from backend.repositories.skill_state_repository import CandidateSkillStateRepository
from backend.services.rag_service import CandidateRAGService
from backend.domain.transfer.skill_mapping import normalize_skill, extract_core_invariants
from backend.domain.role import (
    RoleSpecification,
    RoleCompetencyBlueprint,
    AssessmentPlan,
    AssessmentPlanConfig,
    QuestionPlan,
    RoleCompetencyProfile,
    InterviewCompletionReason,
)
from ai.interview_engine.role_intelligence import RoleIntelligenceService
from ai.interview_engine.assessment_planner import AssessmentPlanner, STAGE_NAMES
from ai.interview_engine.question_generator import AIQuestionGenerator
from ai.evaluation_engine.evaluator import AIEvaluator
from ai.evaluation_engine.deterministic_aggregator import ScoreAggregator
from backend.schemas.interview import (
    InterviewCreateRequest,
    InterviewSessionResponse,
    QuestionResponse,
    TurnEvaluationResponse,
    TurnAnswerResultResponse,
    SessionReportResponse,
    QuestionTurnHistory,
    EvidenceItem,
    CoachHintResponse,
    WeaknessRemediationItem,
    InterviewWeaknessesResponse,
    InterviewDiagnosticEvidence,
)


# In-memory session cache for stable resume & candidate context during active interview turns
_RESUME_CONTEXT_CACHE: Dict[str, tuple] = {}


def clear_resume_context_cache(session_id: Optional[str] = None, candidate_id: Optional[str] = None) -> None:
    """Explicitly invalidates candidate RAG context cache for a session or candidate."""
    global _RESUME_CONTEXT_CACHE
    if not session_id and not candidate_id:
        _RESUME_CONTEXT_CACHE.clear()
        return
    keys_to_del = [
        k for k in _RESUME_CONTEXT_CACHE
        if (session_id and k.startswith(f"{session_id}:"))
        or (candidate_id and f":{candidate_id}:" in k)
    ]
    for k in keys_to_del:
        _RESUME_CONTEXT_CACHE.pop(k, None)


class InterviewService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.session_repo = InterviewSessionRepository(session)
        self.question_repo = QuestionRepository(session)
        self.answer_repo = AnswerRepository(session)
        self.eval_repo = EvaluationRepository(session)
        self.report_repo = SessionReportRepository(session)
        self.candidate_repo = CandidateRepository(session)
        self.resume_repo = ResumeRepository(session)
        self.skill_state_repo = CandidateSkillStateRepository(session)
        self.rag_service = CandidateRAGService(session)
        self.question_generator = AIQuestionGenerator()
        self.evaluator = AIEvaluator()

    def _to_question_response(self, q: QuestionModel, total_questions: int = 5) -> QuestionResponse:
        stg_name = getattr(q, "stage_name", None) or "Foundational Orientation"
        stg_idx = getattr(q, "stage_index", 1) or 1
        target_comp = getattr(q, "target_competency", None) or q.topic
        is_followup = getattr(q, "is_followup", False) or False
        q_plan_data = getattr(q, "question_plan", None) or {}
        followup_concept = q_plan_data.get("followup_target_concept") if isinstance(q_plan_data, dict) else None

        return QuestionResponse(
            id=q.id,
            session_id=q.session_id,
            question_index=q.question_index,
            question_text=q.question_text,
            category=q.category,
            topic=q.topic,
            difficulty=q.difficulty,
            stage_name=stg_name,
            stage_index=stg_idx,
            total_stages=5 if total_questions > 3 else 3,
            target_competency=target_comp,
            assessment_objective=getattr(q, "assessment_objective", None) or f"Assess {target_comp}",
            is_followup=is_followup,
            followup_target_concept=followup_concept,
            resume_evidence=q.resume_evidence,
            expected_concepts=q.expected_concepts or [],
            coach_lead_in=getattr(q, "coach_lead_in", None) or f"Let's focus on your experience with {target_comp}.",
            researched_skill=getattr(q, "researched_skill", None) or target_comp,
            created_at=q.created_at,
        )

    def _to_evaluation_response(
        self, ev: EvaluationModel, diagnostic_evidence: Optional[InterviewDiagnosticEvidence] = None
    ) -> TurnEvaluationResponse:
        evidence_items = []
        for e in (ev.evidence or []):
            if isinstance(e, dict):
                evidence_items.append(EvidenceItem(claim=e.get("claim", ""), basis=e.get("basis", "")))
            elif isinstance(e, str):
                evidence_items.append(EvidenceItem(claim=e, basis="From response"))

        coach_note = getattr(ev, "coach_note", None)
        detected_feeling = getattr(ev, "detected_feeling", None)
        coach_conversational_response = getattr(ev, "coach_conversational_response", None)
        socratic_scaffold = getattr(ev, "socratic_scaffold", None)

        if coach_note and not detected_feeling:
            if coach_note.startswith("[") and "]" in coach_note:
                parts = coach_note.split("]", 1)
                detected_feeling = parts[0].replace("[", "").strip()
                remainder = parts[1].strip()
                if "Socratic Scaffold:" in remainder:
                    scaff_parts = remainder.split("Socratic Scaffold:", 1)
                    coach_conversational_response = scaff_parts[0].strip()
                    socratic_scaffold = scaff_parts[1].strip()
                else:
                    coach_conversational_response = remainder
            else:
                coach_conversational_response = coach_note

        return TurnEvaluationResponse(
            id=ev.id,
            answer_id=ev.answer_id,
            question_id=ev.question_id,
            session_id=ev.session_id,
            overall_score=ev.overall_score,
            correctness=ev.correctness,
            completeness=ev.completeness,
            relevance=ev.relevance,
            technical_depth=ev.technical_depth,
            reasoning=ev.reasoning,
            strengths=ev.strengths or [],
            weaknesses=ev.weaknesses or [],
            missing_concepts=ev.missing_concepts or [],
            evidence=evidence_items,
            recommendations=ev.recommendations or [],
            exemplar_answer=getattr(ev, "exemplar_answer", None),
            coach_note=coach_note,
            detected_feeling=detected_feeling or "Focused & Analytical ⚖️",
            coach_conversational_response=coach_conversational_response or coach_note,
            socratic_scaffold=socratic_scaffold,
            diagnostic_evidence=diagnostic_evidence,
            created_at=ev.created_at,
        )

    def _to_session_response(self, s: InterviewSessionModel) -> InterviewSessionResponse:
        history: List[QuestionTurnHistory] = []
        curr_q: Optional[QuestionResponse] = None

        if s.questions:
            for q in s.questions:
                q_resp = self._to_question_response(q)
                ans_dict = None
                eval_resp = None
                if q.answer:
                    ans_dict = {
                        "id": q.answer.id,
                        "answer_text": q.answer.answer_text,
                        "response_time_seconds": q.answer.response_time_seconds,
                        "submitted_at": q.answer.submitted_at,
                    }
                    if q.answer.evaluation:
                        eval_resp = self._to_evaluation_response(q.answer.evaluation)

                turn = QuestionTurnHistory(question=q_resp, answer=ans_dict, evaluation=eval_resp)
                history.append(turn)

                # Set current question if not yet answered
                if not q.answer and curr_q is None:
                    curr_q = q_resp

        report_resp = None
        if s.report:
            report_resp = SessionReportResponse(
                id=s.report.id,
                session_id=s.report.session_id,
                final_score=s.report.final_score,
                technical_score=s.report.technical_score,
                behavioral_score=s.report.behavioral_score,
                communication_score=s.report.communication_score,
                summary_strengths=s.report.summary_strengths or [],
                summary_weaknesses=s.report.summary_weaknesses or [],
                key_recommendations=s.report.key_recommendations or [],
                role_competency_profile=getattr(s.report, "role_competency_profile", None),
                generated_at=s.report.generated_at,
            )

        active_comp = None
        if curr_q:
            active_comp = curr_q.target_competency or curr_q.topic

        assessed_count = 0
        total_comps = 5
        ev_ratio = getattr(s, "evidence_coverage_ratio", 0.0) or 0.0
        if s.assessment_plan and isinstance(s.assessment_plan, dict):
            ev_records = s.assessment_plan.get("competency_evidence", {})
            assessed_count = len([r for r in ev_records.values() if r.get("questions_asked", 0) > 0])
            total_comps = len(ev_records) or 5
            if not ev_ratio:
                ev_ratio = s.assessment_plan.get("evidence_coverage_ratio", 0.0)

        return InterviewSessionResponse(
            id=s.id,
            candidate_id=s.candidate_id,
            resume_id=s.resume_id,
            target_role=s.target_role,
            target_roles=getattr(s, "target_roles", None),
            custom_role_description=getattr(s, "custom_role_description", None),
            active_competency=active_comp,
            interview_type=s.interview_type,
            difficulty_level=s.difficulty_level,
            coaching_mode=getattr(s, "coaching_mode", "COACHING") or "COACHING",
            status=s.status,
            target_question_count=s.target_question_count,
            current_question_index=s.current_question_index,
            completion_reason=getattr(s, "completion_reason", None),
            evidence_coverage_ratio=round(ev_ratio, 2),
            competencies_assessed_count=assessed_count,
            total_competencies_count=total_comps,
            start_time=s.start_time,
            end_time=s.end_time,
            created_at=s.created_at,
            current_question=curr_q,
            history=history,
            report=report_resp,
        )

    async def create_session(self, payload: InterviewCreateRequest) -> InterviewSessionResponse:
        # Validate candidate
        candidate = await self.candidate_repo.get(payload.candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Candidate with ID '{payload.candidate_id}' not found."
            )

        # Resolve resume
        resume_id = payload.resume_id
        if not resume_id:
            active_resume = await self.resume_repo.get_active_resume(payload.candidate_id)
            if active_resume:
                resume_id = active_resume.id

        target_role = payload.target_role.strip() if payload.target_role and payload.target_role.strip() else "Adaptive Omnirole / Universal Software Engineering"
        target_roles = payload.target_roles or [target_role]
        custom_desc = payload.custom_role_description

        # Build Role Specification & Role Competency Blueprint
        spec = RoleSpecification(
            role_name=target_role,
            target_roles=target_roles,
            custom_role_description=custom_desc,
            seniority=payload.seniority,
            is_custom=bool(custom_desc),
        )
        blueprint = RoleIntelligenceService.build_competency_blueprint(spec)
        target_q = payload.target_question_count or 5
        assessment_plan = AssessmentPlanner.create_assessment_plan(
            blueprint,
            config=AssessmentPlanConfig(
                min_questions=min(3, target_q),
                target_questions=target_q,
                max_questions=min(25, max(8, target_q + 3)),
                max_questions_per_stage=2,
                max_followups_per_competency=2,
            )
        )

        session_model = InterviewSessionModel(
            id=str(uuid.uuid4()),
            candidate_id=payload.candidate_id,
            resume_id=resume_id,
            target_role=target_role,
            target_roles=target_roles,
            custom_role_description=custom_desc,
            assessment_plan=assessment_plan.model_dump(),
            competency_state={c_id: rec.model_dump() for c_id, rec in assessment_plan.competency_evidence.items()},
            interview_type=payload.interview_type.upper(),
            difficulty_level=payload.difficulty_level.upper(),
            coaching_mode=(payload.coaching_mode or "COACHING").upper(),
            status="CREATED",
            target_question_count=payload.target_question_count,
            current_question_index=0,
        )
        created = await self.session_repo.create(session_model)
        loaded = await self.session_repo.get_with_full_history(created.id)
        return self._to_session_response(loaded or created)

    async def start_session(self, session_id: str) -> InterviewSessionResponse:
        session_obj = await self.session_repo.get_with_full_history(session_id)
        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session '{session_id}' not found."
            )

        if session_obj.status == "COMPLETED":
            return self._to_session_response(session_obj)

        if session_obj.status == "CREATED":
            session_obj.status = "IN_PROGRESS"
            session_obj.start_time = datetime.utcnow()
            session_obj.current_question_index = 1

            # Retrieve candidate profile summary, RAG context, claims, and personalized web dossier
            profile_summary, rag_context, cand_claims, candidate_dossier = await self._get_resume_context(session_obj)

            # Reconstruct Role Competency Blueprint and Assessment Plan
            spec = RoleSpecification(
                role_name=session_obj.target_role,
                target_roles=getattr(session_obj, "target_roles", None) or [session_obj.target_role],
                custom_role_description=getattr(session_obj, "custom_role_description", None),
            )
            blueprint = RoleIntelligenceService.build_competency_blueprint(spec)

            raw_plan = getattr(session_obj, "assessment_plan", None)
            if raw_plan and isinstance(raw_plan, dict):
                plan = AssessmentPlan.model_validate(raw_plan)
            else:
                plan = AssessmentPlanner.create_assessment_plan(
                    blueprint,
                    config=AssessmentPlanConfig(
                        min_questions=3,
                        target_questions=session_obj.target_question_count or 5,
                        max_questions=min(25, max(8, (session_obj.target_question_count or 5) + 3)),
                        max_questions_per_stage=2,
                        max_followups_per_competency=2,
                    )
                )

            cand_context = {
                "profile_summary": profile_summary,
                "claims": cand_claims,
            }
            q_plan = AssessmentPlanner.create_question_plan(
                plan=plan,
                blueprint=blueprint,
                candidate_context=cand_context,
                difficulty_level=session_obj.difficulty_level,
            )

            # Generate Question 1 using role-governed generator
            q_data = await self.question_generator.generate_question(
                target_role=session_obj.target_role,
                interview_type=session_obj.interview_type,
                difficulty_level=session_obj.difficulty_level,
                turn_number=1,
                total_questions=plan.config.target_questions,
                resume_summary=profile_summary,
                rag_context=rag_context,
                previous_questions=[],
                last_question=None,
                last_answer=None,
                last_score=None,
                last_missing_concepts=None,
                candidate_claims=cand_claims,
                candidate_dossier=candidate_dossier,
                question_plan=q_plan,
            )

            from ai.interview_engine.question_sanitizer import (
                sanitize_and_enforce_single_question,
                validate_question_semantics,
                validate_substantive_question_focus,
                validate_question_competency_alignment,
                CompetencyAlignmentError,
            )
            clean_first_q = sanitize_and_enforce_single_question(q_data["question"])
            is_valid, validation_err = validate_question_semantics(clean_first_q)
            is_focused, focus_err = validate_substantive_question_focus(clean_first_q)
            is_aligned, align_err = validate_question_competency_alignment(
                question_text=clean_first_q,
                target_competency=q_plan.competency_name,
                expected_concepts=q_plan.expected_concepts,
                core_invariants=q_plan.core_invariants,
            )
            if not is_valid or not is_focused or not is_aligned:
                from ai.interview_engine.question_bank import QuestionBankService
                try:
                    bank_fallback = QuestionBankService.find_question(
                        stage_index=q_plan.stage_index,
                        target_role=session_obj.target_role,
                        resume_summary=f"{profile_summary} {rag_context}",
                        asked_questions=[],
                        difficulty=session_obj.difficulty_level,
                        target_competency=q_plan.competency_name,
                        expected_concepts=q_plan.expected_concepts,
                        is_followup=q_plan.is_followup,
                        followup_concept=q_plan.followup_target_concept,
                        depth_level=q_plan.depth_level,
                    )
                    clean_first_q = sanitize_and_enforce_single_question(bank_fallback.get("question", ""))
                    q_data["topic"] = bank_fallback.get("topic") or q_plan.competency_name
                    q_data["category"] = bank_fallback.get("category", "technical")
                    q_data["expected_concepts"] = bank_fallback.get("expected_concepts") or q_plan.expected_concepts
                except Exception as fb_err:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Unable to generate or retrieve a valid question aligned with target competency '{q_plan.competency_name}': {fb_err}"
                    )

            first_lead_in = q_data.get("coach_lead_in") or f"Welcome! We'll begin by exploring your foundational experience with {q_plan.competency_name}."
            from ai.evaluation_engine.rubrics import get_rubric_for_question
            first_rubric = get_rubric_for_question(
                topic=q_data["topic"],
                question_text=clean_first_q,
                expected_concepts=q_data["expected_concepts"],
                interview_type=session_obj.interview_type,
            )
            q_plan.rubric_snapshot = first_rubric.model_dump()
            first_expected_concepts = q_data.get("expected_concepts") or q_plan.expected_concepts

            first_question = QuestionModel(
                id=str(uuid.uuid4()),
                session_id=session_obj.id,
                question_index=1,
                question_text=clean_first_q,
                category=q_data["category"],
                topic=q_data["topic"],
                difficulty=q_data["difficulty"],
                stage_name=q_plan.stage_name,
                stage_index=q_plan.stage_index,
                target_competency=q_plan.competency_name,
                assessment_objective=q_plan.objective,
                is_followup=q_plan.is_followup,
                question_plan=q_plan.model_dump(),
                resume_evidence=q_data["resume_evidence"],
                expected_concepts=first_expected_concepts,
                coach_lead_in=first_lead_in,
            )
            created_first_q = await self.question_repo.create(first_question)
            if session_obj.questions is not None:
                session_obj.questions.append(created_first_q)
            else:
                session_obj.questions = [created_first_q]

            session_obj.assessment_plan = plan.model_dump()
            session_obj.competency_state = {c_id: rec.model_dump() for c_id, rec in plan.competency_evidence.items()}
            await self.session.flush()

        loaded = await self.session_repo.get_with_full_history(session_id)
        return self._to_session_response(loaded or session_obj)

    async def submit_answer_and_progress(
        self,
        session_id: str,
        answer_text: str,
        response_time_seconds: float = 0.0,
    ) -> TurnAnswerResultResponse:
        t_turn_start = time.perf_counter()
        session_obj = await self.session_repo.get_with_full_history(session_id)
        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session '{session_id}' not found."
            )

        if session_obj.status == "COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This interview session is already completed."
            )

        # Get current unanswered question
        current_q = None
        for q in session_obj.questions:
            if not q.answer:
                current_q = q
                break

        if not current_q:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No pending question to answer in this session."
            )

        # 1. Save Answer
        answer_model = AnswerModel(
            id=str(uuid.uuid4()),
            question_id=current_q.id,
            session_id=session_obj.id,
            answer_text=answer_text,
            response_time_seconds=response_time_seconds,
        )
        current_q.answer = answer_model
        await self.answer_repo.create(answer_model)

        # 2. Evaluate Answer with Explainable Evaluation Engine
        t_eval_start = time.perf_counter()
        q_plan_meta = current_q.question_plan if isinstance(current_q.question_plan, dict) else {}
        rubric_snapshot = q_plan_meta.get("rubric_snapshot")
        eval_data = await self.evaluator.evaluate_answer(
            target_role=session_obj.target_role,
            interview_type=session_obj.interview_type,
            topic=current_q.topic,
            question_text=current_q.question_text,
            expected_concepts=current_q.expected_concepts or [],
            resume_evidence=current_q.resume_evidence or "",
            candidate_answer=answer_text,
            response_time_seconds=response_time_seconds,
            rubric_snapshot=rubric_snapshot,
        )
        t_eval_duration = round(time.perf_counter() - t_eval_start, 3)

        # 2.2 Run Empathy & Emotional Sentiment Extraction
        from ai.interview_engine.empathy_engine import EmpathyEngine
        empathy_data = EmpathyEngine.analyze_candidate_emotion(
            answer_text=answer_text,
            response_time_seconds=response_time_seconds,
            last_score=eval_data.get("overall_score"),
        )
        coach_note_full = (
            f"[{empathy_data['detected_feeling']}] {empathy_data['coach_dialogue']}\n\n"
            f"Socratic Scaffold: {empathy_data['socratic_scaffold']}"
        )

        evaluation_model = EvaluationModel(
            id=str(uuid.uuid4()),
            answer_id=answer_model.id,
            question_id=current_q.id,
            session_id=session_obj.id,
            overall_score=eval_data["overall_score"],
            correctness=eval_data["correctness"],
            completeness=eval_data["completeness"],
            relevance=eval_data["relevance"],
            technical_depth=eval_data["technical_depth"],
            reasoning=eval_data["reasoning"],
            strengths=eval_data["strengths"],
            weaknesses=eval_data["weaknesses"],
            missing_concepts=eval_data["missing_concepts"],
            evidence=eval_data["evidence"],
            recommendations=eval_data["recommendations"],
            exemplar_answer=eval_data.get("exemplar_answer"),
            coach_note=coach_note_full,
        )
        await self.eval_repo.create(evaluation_model)

        # 2.5 Update matching claims in Candidate Evidence Graph
        try:
            from backend.repositories.claim_repository import ClaimRepository
            claim_repo = ClaimRepository(self.session)
            matching_claims = await claim_repo.find_matching_claims(
                session_obj.candidate_id, current_q.topic
            )
            overall_score = float(eval_data.get("overall_score", 7.0))
            for c in matching_claims:
                c.probe_count += 1
                if overall_score >= 7.0:
                    c.verification_status = "VERIFIED"
                elif overall_score >= 4.5:
                    c.verification_status = "PROBED"
                else:
                    c.verification_status = "CONTESTED"

                # Bayesian update on confidence
                c.confidence_score = round(min(0.98, max(0.2, (c.confidence_score + (overall_score / 10.0)) / 2.0)), 2)

                quotes = list(c.verified_quotes or [])
                snippet = answer_text[:140].strip()
                if snippet and snippet not in quotes:
                    quotes.append(snippet)
                c.verified_quotes = quotes
        except Exception:
            pass

        # 2.6 Update Assessment Plan with Competency Evidence & Determine Progression
        spec = RoleSpecification(
            role_name=session_obj.target_role,
            target_roles=getattr(session_obj, "target_roles", None) or [session_obj.target_role],
            custom_role_description=getattr(session_obj, "custom_role_description", None),
        )
        blueprint = RoleIntelligenceService.build_competency_blueprint(spec)

        raw_plan = getattr(session_obj, "assessment_plan", None)
        if raw_plan and isinstance(raw_plan, dict):
            plan = AssessmentPlan.model_validate(raw_plan)
        else:
            plan = AssessmentPlanner.create_assessment_plan(
                blueprint,
                config=AssessmentPlanConfig(
                    min_questions=1,
                    target_questions=session_obj.target_question_count or 5,
                    safety_max_questions=15,
                    max_questions_per_stage=4,
                    max_followups_per_competency=2,
                    min_core_coverage_ratio=0.75,
                )
            )

        if getattr(current_q, "target_competency", None):
            matched_id = None
            for comp in blueprint.competencies:
                if comp.name == current_q.target_competency or comp.identifier == current_q.target_competency:
                    matched_id = comp.identifier
                    break
            if matched_id:
                plan.current_competency_id = matched_id
        if not plan.current_competency_id and plan.competency_evidence:
            plan.current_competency_id = list(plan.competency_evidence.keys())[0]

        # Classify candidate answer to detect contradictions, evasion, ambiguity, and depth
        prev_answers = [
            q.answer.answer_text for q in (session_obj.questions or [])
            if q.answer and q.id != current_q.id and q.answer.answer_text
        ]
        from ai.interview_engine.answer_classifier import (
            classify_candidate_answer,
            determine_interviewer_action,
            AnswerClassification,
            InterviewerAction,
        )
        classification, diag_reason, class_meta = classify_candidate_answer(
            eval_data=eval_data,
            candidate_answer=answer_text,
            question_text=current_q.question_text,
            previous_answers=prev_answers,
        )

        is_followup_needed, is_interview_completed, status_reason = AssessmentPlanner.record_turn_and_progress(
            plan=plan,
            blueprint=blueprint,
            eval_data=eval_data,
            question_text=current_q.question_text,
            is_contradictory=(classification == AnswerClassification.CONTRADICTORY),
        )

        active_record = plan.competency_evidence.get(plan.current_competency_id)
        active_status = active_record.coverage_status.value if active_record else "PARTIALLY_ASSESSED"

        # 2.7 Update Candidate Longitudinal Skill State with Interview Evidence
        diagnostic_evidence = None
        try:
            assessed_skill_key = getattr(current_q, "target_competency", None) or current_q.topic
            skill_id, is_canonical = normalize_skill(
                assessed_skill_key, current_q.category, current_q.expected_concepts
            )
            turn_score = float(eval_data.get("overall_score", 5.0))
            existing_skill = await self.skill_state_repo.get_by_candidate_and_skill(
                session_obj.candidate_id, skill_id
            )

            # Detect failure types and shortcomings from evaluation
            missing_concepts = eval_data.get("missing_concepts", []) or []
            weaknesses = eval_data.get("weaknesses", []) or []
            detected_failures = []
            if turn_score < 6.5 or missing_concepts or weaknesses:
                if missing_concepts:
                    detected_failures.append("MISSING_CONCEPTUAL_MODEL")
                    for mc in missing_concepts:
                        clean_mc = mc.strip().replace(" ", "_")
                        if clean_mc and f"CONCEPT_GAP:{clean_mc}" not in detected_failures:
                            detected_failures.append(f"CONCEPT_GAP:{clean_mc}")
                if any("shallow" in w.lower() or "pattern" in w.lower() or "superficial" in w.lower() for w in weaknesses):
                    detected_failures.append("SURFACE_PATTERN_DEPENDENCE")
                elif "SURFACE_PATTERN_DEPENDENCE" not in detected_failures and turn_score < 5.0:
                    detected_failures.append("SURFACE_PATTERN_DEPENDENCE")

            if existing_skill:
                # Evidence-based mastery update:
                # Credit strictly for demonstrated concepts without automatically zeroing out partial credit.
                # Incorrect answers with zero concepts or refusals receive strictly 0.0.
                has_demonstrated = bool(
                    eval_data.get("matched_concepts")
                    or (eval_data.get("coverage_ratio", 0.0) > 0.0)
                    or (turn_score > 0.0 and len(eval_data.get("missing_concepts", [])) < len(current_q.expected_concepts or []))
                )
                if existing_skill.total_attempts == 0:
                    new_mastery = round(turn_score / 10.0, 3) if (has_demonstrated and turn_score > 0.0) else 0.0
                else:
                    if has_demonstrated and turn_score > 0.0:
                        new_mastery = round(existing_skill.mastery_estimate * 0.6 + (turn_score / 10.0) * 0.4, 3)
                    else:
                        new_mastery = round(existing_skill.mastery_estimate * 0.70, 3)
                new_uncertainty = max(0.2, round(existing_skill.mastery_uncertainty * 0.85, 3))

                # Preserve transfer-derived achievements: an interview observation cannot downgrade L2-L5
                # Crucial invariant: Interview performance alone must NOT produce L5 Independent Transfer
                highest_lvl = existing_skill.highest_transfer_level
                if highest_lvl == "L0_RECALL" and turn_score >= 7.0:
                    highest_lvl = "L1_DIRECT_APPLICATION"

                # Merge failure modes non-destructively
                merged_failures = list(existing_skill.recurring_failure_types or [])
                for f in detected_failures:
                    if f not in merged_failures:
                        merged_failures.append(f)

                existing_skill.mastery_estimate = new_mastery
                existing_skill.mastery_uncertainty = new_uncertainty
                existing_skill.highest_transfer_level = highest_lvl
                existing_skill.recurring_failure_types = merged_failures
                existing_skill.total_attempts += 1
                existing_skill.last_assessed_at = datetime.utcnow()
            else:
                has_demonstrated = bool(
                    eval_data.get("matched_concepts")
                    or (eval_data.get("coverage_ratio", 0.0) > 0.0)
                    or (turn_score > 0.0 and len(eval_data.get("missing_concepts", [])) < len(current_q.expected_concepts or []))
                )
                highest_lvl = "L1_DIRECT_APPLICATION" if turn_score >= 7.0 else "L0_RECALL"
                mastery_val = round(turn_score / 10.0, 3) if (has_demonstrated and turn_score > 0.0) else 0.0
                existing_skill = await self.skill_state_repo.upsert_skill_state(
                    candidate_id=session_obj.candidate_id,
                    skill_name=skill_id,
                    mastery_estimate=mastery_val,
                    mastery_uncertainty=0.70,
                    highest_transfer_level=highest_lvl,
                    assistance_dependency_index=0.0,
                    recurring_failure_types=detected_failures,
                    assessed_at=datetime.utcnow(),
                )

            # Determine mastery signal and recommended followup depth deterministically
            if turn_score < 5.0 or (missing_concepts and len(missing_concepts) > 0):
                mastery_signal = "WEAKNESS"
                rec_depth = "FOLLOW_UP" if is_followup_needed else "PRACTICAL"
            elif turn_score < 7.0:
                mastery_signal = "DEVELOPING"
                rec_depth = "PRACTICAL"
            elif turn_score < 8.5:
                mastery_signal = "PROFICIENT"
                rec_depth = "PRACTICAL"
            else:
                mastery_signal = "MASTERY"
                rec_depth = "ADVANCED"

            confidence_val = round(1.0 - (existing_skill.mastery_uncertainty if existing_skill else 0.70), 2)
            diagnostic_evidence = InterviewDiagnosticEvidence(
                candidate_id=session_obj.candidate_id,
                session_id=session_obj.id,
                question_id=current_q.id,
                competency=getattr(current_q, "target_competency", None) or current_q.topic,
                skill=skill_id,
                score=turn_score,
                mastery_signal=mastery_signal,
                strengths=eval_data.get("strengths") or [],
                weaknesses=weaknesses,
                missing_concepts=missing_concepts,
                misconceptions=[w for w in weaknesses if "misconcept" in w.lower() or "incorrect" in w.lower()],
                evidence=[
                    EvidenceItem(
                        claim=e.get("claim", "") if isinstance(e, dict) else str(e),
                        basis=e.get("basis", "From response") if isinstance(e, dict) else "From response"
                    )
                    for e in (eval_data.get("evidence") or [])
                ],
                confidence=max(0.2, min(0.99, confidence_val)),
                recommended_followup_depth=rec_depth,
            )
        except Exception as e:
            logger.warning(f"Error updating candidate skill state from interview turn: {e}")

        # 3. Check progression
        curr_idx = current_q.question_index
        next_q_resp = None
        is_completed = False
        role_comp_profile_dict = None

        t_qgen_duration = 0.0
        if not is_interview_completed:
            t_qgen_start = time.perf_counter()
            # Generate Next Question
            session_obj.current_question_index = curr_idx + 1
            profile_summary, rag_context, cand_claims, candidate_dossier = await self._get_resume_context(
                session_obj, topic_hint=current_q.topic
            )
            prev_questions = [q.question_text for q in (session_obj.questions or [])]

            current_comp_name = getattr(current_q, "target_competency", None) or current_q.topic
            next_comp_id = plan.current_competency_id
            next_comp_obj = blueprint.get_competency(next_comp_id) if next_comp_id else None
            next_comp_name = next_comp_obj.name if next_comp_obj else (next_comp_id or current_comp_name)

            target_probe_concept = None
            if eval_data.get("missing_concepts"):
                target_probe_concept = eval_data["missing_concepts"][0]
            elif current_q.expected_concepts:
                target_probe_concept = current_q.expected_concepts[-1]

            action, action_directive, conversational_lead_in, transition_rationale = determine_interviewer_action(
                classification=classification,
                is_competency_sufficient=(not is_followup_needed),
                current_competency=current_comp_name,
                next_competency=next_comp_name,
                target_concept=target_probe_concept,
                contradiction_detail=class_meta.get("contradiction_detail"),
                sufficiency_reason=status_reason,
            )

            cand_context = {
                "profile_summary": profile_summary,
                "claims": cand_claims,
            }
            next_q_plan = AssessmentPlanner.create_question_plan(
                plan=plan,
                blueprint=blueprint,
                candidate_context=cand_context,
                difficulty_level=session_obj.difficulty_level,
                interviewer_action=action.value,
                answer_classification=classification.value,
                action_directive=action_directive,
                transition_rationale=transition_rationale,
                preceding_competency=current_comp_name,
            )

            next_q_data = await self.question_generator.generate_question(
                target_role=session_obj.target_role,
                interview_type=session_obj.interview_type,
                difficulty_level=session_obj.difficulty_level,
                turn_number=curr_idx + 1,
                total_questions=plan.config.target_questions,
                resume_summary=profile_summary,
                rag_context=rag_context,
                previous_questions=prev_questions,
                last_question=current_q.question_text,
                last_answer=answer_text,
                last_score=eval_data.get("overall_score"),
                last_missing_concepts=eval_data.get("missing_concepts", []),
                candidate_claims=cand_claims,
                candidate_dossier=candidate_dossier,
                question_plan=next_q_plan,
            )

            lead_in_val = conversational_lead_in

            from ai.interview_engine.question_sanitizer import (
                sanitize_and_enforce_single_question,
                validate_question_semantics,
                validate_substantive_question_focus,
                validate_question_competency_alignment,
                CompetencyAlignmentError,
            )
            raw_q = next_q_data.get("question") or next_q_data.get("question_text", "")
            clean_next_q = sanitize_and_enforce_single_question(raw_q)
            is_valid, validation_err = validate_question_semantics(clean_next_q)
            is_focused, focus_err = validate_substantive_question_focus(clean_next_q)
            is_aligned, align_err = validate_question_competency_alignment(
                question_text=clean_next_q,
                target_competency=next_q_plan.competency_name,
                expected_concepts=next_q_plan.expected_concepts,
                core_invariants=next_q_plan.core_invariants,
                preceding_competency=current_comp_name,
            )
            if not is_valid or not is_focused or not is_aligned:
                reasons = []
                if not is_valid:
                    reasons.append(f"Semantics: {validation_err}")
                if not is_focused:
                    reasons.append(f"Focus: {focus_err}")
                if not is_aligned:
                    reasons.append(f"Competency Alignment: {align_err}")
                logger.warning(
                    f"Generated question failed validation ({' | '.join(reasons)}); "
                    f"deploying verified QuestionBankService fallback."
                )
                from ai.interview_engine.question_bank import QuestionBankService
                try:
                    bank_fallback = QuestionBankService.find_question(
                        stage_index=next_q_plan.stage_index,
                        target_role=session_obj.target_role,
                        resume_summary=f"{profile_summary} {rag_context}",
                        asked_questions=prev_questions,
                        difficulty=session_obj.difficulty_level,
                        target_competency=next_q_plan.competency_name,
                        expected_concepts=next_q_plan.expected_concepts,
                        is_followup=next_q_plan.is_followup,
                        followup_concept=next_q_plan.followup_target_concept,
                        depth_level=next_q_plan.depth_level,
                    )
                    clean_next_q = sanitize_and_enforce_single_question(bank_fallback.get("question", ""))
                    next_q_data["topic"] = bank_fallback.get("topic") or next_q_plan.competency_name
                    next_q_data["category"] = bank_fallback.get("category", "technical")
                    next_q_data["expected_concepts"] = bank_fallback.get("expected_concepts") or next_q_plan.expected_concepts
                except Exception as fb_err:
                    raise HTTPException(
                        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                        detail=f"Unable to generate or retrieve a valid question aligned with canonical target competency '{next_q_plan.competency_name}': {fb_err}"
                    )

            from ai.evaluation_engine.rubrics import get_rubric_for_question
            next_rubric = get_rubric_for_question(
                topic=next_q_data["topic"],
                question_text=clean_next_q,
                expected_concepts=next_q_data["expected_concepts"],
                interview_type=session_obj.interview_type,
            )
            next_q_plan.rubric_snapshot = next_rubric.model_dump()
            next_expected_concepts = next_q_data.get("expected_concepts") or next_q_plan.expected_concepts

            next_question_model = QuestionModel(
                id=str(uuid.uuid4()),
                session_id=session_obj.id,
                question_index=curr_idx + 1,
                question_text=clean_next_q,
                category=next_q_data["category"],
                topic=next_q_data["topic"],
                difficulty=next_q_data["difficulty"],
                stage_name=next_q_plan.stage_name,
                stage_index=next_q_plan.stage_index,
                target_competency=next_q_plan.competency_name,
                assessment_objective=next_q_plan.objective,
                is_followup=next_q_plan.is_followup,
                question_plan=next_q_plan.model_dump(),
                resume_evidence=next_q_data["resume_evidence"],
                expected_concepts=next_expected_concepts,
                coach_lead_in=lead_in_val,
            )
            created_next_q = await self.question_repo.create(next_question_model)
            if session_obj.questions is not None:
                session_obj.questions.append(created_next_q)
            next_q_resp = self._to_question_response(created_next_q, total_questions=plan.config.target_questions)
            t_qgen_duration = round(time.perf_counter() - t_qgen_start, 3)
        else:
            # Interview Ended (evidence satisfied, candidate requested, or emergency safeguard halted)
            is_safeguard_halt = getattr(plan, "is_halted_by_safeguard", False) or (
                plan.completion_reason in [
                    InterviewCompletionReason.OPERATIONAL_SAFETY_CEILING.value,
                    InterviewCompletionReason.SESSION_TIMEOUT.value,
                    InterviewCompletionReason.INFERENCE_BUDGET_EXCEEDED.value,
                    InterviewCompletionReason.LOOP_DETECTED.value,
                    InterviewCompletionReason.SESSION_ABORTED.value,
                ]
            )

            if is_safeguard_halt:
                is_completed = False
                session_obj.status = "INCOMPLETE"
                session_obj.completion_reason = plan.completion_reason
                session_obj.evidence_coverage_ratio = plan.evidence_coverage_ratio
                session_obj.end_time = datetime.utcnow()
                profile_model = AssessmentPlanner.compile_role_competency_profile(plan)
                role_comp_profile_dict = profile_model.model_dump()
                await self._generate_and_save_final_report(
                    session_obj,
                    role_comp_profile=role_comp_profile_dict,
                    is_complete=False,
                    halt_reason=plan.completion_reason,
                )
                await self._reconcile_session_skill_states(session_obj)
            else:
                is_completed = True
                session_obj.status = "COMPLETED"
                session_obj.completion_reason = plan.completion_reason or "COMPETENCY_COVERAGE_SATISFIED"
                session_obj.evidence_coverage_ratio = plan.evidence_coverage_ratio
                session_obj.end_time = datetime.utcnow()
                profile_model = AssessmentPlanner.compile_role_competency_profile(plan)
                role_comp_profile_dict = profile_model.model_dump()
                await self._generate_and_save_final_report(session_obj, role_comp_profile=role_comp_profile_dict, is_complete=True)
                await self._reconcile_session_skill_states(session_obj)

        eval_resp = self._to_evaluation_response(evaluation_model, diagnostic_evidence=diagnostic_evidence)
        session_obj.assessment_plan = plan.model_dump()
        session_obj.competency_state = {c_id: rec.model_dump() for c_id, rec in plan.competency_evidence.items()}
        
        t_db_start = time.perf_counter()
        await self.session.flush()
        t_db_duration = round(time.perf_counter() - t_db_start, 3)
        t_total_turn = round(time.perf_counter() - t_turn_start, 3)

        timing_breakdown = {
            "t_eval_seconds": t_eval_duration,
            "t_qgen_seconds": t_qgen_duration,
            "t_db_seconds": t_db_duration,
            "t_total_seconds": t_total_turn,
        }
        logger.info(f"Interview Turn {curr_idx} latency breakdown: {timing_breakdown}")

        assessed_competencies_count = len([r for r in plan.competency_evidence.values() if r.questions_asked > 0])
        total_competencies_count = len(blueprint.competencies)

        return TurnAnswerResultResponse(
            evaluation=eval_resp,
            next_question=next_q_resp,
            is_completed=is_completed,
            current_question_index=session_obj.current_question_index,
            total_questions=max(session_obj.current_question_index, total_competencies_count),
            active_competency_status=active_status,
            role_competency_profile=role_comp_profile_dict,
            is_followup_probe=is_followup_needed,
            diagnostic_evidence=diagnostic_evidence,
            completion_reason=getattr(session_obj, "completion_reason", None),
            evidence_coverage_ratio=plan.evidence_coverage_ratio,
            competencies_assessed_count=assessed_competencies_count,
            total_competencies_count=total_competencies_count,
            timing_breakdown=timing_breakdown,
        )

    async def _reconcile_session_skill_states(self, session_obj: InterviewSessionModel) -> None:
        """
        Guarantees Research Invariant #1: Interview evaluation must influence candidate skill state.
        Ensures all evaluated question turns in the session have their performance and diagnosed
        conceptual shortcomings reconciled into CandidateSkillStateModel.
        """
        for q in (session_obj.questions or []):
            if q.answer and q.answer.evaluation:
                ev = q.answer.evaluation
                turn_score = float(ev.overall_score)
                assessed_skill_key = getattr(q, "target_competency", None) or q.topic
                skill_id, is_canonical = normalize_skill(
                    assessed_skill_key, q.category, q.expected_concepts
                )
                missing_concepts = ev.missing_concepts or []
                weaknesses = ev.weaknesses or []
                detected_failures = []
                if turn_score < 6.5 or missing_concepts or weaknesses:
                    if missing_concepts:
                        detected_failures.append("MISSING_CONCEPTUAL_MODEL")
                        for mc in missing_concepts:
                            clean_mc = mc.strip().replace(" ", "_")
                            if clean_mc and f"CONCEPT_GAP:{clean_mc}" not in detected_failures:
                                detected_failures.append(f"CONCEPT_GAP:{clean_mc}")
                    if any("shallow" in w.lower() or "pattern" in w.lower() or "superficial" in w.lower() for w in weaknesses):
                        detected_failures.append("SURFACE_PATTERN_DEPENDENCE")
                    elif "SURFACE_PATTERN_DEPENDENCE" not in detected_failures and turn_score < 5.0:
                        detected_failures.append("SURFACE_PATTERN_DEPENDENCE")

                existing_skill = await self.skill_state_repo.get_by_candidate_and_skill(
                    session_obj.candidate_id, skill_id
                )
                if not existing_skill:
                    highest_lvl = "L1_DIRECT_APPLICATION" if turn_score >= 7.0 else "L0_RECALL"
                    await self.skill_state_repo.upsert_skill_state(
                        candidate_id=session_obj.candidate_id,
                        skill_name=skill_id,
                        mastery_estimate=round(turn_score / 10.0, 3),
                        mastery_uncertainty=0.70,
                        highest_transfer_level=highest_lvl,
                        assistance_dependency_index=0.0,
                        recurring_failure_types=detected_failures,
                        assessed_at=datetime.utcnow(),
                    )

    async def complete_session(self, session_id: str, reason: str = "CANDIDATE_REQUESTED") -> InterviewSessionResponse:
        session_obj = await self.session_repo.get_with_full_history(session_id)
        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session '{session_id}' not found."
            )

        if session_obj.status != "COMPLETED":
            session_obj.status = "COMPLETED"
            session_obj.completion_reason = reason
            session_obj.end_time = datetime.utcnow()

            role_comp_profile_dict = None
            if session_obj.assessment_plan and isinstance(session_obj.assessment_plan, dict):
                try:
                    plan = AssessmentPlan.model_validate(session_obj.assessment_plan)
                    plan.is_completed = True
                    plan.completion_reason = reason
                    profile_model = AssessmentPlanner.compile_role_competency_profile(plan)
                    role_comp_profile_dict = profile_model.model_dump()
                    session_obj.evidence_coverage_ratio = plan.evidence_coverage_ratio
                    session_obj.assessment_plan = plan.model_dump()
                except Exception as e:
                    logger.warning(f"Error compiling competency profile on complete: {e}")

            await self._reconcile_session_skill_states(session_obj)
            await self._generate_and_save_final_report(session_obj, role_comp_profile=role_comp_profile_dict)
            await self.session.flush()

        loaded = await self.session_repo.get_with_full_history(session_id)
        return self._to_session_response(loaded or session_obj)

    async def get_session(self, session_id: str) -> InterviewSessionResponse:
        session_obj = await self.session_repo.get_with_full_history(session_id)
        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session '{session_id}' not found."
            )
        return self._to_session_response(session_obj)

    async def list_candidate_interviews(self, candidate_id: str) -> List[InterviewSessionResponse]:
        sessions = await self.session_repo.list_by_candidate(candidate_id)
        return [self._to_session_response(s) for s in sessions]

    async def _get_resume_context(
        self, session_obj: InterviewSessionModel, topic_hint: Optional[str] = None
    ) -> tuple[str, str, List[str], Optional[Dict[str, Any]]]:
        """Retrieves candidate profile summary, RAG context, claims, and autonomous web-researched dossier."""
        query_term = (topic_hint or session_obj.target_role or "general").strip().lower()
        cache_key = f"{session_obj.id}:{session_obj.candidate_id}:{query_term}"
        if cache_key in _RESUME_CONTEXT_CACHE:
            return _RESUME_CONTEXT_CACHE[cache_key]

        profile_summary = ""
        rag_context = ""
        cand_claims = []
        dossier = None
        cand_id_str = str(session_obj.candidate_id)

        try:
            from backend.repositories.claim_repository import ClaimRepository
            claim_repo = ClaimRepository(self.session)
            claims_db = await claim_repo.get_by_candidate(cand_id_str)
            cand_claims = [c.claim_text for c in claims_db if c.claim_text]
        except Exception:
            cand_claims = []

        try:
            profile_model = await self.candidate_repo.get_profile(cand_id_str)
            if profile_model and profile_model.profile_data:
                pd = dict(profile_model.profile_data)
                skills = ", ".join(s.get("name", "") for s in pd.get("skills", []))
                tech = ", ".join(pd.get("technologies", []))
                exp = f"{pd.get('total_years_experience', 0.0)} years"
                edu = ", ".join(f"{e.get('degree', '')} in {e.get('field_of_study', '')} at {e.get('institution', '')}" for e in pd.get("education", []))
                seniority = pd.get("seniority_level", "Fresher / Student")
                
                proj_list = pd.get("projects", [])
                proj_str = ""
                if proj_list:
                    proj_names = [
                        f"{p.get('name') or p.get('title', '')} ({p.get('description', '')[:70]})"
                        for p in proj_list[:3]
                        if p.get('name') or p.get('title')
                    ]
                    if proj_names:
                        proj_str = "\nProjects: " + "; ".join(proj_names)

                profile_summary = (
                    f"Candidate Level: {seniority}\n"
                    f"Target Role: {session_obj.target_role}\n"
                    f"Education: {edu}\n"
                    f"Skills: {skills}\n"
                    f"Technologies: {tech}\n"
                    f"Experience: {exp}"
                    f"{proj_str}"
                )

                dossier = pd.get("personalized_dossier")
                if not dossier:
                    # Dynamically synthesize on-the-fly from live web
                    from ai.interview_engine.personalized_skill_synthesizer import PersonalizedSkillSynthesizer
                    cand_obj = await self.candidate_repo.get_by_id(cand_id_str)
                    cand_name = cand_obj.full_name if cand_obj else "Candidate"
                    extracted_skills = profile_model.skills_flat or [s.get("name") for s in pd.get("skills", [])]
                    dossier = await PersonalizedSkillSynthesizer.synthesize_candidate_dossier(
                        candidate_id=cand_id_str,
                        candidate_name=cand_name,
                        target_role=session_obj.target_role,
                        extracted_skills=extracted_skills,
                        projects=pd.get("projects", []),
                    )
                    pd["personalized_dossier"] = dossier
                    profile_model.profile_data = pd
                    await self.session.flush()

            rag_res = await self.rag_service.query_candidate_memory(cand_id_str, query_term, top_k=2)
            if rag_res and rag_res.results:
                rag_context = "\n---\n".join(r.content for r in rag_res.results)
        except Exception as e:
            logger.warning(f"Error resolving resume context and dossier: {e}")

        result = (profile_summary, rag_context, cand_claims, dossier)
        _RESUME_CONTEXT_CACHE[cache_key] = result
        return result

    async def _generate_and_save_final_report(
        self,
        session_obj: InterviewSessionModel,
        role_comp_profile: Optional[Dict[str, Any]] = None,
        is_complete: bool = True,
        halt_reason: Optional[str] = None,
    ):
        """Calculates deterministic final report and persists SessionReportModel."""
        evals = await self.eval_repo.list_by_session(session_obj.id)
        eval_dicts = [
            {
                "overall_score": e.overall_score,
                "correctness": e.correctness,
                "completeness": e.completeness,
                "relevance": e.relevance,
                "technical_depth": e.technical_depth,
                "reasoning": e.reasoning,
                "strengths": e.strengths or [],
                "weaknesses": e.weaknesses or [],
                "recommendations": e.recommendations or [],
            }
            for e in evals
        ]

        report_data = ScoreAggregator.aggregate_session_report(
            evaluations=eval_dicts,
            interview_type=session_obj.interview_type,
        )

        if not is_complete:
            halt_msg = f"Assessment incomplete: Session halted by operational safeguard ({halt_reason or 'SAFEGUARD_HALTED'}). Outstanding competencies remain unassessed."
            if halt_msg not in report_data.get("summary_weaknesses", []):
                report_data.setdefault("summary_weaknesses", []).insert(0, halt_msg)

        # Attempt to synthesize role competency profile if not provided
        if not role_comp_profile and session_obj.assessment_plan and isinstance(session_obj.assessment_plan, dict):
            try:
                p_obj = AssessmentPlan.model_validate(session_obj.assessment_plan)
                role_comp_profile = AssessmentPlanner.compile_role_competency_profile(p_obj).model_dump()
            except Exception:
                pass

        if not role_comp_profile and (session_obj.questions or []):
            comp_records = []
            for q in session_obj.questions:
                if q.answer and q.answer.evaluation:
                    ev = q.answer.evaluation
                    comp_name = getattr(q, "target_competency", None) or q.topic or "Engineering Invariants"
                    comp_records.append({
                        "competency_id": q.id,
                        "name": comp_name,
                        "description": f"Evaluation evidence for {comp_name}",
                        "importance": "IMPORTANT",
                        "coverage_status": "SUFFICIENT_EVIDENCE" if ev.overall_score >= 7.0 else "PARTIALLY_ASSESSED",
                        "average_score": ev.overall_score,
                        "demonstrated_concepts": ev.strengths or [],
                        "missing_concepts": ev.missing_concepts or [],
                    })
            if comp_records:
                role_comp_profile = {
                    "role_name": session_obj.target_role or "Software Engineer",
                    "overall_fit_score": report_data.get("final_score", 7.0),
                    "competencies": comp_records,
                }

        # Leverage Primary AI Provider (NVIDIA NIM) for high-leverage Final Report Executive Synthesis
        try:
            from backend.infrastructure.ai.factory import get_llm_provider
            from backend.domain.ai.interfaces import LLMRequest
            major_provider = get_llm_provider(task="major")
            if getattr(major_provider, "provider_name", "") != "mock":
                prompt = (
                    f"Synthesize an executive summary for this candidate's {session_obj.interview_type} interview for {session_obj.target_role}.\n"
                    f"Final Overall Score: {report_data['final_score']}/10.\n"
                    f"Weaknesses identified: {report_data['summary_weaknesses']}.\n"
                    f"Strengths identified: {report_data['summary_strengths']}.\n"
                    "Return JSON with: summary_strengths (list of 3 items), summary_weaknesses (list of 3 items), key_recommendations (list of 3 items)."
                )
                req = LLMRequest(
                    system_prompt="You are an expert executive engineering hiring panel director. Be analytical, encouraging, and specific.",
                    user_prompt=prompt,
                    response_json=True,
                    max_tokens=600,
                    metadata={"task_type": "learning_recommendations"},
                )
                res = await major_provider.generate(req)
                if res.raw_json:
                    if "summary_strengths" in res.raw_json and res.raw_json["summary_strengths"]:
                        report_data["summary_strengths"] = res.raw_json["summary_strengths"]
                    if "summary_weaknesses" in res.raw_json and res.raw_json["summary_weaknesses"]:
                        report_data["summary_weaknesses"] = res.raw_json["summary_weaknesses"]
                    if "key_recommendations" in res.raw_json and res.raw_json["key_recommendations"]:
                        report_data["key_recommendations"] = res.raw_json["key_recommendations"]
        except Exception:
            pass  # Fallback to deterministic aggregated report without disruption

        existing_report = await self.report_repo.get_by_session(session_obj.id)
        if existing_report:
            existing_report.final_score = report_data["final_score"]
            existing_report.technical_score = report_data["technical_score"]
            existing_report.behavioral_score = report_data["behavioral_score"]
            existing_report.communication_score = report_data["communication_score"]
            existing_report.summary_strengths = report_data["summary_strengths"]
            existing_report.summary_weaknesses = report_data["summary_weaknesses"]
            existing_report.key_recommendations = report_data["key_recommendations"]
            if role_comp_profile:
                existing_report.role_competency_profile = role_comp_profile
            session_obj.report = existing_report
        else:
            report_model = SessionReportModel(
                id=str(uuid.uuid4()),
                session_id=session_obj.id,
                session=session_obj,
                final_score=report_data["final_score"],
                technical_score=report_data["technical_score"],
                behavioral_score=report_data["behavioral_score"],
                communication_score=report_data["communication_score"],
                summary_strengths=report_data["summary_strengths"],
                summary_weaknesses=report_data["summary_weaknesses"],
                key_recommendations=report_data["key_recommendations"],
                role_competency_profile=role_comp_profile,
            )
            session_obj.report = report_model
            self.session.add(report_model)

    async def get_coach_hint(
        self, session_id: str, partial_answer: Optional[str] = None
    ) -> CoachHintResponse:
        session_obj = await self.session_repo.get_with_full_history(session_id)
        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session '{session_id}' not found."
            )

        # Find current active unanswered question
        active_q = None
        for q in session_obj.questions:
            if not q.answer:
                active_q = q
                break

        if not active_q:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No active unanswered question to provide coaching hints for."
            )

        hint_data = await self.question_generator.generate_coach_hint(
            question_text=active_q.question_text,
            topic=active_q.topic,
            expected_concepts=active_q.expected_concepts or [],
            partial_answer=partial_answer,
        )

        return CoachHintResponse(
            question_id=active_q.id,
            hint_text=hint_data["hint_text"],
            pedagogical_nudge=hint_data["pedagogical_nudge"],
            key_concept_to_consider=hint_data["key_concept_to_consider"],
        )

    async def get_session_weaknesses(
        self, session_id: str, eligibility_threshold: float = 7.0
    ) -> InterviewWeaknessesResponse:
        """
        Extracts actionable candidate weaknesses and conceptual gaps from an interview session.
        Uses evaluation scores, concrete rubric weaknesses, and missing concepts to synthesize
        coaching-ready TrainingContext specifications for the Transfer-Aware Coaching subsystem.
        """
        session_obj = await self.session_repo.get_with_full_history(session_id)
        if not session_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Interview session '{session_id}' not found."
            )

        weakness_items: List[WeaknessRemediationItem] = []
        for q in (session_obj.questions or []):
            if q.answer and q.answer.evaluation:
                ev = q.answer.evaluation
                score = float(ev.overall_score)
                has_missing_concepts = bool(ev.missing_concepts and len(ev.missing_concepts) > 0)
                has_weaknesses = bool(ev.weaknesses and len(ev.weaknesses) > 0)

                # Eligibility considers score deficit AND concrete evaluation evidence
                is_weak = score < eligibility_threshold or has_missing_concepts or has_weaknesses
                if is_weak:
                    skill_id, is_canonical = normalize_skill(q.topic, q.category, q.expected_concepts)
                    core_invariants = extract_core_invariants(q.expected_concepts, q.topic, skill_id)

                    training_ctx = {
                        "task_id": f"interview_{q.id}",
                        "question_text": q.question_text,
                        "skill_id": skill_id,
                        "core_invariants": core_invariants,
                        "base_surface_context": q.topic or "Software Architecture",
                        "base_expected_concepts": q.expected_concepts or [q.topic or "Engineering Invariants"],
                        "topic": q.topic or "Engineering Invariants",
                    }

                    item = WeaknessRemediationItem(
                        question_id=q.id,
                        topic=q.topic,
                        category=q.category,
                        skill_id=skill_id,
                        is_canonical_skill=is_canonical,
                        overall_score=score,
                        weaknesses=ev.weaknesses or [],
                        missing_concepts=ev.missing_concepts or [],
                        recommendations=ev.recommendations or [],
                        training_context=training_ctx,
                    )
                    weakness_items.append(item)

        # Sort by overall score ascending (most critical weaknesses first)
        weakness_items.sort(key=lambda w: w.overall_score)

        return InterviewWeaknessesResponse(
            session_id=session_obj.id,
            candidate_id=session_obj.candidate_id,
            total_weaknesses=len(weakness_items),
            weaknesses=weakness_items,
        )

