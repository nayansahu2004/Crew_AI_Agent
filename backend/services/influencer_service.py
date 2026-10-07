# File path: backend/services/influencer_service.py
"""
Read/update access to the `influencers` collection, with ownership
enforcement on every operation.

NOTE: influencer CREATION during a campaign run happens in
crew_service.py (via a separate synchronous pymongo client). This
service only covers the read and update paths used by the API routes.
"""

from datetime import UTC, datetime

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.errors import AppError
from backend.models import serialize_doc
from backend.schemas.influencer import InfluencerUpdate
from backend.services.campaign_service import get_campaign


def _to_object_id(influencer_id: str) -> ObjectId:
    try:
        return ObjectId(influencer_id)
    except (InvalidId, TypeError):
        raise AppError(404, "INFLUENCER_NOT_FOUND", "Influencer not found.")


async def list_influencers_for_campaign(
    db: AsyncIOMotorDatabase, user_id: str, campaign_id: str
) -> list[dict]:
    await get_campaign(db, user_id, campaign_id)  # 404/403 if not owned
    cursor = db.influencers.find({"campaign_id": campaign_id, "user_id": user_id})
    return [serialize_doc(doc) async for doc in cursor]


async def get_influencer(
    db: AsyncIOMotorDatabase, user_id: str, influencer_id: str
) -> dict:
    oid = _to_object_id(influencer_id)
    doc = await db.influencers.find_one({"_id": oid})

    if not doc:
        raise AppError(404, "INFLUENCER_NOT_FOUND", "Influencer not found.")
    if doc["user_id"] != user_id:
        raise AppError(
            403, "INFLUENCER_FORBIDDEN", "Not authorized to access this influencer."
        )

    return serialize_doc(doc)


async def update_influencer(
    db: AsyncIOMotorDatabase, user_id: str, influencer_id: str, data: InfluencerUpdate
) -> dict:
    await get_influencer(db, user_id, influencer_id)  # ownership check first

    update_fields = data.model_dump(exclude_unset=True)
    if update_fields:
        update_fields["updated_at"] = datetime.now(UTC)
        await db.influencers.update_one(
            {"_id": ObjectId(influencer_id)}, {"$set": update_fields}
        )

    doc = await db.influencers.find_one({"_id": ObjectId(influencer_id)})
    return serialize_doc(doc)