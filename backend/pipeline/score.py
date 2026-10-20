# File path: backend/pipeline/score.py
"""
Scores a creator out of 10 with a fixed formula -- the same input always
gives the same score, and the reason it gives is the actual arithmetic.

    follower fit    up to 4   the follower count is known and in range
    category match  up to 4   how many of the campaign's categories the
                              creator's profile text mentions
    evidence        up to 2   their own Instagram page was found (+1), a
                              bio was found (+0.5), and more than one search
                              turned them up (+0.5)

A creator whose follower count wasn't in the search results can't be checked
against the range, so their score is capped at 6 and the reason says so.
"""

from backend.pipeline.brief import Brief
from backend.pipeline.extract import Candidate

UNKNOWN_FOLLOWERS_CAP = 6.0


def format_count(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}".rstrip("0").rstrip(".") + "M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}".rstrip("0").rstrip(".") + "K"
    return str(n)


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " and " + items[-1]


def score_creator(candidate: Candidate, brief: Brief) -> tuple[float, str]:
    """(score from 0 to 10, one-sentence reason)."""
    # 1. Follower fit.
    if candidate.followers is None:
        fit = 0.0
        followers_note = "follower count wasn't in the search results, so check it yourself"
    else:
        fit = 4.0
        followers_note = (
            f"{format_count(candidate.followers)} followers, inside your "
            f"{format_count(brief.min_followers)}–{format_count(brief.max_followers)} range"
        )

    # 2. Category match.
    matched = brief.matched_terms(candidate.text)
    if len(matched) >= 2:
        category = 4.0
    elif len(matched) == 1:
        category = 2.5 if len(brief.terms) > 1 else 4.0
    else:
        category = 0.0
    where = "bio mentions" if candidate.bio and brief.matched_terms(candidate.bio) else "search text mentions"
    category_note = f"{where} {_join(matched)}" if matched else "none of your category words appear in the search text"

    # 3. Evidence.
    evidence = 0.0
    if candidate.is_profile:
        evidence += 1.0
    if candidate.bio:
        evidence += 0.5
    if candidate.seen_in >= 2:
        evidence += 0.5

    total = fit + category + evidence
    if candidate.followers is None:
        total = min(total, UNKNOWN_FOLLOWERS_CAP)
    score = round(max(0.0, min(total, 10.0)), 1)
    return score, f"{followers_note[0].upper()}{followers_note[1:]}; {category_note}."