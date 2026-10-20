# File path: backend/test/test_influencers.py
import pytest

from backend.test.test_campaigns import VALID_CAMPAIGN_BODY


@pytest.mark.asyncio
async def test_list_influencers_for_new_campaign_is_empty(client):
    create_response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    campaign_id = create_response.json()["id"]

    response = await client.get(f"/api/campaigns/{campaign_id}/influencers")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_list_influencers_for_nonexistent_campaign_returns_404(client):
    response = await client.get("/api/campaigns/" + "a" * 24 + "/influencers")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_nonexistent_influencer_returns_404(client):
    response = await client.get("/api/influencers/" + "a" * 24)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "INFLUENCER_NOT_FOUND"


@pytest.mark.asyncio
async def test_a_creator_with_an_unknown_follower_count_is_listed(client, fake_db):
    from datetime import UTC, datetime

    create_response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    campaign_id = create_response.json()["id"]
    now = datetime.now(UTC)
    await fake_db.influencers.insert_one({
        "campaign_id": campaign_id, "user_id": "test-user-1", "name": "Aditi Banerjee", "username": "@aditi_banerjee",
        "platform": "instagram", "followers": None, "category": [], "location": "India", "profile_url": None,
        "email": None, "bio": None, "discovery_source": "serper", "review_score": 4.5,
        "review_reasoning": "Follower count wasn't in the search results, so check it yourself.",
        "review_status": "reviewed", "outreach_status": "drafted", "created_at": now, "updated_at": now,
    })

    response = await client.get(f"/api/campaigns/{campaign_id}/influencers")
    assert response.status_code == 200
    assert response.json()[0]["followers"] is None