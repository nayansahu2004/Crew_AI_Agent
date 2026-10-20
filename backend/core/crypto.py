# File path: backend/core/crypto.py
"""
Two small security helpers for the Gmail connection:

  * encrypt_secret / decrypt_secret -- Fernet encryption for the Google
    refresh token, so a leaked database dump doesn't hand out access to
    anyone's mailbox. Keys come from TOKEN_ENCRYPTION_KEY (comma-separated
    for rotation: the first encrypts, every key can decrypt).

  * sign_state / verify_state -- the OAuth `state` value. Google redirects
    the browser back to us WITHOUT our login token, so `state` is the only
    thing tying the callback to the user who started the connection. It is
    HMAC-signed (so it can't be forged or swapped for another user's) and
    expires after a few minutes.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

from backend.core.config import settings

__all__ = [
    "CryptoConfigError",
    "InvalidToken",
    "decrypt_secret",
    "encrypt_secret",
    "sign_state",
    "verify_state",
]


class CryptoConfigError(RuntimeError):
    """TOKEN_ENCRYPTION_KEY is missing or not a valid Fernet key."""


def _keys() -> list[str]:
    raw = settings.token_encryption_key or ""
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        raise CryptoConfigError("TOKEN_ENCRYPTION_KEY is not set.")
    return keys


def _fernet() -> MultiFernet:
    try:
        return MultiFernet([Fernet(k) for k in _keys()])
    except ValueError as exc:
        raise CryptoConfigError("TOKEN_ENCRYPTION_KEY is not a valid Fernet key.") from exc


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_secret(token: str) -> str:
    """Raises InvalidToken if the value was tampered with or was encrypted
    with a key that is no longer configured."""
    return _fernet().decrypt(token.encode()).decode()


# --- OAuth state ------------------------------------------------------------

def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _state_key() -> bytes:
    # Derived from (not equal to) the encryption key, so the two uses stay
    # separate.
    return hmac.new(_keys()[0].encode(), b"gmail-oauth-state-v1", hashlib.sha256).digest()


def sign_state(user_id: str, ttl_seconds: int = 600, now: float | None = None) -> str:
    now = time.time() if now is None else now
    payload = {"uid": user_id, "exp": int(now + ttl_seconds), "n": secrets.token_urlsafe(8)}
    body = _b64(json.dumps(payload, separators=(",", ":")).encode())
    signature = _b64(hmac.new(_state_key(), body.encode(), hashlib.sha256).digest())
    return f"{body}.{signature}"


def verify_state(state: str, now: float | None = None) -> str | None:
    """Returns the user id the state was issued to, or None if it is
    forged, malformed or expired."""
    now = time.time() if now is None else now
    try:
        body, signature = state.split(".", 1)
        expected = _b64(hmac.new(_state_key(), body.encode(), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            return None
        payload = json.loads(_unb64(body))
        if payload["exp"] < now:
            return None
        return str(payload["uid"])
    except Exception:
        return None