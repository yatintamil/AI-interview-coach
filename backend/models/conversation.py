"""
SQLAlchemy ORM models for Persistent Conversations and Conversation Messages.
Supports ChatGPT-like conversational flows while maintaining clean relational
separation from domain engine state.
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, Text, Integer, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base

from sqlalchemy.ext.mutable import MutableDict

JSONType = MutableDict.as_mutable(JSON)


class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    candidate_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, default="New Conversation")
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="ACTIVE", index=True)
    metadata_: Mapped[Optional[dict]] = mapped_column("metadata", JSONType, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Relationships
    candidate = relationship("CandidateModel", backref="conversations")
    messages: Mapped[List["ConversationMessageModel"]] = relationship(
        "ConversationMessageModel",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessageModel.sequence",
    )


class ConversationMessageModel(Base):
    __tablename__ = "conversation_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role: Mapped[str] = mapped_column(String(32), nullable=False)  # user / assistant / system / tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(50), nullable=False, default="text")  # text / card / error / system
    ui_payload: Mapped[Optional[dict]] = mapped_column(JSONType, nullable=True)
    intent: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    conversation: Mapped["ConversationModel"] = relationship("ConversationModel", back_populates="messages")

    __table_args__ = (
        Index("ix_conversation_messages_convo_seq", "conversation_id", "sequence"),
    )
