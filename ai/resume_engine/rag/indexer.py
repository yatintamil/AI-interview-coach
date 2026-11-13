"""
Resume Vector Store Indexer.
Combines Chunker and Embedder to produce fully embedded chunk payloads ready for pgvector insertion.
"""

from typing import List, Dict, Any, Optional
from ai.resume_engine.rag.chunker import ResumeSectionChunker
from ai.resume_engine.rag.embedder import VectorEmbedder

class ResumeVectorIndexer:
    """
    Orchestrates section chunking and embedding generation for resume ingestion.
    """

    def __init__(self, embedder: Optional[VectorEmbedder] = None):
        self.chunker = ResumeSectionChunker()
        self.embedder = embedder or VectorEmbedder()

    def process_and_index(self, resume_text: str, candidate_id: str, resume_id: str) -> List[Dict[str, Any]]:
        chunks = self.chunker.chunk_text(resume_text, candidate_id, resume_id)
        
        indexed_chunks: List[Dict[str, Any]] = []
        for chunk in chunks:
            vector = self.embedder.generate_embedding(chunk["content"])
            chunk["embedding"] = vector
            indexed_chunks.append(chunk)

        return indexed_chunks
