# File path: backend/test/test_auth.py
"""
Tests the get_current_user dependency's rejection paths, using the REAL
dependency (unauthenticated_client doesn't override it) -- only the
database is faked.
"""

import pytest


@pytest.mark.asyncio
async def test_missing_authorization_header_returns_401(unauthenticated_client):
    response = await unauthenticated_client.get("/api/users/me")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "UNAUTHORIZED"


@pytest.mark.asyncio
async def test_malformed_authorization_header_returns_401(unauthenticated_client):
    response = await unauthenticated_client.get(
        "/api/users/me", headers={"Authorization": "NotBearer sometoken"}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_garbage_token_returns_401(unauthenticated_client):
    response = await unauthenticated_client.get(
        "/api/users/me", headers={"Authorization": "Bearer not-a-real-jwt"}
    )
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "UNAUTHORIZED"