"""
SQLAlchemy ORM model for Resume documents.
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

class ResumeModel(Base):
    __tablename__ = "resumes"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[uuid.UUID] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    checksum: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=True)
    processing_status: Mapped[str] = mapped_column(String(50), default="PENDING")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate: Mapped["CandidateModel"] = relationship("CandidateModel", back_populates="resumes")
    chunks: Mapped[list["ResumeChunkModel"]] = relationship("ResumeChunkModel", back_populates="resume", cascade="all, delete-orphan")
