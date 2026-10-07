# File path: backend/services/run_service.py
"""
CRUD for the `workflow_runs` collection.

Creation here only writes the initial `queued` document -- the actual
CrewAI execution and stage-by-stage updates happen in crew_service.py,
called from a FastAPI BackgroundTask (see api/runs.py).
"""

from datetime import UTC, datetime

from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.errors import AppError
from backend.models import serialize_doc


def _to_object_id(run_id: str) -> ObjectId:
    try:
        return ObjectId(run_id)
    except (InvalidId, TypeError):
        raise AppError(404, "RUN_NOT_FOUND", "Run not found.")


async def create_run(
    db: AsyncIOMotorDatabase, user_id: str, campaign_id: str
) -> dict:
    """Creates the initial workflow_run document in `queued` status.
    Does NOT start the CrewAI workflow itself -- the caller (the route)
    is responsible for scheduling execute_campaign_run as a background
    task after this returns."""
    doc = {
        "campaign_id": campaign_id,
        "user_id": user_id,
        "status": "queued",
        "current_stage": None,
        "started_at": None,
        "completed_at": None,
        "error": None,
        "result_summary": {},
        "created_at": datetime.now(UTC),
    }
    result = await db.workflow_runs.insert_one(doc)
    doc["_id"] = result.inserted_id
    return serialize_doc(doc)


async def get_run(db: AsyncIOMotorDatabase, user_id: str, run_id: str) -> dict:
    oid = _to_object_id(run_id)
    doc = await db.workflow_runs.find_one({"_id": oid})

    if not doc:
        raise AppError(404, "RUN_NOT_FOUND", "Run not found.")
    if doc["user_id"] != user_id:
        raise AppError(403, "RUN_FORBIDDEN", "Not authorized to access this run.")

    return serialize_doc(doc)


async def list_runs_for_campaign(
    db: AsyncIOMotorDatabase, user_id: str, campaign_id: str
) -> list[dict]:
    cursor = db.workflow_runs.find(
        {"campaign_id": campaign_id, "user_id": user_id}
    ).sort("created_at", -1)
    return [serialize_doc(doc) async for doc in cursor]