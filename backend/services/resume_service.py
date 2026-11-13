"""
High-Level Resume Ingestion & Extraction Orchestration Service.
Contains business logic & workflow orchestration as per fastapi.md guidelines.
"""

import hashlib
import uuid
from typing import Tuple
from pathlib import Path
# pyrefly: ignore [missing-import]
from sqlalchemy.ext.asyncio import AsyncSession

from ai.resume_engine.parsers.pdf_parser import PDFDocumentParser
from ai.resume_engine.parsers.docx_parser import DOCXDocumentParser
from ai.resume_engine.parsers.text_parser import TextDocumentParser
from ai.resume_engine.extractors.llm_extractor import LLMExtractor
from ai.resume_engine.normalizer import CandidateProfileNormalizer
from ai.resume_engine.rag.indexer import ResumeVectorIndexer

from backend.schemas.candidate_profile import CandidateProfile
from backend.repositories.candidate_repository import CandidateRepository
from backend.repositories.resume_repository import ResumeRepository
from backend.models.resume import ResumeModel
from backend.core.exceptions import ResumeParsingError

class ResumeService:
    """
    Orchestrates: Ingestion -> Parsing -> LLM Extraction -> Normalization -> RAG Indexing -> DB Persistence.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.candidate_repo = CandidateRepository(session)
        self.resume_repo = ResumeRepository(session)
        self.extractor = LLMExtractor()
        self.normalizer = CandidateProfileNormalizer()
        self.indexer = ResumeVectorIndexer()

    async def process_resume(self, candidate_id: uuid.UUID, file_name: str, file_bytes: bytes) -> Tuple[ResumeModel, CandidateProfile, int]:
        if not file_bytes:
            raise ResumeParsingError("Empty file uploaded.")

        checksum = hashlib.sha256(file_bytes).hexdigest()
        file_ext = Path(file_name).suffix.lower().replace(".", "")

        # 1. Select Document Parser
        if file_ext == "pdf":
            parser = PDFDocumentParser()
        elif file_ext in ["docx", "doc"]:
            parser = DOCXDocumentParser()
        elif file_ext in ["txt", "md"]:
            parser = TextDocumentParser()
        else:
            parser = TextDocumentParser()

        # 2. Extract Plain Text
        try:
            raw_text = parser.parse(file_bytes)
        except Exception as e:
            raise ResumeParsingError(f"Failed to parse document: {str(e)}")

        if not raw_text or not raw_text.strip():
            raise ResumeParsingError(
                f"Failed to extract readable text from '{file_name}'. Please ensure the file is not an empty or scanned image document."
            )

        # 3. Create Resume Record in DB
        # Auto-create the Candidate row if it doesn't exist (FK requirement)
        # pyrefly: ignore [missing-import]
        from sqlalchemy.future import select
        from backend.models.candidate import CandidateModel
        existing_candidate_result = await self.session.execute(
            select(CandidateModel).where(CandidateModel.id == str(candidate_id))
        )
        existing_candidate = existing_candidate_result.scalars().first()
        if not existing_candidate:
            auto_candidate = CandidateModel(
                id=str(candidate_id),
                email=f"auto-{candidate_id}@resume.upload",
                full_name="Candidate (auto-created)",
            )
            self.session.add(auto_candidate)
            await self.session.flush()

        resume_record = ResumeModel(
            id=str(uuid.uuid4()),
            candidate_id=str(candidate_id),
            file_name=file_name,
            file_path=f"storage/resumes/{candidate_id}/{file_name}",
            file_type=file_ext,
            file_size_bytes=len(file_bytes),
            checksum=checksum,
            raw_text=raw_text,
            processing_status="PROCESSING"
        )
        await self.resume_repo.create(resume_record)

        # 4. Perform LLM Extraction (with fallback chain)
        raw_profile = self.extractor.extract(raw_text)
        raw_profile.raw_text_hash = checksum

        # 5. Normalize Candidate Profile
        normalized_profile = self.normalizer.normalize(raw_profile)

        # 6. Save Profile in Repository
        await self.candidate_repo.save_profile(candidate_id, resume_record.id, normalized_profile)

        # 7. Process & Index Vector Chunks for RAG
        indexed_chunks = self.indexer.process_and_index(
            resume_text=raw_text,
            candidate_id=str(candidate_id),
            resume_id=str(resume_record.id)
        )
        chunks_count = await self.resume_repo.save_chunks(indexed_chunks)

        # 8. Decompose Verifiable Atomic Claims for Candidate Evidence Graph
        try:
            from ai.resume_engine.claim_decomposer import ResumeClaimDecomposer
            from backend.repositories.claim_repository import ClaimRepository
            from backend.models.resume_claim import CandidateClaimModel

            decomposer = ResumeClaimDecomposer()
            claim_repo = ClaimRepository(self.session)

            # Clear any previous claims for this candidate to maintain consistency
            raw_claims = await decomposer.decompose_claims(
                resume_text=raw_text,
                profile_dict=normalized_profile.model_dump() if hasattr(normalized_profile, "model_dump") else None
            )

            claim_models = [
                CandidateClaimModel(
                    id=str(uuid.uuid4()),
                    candidate_id=str(candidate_id),
                    resume_id=str(resume_record.id),
                    skill_name=c["skill_name"],
                    claim_text=c["claim_text"],
                    complexity=c.get("complexity", "INTERMEDIATE"),
                    verification_status=c.get("verification_status", "UNVERIFIED"),
                    confidence_score=float(c.get("confidence_score", 0.5)),
                    verified_quotes=c.get("verified_quotes", []),
                    probe_count=0,
                )
                for c in raw_claims
            ]
            await claim_repo.create_batch(claim_models)
        except Exception as e:
            # Non-blocking claim generation fallback
            print(f"Warning: claim decomposition exception: {e}")

        # 9. Mark Complete
        resume_record.processing_status = "COMPLETED"
        await self.session.flush()

        return resume_record, normalized_profile, chunks_count
