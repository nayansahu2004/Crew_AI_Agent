# File path: backend/main.py
"""
FastAPI application entrypoint.

Run from the PROJECT ROOT (the folder containing backend/), not from
inside backend/, because all imports use the `backend.` prefix:

    uv run uvicorn backend.main:app --reload
"""

import logging
import re
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import campaigns, gmail, users
from backend.api.influencers import campaign_influencers_router, influencers_router
from backend.api.runs import campaign_runs_router, runs_router
from backend.core.config import settings
from backend.core.database import close_mongo_connection, connect_to_mongo
from backend.core.errors import register_exception_handlers

# --- Logging setup ---
# backend/logs/ holds THIS app's logs (requests, errors, startup/shutdown).
# backend/outputs/ (written by pipeline/workflow.py when PIPELINE_DEBUG_DUMP is on)
# holds raw search results. Keeping them in separate folders/files makes it
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


class RedactOAuthParams(logging.Filter):
    """uvicorn's access log prints the full request URL. The Google sign-in
    callback carries a one-time `code` and a `state` value in it, which
    shouldn't sit in log files, so blank them out before they're written."""

    _pattern = re.compile(r"([?&](?:code|state)=)[^&\s\"]+")

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, tuple):
            record.args = tuple(
                self._pattern.sub(r"\1[redacted]", arg) if isinstance(arg, str) else arg
                for arg in record.args
            )
        return True


logging.getLogger("uvicorn.access").addFilter(RedactOAuthParams())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: connect to MongoDB and ensure indexes exist.
    Shutdown: close the connection cleanly."""
    logger.info("CORS allowed origins: %s", settings.cors_origins_list)
    await connect_to_mongo()
    yield
    await close_mongo_connection()


app = FastAPI(
    title="Crew - Search Influencers API",
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
app.include_router(gmail.router)
app.include_router(gmail.influencer_gmail_router)


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}


@app.get("/api/health", tags=["health"])
async def api_health():
    return {"status": "ok"}