"""
Pydantic Schemas for Candidate Claims and Candidate Evidence Graph (CEG).
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class CandidateClaimResponse(BaseModel):
    id: str
    candidate_id: str
    resume_id: Optional[str] = None
    skill_name: str
    claim_text: str
    complexity: str = "INTERMEDIATE"
    verification_status: str = "UNVERIFIED"
    confidence_score: float = 0.5
    verified_quotes: List[str] = Field(default_factory=list)
    probe_count: int = 0
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CandidateEvidenceGraphResponse(BaseModel):
    candidate_id: str
    total_claims: int
    verified_count: int
    probed_count: int
    overall_verification_ratio: float
    claims: List[CandidateClaimResponse]
