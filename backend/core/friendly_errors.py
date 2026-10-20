# File path: backend/core/friendly_errors.py
"""
Turns the raw exception from a failed campaign run into a short,
plain-English message a person can act on.

The full technical error is always logged server-side (see
services/pipeline_service.py); only this friendly text is stored on the run
and shown in the website. Rules are checked in order, most specific first, by
looking for telltale phrases in the exception and anything it was raised from.

The search pipeline's only outside service is Serper, and pipeline/search.py
always puts "Serper" and the HTTP status in its error messages, which is what
the first rules look for.
"""

import re

SEARCH_KEY_OR_CREDITS = (
    "The search service (Serper) refused the request: its API key is wrong or its "
    "credits have run out. Check the key and your balance at serper.dev, then try again."
)
SEARCH_BUSY = (
    "The search service is limiting requests right now. Wait a minute, then run the "
    "pipeline again."
)
SEARCH_DOWN = (
    "The search service is having problems right now. Please try again in a few minutes."
)
DATABASE = (
    "Couldn't reach the database. Check the MongoDB connection and the "
    "Atlas IP allow list, then try again."
)
NETWORK = (
    "Couldn't reach an outside service (the connection timed out). Check "
    "the server's internet connection and try again — a retry often works."
)
DEFAULT = (
    "Something went wrong while running the pipeline. Please try again. If "
    "it keeps happening, check the server logs for details."
)


def _error_text(exc: BaseException) -> str:
    """Lower-cased text of the exception and the errors it was raised from."""
    parts, seen, current = [], set(), exc
    for _ in range(6):
        if current is None or id(current) in seen:
            break
        seen.add(id(current))
        parts.append(f"{type(current).__name__}: {current}")
        current = current.__cause__ or current.__context__
    return " | ".join(parts).lower()


def _has(text: str, *needles: str) -> bool:
    return any(n in text for n in needles)


def _status(text: str, code: int) -> bool:
    # Word-boundary match so an id like "6ac37429cf..." doesn't read as a 429.
    return re.search(rf"\b{code}\b", text) is not None


def explain_run_error(exc: BaseException) -> str:
    text = _error_text(exc)

    if "serper" in text:
        if _has(text, "credit", "api key", "unauthorized", "forbidden") or _status(text, 401) or _status(text, 403):
            return SEARCH_KEY_OR_CREDITS
        if _has(text, "rate limit", "too many requests") or _status(text, 429):
            return SEARCH_BUSY
        if re.search(r"\bhttp 5\d\d\b", text):
            return SEARCH_DOWN
        # "could not be reached ... timed out" falls through to the network rule.

    if _has(text, "serverselectiontimeout", "autoreconnect", "mongodb", "pymongo"):
        return DATABASE

    if _has(
        text,
        "timed out", "timeout", "handshake", "connection error", "connection refused",
        "connecterror", "getaddrinfo", "name or service not known",
        "network is unreachable", "temporary failure in name resolution",
    ):
        return NETWORK

    return DEFAULT