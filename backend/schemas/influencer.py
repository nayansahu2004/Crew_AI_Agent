"""API request/response contracts for the /api/influencers routes."""

from datetime import datetime

from pydantic import BaseModel


class InfluencerUpdate(BaseModel):
    """Body for PATCH /api/influencers/{id}. Only the fields a user (or
    the review/outreach stages) would realistically change after
    discovery -- not the raw discovered data itself."""
    review_score: float | None = None
    review_status: str | None = None
    outreach_status: str | None = None


class InfluencerResponse(BaseModel):
    """Matches the 'influencer card' data shape described in the
    architecture doc (username, followers, category, location, score)."""
    id: str
    campaign_id: str
    user_id: str
    name: str
    username: str | None
    platform: str
    followers: int
    category: list[str]
    location: str | None
    profile_url: str | None
    email: str | None
    bio: str | None
    discovery_source: str | None
    review_score: float | None
    review_status: str
    outreach_status: str
    created_at: datetime
    updated_at: datetime