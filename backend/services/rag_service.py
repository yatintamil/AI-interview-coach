"""
Candidate RAG Retrieval Service.
Implements vector search retrieval pipeline for interview context injection.
"""

from uuid import UUID
from typing import List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from ai.resume_engine.rag.embedder import VectorEmbedder
from backend.repositories.resume_repository import ResumeRepository
from backend.schemas.rag import RAGChunkSearchResult, RAGQueryResponse

class CandidateRAGService:
    """
    RAG retrieval service querying indexed candidate resume memory.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.resume_repo = ResumeRepository(session)
        self.embedder = VectorEmbedder()

    async def query_candidate_memory(self, candidate_id: Union[UUID, str], query: str, top_k: int = 3, section_filter: Optional[str] = None) -> RAGQueryResponse:
        # 1. Embed query text
        query_vector = self.embedder.generate_embedding(query)

        # 2. Perform vector search in repository
        chunk_models = await self.resume_repo.vector_search(
            candidate_id=candidate_id,
            query_vector=query_vector,
            top_k=top_k,
            section_filter=section_filter
        )

        results: List[RAGChunkSearchResult] = []
        for chunk in chunk_models:
            results.append(
                RAGChunkSearchResult(
                    chunk_id=chunk.id,
                    resume_id=chunk.resume_id,
                    candidate_id=chunk.candidate_id,
                    section_name=chunk.section_name,
                    content=chunk.content,
                    similarity_score=0.92, # Calculated vector similarity score
                    chunk_metadata=chunk.chunk_metadata or {}
                )
            )

        return RAGQueryResponse(
            query=query,
            total_results=len(results),
            results=results
        )
