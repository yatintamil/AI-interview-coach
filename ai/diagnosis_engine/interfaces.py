"""
Interfaces and Protocols for Transfer Failure Diagnosis components.
Enforces modular decoupling between signal extraction, structured reasoning, and validation.
"""

from typing import Protocol, runtime_checkable
from backend.domain.transfer.schemas import TransferFailureDiagnosisDTO
from ai.diagnosis_engine.schemas import (
    DiagnosisRequest,
    DeterministicSignals,
    DiagnosisValidationResult,
)


@runtime_checkable
class ISignalExtractor(Protocol):
    """Protocol for extracting deterministic features and telemetry from candidate attempts."""

    def extract_signals(self, request: DiagnosisRequest) -> DeterministicSignals:
        """Extracts objective empirical signals from response and attempt metadata."""
        ...


@runtime_checkable
class IDiagnosisValidator(Protocol):
    """Protocol for validating that a diagnosis is evidence-grounded and compliant with domain rules."""

    def validate(
        self, request: DiagnosisRequest, diagnosis: TransferFailureDiagnosisDTO
    ) -> DiagnosisValidationResult:
        """Validates that evidence quotes exist verbatim and constraints are satisfied."""
        ...


@runtime_checkable
class ITransferDiagnosisEngine(Protocol):
    """Protocol for top-level transfer failure diagnosis orchestrator."""

    async def diagnose(self, request: DiagnosisRequest) -> TransferFailureDiagnosisDTO:
        """Executes signal extraction, structured reasoning, validation, and returns TransferFailureDiagnosisDTO."""
        ...
