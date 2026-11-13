"""
Multi-dimensional Transfer Task Validator.
Enforces empirical anti-triviality, core invariant preservation, surface distance,
and schema integrity.
"""

import re
from typing import Dict, Any, Set, List

from backend.domain.transfer.taxonomy import TransferLevel
from ai.transfer_engine.schemas import (
    TransferGenerationRequest,
    TransferValidationResult,
)
from ai.transfer_engine.normalization import normalize_surface_context


def _tokenize(text: str) -> Set[str]:
    """Tokenize text into lowercase alphanumeric word stems (>2 chars), excluding common stop words."""
    stop_words = {
        "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "with",
        "by", "about", "against", "between", "into", "through", "during", "before",
        "after", "above", "below", "from", "up", "down", "is", "are", "was", "were",
        "be", "been", "being", "have", "has", "had", "do", "does", "did", "you",
        "your", "would", "how", "what", "which", "system", "design", "explain",
    }
    tokens = set()
    for word in re.findall(r"\b[a-zA-Z0-9_-]{3,}\b", text.lower()):
        if word not in stop_words:
            tokens.add(word)
    return tokens


def calculate_jaccard_similarity(text1: str, text2: str) -> float:
    """Calculates Jaccard word-token set similarity between two text prompts."""
    t1 = _tokenize(text1)
    t2 = _tokenize(text2)
    if not t1 or not t2:
        return 0.0
    intersection = len(t1.intersection(t2))
    union = len(t1.union(t2))
    return round(intersection / max(1, union), 3)


class TransferTaskValidator:
    """
    Validates that a transfer task preserves underlying technical invariants while
    exhibiting appropriate situational surface transformation without trivial paraphrasing.
    """

    def validate(
        self, request: TransferGenerationRequest, candidate_task: Dict[str, Any]
    ) -> TransferValidationResult:
        reasons: List[str] = []

        # 1. Skill Alignment Check
        task_skill = str(candidate_task.get("skill_id") or "").strip()
        if task_skill != request.skill_id:
            reasons.append(
                f"Skill mismatch: expected '{request.skill_id}', got '{task_skill}'."
            )

        # 2. Transfer Level Consistency Check
        cand_level = candidate_task.get("transfer_level")
        if cand_level != request.transfer_level.value and cand_level != request.transfer_level:
            reasons.append(
                f"Transfer level mismatch: expected '{request.transfer_level.value}', got '{cand_level}'."
            )

        # 3. Core Invariant Preservation Check
        cand_invariants = set(candidate_task.get("core_invariants") or [])
        req_invariants = set(request.core_invariants)
        invariants_preserved = req_invariants.issubset(cand_invariants)
        if not invariants_preserved:
            missing = req_invariants - cand_invariants
            reasons.append(
                f"Core invariants violated: missing required invariants {sorted(list(missing))}."
            )

        # 4. Surface Context Shift Check
        base_surface = normalize_surface_context(request.base_surface_context).lower()
        cand_surface = normalize_surface_context(candidate_task.get("surface_context"))
        surface_shifted = True

        if not cand_surface:
            reasons.append("Surface context is empty.")
            surface_shifted = False
        elif request.transfer_level in [
            TransferLevel.L2_NEAR_TRANSFER,
            TransferLevel.L3_FAR_TRANSFER,
            TransferLevel.L4_AMBIGUOUS_TRANSFER,
            TransferLevel.L5_INDEPENDENT_TRANSFER,
        ]:
            cand_surface_lower = cand_surface.lower()
            if cand_surface_lower == base_surface or base_surface in cand_surface_lower:
                reasons.append(
                    f"Surface context '{cand_surface}' failed to sufficiently shift from base '{base_surface}' for {request.transfer_level.value}."
                )
                surface_shifted = False

        # 5. Anti-Triviality / Anti-Paraphrase Check
        jaccard = 0.0
        prompt_text = str(candidate_task.get("prompt_template") or "").strip()
        if not prompt_text:
            reasons.append("Prompt template is empty.")

        if request.parent_prompt and prompt_text:
            jaccard = calculate_jaccard_similarity(request.parent_prompt, prompt_text)
            # Rejects trivial paraphrasing if token overlap is too high for transfer challenges
            if request.transfer_level in [
                TransferLevel.L2_NEAR_TRANSFER,
                TransferLevel.L3_FAR_TRANSFER,
                TransferLevel.L4_AMBIGUOUS_TRANSFER,
                TransferLevel.L5_INDEPENDENT_TRANSFER,
            ]:
                if jaccard > 0.65:
                    reasons.append(
                        f"Trivial paraphrase detected: prompt has excessive similarity (Jaccard={jaccard:.2f} > 0.65) with parent prompt."
                    )
                # Exact prefix check (>35 chars)
                if len(prompt_text) > 35 and len(request.parent_prompt) > 35:
                    if prompt_text[:40].lower() == request.parent_prompt[:40].lower():
                        reasons.append("Trivial paraphrase detected: identical prompt prefix.")

        # 6. Expected Concepts Check
        expected_concepts = candidate_task.get("expected_concepts") or []
        if not expected_concepts:
            reasons.append("Expected concepts list cannot be empty.")

        # 7. Ambiguity Check (L4)
        if request.transfer_level == TransferLevel.L4_AMBIGUOUS_TRANSFER:
            # L4 requires missing/noisy constraints: prompt should not spoonfeed exact capacity or traffic numbers
            spoonfed_patterns = [r"\b\d+,\d+\s*qps\b", r"\b\d+\s*million\s*(requests|users)\b", r"\bexact\s*sla\s*of\b"]
            if any(re.search(pat, prompt_text.lower()) for pat in spoonfed_patterns):
                reasons.append("L4 Ambiguous Transfer task must not spoon-feed exact quantitative traffic/SLA constraints.")

        is_valid = len(reasons) == 0
        return TransferValidationResult(
            is_valid=is_valid,
            failure_reasons=reasons,
            jaccard_similarity=jaccard,
            invariants_preserved=invariants_preserved,
            surface_shifted=surface_shifted,
            level_consistent=(cand_level == request.transfer_level.value or cand_level == request.transfer_level),
        )
