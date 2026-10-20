# File path: backend/test/test_pipeline_service.py
"""Saving a pipeline run's creators to the database."""

import mongomock
import pytest

from backend.services import pipeline_service as service

SENDER = {"supabase_user_id": "u1", "name": "Nayan Kumar Sahu", "job_title": "Founder | Talent Director",
          "company_name": "Arista Management", "phone": "+91 72055 40108"}


def creator(handle="vanimir", **overrides):
    values = {
        "handle": handle, "name": "Vani Mir", "followers": 96_000, "niche": "fashion", "bio": "Fashion creator",
        "location": "India", "score": 8.5, "reasoning": "96K followers, inside your range; bio mentions fashion.",
        "email": {"subject": "Collab", "body": "Hi Vani,\n\nMy name is [Your Name] from [Agency Name].\n\nBest regards,\n\n[Your Name]\n[Agency Name]"},
    }
    values.update(overrides)
    return values


@pytest.fixture
def db(monkeypatch):
    database = mongomock.MongoClient()["t"]
    monkeypatch.setattr(service, "_sync_db", database)
    database.users.insert_one(dict(SENDER, run_credits=2))
    return database


def run(db, monkeypatch, creators, on_stage_calls=None):
    def fake(campaign, on_stage=None):
        for stage in ("review", "outreach"):
            if on_stage:
                on_stage(stage)
            if on_stage_calls is not None:
                on_stage_calls.append(stage)
        if isinstance(creators, Exception):
            raise creators
        return creators

    monkeypatch.setattr(service, "run_campaign_workflow", fake)
    campaign_id = (db.campaigns.find_one() or {}).get("_id") or db.campaigns.insert_one({"user_id": "u1", "status": "draft"}).inserted_id
    run_id = db.workflow_runs.insert_one({"status": "queued", "credit_charged": True, "credit_refunded": False}).inserted_id
    service.execute_campaign_run(str(run_id), {
        "campaign_id": str(campaign_id), "user_id": "u1", "platform": "instagram", "category": "fashion",
        "country": "India", "min_followers": 20_000, "max_followers": 100_000,
    })
    return db.workflow_runs.find_one({"_id": run_id})


def test_creators_are_saved_whole_with_score_and_signed_email(db, monkeypatch):
    run_doc = run(db, monkeypatch, [creator()])
    saved = db.influencers.find_one({"username": "@vanimir"})

    assert run_doc["status"] == "completed" and run_doc["current_stage"] == "completed"
    assert run_doc["result_summary"] == {"discovered_count": 1, "reviewed_count": 1, "emails_drafted": 1, "refunded": False}
    assert (saved["name"], saved["followers"], saved["location"], saved["bio"]) == ("Vani Mir", 96_000, "India", "Fashion creator")
    assert saved["category"] == ["fashion"] and saved["platform"] == "instagram"
    assert saved["profile_url"] == "https://www.instagram.com/vanimir/"
    assert saved["review_score"] == 8.5 and saved["review_status"] == "reviewed" and saved["review_reasoning"]
    assert saved["outreach_status"] == "drafted" and saved["discovery_source"] == "serper" and saved["email"] is None

    body = saved["email_draft"]["body"]
    assert "My name is Nayan from Arista Management." in body
    assert body.endswith("Nayan Kumar Sahu\nFounder | Talent Director\nArista Management\nPh: +91 72055 40108")


def test_an_unknown_follower_count_is_stored_as_unknown_not_zero(db, monkeypatch):
    run(db, monkeypatch, [creator(followers=None)])
    assert db.influencers.find_one({"username": "@vanimir"})["followers"] is None


def test_the_campaign_and_progress_follow_the_run(db, monkeypatch):
    stages = []
    run(db, monkeypatch, [creator()], on_stage_calls=stages)
    assert stages == ["review", "outreach"]
    assert db.campaigns.find_one()["status"] == "completed"


def test_running_again_refreshes_creators_instead_of_duplicating(db, monkeypatch):
    run(db, monkeypatch, [creator(score=6.0, followers=90_000)])
    run(db, monkeypatch, [creator(score=9.0, followers=96_000)])
    assert db.influencers.count_documents({}) == 1
    saved = db.influencers.find_one({})
    assert saved["review_score"] == 9.0 and saved["followers"] == 96_000


def test_a_creator_who_was_sent_an_email_keeps_status_and_the_sent_email(db, monkeypatch):
    run(db, monkeypatch, [creator()])
    sent_body = db.influencers.find_one({})["email_draft"]["body"]
    db.influencers.update_one({}, {"$set": {"outreach_status": "sent", "email": "vani@example.com"}})

    second = run(db, monkeypatch, [creator(email={"subject": "New", "body": "Different text"})])
    saved = db.influencers.find_one({})
    assert saved["outreach_status"] == "sent"
    assert saved["email_draft"]["body"] == sent_body            # what was actually sent is not overwritten
    assert saved["email"] == "vani@example.com"                 # the address the user typed survives
    assert second["result_summary"]["emails_drafted"] == 0


def test_a_run_that_finds_nothing_is_completed_and_refunded(db, monkeypatch):
    run_doc = run(db, monkeypatch, [])
    assert run_doc["status"] == "completed" and run_doc["result_summary"]["discovered_count"] == 0
    assert run_doc["result_summary"]["refunded"] is True and run_doc["credit_refunded"] is True
    assert db.users.find_one({})["run_credits"] == 3
    assert db.influencers.count_documents({}) == 0


def test_a_failing_search_marks_the_run_failed_with_a_plain_message(db, monkeypatch):
    from backend.pipeline.search import SearchError
    run_doc = run(db, monkeypatch, SearchError("Serper search failed (HTTP 400): Not enough credits"))
    assert run_doc["status"] == "failed"
    assert "credits have run out" in run_doc["error"] and "400" not in run_doc["error"]
    assert db.campaigns.find_one()["status"] == "failed"
    assert db.users.find_one({})["run_credits"] == 3                 # the search is given back