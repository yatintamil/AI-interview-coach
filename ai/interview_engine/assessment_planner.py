"""
Assessment Planning and Dynamic Progression Engine.

Translates a RoleCompetencyBlueprint into a 5-stage assessment plan,
creates traceable QuestionPlans, tracks competency evidence,
evaluates evidence sufficiency heuristics, and drives adaptive follow-up probing.
"""

import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple

from backend.domain.role.models import (
    RoleCompetencyBlueprint,
    RoleCompetency,
    CompetencyImportance,
    AssessmentPlan,
    AssessmentPlanConfig,
    QuestionPlan,
    QuestionDepthLevel,
    CompetencyEvidenceRecord,
    CompetencyCoverageStatus,
    InterviewCompletionReason,
    RoleCompetencyProfile,
)

logger = logging.getLogger(__name__)

STAGE_NAMES = {
    1: "Foundational Orientation & Resume Grounding",
    2: "Core Engineering & Algorithmic Mechanics",
    3: "Scalable Systems & Architectural Trade-offs",
    4: "Incident Invariants, Failure Modes & Debugging",
    5: "Cross-Functional Ownership & STAR Leadership",
}


class AssessmentPlanner:
    """
    Manages the lifecycle of an interview assessment plan.
    Enforces evidence-driven progression across the 5 stages without a rigid 1-turn-per-stage limitation.
    """

    @classmethod
    def create_assessment_plan(
        cls,
        blueprint: RoleCompetencyBlueprint,
        config: Optional[AssessmentPlanConfig] = None,
    ) -> AssessmentPlan:
        """
        Compiles an initial AssessmentPlan from a RoleCompetencyBlueprint.
        Distributes competencies across the 5 lifecycle stages.
        """
        cfg = config or AssessmentPlanConfig()
        plan_id = str(uuid.uuid4())

        stages: Dict[int, List[str]] = {1: [], 2: [], 3: [], 4: [], 5: []}
        evidence_map: Dict[str, CompetencyEvidenceRecord] = {}

        # Use stage suitability from blueprint, falling back to sequential distribution if needed
        for stage_idx in range(1, 6):
            comp_ids = blueprint.stage_suitability.get(stage_idx, [])
            for c_id in comp_ids:
                stages[stage_idx].append(c_id)

        # Ensure every competency is present in at least one stage
        assigned_ids = set()
        for s_list in stages.values():
            assigned_ids.update(s_list)

        for comp in blueprint.competencies:
            c_id = comp.identifier
            if c_id not in assigned_ids:
                # Assign to stage based on index modulo 5 + 1
                target_stage = min(5, max(1, (len(assigned_ids) % 5) + 1))
                stages[target_stage].append(c_id)
                assigned_ids.add(c_id)

            evidence_map[c_id] = CompetencyEvidenceRecord(
                competency_id=c_id,
                competency_name=comp.name,
                stage_index=1,
                questions_asked=0,
                scores=[],
                evidence_items=[],
                demonstrated_concepts=[],
                missing_concepts=[],
                misconceptions=[],
                question_history=[],
                evaluation_history=[],
                strengths=[],
                weaknesses=[],
                evidence_confidence=0.0,
                assessment_coverage=0.0,
                last_assessment_timestamp=None,
                coverage_status=CompetencyCoverageStatus.UNASSESSED,
            )

        # Set first active stage and competency
        first_stage = 1
        first_comp = stages[first_stage][0] if stages[first_stage] else (blueprint.competencies[0].identifier if blueprint.competencies else "")

        if first_comp and first_comp in evidence_map:
            evidence_map[first_comp].stage_index = first_stage

        return AssessmentPlan(
            plan_id=plan_id,
            role_name=blueprint.role_name,
            stages=stages,
            current_stage_index=first_stage,
            current_competency_id=first_comp,
            completed_competency_ids=[],
            total_questions_asked=0,
            competency_evidence=evidence_map,
            config=cfg,
            evidence_coverage_ratio=0.0,
            is_completed=False,
        )

    @classmethod
    def create_question_plan(
        cls,
        plan: AssessmentPlan,
        blueprint: RoleCompetencyBlueprint,
        candidate_context: Optional[Dict[str, Any]] = None,
        difficulty_level: str = "medium",
        interviewer_action: Optional[str] = None,
        answer_classification: Optional[str] = None,
        action_directive: Optional[str] = None,
        transition_rationale: Optional[str] = None,
        preceding_competency: Optional[str] = None,
    ) -> QuestionPlan:
        """
        Creates a structured, traceable QuestionPlan for the next question.
        Determines question depth level (FOUNDATION, PRACTICAL, FOLLOW_UP, ADVANCED)
        using a deterministic diagnostic policy and answer-driven interviewer action.
        """
        active_comp_id = plan.current_competency_id or (plan.stages.get(plan.current_stage_index, [""])[0] if plan.stages.get(plan.current_stage_index) else "")
        comp = blueprint.get_competency(active_comp_id)

        if not comp:
            # Safe fallback if ID not found or stale
            comp = blueprint.competencies[0] if blueprint.competencies else RoleCompetency(
                identifier="core_engineering_mechanics",
                name="Core Engineering Mechanics",
                description="General engineering competence",
            )
            active_comp_id = comp.identifier
            plan.current_competency_id = active_comp_id

        ev_record = plan.competency_evidence.get(active_comp_id)
        stage_idx = plan.current_stage_index
        stage_name = STAGE_NAMES.get(stage_idx, f"Stage {stage_idx}")

        is_followup = False
        followup_concept = None
        last_score = None

        # 1. Deterministic Depth Policy:
        # Default: FOUNDATION / PRACTICAL.
        # Only advance to ADVANCED if candidate demonstrates sufficient understanding.
        # If candidate exhibits weakness, do NOT drill deeper or punish; use gentle FOLLOW_UP then move on.
        if not ev_record or ev_record.questions_asked == 0:
            # First question for competency: establish baseline
            depth_level = QuestionDepthLevel.FOUNDATION.value if stage_idx <= 2 else QuestionDepthLevel.PRACTICAL.value
            effective_diff = "easy" if depth_level == QuestionDepthLevel.FOUNDATION.value else difficulty_level
        elif ev_record.questions_asked == 1:
            is_followup = True
            if ev_record.scores:
                last_score = ev_record.scores[-1]
            if ev_record.missing_concepts:
                followup_concept = ev_record.missing_concepts[0]
            elif comp.expected_concepts:
                followup_concept = comp.expected_concepts[-1]

            if last_score is not None and last_score >= 7.5:
                # Candidate demonstrated good baseline understanding -> practical application
                depth_level = QuestionDepthLevel.PRACTICAL.value
                effective_diff = "medium"
            elif last_score is not None and last_score >= 4.5:
                # Partial understanding -> practical clarification follow-up
                depth_level = QuestionDepthLevel.FOLLOW_UP.value
                effective_diff = "medium"
            else:
                # Weakness detected -> gentle clarification, do NOT drill with high difficulty
                depth_level = QuestionDepthLevel.FOLLOW_UP.value
                effective_diff = "easy"
        else:
            # 2 or more questions asked on this competency
            is_followup = True
            if ev_record.scores:
                last_score = ev_record.scores[-1]
            if ev_record.missing_concepts:
                followup_concept = ev_record.missing_concepts[0]
            elif comp.expected_concepts:
                followup_concept = comp.expected_concepts[-1]

            if last_score is not None and last_score >= 8.0:
                # Only move to ADVANCED when candidate demonstrated clear understanding
                depth_level = QuestionDepthLevel.ADVANCED.value
                effective_diff = "hard"
            else:
                depth_level = QuestionDepthLevel.FOLLOW_UP.value
                effective_diff = "medium"

        # Objective definition
        if is_followup and followup_concept:
            objective = (
                f"Targeted diagnostic follow-up on '{comp.name}'. Probing concept: "
                f"'{followup_concept}' at {depth_level} level without unnecessary difficulty escalation."
            )
        else:
            base_obj = comp.assessment_objectives[0] if comp.assessment_objectives else f"Assess candidate competence in {comp.name}."
            objective = f"Stage {stage_idx} [{depth_level}] probe: {base_obj}"

        # Determine default interviewer_action & transition rationale if transitioning
        if preceding_competency and preceding_competency.strip().lower() != comp.name.strip().lower():
            if not interviewer_action:
                interviewer_action = "TRANSITION_COMPETENCY"
            if not transition_rationale:
                transition_rationale = f"Assessing {comp.name} following evaluation of '{preceding_competency}'."

        return QuestionPlan(
            role=blueprint.role_name,
            competency_id=comp.identifier,
            competency_name=comp.name,
            stage_index=stage_idx,
            stage_name=stage_name,
            objective=objective,
            difficulty=effective_diff,
            depth_level=depth_level,
            expected_concepts=comp.expected_concepts,
            core_invariants=comp.core_invariants,
            evidence_requirements=comp.evidence_requirements,
            candidate_context=candidate_context or {},
            is_followup=is_followup,
            followup_target_concept=followup_concept,
            previous_turn_score=last_score,
            interviewer_action=interviewer_action,
            answer_classification=answer_classification,
            action_directive=action_directive,
            transition_rationale=transition_rationale,
            preceding_competency=preceding_competency,
        )


    @classmethod
    def evaluate_evidence_sufficiency(
        cls,
        ev_record: CompetencyEvidenceRecord,
        expected_concepts: List[str],
        latest_score: float,
        latest_missing_concepts: List[str],
        latest_evidence: List[str],
        max_followups: int = 2,
        is_contradictory: bool = False,
    ) -> Tuple[bool, CompetencyCoverageStatus, str]:
        """
        Determines whether evidence gathered for an individual competency is sufficient to conclude
        assessment on this competency and advance.
        
        Sufficiency Criteria:
        - Contradictory statements require a reconciliation probe (unless max depth reached) -> CONFLICTING_EVIDENCE.
        - High performance (latest_score >= 7.0 and demonstrated concepts >= 40%): SUFFICIENT_EVIDENCE.
        - Consistent solid performance (avg_score >= 6.5 and demonstrated concepts >= 50%): SUFFICIENT_EVIDENCE.
        - Max diagnostic depth reached (1 initial question + max_followups): PARTIALLY_ASSESSED or SUFFICIENT_EVIDENCE.
        - Initial poor answer (< 4.5) or significant omissions (> 50% concepts missing): PARTIALLY_ASSESSED (needs probe).
        """
        all_scores = ev_record.scores + [latest_score]
        avg_score = sum(all_scores) / max(1, len(all_scores))

        total_expected = len(expected_concepts)
        demonstrated_concepts_set = set(ev_record.demonstrated_concepts)
        for exp in expected_concepts:
            if exp not in latest_missing_concepts:
                demonstrated_concepts_set.add(exp)

        demonstrated_count = len(demonstrated_concepts_set)
        demonstrated_ratio = 1.0 if total_expected == 0 else min(1.0, demonstrated_count / max(1, total_expected))

        # 1. Contradiction detection requires reconciliation follow-up
        if is_contradictory and ev_record.questions_asked < (1 + max_followups):
            return False, CompetencyCoverageStatus.CONFLICTING_EVIDENCE, "Contradictory technical assertions require reconciliation probe."

        # 2. Strong demonstrated competence
        if (latest_score >= 7.0 and demonstrated_ratio >= 0.40) or (avg_score >= 6.5 and demonstrated_ratio >= 0.50):
            return True, CompetencyCoverageStatus.SUFFICIENT_EVIDENCE, f"Demonstrated sufficient evidence ({demonstrated_ratio * 100:.0f}% concept coverage, score={latest_score:.1f}/10)."

        # 3. Maximum diagnostic depth reached for this competency (1 initial + max_followups)
        if ev_record.questions_asked >= max_followups:
            status = CompetencyCoverageStatus.SUFFICIENT_EVIDENCE if avg_score >= 6.0 else CompetencyCoverageStatus.PARTIALLY_ASSESSED
            return True, status, f"Diagnostic depth reached ({ev_record.questions_asked + 1} questions). Competency baseline established."

        # 4. Partial or incomplete understanding -> require diagnostic follow-up probe
        return False, CompetencyCoverageStatus.PARTIALLY_ASSESSED, (
            f"Insufficient evidence: score={latest_score:.1f}/10, demonstrated={demonstrated_count}/{total_expected} concepts."
        )

    @classmethod
    def record_turn_and_progress(
        cls,
        plan: AssessmentPlan,
        blueprint: RoleCompetencyBlueprint,
        eval_data: Dict[str, Any],
        question_text: str = "",
        is_contradictory: bool = False,
        candidate_requested_stop: bool = False,
    ) -> Tuple[bool, bool, str]:
        """
        Updates competency evidence, calculates dynamic evidence coverage across the role,
        and determines progression or evidence-driven completion.
        
        Returns:
            (is_followup_needed: bool, is_interview_completed: bool, status_reason: str)
        """
        # 1. Early Candidate Requested Termination
        if candidate_requested_stop:
            plan.is_completed = True
            plan.completion_reason = InterviewCompletionReason.CANDIDATE_REQUESTED.value
            return False, True, "Candidate explicitly requested interview completion."

        active_comp_id = plan.current_competency_id
        if not active_comp_id or active_comp_id not in plan.competency_evidence:
            active_comp_id = list(plan.competency_evidence.keys())[0]
            plan.current_competency_id = active_comp_id

        ev_record = plan.competency_evidence[active_comp_id]
        comp = blueprint.get_competency(active_comp_id)
        expected_concepts = comp.expected_concepts if comp else []

        turn_score = float(eval_data.get("overall_score", 5.0))
        missing_concepts = eval_data.get("missing_concepts", [])
        evidence_items = [
            f"{e.get('claim', '')}: {e.get('basis', '')}" if isinstance(e, dict) else str(e)
            for e in eval_data.get("evidence", [])
        ]
        strengths = eval_data.get("strengths", [])
        weaknesses = eval_data.get("weaknesses", [])

        # Extract demonstrated concepts: expected concepts demonstrated in answer
        matched_in_eval = eval_data.get("matched_concepts") or []
        for m in matched_in_eval:
            if m not in ev_record.demonstrated_concepts:
                ev_record.demonstrated_concepts.append(m)

        demonstrated_this_turn = [
            c for c in expected_concepts
            if c not in missing_concepts
        ]
        for dc in demonstrated_this_turn:
            if dc not in ev_record.demonstrated_concepts:
                ev_record.demonstrated_concepts.append(dc)

        cfg = plan.config
        # Evaluate sufficiency heuristic for this competency
        is_sufficient, new_status, reason = cls.evaluate_evidence_sufficiency(
            ev_record=ev_record,
            expected_concepts=expected_concepts,
            latest_score=turn_score,
            latest_missing_concepts=missing_concepts,
            latest_evidence=evidence_items,
            max_followups=cfg.max_followups_per_competency,
            is_contradictory=is_contradictory,
        )

        # Update Evidence Record
        ev_record.questions_asked += 1
        ev_record.scores.append(turn_score)
        ev_record.evidence_items.extend(evidence_items)
        ev_record.missing_concepts = missing_concepts
        if question_text:
            ev_record.question_history.append(question_text)

        ev_record.evaluation_history.append({
            "turn": plan.total_questions_asked + 1,
            "score": turn_score,
            "correctness": eval_data.get("correctness", 0.0),
            "technical_depth": eval_data.get("technical_depth", 0.0),
            "evidence_count": len(eval_data.get("evidence", [])),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        for s in strengths:
            if s not in ev_record.strengths:
                ev_record.strengths.append(s)
        for w in weaknesses:
            if w not in ev_record.weaknesses:
                ev_record.weaknesses.append(w)

        ev_record.coverage_status = new_status
        total_exp = len(expected_concepts)
        ev_record.assessment_coverage = min(1.0, round(len(ev_record.demonstrated_concepts) / max(1, total_exp), 2))
        ev_record.evidence_confidence = min(
            1.0,
            round(0.25 * ev_record.questions_asked + 0.45 * ev_record.assessment_coverage + (0.30 if turn_score >= 6.5 else 0.10), 2)
        )
        ev_record.last_assessment_timestamp = datetime.now(timezone.utc).isoformat()

        plan.total_questions_asked += 1

        # 2. Calculate Role-Wide Evidence Coverage
        core_comps = [c for c in blueprint.competencies if c.importance == CompetencyImportance.CORE] or blueprint.competencies
        core_ids = {c.identifier for c in core_comps}

        total_weight = 0.0
        weighted_coverage = 0.0
        all_core_sufficient = True

        for c in blueprint.competencies:
            w = 2.0 if c.importance == CompetencyImportance.CORE else 1.0
            total_weight += w
            rec = plan.competency_evidence.get(c.identifier)
            if rec:
                weighted_coverage += rec.assessment_coverage * w
                if c.identifier in core_ids:
                    # Core competency is sufficient if status is SUFFICIENT_EVIDENCE, OR if probed through diagnostic depth (>= 2 questions)
                    if rec.coverage_status != CompetencyCoverageStatus.SUFFICIENT_EVIDENCE and rec.questions_asked < 2:
                        all_core_sufficient = False
            else:
                if c.identifier in core_ids:
                    all_core_sufficient = False

        plan.evidence_coverage_ratio = min(1.0, round(weighted_coverage / max(1.0, total_weight), 2))

        # 3. Check Operational Safeguards (Emergency Backstops)
        # A. Loop detection on a single competency without progression
        max_repeats = getattr(cfg, "max_repeated_concept_probes", 3) or 3
        if ev_record.questions_asked >= (max_repeats + 1) and not is_sufficient:
            plan.is_completed = False
            plan.is_halted_by_safeguard = True
            plan.completion_reason = InterviewCompletionReason.LOOP_DETECTED.value
            return False, True, f"Operational safeguard: Loop detected on '{active_comp_id}' after {ev_record.questions_asked} turns without evidence progression. Assessment preserved as INCOMPLETE."

        # B. Hard Operational Safety Ceiling
        safety_ceiling = getattr(cfg, "safety_max_questions", 20) or 20
        if plan.total_questions_asked >= safety_ceiling:
            # Emergency ceiling reached: do NOT mark current unverified competency as completed.
            # Preserve incomplete status and outstanding gaps.
            plan.is_completed = False
            plan.is_halted_by_safeguard = True
            plan.completion_reason = InterviewCompletionReason.OPERATIONAL_SAFETY_CEILING.value
            return False, True, f"Operational safeguard: Emergency safety question ceiling reached ({safety_ceiling} turns). Assessment preserved as INCOMPLETE."

        # 4. Check Evidence-Driven Completion: All Core Competencies Evaluated with Sufficient Evidence
        if all_core_sufficient and is_sufficient and plan.evidence_coverage_ratio >= getattr(cfg, "min_core_coverage_ratio", 0.75):
            if active_comp_id not in plan.completed_competency_ids:
                plan.completed_competency_ids.append(active_comp_id)
            plan.is_completed = True
            plan.completion_reason = InterviewCompletionReason.COMPETENCY_COVERAGE_SATISFIED.value
            return False, True, f"Role competency evidence coverage satisfied ({plan.evidence_coverage_ratio * 100:.0f}% coverage across core competencies)."

        # 5. Adaptive Follow-Up on Same Competency if Evidence is Insufficient
        if not is_sufficient:
            return True, False, f"Targeted follow-up triggered for {comp.name if comp else active_comp_id}: {reason}"

        # 6. Mark Current Competency Complete & Transition to Next Most Informative Competency
        if active_comp_id not in plan.completed_competency_ids:
            plan.completed_competency_ids.append(active_comp_id)

        # Select next competency: Prioritize CORE unassessed competencies, then lowest coverage
        uncompleted_comps = [c for c in blueprint.competencies if c.identifier not in plan.completed_competency_ids]

        if uncompleted_comps:
            def sort_key(c: RoleCompetency):
                is_core = 0 if c.importance == CompetencyImportance.CORE else 1
                rec = plan.competency_evidence.get(c.identifier)
                cov = rec.assessment_coverage if rec else 0.0
                return (is_core, cov)

            uncompleted_comps.sort(key=sort_key)
            next_comp = uncompleted_comps[0]
            plan.current_competency_id = next_comp.identifier
            # Derive stage dynamically from index or stage suitability
            plan.current_stage_index = min(5, max(1, len(plan.completed_competency_ids) + 1))
            if next_comp.identifier in plan.competency_evidence:
                plan.competency_evidence[next_comp.identifier].stage_index = plan.current_stage_index

            return False, False, f"Advancing to assess {next_comp.name} (Coverage: {plan.evidence_coverage_ratio * 100:.0f}%)."

        # 7. Low Information Value Completion: All competencies have been assessed
        plan.is_completed = True
        plan.completion_reason = InterviewCompletionReason.LOW_INFORMATION_VALUE.value
        return False, True, "All role competencies evaluated; low expected information value from additional turns."

    @classmethod
    def compile_role_competency_profile(
        cls,
        plan: AssessmentPlan,
    ) -> RoleCompetencyProfile:
        """
        Compiles the final RoleCompetencyProfile aggregating evidence across all competencies.
        Produces non-inflated, evidence-grounded performance metrics.
        """
        total = len(plan.competency_evidence)
        sufficient = 0
        partially = 0
        unassessed = 0

        summary_strengths: List[str] = []
        summary_weaknesses: List[str] = []

        for record in plan.competency_evidence.values():
            if record.coverage_status == CompetencyCoverageStatus.SUFFICIENT_EVIDENCE:
                sufficient += 1
            elif record.coverage_status in (CompetencyCoverageStatus.PARTIALLY_ASSESSED, CompetencyCoverageStatus.INITIAL_EVIDENCE, CompetencyCoverageStatus.CONFLICTING_EVIDENCE):
                partially += 1
            else:
                unassessed += 1

            for s in record.strengths:
                if s not in summary_strengths:
                    summary_strengths.append(s)
            for w in record.weaknesses:
                if w not in summary_weaknesses:
                    summary_weaknesses.append(w)

        coverage_ratio = plan.evidence_coverage_ratio if plan.evidence_coverage_ratio > 0.0 else round((sufficient + (partially * 0.5)) / max(1, total), 2)

        return RoleCompetencyProfile(
            role_name=plan.role_name,
            competency_records=plan.competency_evidence,
            overall_coverage_ratio=coverage_ratio,
            sufficient_evidence_count=sufficient,
            partially_assessed_count=partially,
            unassessed_count=unassessed,
            summary_strengths=summary_strengths,
            summary_weaknesses=summary_weaknesses,
        )
