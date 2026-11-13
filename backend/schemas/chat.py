"""
Domain models and DTO schemas for Chat and Intent Coordination.
Adheres to Pydantic v2 and clean architecture boundaries.
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ChatRole(str, Enum):
    """Permitted message sender roles in conversational dialogues."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ChatIntent(str, Enum):
    """Categorical user intents classified for coordinator routing."""
    GENERAL_CHAT = "GENERAL_CHAT"
    INTERVIEW = "INTERVIEW"
    EVALUATION = "EVALUATION"
    SKILL_GAP = "SKILL_GAP"
    ROADMAP = "ROADMAP"
    TRANSFER = "TRANSFER"
    COACHING = "COACHING"
    SESSION_STATUS = "SESSION_STATUS"


# Request / Response Schemas
class CreateConversationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    candidate_id: Optional[str] = Field(default=None, description="Optional candidate owner UUID")
    title: str = Field(default="New Conversation", max_length=255)
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Target role, focus skill, etc.")


class RenameConversationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., min_length=1, max_length=255)


class SendMessageRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    content: str = Field(..., min_length=1, description="Message text from user")
    candidate_id: Optional[str] = Field(default=None, description="Candidate ID if acting on behalf of user")
    target_role: Optional[str] = Field(default=None, description="Active target role context")
    focus_skill: Optional[str] = Field(default=None, description="Active competency focus")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional turn metadata (e.g. active_state)")


class ConversationMessageDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: str
    conversation_id: str
    role: str
    content: str
    message_type: str = "text"
    ui_payload: Optional[Dict[str, Any]] = None
    intent: Optional[str] = None
    sequence: int
    created_at: datetime


class ConversationDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: str
    candidate_id: Optional[str] = None
    title: str
    status: str
    metadata_: Optional[Dict[str, Any]] = Field(default=None, serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime
    messages_count: Optional[int] = 0


class ConversationDetailDTO(BaseModel):
    model_config = ConfigDict(extra="ignore", from_attributes=True)

    id: str
    candidate_id: Optional[str] = None
    title: str
    status: str
    metadata_: Optional[Dict[str, Any]] = Field(default=None, serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime
    messages: List[ConversationMessageDTO] = Field(default_factory=list)


class SendMessageResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    conversation_id: str
    user_message: ConversationMessageDTO
    assistant_message: ConversationMessageDTO
    detected_intent: ChatIntent
    is_fallback: Optional[bool] = False
    provider_used: Optional[str] = None
    stage_timings: Optional[Dict[str, Any]] = None


class InitiateCoachingRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    candidate_id: Optional[str] = Field(default=None, description="Candidate ID")
    conversation_id: Optional[str] = Field(default=None, description="Optional conversation UUID to resume or use")
    target_role: Optional[str] = Field(default=None, description="Target role (e.g. Backend Engineer)")
    focus_skill: Optional[str] = Field(default=None, description="Target competency or skill ID")
    interview_session_id: Optional[str] = Field(default=None, description="Source interview session ID")
    question_id: Optional[str] = Field(default=None, description="Source question ID")


class InitiateCoachingResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    conversation: ConversationDetailDTO
    focus_skill: str
    learning_objective: str
    why_it_matters: str
    target_role: str
    scaffold_level: str = "HIGH"
    active_phase: str = "PHASE_B_FUNDAMENTALS"
    is_resumed: bool = False
