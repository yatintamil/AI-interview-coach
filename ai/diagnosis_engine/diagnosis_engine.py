"""
Transfer Failure Diagnosis Engine Orchestrator.
Combines deterministic telemetry, concept coverage, evaluation rubrics,
and structured AI reasoning to diagnose WHY a candidate failed transfer.
"""

import json
import logging
import re
from typing import Optional, Dict, Any, List

from backend.domain.ai.interfaces import LLMProvider, LLMRequest
from backend.infrastructure.ai.factory import get_llm_provider
from backend.domain.transfer.diagnosis_types import TransferFailureType
from backend.domain.transfer.coaching_types import CoachingInterventionType
from backend.domain.transfer.schemas import (
    TransferFailureDiagnosisDTO,
    EvidenceItemDTO,
)
from ai.diagnosis_engine.schemas import (
    DiagnosisRequest,
    DeterministicSignals,
    DiagnosisValidationResult,
)
from ai.diagnosis_engine.interfaces import (
    ISignalExtractor,
    IDiagnosisValidator,
    ITransferDiagnosisEngine,
)
from ai.diagnosis_engine.signal_extractor import SignalExtractor
from ai.diagnosis_engine.validators import DiagnosisValidator

logger = logging.getLogger(__name__)

DEFAULT_FAILURE_INTERVENTIONS: Dict[TransferFailureType, CoachingInterventionType] = {
    TransferFailureType.NONE: CoachingInterventionType.TRANSFER_CHALLENGE,
    TransferFailureType.SURFACE_PATTERN_DEPENDENCE: CoachingInterventionType.COUNTEREXAMPLE,
    TransferFailureType.MISSING_CONCEPTUAL_MODEL: CoachingInterventionType.EXPLANATION,
    TransferFailureType.WEAK_REQUIREMENT_ANALYSIS: CoachingInterventionType.CLARIFICATION,
    TransferFailureType.POOR_ABSTRACTION: CoachingInterventionType.ANALOGY,
    TransferFailureType.REASONING_FAILURE: CoachingInterventionType.SOCRATIC_QUESTION,
    TransferFailureType.COMMUNICATION_BREAKDOWN: CoachingInterventionType.DECOMPOSITION,
    TransferFailureType.COGNITIVE_OVERLOAD: CoachingInterventionType.MINIMAL_HINT,
    TransferFailureType.EXCESSIVE_SCAFFOLD_DEPENDENCY: CoachingInterventionType.RETRY,
}

DIAGNOSIS_SYSTEM_PROMPT = """You are an expert psychometric and technical interview diagnostic assessor.
Your objective is to determine WHY a candidate failed to transfer an interview competency to an unseen transfer challenge.
Do NOT simply say if the answer is right or wrong. Diagnose the root cause from the following operational taxonomy:

- SURFACE_PATTERN_DEPENDENCE: Candidate relied on memorized keywords/solutions from training; failed because the surface domain shifted.
- MISSING_CONCEPTUAL_MODEL: Candidate lacks fundamental conceptual knowledge of the underlying invariant or mechanism.
- WEAK_REQUIREMENT_ANALYSIS: Candidate jumped to implementation without analyzing invariants, scale, constraints, or clarifying ambiguities.
- POOR_ABSTRACTION: Candidate cannot separate core architectural invariants from incidental implementation/tooling details.
- REASONING_FAILURE: Candidate exhibited invalid deductions, flawed trade-off proofs, or erroneous scale/complexity analysis.
- COMMUNICATION_BREAKDOWN: Candidate possesses the concepts but produced an incoherent, fragmented, or unorganized presentation.
- COGNITIVE_OVERLOAD: Candidate experienced disorientation, extreme hesitation, fragmented reasoning, or breakdown under complexity.
- EXCESSIVE_SCAFFOLD_DEPENDENCY: Candidate solved steps only when prompted, unable to work autonomously.
- NONE: Successful independent transfer. The candidate demonstrated mastery of the invariants in the new domain.

CRITICAL EVIDENCE GROUNDING REQUIREMENT:
Every evidence item must have:
1. "claim": The diagnostic finding.
2. "basis": MUST BE AN EXACT VERBATIM QUOTE from the candidate's answer (or objective telemetry). Do NOT fabricate quotes.

Return ONLY a valid JSON object matching this schema:
{
  "failure_type": "SURFACE_PATTERN_DEPENDENCE",
  "confidence": 0.85,
  "affected_skill": "consistent_hashing",
  "diagnostic_reasoning": "Detailed justification...",
  "recommended_intervention": "COUNTEREXAMPLE",
  "evidence": [
    {
      "claim": "Claim description",
      "basis": "exact quote from candidate response"
    }
  ]
}
"""


