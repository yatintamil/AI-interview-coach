"""
Answer Diagnostic Classification & Interviewer Action Engine.

Classifies preceding candidate responses using objective evaluation signals and
semantic text analysis into 8 distinct cognitive categories.
Selects targeted pedagogical interviewer actions to guide the interview naturally.
"""

from enum import Enum
import re
from typing import Dict, Any, List, Optional, Tuple


class AnswerClassification(str, Enum):
    """Cognitive and diagnostic classification of candidate answers."""
    STRONG = "STRONG"  # Correct and well-reasoned
    STRONG_DEEPER_PROBE = "STRONG_DEEPER_PROBE"  # Strong baseline warranting deeper trade-off exploration
    INCOMPLETE = "INCOMPLETE"  # Correct but incomplete (missing key concepts)
    INCORRECT = "INCORRECT"  # Incorrect or contains misconceptions
    AMBIGUOUS = "AMBIGUOUS"  # Vague, abstract, or lacking concrete mechanics
    OFF_TOPIC = "OFF_TOPIC"  # Irrelevant, deflection, or unrelated to topic
    CONTRADICTORY = "CONTRADICTORY"  # Conflicting claims or mutually exclusive assertions
    REPEATED_OR_EVASIVE = "REPEATED_OR_EVASIVE"  # Refusal, looping, evasion, or repetition


class InterviewerAction(str, Enum):
    """Pedagogical interviewer action selected in response to candidate answer."""
    PROBE_DEEPER_TRADEOFF = "PROBE_DEEPER_TRADEOFF"  # Explore unstated trade-off or deeper edge case
    PROBE_MISSING_CONCEPT = "PROBE_MISSING_CONCEPT"  # Focused question about the specific missing concept
    DIAGNOSTIC_CLARIFICATION = "DIAGNOSTIC_CLARIFICATION"  # Diagnostic question to isolate misconception
    REQUEST_CONCRETE_EXAMPLE = "REQUEST_CONCRETE_EXAMPLE"  # Request a concrete scenario or implementation
    REDIRECT_TO_QUESTION = "REDIRECT_TO_QUESTION"  # Polite redirection back to the original question
    RECONCILE_CONTRADICTION = "RECONCILE_CONTRADICTION"  # Ask candidate to reconcile conflicting statements
    ADDRESS_EVASION_OR_REPETITION = "ADDRESS_EVASION_OR_REPETITION"  # Address evasion and re-anchor on core problem
    PLANNED_COMPETENCY_TRANSITION = "PLANNED_COMPETENCY_TRANSITION"  # Advance to next competency with clear rationale


REFUSAL_TERMS = [
    "i don't know", "i dont know", "no idea", "not sure", "idk",
    "skip", "pass", "cant answer", "can't answer", "nothing",
    "dont know", "don't know", "i do not know", "have no idea",
    "pass on this", "not familiar", "next question",
]

EVASION_TERMS = [
    "as i said before", "as i mentioned earlier", "already explained",
    "same as before", "same answer", "refer to previous", "as stated above",
    "already covered",
]

CONTRADICTION_KEYWORDS = [
    "contradict", "contradiction", "conflicting", "inconsistent",
    "opposite", "paradox", "mutually exclusive", "incompatible",
    "conflicting claims",
]

AMBIGUOUS_KEYWORDS = [
    "vague", "ambiguous", "high-level", "hand-wavy", "handwaving",
    "superficial", "generic", "lacks concrete", "abstract",
    "lacks operational", "hand-waving",
]

# Domain-specific mutually exclusive contradiction pairs
MUTUALLY_EXCLUSIVE_PATTERNS = [
    ("read uncommitted", "serializable"),
    ("read uncommitted", "lineariz"),
    ("dirty read", "lineariz"),
    ("dirty read", "serializable"),
    ("eventual consistency", "immediate lineariz"),
    ("eventual consistency", "strict lineariz"),
    ("asynchronous replication", "zero data loss"),
    ("optimistic locking", "blocks all readers"),
    ("optimistic locking", "pessimistic lock"),
    ("partition tolerant", "eliminate network partitions"),
]

# Canonical architectural misconceptions
KNOWN_MISCONCEPTIONS = [
    "allows all cpu cores to run python bytecode concurrently in parallel",
    "speeds up multi-threaded cpu-bound",
    "all cpu cores to run python bytecode",
    "gil allows parallel",
    "adding more nodes decreases consensus latency",
    "more raft nodes makes consensus faster",
    "atomicity prevents dirty reads",
    "atomicity guarantees thread safety",
    "asynchronous replication prevents any data loss",
    "eliminate network partitions with redundancy",
]


