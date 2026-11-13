"""
Conversation Repository for Async SQLAlchemy CRUD operations.
Handles conversation threads, chronological message logs, title updates,
and candidate-scoped history retrieval.
"""

from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, delete, update, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.models.conversation import ConversationModel, ConversationMessageModel
from backend.repositories.base import BaseRepository


class ConversationRepository(BaseRepository[ConversationModel]):
    """
    Repository for ConversationModel and associated ConversationMessageModel entities.
    """

    def __init__(self, session: AsyncSession):
        super().__init__(ConversationModel, session)

    async def get_with_messages(self, conversation_id: Union[str, UUID]) -> Optional[ConversationModel]:
        """
        Retrieves a conversation by ID, eagerly loading all messages ordered chronologically.
        Always fetches fresh messages to avoid stale in-memory session collections.
        """
        convo_id_str = str(conversation_id)
        stmt = (
            select(ConversationModel)
            .where(ConversationModel.id == convo_id_str)
            .options(
                selectinload(ConversationModel.messages),
                selectinload(ConversationModel.candidate),
            )
            .execution_options(populate_existing=True)
        )
        res = await self.session.execute(stmt)
        convo = res.scalars().first()
        if convo:
            msg_stmt = (
                select(ConversationMessageModel)
                .where(ConversationMessageModel.conversation_id == convo_id_str)
                .order_by(ConversationMessageModel.sequence.asc())
            )
            msg_res = await self.session.execute(msg_stmt)
            convo.messages = list(msg_res.scalars().all())
        return convo

    async def get_messages(self, conversation_id: Union[str, UUID]) -> List[ConversationMessageModel]:
        """
        Retrieves all messages for a conversation strictly ordered chronologically by sequence.
        """
        stmt = (
            select(ConversationMessageModel)
            .where(ConversationMessageModel.conversation_id == str(conversation_id))
            .order_by(ConversationMessageModel.sequence.asc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_candidate(
        self, candidate_id: str, skip: int = 0, limit: int = 50
    ) -> List[ConversationModel]:
        """
        Lists conversations belonging to a candidate ordered by recency (updated_at DESC).
        """
        stmt = (
            select(ConversationModel)
            .where(ConversationModel.candidate_id == candidate_id)
            .options(selectinload(ConversationModel.messages))
            .order_by(ConversationModel.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def create_conversation(
        self,
        candidate_id: Optional[str] = None,
        title: str = "New Conversation",
        metadata: Optional[Dict[str, Any]] = None,
        status: str = "ACTIVE",
    ) -> ConversationModel:
        """
        Creates and persists a new conversation instance.
        """
        convo = ConversationModel(
            candidate_id=candidate_id,
            title=title,
            metadata_=metadata or {},
            status=status,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        self.session.add(convo)
        await self.session.flush()
        return convo

    async def update_title(self, conversation_id: Union[str, UUID], title: str) -> Optional[ConversationModel]:
        """
        Updates the conversation title and touches updated_at timestamp.
        """
        convo = await self.get(conversation_id)
        if not convo:
            return None
        convo.title = title
        convo.updated_at = datetime.utcnow()
        await self.session.flush()
        return convo

    async def add_message(
        self,
        conversation_id: Union[str, UUID],
        role: str,
        content: str,
        message_type: str = "text",
        ui_payload: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
    ) -> ConversationMessageModel:
        """
        Appends a message to a conversation with auto-incremented sequence number
        and touches the parent conversation's updated_at timestamp.
        """
        convo_id_str = str(conversation_id)

        # Determine next sequence number for deterministic chronological ordering
        seq_stmt = select(func.coalesce(func.max(ConversationMessageModel.sequence), 0)).where(
            ConversationMessageModel.conversation_id == convo_id_str
        )
        seq_res = await self.session.execute(seq_stmt)
        next_seq = (seq_res.scalar() or 0) + 1

        message = ConversationMessageModel(
            conversation_id=convo_id_str,
            role=role,
            content=content,
            message_type=message_type,
            ui_payload=ui_payload,
            intent=intent,
            sequence=next_seq,
            created_at=datetime.utcnow(),
        )
        self.session.add(message)

        # Touch parent conversation updated_at
        touch_stmt = (
            update(ConversationModel)
            .where(ConversationModel.id == convo_id_str)
            .values(updated_at=datetime.utcnow())
        )
        await self.session.execute(touch_stmt)
        await self.session.flush()
        return message

    async def get_messages(
        self, conversation_id: Union[str, UUID], skip: int = 0, limit: int = 100
    ) -> List[ConversationMessageModel]:
        """
        Retrieves messages for a conversation strictly ordered by sequence ASC.
        """
        stmt = (
            select(ConversationMessageModel)
            .where(ConversationMessageModel.conversation_id == str(conversation_id))
            .order_by(ConversationMessageModel.sequence.asc())
            .offset(skip)
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def delete_conversation(self, conversation_id: Union[str, UUID]) -> bool:
        """
        Deletes a conversation by ID. Cascade configuration will automatically
        delete all linked conversation messages.
        """
        convo = await self.get(conversation_id)
        if not convo:
            return False
        await self.session.delete(convo)
        await self.session.flush()
        return True
