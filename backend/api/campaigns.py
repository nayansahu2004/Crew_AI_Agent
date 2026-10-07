# File path: backend/api/campaigns.py
from fastapi import APIRouter, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.database import get_database
from backend.core.security import AuthenticatedUser, get_current_user
from backend.schemas.campaign import CampaignCreate, CampaignResponse, CampaignUpdate
from backend.services import campaign_service

router = APIRouter(prefix="/api/campaigns", tags=["campaigns"])


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    data: CampaignCreate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await campaign_service.create_campaign(db, user.supabase_user_id, data)


@router.get("", response_model=list[CampaignResponse])
async def list_campaigns(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await campaign_service.list_campaigns(db, user.supabase_user_id)


@router.get("/{campaign_id}", response_model=CampaignResponse)
async def get_campaign(
    campaign_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await campaign_service.get_campaign(db, user.supabase_user_id, campaign_id)


@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    data: CampaignUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    return await campaign_service.update_campaign(
        db, user.supabase_user_id, campaign_id, data
    )


@router.delete("/{campaign_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_campaign(
    campaign_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    await campaign_service.delete_campaign(db, user.supabase_user_id, campaign_id)