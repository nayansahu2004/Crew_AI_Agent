# File path: backend/test/test_log_redaction.py
import logging

from backend.main import RedactOAuthParams


def access_record(path):
    # Same argument layout uvicorn's access logger uses.
    return logging.LogRecord(
        "uvicorn.access", logging.INFO, __file__, 1,
        '%s - "%s %s HTTP/%s" %d', ("127.0.0.1:5000", "GET", path, "1.1", 303), None,
    )


def test_the_google_code_and_state_are_blanked_out():
    record = access_record("/api/gmail/callback?state=abc.def&iss=https://accounts.google.com&code=4/0AXlq-secret&scope=email")
    RedactOAuthParams().filter(record)
    line = record.getMessage()
    assert "secret" not in line and "abc.def" not in line
    assert "state=[redacted]" in line and "code=[redacted]" in line
    assert "scope=email" in line  # everything else is kept


def test_ordinary_requests_are_untouched():
    record = access_record("/api/campaigns?limit=5")
    RedactOAuthParams().filter(record)
    assert "/api/campaigns?limit=5" in record.getMessage()