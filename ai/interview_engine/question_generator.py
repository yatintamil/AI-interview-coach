"""
Question Generator Service for Single AI Interviewer.
Utilizes AI Provider Abstraction to generate resume-grounded interview questions.
"""

import json
import logging
import re
from typing import Optional, List, Dict, Any

from backend.domain.ai.interfaces import LLMProvider, LLMRequest
from backend.infrastructure.ai.factory import get_llm_provider
from ai.prompts.interview_v1 import (
    QUESTION_GENERATION_SYSTEM_PROMPT,
    QUESTION_GENERATION_USER_PROMPT_TEMPLATE,
    COACH_HINT_SYSTEM_PROMPT,
    COACH_HINT_USER_PROMPT_TEMPLATE,
)

from ai.interview_engine.question_bank import QuestionBankService

logger = logging.getLogger(__name__)


def is_question_duplicate(q_text: str, prev_list: List[str]) -> bool:
    norm_q = q_text.strip().lower()
    for p in prev_list:
        norm_p = p.strip().lower()
        if norm_q == norm_p:
            return True
        # Match significant prefix overlap
        if len(norm_q) > 30 and len(norm_p) > 30 and norm_q[:45] == norm_p[:45]:
            return True
    return False


def compute_interview_stage(turn_number: int, total_questions: int) -> tuple:
    """
    Computes interview lifecycle stage name, stage index (1-based), and total stages.
    """
    total_stages = 5
    if total_questions <= 3:
        if turn_number == 1:
            return "Foundational Orientation & Technical Baseline", 1, 3
        elif turn_number == 2:
            return "Core Architecture & Engineering Trade-offs", 2, 3
        else:
            return "Behavioral Ownership & STAR Resolution", 3, 3

    ratio = (turn_number - 1) / max(1, total_questions - 1)
    if ratio < 0.20:
        return "Foundational Orientation & Resume Grounding", 1, total_stages
    elif ratio < 0.45:
        return "Core Engineering & Algorithmic Mechanics", 2, total_stages
    elif ratio < 0.70:
        return "Scalable Systems & Architectural Trade-offs", 3, total_stages
    elif ratio < 0.88:
        return "Incident Invariants, Failure Modes & Debugging", 4, total_stages
    else:
        return "Cross-Functional Ownership & STAR Leadership", 5, total_stages