def classify_candidate_answer(
    eval_data: Dict[str, Any],
    candidate_answer: str,
    question_text: str,
    previous_answers: Optional[List[str]] = None,
) -> Tuple[AnswerClassification, str, Dict[str, Any]]:
    """
    Classifies a candidate response into one of the 8 canonical categories using
    deterministic evaluation signals, scores, missing concepts, and textual heuristics.

    Returns:
        (classification, diagnostic_reason, metadata)
    """
    clean_ans = candidate_answer.strip()
    ans_lower = clean_ans.lower()
    words = clean_ans.split()
    word_count = len(words)

    overall_score = float(eval_data.get("overall_score", 5.0))
    correctness = float(eval_data.get("correctness", overall_score))
    completeness = float(eval_data.get("completeness", overall_score))
    relevance = float(eval_data.get("relevance", overall_score))
    technical_depth = float(eval_data.get("technical_depth", overall_score))
    missing_concepts = eval_data.get("missing_concepts", []) or []
    weaknesses = eval_data.get("weaknesses", []) or []
    strengths = eval_data.get("strengths", []) or []
    reasoning_text = str(eval_data.get("reasoning", "")).lower()
    weakness_text = " ".join(str(w) for w in weaknesses).lower()

    # 1. Check for REPEATED_OR_EVASIVE
    # A. Direct refusal
    if any(re.search(r"\b" + re.escape(p) + r"\b", ans_lower) for p in REFUSAL_TERMS):
        return (
            AnswerClassification.REPEATED_OR_EVASIVE,
            "Candidate submitted a refusal or direct admission of unfamiliarity.",
            {"refusal": True, "word_count": word_count},
        )

    # B. Evasive phrase
    if any(e in ans_lower for e in EVASION_TERMS):
        return (
            AnswerClassification.REPEATED_OR_EVASIVE,
            "Candidate deflected the question by referencing earlier turns without substantive technical content.",
            {"evasion": True, "word_count": word_count},
        )

    # C. Verbatim or near-verbatim repetition of previous answer
    if previous_answers:
        for prev in previous_answers:
            prev_clean = prev.strip().lower()
            if len(prev_clean) > 20 and len(ans_lower) > 20:
                if prev_clean == ans_lower or (ans_lower in prev_clean and len(ans_lower) > len(prev_clean) * 0.8):
                    return (
                        AnswerClassification.REPEATED_OR_EVASIVE,
                        "Candidate repeated previous answer text without providing new technical reasoning.",
                        {"repeated_text": True},
                    )

    # D. Ultra-brief non-answer (< 5 words and low score, excluding valid terse technical formulas)
    is_valid_terse = any(sym in ans_lower for sym in ["o(1)", "o(n", "o(log", "lru", "wal", "b-tree", "raft"]) and correctness >= 6.0
    if word_count < 5 and overall_score < 4.0 and not is_valid_terse:
        return (
            AnswerClassification.REPEATED_OR_EVASIVE,
            "Candidate response was too brief to convey meaningful technical reasoning.",
            {"word_count": word_count},
        )

    # 2. Check for CONTRADICTORY
    detected_pairs = []
    for p1, p2 in MUTUALLY_EXCLUSIVE_PATTERNS:
        if p1 in ans_lower and p2 in ans_lower:
            detected_pairs.append(f"'{p1}' vs '{p2}'")

    has_mutually_exclusive = len(detected_pairs) > 0
    has_contradiction_signal = (
        has_mutually_exclusive
        or any(kw in weakness_text or kw in reasoning_text for kw in CONTRADICTION_KEYWORDS)
    )

    if has_contradiction_signal:
        contradiction_detail = (
            ", ".join(detected_pairs)
            if detected_pairs
            else (next((w for w in weaknesses if any(k in w.lower() for k in CONTRADICTION_KEYWORDS)), "competing claims"))
        )
        return (
            AnswerClassification.CONTRADICTORY,
            f"Candidate response introduced conflicting assertions: {contradiction_detail}.",
            {
                "contradiction_detected": True,
                "contradiction_detail": contradiction_detail,
                "mutually_exclusive": has_mutually_exclusive,
            },
        )

    # 3. Check for OFF_TOPIC (Irrelevant or deflected answers)
    is_off_topic_weakness = any(
        kw in weakness_text for kw in ["off-topic", "off topic", "does not address", "unrelated", "irrelevant", "deflected", "tangential"]
    )
    if is_off_topic_weakness or relevance < 3.0:
        return (
            AnswerClassification.OFF_TOPIC,
            f"Candidate response diverged from the subject of the question (relevance: {relevance:.1f}/10).",
            {"relevance": relevance, "weakness": is_off_topic_weakness},
        )

    # 4. Check for INCORRECT (Misconceptions, factual falsehoods, or zero demonstrated concept answers)
    has_known_misconception = any(km in ans_lower for km in KNOWN_MISCONCEPTIONS)
    has_misconception = (
        has_known_misconception
        or any(kw in weakness_text for kw in ["misconception", "incorrect premise", "flawed premise", "inaccurate", "wrong premise"])
    )
    has_demonstrated_concepts = bool(
        eval_data.get("matched_concepts")
        or (eval_data.get("coverage_ratio", 0.0) > 0.0)
        or (strengths and len(strengths) > 0 and overall_score >= 2.0)
    )

    # An answer is INCORRECT if it contains an active misconception/falsehood,
    # or if zero expected concepts were demonstrated with erroneous technical claims.
    # If the candidate demonstrated partial concepts without misconceptions, preserve partial credit and classify as INCOMPLETE or AMBIGUOUS.
    if has_known_misconception or (has_misconception and not has_demonstrated_concepts) or (not has_demonstrated_concepts and correctness < 3.0 and word_count >= 5):
        return (
            AnswerClassification.INCORRECT,
            "Candidate response contained a fundamental technical inaccuracy or misconception.",
            {"correctness": correctness, "misconceptions": weaknesses[:2]},
        )

    # 5. Check for AMBIGUOUS (Vague, hand-waving, lacking concrete mechanics)
    is_ambiguous_weakness = any(
        kw in weakness_text for kw in AMBIGUOUS_KEYWORDS
    )
    is_vague_phrasing = any(
        vp in ans_lower for vp in [
            "runs a quick check", "handles the changes", "it depends on things",
            "checks the system", "just scale up", "optimize the backend",
            "add some caching", "make it robust",
        ]
    ) and word_count < 35
    if is_vague_phrasing or (is_ambiguous_weakness and completeness < 6.0) or (not has_demonstrated_concepts and relevance >= 5.0 and technical_depth < 4.0 and overall_score < 6.5):
        return (
            AnswerClassification.AMBIGUOUS,
            "Candidate response remained abstract or ambiguous without specifying operational mechanics.",
            {"completeness": completeness, "technical_depth": technical_depth, "word_count": word_count},
        )

    # 6. Check for INCOMPLETE
    # Candidate grasped baseline concept but omitted key expected concepts (score < 8.0)
    if missing_concepts and overall_score < 8.0:
        return (
            AnswerClassification.INCOMPLETE,
            f"Candidate correctly grasped the baseline concept but omitted critical aspects: {', '.join(missing_concepts[:2])}.",
            {"missing_concepts": missing_concepts, "completeness": completeness},
        )

    # 7. STRONG vs STRONG_DEEPER_PROBE
    if overall_score >= 8.0 and correctness >= 7.5:
        if missing_concepts:
            return (
                AnswerClassification.STRONG_DEEPER_PROBE,
                f"Candidate demonstrated solid baseline competence; probing deeper architectural trade-off on {missing_concepts[0]}.",
                {"missing_concepts": missing_concepts, "overall_score": overall_score},
            )
        return (
            AnswerClassification.STRONG,
            f"Candidate provided an accurate and well-reasoned response (score: {overall_score:.1f}/10).",
            {"overall_score": overall_score, "strengths": strengths[:2]},
        )

    # Balanced fallback
    if missing_concepts:
        return (
            AnswerClassification.INCOMPLETE,
            f"Candidate gave a partial explanation; omitted {', '.join(missing_concepts[:2])}.",
            {"missing_concepts": missing_concepts},
        )

    return (
        AnswerClassification.STRONG_DEEPER_PROBE,
        "Candidate answered adequately; probing practical edge cases and trade-offs.",
        {"overall_score": overall_score},
    )


