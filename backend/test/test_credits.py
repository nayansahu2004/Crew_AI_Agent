# File path: backend/test/test_credits.py
"""Free searches: new accounts get 2, each run uses one, a failed run is
refunded, accounts that predate the feature stay unlimited."""

import asyncio
from datetime import UTC, datetime

import mongomock
import pytest
from bson import ObjectId

from backend.scripts import grant_credits
from backend.services import pipeline_service, run_service
from backend.test.conftest import COMPLETE_PROFILE, TEST_USER
from backend.test.test_campaigns import VALID_CAMPAIGN_BODY


async def new_campaign(client) -> str:
    return (await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)).json()["id"]


async def start_run(client, campaign_id):
    return await client.post(f"/api/campaigns/{campaign_id}/runs")


async def balance(client):
    return (await client.get("/api/users/me")).json()["run_credits"]


# --- the API ------------------------------------------------------------------

@pytest.mark.asyncio
async def test_new_accounts_start_with_two_free_searches(client):
    assert (await client.get("/api/users/me")).json()["run_credits"] == 2


@pytest.mark.asyncio
async def test_each_run_uses_a_search_and_the_third_is_refused(client, completed_profile, mock_execute_campaign_run):
    campaign_id = await new_campaign(client)

    assert (await start_run(client, campaign_id)).status_code == 202
    assert await balance(client) == 1
    assert (await start_run(client, campaign_id)).status_code == 202
    assert await balance(client) == 0

    refused = await start_run(client, campaign_id)
    assert refused.status_code == 402
    assert refused.json()["error"]["code"] == "NO_CREDITS"
    assert len(mock_execute_campaign_run) == 2  # nothing was started for the refused one
    assert await balance(client) == 0


@pytest.mark.asyncio
async def test_accounts_without_a_counter_are_unlimited(client, fake_db, mock_execute_campaign_run):
    # An account created before free searches existed: no run_credits field.
    now = datetime.now(UTC)
    await fake_db.users.insert_one({
        "supabase_user_id": TEST_USER.supabase_user_id, "email": TEST_USER.email, "role": "admin",
        **COMPLETE_PROFILE, "created_at": now, "updated_at": now,
    })
    assert (await client.get("/api/users/me")).json()["run_credits"] is None

    campaign_id = await new_campaign(client)
    for _ in range(4):
        assert (await start_run(client, campaign_id)).status_code == 202
    assert "run_credits" not in await fake_db.users.find_one({})  # still no counter


@pytest.mark.asyncio
async def test_two_runs_started_at_once_cannot_both_spend_the_last_search(
    client, completed_profile, fake_db, mock_execute_campaign_run
):
    await fake_db.users.update_one({"supabase_user_id": TEST_USER.supabase_user_id}, {"$set": {"run_credits": 1}})
    campaign_id = await new_campaign(client)

    responses = await asyncio.gather(start_run(client, campaign_id), start_run(client, campaign_id))
    assert sorted(r.status_code for r in responses) == [202, 402]
    assert len(mock_execute_campaign_run) == 1
    assert await balance(client) == 0


@pytest.mark.asyncio
async def test_a_run_that_cannot_be_created_gives_the_search_back(
    client, completed_profile, mock_execute_campaign_run, monkeypatch
):
    campaign_id = await new_campaign(client)

    async def broken(*args, **kwargs):
        raise RuntimeError("database hiccup")

    monkeypatch.setattr(run_service, "create_run", broken)
    with pytest.raises(RuntimeError):
        await start_run(client, campaign_id)
    assert await balance(client) == 2


@pytest.mark.asyncio
async def test_the_run_remembers_it_was_charged(client, completed_profile, fake_db, mock_execute_campaign_run):
    campaign_id = await new_campaign(client)
    await start_run(client, campaign_id)
    run = await fake_db.workflow_runs.find_one({})
    assert run["credit_charged"] is True and run["credit_refunded"] is False


# --- refunds when a run fails or finds nothing --------------------------------------

@pytest.fixture
def sync_db(monkeypatch):
    db = mongomock.MongoClient()["t"]
    monkeypatch.setattr(pipeline_service, "_sync_db", db)
    return db


