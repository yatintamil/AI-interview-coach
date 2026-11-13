"""
SQLAlchemy ORM models for Candidate and CandidateProfile tables.
Adheres to postgresql.md & fastapi.md standards.
"""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional
# pyrefly: ignore [missing-import]
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from backend.models.resume import ResumeModel
    from backend.models.skill_state import CandidateSkillStateModel
else:
    import backend.models.resume  # noqa: F401
    import backend.models.skill_state  # noqa: F401

JSONType = JSON

from backend.models.base import Base

class CandidateModel(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    target_role: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    resumes: Mapped[list["ResumeModel"]] = relationship("ResumeModel", back_populates="candidate", cascade="all, delete-orphan")
    profile: Mapped["CandidateProfileModel"] = relationship("CandidateProfileModel", back_populates="candidate", uselist=False, cascade="all, delete-orphan")
    skill_states: Mapped[list["CandidateSkillStateModel"]] = relationship("CandidateSkillStateModel", back_populates="candidate", cascade="all, delete-orphan")

class CandidateProfileModel(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[uuid.UUID] = mapped_column(String(36), ForeignKey("candidates.id"), unique=True, nullable=False)
    resume_id: Mapped[uuid.UUID] = mapped_column(String(36), ForeignKey("resumes.id"), nullable=False)
    
    # Store complete CandidateProfile JSON
    profile_data: Mapped[dict] = mapped_column(JSONType, nullable=False)
    
    # Flat query fields
    skills_flat: Mapped[list] = mapped_column(JSONType, default=list)
    domains_flat: Mapped[list] = mapped_column(JSONType, default=list)
    total_years_exp: Mapped[float] = mapped_column(Float, default=0.0)

    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate: Mapped["CandidateModel"] = relationship("CandidateModel", back_populates="profile")
