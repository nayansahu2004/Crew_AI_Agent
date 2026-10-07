# File path: backend/test/test_campaigns.py
import pytest

from backend.core.security import get_current_user
from backend.test.conftest import OTHER_USER

VALID_CAMPAIGN_BODY = {
    "name": "Test Campaign",
    "description": "A campaign for testing",
    "category": "fashion",
    "target_country": "India",
    "min_followers": 20000,
    "max_followers": 500000,
    "platform": "instagram",
}


@pytest.mark.asyncio
async def test_create_campaign(client):
    response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Test Campaign"
    assert body["status"] == "draft"
    assert "id" in body


@pytest.mark.asyncio
async def test_list_campaigns_returns_only_own(client):
    await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)

    response = await client.get("/api/campaigns")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Test Campaign"


@pytest.mark.asyncio
async def test_get_campaign_by_id(client):
    create_response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    campaign_id = create_response.json()["id"]

    response = await client.get(f"/api/campaigns/{campaign_id}")
    assert response.status_code == 200
    assert response.json()["id"] == campaign_id


@pytest.mark.asyncio
async def test_get_campaign_invalid_id_returns_404(client):
    response = await client.get("/api/campaigns/not-a-real-id")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CAMPAIGN_NOT_FOUND"


@pytest.mark.asyncio
async def test_get_campaign_wellformed_but_nonexistent_id_returns_404(client):
    # A syntactically valid ObjectId that simply doesn't exist.
    response = await client.get("/api/campaigns/" + "a" * 24)
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "CAMPAIGN_NOT_FOUND"


@pytest.mark.asyncio
async def test_other_users_campaign_returns_403(client):
    from backend.main import app  # local import: app already created by fixture

    create_response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    campaign_id = create_response.json()["id"]

    # Switch the authenticated identity for this request only.
    app.dependency_overrides[get_current_user] = lambda: OTHER_USER
    response = await client.get(f"/api/campaigns/{campaign_id}")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "CAMPAIGN_FORBIDDEN"


@pytest.mark.asyncio
async def test_update_campaign(client):
    create_response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    campaign_id = create_response.json()["id"]

    response = await client.patch(
        f"/api/campaigns/{campaign_id}", json={"status": "queued"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "queued"


@pytest.mark.asyncio
async def test_delete_campaign(client):
    create_response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    campaign_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/campaigns/{campaign_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/campaigns/{campaign_id}")
    assert get_response.status_code == 404