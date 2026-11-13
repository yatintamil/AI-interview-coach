"""
FastAPI Router for Conversations and Chat Management.
Exposes endpoints for conversation lifecycles and dialogue turns.
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db_session
from backend.core.security import (
    get_authenticated_candidate_id,
    require_authenticated_candidate_id,
    verify_candidate_access,
)
from backend.services.conversation_service import ConversationService
from backend.services.coaching_tutor_service import CoachingTutorService
from backend.schemas.chat import (
    CreateConversationRequest,
    RenameConversationRequest,
    SendMessageRequest,
    ConversationDTO,
    ConversationDetailDTO,
    SendMessageResponse,
    InitiateCoachingRequest,
    InitiateCoachingResponse,
)

router = APIRouter(prefix="/chat", tags=["Conversational AI Coach"])


@router.post(
    "/coaching/initiate",
    response_model=InitiateCoachingResponse,
    status_code=status.HTTP_200_OK,
    summary="Initiate proactive Conversational AI Coaching Session",
)
async def initiate_coaching(
    payload: InitiateCoachingRequest,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Initiates a proactive AI coaching session: pulls candidate deficits,
    formulates a clear learning objective, and immediately delivers the opening
    teaching lesson without requiring an initial candidate answer.
    """
    verify_candidate_access(payload.candidate_id, authenticated_candidate_id)
    tutor_service = CoachingTutorService(db)
    return await tutor_service.initiate_coaching_session(payload)


@router.post(
    "/conversations",
    response_model=ConversationDTO,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation thread",
)
async def create_conversation(
    payload: CreateConversationRequest,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """Initializes a new persistent conversation thread."""
    if payload.candidate_id:
        verify_candidate_access(payload.candidate_id, authenticated_candidate_id)
    else:
        payload.candidate_id = authenticated_candidate_id
    service = ConversationService(db)
    return await service.create_conversation(payload)


@router.get(
    "/conversations",
    response_model=List[ConversationDTO],
    summary="List all conversations or filter by candidate",
)
async def list_conversations(
    candidate_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieves conversation threads ordered by recency."""
    effective_candidate_id = candidate_id or authenticated_candidate_id
    verify_candidate_access(effective_candidate_id, authenticated_candidate_id)
    service = ConversationService(db)
    return await service.list_conversations(candidate_id=effective_candidate_id, skip=skip, limit=limit)


@router.get(
    "/conversations/{conversation_id}",
    response_model=ConversationDetailDTO,
    summary="Retrieve full conversation thread and chronological messages",
)
async def get_conversation(
    conversation_id: str,
    candidate_id: Optional[str] = None,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """Retrieves conversation details along with all messages ordered chronologically."""
    effective_cand_id = candidate_id or authenticated_candidate_id
    verify_candidate_access(effective_cand_id, authenticated_candidate_id)
    service = ConversationService(db)
    return await service.get_conversation(conversation_id=conversation_id, candidate_id=effective_cand_id)


@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationDTO,
    summary="Rename conversation title",
)
async def rename_conversation(
    conversation_id: str,
    payload: RenameConversationRequest,
    candidate_id: Optional[str] = None,
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """Renames an existing conversation thread."""
    effective_cand_id = authenticated_candidate_id or candidate_id
    if authenticated_candidate_id and candidate_id:
        verify_candidate_access(candidate_id, authenticated_candidate_id)
    service = ConversationService(db)
    return await service.rename_conversation(conversation_id=conversation_id, payload=payload, candidate_id=effective_cand_id)


@router.delete(
    "/conversations/{conversation_id}",
    response_model=Dict[str, Any],
    summary="Delete conversation and cascade delete all messages",
)
async def delete_conversation(
    conversation_id: str,
    candidate_id: Optional[str] = None,
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """Permanently deletes a conversation thread and all its messages."""
    effective_cand_id = authenticated_candidate_id or candidate_id
    if authenticated_candidate_id and candidate_id:
        verify_candidate_access(candidate_id, authenticated_candidate_id)
    service = ConversationService(db)
    return await service.delete_conversation(conversation_id=conversation_id, candidate_id=effective_cand_id)


@router.post(
    "/conversations/{conversation_id}/messages",
    response_model=SendMessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Send a user message and receive AI Coach response",
)
async def send_message(
    conversation_id: str,
    payload: SendMessageRequest,
    authenticated_candidate_id: Optional[str] = Depends(get_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Submits a candidate message, classifies intent, delegates to domain engines or AI synthesis,
    and returns both the persisted user message and assistant turn.
    """
    if authenticated_candidate_id:
        if payload.candidate_id:
            verify_candidate_access(payload.candidate_id, authenticated_candidate_id)
        else:
            payload.candidate_id = authenticated_candidate_id
        service = ConversationService(db)
        # Check that conversation itself belongs to authenticated candidate
        convo = await service.convo_repo.get(conversation_id)
        if convo and convo.candidate_id and str(convo.candidate_id) != str(authenticated_candidate_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Conversation '{conversation_id}' does not belong to candidate '{authenticated_candidate_id}'.",
            )
    else:
        service = ConversationService(db)
    return await service.process_user_turn(conversation_id=conversation_id, payload=payload)
