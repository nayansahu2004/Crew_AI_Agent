"""API request/response contracts for the /api/users routes."""

from datetime import datetime

from pydantic import BaseModel


class UserProfileUpdate(BaseModel):
    """Body for POST /api/users/me -- only fields the user is allowed to
    set themselves. supabase_user_id/email come from the verified token,
    never from this body."""
    name: str | None = None
    company_name: str | None = None


class UserProfileResponse(BaseModel):
    """Response shape for GET and POST /api/users/me."""
    id: str
    supabase_user_id: str
    email: str
    name: str | None
    company_name: str | None
    role: str
    created_at: datetime
    updated_at: datetime