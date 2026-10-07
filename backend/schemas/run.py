"""API request/response contracts for the /api/runs routes."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class RunCreateResponse(BaseModel):
    """Immediate response for POST /api/campaigns/{id}/runs -- returned
    right away, before the background workflow has actually finished."""
    run_id: str
    status: str


class RunStatusResponse(BaseModel):
    """Response for GET /api/runs/{run_id}. Designed for polling -- the
    frontend calls this repeatedly to show live-ish progress."""
    run_id: str
    campaign_id: str
    status: str
    current_stage: str | None
    started_at: datetime | None
    completed_at: datetime | None
    error: str | None
    result_summary: dict[str, Any]


class RunListItem(BaseModel):
    """Slimmer shape for GET /api/campaigns/{id}/runs (a list of past
    runs) -- no need to repeat the full result_summary for every row."""
    run_id: str
    status: str
    current_stage: str | None
    started_at: datetime | None
    completed_at: datetime | None