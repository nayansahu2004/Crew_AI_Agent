# File path: backend/api/runs.py
from fastapi import APIRouter, BackgroundTasks, Depends, status
from motor.motor_asyncio import AsyncIOMotorDatabase

from backend.core.database import get_database
from backend.core.errors import AppError
from backend.core.security import AuthenticatedUser, get_current_user
from backend.models.user import is_profile_complete
from backend.schemas.run import RunCreateResponse, RunListItem, RunStatusResponse
from backend.services import auth_service, campaign_service, credit_service, run_service
from backend.services.pipeline_service import execute_campaign_run

# Same split-router pattern as influencers.py: one route is nested under
# /api/campaigns, the other two stand alone under /api/runs.
campaign_runs_router = APIRouter(prefix="/api/campaigns", tags=["runs"])
runs_router = APIRouter(prefix="/api/runs", tags=["runs"])


@campaign_runs_router.post(
    "/{campaign_id}/runs",
    response_model=RunCreateResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def start_campaign_run(
    campaign_id: str,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    # Ownership check + fetch the campaign's actual config -- 404/403
    # raised here if the campaign doesn't exist or isn't this user's.
    campaign_doc = await campaign_service.get_campaign(
        db, user.supabase_user_id, campaign_id
    )

    # The drafted emails are signed with the user's own details, so a run
    # can't start until those are filled in.
    profile = await auth_service.get_or_create_user(
        db, user.supabase_user_id, user.email
    )
    if not is_profile_complete(profile):
        raise AppError(
            409,
            "PROFILE_INCOMPLETE",
            "Complete your profile (name, job title, company and phone) before "
            "running a campaign — it's used to sign your outreach emails.",
        )

    # Uses one of the user's free searches (402 NO_CREDITS if none are left).
    # Accounts without a counter are unlimited and aren't charged.
    charged = await credit_service.consume_run_credit(db, user.supabase_user_id)
    try:
        run = await run_service.create_run(
            db, user.supabase_user_id, campaign_id, credit_charged=charged
        )
    except Exception:
        if charged:  # never keep the search for a run that never started
            await credit_service.refund_run_credit(db, user.supabase_user_id)
        raise

    # Build the dict the pipeline expects -- note the
    # target_country -> country rename, documented in pipeline_service.py.
    campaign_config = {
        "campaign_id": campaign_id,
        "user_id": user.supabase_user_id,
        "category": campaign_doc["category"],
        "platform": campaign_doc["platform"],
        "country": campaign_doc["target_country"],
        "min_followers": campaign_doc["min_followers"],
        "max_followers": campaign_doc["max_followers"],
    }

    # Runs AFTER this response is sent, in Starlette's thread pool (since
    # execute_campaign_run is a plain sync function) -- see pipeline_service.py
    # for why that matters (sync PyMongo, not async Motor, inside it).
    background_tasks.add_task(execute_campaign_run, run["id"], campaign_config)

    return RunCreateResponse(run_id=run["id"], status=run["status"])


@runs_router.get("/{run_id}", response_model=RunStatusResponse)
async def get_run_status(
    run_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    run = await run_service.get_run(db, user.supabase_user_id, run_id)
    return RunStatusResponse(
        run_id=run["id"],
        campaign_id=run["campaign_id"],
        status=run["status"],
        current_stage=run["current_stage"],
        started_at=run["started_at"],
        completed_at=run["completed_at"],
        error=run["error"],
        result_summary=run["result_summary"],
    )


@campaign_runs_router.get(
    "/{campaign_id}/runs", response_model=list[RunListItem]
)
async def list_campaign_runs(
    campaign_id: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncIOMotorDatabase = Depends(get_database),
):
    # Ownership check on the campaign itself before listing its runs.
    await campaign_service.get_campaign(db, user.supabase_user_id, campaign_id)

    runs = await run_service.list_runs_for_campaign(
        db, user.supabase_user_id, campaign_id
    )
    return [
        RunListItem(
            run_id=r["id"],
            status=r["status"],
            current_stage=r["current_stage"],
            started_at=r["started_at"],
            completed_at=r["completed_at"],
        )
        for r in runs
    ]