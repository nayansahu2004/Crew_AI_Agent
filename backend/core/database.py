"""
MongoDB connection layer, using Motor (async driver, matches FastAPI's
async request handling).

Usage:
  - Call connect_to_mongo() on FastAPI startup, close_mongo_connection()
    on shutdown (wired up in main.py, Phase 7).
  - Use get_database() as a FastAPI dependency in routes/services that
    need DB access: `db = Depends(get_database)`.
"""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from backend.core.config import settings

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None


async def connect_to_mongo() -> None:
    """Opens the MongoDB connection and ensures required indexes exist.
    Call once, on FastAPI startup."""
    global _client, _db

    _client = AsyncIOMotorClient(settings.mongodb_uri)
    _db = _client[settings.mongodb_database]

    # Cheap way to fail fast on startup if the URI/credentials are wrong,
    # instead of failing later on the first real request.
    await _client.admin.command("ping")
    logger.info("Connected to MongoDB database '%s'.", settings.mongodb_database)

    await _create_indexes()


async def close_mongo_connection() -> None:
    """Closes the MongoDB connection. Call once, on FastAPI shutdown."""
    global _client
    if _client is not None:
        _client.close()
        logger.info("MongoDB connection closed.")


def get_database() -> AsyncIOMotorDatabase:
    """FastAPI dependency: returns the shared database handle.

    Raises if called before connect_to_mongo() has run (i.e. outside a
    running FastAPI app with the startup event wired up) -- this is
    intentional, so a missing startup hook fails loudly rather than
    silently returning None.
    """
    if _db is None:
        raise RuntimeError(
            "Database not initialized. connect_to_mongo() must be called "
            "on app startup before any request uses get_database()."
        )
    return _db


async def _create_indexes() -> None:
    """Creates the indexes listed in the architecture doc. Safe to call
    repeatedly -- create_index() is a no-op if the index already exists
    with the same spec."""
    db = get_database()

    await db.users.create_index("supabase_user_id", unique=True)
    await db.campaigns.create_index("user_id")
    await db.influencers.create_index("user_id")
    await db.influencers.create_index("campaign_id")
    await db.workflow_runs.create_index("user_id")
    await db.workflow_runs.create_index("campaign_id")

    logger.info("MongoDB indexes ensured.")