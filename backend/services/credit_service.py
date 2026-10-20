# File path: backend/services/credit_service.py
"""
Free searches. A "search" is one run of the pipeline on a campaign.

New accounts start with `run_credits` = FREE_RUNS_FOR_NEW_USERS (2). Each
run uses one; a run that fails is refunded (see crew_service.py). An
account whose user document has NO `run_credits` field is unlimited --
that's every account that existed before this feature, and anyone you
choose to make unlimited with the grant_credits script.

There is deliberately no payment code here: when someone pays you, you top
them up yourself (see backend/scripts/grant_credits.py).
"""

from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.errors import AppError


async def consume_run_credit(db: AsyncIOMotorDatabase, user_id: str) -> bool:
    """Spend one search. Returns True if one was spent, False if the account
    is unlimited. Raises 402 NO_CREDITS when a metered account is out.

    The decrement is a single conditional update, so two runs started at
    the same moment can't both spend the last search."""
    spent = await db.users.find_one_and_update(
        {"supabase_user_id": user_id, "run_credits": {"$gt": 0}},
        {"$inc": {"run_credits": -1}},
    )
    if spent is not None:
        return True

    metered = await db.users.find_one(
        {"supabase_user_id": user_id, "run_credits": {"$exists": True}}, {"_id": 1}
    )
    if metered is not None:
        raise AppError(
            402,
            "NO_CREDITS",
            "You've used all your free searches. Contact the site owner to continue.",
        )
    return False


async def refund_run_credit(db: AsyncIOMotorDatabase, user_id: str) -> None:
    await db.users.update_one(
        {"supabase_user_id": user_id, "run_credits": {"$exists": True}},
        {"$inc": {"run_credits": 1}},
    )