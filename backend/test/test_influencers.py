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