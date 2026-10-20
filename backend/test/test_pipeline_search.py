# File path: backend/test/test_pipeline_search.py
import httpx
import pytest

from backend.core.config import settings
from backend.pipeline import search as s


class Server:
    """A pretend Serper: answers from a list, one reply per request."""

    def __init__(self, *replies):
        self.replies = list(replies)
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        reply = self.replies[min(len(self.requests), len(self.replies)) - 1]
        if isinstance(reply, Exception):
            raise reply
        return reply


@pytest.fixture
def serve(monkeypatch):
    sleeps = []

    def install(*replies):
        server = Server(*replies)
        monkeypatch.setattr(s, "_transport", httpx.MockTransport(server))
        monkeypatch.setattr(s, "_sleep", sleeps.append)
        server.sleeps = sleeps
        return server

    return install


def ok(organic):
    return httpx.Response(200, json={"organic": organic})


def test_a_search_returns_the_organic_results(serve):
    server = serve(ok([{"title": "T", "link": "https://x.test", "snippet": "S"}]))
    assert s.search("fashion creators", country_code="in") == [{"title": "T", "link": "https://x.test", "snippet": "S"}]

    request = server.requests[0]
    assert request.headers["x-api-key"] == settings.serper_api_key
    import json
    assert json.loads(request.content) == {"q": "fashion creators", "num": 10, "gl": "in"}


def test_no_country_means_no_gl_parameter(serve):
    import json
    server = serve(ok([]))
    s.search("q")
    assert "gl" not in json.loads(server.requests[0].content)


def test_a_reply_without_results_is_an_empty_list(serve):
    serve(httpx.Response(200, json={"searchParameters": {}}))
    assert s.search("q") == []


@pytest.mark.parametrize("status, body", [
    (403, {"message": "Unauthorized"}),
    (401, {"message": "Invalid API key"}),
    (400, {"message": "Not enough credits"}),
])
def test_errors_a_retry_cannot_fix_fail_at_once(serve, status, body):
    server = serve(httpx.Response(status, json=body))
    with pytest.raises(s.SearchError) as error:
        s.search("q")
    assert "Serper" in str(error.value) and str(status) in str(error.value)
    assert len(server.requests) == 1 and server.sleeps == []


def test_a_rate_limit_is_retried_then_succeeds(serve):
    server = serve(httpx.Response(429, json={"message": "Too many requests"}),
                   httpx.Response(429, json={}), ok([{"title": "T", "link": "L", "snippet": "S"}]))
    assert len(s.search("q")) == 1
    assert len(server.requests) == 3
    assert server.sleeps == [1.5, 3.0]           # waits a little longer each time


def test_a_server_that_stays_down_gives_up_after_three_tries(serve):
    server = serve(httpx.Response(503, text="unavailable"))
    with pytest.raises(s.SearchError, match="HTTP 503"):
        s.search("q")
    assert len(server.requests) == 3


def test_a_connection_failure_is_retried_and_explained(serve):
    server = serve(httpx.ConnectTimeout("slow"))
    with pytest.raises(s.SearchError, match="Serper search could not be reached.*timed out"):
        s.search("q")
    assert len(server.requests) == 3


def test_an_unreadable_reply_is_reported(serve):
    serve(httpx.Response(200, text="<html>not json</html>"))
    with pytest.raises(s.SearchError, match="could not be read"):
        s.search("q")


def test_the_api_key_never_appears_in_an_error(serve):
    serve(httpx.Response(403, json={"message": "Unauthorized"}))
    with pytest.raises(s.SearchError) as error:
        s.search("q")
    assert settings.serper_api_key not in str(error.value)