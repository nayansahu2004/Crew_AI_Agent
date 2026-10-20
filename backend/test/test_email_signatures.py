# File path: backend/test/test_email_signature.py
from backend.services.pipeline_service import _finalize_email_body, _fill_company

SENDER = {
    "name": "Nayan Kumar Sahu",
    "title": "Founder | Talent Director",
    "company": "Arista Management",
    "phone": "+91 7205540108",
}
SIGNATURE = (
    "Nayan Kumar Sahu\nFounder | Talent Director\n"
    "Arista Management\nPh: +91 7205540108"
)


def test_fills_placeholders_and_appends_signature():
    body = (
        "Hi Niharika,\n\nMy name is [Your Name] from [Agency Name]. We are planning "
        "a sports collaboration.\n\nLooking forward to connecting!\n\n"
        "Best regards,\n\n[Your Name]\n[Agency Name]"
    )
    out = _finalize_email_body(body, SENDER)

    assert "My name is Nayan from Arista Management." in out
    assert "[" not in out
    assert out.endswith(f"Best regards,\n\n{SIGNATURE}")
    assert out.count("Nayan Kumar Sahu") == 1


def test_replaces_a_signature_the_model_wrote_itself():
    out = _finalize_email_body("Hello there.\n\nWarm regards,\nSomeone Else\nOther Agency", SENDER)
    assert out.endswith(f"Warm regards,\n\n{SIGNATURE}")
    assert "Someone Else" not in out


def test_adds_a_closing_when_the_model_wrote_none():
    out = _finalize_email_body("Hello there.", SENDER)
    assert out == f"Hello there.\n\nBest regards,\n\n{SIGNATURE}"


def test_skips_missing_signature_fields():
    out = _finalize_email_body("Hi.", {"name": "Nayan Kumar Sahu"})
    assert out.endswith("Best regards,\n\nNayan Kumar Sahu")


def test_unchanged_when_no_sender_is_configured():
    assert _finalize_email_body("Hi [Your Name]", None) == "Hi [Your Name]"


def test_empty_body_is_left_alone():
    assert _finalize_email_body(None, SENDER) is None
    assert _finalize_email_body("", SENDER) == ""


def test_subject_company_placeholder():
    assert _fill_company("Collab | [Agency Name]", SENDER) == "Collab | Arista Management"


def test_sender_is_loaded_from_the_run_owners_profile(monkeypatch):
    import mongomock

    from backend.services import pipeline_service

    db = mongomock.MongoClient()["t"]
    db.users.insert_one(
        {
            "supabase_user_id": "user-a",
            "name": "Asha Rao",
            "job_title": "Director",
            "company_name": "Rao Talent",
            "phone": "+44 20 7946 0958",
        }
    )
    db.users.insert_one({"supabase_user_id": "user-b", "name": "Ben Cole", "company_name": "Cole & Co"})
    monkeypatch.setattr(pipeline_service, "_sync_db", db)

    assert pipeline_service._load_sender("user-a") == {
        "name": "Asha Rao",
        "title": "Director",
        "company": "Rao Talent",
        "phone": "+44 20 7946 0958",
    }
    # Each user gets their OWN details -- never another user's.
    assert pipeline_service._load_sender("user-b")["company"] == "Cole & Co"
    assert pipeline_service._load_sender("someone-else") is None