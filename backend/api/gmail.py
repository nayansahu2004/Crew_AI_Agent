# File path: backend/api/gmail.py
import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import RedirectResponse
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.config import settings
from backend.core.database import get_database
from backend.core.security import AuthenticatedUser, get_current_user
from backend.schemas.gmail import GmailConnectResponse, GmailStatusResponse
from backend.schemas.influencer import InfluencerResponse
from backend.services import gmail_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/gmail", tags=["gmail"])
influencer_gmail_router = APIRouter(prefix="/api/influencers", tags=["gmail"])


@router.get("/status", response_model=GmailStatusResponse)
async def gmail_status(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await gmail_service.get_status(db, user.supabase_user_id)


@router.get("/connect", response_model=GmailConnectResponse)
async def gmail_connect(user: AuthenticatedUser = Depends(get_current_user)):
    """Returns the Google consent-screen URL; the frontend sends the
    browser there. (A plain redirect couldn't carry the login token.)"""
    return {"auth_url": gmail_service.start_connect(user.supabase_user_id)}


@router.get("/callback", include_in_schema=False)
async def gmail_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    """Google sends the browser here after the consent screen. There is no
    login token on this request -- the signed `state` identifies the user.
    Always ends in a redirect back to the app, never a JSON error page.
    (code/state are blanked out of the access log by RedactOAuthParams in main.py.)"""
    settings_page = settings.frontend_url.rstrip("/") + "/settings"

    if error or not code or not state:
        reason = "access_denied" if error == "access_denied" else "invalid_request"
        return RedirectResponse(f"{settings_page}?gmail=error&reason={reason}", status_code=303)

    try:
        await gmail_service.complete_connect(db, code, state)
    except gmail_service.ConnectError as exc:
        return RedirectResponse(f"{settings_page}?gmail=error&reason={exc.reason}", status_code=303)
    except Exception:
        logger.exception("Unexpected error while completing the Gmail connection.")
        return RedirectResponse(f"{settings_page}?gmail=error&reason=server_error", status_code=303)

    return RedirectResponse(f"{settings_page}?gmail=connected", status_code=303)


@router.delete("/connection", status_code=status.HTTP_204_NO_CONTENT)
async def gmail_disconnect(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    await gmail_service.disconnect(db, user.supabase_user_id)


@influencer_gmail_router.post("/{influencer_id}/gmail/draft", response_model=InfluencerResponse)
async def save_gmail_draft(
    influencer_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await gmail_service.save_draft(db, user.supabase_user_id, influencer_id)


@influencer_gmail_router.post("/{influencer_id}/gmail/send", response_model=InfluencerResponse)
async def send_gmail_email(
    influencer_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await gmail_service.send_email(db, user.supabase_user_id, influencer_id)