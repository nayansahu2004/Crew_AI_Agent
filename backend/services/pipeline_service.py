# File path: backend/services/pipeline_service.py
"""
Runs a campaign through the search pipeline (backend/pipeline/) and saves
the creators it finds into MongoDB, while keeping the workflow_run document
up to date so the website can show live progress.

SYNC PYMONGO, NOT ASYNC MOTOR:
The pipeline makes blocking web requests. FastAPI's BackgroundTasks runs a
plain (non-async) function in a thread pool. The app's Motor client is tied
to the main event loop and is NOT safe to use from another thread, so this
file uses a separate synchronous pymongo client.

EACH CREATOR IS SAVED WHOLE:
The pipeline hands back every creator with their score and drafted email
already attached, so there is no step that has to match results back to
creators by name.

RE-RUNS:
Creators are upserted by (campaign_id, user_id, instagram handle), so
running a campaign again refreshes existing creators instead of duplicating
them. A creator the user already marked "sent" keeps their sent status AND
the email that was actually sent.

FREE SEARCHES:
A run that fails, or that finds no creators, gives its search back.
"""

import logging
import re
from datetime import UTC, datetime

from bson import ObjectId
from pymongo import MongoClient, ReturnDocument

from backend.core.config import settings
from backend.core.friendly_errors import explain_run_error
from backend.pipeline.workflow import run_campaign_workflow

logger = logging.getLogger(__name__)

_sync_client = MongoClient(settings.mongodb_uri)
_sync_db = _sync_client[settings.mongodb_database]


def _load_sender(user_id: str) -> dict | None:
    """The signature details of the user who owns this run, from their
    profile (filled in at sign-up / first sign-in). Each user's emails
    carry their own details -- never anyone else's."""
    profile = _sync_db.users.find_one({"supabase_user_id": user_id})
    if not profile or not profile.get("name"):
        return None
    return {
        "name": profile["name"],
        "title": profile.get("job_title"),
        "company": profile.get("company_name"),
        "phone": profile.get("phone"),
    }


# --- Email signature -------------------------------------------------------
# The email templates (pipeline/emails.py) contain the placeholders [Your Name]
# and [Agency Name] and a generic sign-off. We replace the placeholders and swap
# the sign-off for the signature block from the user's profile.

