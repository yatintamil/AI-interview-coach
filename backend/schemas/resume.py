"""
Pydantic v2 schemas for Resume endpoints.
"""

from uuid import UUID
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
from backend.schemas.candidate_profile import CandidateProfile

class ResumeUploadRequest(BaseModel):
    candidate_id: UUID = Field(..., description="UUID of candidate")

class ResumeParseResponse(BaseModel):
    resume_id: UUID = Field(..., description="Created resume record ID")
    candidate_id: UUID = Field(..., description="Candidate ID")
    status: str = Field(..., description="Processing status (e.g. COMPLETED, PROCESSING, FAILED)")
    profile: CandidateProfile = Field(..., description="Extracted candidate profile")
    indexed_rag_chunks: int = Field(default=0, description="Number of vector chunks indexed for RAG")
    created_at: datetime = Field(default_factory=datetime.utcnow)

class ResumeResponse(BaseModel):
    id: UUID
    candidate_id: UUID
    file_name: str
    file_type: str
    file_size_bytes: int
    checksum: str
    processing_status: str
    created_at: datetime
