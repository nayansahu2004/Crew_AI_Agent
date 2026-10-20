# File path: backend/test/test_friendly_errors.py
from backend.core import friendly_errors as fe
from backend.core.friendly_errors import explain_run_error
from backend.pipeline.search import SearchError


def test_serper_rejects_the_key():
    exc = SearchError("Serper search failed (HTTP 403): Unauthorized")
    assert explain_run_error(exc) == fe.SEARCH_KEY_OR_CREDITS


def test_serper_is_out_of_credits():
    exc = SearchError("Serper search failed (HTTP 400): Not enough credits")
    assert explain_run_error(exc) == fe.SEARCH_KEY_OR_CREDITS
    assert "credits" in explain_run_error(exc)


def test_serper_rate_limit():
    exc = SearchError("Serper search failed (HTTP 429): Too many requests")
    assert explain_run_error(exc) == fe.SEARCH_BUSY


def test_serper_is_down():
    exc = SearchError("Serper search failed (HTTP 503): unavailable")
    assert explain_run_error(exc) == fe.SEARCH_DOWN


def test_serper_cannot_be_reached():
    exc = SearchError("Serper search could not be reached (ConnectTimeout): connection problem or timed out.")
    assert explain_run_error(exc) == fe.NETWORK


def test_database_unreachable():
    exc = RuntimeError("pymongo.errors.ServerSelectionTimeoutError: SSL handshake failed")
    assert explain_run_error(exc) == fe.DATABASE


def test_a_plain_network_timeout():
    exc = RuntimeError("httpx.ConnectTimeout: _ssl.c:989: The handshake operation timed out")
    assert explain_run_error(exc) == fe.NETWORK


def test_unknown_error_gets_generic_message():
    assert explain_run_error(ValueError("something odd")) == fe.DEFAULT


def test_follows_the_error_chain():
    try:
        try:
            raise SearchError("Serper search failed (HTTP 403): Unauthorized")
        except SearchError as inner:
            raise ValueError("wrapper hides the cause") from inner
    except ValueError as outer:
        assert explain_run_error(outer) == fe.SEARCH_KEY_OR_CREDITS


def test_object_id_digits_are_not_mistaken_for_a_status_code():
    # "429" appears inside a hex id here -- must NOT be read as HTTP 429.
    assert explain_run_error(ValueError("serper run 6ac37429cf07 failed")) == fe.DEFAULT