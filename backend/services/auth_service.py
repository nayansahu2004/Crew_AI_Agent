# File path: backend/services/auth_service.py
"""
Handles the `users` collection: creating/fetching the Mongo profile
linked to a verified Supabase identity.

supabase_user_id is always taken from the verified JWT (via
core/security.py's get_current_user), never from a request body.
"""

from datetime import UTC, datetime

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.config import settings
from backend.models import serialize_doc
from backend.schemas.user import UserProfileUpdate


async def get_or_create_user(
    db: AsyncIOMotorDatabase, supabase_user_id: str, email: str
) -> dict:
    """Called by GET /api/users/me. If no Mongo profile exists yet for
    this Supabase user (e.g. their very first authenticated request),
    creates a blank one on the fly rather than 404-ing. The profile
    fields stay empty until the user fills in the details form."""
    doc = await db.users.find_one({"supabase_user_id": supabase_user_id})
    if doc:
        return serialize_doc(doc)

    now = datetime.now(UTC)
    new_doc = {
        "supabase_user_id": supabase_user_id,
        "email": email,
        "name": None,
        "job_title": None,
        "company_name": None,
        "phone": None,
        "role": "admin",
        # Searches left. Accounts WITHOUT this field are unlimited.
        "run_credits": settings.free_runs_for_new_users,
        "created_at": now,
        "updated_at": now,
    }
    result = await db.users.insert_one(new_doc)
    new_doc["_id"] = result.inserted_id
    return serialize_doc(new_doc)


async def update_user_profile(
    db: AsyncIOMotorDatabase,
    supabase_user_id: str,
    email: str,
    data: UserProfileUpdate,
) -> dict:
    """Called by POST /api/users/me. Ensures a profile exists, then
    applies whichever fields were actually provided in the request."""
    await get_or_create_user(db, supabase_user_id, email)

    update_fields = data.model_dump(exclude_unset=True)
    if update_fields:
        update_fields["updated_at"] = datetime.now(UTC)
        await db.users.update_one(
            {"supabase_user_id": supabase_user_id},
            {"$set": update_fields},
        )

    doc = await db.users.find_one({"supabase_user_id": supabase_user_id})
    return serialize_doc(doc)