# File path: backend/schemas/influencer.py
"""API request/response contracts for the /api/influencers routes."""

from datetime import datetime

from pydantic import BaseModel


class EmailDraft(BaseModel):
    subject: str | None = None
    body: str | None = None


class InfluencerUpdate(BaseModel):
    """Body for PATCH /api/influencers/{id}. Only the fields a user (or
    the review/outreach stages) would realistically change after
    discovery -- not the raw discovered data itself."""
    review_score: float | None = None
    review_status: str | None = None
    outreach_status: str | None = None


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
    created_at: datetime
    updated_at: datetime