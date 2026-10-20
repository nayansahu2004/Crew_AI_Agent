# File path: backend/schemas/gmail.py
"""API response contracts for the /api/gmail routes."""

from datetime import datetime

from pydantic import BaseModel


class GmailStatusResponse(BaseModel):
    # False when the server has no Google credentials -- the UI should say
    # Gmail isn't set up, rather than offering a Connect button that can't work.
    configured: bool
    connected: bool
    # True when a connection existed but Google rejected it (revoked, or
    # expired -- Testing-mode apps expire after 7 days). Needs reconnecting.
    needs_reconnect: bool = False
    email: str | None = None
    connected_at: datetime | None = None


class GmailConnectResponse(BaseModel):
    auth_url: str