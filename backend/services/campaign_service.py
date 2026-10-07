# File path: backend/services/campaign_service.py
"""
CRUD + ownership enforcement for the `campaigns` collection.

Every function that touches a specific campaign takes the authenticated
user's ID and enforces ownership itself -- routes should never query
campaigns directly, always through this service.
"""

from datetime import UTC, datetime

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.errors import AppError
from backend.models import serialize_doc
from backend.schemas.campaign import CampaignCreate, CampaignUpdate


def _to_object_id(campaign_id: str) -> ObjectId:
    try:
        return ObjectId(campaign_id)
    except (InvalidId, TypeError):
        raise AppError(404, "CAMPAIGN_NOT_FOUND", "Campaign not found.")


async def create_campaign(
    db: AsyncIOMotorDatabase, user_id: str, data: CampaignCreate
) -> dict:
    now = datetime.now(UTC)
    doc = {
        "user_id": user_id,
        **data.model_dump(),
        "status": "draft",
        "created_at": now,
        "updated_at": now,
    }
    result = await db.campaigns.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_doc(doc)


async def list_campaigns(db: AsyncIOMotorDatabase, user_id: str) -> list[dict]:
    cursor = db.campaigns.find({"user_id": user_id}).sort("created_at", -1)
    return [serialize_doc(doc) async for doc in cursor]


async def get_campaign(
    db: AsyncIOMotorDatabase, user_id: str, campaign_id: str
) -> dict:
    """404 if the campaign doesn't exist at all; 403 if it exists but
    belongs to someone else."""
    oid = _to_object_id(campaign_id)
    doc = await db.campaigns.find_one({"_id": oid})

    if not doc:
        raise AppError(404, "CAMPAIGN_NOT_FOUND", "Campaign not found.")
    if doc["user_id"] != user_id:
        raise AppError(
            403, "CAMPAIGN_FORBIDDEN", "Not authorized to access this campaign."
        )

    return serialize_doc(doc)


async def update_campaign(
    db: AsyncIOMotorDatabase, user_id: str, campaign_id: str, data: CampaignUpdate
) -> dict:
    await get_campaign(db, user_id, campaign_id)  # ownership check first

    update_fields = data.model_dump(exclude_unset=True)
    if update_fields:
        update_fields["updated_at"] = datetime.now(UTC)
        await db.campaigns.update_one(
            {"_id": ObjectId(campaign_id)}, {"$set": update_fields}
        )

    doc = await db.campaigns.find_one({"_id": ObjectId(campaign_id)})
    return serialize_doc(doc)


async def delete_campaign(
    db: AsyncIOMotorDatabase, user_id: str, campaign_id: str
) -> None:
    await get_campaign(db, user_id, campaign_id)  # ownership check first
    await db.campaigns.delete_one({"_id": ObjectId(campaign_id)})