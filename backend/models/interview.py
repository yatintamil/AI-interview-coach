"""
SQLAlchemy ORM models for Interviews, Questions, Answers, Evaluations, and Session Reports.
Follows clean relational modeling with foreign keys and cascade deletions.
"""

import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, Text, Float, Integer, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

JSONType = JSON


class InterviewSessionModel(Base):
    __tablename__ = "interview_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[str] = mapped_column(String(36), ForeignKey("candidates.id"), nullable=False, index=True)
    resume_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("resumes.id"), nullable=True)

    target_role: Mapped[str] = mapped_column(String(255), nullable=False)
    target_roles: Mapped[Optional[list]] = mapped_column(JSONType, nullable=True)
    custom_role_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    interview_type: Mapped[str] = mapped_column(String(50), default="TECHNICAL")  # TECHNICAL, BEHAVIORAL, MIXED
    difficulty_level: Mapped[str] = mapped_column(String(50), default="MEDIUM")   # EASY, MEDIUM, HARD
    status: Mapped[str] = mapped_column(String(50), default="CREATED", index=True)  # CREATED, IN_PROGRESS, COMPLETED, CANCELLED
    coaching_mode: Mapped[str] = mapped_column(String(50), default="COACHING")     # COACHING, SIMULATION

    target_question_count: Mapped[int] = mapped_column(Integer, default=5)
    current_question_index: Mapped[int] = mapped_column(Integer, default=0)
    completion_reason: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    evidence_coverage_ratio: Mapped[float] = mapped_column(Float, default=0.0)
    assessment_plan: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    competency_state: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)

    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("CandidateModel", backref="interview_sessions")
    resume = relationship("ResumeModel", backref="interview_sessions")
    questions: Mapped[List["QuestionModel"]] = relationship(
        "QuestionModel", back_populates="session", cascade="all, delete-orphan", order_by="QuestionModel.question_index"
    )
    report: Mapped[Optional["SessionReportModel"]] = relationship(
        "SessionReportModel", back_populates="session", uselist=False, cascade="all, delete-orphan"
    )


class QuestionModel(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False, index=True)
    question_index: Mapped[int] = mapped_column(Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(100), default="technical")
    topic: Mapped[str] = mapped_column(String(255), default="General")
    difficulty: Mapped[str] = mapped_column(String(50), default="medium")
    stage_name: Mapped[Optional[str]] = mapped_column(String(100), default="Foundational Orientation", nullable=True)
    stage_index: Mapped[int] = mapped_column(Integer, default=1)
    target_competency: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    assessment_objective: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_followup: Mapped[bool] = mapped_column(Boolean, default=False)
    question_plan: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    resume_evidence: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expected_concepts: Mapped[list] = mapped_column(JSONType, default=list)
    coach_lead_in: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    session: Mapped["InterviewSessionModel"] = relationship("InterviewSessionModel", back_populates="questions")
    answer: Mapped[Optional["AnswerModel"]] = relationship(
        "AnswerModel", back_populates="question", uselist=False, cascade="all, delete-orphan"
    )


class AnswerModel(Base):
    __tablename__ = "answers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("questions.id"), unique=True, nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False, index=True)
    answer_text: Mapped[Text] = mapped_column(Text, nullable=False)
    response_time_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    submitted_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    question: Mapped["QuestionModel"] = relationship("QuestionModel", back_populates="answer")
    evaluation: Mapped[Optional["EvaluationModel"]] = relationship(
        "EvaluationModel", back_populates="answer", uselist=False, cascade="all, delete-orphan"
    )


class EvaluationModel(Base):
    __tablename__ = "evaluations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    answer_id: Mapped[str] = mapped_column(String(36), ForeignKey("answers.id"), unique=True, nullable=False)
    question_id: Mapped[str] = mapped_column(String(36), ForeignKey("questions.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), nullable=False, index=True)

    overall_score: Mapped[float] = mapped_column(Float, nullable=False)
    correctness: Mapped[float] = mapped_column(Float, default=0.0)
    completeness: Mapped[float] = mapped_column(Float, default=0.0)
    relevance: Mapped[float] = mapped_column(Float, default=0.0)
    technical_depth: Mapped[float] = mapped_column(Float, default=0.0)
    reasoning: Mapped[float] = mapped_column(Float, default=0.0)

    strengths: Mapped[list] = mapped_column(JSONType, default=list)
    weaknesses: Mapped[list] = mapped_column(JSONType, default=list)
    missing_concepts: Mapped[list] = mapped_column(JSONType, default=list)
    evidence: Mapped[list] = mapped_column(JSONType, default=list)
    recommendations: Mapped[list] = mapped_column(JSONType, default=list)
    exemplar_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coach_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    answer: Mapped["AnswerModel"] = relationship("AnswerModel", back_populates="evaluation")


class SessionReportModel(Base):
    __tablename__ = "session_reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("interview_sessions.id"), unique=True, nullable=False)

    final_score: Mapped[float] = mapped_column(Float, nullable=False)
    technical_score: Mapped[float] = mapped_column(Float, default=0.0)
    behavioral_score: Mapped[float] = mapped_column(Float, default=0.0)
    communication_score: Mapped[float] = mapped_column(Float, default=0.0)

    summary_strengths: Mapped[list] = mapped_column(JSONType, default=list)
    summary_weaknesses: Mapped[list] = mapped_column(JSONType, default=list)
    key_recommendations: Mapped[list] = mapped_column(JSONType, default=list)
    role_competency_profile: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    generated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    session: Mapped["InterviewSessionModel"] = relationship("InterviewSessionModel", back_populates="report")
