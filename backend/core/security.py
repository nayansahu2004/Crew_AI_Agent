# File path: backend/core/security.py
"""
Supabase JWT verification.

Supports both ways a Supabase project can sign access tokens:

  * Asymmetric keys (ES256 / RS256) -- the default for newer projects.
    Verified against the project's public keys (JWKS), fetched from
    <SUPABASE_URL>/auth/v1/.well-known/jwks.json and cached by PyJWT.
    No secret is needed in .env for this.

  * Legacy shared secret (HS256) -- older projects. Verified with
    SUPABASE_JWT_SECRET. If a token is HS256-signed and that variable
    isn't set, the server logs a clear error.

The token's own `alg` header is only used to pick which branch runs. Each
branch then pins an explicit allow-list of algorithms, so a forged token
can't downgrade verification (e.g. to "none").

Requires: pip install "pyjwt[crypto]"   (the [crypto] extra is what makes
ES256/RS256 verification work.)
"""

import logging

import jwt
from fastapi import Header, HTTPException, status, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient
from pydantic import BaseModel
from starlette.concurrency import run_in_threadpool

from backend.core.config import settings


logger = logging.getLogger(__name__)

_JWKS_URL = f"{settings.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
# Doesn't touch the network until the first asymmetric token is verified;
# fetched keys are cached afterwards.
_jwks_client = PyJWKClient(_JWKS_URL, cache_keys=True)
bearer_scheme = HTTPBearer(auto_error=False)


class AuthenticatedUser(BaseModel):
    """What every protected route gets after successful auth.
    supabase_user_id is the ONLY trustworthy source of user identity --
    never accept a user_id from request bodies/query params instead."""
    supabase_user_id: str
    email: str | None = None


def _extract_bearer_token(authorization: str | None) -> str:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header.",
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header must be in the form: Bearer <token>",
        )

    return parts[1]


def _decode_token(token: str) -> dict:
    """Blocking (may fetch the JWKS over the network on a cache miss), so
    the caller runs it in a thread pool."""
    alg = jwt.get_unverified_header(token).get("alg")

    if alg == "HS256":
        if not settings.supabase_jwt_secret:
            logger.error(
                "Received an HS256-signed token but SUPABASE_JWT_SECRET is "
                "not set. Add it to .env (Supabase dashboard -> Project "
                "Settings -> JWT Keys -> Legacy JWT Secret)."
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authentication is not configured correctly on the server.",
            )
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",  # Supabase's default audience claim
        )

    signing_key = _jwks_client.get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256", "RS256"],
        audience="authenticated",
    )

async def get_current_user(
    authorization: str | None = Header(default=None, include_in_schema=False),
    _: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
) -> AuthenticatedUser:
    """
    FastAPI dependency for protected routes:

        @router.get("/api/campaigns")
        async def list_campaigns(user: AuthenticatedUser = Depends(get_current_user)):
            ...

    Raises 401 for any missing, malformed, expired, or invalid token, so
    routes never need to handle that themselves.
    """
    token = _extract_bearer_token(authorization)

    try:
        payload = await run_in_threadpool(_decode_token, token)
    except HTTPException:
        raise
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired.",
        )
    except jwt.PyJWTError as exc:
        # Covers bad signatures, wrong audience, malformed tokens, and
        # failures fetching/finding the signing key. The detail is logged
        # server-side only; the client just gets a generic message.
        logger.warning("JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        )

    supabase_user_id = payload.get("sub")
    if not supabase_user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing subject claim.",
        )

    return AuthenticatedUser(
        supabase_user_id=supabase_user_id,
        email=payload.get("email"),
    )