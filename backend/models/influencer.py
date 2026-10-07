"""Shape of a document in the `influencers` collection."""

from datetime import datetime

from pydantic import BaseModel, Field


class InfluencerModel(BaseModel):
    campaign_id: str
    user_id: str
    name: str
    username: str | None = None
    platform: str
    followers: int
    category: list[str] = Field(default_factory=list)
    location: str | None = None
    profile_url: str | None = None
    email: str | None = None
    bio: str | None = None
    discovery_source: str | None = None
    review_score: float | None = None
    review_status: str = "pending"        # pending | reviewed
    outreach_status: str = "not_started"  # not_started | sent | replied
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)