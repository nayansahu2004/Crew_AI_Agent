# File path: backend/test/conftest.py
"""
Shared pytest fixtures for the API test suite.

IMPORTANT: the dummy env vars below are set BEFORE any `backend.*` module
is imported anywhere in this file. backend.core.config.Settings() runs
at import time and requires several env vars to be present -- setting
them here first means the test suite never depends on your real .env
file, and never touches your real Gemini/Serper/Mongo credentials.
"""

import os

os.environ.setdefault("SUPABASE_URL", "https://test-project.supabase.co")
os.environ.setdefault("MONGODB_URI", "mongodb://localhost:27017")
os.environ.setdefault("SERPER_API_KEY", "test-serper-key")
os.environ.setdefault("FIRECRAWL_API_KEY", "test-firecrawl-key")
os.environ.setdefault("TAVILY_API_KEY", "test-tavily-key")

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from mongomock_motor import AsyncMongoMockClient

from backend.core import database as database_module
from backend.core.security import AuthenticatedUser, get_current_user

TEST_USER = AuthenticatedUser(supabase_user_id="test-user-1", email="test@example.com")
OTHER_USER = AuthenticatedUser(supabase_user_id="test-user-2", email="other@example.com")


@pytest.fixture
def fake_db():
    """A fresh in-memory Mongo-like database per test -- no state leaks
    between tests, no real MongoDB needed."""
    client = AsyncMongoMockClient()
    return client["test_db"]


@pytest.fixture
def mock_execute_campaign_run(monkeypatch):
    """Replaces the background-task function POST /api/campaigns/{id}/runs
    schedules, so starting a run never imports CrewAI, never calls
    Gemini/Ollama, and never touches crew_service.py's real pymongo
    client. Returns the list of (run_id, campaign_config) calls made, so
    tests can assert on what the route passed through."""
    calls = []

    def fake_execute_campaign_run(run_id: str, campaign: dict) -> None:
        calls.append((run_id, campaign))

    monkeypatch.setattr(
        "backend.api.runs.execute_campaign_run", fake_execute_campaign_run
    )
    return calls


@pytest_asyncio.fixture
async def client(fake_db):
    """An httpx AsyncClient wired directly to the FastAPI app (no real
    server/socket). Database is overridden to the in-memory fake; auth is
    overridden to always return TEST_USER unless a test changes it."""
    from backend.main import app

    app.dependency_overrides[database_module.get_database] = lambda: fake_db
    app.dependency_overrides[get_current_user] = lambda: TEST_USER

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def unauthenticated_client(fake_db):
    """Same as `client`, but WITHOUT overriding auth -- requests go
    through the real get_current_user, so missing/invalid tokens are
    rejected exactly as they would be in production. Used for testing
    401 behavior specifically."""
    from backend.main import app

    app.dependency_overrides[database_module.get_database] = lambda: fake_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()