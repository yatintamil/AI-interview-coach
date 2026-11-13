"""
Application service for experimental sessions.
Coordinates persistence, condition strategy execution, and derived metric computation.
Strictly decoupled: does NOT implement diagnosis, coaching policy, or prompt logic.
"""

import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

from backend.domain.experiments.enums import (
    ExperimentCondition,
    ExperimentPhase,
)
from backend.domain.experiments.ports import (
    EvaluationPort,
    TaskSetProvider,
    ExperimentConditionStrategy,
)
from backend.domain.experiments.schemas import (
    ExperimentConfig,
    ExperimentTrialRaw,
    ExperimentDerivedMetrics,
    ExperimentStepInput,
    ExperimentStepResult,
    ExperimentSessionDTO,
)
from backend.domain.experiments.rules import MetricsCalculator
from backend.models.experiment import ExperimentSessionModel, ExperimentTrialModel
from backend.repositories.experiment_repository import ExperimentRepository
from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.skill_state_repository import CandidateSkillStateRepository
from backend.domain.transfer.taxonomy import TransferLevel, is_higher_transfer_level
from backend.services.experiments.evaluator_adapter import EvaluatorAdapter
from backend.services.experiments.task_set_provider import ApplicationTaskSetProvider
from backend.services.experiments.conditions.factory import ConditionStrategyFactory
from ai.coaching_orchestrator.orchestrator import CoachingOrchestrator

logger = logging.getLogger(__name__)

# Concurrency synchronization per candidate
_candidate_locks: Dict[str, asyncio.Lock] = {}
_candidate_locks_guard = asyncio.Lock()


async def _get_candidate_lock(candidate_id: str) -> asyncio.Lock:
    """Retrieves or creates a process-level async lock for the given candidate ID."""
    async with _candidate_locks_guard:
        if candidate_id not in _candidate_locks:
            _candidate_locks[candidate_id] = asyncio.Lock()
        return _candidate_locks[candidate_id]



