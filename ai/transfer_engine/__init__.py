"""
Transfer Task Engine.
Generates, transforms, and empirically validates invariant-preserving transfer challenges across L0-L5.
"""

from ai.transfer_engine.schemas import (
    TransferGenerationRequest,
    TransferValidationResult,
    TransferGenerationMetadata,
)
from ai.transfer_engine.interfaces import (
    ITransferTransformer,
    ITransferValidator,
    ITransferTaskGenerator,
)
from ai.transfer_engine.validators import TransferTaskValidator, calculate_jaccard_similarity
from ai.transfer_engine.transfer_transformer import TransferTransformer, TASK_FAMILY_CATALOG
from ai.transfer_engine.task_generator import TransferTaskGenerator
from ai.transfer_engine.normalization import (
    normalize_surface_context,
    normalize_transfer_task_dict,
)

__all__ = [
    "TransferGenerationRequest",
    "TransferValidationResult",
    "TransferGenerationMetadata",
    "ITransferTransformer",
    "ITransferValidator",
    "ITransferTaskGenerator",
    "TransferTaskValidator",
    "calculate_jaccard_similarity",
    "TransferTransformer",
    "TASK_FAMILY_CATALOG",
    "TransferTaskGenerator",
    "normalize_surface_context",
    "normalize_transfer_task_dict",
]
