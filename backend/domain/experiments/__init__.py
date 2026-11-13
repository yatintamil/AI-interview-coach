"""
Domain module for the Experimental Framework & Controlled Baselines.
Contains strictly decoupled domain enums, ports, schemas, and pure business rules.
"""

from backend.domain.experiments.enums import (
    ExperimentCondition,
    ExperimentPhase,
    ExperimentOutcome,
    TaskDifficulty,
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
from backend.domain.experiments.rules import (
    DifficultyAdaptationRule,
    MetricsCalculator,
)

__all__ = [
    "ExperimentCondition",
    "ExperimentPhase",
    "ExperimentOutcome",
    "TaskDifficulty",
    "EvaluationPort",
    "TaskSetProvider",
    "ExperimentConditionStrategy",
    "ExperimentConfig",
    "ExperimentTrialRaw",
    "ExperimentDerivedMetrics",
    "ExperimentStepInput",
    "ExperimentStepResult",
    "ExperimentSessionDTO",
    "DifficultyAdaptationRule",
    "MetricsCalculator",
]
