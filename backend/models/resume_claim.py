"""
SQLAlchemy ORM model for Candidate Claims (Claimed vs. Verified Skill Decomposition).
Foundation for Candidate Evidence Graph (CEG).
"""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column

from backend.models.base import Base

JSONType = JSON


class CandidateClaimModel(Base):
    __tablename__ = "candidate_claims"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)
    resume_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("resumes.id"), nullable=True, index=True)

    skill_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    complexity: Mapped[str] = mapped_column(String(50), default="INTERMEDIATE")  # FOUNDATIONAL, INTERMEDIATE, ADVANCED, SYSTEM_LEVEL
    verification_status: Mapped[str] = mapped_column(String(50), default="UNVERIFIED", index=True)  # UNVERIFIED, PROBED, VERIFIED, CONTESTED
    confidence_score: Mapped[float] = mapped_column(Float, default=0.5)

    verified_quotes: Mapped[list] = mapped_column(JSONType, default=list)
    probe_count: Mapped[int] = mapped_column(Integer, default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
