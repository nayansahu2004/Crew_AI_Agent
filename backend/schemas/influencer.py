# File path: backend/schemas/influencer.py
"""API request/response contracts for the /api/influencers routes."""

import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator

# No whitespace, quotes, commas, brackets or semicolons -- which also rules out
# anything that could smuggle extra headers into an outgoing email.
EMAIL_PATTERN = re.compile(r"^[^\s@<>\",;]+@[^\s@<>\",;]+\.[^\s@<>\",;]+$")


class EmailDraft(BaseModel):
    subject: str | None = None
    body: str | None = None


class GmailInfo(BaseModel):
    draft_id: str | None = None
    draft_saved_at: datetime | None = None
    message_id: str | None = None
    thread_id: str | None = None
    sent_at: datetime | None = None
    sent_from: str | None = None


class InfluencerUpdate(BaseModel):
    """Body for PATCH /api/influencers/{id}. Only the fields a user (or
    the review/outreach stages) would realistically change after
    discovery -- not the raw discovered data itself.

    `email` is the creator's address the outreach email goes to. Send
    null (or an empty string) to clear it."""
    review_score: float | None = None
    review_status: str | None = None
    outreach_status: str | None = None
    email: str | None = Field(default=None, max_length=254)

    @field_validator("email", mode="before")
    @classmethod
    def _tidy_email(cls, value):
        if isinstance(value, str):
            value = value.strip().lower()
            return value or None
        return value

    @field_validator("email")
    @classmethod
    def _check_email(cls, value):
        if value is not None and not EMAIL_PATTERN.match(value):
            raise ValueError("Enter a valid email address")
        return value


class InfluencerResponse(BaseModel):
    """Matches the 'influencer card' data shape described in the
    architecture doc (username, followers, category, location, score).

    name and followers are nullable because influencers saved by early
    versions of the pipeline can hold nulls there (an agent returned no
    value) -- a single such record must not make the whole list endpoint
    fail validation. review_reasoning and email_draft default to None for
    the same reason: older records don't have them."""
    id: str
    campaign_id: str
    user_id: str
    name: str | None = None
    username: str | None
    platform: str
    followers: int | None = None
    category: list[str]
    location: str | None
    profile_url: str | None
    email: str | None
    bio: str | None
    discovery_source: str | None
    review_score: float | None
    review_reasoning: str | None = None
    review_status: str
    outreach_status: str
    email_draft: EmailDraft | None = None
    gmail: GmailInfo | None = None
    created_at: datetime
    updated_at: datetime