ONE_CREATOR = [{
    "handle": "vanimir", "name": "Vani Mir", "followers": 50000, "niche": "fashion", "bio": None,
    "location": "India", "score": 8.0, "reasoning": "Good fit.",
    "email": {"subject": "Hi", "body": "Hello\n\nBest regards,\n\n[Your Name]"},
}]


def run_with_workflow(sync_db, monkeypatch, workflow, user_id="u1", charged=True, credits=1):
    monkeypatch.setattr(pipeline_service, "run_campaign_workflow", workflow)

    user = {"supabase_user_id": user_id, "name": "Test User"}
    if credits is not None:
        user["run_credits"] = credits
    sync_db.users.insert_one(user)
    campaign_id = sync_db.campaigns.insert_one({"user_id": user_id, "status": "draft"}).inserted_id
    run_id = sync_db.workflow_runs.insert_one(
        {"status": "queued", "credit_charged": charged, "credit_refunded": False}
    ).inserted_id
    config = {"campaign_id": str(campaign_id), "user_id": user_id, "category": "c", "platform": "instagram",
              "country": "India", "min_followers": 1, "max_followers": 10}
    pipeline_service.execute_campaign_run(str(run_id), config)
    return sync_db.workflow_runs.find_one({"_id": run_id}), sync_db.users.find_one({"supabase_user_id": user_id})


def failing(campaign, on_stage=None):
    raise RuntimeError("Serper search failed (HTTP 503): unavailable")


def finding_one_creator(campaign, on_stage=None):
    return ONE_CREATOR


def finding_nothing(campaign, on_stage=None):
    return []


def test_a_failed_run_refunds_the_search_exactly_once(sync_db, monkeypatch):
    run, user = run_with_workflow(sync_db, monkeypatch, failing, credits=0)
    assert run["status"] == "failed"
    assert run["credit_refunded"] is True
    assert user["run_credits"] == 1

    pipeline_service._refund_credit(run["_id"], "u1")  # a second attempt must do nothing
    assert sync_db.users.find_one({"supabase_user_id": "u1"})["run_credits"] == 1


def test_a_successful_run_keeps_the_search_spent(sync_db, monkeypatch):
    run, user = run_with_workflow(sync_db, monkeypatch, finding_one_creator, credits=0)
    assert run["status"] == "completed"
    assert run["result_summary"]["refunded"] is False
    assert user["run_credits"] == 0


def test_a_run_that_finds_no_creators_is_not_charged(sync_db, monkeypatch):
    run, user = run_with_workflow(sync_db, monkeypatch, finding_nothing, credits=0)
    assert run["status"] == "completed"
    assert run["result_summary"]["discovered_count"] == 0
    assert run["result_summary"]["refunded"] is True
    assert user["run_credits"] == 1


def test_a_failed_run_on_an_unlimited_account_does_not_invent_a_counter(sync_db, monkeypatch):
    run, user = run_with_workflow(sync_db, monkeypatch, failing, charged=False, credits=None)
    assert run["status"] == "failed"
    assert "run_credits" not in user


# --- topping up (the script you use after someone pays) ----------------------------

@pytest.fixture
def users_db():
    db = mongomock.MongoClient()["t"]
    db.users.insert_one({"email": "ann@example.com", "run_credits": 0})
    db.users.insert_one({"email": "old@example.com"})  # unlimited
    return db


def test_add_credits(users_db):
    assert grant_credits.add_credits(users_db, "ann@example.com", 10)["run_credits"] == 10
    assert grant_credits.add_credits(users_db, "ANN@Example.com", 5)["run_credits"] == 15  # case-insensitive


def test_add_credits_rejects_bad_requests(users_db):
    with pytest.raises(LookupError):
        grant_credits.add_credits(users_db, "nobody@example.com", 5)
    with pytest.raises(ValueError):
        grant_credits.add_credits(users_db, "ann@example.com", 0)
    with pytest.raises(ValueError):  # would quietly turn an unlimited account into a metered one
        grant_credits.add_credits(users_db, "old@example.com", 5)


def test_set_unlimited_removes_the_counter(users_db):
    user = grant_credits.set_unlimited(users_db, "ann@example.com")
    assert "run_credits" not in user
    assert grant_credits.describe(user).endswith("unlimited")