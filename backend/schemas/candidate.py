"""
Pydantic Schemas for Candidate Management and API payloads.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, EmailStr, Field


class CandidateCreateRequest(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    full_name: str = Field(..., min_length=1, max_length=255)
    password: Optional[str] = Field(None, min_length=6, max_length=128)


class CandidateUpdateRequest(BaseModel):
    email: Optional[str] = Field(None, pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    full_name: Optional[str] = Field(None, min_length=1, max_length=255)
    target_role: Optional[str] = Field(None, max_length=255)


class ResumeSummaryResponse(BaseModel):
    id: str
    file_name: str
    file_type: str
    file_size_bytes: int
    processing_status: str
    is_active: bool
    created_at: datetime


class CandidateResponse(BaseModel):
    id: str
    email: str
    full_name: str
    created_at: datetime
    resumes: List[ResumeSummaryResponse] = []
    has_profile: bool = False
    skills_summary: List[str] = []
    total_years_exp: float = 0.0
    readiness_state: str = "NO_RESUME"
    target_role: Optional[str] = None


class CandidateListResponse(BaseModel):
    candidates: List[CandidateResponse]
    total: int