class TransferDiagnosisEngine(ITransferDiagnosisEngine):
    """
    Orchestrates the transfer failure diagnosis pipeline:
    Transfer Attempt -> Evaluation -> Signal Extraction -> Structured Reasoning -> Validation -> TransferFailureDiagnosisDTO
    """

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        signal_extractor: Optional[ISignalExtractor] = None,
        validator: Optional[IDiagnosisValidator] = None,
    ):
        self.provider = provider or get_llm_provider(task="complex")
        self.signal_extractor = signal_extractor or SignalExtractor()
        self.validator = validator or DiagnosisValidator()

    async def diagnose(self, request: DiagnosisRequest) -> TransferFailureDiagnosisDTO:
        """
        Diagnoses the root cause of transfer failure using deterministic signals,
        candidate history, and structured LLM reasoning.
        """
        # 1. Deterministic Signal Extraction
        signals = self.signal_extractor.extract_signals(request)

        # 2. If a mock response is explicitly queued for testing, prioritize LLM pathway
        has_custom_mock = (
            getattr(self.provider, "custom_responses", None) is not None
            and len(self.provider.custom_responses) > 0
        )
        if has_custom_mock:
            try:
                llm_diagnosis = await self._reason_with_llm(request, signals)
                validation = self.validator.validate(request, llm_diagnosis)
                if validation.is_valid:
                    return llm_diagnosis
                logger.warning(
                    f"Mock LLM diagnosis failed validation: {'; '.join(validation.failure_reasons)}. "
                    "Falling back to deterministic synthesis."
                )
            except Exception as e:
                logger.warning(f"Mock LLM reasoning error: {e}. Falling back to deterministic synthesis.")
            return self._synthesize_deterministic_diagnosis(request, signals)

        # 3. Deterministic Fast Paths (for live/production and offline default)
        # Fast path 3a: High score & good concept coverage -> NONE
        if (
            signals.overall_score >= 7.0
            and signals.concept_coverage_ratio >= 0.5
            and not signals.is_refusal
            and not signals.is_scaffold_dependent
            and not signals.surface_pattern_leakage_detected
        ):
            return self._build_successful_transfer_diagnosis(request, signals)

        # Fast path 3b: Blatant refusal or empty response -> MISSING_CONCEPTUAL_MODEL
        if signals.is_refusal or signals.is_too_short:
            return self._build_refusal_diagnosis(request, signals)

        # Fast path 3c: Excessive scaffold dependency
        if signals.hints_requested_count >= 2 and signals.is_scaffold_dependent and signals.overall_score < 7.0:
            return self._build_scaffold_dependency_diagnosis(request, signals)

        # Fast path 3d: Surface pattern leakage on L2+ transfer
        if signals.surface_pattern_leakage_detected and request.task.transfer_level.value in (
            "L2_NEAR_TRANSFER", "L3_FAR_TRANSFER", "L4_AMBIGUOUS_TRANSFER", "L5_INDEPENDENT_TRANSFER"
        ):
            return self._build_surface_pattern_diagnosis(request, signals)

        # 4. Structured LLM Reasoning with Live Provider
        is_live_provider = self.provider and getattr(self.provider, "provider_name", "mock") != "mock"
        if is_live_provider:
            try:
                llm_diagnosis = await self._reason_with_llm(request, signals)
                validation = self.validator.validate(request, llm_diagnosis)
                if validation.is_valid:
                    return llm_diagnosis
                logger.warning(
                    f"LLM diagnosis failed validation: {'; '.join(validation.failure_reasons)}. "
                    "Falling back to deterministic synthesis."
                )
            except Exception as e:
                logger.warning(f"LLM reasoning error during diagnosis: {e}. Falling back to deterministic synthesis.")

        # 5. Deterministic Rule Synthesis Fallback
        return self._synthesize_deterministic_diagnosis(request, signals)

    async def _reason_with_llm(
        self, request: DiagnosisRequest, signals: DeterministicSignals
    ) -> TransferFailureDiagnosisDTO:
        """Invokes the LLM with structured evidence to produce an explainable diagnosis."""
        user_prompt = f"""
TASK DEFINITION:
- Skill: {request.task.skill_id}
- Transfer Level: {request.task.transfer_level.value}
- Surface Domain: {request.task.surface_context}
- Core Invariants: {', '.join(request.task.core_invariants)}
- Expected Concepts: {', '.join(request.task.expected_concepts)}

PARENT DOMAIN CONTEXT:
{json.dumps(request.parent_task_context or {}, indent=2)}

CANDIDATE ANSWER:
\"\"\"{request.candidate_answer}\"\"\"

EVALUATION SUMMARY:
{json.dumps(request.evaluation or {}, indent=2)}

DETERMINISTIC SIGNALS:
- Refusal: {signals.is_refusal}
- Concept Coverage Ratio: {signals.concept_coverage_ratio}
- Covered Concepts: {signals.covered_concepts}
- Missing Concepts: {signals.missing_expected_concepts}
- Invariants Addressed Ratio: {signals.invariants_addressed_ratio}
- Surface Pattern Leakage Detected: {signals.surface_pattern_leakage_detected} (Hits: {signals.parent_surface_keyword_hits})
- Hints Requested: {signals.hints_requested_count}
- Scaffold Level: {signals.scaffold_level_applied}
- Overall Score: {signals.overall_score} / 10.0
- Sub-scores: {signals.sub_scores}
- Ambiguity Clarification Detected: {signals.ambiguity_clarification_detected}

DIAGNOSTIC INSTRUCTIONS:
Analyze the candidate's answer and evidence. Identify the single primary failure type from the taxonomy.
Explain the root cause and provide verbatim evidence quotes from the candidate answer.
"""
        req = LLMRequest(
            system_prompt=DIAGNOSIS_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.1,
            response_json=True,
            metadata={"task_type": "failure_diagnosis"},
        )
        resp = await self.provider.generate(req)
        raw_dict = resp.raw_json
        if not raw_dict and resp.content:
            raw_dict = json.loads(resp.content)

        failure_type = TransferFailureType(raw_dict["failure_type"])
        recommended_intervention = CoachingInterventionType(
            raw_dict.get(
                "recommended_intervention",
                DEFAULT_FAILURE_INTERVENTIONS.get(failure_type, CoachingInterventionType.PROMPT).value,
            )
        )

        evidence_items = [
            EvidenceItemDTO(claim=item["claim"], basis=item["basis"])
            for item in raw_dict.get("evidence", [])
        ]

        # Use confidence from model, bounded to [0.0, 1.0] without claiming statistical calibration
        conf = max(0.0, min(1.0, float(raw_dict.get("confidence", 0.8))))

        return TransferFailureDiagnosisDTO(
            failure_type=failure_type,
            confidence=round(conf, 2),
            affected_skill=raw_dict.get("affected_skill", request.task.skill_id),
            deterministic_signals=signals.model_dump(),
            evidence=evidence_items,
            recommended_intervention=recommended_intervention,
            diagnostic_reasoning=raw_dict.get("diagnostic_reasoning", "Diagnosed via structured AI evaluation."),
        )

    def _build_successful_transfer_diagnosis(
        self, request: DiagnosisRequest, signals: DeterministicSignals
    ) -> TransferFailureDiagnosisDTO:
        """Constructs diagnosis for successful transfer."""
        basis = "Candidate covered invariants independently."
        # Extract a short excerpt from candidate answer for grounding
        sentences = [s.strip() for s in re.split(r"[.!?\n]", request.candidate_answer) if len(s.strip()) > 15]
        if sentences:
            basis = sentences[0]

        evidence = [
            EvidenceItemDTO(
                claim="Demonstrated required conceptual invariants in the transfer domain.",
                basis=basis,
            ),
            EvidenceItemDTO(
                claim=f"High evaluation performance without scaffold reliance.",
                basis=f"score={signals.overall_score}, hints_requested={signals.hints_requested_count}",
            ),
        ]
        return TransferFailureDiagnosisDTO(
            failure_type=TransferFailureType.NONE,
            confidence=0.92,
            affected_skill=request.task.skill_id,
            deterministic_signals=signals.model_dump(),
            evidence=evidence,
            recommended_intervention=CoachingInterventionType.TRANSFER_CHALLENGE,
            diagnostic_reasoning="Candidate successfully transferred theoretical invariants to the novel domain context.",
        )

    def _build_refusal_diagnosis(
        self, request: DiagnosisRequest, signals: DeterministicSignals
    ) -> TransferFailureDiagnosisDTO:
        """Constructs diagnosis for explicit candidate refusal or ultra-short abandonment."""
        verbatim_basis = request.candidate_answer.strip() if request.candidate_answer.strip() else "Empty response"
        evidence = [
            EvidenceItemDTO(
                claim="Candidate explicitly declined or provided inadequate response to evaluate.",
                basis=verbatim_basis,
            ),
            EvidenceItemDTO(
                claim="Zero expected technical concepts covered.",
                basis=f"concept_coverage_ratio={signals.concept_coverage_ratio}",
            ),
        ]
        return TransferFailureDiagnosisDTO(
            failure_type=TransferFailureType.MISSING_CONCEPTUAL_MODEL,
            confidence=0.95,
            affected_skill=request.task.skill_id,
            deterministic_signals=signals.model_dump(),
            evidence=evidence,
            recommended_intervention=CoachingInterventionType.EXPLANATION,
            diagnostic_reasoning="Candidate response indicates absent conceptual foundation for the assessed mechanism.",
        )

    def _build_scaffold_dependency_diagnosis(
        self, request: DiagnosisRequest, signals: DeterministicSignals
    ) -> TransferFailureDiagnosisDTO:
        """Constructs diagnosis for excessive hint / scaffold reliance."""
        sentences = [s.strip() for s in re.split(r"[.!?\n]", request.candidate_answer) if len(s.strip()) > 10]
        basis = sentences[0] if sentences else request.candidate_answer.strip()
        evidence = [
            EvidenceItemDTO(
                claim="Candidate required multiple hints and scaffolds during transfer test.",
                basis=f"hints_requested_count={signals.hints_requested_count}",
            ),
            EvidenceItemDTO(
                claim="Autonomous execution was not demonstrated.",
                basis=basis,
            ),
        ]
        return TransferFailureDiagnosisDTO(
            failure_type=TransferFailureType.EXCESSIVE_SCAFFOLD_DEPENDENCY,
            confidence=0.88,
            affected_skill=request.task.skill_id,
            deterministic_signals=signals.model_dump(),
            evidence=evidence,
            recommended_intervention=CoachingInterventionType.RETRY,
            diagnostic_reasoning=(
                f"Candidate requested {signals.hints_requested_count} hints and relied on active scaffolding, "
                "demonstrating low autonomous transfer capacity."
            ),
        )

    def _build_surface_pattern_diagnosis(
        self, request: DiagnosisRequest, signals: DeterministicSignals
    ) -> TransferFailureDiagnosisDTO:
        """Constructs diagnosis for candidate leaking training task specifics into transfer domain."""
        leaked_kw = signals.parent_surface_keyword_hits[0] if signals.parent_surface_keyword_hits else "parent"
        # Find sentence containing the leaked keyword for verbatim basis
        matched_sentence = None
        for s in re.split(r"[.!?\n]", request.candidate_answer):
            if leaked_kw.lower() in s.lower() and len(s.strip()) > 8:
                matched_sentence = s.strip()
                break
        verbatim_basis = matched_sentence or request.candidate_answer.strip()

        evidence = [
            EvidenceItemDTO(
                claim=f"Candidate reused training domain keywords ('{leaked_kw}') in the transfer scenario.",
                basis=verbatim_basis,
            ),
            EvidenceItemDTO(
                claim="Surface pattern leakage detected across different domain framing.",
                basis=f"parent_surface_keyword_hits={signals.parent_surface_keyword_hits}",
            ),
        ]
        return TransferFailureDiagnosisDTO(
            failure_type=TransferFailureType.SURFACE_PATTERN_DEPENDENCE,
            confidence=0.90,
            affected_skill=request.task.skill_id,
            deterministic_signals=signals.model_dump(),
            evidence=evidence,
            recommended_intervention=CoachingInterventionType.COUNTEREXAMPLE,
            diagnostic_reasoning=(
                f"Candidate exhibited surface-pattern dependence by attempting to apply specifics of the training domain "
                f"('{leaked_kw}') to '{request.task.surface_context}'."
            ),
        )

    def _synthesize_deterministic_diagnosis(
        self, request: DiagnosisRequest, signals: DeterministicSignals
    ) -> TransferFailureDiagnosisDTO:
        """
        Rule-based deterministic diagnosis synthesizer ensuring 100% testable,
        explainable root cause classification when LLM is offline or unavailable.
        """
        ans = request.candidate_answer.strip()
        sentences = [s.strip() for s in re.split(r"[.!?\n]", ans) if len(s.strip()) > 10]
        first_sentence = sentences[0] if sentences else (ans if ans else "No response text")

        # 1. Check L4 Ambiguous Transfer missing requirement analysis
        if (
            request.task.transfer_level.value == "L4_AMBIGUOUS_TRANSFER"
            and not signals.ambiguity_clarification_detected
            and signals.overall_score < 6.5
        ):
            failure_type = TransferFailureType.WEAK_REQUIREMENT_ANALYSIS
            claim = "Candidate proceeded into design without clarifying unstated scale or SLA constraints."
            basis = first_sentence
            reasoning = "Candidate failed to identify missing operational requirements in an ambiguous transfer scenario."
            confidence = 0.85

        # 2. Check Reasoning Failure (reasoning sub-score critically low compared to concepts)
        elif (
            signals.sub_scores.get("reasoning", 10.0) <= 4.0
            and signals.sub_scores.get("technical_depth", 0.0) >= 4.0
        ):
            failure_type = TransferFailureType.REASONING_FAILURE
            claim = "Candidate demonstrated flawed deductive proofs or trade-off evaluation."
            basis = sentences[min(1, len(sentences) - 1)] if sentences else first_sentence
            reasoning = "Sub-scores reveal significant logical flaws in complexity analysis or trade-off deductions."
            confidence = 0.82

        # 3. Check Communication Breakdown (concepts present but poor relevance or structure)
        elif (
            signals.concept_coverage_ratio >= 0.4
            and (signals.sub_scores.get("relevance", 10.0) <= 4.0 or signals.sub_scores.get("completeness", 10.0) <= 4.0)
        ):
            failure_type = TransferFailureType.COMMUNICATION_BREAKDOWN
            claim = "Candidate mentioned expected concepts but failed to articulate a coherent architectural structure."
            basis = first_sentence
            reasoning = "Concepts were mentioned but explanation lacked logical progression, clarity, or relevance."
            confidence = 0.80

        # 4. Check Cognitive Overload (high latency + very short/hesitant response)
        elif (
            signals.response_time_seconds > 90.0
            and signals.word_count < 30
            and signals.overall_score < 5.0
        ) or any(h in ans.lower() for h in ("overwhelmed", "lost", "too complex", "not sure where to start")):
            failure_type = TransferFailureType.COGNITIVE_OVERLOAD
            claim = "Candidate showed breakdown under task complexity with high hesitation."
            basis = first_sentence
            reasoning = "High latency combined with sparse, fragmented output indicates cognitive overload."
            confidence = 0.84

        # 5. Check Poor Abstraction (missing core invariants despite high word count)
        elif (
            signals.invariants_addressed_ratio < 0.4
            and signals.word_count >= 40
            and signals.overall_score < 6.0
        ):
            failure_type = TransferFailureType.POOR_ABSTRACTION
            claim = "Candidate focused on implementation minutiae while neglecting underlying theoretical invariants."
            basis = first_sentence
            reasoning = "Response discusses tooling or implementation details without abstracting the underlying invariant."
            confidence = 0.83

        # 6. Check Missing Conceptual Model (low concept coverage & low technical depth)
        elif signals.concept_coverage_ratio < 0.4 or signals.overall_score < 5.0:
            failure_type = TransferFailureType.MISSING_CONCEPTUAL_MODEL
            missing_str = ", ".join(signals.missing_expected_concepts[:2]) if signals.missing_expected_concepts else "invariants"
            claim = f"Candidate omitted fundamental mechanisms: {missing_str}."
            basis = first_sentence
            reasoning = "Low concept coverage and technical depth indicate candidate lacks the foundational conceptual model."
            confidence = 0.86

        # 7. Fallback: Acceptable performance -> NONE
        else:
            failure_type = TransferFailureType.NONE
            claim = "Demonstrated acceptable transfer competence across required invariants."
            basis = first_sentence
            reasoning = "Performance meets baseline criteria for invariant transfer without critical failure."
            confidence = 0.80

        intervention = DEFAULT_FAILURE_INTERVENTIONS.get(
            failure_type, CoachingInterventionType.PROMPT
        )

        evidence = [
            EvidenceItemDTO(claim=claim, basis=basis),
            EvidenceItemDTO(
                claim="Evaluation metric telemetry.",
                basis=f"overall_score={signals.overall_score}, concept_coverage={signals.concept_coverage_ratio}",
            ),
        ]

        return TransferFailureDiagnosisDTO(
            failure_type=failure_type,
            confidence=round(confidence, 2),
            affected_skill=request.task.skill_id,
            deterministic_signals=signals.model_dump(),
            evidence=evidence,
            recommended_intervention=intervention,
            diagnostic_reasoning=reasoning,
        )
