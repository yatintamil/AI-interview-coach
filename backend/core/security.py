"""
Security utilities, cryptographic token management, and authentication boundaries.
Eliminates untrusted caller-controlled header vulnerabilities.
"""

import os
import json
import hmac
import hashlib
import secrets
import base64
import time
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, status

from backend.core.config import settings

INSECURE_SECRETS = {
    "super-secret-key-change-in-production",
    "dev-secret-key-ai-interview-coach",
    "interview-coach-hmac-sha256-canonical-secret-2026",
    "insecure-dev-secret-change-in-production",
}


def hash_password(password: str) -> str:
    """
    Hashes a password using PBKDF2 with HMAC-SHA256, 100,000 iterations, and a 16-byte random salt.
    Format: pbkdf2_sha256$<salt_hex>$<hash_hex>
    """
    if not password or not isinstance(password, str):
        raise ValueError("Password must be a non-empty string.")
    salt = secrets.token_hex(16)
    pw_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100_000,
    ).hex()
    return f"pbkdf2_sha256${salt}${pw_hash}"


def verify_password(password: str, hashed_password: Optional[str]) -> bool:
    """
    Verifies a plaintext password against a stored PBKDF2-SHA256 password hash.
    Uses timing-resistant comparison to prevent side-channel timing attacks.
    """
    if not password or not hashed_password or not isinstance(hashed_password, str):
        return False
    try:
        parts = hashed_password.split("$")
        if len(parts) != 3 or parts[0] != "pbkdf2_sha256":
            return False
        salt = parts[1]
        expected_hash = parts[2]
        computed_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100_000,
        ).hex()
        return secrets.compare_digest(computed_hash, expected_hash)
    except Exception:
        return False



def get_signing_secret() -> bytes:
    """
    Retrieves HMAC signing secret with strict fail-closed enforcement for production.
    Raises RuntimeError if insecure default secrets or weak keys (<32 chars) are used in production.
    """
    env = (os.getenv("ENVIRONMENT") or getattr(settings, "ENVIRONMENT", "development")).strip().lower()
    secret = (
        os.getenv("AUTH_SECRET_KEY")
        or getattr(settings, "AUTH_SECRET_KEY", None)
        or os.getenv("SECRET_KEY")
        or getattr(settings, "SECRET_KEY", None)
    )

    if env == "production":
        if not secret or str(secret).strip() in INSECURE_SECRETS or len(str(secret).strip()) < 32:
            raise RuntimeError(
                "Production Configuration Security Error: Insecure or missing AUTH_SECRET_KEY/SECRET_KEY in production. "
                "Production deployment must configure a high-entropy secret key (at least 32 characters)."
            )

    if not secret:
        secret = "interview-coach-hmac-sha256-canonical-secret-2026"
    return str(secret).encode("utf-8")


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64url_decode(data: str) -> bytes:
    padding = 4 - (len(data) % 4)
    if padding != 4:
        data += "=" * padding
    return base64.urlsafe_b64decode(data.encode("utf-8"))


def create_access_token(
    candidate_id: str,
    expires_in_seconds: int = 86400,
    auth_tier: str = "DEVELOPMENT_PROTOTYPE",
) -> str:
    """
    Issues a cryptographically signed HMAC-SHA256 authentication token for candidate principal.
    Token structure: <b64_payload>.<b64_signature>
    """
    now = int(time.time())
    payload: Dict[str, Any] = {
        "sub": candidate_id,
        "iat": now,
        "exp": now + expires_in_seconds,
        "auth_tier": auth_tier,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    payload_b64 = _b64url_encode(payload_bytes)

    secret = get_signing_secret()
    sig = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)

    return f"{payload_b64}.{sig_b64}"


def get_access_token_payload(token: str) -> Optional[Dict[str, Any]]:
    """
    Verifies token HMAC-SHA256 signature and expiration timestamp.
    Returns decoded payload dictionary if valid; None if forged, tampered, or expired.
    """
    if not token or "." not in token:
        return None

    parts = token.split(".")
    if len(parts) != 2:
        return None

    payload_b64, sig_b64 = parts[0], parts[1]

    secret = get_signing_secret()
    expected_sig = hmac.new(secret, payload_b64.encode("utf-8"), hashlib.sha256).digest()
    expected_sig_b64 = _b64url_encode(expected_sig)

    if not hmac.compare_digest(sig_b64, expected_sig_b64):
        return None

    try:
        payload_bytes = _b64url_decode(payload_b64)
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return None

    # Check expiration
    exp = payload.get("exp")
    if exp is not None and int(exp) < int(time.time()):
        return None

    return payload


def verify_access_token(token: str) -> Optional[str]:
    """
    Verifies token HMAC-SHA256 signature and expiration timestamp.
    Returns authenticated candidate_id if valid; None if forged, tampered, or expired.
    """
    payload = get_access_token_payload(token)
    return payload.get("sub") if payload else None


def get_current_user_id() -> str:
    """
    Returns default candidate ID for internal mock fallback contexts.
    """
    return "f47ac10b-58cc-4372-a567-0e02b2c3d479"


