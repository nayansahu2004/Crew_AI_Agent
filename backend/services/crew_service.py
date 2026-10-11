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
boot meant any crew-side problem stopped the whole API from starting. Now
the API always boots, and such a problem shows up as a `failed` run with
an error message.

SYNC PYMONGO, NOT ASYNC MOTOR:
crew.kickoff() is a long-running, blocking call. FastAPI's BackgroundTasks
runs a plain (non-async) function in a thread pool. The app's Motor client
is tied to the main event loop and is NOT safe to use from another thread,
so this file uses a separate synchronous pymongo client.

RE-RUNS:
Discovery upserts creators by (campaign_id, user_id, instagram_handle), so
running a campaign again refreshes existing creators instead of
duplicating them. Review and Outreach results are applied ONLY to the
creators found in the current run (matched by instagram_handle / name),
and outreach_status only ever moves not_started -> drafted here, so a
creator a user already marked "sent" is never reset by a later run.

KNOWN LIMITATIONS:
* Review/Outreach results are matched back to creators by instagram_handle
  / name -- the only shared keys the agent prompts produce. A typo'd
  handle or a differently-phrased name silently fails to match.
* The whole pipeline runs inside ONE blocking crew.kickoff() call, so
  current_stage only changes after it finishes.
"""

import json
import logging
import re
from datetime import UTC, datetime

from bson import ObjectId
from pymongo import MongoClient, ReturnDocument

from backend.core.config import settings

logger = logging.getLogger(__name__)

_sync_client = MongoClient(settings.mongodb_uri)
_sync_db = _sync_client[settings.mongodb_database]

_CODE_FENCE = re.compile(r"^```(?:json)?\s*(.*?)\s*```$", re.DOTALL | re.IGNORECASE)


def _parse_json_or_none(raw):
    """The agents are prompted to return ONLY JSON, but models (Gemini in
    particular) often wrap it in a ```json fence anyway. Strip a fence if
    present; if it still isn't valid JSON, treat that stage's structured
    data as unavailable rather than crashing the run."""
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    match = _CODE_FENCE.match(text)
    if match:
        text = match.group(1)
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        logger.warning("Stage output was not valid JSON, skipping structured parse.")
        return None


def _normalize_score(raw) -> float | None:
    """Reviewer scores are prompted as 1-10 but models sometimes answer
    on a 0-100 scale. Store everything on a 0-10 scale."""
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    if value > 10:
        value = value / 10
    return round(max(0.0, min(value, 10.0)), 1)


def _to_int(raw) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _upsert_influencer(campaign: dict, item: dict) -> ObjectId:
    """Create (or refresh) one discovered creator and return its _id.

    Values from the LLM are coerced so a null name/follower count can't
    later break the response schema for the whole influencer list."""
    now = datetime.now(UTC)
    handle = item.get("instagram_handle") or None

    refreshed = {
        "name": item.get("name") or handle or "Unknown",
        "followers": _to_int(item.get("follower_count")),
        "category": [item["niche"]] if item.get("niche") else [],
        "updated_at": now,
    }
    defaults = {
        "platform": campaign.get("platform", "instagram"),
        "location": campaign.get("country"),
        "profile_url": None,
        "email": None,
        "bio": None,
        "discovery_source": "serper",
        "review_score": None,
        "review_reasoning": None,
        "review_status": "pending",
        "outreach_status": "not_started",
        "email_draft": None,
        "created_at": now,
    }
    identity = {
        "campaign_id": campaign["campaign_id"],
        "user_id": campaign["user_id"],
    }

    if not handle:
        # Nothing stable to dedupe on -- insert a fresh document.
        doc = {**identity, "username": None, **defaults, **refreshed}
        return _sync_db.influencers.insert_one(doc).inserted_id

    doc = _sync_db.influencers.find_one_and_update(
        {**identity, "username": handle},
        {"$set": refreshed, "$setOnInsert": defaults},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["_id"]


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
    campaign_object_id = ObjectId(campaign["campaign_id"])

    def _update_run(**fields) -> None:
        _sync_db.workflow_runs.update_one({"_id": run_object_id}, {"$set": fields})

    def _set_campaign_status(new_status: str) -> None:
        _sync_db.campaigns.update_one(
            {"_id": campaign_object_id},
            {"$set": {"status": new_status, "updated_at": datetime.now(UTC)}},
        )

    logger.info(
        "Starting run %s (crew_service v2: saves email drafts + review reasoning)", run_id
    )

    try:
        _update_run(
            status="running",
            current_stage="discovery",
            started_at=datetime.now(UTC),
        )
        _set_campaign_status("running")

        # Lazy import -- see module docstring.
        from backend.crew.workflow import run_campaign_workflow

        result = run_campaign_workflow(campaign)

        # --- Discovery: upsert creators, remember which ones this run found ---
        discovery_data = _parse_json_or_none(result.get("discovery_result"))
        influencer_ids: list[ObjectId] = []
        if isinstance(discovery_data, list):
            for item in discovery_data:
                if isinstance(item, dict):
                    influencer_ids.append(_upsert_influencer(campaign, item))

        _update_run(current_stage="review")

        # --- Review: score + reasoning, only for creators from THIS run ---
        review_data = _parse_json_or_none(result.get("review_result"))
        reviewed_count = 0
        if isinstance(review_data, list):
            for item in review_data:
                handle = item.get("instagram_handle") if isinstance(item, dict) else None
                if not handle:
                    continue
                update_result = _sync_db.influencers.update_one(
                    {"_id": {"$in": influencer_ids}, "username": handle},
                    {
                        "$set": {
                            "review_score": _normalize_score(item.get("score")),
                            "review_reasoning": item.get("reasoning"),
                            "review_status": "reviewed",
                            "updated_at": datetime.now(UTC),
                        }
                    },
                )
                if update_result.matched_count:
                    reviewed_count += 1

        _update_run(current_stage="outreach")

        # --- Outreach: save the drafted email, only for creators from THIS run ---
        outreach_data = _parse_json_or_none(result.get("outreach_result"))
        emails = outreach_data.get("emails", []) if isinstance(outreach_data, dict) else []
        drafted_count = 0
        for email in emails:
            creator_name = email.get("creator_name") if isinstance(email, dict) else None
            if not creator_name:
                continue
            match = {"_id": {"$in": influencer_ids}, "name": creator_name}
            update_result = _sync_db.influencers.update_one(
                match,
                {
                    "$set": {
                        "email_draft": {
                            "subject": email.get("subject"),
                            "body": email.get("body"),
                        },
                        "updated_at": datetime.now(UTC),
                    }
                },
            )
            if update_result.matched_count:
                drafted_count += 1
                # Only ever move not_started -> drafted. A creator the user
                # already marked "sent"/"replied" keeps that status.
                _sync_db.influencers.update_one(
                    {**match, "outreach_status": "not_started"},
                    {"$set": {"outreach_status": "drafted"}},
                )

        _update_run(
            status="completed",
            current_stage="completed",
            completed_at=datetime.now(UTC),
            result_summary={
                "discovered_count": len(influencer_ids),
                "reviewed_count": reviewed_count,
                "emails_drafted": drafted_count,
            },
        )
        _set_campaign_status("completed")

    except Exception as exc:
        logger.exception("Campaign run %s failed.", run_id)
        try:
            _update_run(
                status="failed",
                error=str(exc),
                completed_at=datetime.now(UTC),
            )
            _set_campaign_status("failed")
        except Exception:
            # The database itself may be what failed -- don't mask the
            # original error by raising a second one from here.
            logger.exception("Could not record failure for run %s.", run_id)