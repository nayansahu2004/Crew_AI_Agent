"""Shape of a document in the `campaigns` collection."""

from datetime import datetime

from pydantic import BaseModel, Field


class CampaignModel(BaseModel):
    user_id: str
    name: str
    description: str | None = None
    category: str
    target_country: str
    min_followers: int
    max_followers: int
    platform: str
    status: str = "draft"  # draft | queued | running | completed | failed
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)