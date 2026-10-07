"""
Shared helpers for models/. Each file in this package defines the plain
data shape stored in one MongoDB collection -- these are NOT the same as
schemas/ (API request/response contracts). A models/ change reflects a DB
shape change; a schemas/ change reflects an API contract change. Keeping
them separate means you can add an internal-only DB field without it
automatically leaking into an API response, and vice versa.
"""


def serialize_doc(doc: dict) -> dict:
    """Converts a raw MongoDB document into a plain dict safe to hand to
    a Pydantic schema: turns ObjectId -> str and renames _id -> id.

    Use this at the boundary between database.py/services and schemas --
    routes and services should never pass raw Mongo documents (with a
    real ObjectId in them) directly into a Pydantic response model.
    """
    if doc is None:
        return doc
    doc = dict(doc)
    if "_id" in doc:
        doc["id"] = str(doc.pop("_id"))
    return doc