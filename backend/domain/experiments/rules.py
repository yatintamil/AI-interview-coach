"""
Pure domain business rules for the experimental framework.
Implements difficulty adaptation and on-demand metric calculation without infrastructure dependencies.
"""

from typing import List, Optional
from backend.domain.experiments.enums import (
    ExperimentCondition,
    ExperimentPhase,
    ExperimentOutcome,
    TaskDifficulty,
)
from backend.domain.experiments.schemas import (
    ExperimentTrialRaw,
    ExperimentDerivedMetrics,
)


class DifficultyAdaptationRule:
    """
    Pure domain rule for Baseline B difficulty adaptation.
    Strictly performance-based: utilizes only score and current difficulty level.
    Never inspects diagnosis, failure modes, or scaffolding.
    """

    @staticmethod
    def calculate_next_difficulty(
        current_difficulty: TaskDifficulty,
        score: float,
        threshold_high: float = 0.75,
        threshold_low: float = 0.50,
    ) -> TaskDifficulty:
        """
        Step-up if score >= threshold_high.
        Step-down if score < threshold_low.
        Otherwise maintain current difficulty.
        """
        if score >= threshold_high:
            if current_difficulty == TaskDifficulty.EASY:
                return TaskDifficulty.MEDIUM
            elif current_difficulty == TaskDifficulty.MEDIUM:
                return TaskDifficulty.HARD
            return TaskDifficulty.HARD

        elif score < threshold_low:
            if current_difficulty == TaskDifficulty.HARD:
                return TaskDifficulty.MEDIUM
            elif current_difficulty == TaskDifficulty.MEDIUM:
                return TaskDifficulty.EASY
            return TaskDifficulty.EASY

        return current_difficulty


class MetricsCalculator:
    """
    Pure domain calculator deriving experimental summary metrics from raw observations.
    Ensures research derivations remain completely reproducible from persisted raw data.
    """

    @staticmethod
    def calculate_metrics(
        session_id: str,
        condition: ExperimentCondition,
        trials: List[ExperimentTrialRaw],
    ) -> ExperimentDerivedMetrics:
        """
        Derives summary research metrics from raw trials.
        """
        pretest_trials = [t for t in trials if t.phase == ExperimentPhase.PRETEST]
        training_trials = [t for t in trials if t.phase == ExperimentPhase.TRAINING]
        posttest_trials = [t for t in trials if t.phase == ExperimentPhase.POSTTEST]
        transfer_trials = [t for t in trials if t.phase == ExperimentPhase.TRANSFER_TEST]
        independent_trials = [t for t in trials if t.phase == ExperimentPhase.INDEPENDENT_TRANSFER]

        pretest_score = pretest_trials[-1].score if pretest_trials else None
        posttest_score = posttest_trials[-1].score if posttest_trials else None
        transfer_score = transfer_trials[-1].score if transfer_trials else None
        independent_score = independent_trials[-1].score if independent_trials else None

        training_mean = (
            sum(t.score for t in training_trials) / len(training_trials)
            if training_trials else None
        )

        # Normalized gain = (posttest - pretest) / (1.0 - pretest)
        normalized_gain = None
        if pretest_score is not None and posttest_score is not None:
            if pretest_score < 1.0:
                normalized_gain = round((posttest_score - pretest_score) / (1.0 - pretest_score), 4)
            else:
                normalized_gain = 0.0

        # Transfer delta = transfer_score - posttest_score
        transfer_delta = None
        if transfer_score is not None and posttest_score is not None:
            transfer_delta = round(transfer_score - posttest_score, 4)

        total_hints = sum(t.hints_requested_count for t in trials)
        total_retries = max((t.retry_count for t in trials), default=0)
        total_interventions = sum(1 for t in trials if t.intervention_type is not None)

        retry_recovery_success = any(
            t.phase == ExperimentPhase.TARGETED_RETRAINING and t.outcome == ExperimentOutcome.PASS
            for t in trials
        )
        independent_transfer_success = any(
            t.phase == ExperimentPhase.INDEPENDENT_TRANSFER and t.outcome == ExperimentOutcome.PASS
            for t in trials
        )

        return ExperimentDerivedMetrics(
            session_id=session_id,
            condition=condition,
            pretest_score=pretest_score,
            training_mean_score=round(training_mean, 4) if training_mean is not None else None,
            posttest_score=posttest_score,
            transfer_test_score=transfer_score,
            independent_transfer_score=independent_score,
            normalized_gain=normalized_gain,
            transfer_delta=transfer_delta,
            total_hints_consumed=total_hints,
            total_retries=total_retries,
            total_interventions=total_interventions,
            retry_recovery_success=retry_recovery_success,
            independent_transfer_success=independent_transfer_success,
        )
