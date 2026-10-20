# File path: backend/schemas/user.py
"""API request/response contracts for the /api/users routes."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, computed_field, field_validator

from backend.models.user import REQUIRED_PROFILE_FIELDS

# 7-20 characters: optional leading +, then digits with spaces, dashes or
# brackets allowed between them (e.g. "+91 98765 43210").
PHONE_PATTERN = re.compile(r"^\+?[0-9][0-9\s\-()]{6,19}$")


class UserProfileUpdate(BaseModel):
    """Body for POST /api/users/me -- only fields the user is allowed to
    set themselves. supabase_user_id/email come from the verified token,
    never from this body."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    job_title: str | None = Field(default=None, min_length=2, max_length=100)
    company_name: str | None = Field(default=None, min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)

    @field_validator("name", "job_title", "company_name", "phone", mode="before")
    @classmethod
    def _tidy_whitespace(cls, value):
        # Trim and collapse runs of spaces BEFORE the length checks, so a
        # value of just spaces is rejected rather than stored.
        if isinstance(value, str):
            return " ".join(value.split())
        return value

    @field_validator("phone")
    @classmethod
    def _check_phone(cls, value):
        if value is not None and not PHONE_PATTERN.match(value):
            raise ValueError("Enter a valid phone number, e.g. +91 98765 43210")
        return value


class UserProfileResponse(BaseModel):
    """Response shape for GET and POST /api/users/me. The profile fields
    default to None so users created before they existed still serialize."""

    id: str
    supabase_user_id: str
    email: str
    name: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    phone: str | None = None
    role: str
    # Searches left; None means unlimited.
    run_credits: int | None = None
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def profile_complete(self) -> bool:
        return all((getattr(self, f) or "").strip() for f in REQUIRED_PROFILE_FIELDS)