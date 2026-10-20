# File path: backend/test/test_gmail.py
"""
Gmail connection + sending. Google is replaced by FakeGoogle (an
httpx.MockTransport), so nothing here touches the network or a real mailbox.
"""

import asyncio
import base64
import json
from datetime import UTC, datetime
from email import message_from_bytes, policy
from urllib.parse import parse_qs, urlparse

import httpx
import jwt
import pytest
from cryptography.fernet import Fernet, InvalidToken

from backend.core import crypto
from backend.core.config import settings
from backend.core.security import get_current_user
from backend.services import google_client
from backend.test.conftest import OTHER_USER, TEST_USER

COMPOSE = google_client.COMPOSE_SCOPE


class FakeGoogle:
    def __init__(self):
        self.requests: list[httpx.Request] = []
        self.granted_scope = f"openid email {COMPOSE}"
        self.refresh_token = "refresh-secret-1"
        self.email = "nayan@gmail.com"
        self.refresh_fails = False
        self.draft_send_not_found = False
        self.send_error: int | None = None

    def handler(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        url = str(request.url)

        if url == google_client.GOOGLE_TOKEN_URL:
            form = parse_qs(request.content.decode())
            if form["grant_type"][0] == "authorization_code":
                id_token = jwt.encode({"email": self.email, "email_verified": True}, "k", algorithm="HS256")
                return httpx.Response(200, json={
                    "access_token": "access-1", "refresh_token": self.refresh_token,
                    "scope": self.granted_scope, "id_token": id_token,
                })
            if self.refresh_fails:
                return httpx.Response(400, json={"error": "invalid_grant"})
            return httpx.Response(200, json={"access_token": "access-2"})

        if url == google_client.GOOGLE_REVOKE_URL:
            return httpx.Response(200, json={})
        if url.endswith("/drafts/send"):
            if self.draft_send_not_found:
                return httpx.Response(404, json={"error": {"message": "Requested entity was not found."}})
            return httpx.Response(200, json={"id": "sent-from-draft", "threadId": "thread-1"})
        if url.endswith("/drafts"):
            return httpx.Response(200, json={"id": "draft-1", "message": {"id": "m1"}})
        if url.endswith("/messages/send"):
            if self.send_error:
                return httpx.Response(self.send_error, json={"error": {"message": "limit", "errors": [{"reason": "rateLimitExceeded"}]}})
            return httpx.Response(200, json={"id": "sent-1", "threadId": "thread-1"})
        return httpx.Response(404, json={})

    def calls(self, suffix: str) -> list[httpx.Request]:
        return [r for r in self.requests if str(r.url).endswith(suffix)]

    def sent_message(self, suffix: str = "/messages/send"):
        """The most recent outgoing email, parsed."""
        body = json.loads(self.calls(suffix)[-1].content)
        raw = body["raw"] if "raw" in body else body["message"]["raw"]
        return message_from_bytes(base64.urlsafe_b64decode(raw), policy=policy.default)


@pytest.fixture
def fake_google(monkeypatch):
    fake = FakeGoogle()
    monkeypatch.setattr(google_client, "_transport", httpx.MockTransport(fake.handler))
    return fake


async def connect(client):
    auth_url = (await client.get("/api/gmail/connect")).json()["auth_url"]
    state = parse_qs(urlparse(auth_url).query)["state"][0]
    return await client.get("/api/gmail/callback", params={"code": "auth-code", "state": state})


async def make_influencer(fake_db, user_id=TEST_USER.supabase_user_id, **overrides) -> str:
    now = datetime.now(UTC)
    doc = {
        "campaign_id": "c1", "user_id": user_id, "name": "Vani Mir", "username": "@vanimir",
        "platform": "instagram", "followers": 96000, "category": [], "location": "India",
        "profile_url": None, "email": None, "bio": None, "discovery_source": "serper",
        "review_score": 8.0, "review_reasoning": "Good fit.", "review_status": "reviewed",
        "outreach_status": "drafted",
        "email_draft": {"subject": "Collab", "body": "Hi Vani,\n\nLet's work together."},
        "created_at": now, "updated_at": now,
    }
    doc.update(overrides)
    return str((await fake_db.influencers.insert_one(doc)).inserted_id)


async def set_recipient(client, influencer_id, email="vani@example.com"):
    response = await client.patch(f"/api/influencers/{influencer_id}", json={"email": email})
    assert response.status_code == 200
    return response


# --- connecting -----------------------------------------------------------------

@pytest.mark.asyncio
async def test_status_when_nothing_is_connected(client):
    body = (await client.get("/api/gmail/status")).json()
    assert body["configured"] is True
    assert body["connected"] is False
    assert body["email"] is None


@pytest.mark.asyncio
async def test_not_configured_is_reported_and_connect_is_refused(client, monkeypatch):
    monkeypatch.setattr(settings, "google_client_id", None)
    assert (await client.get("/api/gmail/status")).json()["configured"] is False
    response = await client.get("/api/gmail/connect")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "GMAIL_NOT_CONFIGURED"


@pytest.mark.asyncio
async def test_connect_returns_the_google_consent_url(client):
    url = (await client.get("/api/gmail/connect")).json()["auth_url"]
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    assert parsed.netloc == "accounts.google.com"
    assert query["client_id"] == [settings.google_client_id]
    assert query["redirect_uri"] == [settings.google_redirect_uri]
    assert COMPOSE in query["scope"][0]
    assert query["access_type"] == ["offline"]
    assert query["state"][0]


@pytest.mark.asyncio
async def test_callback_connects_and_encrypts_the_refresh_token(client, fake_google, fake_db):
    response = await connect(client)
    assert response.status_code == 303
    assert response.headers["location"].endswith("/settings?gmail=connected")

    status = (await client.get("/api/gmail/status")).json()
    assert status["connected"] is True
    assert status["email"] == "nayan@gmail.com"

    stored = await fake_db.gmail_connections.find_one({"supabase_user_id": TEST_USER.supabase_user_id})
    assert stored["refresh_token_enc"] != "refresh-secret-1"
    assert crypto.decrypt_secret(stored["refresh_token_enc"]) == "refresh-secret-1"
    assert "refresh-secret-1" not in str(stored)


@pytest.mark.asyncio
async def test_callback_rejects_a_forged_state(client, fake_google):
    response = await client.get("/api/gmail/callback", params={"code": "x", "state": "forged.value"})
    assert response.status_code == 303
    assert "reason=invalid_state" in response.headers["location"]
    assert (await client.get("/api/gmail/status")).json()["connected"] is False
    assert fake_google.requests == []  # never even reached Google


@pytest.mark.asyncio
async def test_callback_rejects_an_expired_state(client, fake_google):
    state = crypto.sign_state(TEST_USER.supabase_user_id, ttl_seconds=-10)
    response = await client.get("/api/gmail/callback", params={"code": "x", "state": state})
    assert "reason=invalid_state" in response.headers["location"]


@pytest.mark.asyncio
async def test_state_cannot_be_swapped_to_another_user():
    a = crypto.sign_state("user-a")
    b = crypto.sign_state("user-b")
    spliced = b.split(".")[0] + "." + a.split(".")[1]
    assert crypto.verify_state(a) == "user-a"
    assert crypto.verify_state(spliced) is None


@pytest.mark.asyncio
async def test_callback_requires_the_compose_permission(client, fake_google):
    fake_google.granted_scope = "openid email"  # the user unticked the Gmail box
    response = await connect(client)
    assert "reason=permission_denied" in response.headers["location"]
    assert (await client.get("/api/gmail/status")).json()["connected"] is False


@pytest.mark.asyncio
async def test_callback_handles_the_user_cancelling(client):
    response = await client.get("/api/gmail/callback", params={"error": "access_denied"})
    assert response.status_code == 303
    assert "reason=access_denied" in response.headers["location"]


@pytest.mark.asyncio
async def test_disconnect_revokes_and_removes_and_is_idempotent(client, fake_google):
    await connect(client)
    assert (await client.delete("/api/gmail/connection")).status_code == 204
    assert len(fake_google.calls("/revoke")) == 1
    assert (await client.get("/api/gmail/status")).json()["connected"] is False
    assert (await client.delete("/api/gmail/connection")).status_code == 204


# --- saving drafts --------------------------------------------------------------

@pytest.mark.asyncio
async def test_save_draft_needs_a_recipient(client, fake_google, fake_db):
    await connect(client)
    influencer_id = await make_influencer(fake_db)
    response = await client.post(f"/api/influencers/{influencer_id}/gmail/draft")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "RECIPIENT_MISSING"
    assert fake_google.calls("/drafts") == []


@pytest.mark.asyncio
async def test_save_draft_creates_a_gmail_draft(client, fake_google, fake_db, completed_profile):
    await connect(client)
    influencer_id = await make_influencer(fake_db)
    await set_recipient(client, influencer_id)

    response = await client.post(f"/api/influencers/{influencer_id}/gmail/draft")
    assert response.status_code == 200
    assert response.json()["gmail"]["draft_id"] == "draft-1"
    assert response.json()["outreach_status"] == "drafted"  # not sent

    message = fake_google.sent_message("/drafts")
    assert message["To"] == "vani@example.com"
    assert message["Subject"] == "Collab"
    assert "nayan@gmail.com" in message["From"] and "Test User" in message["From"]
    assert "work together" in message.get_content()
    assert fake_google.calls("/messages/send") == []


# --- sending --------------------------------------------------------------------

@pytest.mark.asyncio
async def test_send_email_sends_and_marks_sent(client, fake_google, fake_db):
    await connect(client)
    influencer_id = await make_influencer(fake_db)
    await set_recipient(client, influencer_id)

    response = await client.post(f"/api/influencers/{influencer_id}/gmail/send")
    assert response.status_code == 200
    body = response.json()
    assert body["outreach_status"] == "sent"
    assert body["gmail"]["message_id"] == "sent-1"
    assert body["gmail"]["sent_from"] == "nayan@gmail.com"
    assert body["gmail"]["sent_at"]

    again = await client.post(f"/api/influencers/{influencer_id}/gmail/send")
    assert again.status_code == 409
    assert again.json()["error"]["code"] == "ALREADY_SENT"
    assert len(fake_google.calls("/messages/send")) == 1


@pytest.mark.asyncio
async def test_send_uses_the_saved_gmail_draft(client, fake_google, fake_db):
    await connect(client)
    influencer_id = await make_influencer(fake_db)
    await set_recipient(client, influencer_id)
    await client.post(f"/api/influencers/{influencer_id}/gmail/draft")

    response = await client.post(f"/api/influencers/{influencer_id}/gmail/send")
    assert response.json()["gmail"]["message_id"] == "sent-from-draft"
    assert len(fake_google.calls("/drafts/send")) == 1
    assert fake_google.calls("/messages/send") == []


@pytest.mark.asyncio
async def test_send_falls_back_when_the_draft_was_deleted(client, fake_google, fake_db):
    await connect(client)
    influencer_id = await make_influencer(fake_db)
    await set_recipient(client, influencer_id)
    await client.post(f"/api/influencers/{influencer_id}/gmail/draft")
    fake_google.draft_send_not_found = True

    response = await client.post(f"/api/influencers/{influencer_id}/gmail/send")
    assert response.status_code == 200
    assert response.json()["gmail"]["message_id"] == "sent-1"


@pytest.mark.asyncio
async def test_send_without_a_connected_gmail(client, fake_google, fake_db):
    influencer_id = await make_influencer(fake_db)
    await set_recipient(client, influencer_id)

    response = await client.post(f"/api/influencers/{influencer_id}/gmail/send")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GMAIL_NOT_CONNECTED"
    doc = await fake_db.influencers.find_one({})
    assert doc["outreach_status"] == "drafted"
    assert not doc.get("gmail_sending_at")  # the lock was released


@pytest.mark.asyncio
async def test_expired_connection_asks_to_reconnect(client, fake_google, fake_db):
    await connect(client)
    influencer_id = await make_influencer(fake_db)
    await set_recipient(client, influencer_id)
    fake_google.refresh_fails = True  # Google says the token was revoked/expired

    response = await client.post(f"/api/influencers/{influencer_id}/gmail/send")
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "GMAIL_RECONNECT_REQUIRED"

    status = (await client.get("/api/gmail/status")).json()
    assert status["connected"] is False
    assert status["needs_reconnect"] is True
    assert fake_google.calls("/messages/send") == []


@pytest.mark.asyncio
async def test_a_gmail_rate_limit_is_explained_and_does_not_lock_the_email(client, fake_google, fake_db):
    await connect(client)
    influencer_id = await make_influencer(fake_db)
    await set_recipient(client, influencer_id)

    fake_google.send_error = 429
    failed = await client.post(f"/api/influencers/{influencer_id}/gmail/send")
    assert failed.status_code == 429
    assert failed.json()["error"]["code"] == "GMAIL_RATE_LIMITED"

    fake_google.send_error = None  # a retry must be possible
    retried = await client.post(f"/api/influencers/{influencer_id}/gmail/send")
    assert retried.status_code == 200
    assert retried.json()["outreach_status"] == "sent"


@pytest.mark.asyncio
async def test_daily_send_limit(client, fake_google, fake_db, monkeypatch):
    monkeypatch.setattr(settings, "gmail_daily_send_limit", 1)
    await connect(client)
    first = await make_influencer(fake_db, username="@one")
    second = await make_influencer(fake_db, username="@two", name="Second")
    await set_recipient(client, first, "one@example.com")
    await set_recipient(client, second, "two@example.com")

    assert (await client.post(f"/api/influencers/{first}/gmail/send")).status_code == 200
    blocked = await client.post(f"/api/influencers/{second}/gmail/send")
    assert blocked.status_code == 429
    assert blocked.json()["error"]["code"] == "SEND_LIMIT_REACHED"
    assert len(fake_google.calls("/messages/send")) == 1


@pytest.mark.asyncio
async def test_cannot_send_another_users_creator(client, fake_google, fake_db):
    await connect(client)
    theirs = await make_influencer(fake_db, user_id=OTHER_USER.supabase_user_id, email="vani@example.com")

    response = await client.post(f"/api/influencers/{theirs}/gmail/send")
    assert response.status_code == 403
    assert fake_google.calls("/messages/send") == []


@pytest.mark.asyncio
async def test_double_click_sends_only_one_email(client, fake_google, fake_db):
    await connect(client)
    influencer_id = await make_influencer(fake_db)
    await set_recipient(client, influencer_id)

    responses = await asyncio.gather(
        client.post(f"/api/influencers/{influencer_id}/gmail/send"),
        client.post(f"/api/influencers/{influencer_id}/gmail/send"),
    )
    assert sorted(r.status_code for r in responses) == [200, 409]
    assert len(fake_google.calls("/messages/send")) == 1


@pytest.mark.asyncio
async def test_a_newline_in_the_subject_cannot_inject_headers(client, fake_google, fake_db):
    await connect(client)
    influencer_id = await make_influencer(
        fake_db, email_draft={"subject": "Hello\nBcc: evil@example.com", "body": "Hi"}
    )
    await set_recipient(client, influencer_id)

    assert (await client.post(f"/api/influencers/{influencer_id}/gmail/send")).status_code == 200
    message = fake_google.sent_message()
    assert message["Bcc"] is None
    assert message["Subject"] == "Hello Bcc: evil@example.com"


# --- recipient address ----------------------------------------------------------

@pytest.mark.asyncio
async def test_recipient_email_is_validated_and_tidied(client, fake_db):
    influencer_id = await make_influencer(fake_db)

    ok = await client.patch(f"/api/influencers/{influencer_id}", json={"email": "  Vani@Example.COM "})
    assert ok.json()["email"] == "vani@example.com"

    for bad in ["not an email", "a@b.co\nBcc: x@y.com", "a@b", "two@x.com, three@x.com"]:
        response = await client.patch(f"/api/influencers/{influencer_id}", json={"email": bad})
        assert response.status_code == 422, bad

    cleared = await client.patch(f"/api/influencers/{influencer_id}", json={"email": ""})
    assert cleared.json()["email"] is None


# --- crypto ---------------------------------------------------------------------

def test_encryption_round_trip_tamper_and_key_rotation(monkeypatch):
    token = crypto.encrypt_secret("super-secret")
    assert token != "super-secret"
    assert crypto.decrypt_secret(token) == "super-secret"

    with pytest.raises(InvalidToken):
        crypto.decrypt_secret(token[:-4] + "AAAA")

    # Rotating: add a new key in front. The old token still decrypts.
    new_key = Fernet.generate_key().decode()
    monkeypatch.setattr(settings, "token_encryption_key", f"{new_key},{settings.token_encryption_key}")
    assert crypto.decrypt_secret(token) == "super-secret"