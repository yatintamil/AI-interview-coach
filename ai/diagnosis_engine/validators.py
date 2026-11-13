"""
Validators for Transfer Failure Diagnosis.
Enforces empirical evidence grounding, verbatim quote verification,
confidence bounds, and taxonomy consistency.
"""

import re
from typing import List, Optional
from backend.domain.transfer.diagnosis_types import TransferFailureType
from backend.domain.transfer.coaching_types import CoachingInterventionType
from backend.domain.transfer.schemas import TransferFailureDiagnosisDTO
from ai.diagnosis_engine.interfaces import IDiagnosisValidator
from ai.diagnosis_engine.schemas import DiagnosisRequest, DiagnosisValidationResult


class DiagnosisValidator(IDiagnosisValidator):
    """
    Validates candidate TransferFailureDiagnosisDTO objects to prevent hallucinations,
    fabricated quotations, out-of-bound confidences, or unaligned skill diagnoses.
    """

    def validate(
        self, request: DiagnosisRequest, diagnosis: TransferFailureDiagnosisDTO
    ) -> DiagnosisValidationResult:
        failure_reasons: List[str] = []
        verbatim_basis_verified = True
        confidence_in_bounds = True
        skill_aligned = True

        # 1. Validate failure_type is a valid enum member
        if not isinstance(diagnosis.failure_type, TransferFailureType):
            try:
                TransferFailureType(diagnosis.failure_type)
            except ValueError:
                failure_reasons.append(f"Invalid failure_type: {diagnosis.failure_type}")

        # 2. Validate confidence bounds [0.0, 1.0]
        if diagnosis.confidence < 0.0 or diagnosis.confidence > 1.0:
            confidence_in_bounds = False
            failure_reasons.append(f"Confidence {diagnosis.confidence} is out of bounds [0.0, 1.0]")

        # 3. Validate affected skill alignment
        task_skill = request.task.skill_id.lower().strip()
        affected = diagnosis.affected_skill.lower().strip()
        invariants_text = " ".join(request.task.core_invariants).lower()

        # Skill is aligned if it contains or is contained in task skill or core invariants
        if not (
            affected in task_skill
            or task_skill in affected
            or affected in invariants_text
            or any(t in invariants_text for t in affected.split())
        ):
            # If not aligned with task competency, flag
            skill_aligned = False
            failure_reasons.append(
                f"affected_skill '{diagnosis.affected_skill}' not aligned with task skill '{request.task.skill_id}'"
            )

        # 4. Validate recommended intervention enum
        if not isinstance(diagnosis.recommended_intervention, CoachingInterventionType):
            try:
                CoachingInterventionType(diagnosis.recommended_intervention)
            except ValueError:
                failure_reasons.append(
                    f"Invalid recommended_intervention: {diagnosis.recommended_intervention}"
                )

        # 5. Validate diagnostic reasoning
        if not diagnosis.diagnostic_reasoning or len(diagnosis.diagnostic_reasoning.strip()) < 15:
            failure_reasons.append("diagnostic_reasoning must be at least 15 characters.")

        # 6. Verbatim Evidence Grounding Verification
        clean_ans_lower = request.candidate_answer.lower()
        signals = diagnosis.deterministic_signals or {}

        for idx, item in enumerate(diagnosis.evidence):
            claim = item.claim.strip()
            basis = item.basis.strip()

            if not claim:
                failure_reasons.append(f"Evidence item #{idx + 1} has an empty claim.")
            if not basis:
                failure_reasons.append(f"Evidence item #{idx + 1} has an empty basis.")
                continue

            # Strip quotation marks for checking
            normalized_basis = basis.strip('"\'').lower()

            # If basis refers to telemetry/deterministic signal (e.g., 'hints_requested_count=3', 'overall_score=4.5')
            is_telemetry_signal = any(
                sig in normalized_basis
                for sig in (
                    "hint", "scaffold", "score", "refusal", "coverage",
                    "latency", "time", "count", "metric", "signal", "ratio"
                )
            )

            if not is_telemetry_signal and len(normalized_basis) > 5:
                # Must exist as a substring in candidate answer
                # Allow minor punctuation variations by matching word sequences
                basis_words = re.findall(r"\b\w+\b", normalized_basis)
                if basis_words:
                    # Check if at least a 3-word sequence or whole basis is in answer
                    sample = " ".join(basis_words[:min(4, len(basis_words))])
                    if sample not in clean_ans_lower and normalized_basis not in clean_ans_lower:
                        verbatim_basis_verified = False
                        failure_reasons.append(
                            f"Evidence item #{idx + 1} basis '{basis}' is not found verbatim in candidate response."
                        )

        # 7. Logical Consistency
        if diagnosis.failure_type == TransferFailureType.NONE:
            # If overall score is catastrophically low (< 3.0), cannot diagnose NONE
            eval_score = float(signals.get("overall_score", 0.0))
            if eval_score < 3.0 and eval_score > 0.0:
                failure_reasons.append(
                    f"Inconsistent diagnosis: failure_type is NONE but overall score is {eval_score} (< 3.0)"
                )

        is_valid = (
            len(failure_reasons) == 0
            and verbatim_basis_verified
            and confidence_in_bounds
            and skill_aligned
        )

        return DiagnosisValidationResult(
            is_valid=is_valid,
            failure_reasons=failure_reasons,
            verbatim_basis_verified=verbatim_basis_verified,
            confidence_in_bounds=confidence_in_bounds,
            skill_aligned=skill_aligned,
        )
