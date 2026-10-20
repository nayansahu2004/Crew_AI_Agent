# File path: backend/pipeline/workflow.py
"""
Runs the pipeline for one campaign:

    Discovery   search, then pull creators out of the results
    Review      score each creator and keep the best
    Outreach    draft an email for each

The one function the rest of the app calls is run_campaign_workflow(). It
returns the finished creators and never touches the database -- saving them
is services/pipeline_service.py's job.
"""

import json
import logging
from pathlib import Path
from typing import Callable

from backend.core.config import settings
from backend.pipeline.brief import Brief, build_brief, build_queries
from backend.pipeline.emails import draft_email
from backend.pipeline.extract import Candidate, extract_candidates, merge
from backend.pipeline.score import score_creator
from backend.pipeline.search import search

logger = logging.getLogger(__name__)

# backend/outputs/ whatever folder the server was started from.
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


def _dump(query: str, results: list[dict]) -> None:
    """With PIPELINE_DEBUG_DUMP=true, keeps the raw search results in
    backend/outputs/search_debug.jsonl -- useful for seeing exactly what the
    search returned when a run finds fewer creators than expected."""
    if not settings.pipeline_debug_dump:
        return
    try:
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        with open(OUTPUTS_DIR / "search_debug.jsonl", "a", encoding="utf-8") as handle:
            handle.write(json.dumps({"query": query, "results": results}, ensure_ascii=False) + "\n")
    except OSError:
        logger.warning("Could not write the search debug file.")


def _in_range_count(found: dict[str, Candidate], brief: Brief) -> int:
    return sum(1 for c in found.values() if c.followers is not None and brief.in_range(c.followers))


def discover(brief: Brief) -> list[Candidate]:
    """Search until there are enough creators, or the search budget runs out."""
    found: dict[str, Candidate] = {}
    queries = build_queries(brief, settings.pipeline_max_queries)

    for number, query in enumerate(queries, start=1):
        results = search(query, country_code=brief.country_code)
        candidates = extract_candidates(results)
        for candidate in candidates:
            merge(found, candidate)
        logger.info(
            "Search %d/%d %r: %d results, %d creators (%d in range so far).",
            number, len(queries), query, len(results), len(candidates), _in_range_count(found, brief),
        )
        _dump(query, results)
        if _in_range_count(found, brief) >= settings.pipeline_max_creators:
            break

    return list(found.values())


def _review(candidates: list[Candidate], brief: Brief) -> list[tuple[Candidate, float, str]]:
    """Drop creators known to be outside the follower range, score the rest,
    and keep the best. Creators whose follower count the search never gave are
    kept (they may be a fit) but capped, so they can't crowd out verified ones."""
    keep = [c for c in candidates if c.followers is None or brief.in_range(c.followers)]
    scored = [(c, *score_creator(c, brief)) for c in keep]
    scored.sort(key=lambda item: item[1], reverse=True)

    unknown_allowed = max(3, settings.pipeline_max_creators // 3)
    chosen: list[tuple[Candidate, float, str]] = []
    unknown_taken = 0
    for item in scored:
        if item[0].followers is None:
            if unknown_taken >= unknown_allowed:
                continue
            unknown_taken += 1
        chosen.append(item)
        if len(chosen) >= settings.pipeline_max_creators:
            break
    return chosen


def _unique_names(chosen: list[tuple[Candidate, float, str]]) -> None:
    """Two creators can share a display name; the interface is clearer when
    they don't."""
    seen: set[str] = set()
    for candidate, _score, _reason in chosen:
        if candidate.name.lower() in seen:
            candidate.name = f"{candidate.name} (@{candidate.handle})"
        seen.add(candidate.name.lower())


def run_campaign_workflow(campaign: dict, on_stage: Callable[[str], None] | None = None) -> list[dict]:
    """
    Args:
        campaign: category, country, min_followers, max_followers (the shape
                  api/runs.py builds -- `country` is the campaign's target
                  country text, which may name several countries).
        on_stage: called with "review" and then "outreach" as the pipeline
                  moves on, so the run's progress can be shown live.

    Returns one dict per creator, best first:
        handle, name, followers (None if unknown), niche, bio, location,
        score (0-10), reasoning, email {subject, body}
    An empty list means nothing matched.
    """
    brief = build_brief(campaign)

    candidates = discover(brief)

    if on_stage:
        on_stage("review")
    chosen = _review(candidates, brief)
    _unique_names(chosen)

    if on_stage:
        on_stage("outreach")
    location = ", ".join(c.name for c in brief.countries) or None
    return [
        {
            "handle": candidate.handle,
            "name": candidate.name,
            "followers": candidate.followers,
            "niche": ", ".join(brief.matched_terms(candidate.text)) or None,
            "bio": candidate.bio,
            "location": location,
            "score": score,
            "reasoning": reasoning,
            "email": draft_email(candidate, brief),
        }
        for candidate, score, reasoning in chosen
    ]