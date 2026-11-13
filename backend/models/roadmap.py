"""
SQLAlchemy ORM models for Personalized Learning Roadmaps and Roadmap Items.
Directly grounded in candidate skill state gaps, role competencies, and transfer performance.
"""

import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
# pyrefly: ignore [missing-import]
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON, Boolean
# pyrefly: ignore [missing-import]
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from backend.models.candidate import CandidateModel
    from backend.models.interview import InterviewSessionModel

from backend.models.base import Base

JSONType = JSON


class PersonalizedRoadmapModel(Base):
    __tablename__ = "personalized_roadmaps"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)
    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    seniority: Mapped[str] = mapped_column(String(50), default="Mid")
    status: Mapped[str] = mapped_column(String(50), default="ACTIVE", index=True)  # ACTIVE, COMPLETED, ARCHIVED

    overall_progress: Mapped[float] = mapped_column(Float, default=0.0)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)

    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta_info: Mapped[dict] = mapped_column(JSONType, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    candidate = relationship("CandidateModel", backref="roadmaps")
    items: Mapped[List["RoadmapItemModel"]] = relationship(
        "RoadmapItemModel",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapItemModel.sequence_order",
        lazy="selectin",
    )


class RoadmapItemModel(Base):
    __tablename__ = "roadmap_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    roadmap_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("personalized_roadmaps.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    skill_id: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    skill_title: Mapped[str] = mapped_column(String(255), nullable=False)
    role_importance: Mapped[str] = mapped_column(String(50), default="CORE")  # CORE, SECONDARY, SPECIALIZED, CROSS_FUNCTIONAL
    priority: Mapped[str] = mapped_column(String(50), default="HIGH", index=True)  # CRITICAL, HIGH, MEDIUM, LOW, SATISFIED
    sequence_order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    learning_objective: Mapped[str] = mapped_column(Text, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    current_mastery: Mapped[float] = mapped_column(Float, default=0.0)
    target_mastery: Mapped[float] = mapped_column(Float, default=0.80)
    current_transfer_level: Mapped[str] = mapped_column(String(50), default="L0_RECALL")
    target_transfer_level: Mapped[str] = mapped_column(String(50), default="L5_INDEPENDENT_TRANSFER")
    assistance_dependency: Mapped[float] = mapped_column(Float, default=0.0)

    status: Mapped[str] = mapped_column(String(50), default="NOT_STARTED", index=True)  # NOT_STARTED, IN_PROGRESS, PRACTICING, COMPLETED
    coaching_session_id: Mapped[Optional[str]] = mapped_column(
        String(36),
        ForeignKey("interview_sessions.id", ondelete="SET NULL"),
        nullable=True,
    )

    core_invariants: Mapped[list] = mapped_column(JSONType, default=list)
    recurring_failures: Mapped[list] = mapped_column(JSONType, default=list)
    actionable_steps: Mapped[list] = mapped_column(JSONType, default=list)

    # Actionable Milestone details & learning progression
    topics_to_study: Mapped[list] = mapped_column(JSONType, default=list)
    practical_exercises: Mapped[list] = mapped_column(JSONType, default=list)
    implementation_task: Mapped[dict] = mapped_column(JSONType, default=dict)
    expected_deliverables: Mapped[list] = mapped_column(JSONType, default=list)
    estimated_duration: Mapped[str] = mapped_column(String(100), default="1-2 weeks")
    difficulty_level: Mapped[str] = mapped_column(String(50), default="INTERMEDIATE")  # FOUNDATIONAL, INTERMEDIATE, ADVANCED, EXPERT
    evaluation_criteria: Mapped[list] = mapped_column(JSONType, default=list)
    evidence_required: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prerequisite_milestone_ids: Mapped[list] = mapped_column(JSONType, default=list)
    mapping_status: Mapped[str] = mapped_column(String(50), default="MAPPED")  # MAPPED, REVIEW_FLAGGED
    is_flagged_for_review: Mapped[bool] = mapped_column(Boolean, default=False)
    progression_tier: Mapped[str] = mapped_column(String(100), default="Tier 1: Assessed, Needs Practice")
    proficiency_state: Mapped[str] = mapped_column(String(50), default="NOT_ASSESSED")

    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    roadmap: Mapped["PersonalizedRoadmapModel"] = relationship("PersonalizedRoadmapModel", back_populates="items", lazy="selectin")
    coaching_session = relationship("InterviewSessionModel", foreign_keys=[coaching_session_id], lazy="selectin")
