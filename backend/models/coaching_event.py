"""
SQLAlchemy ORM model for Coaching Intervention Events.
Captures both domain intervention context and research telemetry for scaffold fading analysis.
"""

import uuid
from datetime import datetime
from typing import Optional
# pyrefly: ignore [missing-import]
from sqlalchemy import String, Text, DateTime, ForeignKey, Boolean
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


class CoachingInterventionEventModel(Base):
    __tablename__ = "coaching_intervention_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transfer_attempts.id"), nullable=True, index=True
    )
    diagnosis_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("transfer_diagnoses.id"), nullable=True, index=True
    )
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("interview_sessions.id"), nullable=False, index=True
    )

    intervention_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    scaffold_level: Mapped[str] = mapped_column(String(50), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    pedagogical_intent: Mapped[str] = mapped_column(Text, nullable=False)

    is_faded: Mapped[bool] = mapped_column(Boolean, default=False)
    retry_required: Mapped[bool] = mapped_column(Boolean, default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    attempt = relationship("TransferAttemptModel", back_populates="intervention_events")
    diagnosis = relationship("TransferDiagnosisModel", back_populates="interventions")
    session = relationship("InterviewSessionModel")
