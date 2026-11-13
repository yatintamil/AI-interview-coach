"""
SQLAlchemy ORM models for Experimental Framework sessions and trials.
Preserves raw experimental telemetry as immutable ground truth.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

JSONType = JSON


class ExperimentSessionModel(Base):
    """
    Persisted experimental session record linking candidate, condition, and task set.
    """
    __tablename__ = "experiment_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)
    experiment_name: Mapped[str] = mapped_column(String(255), nullable=False)
    condition: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # CONDITION_A, CONDITION_B, CONDITION_C
    skill: Mapped[str] = mapped_column(String(100), nullable=False)
    task_set_id: Mapped[str] = mapped_column(String(100), nullable=False)
    config_json: Mapped[Dict[str, Any]] = mapped_column(JSONType, nullable=False)
    current_phase: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="IN_PROGRESS", index=True)
    execution_provenance: Mapped[str] = mapped_column(String(50), default="SYNTHETIC", nullable=True)

    start_time: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    candidate = relationship("CandidateModel", backref="experiment_sessions")
    trials: Mapped[List["ExperimentTrialModel"]] = relationship(
        "ExperimentTrialModel",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ExperimentTrialModel.timestamp",
    )


class ExperimentTrialModel(Base):
    """
    Persisted raw observation for an individual experimental trial.
    Serves as the immutable primary record for research telemetry.
    """
    __tablename__ = "experiment_trials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiment_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    task_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    phase: Mapped[str] = mapped_column(String(50), nullable=False)
    transfer_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    difficulty: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    transfer_distance: Mapped[Optional[float]] = mapped_column(Float, nullable=True, default=None)

    attempt_number: Mapped[int] = mapped_column(Integer, default=1)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    outcome: Mapped[str] = mapped_column(String(50), nullable=False)
    response_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)

    feedback_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    candidate_answer_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    intervention_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    scaffold_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    hints_requested_count: Mapped[int] = mapped_column(Integer, default=0)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)

    # Evaluator Provenance and Traceability
    evaluator_provider: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, default="GROUNDED_NLP")
    evaluator_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="v1.0")
    rubric_version: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default="technical_v1")
    evaluator_fallback: Mapped[bool] = mapped_column(Boolean, default=False, nullable=True)
    fallback_reason: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    form_id: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, default="FORM_A")
    execution_provenance: Mapped[str] = mapped_column(String(50), nullable=True, default="SYNTHETIC")

    # Condition C specific diagnostic fields (null for Baseline A & B)
    diagnosis_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    diagnosis_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    affected_skill: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    diagnostic_evidence_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSONType, nullable=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationship back to session
    session: Mapped["ExperimentSessionModel"] = relationship("ExperimentSessionModel", back_populates="trials")


class ExperimentParticipantAssignmentModel(Base):
    """
    Authoritative record locking a participant to their assigned experimental condition.
    Ensures strict between-subjects isolation and prevents concurrent condition divergence.
    """
    __tablename__ = "experiment_participant_assignments"

    candidate_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    condition: Mapped[str] = mapped_column(String(50), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))


class ExperimentConsentModel(Base):
    """
    Persisted record of informed consent for experiment participants.
    Records explicit consent status, version, timestamps, and voluntary withdrawal state.
    """
    __tablename__ = "experiment_consents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), unique=True, nullable=False, index=True)
    consent_status: Mapped[str] = mapped_column(String(20), default="CONSENTED", nullable=False, index=True)  # CONSENTED, WITHDRAWN, DECLINED
    consent_version: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g. "v1.0-feasibility-study"
    consented_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    withdrawn_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    withdrawal_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    study_title: Mapped[str] = mapped_column(
        String(255),
        default="Transfer-Aware AI Interview Coaching Feasibility Study",
        nullable=False,
    )
    study_metadata_json: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONType, nullable=True)


class ExperimentRetentionScheduleModel(Base):
    """
    Persisted schedule for 7-day or 14-day delayed retention assessments.
    Enables reproducible longitudinal follow-ups and supervised tracking.
    """
    __tablename__ = "experiment_retention_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("experiment_sessions.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)
    delay_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(50), default="PENDING", nullable=False, index=True)  # PENDING, DUE, OVERDUE, COMPLETED, CANCELLED
    retention_session_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

