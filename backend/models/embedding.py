"""
SQLAlchemy ORM model for Resume vector chunks (pgvector).
"""

import uuid
from datetime import datetime
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

from ai.config import ai_settings

try:
    from pgvector.sqlalchemy import Vector
    EmbeddingVectorType = Vector(ai_settings.embedding_dimension)
except Exception:
    EmbeddingVectorType = JSON

class ResumeChunkModel(Base):
    __tablename__ = "resume_chunks"

    id: Mapped[uuid.UUID] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    resume_id: Mapped[uuid.UUID] = mapped_column(String(36), ForeignKey("resumes.id"), nullable=False)
    candidate_id: Mapped[uuid.UUID] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)
    
    section_name: Mapped[str] = mapped_column(String(100), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # 384 dimension vector for all-MiniLM-L6-v2 (Option A)
    embedding: Mapped[list] = mapped_column(EmbeddingVectorType, nullable=False)
    
    chunk_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    resume: Mapped["ResumeModel"] = relationship("ResumeModel", back_populates="chunks")