def get_authenticated_candidate_id(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
    x_candidate_id: Optional[str] = Header(None, alias="X-Candidate-ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> Optional[str]:
    """
    Extracts and validates candidate identity against a trusted cryptographic boundary.
    Rejects caller-controlled headers (X-Candidate-ID / X-User-ID) if presented without
    or conflicting with a valid cryptographically signed authentication token.
    """
    raw_token = None
    if isinstance(authorization, str) and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
    elif isinstance(x_auth_token, str) and x_auth_token.strip():
        raw_token = x_auth_token.strip()

    # 1. If token is provided, it MUST be valid
    if raw_token:
        candidate_id = verify_access_token(raw_token)
        if not candidate_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication credentials.",
            )
        # Check for spoofed caller-supplied header mismatch
        caller_id = x_candidate_id if isinstance(x_candidate_id, str) else (x_user_id if isinstance(x_user_id, str) else None)
        if caller_id and str(caller_id) != str(candidate_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Caller supplied candidate ID '{caller_id}' does not match authenticated token principal '{candidate_id}'.",
            )
        return candidate_id

    # 2. If caller attempts to assert identity via raw X-Candidate-ID / X-User-ID without token,
    # reject as unverified / untrusted caller-controlled identity!
    caller_id = x_candidate_id if isinstance(x_candidate_id, str) else (x_user_id if isinstance(x_user_id, str) else None)
    if caller_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Raw caller-controlled identity headers are not trusted without a valid signed authentication token.",
        )

    # 3. No token and no candidate headers: unauthenticated / public dev mode
    return None


def require_authenticated_candidate_id(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
    x_candidate_id: Optional[str] = Header(None, alias="X-Candidate-ID"),
    x_user_id: Optional[str] = Header(None, alias="X-User-ID"),
) -> str:
    """
    Strict dependency: strictly requires a valid signed token.
    """
    principal = get_authenticated_candidate_id(
        authorization=authorization,
        x_auth_token=x_auth_token,
        x_candidate_id=x_candidate_id,
        x_user_id=x_user_id,
    )
    if not principal:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Missing or invalid authentication token.",
        )
    return principal


def verify_candidate_access(
    target_candidate_id: Optional[str],
    authenticated_candidate_id: Optional[str],
) -> None:
    """
    Enforces candidate isolation across tenant boundaries:
    If authenticated_candidate_id is present, strictly verifies that target_candidate_id matches.
    If they differ, raises HTTP 403 Forbidden.
    """
    if authenticated_candidate_id and target_candidate_id:
        if str(target_candidate_id).strip() != str(authenticated_candidate_id).strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: Target candidate '{target_candidate_id}' does not match authenticated principal '{authenticated_candidate_id}'.",
            )


def require_researcher_auth(
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
    x_researcher_key: Optional[str] = Header(None, alias="X-Researcher-Key"),
    x_admin_key: Optional[str] = Header(None, alias="X-Admin-Key"),
) -> Dict[str, Any]:
    """
    Strict dependency for research-only exports and administrative retention queues.
    Requires either:
    1. A signed bearer token with auth_tier in ('RESEARCHER', 'ADMIN').
    2. A valid researcher key header (X-Researcher-Key or X-Admin-Key).
    Candidate/participant tokens (auth_tier in ('DEVELOPMENT_PROTOTYPE', 'CANDIDATE')) are strictly forbidden.
    In production environments, unauthenticated access is rejected with 401.
    """
    raw_token = None
    if isinstance(authorization, str) and authorization.lower().startswith("bearer "):
        raw_token = authorization[7:].strip()
    elif isinstance(x_auth_token, str) and x_auth_token.strip():
        raw_token = x_auth_token.strip()

    # 1. If token is provided, verify signature and check role/tier
    if raw_token:
        payload = get_access_token_payload(raw_token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication credentials.",
            )
        auth_tier = str(payload.get("auth_tier", "")).upper()
        if auth_tier in ("RESEARCHER", "ADMIN"):
            return payload

        # Participant tokens cannot access research-only administrative endpoints
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access denied: Research administrative authorization required. "
                f"Candidate token tier '{auth_tier}' does not possess researcher privileges."
            ),
        )

    # 2. Check researcher / admin API key header
    provided_key = x_researcher_key or x_admin_key
    configured_key = (
        os.getenv("RESEARCHER_API_KEY")
        or getattr(settings, "RESEARCHER_API_KEY", None)
        or "researcher-pilot-canonical-key-2026"
    )
    if provided_key:
        if hmac.compare_digest(str(provided_key).strip(), str(configured_key).strip()):
            return {"sub": "researcher_key_holder", "auth_tier": "RESEARCHER"}
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid researcher administrative key.",
        )

    # 3. No token and no key: check environment
    env = (os.getenv("ENVIRONMENT") or getattr(settings, "ENVIRONMENT", "development")).strip().lower()
    if env == "production":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Researcher authentication required: Missing researcher credentials in production environment.",
        )

    # In local development prototype testing without credentials, allow fallback researcher context
    return {"sub": "dev_local_researcher", "auth_tier": "RESEARCHER"}
