"""
SQLAlchemy ORM model for Transfer Failure Diagnosis.
Captures root causes, confidence, deterministic signals, evidence grounding,
and recommended interventions.
"""

import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.transfer_task import TransferAttemptModel
    from backend.models.coaching_event import CoachingInterventionEventModel
else:
    # Ensure related models are imported into Base.registry at runtime
    import backend.models.transfer_task  # noqa: F401
    import backend.models.coaching_event  # noqa: F401

JSONType = JSON


class TransferDiagnosisModel(Base):
    __tablename__ = "transfer_diagnoses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    attempt_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("transfer_attempts.id"), unique=True, nullable=False, index=True
    )

    failure_type: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    affected_skill: Mapped[str] = mapped_column(String(150), nullable=False, index=True)

    deterministic_signals: Mapped[dict] = mapped_column(JSONType, default=dict)
    evidence: Mapped[list] = mapped_column(JSONType, default=list)
    recommended_intervention: Mapped[str] = mapped_column(String(100), nullable=False)
    diagnostic_reasoning: Mapped[str] = mapped_column(Text, nullable=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    attempt: Mapped["TransferAttemptModel"] = relationship("TransferAttemptModel", back_populates="diagnosis")
    interventions: Mapped[List["CoachingInterventionEventModel"]] = relationship(
        "CoachingInterventionEventModel", back_populates="diagnosis"
    )
