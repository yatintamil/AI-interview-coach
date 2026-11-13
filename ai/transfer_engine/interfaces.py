"""
Interfaces and Protocols for Transfer Task Engine components.
Enforces modular decoupling between generation, transformation, and validation.
"""

from typing import Protocol, Dict, Any, runtime_checkable
from backend.domain.transfer.schemas import TransferTaskDefinitionDTO
from ai.transfer_engine.schemas import (
    TransferGenerationRequest,
    TransferValidationResult,
)


@runtime_checkable
class ITransferTransformer(Protocol):
    """Protocol for transforming a training specification into a transfer challenge."""

    async def transform(self, request: TransferGenerationRequest) -> Dict[str, Any]:
        """Executes invariant-preserving transfer transformation."""
        ...


@runtime_checkable
class ITransferValidator(Protocol):
    """Protocol for verifying that a generated task preserves invariants and avoids trivial paraphrasing."""

    def validate(
        self, request: TransferGenerationRequest, candidate_task: Dict[str, Any]
    ) -> TransferValidationResult:
        """Validates candidate transfer task against empirical anti-triviality invariants."""
        ...


@runtime_checkable
class ITransferTaskGenerator(Protocol):
    """Protocol for the top-level Transfer Task Engine orchestrator."""

    async def generate_transfer_task(
        self, request: TransferGenerationRequest
    ) -> TransferTaskDefinitionDTO:
        """Orchestrates transformation, validation, and returns a verified TransferTaskDefinitionDTO."""
        ...