class ExperimentService:
    """
    Application Service managing the lifecycle, persistence, and telemetry of experimental sessions.
    Coordinates between ExperimentRepository and the injected ExperimentConditionStrategy.
    """

    def __init__(
        self,
        session: AsyncSession,
        evaluation_port: Optional[EvaluationPort] = None,
        task_set_provider: Optional[TaskSetProvider] = None,
        orchestrator: Optional[CoachingOrchestrator] = None,
    ):
        self.session = session
        self.repo = ExperimentRepository(session)
        self.candidate_repo = CandidateRepository(session)
        self.skill_state_repo = CandidateSkillStateRepository(session)

        self.evaluation_port = evaluation_port or EvaluatorAdapter()
        self.task_set_provider = task_set_provider or ApplicationTaskSetProvider()
        self.orchestrator = orchestrator

        # Active strategy registry for multi-turn step coordination
        self._strategy_cache: Dict[str, ExperimentConditionStrategy] = {}

    async def assign_balanced_condition(
        self,
        candidate_id: str,
        preferred_condition: Optional[ExperimentCondition] = None,
        random_seed: Optional[int] = None,
    ) -> ExperimentCondition:
        """
        Determines the experimental condition for a participant with concurrency safety:
        1. Checks persistent candidate-condition assignment (between-subjects isolation).
        2. If preferred_condition is explicitly provided, honors that preference for a new participant.
        3. Dynamic balancing across counts with deterministic seeded tie-breaking.
        4. Atomically records participant assignment to prevent concurrent race conditions.
        """
        cand_lock = await _get_candidate_lock(candidate_id)
        async with cand_lock:
            return await self._assign_balanced_condition_unlocked(
                candidate_id=candidate_id,
                preferred_condition=preferred_condition,
                random_seed=random_seed,
            )

    async def _assign_balanced_condition_unlocked(
        self,
        candidate_id: str,
        preferred_condition: Optional[ExperimentCondition] = None,
        random_seed: Optional[int] = None,
    ) -> ExperimentCondition:
        """Internal condition assignment implementation executed under candidate lock."""
        # 1. Check existing assignment via repository
        if hasattr(self.repo, "get_participant_assignment"):
            try:
                existing = await self.repo.get_participant_assignment(candidate_id)
                if existing and isinstance(existing, (str, ExperimentCondition)):
                    return ExperimentCondition(existing)
            except Exception:
                pass

        prior_sessions = await self.repo.list_by_candidate(candidate_id)
        if prior_sessions:
            first_session = min(
                prior_sessions,
                key=lambda s: getattr(s, "created_at", None) or 0
            )
            logger.info(
                "Candidate %s already has session with condition %s; preserving assignment.",
                candidate_id,
                first_session.condition,
            )
            return ExperimentCondition(first_session.condition)

        # 2. Preferred condition or dynamic balancing
        if preferred_condition is not None:
            assigned = preferred_condition
        else:
            conditions = [
                ExperimentCondition.CONDITION_A,
                ExperimentCondition.CONDITION_B,
                ExperimentCondition.CONDITION_C,
            ]
            counts = {}
            for c in conditions:
                counts[c] = await self.repo.count_by_condition(c.value)

            min_count = min(counts.values())
            tied = [c for c in conditions if counts[c] == min_count]

            if random_seed is not None and len(tied) > 1:
                import random
                rng = random.Random(random_seed)
                assigned = rng.choice(tied)
            else:
                assigned = tied[0]

        # 3. Persist assignment atomically
        if hasattr(self.repo, "record_participant_assignment"):
            try:
                saved = await self.repo.record_participant_assignment(candidate_id, assigned.value)
                if saved and isinstance(saved, (str, ExperimentCondition)):
                    return ExperimentCondition(saved)
            except Exception:
                pass

        return assigned

    async def start_experiment(
        self,
        candidate_id: str,
        config: ExperimentConfig,
        experiment_name: str = "Research_Comparative_Trial_v1",
        session_id: Optional[str] = None,
    ) -> ExperimentStepResult:
        """
        Creates a new experiment session record and initializes the condition strategy.
        Guarantees concurrency-safe condition locking and idempotency.
        """
        exp_id = session_id or str(uuid.uuid4())
        cand_lock = await _get_candidate_lock(candidate_id)
        async with cand_lock:
            # Check informed consent and withdrawal status
            if hasattr(self.repo, "get_consent"):
                try:
                    consent = await self.repo.get_consent(candidate_id)
                    if consent and consent.consent_status == "WITHDRAWN":
                        raise ValueError(
                            f"Participant '{candidate_id}' has withdrawn consent. "
                            "Experiment enrollment and participation is permanently blocked."
                        )
                    if getattr(config, "require_consent", False) and (
                        not consent or consent.consent_status != "CONSENTED"
                    ):
                        raise ValueError(
                            f"Participant '{candidate_id}' has not provided valid informed consent on file. "
                            "Experiment enrollment requires verified server-side informed consent."
                        )
                except ValueError:
                    raise
                except Exception:
                    pass

            # Ensure persistent experiment assignment for the candidate to avoid cross-condition contamination
            if config.session_type == "DELAYED_RETENTION" and config.parent_session_id:
                parent_sess = await self.repo.get(config.parent_session_id)
                if parent_sess:
                    config = config.model_copy(update={"condition": ExperimentCondition(parent_sess.condition)})
            else:
                assigned_condition = await self._assign_balanced_condition_unlocked(
                    candidate_id=candidate_id,
                    preferred_condition=config.condition,
                    random_seed=config.random_seed,
                )
                if config.condition != assigned_condition:
                    logger.info(
                        f"Candidate {candidate_id} has existing assigned condition {assigned_condition.value}. "
                        f"Locking experiment condition to {assigned_condition.value} to prevent cross-condition contamination."
                    )
                    config = config.model_copy(update={"condition": assigned_condition})

            # Check idempotency if a specific session_id was requested
            if session_id:
                existing_session = await self.repo.get(session_id)
                if existing_session:
                    cached_strat = self._strategy_cache.get(session_id)
                    if cached_strat and cached_strat.trials:
                        last_trial = cached_strat.trials[-1]
                        return ExperimentStepResult(
                            session_id=existing_session.id,
                            condition=ExperimentCondition(existing_session.condition),
                            phase=ExperimentPhase(last_trial.phase),
                            task_id=last_trial.task_id,
                            task_prompt=cached_strat.current_task.get("prompt", "") if cached_strat.current_task else "",
                            score=last_trial.score,
                            feedback=last_trial.feedback_text,
                            raw_trial=last_trial,
                        )

        # 1. Instantiate strategy via factory
        strategy = ConditionStrategyFactory.create_strategy(
            config=config,
            evaluation_port=self.evaluation_port,
            task_set_provider=self.task_set_provider,
            orchestrator=self.orchestrator,
        )

        # 2. Initialize strategy turn
        init_result = await strategy.initialize(
            session_id=exp_id,
            candidate_id=candidate_id,
            skill=config.skill,
            task_set_id=config.task_set_id,
            config_dict=config.model_dump(),
        )

        # 3. Persist session record
        provenance = getattr(config, "execution_provenance", "SYNTHETIC")
        session_model = ExperimentSessionModel(
            id=exp_id,
            candidate_id=candidate_id,
            experiment_name=experiment_name,
            condition=config.condition.value,
            skill=config.skill,
            task_set_id=config.task_set_id,
            config_json=config.model_dump(),
            current_phase=init_result.phase.value,
            status="IN_PROGRESS",
            execution_provenance=provenance,
            start_time=datetime.now(timezone.utc),
        )
        await self.repo.create(session_model)

        self._strategy_cache[exp_id] = strategy
        return init_result

    async def execute_step(
        self,
        session_id: str,
        step_input: ExperimentStepInput,
    ) -> ExperimentStepResult:
        """
        Executes a candidate turn under the active condition strategy and persists the raw trial.
        """
        strategy = self._strategy_cache.get(session_id)
        session_model = await self.repo.get(session_id)
        if not session_model:
            raise ValueError(f"Experiment session '{session_id}' not found.")

        # Check for participant withdrawal
        if hasattr(self.repo, "get_consent"):
            try:
                consent = await self.repo.get_consent(session_model.candidate_id)
                if consent and consent.consent_status == "WITHDRAWN":
                    raise ValueError(
                        f"Participant '{session_model.candidate_id}' has withdrawn from the study. "
                        "Subsequent step execution is prohibited."
                    )
            except ValueError:
                raise
            except Exception:
                pass

        # Prevent duplicate submissions or advancing already terminated sessions
        if session_model.status in ("COMPLETED", "ABANDONED"):
            raise ValueError(
                f"Cannot execute step: session '{session_id}' is already {session_model.status}."
            )

        if not strategy:
            # Rehydrate strategy from persisted configuration
            config = ExperimentConfig(**session_model.config_json)
            strategy = ConditionStrategyFactory.create_strategy(
                config=config,
                evaluation_port=self.evaluation_port,
                task_set_provider=self.task_set_provider,
                orchestrator=self.orchestrator,
            )
            # Re-initialize
            await strategy.initialize(
                session_id=session_id,
                candidate_id=session_model.candidate_id,
                skill=session_model.skill,
                task_set_id=session_model.task_set_id,
                config_dict=config.model_dump(),
            )
            self._strategy_cache[session_id] = strategy

        # 1. Execute strategy turn
        step_result: ExperimentStepResult = await strategy.execute_step(
            candidate_answer=step_input.candidate_answer,
            hints_requested=step_input.hints_requested,
            response_time_seconds=step_input.response_time_seconds,
        )

        # 2. Persist raw trial observation
        if step_result.raw_trial:
            trial_raw = step_result.raw_trial
            if not trial_raw.candidate_answer_text:
                trial_raw.candidate_answer_text = step_input.candidate_answer

            trial_prov = getattr(trial_raw, "execution_provenance", None) or getattr(session_model, "execution_provenance", "SYNTHETIC")
            eval_prov = getattr(trial_raw, "evaluator_provider", None) or "GROUNDED_NLP"
            eval_ver = getattr(trial_raw, "evaluator_version", None) or session_model.config_json.get("evaluator_version", "v1.0")
            rubric_ver = getattr(trial_raw, "rubric_version", None) or "technical_v1"

            trial_model = ExperimentTrialModel(
                id=trial_raw.trial_id,
                session_id=session_id,
                task_id=trial_raw.task_id,
                phase=trial_raw.phase.value,
                transfer_level=trial_raw.transfer_level,
                transfer_distance=getattr(trial_raw, "transfer_distance", None),
                difficulty=trial_raw.difficulty.value if trial_raw.difficulty else None,
                attempt_number=trial_raw.attempt_number,
                score=trial_raw.score,
                outcome=trial_raw.outcome.value,
                response_time_seconds=trial_raw.response_time_seconds,
                candidate_answer_text=trial_raw.candidate_answer_text,
                feedback_text=trial_raw.feedback_text,
                intervention_type=trial_raw.intervention_type,
                scaffold_level=trial_raw.scaffold_level,
                hints_requested_count=trial_raw.hints_requested_count,
                retry_count=trial_raw.retry_count,
                evaluator_provider=eval_prov,
                evaluator_version=eval_ver,
                rubric_version=rubric_ver,
                evaluator_fallback=bool(getattr(trial_raw, "evaluator_fallback", False)),
                fallback_reason=getattr(trial_raw, "fallback_reason", None),
                form_id=getattr(trial_raw, "form_id", "FORM_A") or "FORM_A",
                execution_provenance=trial_prov,
                diagnosis_type=trial_raw.diagnosis_type,
                diagnosis_confidence=trial_raw.diagnosis_confidence,
                affected_skill=trial_raw.affected_skill,
                diagnostic_evidence_json=trial_raw.diagnostic_evidence,
                timestamp=trial_raw.timestamp,
            )
            await self.repo.record_trial(trial_model)

            # 2a. Synchronize Candidate Longitudinal Skill State (REQUIRED 3)
            try:
                skill_id = session_model.skill
                existing_skill = await self.skill_state_repo.get_by_candidate_and_skill(
                    session_model.candidate_id, skill_id
                )
                trial_score_norm = float(trial_raw.score)
                trial_tl_str = trial_raw.transfer_level or ""

                # Map trial transfer level to canonical TransferLevel
                trial_tl_enum = None
                for tl in TransferLevel:
                    if tl.value == trial_tl_str or tl.name == trial_tl_str:
                        trial_tl_enum = tl
                        break
                if not trial_tl_enum:
                    if "L5" in trial_tl_str:
                        trial_tl_enum = TransferLevel.L5_INDEPENDENT_TRANSFER
                    elif "L4" in trial_tl_str:
                        trial_tl_enum = TransferLevel.L4_AMBIGUOUS_TRANSFER
                    elif "L3" in trial_tl_str:
                        trial_tl_enum = TransferLevel.L3_FAR_TRANSFER
                    elif "L2" in trial_tl_str:
                        trial_tl_enum = TransferLevel.L2_NEAR_TRANSFER
                    elif "L1" in trial_tl_str:
                        trial_tl_enum = TransferLevel.L1_DIRECT_APPLICATION
                    elif "L0" in trial_tl_str:
                        trial_tl_enum = TransferLevel.L0_RECALL

                if existing_skill:
                    # Non-destructive EMA-style prototype update
                    new_mastery = round(existing_skill.mastery_estimate * 0.6 + trial_score_norm * 0.4, 3)
                    new_uncertainty = max(0.1, round(existing_skill.mastery_uncertainty * 0.85, 3))

                    # Never downgrade transfer achievement; enforce canonical L5 thresholds
                    highest_lvl_str = existing_skill.highest_transfer_level
                    is_valid_level_achievement = False
                    if trial_tl_enum == TransferLevel.L5_INDEPENDENT_TRANSFER:
                        is_valid_level_achievement = (
                            trial_score_norm >= 0.85
                            and trial_raw.hints_requested_count == 0
                            and (not trial_raw.scaffold_level or "INDEP" in str(trial_raw.scaffold_level).upper())
                        )
                    elif trial_score_norm >= 0.70 and trial_tl_enum:
                        is_valid_level_achievement = True

                    if is_valid_level_achievement and trial_tl_enum:
                        try:
                            curr_tl_enum = TransferLevel(highest_lvl_str)
                            if is_higher_transfer_level(trial_tl_enum, curr_tl_enum):
                                highest_lvl_str = trial_tl_enum.value
                        except Exception:
                            highest_lvl_str = trial_tl_enum.value

                    # Update ADI if assistance or hints were applied
                    adi = existing_skill.assistance_dependency_index
                    if trial_raw.scaffold_level and "INDEP" not in str(trial_raw.scaffold_level).upper():
                        adi = round(min(1.0, adi + 0.05), 3)
                    elif trial_raw.hints_requested_count > 0:
                        adi = round(min(1.0, adi + 0.05), 3)

                    existing_skill.mastery_estimate = new_mastery
                    existing_skill.mastery_uncertainty = new_uncertainty
                    existing_skill.highest_transfer_level = highest_lvl_str
                    existing_skill.assistance_dependency_index = adi
                    existing_skill.total_attempts += 1
                    existing_skill.last_assessed_at = datetime.now(timezone.utc)
                else:
                    highest_lvl_str = TransferLevel.L0_RECALL.value
                    if trial_tl_enum == TransferLevel.L5_INDEPENDENT_TRANSFER:
                        if (
                            trial_score_norm >= 0.85
                            and trial_raw.hints_requested_count == 0
                            and (not trial_raw.scaffold_level or "INDEP" in str(trial_raw.scaffold_level).upper())
                        ):
                            highest_lvl_str = trial_tl_enum.value
                        elif trial_score_norm >= 0.70:
                            highest_lvl_str = TransferLevel.L4_CROSS_DOMAIN.value
                    elif trial_score_norm >= 0.70 and trial_tl_enum:
                        highest_lvl_str = trial_tl_enum.value

                    adi = 0.0
                    if trial_raw.scaffold_level and "INDEP" not in str(trial_raw.scaffold_level).upper():
                        adi = 0.2
                    elif trial_raw.hints_requested_count > 0:
                        adi = 0.1

                    await self.skill_state_repo.upsert_skill_state(
                        candidate_id=session_model.candidate_id,
                        skill_name=skill_id,
                        mastery_estimate=round(trial_score_norm, 3),
                        mastery_uncertainty=0.70,
                        highest_transfer_level=highest_lvl_str,
                        assistance_dependency_index=adi,
                        recurring_failure_types=[],
                        assessed_at=datetime.now(timezone.utc),
                    )
            except Exception as e:
                logger.warning(f"Error synchronizing candidate skill state from experiment trial: {e}")

        # 3. Update session model state
        session_model.current_phase = step_result.phase.value
        if step_result.is_complete:
            session_model.status = "COMPLETED"
            session_model.end_time = datetime.now(timezone.utc)
            cfg = session_model.config_json or {}
            sess_type = cfg.get("session_type", "PRIMARY")
            if sess_type == "PRIMARY" and hasattr(self.repo, "schedule_retention"):
                try:
                    await self.repo.schedule_retention(
                        session_id=session_id,
                        candidate_id=session_model.candidate_id,
                        delay_days=7,
                    )
                except Exception as exc:
                    logger.warning(f"Failed to schedule retention follow-up: {exc}")
            elif sess_type == "DELAYED_RETENTION" and cfg.get("parent_session_id") and hasattr(self.repo, "complete_retention"):
                try:
                    await self.repo.complete_retention(
                        session_id=cfg.get("parent_session_id"),
                        retention_session_id=session_id,
                    )
                except Exception as exc:
                    logger.warning(f"Failed to complete parent retention schedule: {exc}")

        await self.session.flush()
        return step_result

    async def abandon_session(
        self,
        session_id: str,
        reason: Optional[str] = None,
    ) -> ExperimentSessionModel:
        """
        Marks an experimental session as ABANDONED (e.g. candidate dropout, timeout, or voluntary withdrawal).
        Preserves all completed trials up to the point of abandonment.
        """
        session_model = await self.repo.get(session_id)
        if not session_model:
            raise ValueError(f"Experiment session '{session_id}' not found.")

        session_model.status = "ABANDONED"
        session_model.end_time = datetime.now(timezone.utc)
        if reason:
            cfg = dict(session_model.config_json or {})
            cfg["abandonment_reason"] = reason
            session_model.config_json = cfg

        if hasattr(self.repo, "cancel_retention"):
            try:
                await self.repo.cancel_retention(session_id)
            except Exception:
                pass

        await self.session.flush()
        return session_model

    async def withdraw_participant(
        self, candidate_id: str, reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Executes complete voluntary withdrawal for a participant:
        1. Records withdrawal in consent repository.
        2. Abandons all active (IN_PROGRESS) sessions for this candidate.
        3. Cancels any pending retention schedules.
        """
        consent = None
        if hasattr(self.repo, "withdraw_consent"):
            consent = await self.repo.withdraw_consent(candidate_id, reason=reason)

        sessions = await self.repo.list_by_candidate(candidate_id)
        abandoned_count = 0
        cancelled_retentions = 0
        now = datetime.now(timezone.utc)
        for s in sessions:
            if s.status == "IN_PROGRESS":
                s.status = "ABANDONED"
                s.end_time = now
                cfg = dict(s.config_json or {})
                cfg["abandonment_reason"] = f"PARTICIPANT_WITHDRAWAL: {reason or 'Voluntary'}"
                s.config_json = cfg
                abandoned_count += 1
            if hasattr(self.repo, "cancel_retention"):
                try:
                    await self.repo.cancel_retention(s.id)
                    cancelled_retentions += 1
                except Exception:
                    pass

        await self.session.flush()
        return {
            "candidate_id": candidate_id,
            "status": "WITHDRAWN",
            "withdrawn_at": getattr(consent, "withdrawn_at", now) or now,
            "sessions_abandoned": abandoned_count,
            "retention_schedules_cancelled": cancelled_retentions,
            "message": "Participant successfully withdrawn. Future participation blocked and active sessions abandoned.",
        }

    async def get_session(self, session_id: str) -> ExperimentSessionDTO:
        """
        Retrieves the experiment session, converts raw trial records, and computes derived metrics on-demand.
        """
        session_model = await self.repo.get_session_with_trials(session_id)
        if not session_model:
            raise ValueError(f"Experiment session '{session_id}' not found.")

        trials_raw: List[ExperimentTrialRaw] = []
        for tm in session_model.trials:
            trials_raw.append(
                ExperimentTrialRaw(
                    trial_id=tm.id,
                    session_id=tm.session_id,
                    task_id=tm.task_id,
                    phase=ExperimentPhase(tm.phase),
                    transfer_level=tm.transfer_level,
                    difficulty=tm.difficulty,
                    attempt_number=tm.attempt_number,
                    score=tm.score,
                    outcome=tm.outcome,
                    response_time_seconds=tm.response_time_seconds,
                    candidate_answer_text=tm.candidate_answer_text,
                    feedback_text=tm.feedback_text,
                    intervention_type=tm.intervention_type,
                    scaffold_level=tm.scaffold_level,
                    hints_requested_count=tm.hints_requested_count,
                    retry_count=tm.retry_count,
                    diagnosis_type=tm.diagnosis_type,
                    diagnosis_confidence=tm.diagnosis_confidence,
                    affected_skill=tm.affected_skill,
                    diagnostic_evidence=tm.diagnostic_evidence_json,
                    timestamp=tm.timestamp,
                )
            )

        condition_enum = ExperimentCondition(session_model.condition)
        derived = MetricsCalculator.calculate_metrics(
            session_id=session_id,
            condition=condition_enum,
            trials=trials_raw,
        )

        return ExperimentSessionDTO(
            session_id=session_model.id,
            candidate_id=session_model.candidate_id,
            experiment_name=session_model.experiment_name,
            condition=condition_enum,
            skill=session_model.skill,
            task_set_id=session_model.task_set_id,
            config=ExperimentConfig(**session_model.config_json),
            current_phase=ExperimentPhase(session_model.current_phase),
            status=session_model.status,
            start_time=session_model.start_time,
            end_time=session_model.end_time,
            trials=trials_raw,
            derived_metrics=derived,
        )

    async def get_telemetry(self, session_id: str) -> List[ExperimentTrialRaw]:
        """
        Returns the sequence of raw observation trials for research telemetry analysis.
        """
        dto = await self.get_session(session_id)
        return dto.trials