def determine_interviewer_action(
    classification: AnswerClassification,
    is_competency_sufficient: bool,
    current_competency: str,
    next_competency: str,
    target_concept: Optional[str] = None,
    contradiction_detail: Optional[str] = None,
    sufficiency_reason: Optional[str] = None,
) -> Tuple[InterviewerAction, str, str, str]:
    """
    Selects the targeted pedagogical interviewer action and generates:
    1. InterviewerAction enum
    2. action_directive: Prompt instruction for the question generator
    3. conversational_lead_in: Candidate-facing natural lead-in bridge
    4. transition_rationale: Explainable rationale for logging/reports

    Returns:
        (action, action_directive, conversational_lead_in, transition_rationale)
    """
    # --------------------------------------------------------------------------
    # Case 1: Assessment Plan Transitions to Next Competency
    # --------------------------------------------------------------------------
    if is_competency_sufficient and current_competency != next_competency:
        action = InterviewerAction.PLANNED_COMPETENCY_TRANSITION

        is_quota = (
            any(kw in str(sufficiency_reason).lower() for kw in ["limit", "quota", "max", "cap", "reach"])
            or classification in [
                AnswerClassification.INCOMPLETE,
                AnswerClassification.INCORRECT,
                AnswerClassification.OFF_TOPIC,
                AnswerClassification.CONTRADICTORY,
                AnswerClassification.REPEATED_OR_EVASIVE,
                AnswerClassification.AMBIGUOUS,
            ]
        )

        # 1A. Genuine Mastery Transition: Candidate demonstrated solid evidence AND not quota-capped
        if not is_quota and classification in [AnswerClassification.STRONG, AnswerClassification.STRONG_DEEPER_PROBE]:
            action_directive = (
                f"The candidate has demonstrated solid evidence on '{current_competency}'. "
                f"Transition smoothly to the next planned role competency: '{next_competency}'. "
                f"Ask a clear, realistic baseline question grounded in '{next_competency}'."
            )
            lead_in = (
                f"You've shown a clear grasp of {current_competency}. Having established that solid foundation, "
                f"let's transition as planned to examine your approach to {next_competency}:"
            )
            rationale = (
                f"Competency '{current_competency}' achieved sufficient evidence. "
                f"Advancing as planned to blueprint competency '{next_competency}'."
            )
        else:
            # 1B. Quota/Schedule transition: Neutral schedule pacing, NO false praise
            action_directive = (
                f"The assessment plan has concluded inquiry on '{current_competency}' ({sufficiency_reason or 'follow-up quota reached'}). "
                f"Pivot professionally to the next planned role competency: '{next_competency}'. "
                f"Ask a clear foundational question grounded in '{next_competency}' without dwelling on prior gaps."
            )
            lead_in = (
                f"Thank you for working through those trade-offs on {current_competency}. "
                f"In the interest of covering our full assessment scope within our session schedule, "
                f"let's pivot to our next planned area: {next_competency}:"
            )
            rationale = (
                f"Competency '{current_competency}' assessment concluded (quota reached: {sufficiency_reason or 'max follow-ups'}). "
                f"Plan-budgeted transition to '{next_competency}' to preserve full interview schedule coverage."
            )

        return action, action_directive, lead_in, rationale

    # --------------------------------------------------------------------------
    # In-Competency Answer-Driven Pedagogical Dispatch
    # --------------------------------------------------------------------------

    # Case 2: OFF_TOPIC -> Polite Redirection
    if classification == AnswerClassification.OFF_TOPIC:
        action = InterviewerAction.REDIRECT_TO_QUESTION
        action_directive = (
            f"The candidate's response diverged from or deflected away from '{current_competency}'. "
            f"Politely redirect them back to the original technical inquiry. "
            f"Ask a clear, focused single question that re-anchors them on the core problem without penalty."
        )
        lead_in = (
            f"Thank you for sharing that context. To ensure we evaluate your approach to the core technical challenge, "
            f"let's refocus directly on {current_competency}:"
        )
        rationale = f"Candidate response diverged from {current_competency}. Redirection issued to re-anchor dialogue."
        return action, action_directive, lead_in, rationale

    # Case 3: CONTRADICTORY -> Reconcile Conflicting Claims
    if classification == AnswerClassification.CONTRADICTORY:
        action = InterviewerAction.RECONCILE_CONTRADICTION
        detail_phrase = f" regarding {contradiction_detail}" if contradiction_detail else ""
        action_directive = (
            f"The candidate introduced conflicting statements{detail_phrase} in '{current_competency}'. "
            f"Ask a single clarifying question inviting them to reconcile those competing claims. "
            f"Do NOT lecture or reveal the correct answer; allow them to clarify their reasoning."
        )
        lead_in = (
            f"You touched on two competing assertions{detail_phrase} in {current_competency}. "
            f"Could you clarify how you reconcile those two aspects?"
        )
        rationale = f"Candidate made contradictory claims{detail_phrase} regarding {current_competency}. Clarification requested."
        return action, action_directive, lead_in, rationale

    # Case 4: INCORRECT -> Diagnostic Clarification
    if classification == AnswerClassification.INCORRECT:
        action = InterviewerAction.DIAGNOSTIC_CLARIFICATION
        action_directive = (
            f"The candidate made a technical error or revealed a misconception regarding '{current_competency}'. "
            f"Ask a supportive diagnostic question to isolate their underlying mental model. "
            f"Do NOT increase difficulty and do NOT reveal the solution directly; ask a single clarifying question."
        )
        lead_in = (
            f"Let's look a little closer at that mechanism in {current_competency}. "
            f"To make sure we're aligned on the foundational behavior:"
        )
        rationale = f"Misconception identified in {current_competency}. Diagnostic probe deployed to evaluate core mental model."
        return action, action_directive, lead_in, rationale

    # Case 5: AMBIGUOUS -> Request Concrete Example
    if classification == AnswerClassification.AMBIGUOUS:
        action = InterviewerAction.REQUEST_CONCRETE_EXAMPLE
        action_directive = (
            f"The candidate gave an abstract, vague, or high-level answer regarding '{current_competency}'. "
            f"Ask for a concrete, real-world example or specific operational mechanics to test practical depth. "
            f"Frame it as a single focused inquiry without presupposing the answer."
        )
        lead_in = (
            f"Your high-level overview covers the general concept. To see how that operates under real conditions in {current_competency}, "
            f"could you walk through a concrete implementation example?"
        )
        rationale = f"High-level response on {current_competency}. Concrete implementation example requested."
        return action, action_directive, lead_in, rationale

    # Case 6: REPEATED_OR_EVASIVE -> Address Evasion / Repetition
    if classification == AnswerClassification.REPEATED_OR_EVASIVE:
        action = InterviewerAction.ADDRESS_EVASION_OR_REPETITION
        action_directive = (
            f"The candidate repeated a previous response, offered an evasive deflection, or admitted unfamiliarity. "
            f"Gently acknowledge their response and provide a simpler, accessible baseline entry point to '{current_competency}'. "
            f"Ask ONE clear, simple foundational question."
        )
        lead_in = (
            f"No problem at all—let's step back and look at a simpler, foundational aspect of {current_competency}:"
        )
        rationale = f"Candidate offered a brief response or evasion on {current_competency}. Stepped back to simpler foundational inquiry."
        return action, action_directive, lead_in, rationale

    # Case 7: INCOMPLETE -> Probe Specific Missing Concept
    if classification == AnswerClassification.INCOMPLETE:
        action = InterviewerAction.PROBE_MISSING_CONCEPT
        missing_target = target_concept or "the primary operational edge case"
        action_directive = (
            f"The candidate explained the primary flow well, but omitted '{missing_target}'. "
            f"Ask a targeted single follow-up question specifically probing '{missing_target}' "
            f"without escalating difficulty unnecessarily."
        )
        lead_in = (
            f"Good foundation on the main path for {current_competency}. Let's look specifically at how {missing_target} is handled:"
        )
        rationale = f"Omission of '{missing_target}' identified in {current_competency}. Focused follow-up probe issued."
        return action, action_directive, lead_in, rationale

    # Case 8: STRONG / STRONG_DEEPER_PROBE -> Probe Deeper Trade-off of SAME concept
    action = InterviewerAction.PROBE_DEEPER_TRADEOFF
    focus_target = target_concept or current_competency
    action_directive = (
        f"The candidate demonstrated strong understanding of '{current_competency}'. "
        f"Probe an unstated architectural trade-off, edge case, or high-scale failure mode of '{focus_target}'. "
        f"Ask EXACTLY ONE deep, practical question."
    )
    lead_in = (
        f"Strong breakdown on {current_competency}. Considering the architectural trade-offs at higher scale:"
    )
    rationale = f"Strong answer on {current_competency}. Probing deeper edge case / architectural trade-off within same competency."
    return action, action_directive, lead_in, rationale
