# File path: backend/pipeline/emails.py
"""
Fills an email template for each creator. No AI: the wording is fixed, so
every sentence is true -- it says the creator's page "came up in our search"
and only mentions a topic when their profile text really does. It never
pretends to have read their posts.

The placeholders [Your Name] and [Agency Name] are filled in later, from the
signed-in user's own profile, by services/pipeline_service.py (which also
adds the signature block).
"""

import hashlib
import re

from backend.pipeline.brief import Brief
from backend.pipeline.extract import Candidate

_OPENERS = (
    "I came across your Instagram page (@{handle}) and wanted to reach out.",
    "Your Instagram page (@{handle}) came up while we were putting together a creator list for a campaign.",
    "We're building a creator list for an upcoming campaign, and your Instagram page (@{handle}) came up in our search.",
)


def _variant(handle: str) -> int:
    """Picks one of three wordings from the handle, so a batch of emails
    doesn't read as identical copies, yet the same creator always gets the
    same one."""
    return int(hashlib.sha1(handle.encode()).hexdigest()[:8], 16) % 3


def _article(phrase: str) -> str:
    return "an" if phrase[:1].lower() in "aeiou" else "a"


def first_name(name: str, handle: str) -> str | None:
    """The creator's first name, or None when the "name" is really a
    username or a brand and a greeting by name would look wrong."""
    cleaned = " ".join(name.split())
    tokens = cleaned.split()
    looks_like_username = (
        cleaned.lower().lstrip("@") == handle
        or any(ch.isdigit() or ch in "_." for ch in cleaned)
        or len(tokens) > 3
        or not tokens
    )
    if looks_like_username:
        return None
    token = re.sub(r"[^\w'’-]", "", tokens[0])
    if not token:
        return None
    return token.capitalize() if token.islower() or token.isupper() else token


def draft_email(candidate: Candidate, brief: Brief) -> dict[str, str]:
    variant = _variant(candidate.handle)
    niche = brief.niche
    greeting = first_name(candidate.name, candidate.handle)

    subjects = (
        f"Collaboration opportunity: {niche} campaign",
        f"Would you be open to {_article(niche)} {niche} collaboration?",
        f"Collaboration idea for @{candidate.handle}",
    )

    matched = brief.matched_terms(candidate.text)
    mention = f" We noticed your page mentions {matched[0]}." if matched else ""

    body = "\n".join(
        [
            f"Hi {greeting}," if greeting else "Hi there,",
            "",
            f"My name is [Your Name] from [Agency Name]. {_OPENERS[variant].format(handle=candidate.handle)}{mention}",
            "",
            f"We're planning {_article(niche)} {niche} campaign{brief.country_phrase} and think your content "
            "could be a good fit. If you're open to paid collaborations, we'd love to know:",
            "",
            "- Your availability over the next few weeks",
            "- Your approximate rates or rate card for Reels, Stories and static posts",
            "- Whether you work with a manager or agency, and the best contact for them",
            "",
            "A media kit is welcome too, if you have one.",
            "",
            "Looking forward to hearing from you.",
            "",
            "Best regards,",
            "",
            "[Your Name]",
            "[Agency Name]",
        ]
    )
    return {"subject": subjects[variant], "body": body}