# File path: backend/test/test_users.py
import pytest

from backend.test.conftest import TEST_USER


@pytest.mark.asyncio
async def test_get_my_profile_creates_user_on_first_call(client):
    response = await client.get("/api/users/me")
    assert response.status_code == 200
    body = response.json()
    assert body["supabase_user_id"] == TEST_USER.supabase_user_id
    assert body["email"] == TEST_USER.email
    assert body["role"] == "admin"


@pytest.mark.asyncio
async def test_update_my_profile(client):
    await client.get("/api/users/me")  # ensure the profile exists first

    response = await client.post(
        "/api/users/me",
        json={"name": "Nayan", "company_name": "Test Co"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Nayan"
    assert body["company_name"] == "Test Co"