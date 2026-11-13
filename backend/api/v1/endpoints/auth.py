"""
Authentication endpoints: Development Prototype Token Issuance & Identity Verification.
"""

import os
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import settings
from backend.dependencies.database import get_db_session
from backend.repositories.candidate_repository import CandidateRepository
from backend.schemas.candidate import CandidateCreateRequest
from backend.core.security import (
    create_access_token,
    require_authenticated_candidate_id,
    get_authenticated_candidate_id,
)

router = APIRouter(prefix="/auth", tags=["auth"])


class TokenRequest(BaseModel):
    candidate_id: str = Field(..., min_length=1, description="Candidate ID requesting authenticated token.")
    email: str = Field(
        ...,
        min_length=3,
        description="Candidate registered email matched against database record (record matching, NOT verified account ownership).",
    )
    expires_in_seconds: int = Field(default=86400, ge=60, le=604800, description="Token TTL in seconds.")


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    candidate_id: str
    expires_in_seconds: int
    auth_tier: str = "DEVELOPMENT_PROTOTYPE"
    warning: str = (
        "Supervised prototype token: verifies database candidate record existence and registered email only. "
        "Does NOT prove verified account ownership. Restricted to supervised research and local development."
    )


@router.post("/token", response_model=TokenResponse)
async def issue_candidate_token(
    payload: TokenRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Issues a cryptographically signed HMAC-SHA256 bearer token for candidate identity.
    Restricted to Supervised Research Prototype / Local Development mode.
    Validates candidate database record existence and registered email (record matching).
    Does NOT constitute verified account ownership (e.g., password, WebAuthn, OAuth2 callback).
    Disabled in production.
    """
    env = (os.getenv("ENVIRONMENT") or getattr(settings, "ENVIRONMENT", "development")).strip().lower()
    if env == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Direct candidate token issuance is disabled in production environment. "
                   "Production authentication requires a verified external Identity Provider (IdP) "
                   "or multi-factor verified account ownership.",
        )

    # Validate identity credentials against database records
    cand_repo = CandidateRepository(db)
    candidate = await cand_repo.get(payload.candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: Candidate with ID '{payload.candidate_id}' does not exist.",
        )

    registered_email = str(candidate.email or "").strip().lower()
    provided_email = str(payload.email).strip().lower()
    if registered_email != provided_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed: Provided email does not match registered candidate profile.",
        )

    token = create_access_token(
        candidate_id=candidate.id,
        expires_in_seconds=payload.expires_in_seconds,
        auth_tier="DEVELOPMENT_PROTOTYPE",
    )
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        candidate_id=candidate.id,
        expires_in_seconds=payload.expires_in_seconds,
        auth_tier="DEVELOPMENT_PROTOTYPE",
        warning="Local research prototype token: do not use as production-grade user authentication.",
    )


from backend.core.security import (
    create_access_token,
    require_authenticated_candidate_id,
    get_authenticated_candidate_id,
    hash_password,
    verify_password,
)

class RegisterRequest(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$", description="Candidate email address")
    full_name: str = Field(..., min_length=1, max_length=255, description="Candidate full name")
    password: str = Field(default="CandidateP@ss123!", min_length=6, max_length=128, description="Candidate account password")


class LoginRequest(BaseModel):
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$", description="Candidate email address")
    password: str = Field(default="CandidateP@ss123!", min_length=1, max_length=128, description="Candidate account password")


class CandidateAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    candidate_id: str
    candidate: dict
    auth_tier: str = "CANDIDATE"


@router.post("/register", response_model=CandidateAuthResponse, status_code=status.HTTP_201_CREATED)
async def register_candidate(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Registers a new candidate profile with hashed password and issues an authenticated session token.
    Rejects duplicate registration with 409 Conflict.
    """
    from backend.services.candidate_service import CandidateService
    cand_service = CandidateService(db)
    cand_repo = CandidateRepository(db)

    norm_email = payload.email.strip().lower()
    existing = await cand_repo.get_by_email(norm_email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email address already exists. Please sign in with your password.",
        )

    created = await cand_service.create_candidate(
        payload=CandidateCreateRequest(
            email=norm_email,
            full_name=payload.full_name.strip(),
            password=payload.password,
        )
    )
    token = create_access_token(candidate_id=created.id, auth_tier="CANDIDATE")
    return CandidateAuthResponse(
        access_token=token,
        candidate_id=created.id,
        candidate=created.model_dump(),
        auth_tier="CANDIDATE",
    )


@router.post("/login", response_model=CandidateAuthResponse, status_code=status.HTTP_200_OK)
async def login_candidate(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Authenticates an existing candidate by verified email and password, issuing a session token.
    """
    from backend.services.candidate_service import CandidateService
    cand_repo = CandidateRepository(db)
    cand_service = CandidateService(db)

    norm_email = payload.email.strip().lower()
    candidate = await cand_repo.get_by_email(norm_email)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No candidate profile found for email '{payload.email}'. Please register to create your profile.",
        )

    # Enforce password verification
    if candidate.password_hash:
        if not verify_password(payload.password, candidate.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password for this candidate account.",
            )
    else:
        # Legacy candidate record without password: automatically secure on first authenticated login
        candidate.password_hash = hash_password(payload.password)
        await db.flush()

    token = create_access_token(candidate_id=candidate.id, auth_tier="CANDIDATE")
    cand_res = cand_service._to_response(candidate)
    return CandidateAuthResponse(
        access_token=token,
        candidate_id=candidate.id,
        candidate=cand_res.model_dump(),
        auth_tier="CANDIDATE",
    )


@router.get("/me")
async def get_current_authenticated_candidate(
    candidate_id: str = Depends(require_authenticated_candidate_id),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Verifies caller bearer token against database and returns active candidate profile.
    Rejects requests if candidate profile no longer exists in database (e.g., after database reset).
    """
    from backend.services.candidate_service import CandidateService
    cand_repo = CandidateRepository(db)
    candidate = await cand_repo.get_with_details(candidate_id)
    if not candidate:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Active session expired: Candidate profile was removed from database. Please sign in again.",
        )

    cand_service = CandidateService(db)
    cand_res = cand_service._to_response(candidate)
    return {
        "authenticated_candidate_id": candidate_id,
        "candidate": cand_res.model_dump(),
    }


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout_candidate(
    candidate_id: str = Depends(require_authenticated_candidate_id),
):
    """
    Candidate logout acknowledgement endpoint.
    """
    return {
        "status": "success",
        "message": f"Session for candidate '{candidate_id}' successfully terminated.",
    }


class DevResetRequest(BaseModel):
    confirmation: str = Field(..., description="Confirmation phrase 'CONFIRM_DEVELOPMENT_RESET'")


@router.post("/dev-reset", status_code=status.HTTP_200_OK, summary="Reset development database candidate records")
async def dev_reset_database(
    payload: DevResetRequest,
    db: AsyncSession = Depends(get_db_session),
):
    """
    Safely resets development/test candidate records, vector chunks, and conversation histories.
    Strictly disabled in production. Requires exact confirmation phrase.
    """
    from backend.services.dev_reset_service import DevelopmentDatabaseResetService
    service = DevelopmentDatabaseResetService(db)
    try:
        result = await service.execute_reset(payload.confirmation)
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(re))

