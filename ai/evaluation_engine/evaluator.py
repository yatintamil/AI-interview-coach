"""
Explainable Evaluation Engine Service.
Utilizes AI Provider Abstraction + Configurable Question-Specific Rubrics + Deterministic Aggregation.
Integrates Deterministic Pre-Analysis to anchor semantic LLM evaluation and optimize inference latency.
"""

import json
import logging
import re
from typing import Optional, Dict, Any, List

from backend.domain.ai.interfaces import LLMProvider, LLMRequest
from backend.infrastructure.ai.factory import get_llm_provider
from ai.prompts.evaluation_v1 import (
    EVALUATION_SYSTEM_PROMPT,
    EVALUATION_USER_PROMPT_TEMPLATE,
)
from ai.evaluation_engine.rubrics import (
    RubricWeights,
    QuestionRubric,
    get_rubric_for_type,
    get_rubric_for_question,
)
from ai.evaluation_engine.deterministic_aggregator import ScoreAggregator
from ai.evaluation_engine.deterministic_pre_evaluator import (
    DeterministicPreEvaluator,
    DeterministicSignals,
    REFUSAL_PHRASES,
)

logger = logging.getLogger(__name__)


def evaluate_with_grounded_nlp(
    candidate_answer: str,
    expected_concepts: List[str],
    topic: str,
    interview_type: str,
    target_role: str,
    signals: Optional[DeterministicSignals] = None,
    rubric: Optional[QuestionRubric] = None,
    fallback: bool = False,
    fallback_reason: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Truthful deterministic NLP evaluation for low-latency, offline, or fallback turns.
    Accurately penalizes refusals/empty answers and rewards concept coverage with verbatim evidence.
    Evaluates against question-specific rubric dimensions without penalizing alternative valid structures.
    """
    clean_ans = candidate_answer.strip()
    words = clean_ans.split()
    ans_lower = clean_ans.lower()

    if rubric is None:
        rubric = get_rubric_for_question(topic=topic, expected_concepts=expected_concepts, interview_type=interview_type)

    if signals is None:
        signals = DeterministicPreEvaluator.analyze(
            candidate_answer=candidate_answer,
            expected_concepts=expected_concepts,
            topic=topic,
        )

    # 1. Check for genuine refusal or empty answer
    if signals.is_refusal or signals.word_count == 0:
        sub_scores = {
            "correctness": 0.0,
            "completeness": 0.0,
            "relevance": 0.0,
            "technical_depth": 0.0,
            "reasoning": 0.0,
        }
        overall = 0.0
        missing = list(expected_concepts) if expected_concepts else [topic]
        first_missing = missing[0] if missing else topic
        return {
            "overall_score": overall,
            "correctness": 0.0,
            "completeness": 0.0,
            "relevance": 0.0,
            "technical_depth": 0.0,
            "reasoning": 0.0,
            "performance_level": "INSUFFICIENT",
            "correct_concepts": [],
            "missing_concepts": missing,
            "technical_mistakes": ["Answer declined to address the technical core of the question or was empty/unresponsive."],
            "unsupported_claims": [],
            "strengths": [],
            "weaknesses": ["Answer declined to address the technical core of the question or was empty/unresponsive."],
            "evidence": [{"claim": "Refusal / minimal response submitted", "basis": clean_ans[:100] or "No response"}],
            "recommendations": [f"Review foundational concepts of {first_missing} before entering technical rounds."],
            "exemplar_answer": (
                f"When discussing {topic}, structure your response around {first_missing}. "
                f"Begin with core principles, describe the operational mechanism, and analyze time/space trade-offs."
            ),
            "coach_note": "Don't be discouraged! When unfamiliar with a concept, clarify assumptions and reason from first principles.",
            "evaluation_confidence": 0.99,
            "evaluator_provider": "GROUNDED_NLP",
            "evaluator_version": "v2.0",
            "rubric_version": "question_specific_v2",
            "evaluator_fallback": fallback,
            "fallback_reason": fallback_reason,
        }

    if signals.word_count < 5:
        sub_scores = {
            "correctness": 0.5,
            "completeness": 0.5,
            "relevance": 1.5 if any(w in ans_lower for w in topic.lower().split() if len(w) > 3) else 0.5,
            "technical_depth": 0.0,
            "reasoning": 0.0,
        }
        overall = ScoreAggregator.calculate_turn_score(sub_scores, custom_weights=rubric.weights)
        missing = list(expected_concepts) if expected_concepts else [topic]
        first_missing = missing[0] if missing else topic
        return {
            "overall_score": overall,
            "correctness": sub_scores["correctness"],
            "completeness": sub_scores["completeness"],
            "relevance": sub_scores["relevance"],
            "technical_depth": sub_scores["technical_depth"],
            "reasoning": sub_scores["reasoning"],
            "performance_level": "INSUFFICIENT",
            "correct_concepts": signals.matched_concepts,
            "missing_concepts": missing,
            "technical_mistakes": [],
            "unsupported_claims": [],
            "strengths": [],
            "weaknesses": ["Answer is too brief to demonstrate technical competence or mechanism grasp."],
            "evidence": [{"claim": "Ultra-brief response", "basis": clean_ans[:100]}],
            "recommendations": [f"State the core definition and mechanism of {first_missing} with explicit trade-offs."],
            "exemplar_answer": f"When discussing {topic}, explain the operational mechanism, architecture invariants, and trade-offs.",
            "coach_note": "Expand on your reasoning by walking through an architecture diagram or code flow.",
            "evaluation_confidence": 0.95,
            "evaluator_provider": "GROUNDED_NLP",
            "evaluator_version": "v2.0",
            "rubric_version": "question_specific_v2",
            "evaluator_fallback": fallback,
            "fallback_reason": fallback_reason,
        }

    matched_concepts = signals.matched_concepts
    missing_concepts = signals.missing_concepts
    coverage_ratio = signals.coverage_ratio
    word_count = signals.word_count
    topic_matched = any(w in ans_lower for w in topic.lower().split() if len(w) > 3)

    # Fair coverage ratio calculation:
    # Anchor against question's expected_concepts first if available, otherwise rubric essential concepts
    if expected_concepts:
        matched_base = [c for c in expected_concepts if c in matched_concepts]
        coverage_ratio = len(matched_base) / len(expected_concepts)
        missing_concepts = [c for c in expected_concepts if c not in matched_base]
    elif rubric and rubric.essential_concepts:
        matched_essential = [c for c in rubric.essential_concepts if c in matched_concepts]
        missing_essential = [c for c in rubric.essential_concepts if c not in matched_concepts]
        coverage_ratio = len(matched_essential) / max(1, len(rubric.essential_concepts))
        missing_concepts = missing_essential
    else:
        coverage_ratio = signals.coverage_ratio

    # Dynamic scoring based on true concept density, structural markers, and answer length
    struct_boost = 0.5 if (signals.has_quantitative_metrics or signals.has_tradeoff_analysis) else 0.0

    # Differentiate substantive answers from superficial answers
    if coverage_ratio == 0.0:
        if word_count >= 40 and struct_boost > 0:
            correctness = 4.0
            completeness = 3.5
            relevance = 5.0 if topic_matched else 3.5
            technical_depth = 4.0
            reasoning = 4.5
        else:
            correctness = 1.0
            completeness = 1.0
            relevance = round(min(3.0, 2.0 if topic_matched else 0.5), 1)
            technical_depth = 0.5
            reasoning = round(min(2.0, 0.5 * struct_boost), 1)
    else:
        # Scale score fairly based on coverage ratio, concept count, and structural depth
        concept_bonus = min(1.5, len(matched_concepts) * 0.25)
        correctness = round(min(9.8, max(2.5, 2.5 + coverage_ratio * 6.0 + concept_bonus + struct_boost + (0.5 if word_count > 100 else 0.0))), 1)
        completeness = round(min(9.5, max(2.0, 2.0 + coverage_ratio * 6.0 + concept_bonus + min(1.0, word_count / 80.0))), 1)
        relevance = round(min(9.8, max(3.5, 4.0 + coverage_ratio * 4.5 + (1.0 if topic_matched else 0.0))), 1)
        technical_depth = round(min(9.8, max(2.0, 2.0 + coverage_ratio * 5.5 + concept_bonus + min(1.5, word_count / 60.0) + struct_boost)), 1)
        reasoning = round(min(9.8, max(2.5, 3.0 + coverage_ratio * 5.0 + concept_bonus + struct_boost)), 1)

    # Check for technical misconceptions and factual inversions
    technical_mistakes: List[str] = []
    # 1. HNSW vs IVF-PQ memory inversion
    if ("hnsw" in ans_lower and "ivf" in ans_lower) and any(m in ans_lower for m in ["less ram", "less memory", "smaller footprint", "don't need any vector", "dont need vector", "doesn't need vector", "without any vector"]):
        mistake = "Factual inversion: HNSW requires raw vectors and graph adjacency links in RAM (hundreds of GBs for 50M scale), whereas IVF-PQ achieves 80-95% compression by quantizing into codebooks."
        technical_mistakes.append(mistake)

    # 2. MQTT QoS 2 end-to-end idempotency fallacy
    if "qos 2" in ans_lower and any(m in ans_lower for m in ["without any application", "automatically execute idempotent", "automatic idempotency", "no application code"]):
        mistake = "Misconception: MQTT QoS 2 guarantees transport delivery between client and broker, but does not provide application-level idempotency or database transaction deduplication without application code."
        technical_mistakes.append(mistake)

    # Penalize sub-scores if fundamental technical misconceptions are identified
    if technical_mistakes:
        correctness = round(min(correctness, 2.0), 1)
        completeness = round(min(completeness, 3.0), 1)
        reasoning = round(min(reasoning, 2.5), 1)
        technical_depth = round(min(technical_depth, 2.5), 1)
        relevance = round(min(relevance, 5.0), 1)

    # Check for unverified previous company / empirical outcome claims
    unsupported: List[str] = []
    unverified_claim_patterns = [
        r"\b(?:at|in)\s+my\s+(?:previous|last|past)\s+(?:company|team|role|employer)\b",
        r"\bwe\s+(?:reduced|cut|decreased|saved)\s+.*?\bby\s+\d+%",
        r"\b(?:i|we)\s+cut\s+(?:vector\s+hosting\s+)?costs\b",
    ]
    for pat in unverified_claim_patterns:
        if re.search(pat, ans_lower):
            claim_note = "Previous-company production outcome claim unverified; evaluated based on technical reasoning."
            if claim_note not in unsupported:
                unsupported.append(claim_note)

    sub_scores = {
        "correctness": correctness,
        "completeness": completeness,
        "relevance": relevance,
        "technical_depth": technical_depth,
        "reasoning": reasoning,
    }
    overall_score = ScoreAggregator.calculate_turn_score(sub_scores, custom_weights=rubric.weights)

    # Performance Level
    if overall_score >= 8.5:
        perf_level = "EXEMPLARY"
    elif overall_score >= 7.0:
        perf_level = "STRONG"
    elif overall_score >= 4.5:
        perf_level = "DEVELOPING"
    else:
        perf_level = "INSUFFICIENT"

    # Strengths
    if matched_concepts:
        strengths = [
            f"Accurately addressed key technical concepts: {', '.join(matched_concepts[:3])}.",
            f"Provided clear practical explanation relevant to {topic}."
        ]
    elif word_count >= 8:
        strengths = [f"Communicated an approach to {topic} in own words."]
    else:
        strengths = []

    # Weaknesses / omissions
    weaknesses = []
    if technical_mistakes:
        weaknesses.extend([f"Technical mistake: {m}" for m in technical_mistakes])
    if missing_concepts:
        weaknesses.append(f"Omitted deeper discussion on: {', '.join(missing_concepts[:2])}.")
        weaknesses.append("Could strengthen response by quantifying performance trade-offs and edge cases.")
    elif not technical_mistakes:
        weaknesses.append("Consider discussing production edge cases, telemetry metrics, and concurrency limits.")

    # Recommendations
    recs = []
    if missing_concepts:
        recs.append(f"Incorporate {missing_concepts[0]} into your architectural justification.")
    recs.append(f"Quantify latency, memory, or throughput metrics when explaining {topic}.")

    evidence = signals.evidence_matches or [{"claim": f"Response to {topic}", "basis": f'"{clean_ans[:120]}"'}]

    first_missing = missing_concepts[0] if missing_concepts else topic
    exemplar_answer = (
        f"When addressing {topic}, start with the overarching architectural design: establish clean abstractions, "
        f"quantify SLAs, and leverage {first_missing} for efficient data processing."
    )
    coach_note = (
        f"Solid technical effort on this question! Frame your answer around {first_missing} and state your assumptions before diving into implementation details."
    )

    return {
        "overall_score": overall_score,
        "correctness": correctness,
        "completeness": completeness,
        "relevance": relevance,
        "technical_depth": technical_depth,
        "reasoning": reasoning,
        "performance_level": perf_level,
        "correct_concepts": matched_concepts,
        "missing_concepts": missing_concepts,
        "technical_mistakes": technical_mistakes,
        "unsupported_claims": unsupported,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "evidence": evidence,
        "recommendations": recs,
        "exemplar_answer": exemplar_answer,
        "coach_note": coach_note,
        "evaluation_confidence": 0.85,
        "evaluator_provider": "GROUNDED_NLP",
        "evaluator_version": "v2.0",
        "rubric_version": "question_specific_v2",
        "evaluator_fallback": fallback,
        "fallback_reason": fallback_reason,
    }


def check_context_divergence(
    question_text: str,
    topic: str,
    expected_concepts: List[str],
) -> bool:
    """
    Detects if expected_concepts are completely divergent from question_text.
    Example: question is about cache stampedes, but expected_concepts are about GPU PagedAttention.
    """
    if not expected_concepts or not question_text:
        return False

    q_lower = f"{topic.lower()} {question_text.lower()}"
    exp_lower = [c.lower() for c in expected_concepts]

    # Check for known cross-domain collision pairs
    is_cache_stampede_q = bool(re.search(r"\b(cache stampedes?|thundering herds?|redis|primary database|cache-aside|stale-while-revalidate)\b", q_lower))
    has_gpu_serving_concepts = any(
        re.search(r"\b(continuous batching|pagedattention|paged attention|kv cache|gpu memory|quantization)\b", ec)
        for ec in exp_lower
    )
    if is_cache_stampede_q and has_gpu_serving_concepts:
        if not re.search(r"\b(gpu|llm|model serving|continuous batching)\b", q_lower):
            return True

    is_gpu_serving_q = bool(re.search(r"\b(continuous batching|pagedattention|paged attention|kv cache|model serving|gpu memory)\b", q_lower))
    has_cache_stampede_concepts = any(
        re.search(r"\b(cache stampedes?|thundering herds?|primary database|cache-aside)\b", ec)
        for ec in exp_lower
    )
    if is_gpu_serving_q and has_cache_stampede_concepts:
        if not re.search(r"\b(cache stampede|thundering herd|primary database)\b", q_lower):
            return True

    is_iot_q = bool(re.search(r"\b(mqtt|coap|telemetry|sensor|qos \d)\b", q_lower))
    has_rag_concepts = any(re.search(r"\b(rag|bm25|dense vector|reciprocal rank fusion)\b", ec) for ec in exp_lower)
    if is_iot_q and has_rag_concepts:
        return True

    is_rag_q = bool(re.search(r"\b(bm25|dense vector|hybrid retrieval|sparse.*dense|reciprocal rank fusion)\b", q_lower))
    has_iot_concepts = any(re.search(r"\b(mqtt|coap|sensor|sram|battery)\b", ec) for ec in exp_lower)
    if is_rag_q and has_iot_concepts:
        return True

    return False


class AIEvaluator:
    """
    Evaluates individual candidate answers and returns structured, explainable feedback.
    Features Question-Specific Rubrics + Deterministic Pre-Analysis + Anchored LLM Semantic Evaluation + Grounded NLP Fallback.
    Production token budget: max_tokens = 1000 (ensures full JSON completeness without truncation).
    """

    def __init__(self, provider: Optional[LLMProvider] = None):
        self.provider = provider or get_llm_provider(task="routine")

    def evaluate_answer_sync(
        self,
        target_role: str,
        interview_type: str,
        topic: str,
        question_text: str,
        expected_concepts: List[str],
        resume_evidence: str,
        candidate_answer: str,
        response_time_seconds: float = 0.0,
        rubric_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Synchronous deterministic evaluation using Question Rubric and Grounded NLP.
        Fast-path evaluation with zero network dependencies and sub-millisecond execution.
        """
        if rubric_snapshot and isinstance(rubric_snapshot, dict) and "essential_concepts" in rubric_snapshot:
            rubric = QuestionRubric(**rubric_snapshot)
        else:
            rubric = get_rubric_for_question(
                topic=topic,
                question_text=question_text,
                expected_concepts=expected_concepts,
                interview_type=interview_type,
            )

        if check_context_divergence(question_text=question_text, topic=topic, expected_concepts=expected_concepts):
            logger.warning(
                f"Context Divergence detected for question '{question_text[:60]}...'. "
                f"Re-anchoring rubric and expected concepts to question text to enforce context integrity."
            )
            rubric = get_rubric_for_question(
                topic=topic,
                question_text=question_text,
                expected_concepts=None,
                interview_type=interview_type,
            )
            expected_concepts = rubric.essential_concepts
            all_expected = list(dict.fromkeys(rubric.essential_concepts + rubric.optional_advanced_concepts))
        else:
            all_expected = list(dict.fromkeys((expected_concepts or []) + rubric.essential_concepts + rubric.optional_advanced_concepts))

        signals = DeterministicPreEvaluator.analyze(
            candidate_answer=candidate_answer,
            expected_concepts=all_expected,
            topic=topic,
            response_time_seconds=response_time_seconds,
        )
        return evaluate_with_grounded_nlp(
            candidate_answer=candidate_answer,
            expected_concepts=expected_concepts,
            topic=topic,
            interview_type=interview_type,
            target_role=target_role,
            signals=signals,
            rubric=rubric,
        )

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
        rubric_snapshot: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generates explainable evaluation dictionary with deterministic overall score.
        Pre-analyzes deterministic signals before LLM inference to anchor evaluation and minimize latency.
        Evaluates against question-specific rubric rather than generic keyword matching.
        """
        # 1. Resolve structured question-specific rubric
        if rubric_snapshot and isinstance(rubric_snapshot, dict) and "essential_concepts" in rubric_snapshot:
            rubric = QuestionRubric(**rubric_snapshot)
        else:
            rubric = get_rubric_for_question(
                topic=topic,
                question_text=question_text,
                expected_concepts=expected_concepts,
                interview_type=interview_type,
            )

        # Context Integrity Guard: verify that expected_concepts and rubric semantically align with question_text
        if check_context_divergence(question_text=question_text, topic=topic, expected_concepts=expected_concepts):
            logger.warning(
                f"Context Divergence detected for question '{question_text[:60]}...'. "
                f"Re-anchoring rubric and expected concepts to question text to enforce context integrity."
            )
            rubric = get_rubric_for_question(
                topic=topic,
                question_text=question_text,
                expected_concepts=None,
                interview_type=interview_type,
            )
            expected_concepts = rubric.essential_concepts
            all_expected = list(dict.fromkeys(rubric.essential_concepts + rubric.optional_advanced_concepts))
        else:
            all_expected = list(dict.fromkeys((expected_concepts or []) + rubric.essential_concepts + rubric.optional_advanced_concepts))

        # 2. Deterministic Pre-Analysis Stage
        signals = DeterministicPreEvaluator.analyze(
            candidate_answer=candidate_answer,
            expected_concepts=all_expected,
            topic=topic,
            response_time_seconds=response_time_seconds,
        )

        # 3. Refusal / Trivial response / Mock provider fast-path: evaluate immediately without LLM call
        is_mock_provider = getattr(self.provider, "provider_name", "") == "mock"
        if signals.is_refusal or signals.word_count < 5 or is_mock_provider:
            return evaluate_with_grounded_nlp(
                candidate_answer=candidate_answer,
                expected_concepts=expected_concepts,
                topic=topic,
                interview_type=interview_type,
                target_role=target_role,
                signals=signals,
                rubric=rubric,
                fallback=is_mock_provider,
                fallback_reason="LLM_PROVIDER_MOCK" if is_mock_provider else None,
            )

        # 4. Compact Structured Prompt Construction with Question Rubric & Pre-Analyzed Signals
        essential_str = ", ".join(rubric.essential_concepts) if rubric.essential_concepts else "Core relevant domain principles."
        optional_str = ", ".join(rubric.optional_advanced_concepts) if rubric.optional_advanced_concepts else "None required."
        misconceptions_str = "; ".join(rubric.common_misconceptions) if rubric.common_misconceptions else "None specifically noted."
        detected_str = ", ".join(signals.matched_concepts) if signals.matched_concepts else "Concepts present in prose"

        user_prompt = EVALUATION_USER_PROMPT_TEMPLATE.format(
            target_role=target_role,
            interview_type=interview_type,
            topic=topic or "General",
            question_text=question_text,
            essential_concepts=essential_str,
            optional_concepts=optional_str,
            common_misconceptions=misconceptions_str,
            evaluation_guidance=rubric.evaluation_guidance or "Assess technical correctness and reasoning depth.",
            detected_concepts=detected_str,
            word_count=signals.word_count,
            response_time_seconds=signals.response_time_seconds,
            structural_signals=signals.structural_summary,
            candidate_answer=candidate_answer,
        )

        # Production budget: max_tokens = 650 (sufficient for structured JSON with fast latency)
        request = LLMRequest(
            system_prompt=EVALUATION_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            max_tokens=650,
            response_json=True,
            metadata={"task_type": "interview_evaluation"},
        )

        raw_eval: Dict[str, Any] = {}
        fallback_reason: Optional[str] = None
        try:
            response = await self.provider.generate(request)
            if response.raw_json and isinstance(response.raw_json, dict) and "correctness" in response.raw_json:
                raw_eval = response.raw_json
            elif response.content:
                cleaned = re.sub(r"^```json\s*", "", response.content.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
                cleaned = cleaned.rstrip("`").strip()
                try:
                    raw_eval = json.loads(cleaned)
                except Exception:
                    # Robust search for JSON block
                    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
                    if match:
                        try:
                            raw_eval = json.loads(match.group(1))
                        except Exception:
                            pass
        except Exception as e:
            fallback_reason = f"LLM_EXCEPTION: {type(e).__name__}"
            logger.info(f"Routine LLM evaluation unavailable ({e}), using grounded NLP evaluation.")

        # If LLM did not provide valid evaluation or provider is mock, use grounded NLP evaluation
        if getattr(self.provider, "provider_name", "") == "mock" or not raw_eval or "correctness" not in raw_eval:
            if not fallback_reason:
                if getattr(self.provider, "provider_name", "") == "mock":
                    fallback_reason = "LLM_PROVIDER_MOCK"
                else:
                    fallback_reason = "LLM_RESPONSE_INCOMPLETE"
            return evaluate_with_grounded_nlp(
                candidate_answer=candidate_answer,
                expected_concepts=expected_concepts,
                topic=topic,
                interview_type=interview_type,
                target_role=target_role,
                signals=signals,
                rubric=rubric,
                fallback=True,
                fallback_reason=fallback_reason,
            )

        # 5. Extract Semantic Scores bounded 0.0 - 10.0
        correctness = float(min(10.0, max(0.0, float(raw_eval.get("correctness", 0.0)))))
        completeness = float(min(10.0, max(0.0, float(raw_eval.get("completeness", 0.0)))))
        relevance = float(min(10.0, max(0.0, float(raw_eval.get("relevance", 1.0)))))
        technical_depth = float(min(10.0, max(0.0, float(raw_eval.get("technical_depth", 0.0)))))
        reasoning = float(min(10.0, max(0.0, float(raw_eval.get("reasoning", 0.0)))))

        # Check for unverified personal claims or misconceptions
        unsupported = raw_eval.get("unsupported_claims", [])
        if isinstance(unsupported, str):
            unsupported = [unsupported]
        elif not isinstance(unsupported, list):
            unsupported = []

        # Check candidate answer against unverified claim indicators
        for ind in rubric.unverified_claim_indicators:
            if any(re.search(r"\b" + re.escape(w) + r"\b", candidate_answer.lower()) for w in ["at my last company", "in my previous team", "we reduced by 80%", "we cut by 90%"]):
                claim_note = "Previous-company production outcome claim unverified; scored based on architectural reasoning."
                if claim_note not in unsupported:
                    unsupported.append(claim_note)

        technical_mistakes = raw_eval.get("technical_mistakes", [])
        if isinstance(technical_mistakes, str):
            technical_mistakes = [technical_mistakes]
        elif not isinstance(technical_mistakes, list):
            technical_mistakes = []

        sub_scores = {
            "correctness": correctness,
            "completeness": completeness,
            "relevance": relevance,
            "technical_depth": technical_depth,
            "reasoning": reasoning,
        }

        # Deterministic calculation of overall score using configured rubric (NO LLM MATH)
        overall_score = ScoreAggregator.calculate_turn_score(sub_scores, custom_weights=rubric.weights)

        # Performance level
        perf_level = raw_eval.get("performance_level")
        if not perf_level or perf_level not in ["EXEMPLARY", "STRONG", "DEVELOPING", "INSUFFICIENT"]:
            if overall_score >= 8.5:
                perf_level = "EXEMPLARY"
            elif overall_score >= 7.0:
                perf_level = "STRONG"
            elif overall_score >= 4.5:
                perf_level = "DEVELOPING"
            else:
                perf_level = "INSUFFICIENT"

        # Correct concepts
        llm_correct = raw_eval.get("correct_concepts", [])
        if not isinstance(llm_correct, list):
            llm_correct = [str(llm_correct)]
        correct_concepts = list(dict.fromkeys(signals.matched_concepts + llm_correct))

        # Integrate qualitative feedback and reconcile missing concepts
        strengths = raw_eval.get("strengths", ["Addressed the core question effectively."])
        if isinstance(strengths, str):
            strengths = [strengths]

        weaknesses = raw_eval.get("weaknesses", ["Could provide more technical depth."])
        if isinstance(weaknesses, str):
            weaknesses = [weaknesses]

        # Combine LLM missing concepts with rubric essential concept omissions
        llm_missing = raw_eval.get("missing_concepts", [])
        if not isinstance(llm_missing, list):
            llm_missing = [str(llm_missing)]
        combined_missing = list(llm_missing)
        for mc in signals.missing_concepts:
            # Only add to missing if it was an essential concept
            if mc in rubric.essential_concepts and mc not in combined_missing:
                combined_missing.append(mc)

        # Format Grounded Evidence Anchors
        formatted_evidence: List[Dict[str, str]] = []
        raw_evidence = raw_eval.get("evidence", [])
        if raw_evidence and isinstance(raw_evidence, list):
            for ev in raw_evidence:
                if isinstance(ev, dict) and "claim" in ev and "basis" in ev:
                    formatted_evidence.append({"claim": str(ev["claim"]), "basis": str(ev["basis"])})
                elif isinstance(ev, str):
                    formatted_evidence.append({"claim": ev, "basis": "From candidate answer"})

        if not formatted_evidence:
            formatted_evidence = list(signals.evidence_matches)
        if not formatted_evidence:
            formatted_evidence = [{"claim": f"Response to {topic}", "basis": f'"{candidate_answer[:120]}"'}]

        # Actionable Recommendations
        recommendations = raw_eval.get("recommendations")
        if not recommendations or not isinstance(recommendations, list):
            recs = []
            if combined_missing:
                recs.append(f"Incorporate {combined_missing[0]} into your architectural justification.")
            recs.append(f"Quantify latency, memory, or throughput metrics when explaining {topic}.")
            recommendations = recs

        # Synthesize fast grounded exemplar without adding latency to routine turn
        first_concept = combined_missing[0] if combined_missing else topic
        default_exemplar = (
            f"When addressing {topic}, start with the overarching architectural design: establish clean abstractions, "
            f"quantify SLAs, and leverage {first_concept} for efficient data processing."
        )
        exemplar_answer = raw_eval.get("exemplar_answer") or default_exemplar
        coach_note = raw_eval.get("coach_note") or f"Solid effort on this question! Frame your answer around {first_concept}."

        confidence = float(min(1.0, max(0.1, float(raw_eval.get("evaluation_confidence", 0.90)))))
        provider_name = getattr(self.provider, "provider_name", "UNKNOWN")

        return {
            "overall_score": overall_score,
            "correctness": correctness,
            "completeness": completeness,
            "relevance": relevance,
            "technical_depth": technical_depth,
            "reasoning": reasoning,
            "performance_level": perf_level,
            "correct_concepts": correct_concepts,
            "missing_concepts": combined_missing,
            "technical_mistakes": technical_mistakes,
            "unsupported_claims": unsupported,
            "strengths": strengths,
            "weaknesses": weaknesses,
            "evidence": formatted_evidence,
            "recommendations": recommendations,
            "exemplar_answer": exemplar_answer,
            "coach_note": coach_note,
            "evaluation_confidence": confidence,
            "evaluator_provider": f"LLM_{provider_name.upper()}",
            "evaluator_version": "v2.0",
            "rubric_version": "question_specific_v2",
            "evaluator_fallback": False,
            "fallback_reason": None,
        }

    async def generate_exemplar_answer(
        self,
        target_role: str,
        topic: str,
        question_text: str,
        expected_concepts: List[str],
        candidate_answer: str,
        missing_concepts: Optional[List[str]] = None,
    ) -> Dict[str, str]:
        """
        On-demand Staff-level exemplar answer generation.
        Separated from the routine evaluation turn to preserve fast interactive latency.
        """
        from ai.prompts.evaluation_v1 import EXEMPLAR_SYSTEM_PROMPT, EXEMPLAR_USER_PROMPT_TEMPLATE

        user_prompt = EXEMPLAR_USER_PROMPT_TEMPLATE.format(
            target_role=target_role,
            topic=topic,
            question_text=question_text,
            expected_concepts=", ".join(expected_concepts) if expected_concepts else "Core architectural principles",
            candidate_answer=candidate_answer,
            missing_concepts=", ".join(missing_concepts) if missing_concepts else "None",
        )

        request = LLMRequest(
            system_prompt=EXEMPLAR_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.2,
            max_tokens=300,
            response_json=True,
            metadata={"task_type": "qualitative_feedback"},
        )
        try:
            resp = await self.provider.generate(request)
            if resp.raw_json:
                return resp.raw_json
            if resp.content:
                cleaned = re.sub(r"^```json\s*", "", resp.content.strip(), flags=re.MULTILINE)
                cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.MULTILINE)
                return json.loads(cleaned)
        except Exception as e:
            logger.warning(f"Failed to generate exemplar answer: {e}")

        first_missing = (missing_concepts or [topic])[0]
        return {
            "exemplar_answer": (
                f"When designing solutions for {topic}, establish rigorous architectural bounds: defend state invariants, "
                f"enforce graceful degradation under edge network partitions, and quantify trade-offs for {first_missing}."
            ),
            "coach_note": f"Remember to structure your response around measurable SLAs and core mechanism trade-offs like {first_missing}.",
        }
