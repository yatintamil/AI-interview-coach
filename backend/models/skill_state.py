"""
SQLAlchemy ORM model for Candidate Longitudinal Skill State.
Tracks latent mastery estimate, engineering uncertainty, highest validated transfer level,
and assistance dependency across interview iterations.
"""

import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import String, Float, Integer, DateTime, ForeignKey, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

if TYPE_CHECKING:
    from backend.models.candidate import CandidateModel
else:
    import backend.models.candidate  # noqa: F401

JSONType = JSON


class CandidateSkillStateModel(Base):
    __tablename__ = "candidate_skill_states"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)

    skill_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    mastery_estimate: Mapped[float] = mapped_column(Float, default=0.0)
    mastery_uncertainty: Mapped[float] = mapped_column(Float, default=1.0)
    highest_transfer_level: Mapped[str] = mapped_column(String(50), default="L0_RECALL")
    assistance_dependency_index: Mapped[float] = mapped_column(Float, default=0.0)

    recurring_failure_types: Mapped[list] = mapped_column(JSONType, default=list)
    total_attempts: Mapped[int] = mapped_column(Integer, default=0)

    last_assessed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    candidate: Mapped["CandidateModel"] = relationship("CandidateModel", back_populates="skill_states")
