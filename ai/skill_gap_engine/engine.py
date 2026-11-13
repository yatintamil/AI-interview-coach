"""
Deterministic Role-Aware Skill Gap Engine.
Computes empirical competency deficits by comparing candidate longitudinal skill states
against target role blueprints, factoring in transfer performance, failure histories, and scaffolding dependency.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone

from backend.models.skill_state import CandidateSkillStateModel
from backend.domain.role.models import (
    RoleCompetencyBlueprint,
    RoleCompetency,
    CompetencyImportance,
    RoleProvenance,
)
from backend.domain.transfer.taxonomy import TransferLevel
from backend.domain.transfer.skill_mapping import (
    normalize_skill,
    extract_core_invariants,
    CANONICAL_SKILLS,
    clean_competency_display_name,
    topological_prerequisite_sort,
    get_skill_tier,
)
from backend.domain.roadmap.models import (
    SkillGapDTO,
    SkillGapPriority,
    SkillGapAnalysisResult,
    CandidateProficiencyState,
)
from ai.skill_gap_engine.constants import (
    WEIGHT_EFFECTIVE_GAP,
    WEIGHT_ROLE_IMPORTANCE,
    WEIGHT_RECURRING_FAILURE,
    WEIGHT_EPISTEMIC_UNCERTAINTY,
    ROLE_IMPORTANCE_SCORES,
    BASE_REQUIRED_MASTERY,
    SENIORITY_MASTERY_MODIFIERS,
    TRANSFER_DEFICIT_PENALTIES,
    THRESHOLD_CRITICAL,
    THRESHOLD_HIGH,
    THRESHOLD_MEDIUM,
    MAX_SATISFIED_GAP,
    MAX_SATISFIED_ADI,
)


class SkillGapEngine:
    """
    Transparent, explainable Skill Gap Engine.
    Distinguishes recall in familiar interview contexts from generalizable, unassisted transfer.
    """

    @classmethod
    def calculate_required_mastery(
        cls,
        importance: CompetencyImportance,
        seniority: str = "Mid",
    ) -> float:
        """Calculates expected mastery threshold for a role competency given seniority."""
        base = BASE_REQUIRED_MASTERY.get(importance, 0.70)
        sen_key = seniority.lower().strip() if seniority else "mid"
        modifier = SENIORITY_MASTERY_MODIFIERS.get(sen_key, 0.0)
        return round(max(0.30, min(1.0, base + modifier)), 2)

    @classmethod
    def calculate_gap(
        cls,
        competency: RoleCompetency,
        candidate_state: Optional[CandidateSkillStateModel] = None,
        seniority: str = "Mid",
        transfer_failures: Optional[List[str]] = None,
    ) -> SkillGapDTO:
        """
        Calculates the transfer-aware skill gap and deterministic priority for an individual competency.
        """
        # 1. Determine candidate longitudinal metrics & empirical proficiency state
        has_assessed_history = False
        if candidate_state and (getattr(candidate_state, "total_attempts", 0) or 0) > 0:
            has_assessed_history = True
            cand_mastery = float(candidate_state.mastery_estimate) if candidate_state.mastery_estimate is not None else 0.50
            uncertainty = float(candidate_state.mastery_uncertainty) if candidate_state.mastery_uncertainty is not None else 0.50
            try:
                highest_transfer = TransferLevel(candidate_state.highest_transfer_level)
            except Exception:
                highest_transfer = TransferLevel.L0_RECALL
            adi = float(candidate_state.assistance_dependency_index) if candidate_state.assistance_dependency_index is not None else 0.0
            if transfer_failures is not None:
                recurring_fails = list(transfer_failures)
            else:
                recurring_fails = list(candidate_state.recurring_failure_types or [])
        elif candidate_state:
            # Candidate state exists from profile or resume claim, but not yet evaluated in an interview session
            cand_mastery = float(candidate_state.mastery_estimate) if candidate_state.mastery_estimate and float(candidate_state.mastery_estimate) > 0.0 else 0.50
            uncertainty = 1.0
            highest_transfer = TransferLevel.L0_RECALL
            adi = 0.0
            recurring_fails = list(transfer_failures) if transfer_failures is not None else []
        else:
            # No prior state or evidence recorded
            cand_mastery = 0.50  # Neutral prior for unassessed competency (never 0.0)
            uncertainty = 1.0
            highest_transfer = TransferLevel.L0_RECALL
            adi = 0.0
            recurring_fails = list(transfer_failures) if transfer_failures is not None else []

        # 2. Required Mastery & Raw Gap
        req_mastery = cls.calculate_required_mastery(competency.importance, seniority)
        raw_gap = max(0.0, round(req_mastery - cand_mastery, 3))

        # 3. Transfer Deficit Calculation
        if has_assessed_history and highest_transfer == TransferLevel.L5_INDEPENDENT_TRANSFER and cand_mastery >= req_mastery and adi <= MAX_SATISFIED_ADI:
            transfer_deficit = 0.0
        elif not has_assessed_history:
            # Unassessed baseline penalty reflecting lack of verified transfer evidence
            transfer_deficit = 0.15
        else:
            transfer_deficit = TRANSFER_DEFICIT_PENALTIES.get(highest_transfer, 0.35)
            if recurring_fails:
                transfer_deficit += min(0.15, round(len(recurring_fails) * 0.05, 3))
            if adi > 0.30:
                transfer_deficit += min(0.10, round(adi * 0.12, 3))
            transfer_deficit = round(min(0.50, transfer_deficit), 3)

        # 4. Effective Transfer-Adjusted Gap
        if has_assessed_history and highest_transfer == TransferLevel.L5_INDEPENDENT_TRANSFER and raw_gap <= MAX_SATISFIED_GAP and adi <= MAX_SATISFIED_ADI:
            effective_gap = 0.0
        else:
            effective_gap = round(min(1.0, raw_gap + transfer_deficit), 3)

        # 5. Determine 5 Distinct Evidence-Based Proficiency States
        if has_assessed_history:
            if (
                cand_mastery >= req_mastery
                and highest_transfer in (TransferLevel.L4_AMBIGUOUS_TRANSFER, TransferLevel.L5_INDEPENDENT_TRANSFER)
                and not recurring_fails
                and adi <= MAX_SATISFIED_ADI
            ):
                proficiency_state = CandidateProficiencyState.DEMONSTRATED_COMPETENCY
            elif cand_mastery < 0.45 or bool(recurring_fails) or adi > 0.35:
                proficiency_state = CandidateProficiencyState.DEMONSTRATED_WEAKNESS
            else:
                proficiency_state = CandidateProficiencyState.PARTIALLY_DEMONSTRATED
        else:
            if candidate_state:
                proficiency_state = CandidateProficiencyState.NOT_ASSESSED
            else:
                proficiency_state = CandidateProficiencyState.NO_EVIDENCE

        # 6. Priority Scoring & Classification
        role_score = ROLE_IMPORTANCE_SCORES.get(competency.importance, 0.70)
        fail_score = min(1.0, round(len(recurring_fails) * 0.35 + adi * 0.50, 3)) if has_assessed_history else 0.0

        if proficiency_state == CandidateProficiencyState.DEMONSTRATED_COMPETENCY:
            if raw_gap <= MAX_SATISFIED_GAP and highest_transfer == TransferLevel.L5_INDEPENDENT_TRANSFER and adi <= MAX_SATISFIED_ADI:
                priority = SkillGapPriority.SATISFIED
                priority_score = 0.0
            else:
                priority = SkillGapPriority.LOW
                priority_score = 0.15
        elif proficiency_state == CandidateProficiencyState.DEMONSTRATED_WEAKNESS:
            priority_score = round(
                max(0.70, (WEIGHT_EFFECTIVE_GAP * effective_gap) + (WEIGHT_ROLE_IMPORTANCE * role_score) + (WEIGHT_RECURRING_FAILURE * fail_score)),
                3
            )
            if competency.importance == CompetencyImportance.CORE:
                priority = SkillGapPriority.CRITICAL
            else:
                priority = SkillGapPriority.HIGH
        elif proficiency_state == CandidateProficiencyState.PARTIALLY_DEMONSTRATED:
            priority_score = round(
                min(0.68, max(0.35, (WEIGHT_EFFECTIVE_GAP * effective_gap) + (WEIGHT_ROLE_IMPORTANCE * role_score))),
                3
            )
            if competency.importance == CompetencyImportance.CORE:
                priority = SkillGapPriority.HIGH
            else:
                priority = SkillGapPriority.MEDIUM
        else:
            # NOT_ASSESSED or NO_EVIDENCE: Pending diagnostic evaluation, NEVER default to CRITICAL
            priority_score = round(0.55 if competency.importance == CompetencyImportance.CORE else 0.40, 3)
            if competency.importance == CompetencyImportance.CORE:
                priority = SkillGapPriority.HIGH
            else:
                priority = SkillGapPriority.MEDIUM

        # 7. Invariants and Actionable Pedagogy
        invariants = competency.core_invariants
        if not invariants:
            invariants = extract_core_invariants(competency.expected_concepts, competency.name, competency.identifier)

        # 8. Explainable Reasoning Generation
        reasoning = cls._generate_reasoning(
            comp_name=competency.name,
            importance=competency.importance,
            cand_mastery=cand_mastery,
            req_mastery=req_mastery,
            highest_transfer=highest_transfer,
            effective_gap=effective_gap,
            priority=priority,
            proficiency_state=proficiency_state,
            recurring_fails=recurring_fails,
            adi=adi,
        )

        # 9. Actionable Learning Objective
        learning_objective = cls._generate_learning_objective(
            comp_name=competency.name,
            invariants=invariants,
            priority=priority,
            highest_transfer=highest_transfer,
            recurring_fails=recurring_fails,
        )

        actionable_steps = [
            f"Master core invariants: {'; '.join(invariants[:3]) if invariants else 'Foundational constraints'}.",
            f"Engage transfer practice moving beyond {highest_transfer.value} towards L5 Independent Transfer.",
            f"Eliminate reliance on scaffolding (current ADI: {adi:.2f}) and prevent failure modes: {', '.join(recurring_fails) if recurring_fails else 'None diagnosed'}.",
        ]

        return SkillGapDTO(
            skill_id=competency.identifier,
            skill_name=competency.name,
            role_importance=competency.importance,
            candidate_mastery=cand_mastery,
            mastery_uncertainty=uncertainty,
            required_mastery=req_mastery,
            raw_gap=raw_gap,
            highest_transfer_level=highest_transfer,
            transfer_deficit=transfer_deficit,
            effective_gap=effective_gap,
            assistance_dependency=adi,
            recurring_failure_types=recurring_fails,
            priority_score=priority_score,
            priority=priority,
            priority_rank=1,
            proficiency_state=proficiency_state,
            is_measured_proficiency=has_assessed_history,
            reasoning=reasoning,
            learning_objective=learning_objective,
            core_invariants=invariants,
            actionable_steps=actionable_steps,
        )

    @classmethod
    def analyze_gaps(
        cls,
        candidate_id: str,
        candidate_states: Dict[str, CandidateSkillStateModel],
        blueprint: RoleCompetencyBlueprint,
        seniority: str = "Mid",
    ) -> SkillGapAnalysisResult:
        """
        Analyzes and prioritizes all competencies against candidate skill state.
        Incorporates role blueprint competencies and candidate-demonstrated skill deficits.
        Sequences milestones by prerequisite dependencies, urgency, and failure patterns.
        """
        gaps: List[SkillGapDTO] = []
        satisfied_count = 0
        evaluated_keys = set()
        evaluated_skill_names = set()
        evaluated_state_ids = set()

        for comp in blueprint.competencies:
            evaluated_keys.add(comp.identifier.lower().strip())
            evaluated_keys.add(comp.name.lower().strip())
            evaluated_keys.add(comp.name.lower().replace(" ", "_").strip())
            evaluated_skill_names.add(comp.identifier.lower().strip())
            evaluated_skill_names.add(comp.name.lower().replace(" ", "_").strip())
            norm_k, _ = normalize_skill(topic=comp.name, category=comp.identifier, expected_concepts=comp.expected_concepts)
            evaluated_keys.add(norm_k.lower().strip())

            # 1. Locate candidate skill state by exact identifier or normalized canonical match
            state = candidate_states.get(comp.identifier)
            if not state:
                norm_id, _ = normalize_skill(topic=comp.name, category=comp.identifier, expected_concepts=comp.expected_concepts)
                state = candidate_states.get(norm_id)
            if not state:
                state = candidate_states.get(comp.identifier.lower().strip())

            if state:
                if state.id:
                    evaluated_state_ids.add(str(state.id))
                evaluated_skill_names.add(state.skill_name.lower().strip())
                evaluated_skill_names.add(state.skill_name.lower().replace(" ", "_").strip())

            gap_dto = cls.calculate_gap(
                competency=comp,
                candidate_state=state,
                seniority=seniority,
            )
            if gap_dto.priority == SkillGapPriority.SATISFIED:
                satisfied_count += 1
            gaps.append(gap_dto)

        # 2. Deterministic Topological & Prerequisite-Aware Multi-Key Sorting
        priority_order = {
            SkillGapPriority.CRITICAL: 0,
            SkillGapPriority.HIGH: 1,
            SkillGapPriority.MEDIUM: 2,
            SkillGapPriority.LOW: 3,
            SkillGapPriority.SATISFIED: 4,
        }

        # Build priority key map for tie-breaking in topological sort
        priority_key_map: Dict[str, Any] = {
            g.skill_id: (priority_order[g.priority], -g.priority_score, -g.effective_gap)
            for g in gaps
        }

        all_skill_ids = [g.skill_id for g in gaps]
        sorted_skill_ids = topological_prerequisite_sort(all_skill_ids, priority_key_map=priority_key_map)
        
        # Reorder gaps list matching topological DAG sequence
        order_index = {sid: idx for idx, sid in enumerate(sorted_skill_ids)}
        gaps.sort(key=lambda g: order_index.get(g.skill_id, 999))

        # Assign sequential rank and compute assessment evidence statistics
        assessed_count = 0
        excluded_competencies: List[Dict[str, Any]] = []
        for idx, g in enumerate(gaps, start=1):
            g.priority_rank = idx
            if g.is_measured_proficiency:
                assessed_count += 1
            if g.priority == SkillGapPriority.SATISFIED:
                excluded_competencies.append({
                    "skill_id": g.skill_id,
                    "skill_name": g.skill_name,
                    "reason": f"Demonstrated competency at {g.highest_transfer_level.value} with verified mastery of {(g.candidate_mastery * 100):.0f}% (Target: {(g.required_mastery * 100):.0f}%).",
                    "classification": "SATISFIED_MASTERY",
                })

        total_blueprint_comps = len(blueprint.competencies)
        unassessed_count = max(0, total_blueprint_comps - assessed_count)

        return SkillGapAnalysisResult(
            candidate_id=candidate_id,
            target_role=blueprint.role_name,
            seniority=seniority,
            total_competencies_evaluated=len(gaps),
            satisfied_competencies=satisfied_count,
            gaps_detected=len(gaps) - satisfied_count,
            total_role_competencies=total_blueprint_comps,
            assessed_competencies_count=assessed_count,
            unassessed_competencies_count=unassessed_count,
            excluded_competencies=excluded_competencies,
            gaps=gaps,
            analyzed_at=datetime.now(timezone.utc),
        )

    @classmethod
    def _generate_reasoning(
        cls,
        comp_name: str,
        importance: CompetencyImportance,
        cand_mastery: float,
        req_mastery: float,
        highest_transfer: TransferLevel,
        effective_gap: float,
        priority: SkillGapPriority,
        proficiency_state: CandidateProficiencyState,
        recurring_fails: List[str],
        adi: float,
    ) -> str:
        """Constructs an explainable, research-grade justification for the gap assessment."""
        if proficiency_state == CandidateProficiencyState.DEMONSTRATED_COMPETENCY or priority == SkillGapPriority.SATISFIED:
            return (
                f"Demonstrated Competency: Candidate achieved {cand_mastery*100:.0f}% mastery with unassisted {highest_transfer.value} "
                f"transfer on '{comp_name}'. Invariant constraints are validated (ADI: {adi:.2f})."
            )

        if proficiency_state == CandidateProficiencyState.NOT_ASSESSED:
            return (
                f"Pending Diagnostic Assessment: '{comp_name}' is a {importance.value.lower()} competency required for the target role blueprint. "
                f"It has not yet been evaluated in an interview session. Prioritized for diagnostic assessment."
            )

        if proficiency_state == CandidateProficiencyState.NO_EVIDENCE:
            return (
                f"Pending Assessment (No Evidence): No prior resume claim or interview assessment recorded for '{comp_name}'. "
                f"Required by {importance.value.lower()} role specification."
            )

        if proficiency_state == CandidateProficiencyState.DEMONSTRATED_WEAKNESS:
            fail_detail = f" Recurring failure modes: {', '.join(recurring_fails)}." if recurring_fails else ""
            adi_detail = f" Elevated assistance dependency (ADI: {adi:.2f})." if adi > 0.30 else ""
            return (
                f"Demonstrated Weakness ({priority.value}): Evaluated during interview with latent mastery of {cand_mastery*100:.0f}% vs required {req_mastery*100:.0f}% "
                f"(effective deficit: {effective_gap:.2f}).{fail_detail}{adi_detail} Requires targeted architectural remediation."
            )

        # PARTIALLY_DEMONSTRATED
        fail_detail = f" Diagnosed issues: {', '.join(recurring_fails)}." if recurring_fails else ""
        transfer_detail = (
            f"Demonstrated transfer distance is {highest_transfer.value}, requiring practice to achieve unassisted L5 Independent Transfer."
            if highest_transfer != TransferLevel.L5_INDEPENDENT_TRANSFER
            else "Candidate requires mastery consolidation."
        )
        return (
            f"Partially Demonstrated ({priority.value}): Evaluated latent mastery is {cand_mastery*100:.0f}% against target {req_mastery*100:.0f}%. "
            f"{transfer_detail}{fail_detail}"
        )

    @classmethod
    def _generate_learning_objective(
        cls,
        comp_name: str,
        invariants: List[str],
        priority: SkillGapPriority,
        highest_transfer: TransferLevel,
        recurring_fails: Optional[List[str]] = None,
    ) -> str:
        """Formulates a concrete, non-generic pedagogical target grounded in invariants and diagnosed shortcomings."""
        if priority == SkillGapPriority.SATISFIED:
            return f"Maintain independent mastery of {comp_name} across evolving system contexts."

        weakness_target = ""
        if recurring_fails:
            clean_fails = [f.replace("CONCEPT_GAP:", "").replace("_", " ").title() for f in recurring_fails]
            weakness_target = f"Resolve diagnosed shortcomings in {', '.join(clean_fails[:2])} and "

        inv_str = f" emphasizing {', '.join(invariants[:2])}" if invariants else ""
        return (
            f"{weakness_target}achieve unassisted independent mastery of {comp_name}{inv_str}, "
            f"advancing from current {highest_transfer.value} to validated L5 Independent Transfer."
        )
