# File path: backend/services/google_client.py
"""
Thin client for the Google endpoints we use: the OAuth token exchange and
the Gmail API. No database access and no business rules live here -- just
HTTP calls and a uniform error type (GoogleApiError) so callers can react
to "the token was revoked" vs "Google is down" without parsing responses.

Tests swap `_transport` for an httpx.MockTransport, so the test suite never
makes a real network call.
"""

import logging
from urllib.parse import urlencode

import httpx
import jwt

from backend.core.config import settings

logger = logging.getLogger(__name__)

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"

# gmail.compose covers creating drafts AND sending (drafts or messages).
# Note: Google classes it as a RESTRICTED scope -- see the README before
# opening the app up to the public. openid+email let us learn which Google
# account was connected.
COMPOSE_SCOPE = "https://www.googleapis.com/auth/gmail.compose"
SCOPES = ["openid", "email", COMPOSE_SCOPE]

# Set by tests to an httpx.MockTransport.
_transport: httpx.AsyncBaseTransport | None = None


class GoogleApiError(Exception):
    """kind is one of: invalid_grant, unauthorized, forbidden, not_found,
    rate_limited, unavailable, bad_request, unknown."""

    def __init__(self, kind: str, message: str = "", status: int | None = None):
        super().__init__(f"{kind}: {message}" if message else kind)
        self.kind = kind
        self.status = status


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=_transport, timeout=httpx.Timeout(15.0))


def _classify(response: httpx.Response) -> GoogleApiError:
    status = response.status_code
    try:
        body = response.json()
    except ValueError:
        body = {}

    error = body.get("error")
    code = error if isinstance(error, str) else ""
    detail = body.get("error_description") or ""
    reasons = ""
    if isinstance(error, dict):
        detail = error.get("message", "")
        reasons = " ".join(str(e.get("reason", "")) for e in error.get("errors", []) if isinstance(e, dict))

    if code == "invalid_grant":
        return GoogleApiError("invalid_grant", detail, status)
    if status == 401:
        return GoogleApiError("unauthorized", detail, status)
    if status == 429 or "ratelimit" in reasons.lower() or "limitexceeded" in reasons.lower():
        return GoogleApiError("rate_limited", detail, status)
    if status == 403:
        return GoogleApiError("forbidden", detail, status)
    if status == 404:
        return GoogleApiError("not_found", detail, status)
    if status >= 500:
        return GoogleApiError("unavailable", detail, status)
    if status == 400:
        return GoogleApiError("bad_request", detail, status)
    return GoogleApiError("unknown", detail, status)


async def _post(url: str, **kwargs) -> dict:
    try:
        async with _client() as client:
            response = await client.post(url, **kwargs)
    except httpx.HTTPError as exc:
        raise GoogleApiError("unavailable", str(exc)) from exc
    if response.status_code >= 400:
        raise _classify(response)
    return response.json() if response.content else {}


# --- OAuth -------------------------------------------------------------------

def build_auth_url(state: str) -> str:
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": settings.google_redirect_uri,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        # offline + consent => Google returns a long-lived refresh token.
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code(code: str) -> dict:
    return await _post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": settings.google_redirect_uri,
            "grant_type": "authorization_code",
        },
    )


async def refresh_access_token(refresh_token: str) -> str:
    tokens = await _post(
        GOOGLE_TOKEN_URL,
        data={
            "refresh_token": refresh_token,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "grant_type": "refresh_token",
        },
    )
    return tokens["access_token"]


async def revoke_token(token: str) -> None:
    """Best effort: failing to revoke must never block disconnecting."""
    try:
        await _post(GOOGLE_REVOKE_URL, data={"token": token})
    except GoogleApiError as exc:
        logger.warning("Could not revoke Google token (%s).", exc.kind)


def email_from_id_token(id_token: str | None) -> str | None:
    """Read the account's address from the id_token. It arrived directly
    from Google over TLS in the code exchange, so per the OpenID Connect
    spec the signature doesn't need re-checking."""
    if not id_token:
        return None
    try:
        claims = jwt.decode(id_token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return None
    if not claims.get("email") or claims.get("email_verified") is False:
        return None
    return str(claims["email"])


# --- Gmail API ---------------------------------------------------------------

def _auth(access_token: str) -> dict:
    return {"Authorization": f"Bearer {access_token}"}


async def create_draft(access_token: str, raw_message: str) -> dict:
    return await _post(
        f"{GMAIL_API}/drafts",
        headers=_auth(access_token),
        json={"message": {"raw": raw_message}},
    )


async def send_message(access_token: str, raw_message: str) -> dict:
    return await _post(
        f"{GMAIL_API}/messages/send",
        headers=_auth(access_token),
        json={"raw": raw_message},
    )


async def send_draft(access_token: str, draft_id: str) -> dict:
    return await _post(
        f"{GMAIL_API}/drafts/send",
        headers=_auth(access_token),
        json={"id": draft_id},
    )