"""
SQLAlchemy ORM models for Transfer Tasks and Transfer Attempts.
Defines invariant-preserving task transformations and captures candidate transfer performance.
"""

import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

JSONType = JSON


class TransferTaskModel(Base):
    __tablename__ = "transfer_tasks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    parent_task_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("transfer_tasks.id"), nullable=True, index=True)

    skill_id: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    transfer_level: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    surface_context: Mapped[str] = mapped_column(String(255), nullable=False)

    core_invariants: Mapped[list] = mapped_column(JSONType, default=list)
    surface_distractors: Mapped[list] = mapped_column(JSONType, default=list)
    expected_concepts: Mapped[list] = mapped_column(JSONType, default=list)
    rubric_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt_template: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    transfer_distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Hierarchical relationship (Parent Task -> Derived Variants)
    parent_task: Mapped[Optional["TransferTaskModel"]] = relationship(
        "TransferTaskModel", remote_side=[id], back_populates="derived_tasks"
    )
    derived_tasks: Mapped[List["TransferTaskModel"]] = relationship(
        "TransferTaskModel", back_populates="parent_task"
    )

    # Attempts on this transfer task
    attempts: Mapped[List["TransferAttemptModel"]] = relationship(
        "TransferAttemptModel", back_populates="transfer_task", cascade="all, delete-orphan"
    )


class TransferAttemptModel(Base):
    __tablename__ = "transfer_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)
    transfer_task_id: Mapped[str] = mapped_column(String(36), ForeignKey("transfer_tasks.id"), nullable=False, index=True)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False, index=True)

    # Reuses existing interview infrastructure rather than duplicating answer/evaluation storage
    question_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("questions.id"), nullable=True, index=True)
    answer_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("answers.id"), nullable=True, index=True)
    evaluation_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("evaluations.id"), nullable=True, index=True)

    transfer_success: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    independence_score: Mapped[float] = mapped_column(Float, default=1.0)
    scaffold_level_applied: Mapped[str] = mapped_column(String(50), default="INDEPENDENT")
    hints_requested_count: Mapped[int] = mapped_column(Integer, default=0)
    attempt_number: Mapped[int] = mapped_column(Integer, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("CandidateModel")
    transfer_task: Mapped["TransferTaskModel"] = relationship("TransferTaskModel", back_populates="attempts")
    session = relationship("InterviewSessionModel")
    question = relationship("QuestionModel")
    answer = relationship("AnswerModel")
    evaluation = relationship("EvaluationModel")

    diagnosis: Mapped[Optional["TransferDiagnosisModel"]] = relationship(
        "TransferDiagnosisModel", back_populates="attempt", uselist=False, cascade="all, delete-orphan"
    )
    intervention_events: Mapped[List["CoachingInterventionEventModel"]] = relationship(
        "CoachingInterventionEventModel", back_populates="attempt", cascade="all, delete-orphan"
    )
