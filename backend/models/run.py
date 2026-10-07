"""Shape of a document in the `workflow_runs` collection."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class WorkflowRunModel(BaseModel):
    campaign_id: str
    user_id: str
    status: str = "queued"          # queued | running | completed | failed
    current_stage: str | None = None  # discovery | review | outreach | completed
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None
    result_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)