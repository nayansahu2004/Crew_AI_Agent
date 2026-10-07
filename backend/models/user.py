"""Shape of a document in the `users` collection."""

from datetime import datetime

from pydantic import BaseModel, Field


class UserModel(BaseModel):
    supabase_user_id: str
    email: str
    name: str | None = None
    company_name: str | None = None
    role: str = "admin"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)