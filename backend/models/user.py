# File path: backend/models/user.py
"""Shape of a document in the `users` collection."""

from datetime import datetime

from pydantic import BaseModel, Field

# Collected at sign-up / first sign-in. All four are needed before a user
# can run a campaign, because they're used to sign the outreach emails.
REQUIRED_PROFILE_FIELDS = ("name", "job_title", "company_name", "phone")


class UserModel(BaseModel):
    supabase_user_id: str
    email: str
    name: str | None = None
    job_title: str | None = None
    company_name: str | None = None
    phone: str | None = None
    role: str = "admin"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


def is_profile_complete(doc: dict) -> bool:
    """True when every required profile field has real (non-blank) content."""
    return all(str(doc.get(field) or "").strip() for field in REQUIRED_PROFILE_FIELDS)