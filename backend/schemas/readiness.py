"""
Pydantic Schemas and Enums for Candidate Readiness Lifecycle and Gating.
Defines explicit prerequisite states and feature gating contracts.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CandidateReadinessState(str, Enum):
    """
    Explicit sequential readiness progression states for a candidate.
    """
    NO_RESUME = "NO_RESUME"
    RESUME_PROCESSING = "RESUME_PROCESSING"
    PROFILE_READY = "PROFILE_READY"
    ROLE_READY = "ROLE_READY"
    ASSESSMENT_READY = "ASSESSMENT_READY"
    COACHING_READY = "COACHING_READY"
    TRANSFER_READY = "TRANSFER_READY"


class CandidateReadinessResponse(BaseModel):
    """
    Authoritative backend readiness evaluation for an authenticated candidate.
    """
    candidate_id: str
    readiness_state: CandidateReadinessState = Field(
        ..., description="Current authoritative candidate lifecycle readiness state"
    )
    is_resume_uploaded: bool = Field(
        default=False, description="True if at least one resume record exists"
    )
    is_resume_processed: bool = Field(
        default=False, description="True if an active resume has completed parsing and evidence extraction"
    )
    is_profile_ready: bool = Field(
        default=False, description="True if grounded candidate profile with extracted skills exists"
    )
    is_role_selected: bool = Field(
        default=False, description="True if candidate has selected or configured a target engineering role"
    )
    target_role: Optional[str] = Field(
        default=None, description="Active target engineering role title if resolved"
    )
    is_assessment_ready: bool = Field(
        default=False, description="True if candidate has completed at least one evaluated interview assessment"
    )
    completed_interviews_count: int = Field(
        default=0, description="Total completed interview gauntlets with evaluation debriefs"
    )
    is_coaching_ready: bool = Field(
        default=False, description="True if candidate has diagnosed skill gaps and context for targeted coaching"
    )
    is_transfer_ready: bool = Field(
        default=False, description="True if candidate has completed prerequisite coaching for unassisted transfer"
    )
    allowed_features: List[str] = Field(
        default_factory=list, description="List of feature keys unlocked by current readiness state"
    )
    blocked_features: Dict[str, str] = Field(
        default_factory=dict, description="Feature keys that are blocked with human-readable rationale"
    )
    next_action: Dict[str, str] = Field(
        default_factory=dict, description="Recommended next action {action, route, title, rationale}"
    )
