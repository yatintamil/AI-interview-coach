"""
Pydantic v2 schemas for RAG queries and candidate resume vector retrieval.
"""

from uuid import UUID
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class RAGQueryRequest(BaseModel):
    query: str = Field(..., description="Query text for vector similarity search")
    top_k: int = Field(default=3, ge=1, le=20, description="Number of context chunks to retrieve")
    section_filter: Optional[str] = Field(default=None, description="Optional section filter (e.g. Experience, Projects)")

class RAGChunkSearchResult(BaseModel):
    chunk_id: UUID
    resume_id: UUID
    candidate_id: UUID
    section_name: str
    content: str
    similarity_score: float = Field(..., description="Cosine similarity score (0.0 to 1.0)")
    chunk_metadata: Dict[str, Any] = Field(default_factory=dict)

class RAGQueryResponse(BaseModel):
    query: str
    total_results: int
    results: List[RAGChunkSearchResult]
