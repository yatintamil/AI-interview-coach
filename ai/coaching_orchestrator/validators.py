"""
Validators for Coaching Orchestration.
Verifies session configuration, task linkage, invariant preservation, and independent transfer purity.
"""

from typing import List, Optional
from backend.domain.transfer.coaching_types import ScaffoldLevel
from backend.domain.transfer.schemas import TransferTaskDefinitionDTO
from ai.coaching_orchestrator.schemas import CoachingSessionConfig, TrainingContext


class CoachingOrchestrationValidator:
    """
    Validates domain integrity and experimental invariants during loop orchestration.
    """

    @staticmethod
    def validate_session_config(config: CoachingSessionConfig) -> List[str]:
        """Validates that session configuration parameters are within sound experimental bounds."""
        errors = []
        if config.max_retries < 1 or config.max_retries > 5:
            errors.append(f"max_retries must be in [1, 5], got {config.max_retries}")
        if config.pass_threshold < 1.0 or config.pass_threshold > 10.0:
            errors.append(f"pass_threshold must be in [1.0, 10.0], got {config.pass_threshold}")
        return errors

    @staticmethod
    def validate_training_context(context: TrainingContext) -> List[str]:
        """Validates that anchor training task has necessary invariants for transfer derivation."""
        errors = []
        if not context.core_invariants:
            errors.append("Training context must specify at least one core invariant.")
        if not context.base_expected_concepts:
            errors.append("Training context must specify at least one expected concept.")
        if not context.skill_id.strip():
            errors.append("Training context must specify a non-empty skill_id.")
        return errors

    @staticmethod
    def validate_transfer_linkage(
        training_context: TrainingContext, transfer_task: TransferTaskDefinitionDTO
    ) -> List[str]:
        """Validates that a generated transfer task correctly links back to the training task and skill."""
        errors = []
        if transfer_task.skill_id != training_context.skill_id:
            errors.append(
                f"Transfer task skill '{transfer_task.skill_id}' does not match "
                f"training skill '{training_context.skill_id}'"
            )
        # Check that core invariants are preserved
        missing_invariants = [
            inv for inv in training_context.core_invariants
            if inv not in transfer_task.core_invariants
        ]
        if missing_invariants:
            errors.append(f"Transfer task omitted core invariants: {missing_invariants}")
        return errors

    @staticmethod
    def validate_independent_conditions(
        scaffold_level: ScaffoldLevel,
        hints_requested: int,
        transfer_distance: Optional[float] = None,
        min_distance: float = 0.70,
    ) -> List[str]:
        """
        Validates that independent transfer conditions are strictly unassisted:
        scaffold must be INDEPENDENT, hints_requested must be 0, and transfer distance D >= 0.70.
        """
        errors = []
        if scaffold_level != ScaffoldLevel.INDEPENDENT:
            errors.append(
                f"Independent transfer must have scaffold level INDEPENDENT, got '{scaffold_level.value}'"
            )
        if hints_requested > 0:
            errors.append(
                f"Independent transfer cannot permit hints (requested {hints_requested})"
            )
        if transfer_distance is not None and round(float(transfer_distance), 4) < round(float(min_distance), 4):
            errors.append(
                f"Independent transfer requires situational transfer distance D >= {min_distance:.2f}, got {transfer_distance:.2f}"
            )
        return errors
