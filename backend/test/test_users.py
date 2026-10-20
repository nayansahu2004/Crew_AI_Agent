# File path: backend/test/test_users.py
import pytest

from backend.test.conftest import COMPLETE_PROFILE, TEST_USER


@pytest.mark.asyncio
async def test_get_my_profile_creates_user_on_first_call(client):
    response = await client.get("/api/users/me")
    assert response.status_code == 200
    body = response.json()
    assert body["supabase_user_id"] == TEST_USER.supabase_user_id
    assert body["email"] == TEST_USER.email
    assert body["role"] == "admin"
    # A brand-new user has no details yet, so onboarding must be required.
    assert body["profile_complete"] is False
    assert body["phone"] is None


@pytest.mark.asyncio
async def test_saving_all_details_completes_the_profile(client):
    response = await client.post("/api/users/me", json=COMPLETE_PROFILE)
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Test User"
    assert body["company_name"] == "Test Co"
    assert body["job_title"] == "Founder"
    assert body["phone"] == "+91 98765 43210"
    assert body["profile_complete"] is True


@pytest.mark.asyncio
async def test_partial_save_keeps_profile_incomplete(client):
    response = await client.post("/api/users/me", json={"name": "Test User"})
    assert response.status_code == 200
    assert response.json()["profile_complete"] is False


@pytest.mark.asyncio
async def test_partial_update_does_not_erase_other_fields(client):
    await client.post("/api/users/me", json=COMPLETE_PROFILE)
    response = await client.post("/api/users/me", json={"phone": "+91 11111 22222"})
    body = response.json()
    assert body["phone"] == "+91 11111 22222"
    assert body["name"] == "Test User"
    assert body["profile_complete"] is True


@pytest.mark.asyncio
async def test_whitespace_is_trimmed_and_collapsed(client):
    response = await client.post(
        "/api/users/me", json={**COMPLETE_PROFILE, "name": "   Nayan    Kumar  Sahu "}
    )
    assert response.json()["name"] == "Nayan Kumar Sahu"


@pytest.mark.asyncio
async def test_invalid_phone_is_rejected_with_a_readable_message(client):
    response = await client.post("/api/users/me", json={"phone": "call me"})
    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert "phone" in body["error"]["message"]
    assert "valid phone number" in body["error"]["message"]


@pytest.mark.asyncio
async def test_blank_name_is_rejected(client):
    response = await client.post("/api/users/me", json={"name": "     "})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_email_and_user_id_cannot_be_changed_through_the_body(client):
    await client.get("/api/users/me")
    response = await client.post(
        "/api/users/me",
        json={**COMPLETE_PROFILE, "email": "evil@example.com", "supabase_user_id": "someone-else"},
    )
    body = response.json()
    assert body["email"] == TEST_USER.email
    assert body["supabase_user_id"] == TEST_USER.supabase_user_id