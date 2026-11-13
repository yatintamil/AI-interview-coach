"""
Pydantic Schemas for Transfer Task Engine operations, generation requests, and validation.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, ConfigDict

from backend.domain.transfer.taxonomy import TransferLevel


class TransferGenerationRequest(BaseModel):
    """
    Specification submitted to the Transfer Task Engine to transform a training task
    into an invariant-preserving transfer challenge.
    """
    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(..., min_length=1, description="Competency key being evaluated.")
    transfer_level: TransferLevel = Field(..., description="Target transfer distance (L0 to L5).")
    core_invariants: List[str] = Field(..., min_length=1, description="Structural principles that MUST be preserved.")
    base_surface_context: str = Field(..., min_length=1, description="Original training surface domain (e.g. 'URL Shortener').")
    base_expected_concepts: List[str] = Field(..., min_length=1, description="Core technical concepts required.")

    parent_task_id: Optional[str] = Field(default=None, description="Identifier of training task (None for independent L5).")
    parent_prompt: Optional[str] = Field(default=None, description="Prompt text of the original question to check for trivial paraphrasing.")
    task_family: str = Field(default="system_design", description="Category: 'system_design', 'technical_reasoning', or 'behavioral_tradeoff'.")
    rubric_id: Optional[str] = Field(default=None, description="Evaluation rubric identifier.")


class TransferValidationResult(BaseModel):
    """
    Output of the multi-dimensional anti-triviality and invariant preservation validator.
    """
    model_config = ConfigDict(extra="forbid")

    is_valid: bool = Field(..., description="Whether the generated task satisfies all transfer constraints.")
    failure_reasons: List[str] = Field(default_factory=list, description="Specific criteria failures if invalid.")
    jaccard_similarity: float = Field(default=0.0, ge=0.0, le=1.0, description="Word token overlap with parent prompt.")
    invariants_preserved: bool = Field(default=True, description="Whether all core invariants are present in the target task.")
    surface_shifted: bool = Field(default=True, description="Whether the surface domain changed sufficiently for L2+.")
    level_consistent: bool = Field(default=True, description="Whether the structural framing aligns with requested transfer level.")


class TransferGenerationMetadata(BaseModel):
    """
    Research audit metadata stored to ensure reproducible experimental tracking.
    """
    model_config = ConfigDict(extra="forbid")

    generator_version: str = Field(default="1.0.0", description="Engine version identifier.")
    transformation_strategy: str = Field(..., description="Strategy name applied (e.g., 'DomainMappingShift', 'AmbiguityMasking').")
    transfer_level: TransferLevel = Field(..., description="Transfer taxonomy level.")
    parent_task_id: Optional[str] = Field(default=None, description="Original parent task ID.")
    validation_passed: bool = Field(..., description="Whether task passed validation.")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Generation timestamp.")
    provider_name: Optional[str] = Field(default="deterministic", description="AI provider or heuristic engine used.")
