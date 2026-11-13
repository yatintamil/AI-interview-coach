"""
Thin FastAPI Router for Resume Intelligence Engine endpoints.
Adheres to fastapi.md standards (thin router, proper status codes, Pydantic response models).
"""

import uuid
from typing import Optional
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.dependencies.database import get_db_session
from backend.core.security import require_authenticated_candidate_id, verify_candidate_access
from backend.services.resume_service import ResumeService
from backend.services.rag_service import CandidateRAGService
from backend.schemas.resume import ResumeParseResponse
from backend.schemas.candidate_profile import CandidateProfile
from backend.schemas.rag import RAGQueryRequest, RAGQueryResponse
from backend.repositories.candidate_repository import CandidateRepository
from backend.core.exceptions import ResumeParsingError

router = APIRouter(prefix="/resumes", tags=["Resume Intelligence Engine"])

@router.post(
    "/parse",
    response_model=ResumeParseResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload and Parse Candidate Resume",
    description="Upload a candidate resume (PDF, DOCX, TXT). Automatically generates a Candidate UUID, extracts profile entities, normalizes data, and indexes RAG vectors."
)
async def parse_resume(
    file: UploadFile = File(..., description="Resume document (PDF, DOCX, TXT)"),
    session: AsyncSession = Depends(get_db_session)
):
    # Automatically generate a unique candidate_id UUID
    cand_uuid = uuid.uuid4()

    content = await file.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    service = ResumeService(session)
    try:
        resume_record, profile, chunks_count = await service.process_resume(
            candidate_id=cand_uuid,
            file_name=file.filename or "resume.pdf",
            file_bytes=content
        )
    except ResumeParsingError as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(e))
    except Exception as e:
        import traceback
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}")

    return ResumeParseResponse(
        candidate_id=cand_uuid,
        resume_id=resume_record.id,
        status=resume_record.processing_status,
        profile=profile,
        indexed_rag_chunks=chunks_count,
        created_at=resume_record.created_at
    )

@router.get(
    "/candidates/{candidate_id}/profile",
    response_model=Optional[CandidateProfile],
    summary="Get Extracted Candidate Profile",
    description="Retrieves the structured candidate profile object. Returns null if candidate has no uploaded resume yet."
)
async def get_candidate_profile(
    candidate_id: str,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session)
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    try:
        cand_uuid = uuid.UUID(candidate_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid candidate_id UUID format.")

    repo = CandidateRepository(session)
    cand = await repo.get(str(cand_uuid))
    if not cand:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found.")

    profile_model = await repo.get_profile(cand_uuid)
    if not profile_model or not profile_model.profile_data:
        return None

    return CandidateProfile.model_validate(profile_model.profile_data)

@router.post(
    "/candidates/{candidate_id}/rag/query",
    response_model=RAGQueryResponse,
    summary="Query Candidate Resume Memory (RAG)",
    description="Retrieves top-k relevant vector context chunks from indexed candidate resume."
)
async def query_candidate_rag(
    candidate_id: str,
    payload: RAGQueryRequest,
    authenticated_candidate_id: str = Depends(require_authenticated_candidate_id),
    session: AsyncSession = Depends(get_db_session)
):
    verify_candidate_access(candidate_id, authenticated_candidate_id)
    try:
        cand_uuid = uuid.UUID(candidate_id)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid candidate_id UUID format.")

    rag_service = CandidateRAGService(session)
    response = await rag_service.query_candidate_memory(
        candidate_id=cand_uuid,
        query=payload.query,
        top_k=payload.top_k,
        section_filter=payload.section_filter
    )
    return response
