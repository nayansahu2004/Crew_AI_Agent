# File path: backend/services/gmail_service.py
"""
Gmail business logic: connecting an account, and saving / sending an
outreach email from it.

Stored per user in the `gmail_connections` collection:
    supabase_user_id, google_email, refresh_token_enc (ENCRYPTED), scopes,
    connected_at, updated_at, needs_reconnect
The refresh token is only ever decrypted in memory, to fetch a short-lived
access token for one action. It never goes to the browser or the logs.

Nothing here sends an email unless a user explicitly asks for that one
creator's email to be sent -- the pipeline itself still only drafts.
"""

import base64
import logging
from datetime import UTC, datetime, timedelta
from email.headerregistry import Address
from email.message import EmailMessage

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core import crypto
from backend.core.config import settings
from backend.core.errors import AppError
from backend.services import google_client, influencer_service
from backend.services.google_client import GoogleApiError

logger = logging.getLogger(__name__)

_LOCK_SECONDS = 120  # a send that never finished frees itself after this long


class ConnectError(Exception):
    """The OAuth callback failed. `reason` is a short code the frontend maps
    to a message (it travels in the redirect URL, so keep it a plain word)."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


# --- Connection ---------------------------------------------------------------

async def get_status(db: AsyncIOMotorDatabase, user_id: str) -> dict:
    conn = await db.gmail_connections.find_one({"supabase_user_id": user_id})
    needs_reconnect = bool(conn and conn.get("needs_reconnect"))
    return {
        "configured": settings.gmail_configured,
        "connected": bool(conn) and not needs_reconnect,
        "needs_reconnect": needs_reconnect,
        "email": conn.get("google_email") if conn else None,
        "connected_at": conn.get("connected_at") if conn else None,
    }


def start_connect(user_id: str) -> str:
    if not settings.gmail_configured:
        raise AppError(
            503,
            "GMAIL_NOT_CONFIGURED",
            "Gmail isn't set up on this server yet. Ask the administrator to add the Google credentials.",
        )
    return google_client.build_auth_url(crypto.sign_state(user_id))


async def complete_connect(db: AsyncIOMotorDatabase, code: str, state: str) -> None:
    user_id = crypto.verify_state(state)
    if user_id is None:
        raise ConnectError("invalid_state")

    try:
        tokens = await google_client.exchange_code(code)
    except GoogleApiError as exc:
        logger.warning("Google code exchange failed (%s).", exc.kind)
        raise ConnectError("exchange_failed") from exc

    # Google lets people untick individual permissions on the consent screen.
    granted = (tokens.get("scope") or "").split()
    if google_client.COMPOSE_SCOPE not in granted:
        raise ConnectError("permission_denied")

    refresh_token = tokens.get("refresh_token")
    if not refresh_token:
        raise ConnectError("no_refresh_token")

    google_email = google_client.email_from_id_token(tokens.get("id_token"))
    if not google_email:
        raise ConnectError("no_email")

    now = datetime.now(UTC)
    await db.gmail_connections.update_one(
        {"supabase_user_id": user_id},
        {
            "$set": {
                "google_email": google_email,
                "refresh_token_enc": crypto.encrypt_secret(refresh_token),
                "scopes": granted,
                "needs_reconnect": False,
                "updated_at": now,
            },
            "$setOnInsert": {"connected_at": now},
        },
        upsert=True,
    )
    # Re-connecting after a revoke should read as a fresh connection.
    await db.gmail_connections.update_one(
        {"supabase_user_id": user_id}, {"$set": {"connected_at": now}}
    )


async def disconnect(db: AsyncIOMotorDatabase, user_id: str) -> None:
    """Idempotent: disconnecting when nothing is connected is not an error."""
    conn = await db.gmail_connections.find_one({"supabase_user_id": user_id})
    if not conn:
        return
    try:
        await google_client.revoke_token(crypto.decrypt_secret(conn["refresh_token_enc"]))
    except (crypto.InvalidToken, crypto.CryptoConfigError, KeyError):
        pass  # can't decrypt it, so nothing to revoke -- still remove it below
    await db.gmail_connections.delete_one({"supabase_user_id": user_id})


# --- Errors -------------------------------------------------------------------

def _to_app_error(exc: GoogleApiError) -> AppError:
    if exc.kind == "rate_limited":
        return AppError(429, "GMAIL_RATE_LIMITED", "Gmail is limiting requests right now. Wait a few minutes and try again.")
    if exc.kind == "forbidden":
        return AppError(409, "GMAIL_PERMISSION_DENIED", "Gmail refused the request. Reconnect Gmail in Settings and allow all the requested permissions.")
    if exc.kind == "unavailable":
        return AppError(502, "GMAIL_UNAVAILABLE", "Couldn't reach Gmail. Please try again in a moment.")
    if exc.kind == "bad_request":
        return AppError(502, "GMAIL_REJECTED", "Gmail rejected this email. Check the recipient's address and try again.")
    return AppError(502, "GMAIL_ERROR", "Something went wrong talking to Gmail. Please try again.")


async def _mark_needs_reconnect(db: AsyncIOMotorDatabase, user_id: str) -> None:
    await db.gmail_connections.update_one(
        {"supabase_user_id": user_id},
        {"$set": {"needs_reconnect": True, "updated_at": datetime.now(UTC)}},
    )


async def _access_token(db: AsyncIOMotorDatabase, user_id: str) -> tuple[str, str]:
    """A fresh short-lived access token and the connected address."""
    conn = await db.gmail_connections.find_one({"supabase_user_id": user_id})
    if not conn:
        raise AppError(409, "GMAIL_NOT_CONNECTED", "Connect your Gmail in Settings first.")
    reconnect = AppError(
        409, "GMAIL_RECONNECT_REQUIRED",
        "Your Gmail connection has expired. Reconnect it in Settings.",
    )
    if conn.get("needs_reconnect"):
        raise reconnect

    try:
        refresh_token = crypto.decrypt_secret(conn["refresh_token_enc"])
    except crypto.InvalidToken:
        await _mark_needs_reconnect(db, user_id)
        raise reconnect

    try:
        return await google_client.refresh_access_token(refresh_token), conn["google_email"]
    except GoogleApiError as exc:
        if exc.kind == "invalid_grant":
            await _mark_needs_reconnect(db, user_id)
            raise reconnect from exc
        raise _to_app_error(exc) from exc


# --- Messages -----------------------------------------------------------------

def build_raw_message(sender_name: str | None, from_email: str, to_email: str, subject: str | None, body: str | None) -> str:
    """The email as the base64url string the Gmail API expects."""
    message = EmailMessage()
    message["To"] = to_email
    message["From"] = Address(display_name=sender_name or "", addr_spec=from_email)
    # A newline in a header would let the text smuggle in extra headers.
    message["Subject"] = " ".join((subject or "").split()) or "(no subject)"
    message.set_content(body or "")
    return base64.urlsafe_b64encode(message.as_bytes()).decode()


async def _prepare(db: AsyncIOMotorDatabase, user_id: str, influencer_id: str) -> tuple[dict, str | None]:
    """Ownership check (404/403), then make sure there's something to send
    and somewhere to send it."""
    influencer = await influencer_service.get_influencer(db, user_id, influencer_id)
    draft = influencer.get("email_draft") or {}
    if not (draft.get("subject") or draft.get("body")):
        raise AppError(409, "NO_DRAFT", "This creator has no email draft yet. Run the pipeline first.")
    if not influencer.get("email"):
        raise AppError(409, "RECIPIENT_MISSING", "Add the creator's email address first.")
    profile = await db.users.find_one({"supabase_user_id": user_id})
    return influencer, (profile or {}).get("name")


async def save_draft(db: AsyncIOMotorDatabase, user_id: str, influencer_id: str) -> dict:
    influencer, sender_name = await _prepare(db, user_id, influencer_id)
    if influencer["outreach_status"] in ("sent", "replied"):
        raise AppError(409, "ALREADY_SENT", "This email has already been sent.")

    access_token, from_email = await _access_token(db, user_id)
    draft = influencer["email_draft"]
    raw = build_raw_message(sender_name, from_email, influencer["email"], draft.get("subject"), draft.get("body"))

    try:
        created = await google_client.create_draft(access_token, raw)
    except GoogleApiError as exc:
        raise _to_app_error(exc) from exc

    now = datetime.now(UTC)
    await db.influencers.update_one(
        {"_id": _oid(influencer_id)},
        {"$set": {"gmail.draft_id": created.get("id"), "gmail.draft_saved_at": now, "updated_at": now}},
    )
    return await influencer_service.get_influencer(db, user_id, influencer_id)


async def send_email(db: AsyncIOMotorDatabase, user_id: str, influencer_id: str) -> dict:
    influencer, sender_name = await _prepare(db, user_id, influencer_id)
    if influencer["outreach_status"] in ("sent", "replied"):
        raise AppError(409, "ALREADY_SENT", "This email has already been sent.")

    now = datetime.now(UTC)
    limit = settings.gmail_daily_send_limit
    sent_today = await db.influencers.count_documents(
        {"user_id": user_id, "gmail.sent_at": {"$gte": now - timedelta(hours=24)}}
    )
    if sent_today >= limit:
        raise AppError(429, "SEND_LIMIT_REACHED", f"You've reached the limit of {limit} emails per 24 hours. Try again later.")

    # Claim this creator atomically so a double-click (or two tabs) can't
    # send the same email twice. A lock left by a crashed request expires.
    claimed = await db.influencers.find_one_and_update(
        {
            "_id": _oid(influencer_id),
            "user_id": user_id,
            "outreach_status": {"$nin": ["sent", "replied"]},
            "$or": [
                {"gmail_sending_at": {"$exists": False}},
                {"gmail_sending_at": None},
                {"gmail_sending_at": {"$lt": now - timedelta(seconds=_LOCK_SECONDS)}},
            ],
        },
        {"$set": {"gmail_sending_at": now}},
    )
    if claimed is None:
        raise AppError(409, "SEND_IN_PROGRESS", "This email is already being sent, or was just sent.")

    try:
        access_token, from_email = await _access_token(db, user_id)
        draft = influencer["email_draft"]
        raw = build_raw_message(sender_name, from_email, influencer["email"], draft.get("subject"), draft.get("body"))
        saved_draft_id = (influencer.get("gmail") or {}).get("draft_id")

        try:
            if saved_draft_id:
                # Send the Gmail draft, so edits the user made there are kept.
                try:
                    result = await google_client.send_draft(access_token, saved_draft_id)
                except GoogleApiError as exc:
                    if exc.kind != "not_found":
                        raise
                    result = await google_client.send_message(access_token, raw)  # draft was deleted
            else:
                result = await google_client.send_message(access_token, raw)
        except GoogleApiError as exc:
            raise _to_app_error(exc) from exc
    except BaseException:
        await db.influencers.update_one({"_id": _oid(influencer_id)}, {"$unset": {"gmail_sending_at": ""}})
        raise

    try:
        sent_at = datetime.now(UTC)
        await db.influencers.update_one(
            {"_id": _oid(influencer_id)},
            {
                "$set": {
                    "outreach_status": "sent",
                    "gmail.message_id": result.get("id"),
                    "gmail.thread_id": result.get("threadId"),
                    "gmail.sent_at": sent_at,
                    "gmail.sent_from": from_email,
                    "updated_at": sent_at,
                },
                "$unset": {"gmail_sending_at": ""},
            },
        )
    except Exception:
        # The email IS out. Don't tell the user it failed (they'd resend).
        logger.exception("Email %s was sent but could not be recorded.", influencer_id)
    return await influencer_service.get_influencer(db, user_id, influencer_id)


def _oid(influencer_id: str):
    from bson import ObjectId

    return ObjectId(influencer_id)