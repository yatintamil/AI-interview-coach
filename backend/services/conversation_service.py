"""
Conversation Service and Coordinator.
Orchestrates conversation lifecycles, persists dialogue history, detects intents,
and delegates domain requests to existing domain engines without state contamination.
"""

import uuid
import asyncio
import logging
from typing import Optional, List, Dict, Any, Union, Tuple
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.repositories.conversation_repository import ConversationRepository
from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.skill_state_repository import CandidateSkillStateRepository
from backend.schemas.chat import (
    CreateConversationRequest,
    RenameConversationRequest,
    SendMessageRequest,
    ConversationDTO,
    ConversationDetailDTO,
    ConversationMessageDTO,
    SendMessageResponse,
    ChatIntent,
    ChatRole,
)
from backend.services.intent_coordinator import IntentCoordinator
from backend.infrastructure.ai.factory import get_llm_provider
from backend.domain.ai.interfaces import LLMRequest

logger = logging.getLogger(__name__)


class ConversationService:
    """
    Thin, cohesive service managing conversation persistence and coordinating
    delegated domain actions (Interview, Coaching, Transfer, Roadmap).
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.convo_repo = ConversationRepository(session)
        self.candidate_repo = CandidateRepository(session)
        self.skill_state_repo = CandidateSkillStateRepository(session)
        self.intent_coordinator = IntentCoordinator()

    async def create_conversation(self, payload: CreateConversationRequest) -> ConversationDTO:
        """Creates a new conversation thread, validating candidate ownership if provided."""
        if payload.candidate_id:
            candidate = await self.candidate_repo.get(payload.candidate_id)
            if not candidate:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Candidate with ID '{payload.candidate_id}' not found.",
                )

        convo = await self.convo_repo.create_conversation(
            candidate_id=payload.candidate_id,
            title=payload.title,
            metadata=payload.metadata,
        )
        await self.session.commit()
        return ConversationDTO.model_validate(convo)

    async def list_conversations(
        self, candidate_id: Optional[str] = None, skip: int = 0, limit: int = 50
    ) -> List[ConversationDTO]:
        """Lists conversations, optionally filtered by candidate ID."""
        if candidate_id:
            convos = await self.convo_repo.list_by_candidate(candidate_id, skip=skip, limit=limit)
        else:
            convos = await self.convo_repo.list_all(skip=skip, limit=limit)

        dtos = []
        for c in convos:
            dto = ConversationDTO.model_validate(c)
            # Count messages safely if eagerly loaded in __dict__
            if "messages" in c.__dict__ and c.messages:
                dto.messages_count = len(c.messages)
            else:
                dto.messages_count = 0
            dtos.append(dto)
        return dtos

    async def get_conversation(
        self, conversation_id: str, candidate_id: Optional[str] = None
    ) -> ConversationDetailDTO:
        """
        Retrieves a conversation and all its messages.
        Enforces candidate ownership if candidate_id is specified.
        """
        convo = await self.convo_repo.get_with_messages(conversation_id)
        if not convo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

        if candidate_id and convo.candidate_id and str(convo.candidate_id) != str(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Conversation '{conversation_id}' does not belong to candidate '{candidate_id}'.",
            )

        return ConversationDetailDTO.model_validate(convo)

    async def rename_conversation(
        self, conversation_id: str, payload: RenameConversationRequest, candidate_id: Optional[str] = None
    ) -> ConversationDTO:
        """Renames a conversation title with ownership verification."""
        convo = await self.convo_repo.get(conversation_id)
        if not convo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

        if candidate_id and convo.candidate_id and str(convo.candidate_id) != str(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to rename conversation '{conversation_id}'.",
            )

        updated = await self.convo_repo.update_title(conversation_id, payload.title)
        await self.session.commit()
        return ConversationDTO.model_validate(updated)

    async def delete_conversation(
        self, conversation_id: str, candidate_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Deletes a conversation and cascades to all child messages."""
        convo = await self.convo_repo.get(conversation_id)
        if not convo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

        if candidate_id and convo.candidate_id and str(convo.candidate_id) != str(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to delete conversation '{conversation_id}'.",
            )

        await self.convo_repo.delete_conversation(conversation_id)
        await self.session.commit()
        return {"status": "success", "deleted_id": conversation_id}

    async def process_user_turn(
        self, conversation_id: str, payload: SendMessageRequest
    ) -> SendMessageResponse:
        """
        Coordinates a single user turn:
        1. Validates conversation and candidate ownership.
        2. Persists the incoming user message.
        3. Classifies intent using the IntentCoordinator.
        4. Delegates to the appropriate domain engine or conversational generator.
        5. Persists the assistant response (with structured ui_payload if generated).
        6. Guarantees normal conversation does NOT mutate candidate skill state.
        """
        convo = await self.convo_repo.get_with_messages(conversation_id)
        if not convo:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation '{conversation_id}' not found.",
            )

        effective_cand_id = payload.candidate_id or convo.candidate_id
        if payload.candidate_id and convo.candidate_id and str(convo.candidate_id) != str(payload.candidate_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Not authorized to post to conversation '{conversation_id}'.",
            )

        # Check if conversation is an AI Coaching Studio session
        is_coaching_studio = (
            (convo.metadata_ or {}).get("session_type") == "coaching_studio"
            or (payload.metadata or {}).get("session_type") == "coaching_studio"
        )
        if is_coaching_studio:
            from backend.services.coaching_tutor_service import CoachingTutorService
            tutor = CoachingTutorService(self.session)
            return await tutor.process_coaching_turn(
                conversation_id=conversation_id,
                user_message=payload.content,
                candidate_id=effective_cand_id,
                target_role=payload.target_role,
                focus_skill=payload.focus_skill,
                metadata=payload.metadata,
            )

        # 1. Detect Intent with contextual active_state if present
        active_state = (convo.metadata_ or {}).get("active_state") or (payload.metadata or {}).get("active_state")
        detected_intent = self.intent_coordinator.classify_intent(payload.content, active_state=active_state)

        # 2. Persist User Message
        user_msg = await self.convo_repo.add_message(
            conversation_id=conversation_id,
            role=ChatRole.USER.value,
            content=payload.content,
            message_type="text",
            intent=detected_intent.value,
        )

        # 3. Delegate to Domain Handler or Conversational Synthesis
        prior_msgs = [m for m in (convo.messages or []) if str(m.id) != str(user_msg.id)]
        assistant_content, ui_card, msg_type, is_fallback, provider_used = await self._dispatch_domain_intent(
            intent=detected_intent,
            user_message=payload.content,
            candidate_id=effective_cand_id,
            target_role=payload.target_role,
            focus_skill=payload.focus_skill,
            conversation_metadata=convo.metadata_ or {},
            prior_messages=prior_msgs,
        )

        # 4. Persist Assistant Response
        assistant_msg = await self.convo_repo.add_message(
            conversation_id=conversation_id,
            role=ChatRole.ASSISTANT.value,
            content=assistant_content,
            message_type=msg_type,
            ui_payload=ui_card,
            intent=detected_intent.value,
        )

        await self.session.commit()

        return SendMessageResponse(
            conversation_id=conversation_id,
            user_message=ConversationMessageDTO.model_validate(user_msg),
            assistant_message=ConversationMessageDTO.model_validate(assistant_msg),
            detected_intent=detected_intent,
            is_fallback=is_fallback,
            provider_used=provider_used,
        )

    async def _dispatch_domain_intent(
        self,
        intent: ChatIntent,
        user_message: str,
        candidate_id: Optional[str],
        target_role: Optional[str],
        focus_skill: Optional[str],
        conversation_metadata: Dict[str, Any],
        prior_messages: Optional[List[Any]] = None,
    ) -> Tuple[str, Optional[Dict[str, Any]], str, bool, str]:
        """
        Dispatches intent to existing domain services with multi-turn conversational context,
        persisted candidate evidence, and skill state.
        Ensures normal chat does NOT mutate candidate skill state or research telemetry.
        Returns: (content, ui_card, msg_type, is_fallback, provider_used)
        """
        candidate_obj = None
        profile_summary = ""
        weak_skills = []
        if candidate_id:
            try:
                candidate_obj = await self.candidate_repo.get(candidate_id)
                profile_model = await self.candidate_repo.get_profile(candidate_id)
                if profile_model and profile_model.profile_data:
                    pd = dict(profile_model.profile_data)
                    skills_str = ", ".join(s.get("name", "") for s in pd.get("skills", []))
                    exp_val = pd.get("total_years_experience", 0)
                    profile_summary = f"Experience: {exp_val} years. Skills: {skills_str}."

                skill_states = await self.skill_state_repo.list_by_candidate(candidate_id)
                if skill_states:
                    weak_skills = [
                        s.skill_name for s in sorted(skill_states, key=lambda x: x.mastery_estimate)
                        if s.mastery_estimate < 0.7
                    ]
            except Exception as e:
                logger.debug(f"Candidate context lookup fallback: {e}")

        cand_role = getattr(candidate_obj, "target_role", None) if candidate_obj else None
        role = target_role or conversation_metadata.get("target_role") or cand_role or "Software Engineer"
        skill = focus_skill or conversation_metadata.get("focus_skill") or (weak_skills[0] if weak_skills else "System Design")

        # Chronological multi-turn history extraction (bounded to prevent context overflow while preserving full technical depth and code blocks)
        recent_history_lines = []
        if prior_messages:
            total_history_budget = 8000
            current_len = 0
            collected = []
            for m in reversed(prior_messages[-10:]):
                speaker = "Candidate" if getattr(m, "role", "") == ChatRole.USER.value else "Coach"
                # Preserve complete candidate answers and code blocks without arbitrary 500-char truncation
                max_len = 2500
                m_content = getattr(m, "content", "")[:max_len].strip()
                line = f"{speaker}: {m_content}"
                if current_len + len(line) > total_history_budget:
                    break
                collected.append(line)
                current_len += len(line)
            recent_history_lines = list(reversed(collected))
        history_str = "\n".join(recent_history_lines) if recent_history_lines else "None (Beginning of conversation)"

        if intent == ChatIntent.ROADMAP:
            if candidate_id:
                from backend.services.roadmap_service import RoadmapService
                roadmap_svc = RoadmapService(self.session)
                try:
                    gap_result = await roadmap_svc.calculate_gaps(candidate_id, role)
                    top_gaps = [
                        {"skill_id": g.skill_id, "skill_name": g.skill_name, "gap": round(g.raw_gap, 2)}
                        for g in gap_result.gaps[:3]
                    ]
                    content = (
                        f"Here is a summary of your key competency gaps for **{role}**. "
                        "You can select any milestone to begin targeted transfer coaching."
                    )
                    return content, {"type": "ROADMAP_SUMMARY", "role": role, "top_gaps": top_gaps}, "card", False, "roadmap_service"
                except Exception as e:
                    logger.warning(f"Roadmap query fallback: {e}")

            content = (
                f"For the **{role}** track, key milestones include System Architecture, Distributed Invariants, "
                "and Concurrency Mechanics. Let me know which skill you want to target!"
            )
            return content, None, "text", False, "system_rule"

        elif intent == ChatIntent.SKILL_GAP or intent == ChatIntent.SESSION_STATUS:
            if candidate_id:
                states = await self.skill_state_repo.list_by_candidate(candidate_id)
                if states:
                    summary = [
                        {
                            "skill": s.skill_name,
                            "mastery": round(s.mastery_estimate, 2),
                            "transfer_level": s.highest_transfer_level,
                        }
                        for s in states[:5]
                    ]
                    content = f"Here is your current verified skill breakdown across {len(states)} competencies."
                    return content, {"type": "SKILL_STATUS", "skills": summary}, "card", False, "skill_state_service"

            content = (
                "You haven't completed any evaluated interview turns or coaching loops yet. "
                "Ask for a **practice question** or start a **mock interview** to establish your baseline!"
            )
            return content, None, "text", False, "system_rule"

        elif intent == ChatIntent.COACHING:
            try:
                from ai.interview_engine.question_generator import AIQuestionGenerator
                q_gen = AIQuestionGenerator()
                hint_res = await q_gen.generate_coach_hint(
                    question_text=f"How do you design and operate {skill} reliably in production systems?",
                    topic=skill,
                    expected_concepts=[skill, "failure isolation", "consistency invariants"],
                    partial_answer=user_message,
                )
                hint_text = hint_res.get("hint_text", "Focus on the fundamental invariants of state transitions.")
                nudge = hint_res.get("pedagogical_nudge", "What invariant guarantees consistency during node failure?")
                concept = hint_res.get("key_concept_to_consider", skill)

                content = (
                    f"💡 **Socratic Guidance on {skill}**:\n\n"
                    f"{hint_text}\n\n"
                    f"**Pedagogical Nudge:** {nudge}\n\n"
                    f"**Key Concept to Consider:** {concept}"
                )
                ui_card = {
                    "type": "SOCRATIC_HINT",
                    "scaffold_level": "MEDIUM",
                    "topic": skill,
                    "guiding_question": nudge,
                    "key_concept": concept,
                }
                return content, ui_card, "card", False, "ai_question_generator"
            except Exception as e:
                logger.warning(f"Coaching intent delegation error: {e}")
                content = (
                    f"💡 **Socratic Guidance on {skill}**: Consider the fundamental invariant of this problem. "
                    "How does the state change during boundary transitions? What happens if two concurrent "
                    "requests execute at the exact same timestamp?"
                )
                ui_card = {
                    "type": "SOCRATIC_HINT",
                    "scaffold_level": "MEDIUM",
                    "guiding_question": "What invariant guarantees consistency during node failure?",
                }
                return content, ui_card, "card", True, "deterministic_coach_fallback"

        elif intent == ChatIntent.INTERVIEW:
            try:
                from ai.interview_engine.question_generator import AIQuestionGenerator
                q_gen = AIQuestionGenerator()

                past_questions = [
                    getattr(m, "content", "")[:80]
                    for m in (prior_messages or [])
                    if getattr(m, "role", "") == ChatRole.ASSISTANT.value and "?" in getattr(m, "content", "")
                ]

                gen_result = await q_gen.generate_question(
                    target_role=role,
                    interview_type="technical",
                    difficulty_level="medium",
                    turn_number=1,
                    total_questions=5,
                    resume_summary=profile_summary or f"Candidate targeting {role}",
                    rag_context="",
                    previous_questions=past_questions,
                )
                question_text = gen_result.get("question_text", f"Explain how you would design a scalable solution for {skill}.")
                stage_name = gen_result.get("stage_name", "Technical Assessment")
                competency = gen_result.get("target_competency", role)
                invariants = gen_result.get("expected_concepts") or ["System Correctness", "Failure Modes"]

                content = f"🎯 **Interview Practice for {role}** ({stage_name}):\n\n{question_text}"
                ui_card = {
                    "type": "INTERVIEW_QUESTION",
                    "role": role,
                    "topic": competency,
                    "difficulty": gen_result.get("difficulty_level", "medium"),
                    "expected_invariants": invariants,
                }
                return content, ui_card, "card", False, "ai_question_generator"
            except Exception as e:
                logger.warning(f"Interview intent generation error: {e}")
                content = (
                    f"🎯 **Interview Practice for {role}**:\n\n"
                    f"Explain how you would design an idempotency and locking layer for a high-volume {skill} service. "
                    "What database structures and invariants would you employ to guarantee correctness?"
                )
                ui_card = {
                    "type": "INTERVIEW_QUESTION",
                    "role": role,
                    "topic": f"{skill} Architecture",
                    "expected_invariants": ["Idempotency keys", "Distributed lock / 2PC alternatives"],
                }
                return content, ui_card, "card", True, "deterministic_interview_fallback"

        elif intent == ChatIntent.TRANSFER:
            try:
                from ai.transfer_engine.task_generator import TransferTaskGenerator
                from ai.transfer_engine.schemas import TransferGenerationRequest
                from backend.domain.transfer.taxonomy import TransferLevel

                t_gen = TransferTaskGenerator()
                req = TransferGenerationRequest(
                    skill_id=skill.lower().replace(" ", "_"),
                    transfer_level=TransferLevel.L3_FAR_TRANSFER,
                    core_invariants=["Partition isolation", "Eventual vs serial consistency", "State reconciliation"],
                    base_surface_context=f"Real-world {skill} production architecture",
                    base_expected_concepts=["invariant_preservation", "trade_offs", "failure_handling"],
                    parent_task_id=f"chat_task_{uuid.uuid4().hex[:6]}",
                )
                task_dto = await t_gen.generate_transfer_task(req)
                prompt_text = task_dto.prompt_template or f"How would you preserve invariants in {task_dto.surface_context}?"

                content = (
                    f"🧪 **Transfer Challenge ({task_dto.transfer_level.value})**:\n\n"
                    f"{prompt_text}\n\n"
                    f"**Core Invariants to Preserve:** {', '.join(task_dto.core_invariants)}"
                )
                ui_card = {
                    "type": "TRANSFER_TASK",
                    "transfer_level": task_dto.transfer_level.value,
                    "surface_context": task_dto.surface_context,
                    "core_invariants": task_dto.core_invariants,
                    "task_id": task_dto.id,
                }
                return content, ui_card, "card", False, "ai_transfer_generator"
            except Exception as e:
                logger.warning(f"Transfer intent generation error: {e}")
                content = (
                    f"🧪 **Transfer Challenge (L3 Far Transfer - {skill})**:\n\n"
                    "Consider a globally distributed event stream with asynchronous multi-region replication. "
                    "How would you preserve serializable consistency across conflicting partition writes without "
                    "inducing cross-region latency bottlenecks?"
                )
                ui_card = {
                    "type": "TRANSFER_TASK",
                    "transfer_level": "L3_FAR_TRANSFER",
                    "core_invariants": ["Partition tolerance", "Eventual vs Serial Consistency"],
                }
                return content, ui_card, "card", True, "deterministic_transfer_fallback"

        else:
            # Intent: GENERAL_CHAT or conversational inquiry with full chronological history
            provider = get_llm_provider(task="routine")
            try:
                system_prompt = (
                    "You are the Transfer-Aware AI Interview Coach. You coach software candidates "
                    "in system architecture, distributed systems, algorithmic invariants, and interview mastery.\n\n"
                    f"Target Role: {role}\n"
                )
                if profile_summary:
                    system_prompt += f"Candidate Profile: {profile_summary}\n"
                if weak_skills:
                    system_prompt += f"Target Competencies: {', '.join(weak_skills[:3])}\n"

                system_prompt += (
                    "\nPedagogical & Conversational Instructions:\n"
                    "1. Contextual Continuity: Closely maintain context from the prior turns. Do NOT reset or restart lessons.\n"
                    "2. Explain in Detail: If asked for detail, delve into underlying mechanics (e.g. storage engines, locks, state machines) rather than high-level bullet points.\n"
                    "3. Explain from First Principles: Ground reasoning in core fundamental constraints (e.g. network unreliability, CAP theorem, atomicity boundaries).\n"
                    "4. Python Implementations: When code is requested, provide robust, readable Python code with clear assumptions, edge cases, and architectural trade-offs.\n"
                    "5. Challenge Handling: If the candidate questions an assertion or points out an edge case, objectively verify the technical mechanics. Agree if valid or explain why the boundary condition behaves differently.\n"
                    "6. New Scenarios: Reason systematically about how the invariants adapt to the new context.\n"
                    "7. Formative Check: Conclude with a crisp, relevant question to verify deep candidate understanding.\n"
                    "8. Clean Output: Never output internal debug labels, stage tags, or json artifacts directly in text.\n"
                )

                system_prompt += f"\nRecent Conversation History:\n{history_str}\n"

                req = LLMRequest(
                    system_prompt=system_prompt,
                    user_prompt=user_message,
                    temperature=0.3,
                    max_tokens=650,
                    response_json=False,
                    metadata={"task_type": "conversational_coaching"},
                )
                from ai.config import ai_settings
                gen_timeout = float(getattr(ai_settings, "nvidia_nim_timeout", 35.0))
                resp = await asyncio.wait_for(provider.generate(req), timeout=gen_timeout)
                if resp and resp.content and resp.content.strip():
                    raw_model = getattr(resp, "model", None) or getattr(resp, "model_name", None) or getattr(provider, "provider_name", "ai_coach")
                    model_name = str(raw_model)
                    return resp.content, None, "text", False, model_name
                else:
                    raise RuntimeError("Empty response received from LLM provider")
            except Exception as e:
                logger.error(f"Conversational generation provider error: {e}", exc_info=True)
                # Attempt secondary provider before returning error card
                try:
                    from backend.infrastructure.ai.gemini_provider import GeminiLLMProvider
                    from backend.infrastructure.ai.telemetry import ai_telemetry
                    ai_telemetry.record_fallback(
                        primary_provider=getattr(provider, "provider_name", "nvidia_nim"),
                        fallback_provider="gemini",
                        task_type="conversation_turn",
                        reason=str(e)[:150],
                    )
                    if ai_settings.gemini_api_key and not isinstance(provider, GeminiLLMProvider):
                        gemini_prov = GeminiLLMProvider()
                        resp = await asyncio.wait_for(gemini_prov.generate(req), timeout=12.0)
                        if resp and resp.content and resp.content.strip():
                            raw_model = getattr(resp, "model", None) or getattr(gemini_prov, "default_model", "gemini-3.8-flash")
                            return resp.content, None, "text", False, f"gemini:{raw_model}"
                except Exception as sec_e:
                    logger.warning(f"Secondary provider fallback in conversation_service failed: {sec_e}")

                content = (
                    f"⚠️ **AI Coach Temporarily Unavailable**\n\n"
                    f"I encountered an issue connecting to the AI provider while processing your request: *\"{user_message[:120]}\"*.\n\n"
                    "The system has logged this diagnostic event. Please verify your connection or click **Retry** to resend your message."
                )
                return content, None, "text", True, "provider_failure_fallback"

