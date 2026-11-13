"""
Resume & ResumeChunk Repository.
Handles vector persistence, pgvector similarity queries, and resume activation.
"""

from typing import List, Dict, Any, Optional
from uuid import UUID
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession
# pyrefly: ignore [missing-import]
from sqlalchemy.future import select
# pyrefly: ignore [missing-import]
from sqlalchemy import update

from backend.models.resume import ResumeModel
from backend.models.embedding import ResumeChunkModel
from backend.repositories.base import BaseRepository


class ResumeRepository(BaseRepository[ResumeModel]):
    def __init__(self, session: AsyncSession):
        super().__init__(ResumeModel, session)

    async def get_by_checksum(self, checksum: str) -> Optional[ResumeModel]:
        stmt = select(ResumeModel).where(ResumeModel.checksum == checksum)
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def list_by_candidate(self, candidate_id: str) -> List[ResumeModel]:
        stmt = select(ResumeModel).where(ResumeModel.candidate_id == candidate_id).order_by(ResumeModel.created_at.desc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_active_resume(self, candidate_id: str) -> Optional[ResumeModel]:
        stmt = select(ResumeModel).where(ResumeModel.candidate_id == candidate_id, ResumeModel.is_active == True).order_by(ResumeModel.created_at.desc())
        res = await self.session.execute(stmt)
        return res.scalars().first()

    async def set_active_resume(self, candidate_id: str, resume_id: str) -> Optional[ResumeModel]:
        # Deactivate all candidate resumes
        await self.session.execute(
            update(ResumeModel).where(ResumeModel.candidate_id == candidate_id).values(is_active=False)
        )
        # Activate targeted resume
        target = await self.get(resume_id)
        if target:
            target.is_active = True
            await self.session.flush()
        return target

    async def save_chunks(self, chunks_data: List[Dict[str, Any]]) -> int:
        count = 0
        for chunk in chunks_data:
            chunk_orm = ResumeChunkModel(
                resume_id=chunk["resume_id"],
                candidate_id=chunk["candidate_id"],
                section_name=chunk["section_name"],
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                embedding=chunk["embedding"],
                chunk_metadata=chunk.get("chunk_metadata", {})
            )
            self.session.add(chunk_orm)
            count += 1
        await self.session.flush()
        return count

    async def vector_search(self, candidate_id: UUID, query_vector: List[float], top_k: int = 3, section_filter: Optional[str] = None) -> List[ResumeChunkModel]:
        stmt = select(ResumeChunkModel).where(ResumeChunkModel.candidate_id == str(candidate_id))
        if section_filter:
            stmt = stmt.where(ResumeChunkModel.section_name.ilike(f"%{section_filter}%"))

        try:
            pg_stmt = stmt.order_by(ResumeChunkModel.embedding.cosine_distance(query_vector)).limit(top_k)
            res = await self.session.execute(pg_stmt)
            return list(res.scalars().all())
        except Exception:
            # In SQLite / non-pgvector environments, fetch and compute cosine similarity in Python
            res = await self.session.execute(stmt)
            chunks = list(res.scalars().all())

            def cosine_sim(v1, v2):
                if not v1 or not v2 or len(v1) != len(v2):
                    return 0.0
                dot = sum(a * b for a, b in zip(v1, v2))
                norm1 = sum(a * a for a in v1) ** 0.5
                norm2 = sum(b * b for b in v2) ** 0.5
                return dot / (norm1 * norm2) if (norm1 * norm2) > 0 else 0.0

            chunks.sort(
                key=lambda c: cosine_sim(c.embedding if isinstance(c.embedding, list) else [], query_vector),
                reverse=True,
            )
            return chunks[:top_k]
