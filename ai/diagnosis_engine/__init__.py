"""
Transfer Failure Diagnosis Engine.

Provides evidence-grounded, multi-signal diagnosis of WHY a candidate failed
to transfer an interview competency to an unseen transfer challenge.
"""

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
from ai.diagnosis_engine.diagnosis_engine import (
    TransferDiagnosisEngine,
    DEFAULT_FAILURE_INTERVENTIONS,
)

__all__ = [
    "DiagnosisRequest",
    "DeterministicSignals",
    "DiagnosisValidationResult",
    "ISignalExtractor",
    "IDiagnosisValidator",
    "ITransferDiagnosisEngine",
    "SignalExtractor",
    "DiagnosisValidator",
    "TransferDiagnosisEngine",
    "DEFAULT_FAILURE_INTERVENTIONS",
]