_CLOSING_LINE = re.compile(
    r"^[ \t]*(?:best regards|kind regards|warm regards|warmest regards|regards|"
    r"sincerely|yours sincerely|best wishes|best|thanks|thank you|cheers)"
    r"[ \t]*,?[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)
_NAME_PLACEHOLDER = re.compile(r"\[\s*(?:your|sender(?:'s)?)\s+name\s*\]", re.IGNORECASE)
_COMPANY_PLACEHOLDER = re.compile(
    r"\[\s*(?:your\s+)?(?:agency|company|organi[sz]ation)(?:\s+name)?\s*\]",
    re.IGNORECASE,
)


def _fill_company(text, sender):
    if not text or not sender or not sender.get("company"):
        return text
    return _COMPANY_PLACEHOLDER.sub(sender["company"], text)


def _finalize_email_body(body, sender):
    """Fill placeholders and end the email with the sender's signature."""
    if not body or not sender:
        return body

    lines = [
        sender["name"],
        sender.get("title"),
        sender.get("company"),
        f"Ph: {sender['phone']}" if sender.get("phone") else None,
    ]
    signature = "\n".join(line for line in lines if line)

    closings = list(_CLOSING_LINE.finditer(body))
    if closings:
        last = closings[-1]
        main = body[: last.start()].rstrip()
        closing = last.group(0).strip().rstrip(",").strip()
    else:
        main, closing = body.rstrip(), "Best regards"

    main = _NAME_PLACEHOLDER.sub(sender["name"].split()[0], main)
    main = _fill_company(main, sender)
    return f"{main}\n\n{closing},\n\n{signature}"


def _save_creator(campaign: dict, creator: dict) -> ObjectId:
    """Create (or refresh) one creator, with their score, and return its _id."""
    now = datetime.now(UTC)
    handle = creator["handle"]

    refreshed = {
        "name": creator.get("name") or f"@{handle}",
        "followers": creator.get("followers"),   # None when the search never said
        "category": [creator["niche"]] if creator.get("niche") else [],
        "location": creator.get("location"),
        "profile_url": f"https://www.instagram.com/{handle}/",
        "review_score": creator.get("score"),
        "review_reasoning": creator.get("reasoning"),
        "review_status": "reviewed",
        "updated_at": now,
    }
    defaults = {
        "platform": campaign.get("platform", "instagram"),
        "email": None,
        "discovery_source": "serper",
        "outreach_status": "not_started",
        "email_draft": None,
        "created_at": now,
    }
    if creator.get("bio"):
        refreshed["bio"] = creator["bio"]
    else:
        defaults["bio"] = None

    doc = _sync_db.influencers.find_one_and_update(
        {
            "campaign_id": campaign["campaign_id"],
            "user_id": campaign["user_id"],
            "username": f"@{handle}",
        },
        {"$set": refreshed, "$setOnInsert": defaults},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["_id"]


def _save_draft(influencer_id: ObjectId, email: dict, sender: dict | None) -> bool:
    """Store the drafted email. Returns False when the creator was already
    sent an email: that creator keeps the email that was actually sent."""
    saved = _sync_db.influencers.update_one(
        {"_id": influencer_id, "outreach_status": {"$nin": ["sent", "replied"]}},
        {
            "$set": {
                "email_draft": {
                    "subject": _fill_company(email.get("subject"), sender),
                    "body": _finalize_email_body(email.get("body"), sender),
                },
                "updated_at": datetime.now(UTC),
            }
        },
    )
    if saved.matched_count == 0:
        return False
    # Only ever move not_started -> drafted; never reset "sent"/"replied".
    _sync_db.influencers.update_one(
        {"_id": influencer_id, "outreach_status": "not_started"},
        {"$set": {"outreach_status": "drafted"}},
    )
    return True


def _refund_credit(run_object_id, user_id: str) -> None:
    """A run that fails shouldn't cost the user a free search. The flag on
    the run makes sure the refund happens at most once."""
    claimed = _sync_db.workflow_runs.find_one_and_update(
        {"_id": run_object_id, "credit_charged": True, "credit_refunded": {"$ne": True}},
        {"$set": {"credit_refunded": True}},
    )
    if claimed is not None:
        _sync_db.users.update_one(
            {"supabase_user_id": user_id, "run_credits": {"$exists": True}},
            {"$inc": {"run_credits": 1}},
        )


def execute_campaign_run(run_id: str, campaign: dict) -> None:
    """
    Entry point called from a FastAPI BackgroundTask (see api/runs.py).
    Runs synchronously in Starlette's thread pool.

    `campaign` is built by the caller from the stored campaign:
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

    logger.info("Starting run %s (pipeline_service v6: built-in search pipeline)", run_id)

    try:
        _update_run(
            status="running",
            current_stage="discovery",
            started_at=datetime.now(UTC),
        )
        _set_campaign_status("running")
        sender = _load_sender(campaign["user_id"])

        # The pipeline reports "review" then "outreach" as it moves on, so the
        # website's progress strip follows the real work.
        creators = run_campaign_workflow(
            campaign, on_stage=lambda stage: _update_run(current_stage=stage)
        )

        drafted_count = 0
        for creator in creators:
            influencer_id = _save_creator(campaign, creator)
            if _save_draft(influencer_id, creator["email"], sender):
                drafted_count += 1

        found_nothing = not creators
        _update_run(
            status="completed",
            current_stage="completed",
            completed_at=datetime.now(UTC),
            result_summary={
                "discovered_count": len(creators),
                "reviewed_count": len(creators),
                "emails_drafted": drafted_count,
                # A search that finds nothing isn't charged.
                "refunded": found_nothing,
            },
        )
        _set_campaign_status("completed")
        if found_nothing:
            try:
                _refund_credit(run_object_id, campaign["user_id"])
            except Exception:
                logger.exception("Could not refund the search for run %s.", run_id)

    except Exception as exc:
        logger.exception("Campaign run %s failed.", run_id)
        # Each step is guarded on its own, so one failing (say the database
        # is struggling) can't stop the others -- especially the refund.
        steps = (
            lambda: _update_run(
                status="failed",
                error=explain_run_error(exc),
                completed_at=datetime.now(UTC),
            ),
            lambda: _set_campaign_status("failed"),
            lambda: _refund_credit(run_object_id, campaign["user_id"]),
        )
        for step in steps:
            try:
                step()
            except Exception:
                logger.exception("Could not finish recording the failure of run %s.", run_id)