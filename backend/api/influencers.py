# File path: backend/api/influencers.py
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.database import get_database
from backend.core.security import AuthenticatedUser, get_current_user
from backend.schemas.influencer import InfluencerResponse, InfluencerUpdate
from backend.services import influencer_service

# Two routers because the endpoints hang off two different URL prefixes
# (nested under /api/campaigns for the list, standalone under
# /api/influencers for a single one) -- both included in main.py.
campaign_influencers_router = APIRouter(prefix="/api/campaigns", tags=["influencers"])
influencers_router = APIRouter(prefix="/api/influencers", tags=["influencers"])


@campaign_influencers_router.get(
    "/{campaign_id}/influencers", response_model=list[InfluencerResponse]
)
async def list_influencers_for_campaign(
    campaign_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await influencer_service.list_influencers_for_campaign(
        db, user.supabase_user_id, campaign_id
    )


@influencers_router.get("/{influencer_id}", response_model=InfluencerResponse)
async def get_influencer(
    influencer_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await influencer_service.get_influencer(
        db, user.supabase_user_id, influencer_id
    )


@influencers_router.patch("/{influencer_id}", response_model=InfluencerResponse)
async def update_influencer(
    influencer_id: str,
    data: InfluencerUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await influencer_service.update_influencer(
        db, user.supabase_user_id, influencer_id, data
    )