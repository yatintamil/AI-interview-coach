"""
Domain package for Transfer-Aware AI Coaching.
Exports core enums, taxonomy definitions, and Pydantic DTOs.
"""

from backend.domain.transfer.taxonomy import (
    TransferLevel,
    TRANSFER_LEVEL_RANKS,
    is_higher_transfer_level,
)
from backend.domain.transfer.diagnosis_types import TransferFailureType
from backend.domain.transfer.coaching_types import (
    CoachingInterventionType,
    ScaffoldLevel,
    DEFAULT_INTERVENTION_SCAFFOLD,
)
from backend.domain.transfer.schemas import (
    SessionPhase,
    EvidenceItemDTO,
    TransferTaskDefinitionDTO,
    TransferFailureDiagnosisDTO,
    CoachingInterventionDecisionDTO,
    CandidateSkillStateDTO,
)

__all__ = [
    "TransferLevel",
    "TRANSFER_LEVEL_RANKS",
    "is_higher_transfer_level",
    "TransferFailureType",
    "CoachingInterventionType",
    "ScaffoldLevel",
    "DEFAULT_INTERVENTION_SCAFFOLD",
    "SessionPhase",
    "EvidenceItemDTO",
    "TransferTaskDefinitionDTO",
    "TransferFailureDiagnosisDTO",
    "CoachingInterventionDecisionDTO",
    "CandidateSkillStateDTO",
]
