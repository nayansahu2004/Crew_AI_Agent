# File path: backend/main.py
"""
FastAPI application entrypoint.

Run from the PROJECT ROOT (the folder containing backend/), not from
inside backend/, because all imports use the `backend.` prefix:

    uv run uvicorn backend.main:app --reload
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import campaigns, users
from backend.api.influencers import campaign_influencers_router, influencers_router
from backend.api.runs import campaign_runs_router, runs_router
from backend.core.config import settings
from backend.core.database import close_mongo_connection, connect_to_mongo
from backend.core.errors import register_exception_handlers

# --- Logging setup ---
# backend/logs/ holds THIS app's logs (requests, errors, startup/shutdown).
# backend/outputs/ (written by crew/agents.py's step_callback) holds raw
# CrewAI run artifacts. Keeping them in separate folders/files makes it
# obvious which is which when debugging a failed run vs. an API bug.
LOGS_DIR = Path(__file__).resolve().parent / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[
        logging.StreamHandler(),  # still prints to the terminal
        logging.FileHandler(LOGS_DIR / "app.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to MongoDB and ensure indexes exist.
    Shutdown: close the connection cleanly."""
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="Crew AI Influencer API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

# Routers. influencers.py and runs.py each export TWO routers (one nested
# under /api/campaigns, one standalone), so all of them are included here.
app.include_router(users.router)
app.include_router(campaigns.router)
app.include_router(campaign_influencers_router)
app.include_router(influencers_router)
app.include_router(campaign_runs_router)
app.include_router(runs_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


@app.get("/api/health", tags=["health"])
async def api_health():
    return {"status": "ok"}