# File path: backend/api/users.py
from fastapi import APIRouter, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.database import get_database
from backend.core.security import AuthenticatedUser, get_current_user
from backend.schemas.user import UserProfileResponse, UserProfileUpdate
from backend.services import auth_service

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    profile = await auth_service.get_or_create_user(
        db, user.supabase_user_id, user.email
    )
    return profile


@router.post("/me", response_model=UserProfileResponse)
async def update_my_profile(
    data: UserProfileUpdate,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    profile = await auth_service.update_user_profile(
        db, user.supabase_user_id, user.email, data
    )
    return profile