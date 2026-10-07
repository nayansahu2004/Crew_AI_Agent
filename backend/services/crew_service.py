# File path: backend/services/crew_service.py
"""
Orchestrates a full campaign workflow run: advances the workflow_run
document through its stages, calls the CrewAI pipeline (crew/workflow.py),
and persists Discovery/Review/Outreach results into MongoDB.

LAZY CREW IMPORT:
The CrewAI code (crew/workflow.py -> tasks.py -> agents.py) is imported
INSIDE execute_campaign_run, not at the top of this file. Importing it
runs the LLM health check and fetches the agents from the CrewAI
repository, which needs a valid `crewai login` session. Doing that at API
boot meant any crew-side problem (expired login, Gemini and Ollama both
down) stopped the whole API from starting. Now the API always boots, and
such a problem shows up as a `failed` run with an error message. Python
doesn't cache a failed import, so after fixing the cause (e.g. re-running
`crewai login`) the next run works without restarting the server.

DELIBERATE DESIGN CHOICE -- SYNC PYMONGO, NOT ASYNC MOTOR:
crew.kickoff() is a long-running, blocking call. FastAPI's BackgroundTasks
runs a plain (non-async) function in a thread pool -- the simplest way to
keep a multi-minute CrewAI run from blocking the API. But the app's Motor
client is tied to the main event loop and is NOT safe to use from another
thread, so this file uses a separate synchronous pymongo client. If a real
task queue is added later, this could move back to Motor.

KNOWN LIMITATIONS:
* Review and Outreach results are matched back to the influencer documents
  by instagram_handle / name -- the only shared keys the current agent
  prompts produce. A typo'd handle or a differently-phrased name silently
  fails to match. A sturdier version would pass a stable ID through the
  stages.
* The whole Discovery -> Review -> Outreach pipeline runs inside ONE
  blocking crew.kickoff() call, so current_stage is only updated after it
  finishes. Polling GET /api/runs/{id} shows "discovery" for the whole
  run rather than live stage-by-stage progress.
"""

import json
import logging
from datetime import UTC, datetime

from bson import ObjectId
from pymongo import MongoClient

from backend.core.config import settings

logger = logging.getLogger(__name__)

_sync_client = MongoClient(settings.mongodb_uri)
_sync_db = _sync_client[settings.mongodb_database]


def _parse_json_or_none(raw: str | None):
    """The agents are prompted to return ONLY JSON, but nothing guarantees
    it. Never let malformed output crash the run; treat that stage's
    structured data as unavailable."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Stage output was not valid JSON, skipping structured parse.")
        return None


def execute_campaign_run(run_id: str, campaign: dict) -> None:
    """
    Entry point called from a FastAPI BackgroundTask (see api/runs.py).
    Runs synchronously in Starlette's thread pool.

    `campaign` MUST be built by the caller from the stored campaign, with
    keys renamed to match what crew/tasks.py expects:
        {
            "campaign_id": str,
            "user_id": str,
            "category": ...,
            "platform": ...,
            "country": <campaign target_country>,   # renamed!
            "min_followers": int,
            "max_followers": int,
        }
    """
    run_object_id = ObjectId(run_id)

    def _update_run(**fields) -> None:
        _sync_db.workflow_runs.update_one({"_id": run_object_id}, {"$set": fields})

    try:
        _update_run(
            status="running",
            current_stage="discovery",
            started_at=datetime.now(UTC),
        )

        # Lazy import -- see module docstring.
        from backend.crew.workflow import run_campaign_workflow

        result = run_campaign_workflow(campaign)

        # --- Discovery: insert newly found influencers ---
        discovery_data = _parse_json_or_none(result.get("discovery_result"))
        inserted_ids: list = []
        if isinstance(discovery_data, list):
            now = datetime.now(UTC)
            docs = [
                {
                    "campaign_id": campaign["campaign_id"],
                    "user_id": campaign["user_id"],
                    "name": item.get("name"),
                    "username": item.get("instagram_handle"),
                    "platform": campaign.get("platform", "instagram"),
                    "followers": item.get("follower_count"),
                    "category": [item["niche"]] if item.get("niche") else [],
                    "location": campaign.get("country"),
                    "profile_url": None,
                    "email": None,
                    "bio": None,
                    "discovery_source": "serper",
                    "review_score": None,
                    "review_status": "pending",
                    "outreach_status": "not_started",
                    "created_at": now,
                    "updated_at": now,
                }
                for item in discovery_data
                if isinstance(item, dict)
            ]
            if docs:
                inserted_ids = _sync_db.influencers.insert_many(docs).inserted_ids

        _update_run(current_stage="review")

        # --- Review: update matching influencer docs with score ---
        review_data = _parse_json_or_none(result.get("review_result"))
        reviewed_count = 0
        if isinstance(review_data, list):
            for item in review_data:
                handle = item.get("instagram_handle") if isinstance(item, dict) else None
                if not handle:
                    continue
                update_result = _sync_db.influencers.update_one(
                    {"campaign_id": campaign["campaign_id"], "username": handle},
                    {
                        "$set": {
                            "review_score": item.get("score"),
                            "review_status": "reviewed",
                            "updated_at": datetime.now(UTC),
                        }
                    },
                )
                if update_result.matched_count:
                    reviewed_count += 1

        _update_run(current_stage="outreach")

        # --- Outreach: mark matching influencers as having a drafted email ---
        outreach_data = _parse_json_or_none(result.get("outreach_result"))
        emails = outreach_data.get("emails", []) if isinstance(outreach_data, dict) else []
        drafted_count = 0
        for email in emails:
            creator_name = email.get("creator_name") if isinstance(email, dict) else None
            if not creator_name:
                continue
            update_result = _sync_db.influencers.update_one(
                {"campaign_id": campaign["campaign_id"], "name": creator_name},
                {
                    "$set": {
                        # "drafted", not "sent" -- nothing is ever emailed.
                        "outreach_status": "drafted",
                        "updated_at": datetime.now(UTC),
                    }
                },
            )
            if update_result.matched_count:
                drafted_count += 1

        _update_run(
            status="completed",
            current_stage="completed",
            completed_at=datetime.now(UTC),
            result_summary={
                "discovered_count": len(inserted_ids),
                "reviewed_count": reviewed_count,
                "emails_drafted": drafted_count,
            },
        )

    except Exception as exc:
        logger.exception("Campaign run %s failed.", run_id)
        _update_run(
            status="failed",
            error=str(exc),
            completed_at=datetime.now(UTC),
        )