class AIQuestionGenerator:
    """
    Generates structured, resume-grounded questions for technical, behavioral, and mixed interviews.
    Guarantees strictly zero-repetition across an interview session.
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider(task="routine")

    async def generate_question(
        self,
        target_role: str,
        interview_type: str,
        difficulty_level: str,
        turn_number: int,
        total_questions: int,
        resume_summary: str,
        rag_context: str,
        previous_questions: List[str] = [],
        last_question: Optional[str] = None,
        last_answer: Optional[str] = None,
        last_score: Optional[float] = None,
        last_missing_concepts: Optional[List[str]] = None,
        candidate_claims: Optional[List[str]] = None,
        candidate_dossier: Optional[Dict[str, Any]] = None,
        question_plan: Optional[Any] = None,
    ) -> Dict[str, Any]:
        """
        Generates a structured question dictionary with conversational continuity,
        adaptive difficulty steering, zero repetition, and strict role competency governance.
        """
        prev_summary = "\n".join(f"- Turn {i+1}: {q}" for i, q in enumerate(previous_questions)) or "None (First Question)"

        role_desc = target_role
        if "omnirole" in target_role.lower() or "universal" in target_role.lower():
            role_desc = "Universal Software Engineering (Cross-Company Competencies: Algorithms, Architecture, Real-World Systems, and Problem Solving)"

        # Stage and Competency Resolution
        if question_plan is not None:
            stage_name = getattr(question_plan, "stage_name", None) or "Core Engineering"
            stage_idx = getattr(question_plan, "stage_index", 1) or 1
            total_stg = 5
            target_competency = getattr(question_plan, "competency_name", role_desc)
            assessment_objective = getattr(question_plan, "objective", f"Assess {target_competency}")
            core_invs = getattr(question_plan, "core_invariants", [])
            core_invariants = "; ".join(core_invs) if core_invs else "Maintain foundational algorithmic and architectural invariants"
            exp_concs = getattr(question_plan, "expected_concepts", [])
            expected_concepts_str = ", ".join(exp_concs) if exp_concs else target_competency
            is_followup = getattr(question_plan, "is_followup", False)
            followup_concept = getattr(question_plan, "followup_target_concept", None)
            interviewer_action = getattr(question_plan, "interviewer_action", None) or ("PROBE_MISSING_CONCEPT" if is_followup else "ESTABLISH_BASELINE")
            action_directive = getattr(question_plan, "action_directive", None) or (f"Targeted probe on '{followup_concept}'." if followup_concept else "Establish baseline practical competence.")
            transition_rationale = getattr(question_plan, "transition_rationale", None) or f"Assessing {target_competency}."
        else:
            stage_name, stage_idx, total_stg = compute_interview_stage(turn_number, total_questions)
            target_competency = role_desc
            assessment_objective = f"Calibrate candidate competence in {role_desc} for {stage_name}"
            core_invariants = "Maintain clean architecture and robustness under edge constraints"
            expected_concepts_str = "Core technical fundamentals and domain patterns"
            is_followup = False
            followup_concept = None
            interviewer_action = "ESTABLISH_BASELINE"
            action_directive = "Standard stage progression inquiry."
            transition_rationale = "Initial competency baseline."
            exp_concs = []
            core_invs = []

        # Enhance with personalized dossier if available
        dossier_context = ""
        if candidate_dossier and candidate_dossier.get("researched_skills"):
            top_skills = [
                f"{s.get('skill_name')}: {s.get('web_summary', '')[:120]} (Principles: {', '.join(s.get('core_principles', [])[:3])})"
                for s in candidate_dossier.get("researched_skills", [])[:3]
            ]
            dossier_context = f"\nAutonomous Live-Web Researched Candidate Skills:\n" + "\n".join(f"- {ts}" for ts in top_skills)

        # Build Conversational Continuity & Previous Turn Performance Context
        preceding_comp_name = None
        if question_plan and getattr(question_plan, "preceding_competency", None):
            preceding_comp_name = question_plan.preceding_competency
        elif last_question and transition_rationale:
            m_from = re.search(r"(?:from|on)\s+'([^']+)'", transition_rationale, flags=re.I)
            if m_from:
                preceding_comp_name = m_from.group(1).strip()

        is_transition = False
        if preceding_comp_name and preceding_comp_name.strip().lower() != target_competency.strip().lower():
            is_transition = True
        elif interviewer_action == "TRANSITION_COMPETENCY" or (not is_followup and last_question):
            is_transition = True

        if last_question and last_answer:
            missing_text = ", ".join(last_missing_concepts) if last_missing_concepts else "None identified"
            score_text = f"{last_score:.1f}/10" if last_score is not None else "Not scored"
            if is_transition and preceding_comp_name:
                last_turn_context = (
                    f"- Preceding Evaluated Competency: {preceding_comp_name}\n"
                    f"- Candidate Answer on Preceding Turn: {last_answer}\n"
                    f"- Assessed Performance on Preceding Turn: {score_text}\n"
                    f"CRITICAL COMPETENCY TRANSITION INSTRUCTION:\n"
                    f"The interview has transitioned AWAY from '{preceding_comp_name}'.\n"
                    f"DO NOT generate a question about '{preceding_comp_name}' or its concepts ({missing_text}).\n"
                    f"You MUST generate a question assessing the NEW Target Competency: '{target_competency}' using the Expected Core Concepts: {expected_concepts_str}."
                )
            else:
                last_turn_context = (
                    f"- Previous Question (Turn {turn_number - 1}): {last_question}\n"
                    f"- Candidate's Answer: {last_answer}\n"
                    f"- Assessed Performance Score: {score_text}\n"
                    f"- Gaps / Missing Concepts: {missing_text}"
                )
        else:
            last_turn_context = "First question of the interview. Ground initial dialogue directly in candidate's verified resume claims."

        q_depth = getattr(question_plan, "depth_level", None) or "FOUNDATION"

        # Bounded structured candidate context (up to 800 chars) preserving skills and highlights
        structured_candidate_context = (resume_summary or "General software background")[:800]
        if rag_context:
            structured_candidate_context += f"\nRelevant Background Evidence:\n{rag_context[:300]}"

        user_prompt = QUESTION_GENERATION_USER_PROMPT_TEMPLATE.format(
            target_role=role_desc,
            target_competency=target_competency,
            assessment_objective=assessment_objective,
            expected_concepts=expected_concepts_str,
            core_invariants=core_invariants,
            difficulty_level=difficulty_level,
            turn_number=turn_number,
            total_questions=total_questions,
            stage_name=stage_name,
            interviewer_action=interviewer_action,
            action_directive=action_directive,
            transition_rationale=transition_rationale,
            resume_summary=structured_candidate_context,
            last_turn_context=last_turn_context,
        )

        request = LLMRequest(
            system_prompt=QUESTION_GENERATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=250,
            response_json=True,
            metadata={"task_type": "question_generation"},
        )

        # 1. Primary: Generate role-aware and resume-grounded question via configured LLM provider
        if getattr(self.provider, "provider_name", "") != "mock":
            try:
                response = await self.provider.generate(request)
                data = None
                if response.raw_json and ("question" in response.raw_json or "question_text" in response.raw_json):
                    data = dict(response.raw_json)
                elif response.content:
                    cleaned = re.sub(r"^```json\s*", "", response.content.strip(), flags=re.MULTILINE)
                    cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
                    data = json.loads(cleaned)

                if data and ("question" in data or "question_text" in data):
                    raw_candidate_q = (data.get("question") or data.get("question_text", "")).strip()
                    from ai.interview_engine.question_sanitizer import (
                        sanitize_and_enforce_single_question,
                        validate_question_semantics,
                        validate_substantive_question_focus,
                        validate_question_competency_alignment,
                        CompetencyAlignmentError,
                    )
                    candidate_q = sanitize_and_enforce_single_question(raw_candidate_q)
                    data["question"] = candidate_q
                    data["question_text"] = candidate_q
                    if question_plan is None and data.get("target_competency"):
                        target_competency = data.get("target_competency")
                        if data.get("expected_concepts"):
                            exp_concs = data.get("expected_concepts")

                    # Verify single-question semantics, substantive focus, and canonical competency alignment
                    is_valid_q, val_reason = validate_question_semantics(candidate_q)
                    is_focused, focus_reason = validate_substantive_question_focus(candidate_q)
                    is_aligned, align_reason = validate_question_competency_alignment(
                        question_text=candidate_q,
                        target_competency=target_competency,
                        expected_concepts=exp_concs,
                        core_invariants=core_invs,
                        preceding_competency=preceding_comp_name if is_transition else None,
                    )
                    is_duplicate = is_question_duplicate(candidate_q, previous_questions)

                    # Constrained Regeneration if question is compound or misaligned
                    if is_valid_q and not is_duplicate and (not is_focused or not is_aligned):
                        reasons = []
                        if not is_focused:
                            reasons.append(f"Substantive Focus: {focus_reason}")
                        if not is_aligned:
                            reasons.append(f"Competency Misalignment: {align_reason}")
                        logger.info(
                            f"Generated question failed validation ({' | '.join(reasons)}). "
                            f"Attempting constrained regeneration."
                        )
                        regen_user_prompt = (
                            f"{user_prompt}\n\n"
                            f"CRITICAL REGENERATION REQUIREMENT:\n"
                            f"Your previous attempt was rejected:\n"
                            f"Issue: {' | '.join(reasons)}\n"
                            f"Previous attempt: \"{candidate_q}\"\n\n"
                            f"Regenerate a focused single inquiry strictly assessing '{target_competency}'.\n"
                            f"- You MUST incorporate at least one of the Expected Core Concepts: {expected_concepts_str}.\n"
                            f"- Do NOT ask about any preceding competencies or topics (e.g. '{preceding_comp_name}').\n"
                            f"- You may keep a 1-sentence scenario setting up the context.\n"
                            f"- Focus on EXACTLY ONE primary technical mechanism or trade-off decision.\n"
                            f"- Do NOT attach secondary clauses or constraints ('while also', 'considering X and Y', 'and how do you').\n"
                            f"- Respond strictly in valid JSON matching the schema."
                        )
                        try:
                            regen_request = LLMRequest(
                                system_prompt=QUESTION_GENERATION_SYSTEM_PROMPT,
                                user_prompt=regen_user_prompt,
                                temperature=0.2,
                                max_tokens=250,
                                response_json=True,
                                metadata={"task_type": "question_generation"},
                            )
                            regen_resp = await self.provider.generate(regen_request)
                            regen_data = None
                            if regen_resp.raw_json and ("question" in regen_resp.raw_json or "question_text" in regen_resp.raw_json):
                                regen_data = regen_resp.raw_json
                            elif regen_resp.content:
                                r_cleaned = re.sub(r"^```json\s*", "", regen_resp.content.strip(), flags=re.MULTILINE)
                                r_cleaned = re.sub(r"^```\s*", "", r_cleaned, flags=re.MULTILINE)
                                regen_data = json.loads(r_cleaned)
                            if regen_data and ("question" in regen_data or "question_text" in regen_data):
                                raw_regen_q = (regen_data.get("question") or regen_data.get("question_text", "")).strip()
                                clean_regen_q = sanitize_and_enforce_single_question(raw_regen_q)
                                r_valid, _ = validate_question_semantics(clean_regen_q)
                                r_focused, r_f_reason = validate_substantive_question_focus(clean_regen_q)
                                r_aligned, r_a_reason = validate_question_competency_alignment(
                                    question_text=clean_regen_q,
                                    target_competency=target_competency,
                                    expected_concepts=exp_concs,
                                    core_invariants=core_invs,
                                    preceding_competency=preceding_comp_name if is_transition else None,
                                )
                                if r_valid and r_focused and r_aligned and not is_question_duplicate(clean_regen_q, previous_questions):
                                    logger.info(f"Constrained regeneration succeeded: '{clean_regen_q}'")
                                    data = regen_data
                                    data["question"] = clean_regen_q
                                    data["question_text"] = clean_regen_q
                                    is_valid_q = True
                                    is_focused = True
                                    is_aligned = True
                                else:
                                    logger.warning(f"Regenerated question still misaligned/compound ({r_a_reason} / {r_f_reason}); deploying QuestionBank fallback.")
                        except Exception as regen_err:
                            logger.warning(f"Constrained regeneration request failed ({regen_err}); deploying QuestionBank fallback.")

                    if is_valid_q and is_focused and is_aligned and not is_duplicate:
                        normalized = self._normalize_question_output(
                            data, target_role, difficulty_level, stage_name, stage_idx, total_stg, target_competency=target_competency
                        )
                        normalized["target_competency"] = target_competency
                        normalized["expected_concepts"] = exp_concs if exp_concs else normalized.get("expected_concepts", [])
                        normalized["assessment_objective"] = assessment_objective
                        normalized["is_followup"] = is_followup
                        return normalized
                    else:
                        logger.warning(
                            f"LLM question rejected (valid={is_valid_q} [{val_reason}], focused={is_focused} [{focus_reason}], "
                            f"aligned={is_aligned} [{align_reason}], duplicate={is_duplicate}); "
                            f"switching to verified QuestionBankService fallback."
                        )
            except Exception as e:
                logger.info(f"Routine LLM unavailable ({e}), utilizing zero-repetition QuestionBankService fallback.")

        # 2. Deliberate Fallback: QuestionBankService for offline/mock execution or provider failure
        bank_q = QuestionBankService.find_question(
            stage_index=stage_idx,
            target_role=target_role,
            resume_summary=f"{resume_summary} {rag_context}",
            asked_questions=previous_questions,
            difficulty=difficulty_level,
            last_question=last_question,
            last_answer=last_answer,
            last_score=last_score,
            last_missing_concepts=last_missing_concepts,
            candidate_claims=candidate_claims,
            candidate_dossier=candidate_dossier,
            target_competency=target_competency,
            expected_concepts=exp_concs,
            is_followup=is_followup,
            followup_concept=followup_concept,
            depth_level=q_depth,
        )
        from ai.interview_engine.question_sanitizer import (
            sanitize_and_enforce_single_question,
            validate_question_competency_alignment,
            CompetencyAlignmentError,
        )
        sanitized_bank_q = sanitize_and_enforce_single_question(bank_q.get("question", ""))
        bank_q["question"] = sanitized_bank_q
        bank_q["question_text"] = sanitized_bank_q
        bank_q["target_competency"] = target_competency
        bank_q["expected_concepts"] = exp_concs if exp_concs else bank_q.get("expected_concepts", [])
        bank_q["assessment_objective"] = assessment_objective
        bank_q["is_followup"] = is_followup

        # Verify fallback alignment before returning
        b_aligned, b_reason = validate_question_competency_alignment(
            question_text=sanitized_bank_q,
            target_competency=target_competency,
            expected_concepts=exp_concs,
            core_invariants=core_invs,
            preceding_competency=preceding_comp_name if is_transition else None,
        )
        if not b_aligned:
            raise CompetencyAlignmentError(
                f"Question bank fallback failed competency alignment for target competency '{target_competency}': {b_reason}"
            )

        return bank_q


    async def generate_coach_hint(
        self,
        question_text: str,
        topic: str,
        expected_concepts: List[str],
        partial_answer: Optional[str] = None,
    ) -> Dict[str, str]:
        """
        Generates Socratic pedagogical scaffolding and a non-spoiling hint.
        """
        concepts_str = ", ".join(expected_concepts) if expected_concepts else "Core domain fundamentals"
        user_prompt = COACH_HINT_USER_PROMPT_TEMPLATE.format(
            question_text=question_text,
            topic=topic,
            expected_concepts=concepts_str,
            partial_answer=partial_answer or "I need guidance on how to structure my approach.",
        )

        request = LLMRequest(
            system_prompt=COACH_HINT_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,
            max_tokens=200,
            response_json=True,
            metadata={"task_type": "socratic_hint"},
        )

        try:
            response = await self.provider.generate(request)
            if response.raw_json and "hint_text" in response.raw_json:
                return {
                    "hint_text": response.raw_json["hint_text"],
                    "pedagogical_nudge": response.raw_json.get("pedagogical_nudge", "Consider the trade-offs between performance and complexity."),
                    "key_concept_to_consider": response.raw_json.get("key_concept_to_consider", expected_concepts[0] if expected_concepts else topic),
                }
            if response.content:
                cleaned = re.sub(r"^```json\s*", "", response.content.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
                data = json.loads(cleaned)
                return {
                    "hint_text": data.get("hint_text", "Focus on decomposing the problem into input assumptions, core processing invariants, and operational trade-offs."),
                    "pedagogical_nudge": data.get("pedagogical_nudge", "What pattern handles edge cases and scale gracefully here?"),
                    "key_concept_to_consider": data.get("key_concept_to_consider", expected_concepts[0] if expected_concepts else topic),
                }
        except Exception as e:
            logger.error(f"Error generating coach hint: {e}")

        first_concept = expected_concepts[0] if expected_concepts else topic
        return {
            "hint_text": f"Start by stating your architectural thesis clearly, then explain how you would leverage {first_concept} to address performance, edge cases, and failure modes.",
            "pedagogical_nudge": f"Have you considered how {first_concept} behaves under high concurrency or edge constraints?",
            "key_concept_to_consider": first_concept,
        }

    def _normalize_question_output(
        self,
        data: Dict[str, Any],
        target_role: str,
        difficulty_level: str,
        stage_name: str,
        stage_index: int,
        total_stages: int,
        target_competency: Optional[str] = None,
    ) -> Dict[str, Any]:
        from ai.interview_engine.question_sanitizer import sanitize_and_enforce_single_question
        raw_q = data.get("question") or data.get("question_text") or f"Tell me about your experience as a {target_role}."
        q_val = sanitize_and_enforce_single_question(raw_q)
        topic_val = data.get("topic")
        if not topic_val or topic_val.strip().lower() in [target_role.lower(), "general", "technical"]:
            topic_val = target_competency or target_role
        return {
            "question": q_val,
            "question_text": q_val,
            "category": data.get("category", "technical").lower(),
            "topic": topic_val,
            "difficulty": data.get("difficulty", difficulty_level).lower(),
            "stage_name": stage_name,
            "stage_index": stage_index,
            "total_stages": total_stages,
            "resume_evidence": data.get("resume_evidence", "Derived from candidate background."),
            "expected_concepts": data.get("expected_concepts", []),
        }
