"""
Factory for creating experiment condition strategies using dependency injection.
Decouples strategy creation from consumers.
"""

from typing import Optional
from backend.domain.experiments.enums import ExperimentCondition
from backend.domain.experiments.ports import (
    ExperimentConditionStrategy,
    EvaluationPort,
    TaskSetProvider,
)
from backend.domain.experiments.schemas import ExperimentConfig
from backend.services.experiments.conditions.generic_feedback import GenericFeedbackCondition
from backend.services.experiments.conditions.adaptive_difficulty import AdaptiveDifficultyCondition
from backend.services.experiments.conditions.transfer_aware_adapter import TransferAwareConditionAdapter
from ai.coaching_orchestrator.orchestrator import CoachingOrchestrator


class ConditionStrategyFactory:
    """
    Factory creating concrete ExperimentConditionStrategy instances with injected dependencies.
    """

    @staticmethod
    def create_strategy(
        config: ExperimentConfig,
        evaluation_port: EvaluationPort,
        task_set_provider: TaskSetProvider,
        orchestrator: Optional[CoachingOrchestrator] = None,
    ) -> ExperimentConditionStrategy:
        """
        Instantiates and returns the condition strategy based on the experimental condition.
        """
        if config.condition == ExperimentCondition.CONDITION_A:
            return GenericFeedbackCondition(
                evaluation_port=evaluation_port,
                task_set_provider=task_set_provider,
            )
        elif config.condition == ExperimentCondition.CONDITION_B:
            return AdaptiveDifficultyCondition(
                evaluation_port=evaluation_port,
                task_set_provider=task_set_provider,
                difficulty_threshold_high=config.difficulty_threshold_high,
                difficulty_threshold_low=config.difficulty_threshold_low,
            )
        elif config.condition == ExperimentCondition.CONDITION_C:
            return TransferAwareConditionAdapter(
                evaluation_port=evaluation_port,
                task_set_provider=task_set_provider,
                orchestrator=orchestrator,
            )
        else:
            raise ValueError(f"Unsupported experiment condition: {config.condition}")
