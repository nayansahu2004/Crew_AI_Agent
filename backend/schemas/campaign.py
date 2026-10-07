"""API request/response contracts for the /api/campaigns routes."""

from datetime import datetime

from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    """Body for POST /api/campaigns. user_id is deliberately NOT here --
    it's always taken from the authenticated user, never from the request."""
    name: str
    description: str | None = None
    category: str
    target_country: str
    min_followers: int = Field(gt=0)
    max_followers: int = Field(gt=0)
    platform: str = "instagram"


class CampaignUpdate(BaseModel):
    """Body for PATCH /api/campaigns/{id}. All fields optional -- only
    provided fields are updated."""
    name: str | None = None
    description: str | None = None
    category: str | None = None
    target_country: str | None = None
    min_followers: int | None = Field(default=None, gt=0)
    max_followers: int | None = Field(default=None, gt=0)
    platform: str | None = None
    status: str | None = None


class CampaignResponse(BaseModel):
    id: str
    user_id: str
    name: str
    description: str | None
    category: str
    target_country: str
    min_followers: int
    max_followers: int
    platform: str
    status: str
    created_at: datetime
    updated_at: datetime