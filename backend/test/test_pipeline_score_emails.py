# File path: backend/test/test_pipeline_score_emails.py
import pytest

from backend.pipeline.brief import build_brief
from backend.pipeline.emails import draft_email, first_name
from backend.pipeline.extract import Candidate
from backend.pipeline.score import format_count, score_creator
from backend.services.pipeline_service import _finalize_email_body

BRIEF = build_brief({"category": "fashion and beauty", "country": "India", "min_followers": 20_000, "max_followers": 100_000})


def candidate(**overrides) -> Candidate:
    values = dict(handle="vanimir", name="Vani Mir", followers=50_000,
                  text="Vani Mir\nFashion & makeup creator", bio=None, is_profile=False, seen_in=1)
    values.update(overrides)
    return Candidate(**values)


# --- scoring ---------------------------------------------------------------------

def test_a_perfect_creator_scores_ten():
    best = candidate(bio="Fashion and beauty", is_profile=True, seen_in=3)
    score, reason = score_creator(best, BRIEF)
    assert score == 10.0
    assert "50K followers, inside your 20K–100K range" in reason
    assert "bio mentions fashion and beauty" in reason


def test_the_score_is_the_arithmetic_and_always_the_same():
    # in range 4 + one of two categories 2.5 + no evidence 0
    one_match = candidate(text="Fashion creator")
    assert score_creator(one_match, BRIEF)[0] == 6.5
    assert score_creator(one_match, BRIEF) == score_creator(one_match, BRIEF)


def test_evidence_adds_up():
    base = candidate(text="Fashion creator")                       # 4 + 2.5
    assert score_creator(candidate(text="Fashion creator", is_profile=True), BRIEF)[0] == 7.5
    assert score_creator(candidate(text="Fashion creator", bio="x"), BRIEF)[0] == 7.0
    assert score_creator(candidate(text="Fashion creator", seen_in=2), BRIEF)[0] == 7.0
    assert score_creator(base, BRIEF)[0] == 6.5


def test_no_category_words_means_a_low_score_and_says_so():
    score, reason = score_creator(candidate(text="I love puppies"), BRIEF)
    assert score == 4.0
    assert "none of your category words appear" in reason


def test_an_unknown_follower_count_is_capped_and_flagged():
    unknown = candidate(followers=None, bio="Fashion and beauty", is_profile=True, seen_in=3)
    score, reason = score_creator(unknown, BRIEF)
    assert score == 6.0                                  # would be 6.0 + ... without the cap
    assert reason.startswith("Follower count wasn't in the search results")
    assert "check it yourself" in reason


def test_a_single_term_campaign_gives_full_marks_for_one_match():
    brief = build_brief({"category": "fashion", "country": "", "min_followers": 1, "max_followers": 100})
    assert score_creator(candidate(text="fashion", followers=5), brief)[0] == 8.0


@pytest.mark.parametrize("n, label", [(850, "850"), (1_000, "1K"), (45_300, "45.3K"), (100_000, "100K"), (8_100_000, "8.1M"), (2_000_000, "2M")])
def test_counts_are_shown_shortly(n, label):
    assert format_count(n) == label


# --- emails ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, handle, expected", [
    ("Vani Mir", "vanimir", "Vani"),
    ("himanchal gupta", "justtechit.english", "Himanchal"),
    ("PRIYA", "priya", None),                 # same as the handle: it's a username
    ("vanimir", "vanimir", None),
    ("Tech Street 24", "techxstreet", None),   # a digit means it's a brand/username
    ("the_real_vani", "vani", None),
    ("The Big Daily Fashion Show Network", "tdfsn", None),   # too long to be a person
    ("", "x", None),
])
def test_greeting_names(name, handle, expected):
    assert first_name(name, handle) == expected


def test_the_email_keeps_the_placeholders_for_the_users_own_details():
    email = draft_email(candidate(), BRIEF)
    assert "[Your Name]" in email["body"] and "[Agency Name]" in email["body"]
    assert email["body"].startswith("Hi Vani,")
    assert "@vanimir" in email["body"]
    assert "a fashion and beauty campaign in India" in email["body"]
    assert "rate card" in email["body"] and "availability" in email["body"]
    assert email["subject"]


def test_the_email_only_says_true_things():
    email = draft_email(candidate(text="I love puppies"), BRIEF)["body"]
    assert "page mentions" not in email                     # nothing matched, nothing claimed
    for pretend in ("loved your", "your recent post", "your latest", "big fan"):
        assert pretend not in email.lower()
    matched = draft_email(candidate(text="Fashion creator"), BRIEF)["body"]
    assert "We noticed your page mentions fashion." in matched


def test_an_unknown_name_gets_a_neutral_greeting():
    assert draft_email(candidate(name="vanimir"), BRIEF)["body"].startswith("Hi there,")


def test_a_creator_always_gets_the_same_wording_but_a_batch_varies():
    assert draft_email(candidate(), BRIEF) == draft_email(candidate(), BRIEF)
    subjects = {draft_email(candidate(handle=f"creator{i}"), BRIEF)["subject"].split(":")[0][:12] for i in range(30)}
    assert len(subjects) >= 2


def test_the_article_is_right():
    brief = build_brief({"category": "", "country": "", "min_followers": 1, "max_followers": 9})
    assert "an influencer campaign" in draft_email(candidate(), brief)["body"]


def test_the_finished_email_carries_the_users_own_signature():
    sender = {"name": "Nayan Kumar Sahu", "title": "Founder | Talent Director", "company": "Arista Management", "phone": "+91 72055 40108"}
    body = _finalize_email_body(draft_email(candidate(), BRIEF)["body"], sender)

    assert "My name is Nayan from Arista Management." in body
    assert body.endswith("Best regards,\n\nNayan Kumar Sahu\nFounder | Talent Director\nArista Management\nPh: +91 72055 40108")
    assert "[" not in body
    assert "- Your availability over the next few weeks" in body      # the list survives