# File path: backend/pipeline/search.py
"""
A small client for Serper (https://serper.dev), which returns Google search
results as JSON. This is the only outside service the pipeline uses.

The pipeline runs in a background thread, so this uses ordinary (blocking)
requests. Tests replace `_transport` with an httpx.MockTransport, so the
test suite never makes a real request.
"""

import logging
import time

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)

SERPER_URL = "https://google.serper.dev/search"
MAX_ATTEMPTS = 3

# Set by tests.
_transport: httpx.BaseTransport | None = None
_sleep = time.sleep


class SearchError(RuntimeError):
    """The search failed. The message always names Serper and the HTTP
    status, because core/friendly_errors.py reads those to explain what
    went wrong (bad key, no credits left, rate limit...)."""


def _detail(response: httpx.Response) -> str:
    try:
        body = response.json()
        if isinstance(body, dict) and body.get("message"):
            return str(body["message"])[:200]
    except ValueError:
        pass
    return response.text[:200] or "no details"


def search(query: str, *, country_code: str | None = None, num: int = 10) -> list[dict]:
    """Run one search and return Serper's `organic` results: dicts with
    title, link and snippet. Retries rate limits and server errors; gives up
    straight away on errors a retry can't fix (400/401/403: a bad key or no
    credits left)."""
    payload: dict = {"q": query, "num": num}
    if country_code:
        payload["gl"] = country_code
    headers = {"X-API-KEY": settings.serper_api_key, "Content-Type": "application/json"}

    last_error: SearchError | None = None
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with httpx.Client(transport=_transport, timeout=httpx.Timeout(20.0)) as client:
                response = client.post(SERPER_URL, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            last_error = SearchError(
                f"Serper search could not be reached ({type(exc).__name__}): connection problem or timed out."
            )
        else:
            if response.status_code == 200:
                try:
                    organic = response.json().get("organic")
                except (ValueError, AttributeError):
                    raise SearchError("Serper returned a response that could not be read.") from None
                return organic if isinstance(organic, list) else []

            error = SearchError(f"Serper search failed (HTTP {response.status_code}): {_detail(response)}")
            if response.status_code != 429 and response.status_code < 500:
                raise error
            last_error = error

        if attempt < MAX_ATTEMPTS:
            logger.warning("Search attempt %d failed; retrying.", attempt)
            _sleep(1.5 * attempt)

    assert last_error is not None
    raise last_error