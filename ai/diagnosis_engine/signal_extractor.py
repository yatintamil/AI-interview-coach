"""
Deterministic Signal Extractor for Transfer Failure Diagnostics.
Extracts objective telemetry, concept coverage, invariant adherence,
and surface-leakage markers without LLM hallucinations.
"""

import re
from typing import List, Dict, Any, Set
from ai.evaluation_engine.evaluator import REFUSAL_PHRASES
from ai.diagnosis_engine.interfaces import ISignalExtractor
from ai.diagnosis_engine.schemas import DiagnosisRequest, DeterministicSignals
from ai.transfer_engine.normalization import normalize_surface_context

# Common stop words to exclude when extracting domain keywords
STOP_WORDS: Set[str] = {
    "a", "an", "the", "in", "on", "of", "for", "to", "at", "by", "with", "from",
    "is", "are", "was", "were", "be", "been", "being", "have", "has", "had",
    "do", "does", "did", "and", "or", "but", "if", "then", "else", "when",
    "up", "down", "out", "over", "under", "system", "design", "service", "platform"
}

# Ambiguity clarification indicator phrases (relevant for L4 AMBIGUOUS_TRANSFER)
AMBIGUITY_INDICATORS = [
    "assuming", "assumption", "clarify", "clarification", "sla", "slo",
    "traffic", "throughput", "qps", "retention", "scale", "unspecified",
    "trade-off", "requirements", "capacity estimation", "read/write ratio"
]


class SignalExtractor(ISignalExtractor):
    """
    Extracts deterministic signals from candidate responses, evaluation results,
    and attempt telemetry.
    """

    def extract_signals(self, request: DiagnosisRequest) -> DeterministicSignals:
        clean_ans = request.candidate_answer.strip()
        ans_lower = clean_ans.lower()
        words = re.findall(r"\b\w+\b", ans_lower)
        word_count = len(words)

        # 1. Refusal and Shortness Check
        is_refusal = any(phrase in ans_lower for phrase in REFUSAL_PHRASES)
        is_too_short = word_count < 10

        # 2. Concept Coverage
        expected_concepts = request.task.expected_concepts
        covered_concepts: List[str] = []
        missing_expected_concepts: List[str] = []

        for concept in expected_concepts:
            c_norm = concept.lower().strip()
            # Match exact phrase or substantial multi-word match
            if c_norm in ans_lower or any(part in ans_lower for part in c_norm.split() if len(part) > 4):
                covered_concepts.append(concept)
            else:
                missing_expected_concepts.append(concept)

        concept_coverage_ratio = (
            len(covered_concepts) / len(expected_concepts)
            if expected_concepts
            else 1.0
        )

        # 3. Core Invariants Addressed
        core_invariants = request.task.core_invariants
        addressed_invariants: List[str] = []
        missing_invariants: List[str] = []

        for invariant in core_invariants:
            inv_tokens = [t for t in re.findall(r"\b\w+\b", invariant.lower()) if t not in STOP_WORDS and len(t) > 3]
            # If at least half of key invariant tokens appear in answer, consider addressed
            hits = sum(1 for t in inv_tokens if t in ans_lower)
            if inv_tokens and hits >= max(1, len(inv_tokens) // 2):
                addressed_invariants.append(invariant)
            else:
                missing_invariants.append(invariant)

        invariants_addressed_ratio = (
            len(addressed_invariants) / len(core_invariants)
            if core_invariants
            else 1.0
        )

        # 4. Surface Pattern Leakage Detection (Parent Domain Memorization)
        parent_hits: List[str] = []
        surface_leakage = False
        if request.parent_task_context:
            parent_surface = normalize_surface_context(request.parent_task_context.get("surface_context", ""))
            parent_keywords = request.parent_task_context.get("domain_keywords", [])
            # Extract tokens from parent surface
            candidate_parent_tokens = set(
                t for t in re.findall(r"\b\w+\b", parent_surface.lower())
                if t not in STOP_WORDS and len(t) > 2
            )
            for kw in parent_keywords:
                for t in re.findall(r"\b\w+\b", str(kw).lower()):
                    if t not in STOP_WORDS and len(t) > 2:
                        candidate_parent_tokens.add(t)

            # Only check for leakage if current surface is different (L2+)
            curr_surface = normalize_surface_context(getattr(request.task, "surface_context", ""))
            curr_surface_tokens = set(
                t for t in re.findall(r"\b\w+\b", curr_surface.lower())
                if t not in STOP_WORDS
            )
            distinguishing_parent_tokens = candidate_parent_tokens - curr_surface_tokens

            for token in distinguishing_parent_tokens:
                if re.search(r"\b" + re.escape(token) + r"\b", ans_lower):
                    parent_hits.append(token)

            if parent_hits and len(parent_hits) >= 1:
                surface_leakage = True

        # 5. Scaffold & Hint Telemetry
        attempt_meta = request.attempt_metadata or {}
        hints_requested = int(attempt_meta.get("hints_requested_count", 0))
        scaffold_level = str(attempt_meta.get("scaffold_level_applied", "INDEPENDENT"))
        resp_time = float(attempt_meta.get("response_time_seconds", 0.0))
        is_scaffold_dependent = (
            hints_requested >= 2 or scaffold_level in ("HIGH_ASSISTANCE", "MEDIUM_ASSISTANCE")
        )

        # 6. Evaluation Sub-scores Extraction
        eval_data = request.evaluation or {}
        raw_overall = float(eval_data.get("overall_score", 0.0))
        # Normalize to 0-10 scale if represented as 0-100
        overall_score = raw_overall if raw_overall <= 10.0 else raw_overall / 10.0

        sub_scores: Dict[str, float] = {
            "correctness": float(eval_data.get("correctness", overall_score)),
            "completeness": float(eval_data.get("completeness", overall_score)),
            "relevance": float(eval_data.get("relevance", overall_score)),
            "technical_depth": float(eval_data.get("technical_depth", overall_score)),
            "reasoning": float(eval_data.get("reasoning", overall_score)),
        }

        # 7. Ambiguity Clarification Detection (L4)
        ambiguity_detected = any(ind in ans_lower for ind in AMBIGUITY_INDICATORS)

        # 8. Candidate History
        history = request.candidate_history or {}
        recurring_failures = list(history.get("recurring_failure_types", []))

        return DeterministicSignals(
            is_refusal=is_refusal,
            is_too_short=is_too_short,
            word_count=word_count,
            response_time_seconds=resp_time,
            concept_coverage_ratio=round(concept_coverage_ratio, 3),
            covered_concepts=covered_concepts,
            missing_expected_concepts=missing_expected_concepts,
            invariants_addressed_ratio=round(invariants_addressed_ratio, 3),
            addressed_invariants=addressed_invariants,
            missing_invariants=missing_invariants,
            parent_surface_keyword_hits=sorted(list(set(parent_hits))),
            surface_pattern_leakage_detected=surface_leakage,
            hints_requested_count=hints_requested,
            scaffold_level_applied=scaffold_level,
            is_scaffold_dependent=is_scaffold_dependent,
            overall_score=round(overall_score, 2),
            sub_scores={k: round(v, 2) for k, v in sub_scores.items()},
            ambiguity_clarification_detected=ambiguity_detected,
            historical_recurring_failures=recurring_failures,
        )
