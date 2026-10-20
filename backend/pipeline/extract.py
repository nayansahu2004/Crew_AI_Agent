# File path: backend/pipeline/extract.py
"""
Pulls Instagram creators out of search results -- only what the results
actually say. Nothing is guessed, so a handle or follower count that isn't in
the results can never be invented.

Two kinds of result are understood:

1. A result on instagram.com. The handle comes from the address
   (instagram.com/<handle>/), and Instagram's own page description usually
   states the followers: "96K Followers, 1,203 Following, 842 Posts - See
   Instagram photos and videos from Name (@handle)".

2. A list on another site ("1. Name · @handle Instagram Followers 8.1M").
   Here a bare @mention proves nothing, so a creator is only taken when a
   follower count sits next to it.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse


@dataclass
class Candidate:
    handle: str              # lower case, no "@"
    name: str
    followers: int | None    # None when the results never said
    text: str                # title + snippet, used to match the campaign's category
    bio: str | None
    is_profile: bool         # came from the creator's own instagram.com page
    seen_in: int = 1         # how many searches turned this creator up


# --- follower counts -------------------------------------------------------------

_NUMBER = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
_UNIT = r"(K|M|thousand|million)"
_BEFORE = re.compile(rf"{_NUMBER}\s*{_UNIT}?\s*(?:\+\s*)?followers\b", re.IGNORECASE)   # "96K Followers"
_AFTER_UNIT = re.compile(rf"followers\s*[:\-]?\s*{_NUMBER}\s*{_UNIT}\b", re.IGNORECASE)  # "Followers 8.1M"
_AFTER_PLAIN = re.compile(r"followers\s*[:\-]?\s*(\d{1,3}(?:,\d{3})+)\b", re.IGNORECASE)  # "Followers 12,345"

_MULTIPLIER = {"k": 1_000, "thousand": 1_000, "m": 1_000_000, "million": 1_000_000}


def _to_int(number: str, unit: str | None) -> int | None:
    value = float(number.replace(",", "")) * _MULTIPLIER.get((unit or "").lower(), 1)
    count = int(round(value))
    return count if 0 <= count <= 2_000_000_000 else None


def find_follower_count(text: str) -> int | None:
    """The first follower count mentioned in the text, or None."""
    best: tuple[int, int | None] | None = None
    for pattern in (_BEFORE, _AFTER_UNIT, _AFTER_PLAIN):
        match = pattern.search(text)
        if not match:
            continue
        unit = match.group(2) if match.re.groups >= 2 else None
        count = _to_int(match.group(1), unit)
        if count is not None and (best is None or match.start() < best[0]):
            best = (match.start(), count)
    return best[1] if best else None


# --- handles -----------------------------------------------------------------------

_HANDLE = re.compile(r"^[A-Za-z0-9._]{1,30}$")
# Instagram addresses that look like a profile but aren't one.
_RESERVED = {
    "p", "reel", "reels", "explore", "stories", "tv", "accounts", "direct", "about", "legal",
    "developer", "web", "directory", "popular", "challenge", "tags", "locations", "ar", "emails",
    "nametag", "oauth", "privacy", "press", "api", "download", "lite", "shop", "help", "business",
}
_NOT_CREATORS = {"instagram", "meta", "facebook", "gmail", "yahoo", "outlook", "hotmail"}
_POST_PATHS = {"p", "reel", "reels", "tv", "tagged"}


def _valid_handle(handle: str) -> str | None:
    handle = handle.lower().strip(".")
    if _HANDLE.match(handle) and handle and handle not in _NOT_CREATORS:
        return handle
    return None


def handle_from_link(link: str | None) -> tuple[str | None, bool]:
    """(handle, is it the creator's own profile page) for an instagram.com
    address; (None, False) for anything else or when there's no handle
    in the address (instagram.com/reel/<id> doesn't say whose it is)."""
    parsed = urlparse(link or "")
    if parsed.netloc.lower().removeprefix("www.") != "instagram.com":
        return None, False
    parts = [p for p in parsed.path.split("/") if p]
    if not parts:
        return None, False

    first = parts[0].lower()
    if first == "stories" and len(parts) >= 2:
        return _valid_handle(parts[1]), False
    if first in _RESERVED:
        return None, False
    if len(parts) == 1:
        handle = _valid_handle(parts[0])
        return handle, handle is not None
    if parts[1].lower() in _POST_PATHS:
        return _valid_handle(parts[0]), False
    return None, False


# --- names and bios ---------------------------------------------------------------------

_NAME_BEFORE_HANDLE = re.compile(r"^(.*?)\s*\(@[A-Za-z0-9._]+\)")
_NAME_BEFORE_ON_INSTAGRAM = re.compile(r"^(.+?)\s+on Instagram\b", re.IGNORECASE)
_BIO = re.compile(r"on Instagram:\s*[\"“”']?(.+?)[\"“”']?\s*$", re.IGNORECASE | re.DOTALL)
_MENTION = re.compile(r"(?<![\w.])@([A-Za-z0-9._]{2,30})")


def _clean_name(raw: str, fallback: str) -> str:
    first_part = re.split(r"\s*[|•·]\s*|\s+-\s+|\s*[–—]\s*|\(", raw or "")[0]
    name = re.sub(r"[^\w\s'’.&-]", "", first_part)   # drops emoji and stray symbols
    name = " ".join(name.split())
    return name if 2 <= len(name) <= 60 else fallback


def _name_from_title(title: str, handle: str) -> str:
    for pattern in (_NAME_BEFORE_HANDLE, _NAME_BEFORE_ON_INSTAGRAM):
        match = pattern.match(title or "")
        if match:
            return _clean_name(match.group(1), handle)
    return handle


def _bio_from_snippet(snippet: str) -> str | None:
    match = _BIO.search(snippet or "")
    bio = " ".join(match.group(1).split()).strip(" .…") if match else ""
    return bio or None


def _name_before(text: str, position: int, handle: str) -> str:
    segment = text[max(0, position - 80): position]
    segment = re.sub(r"[\s·|•\-–—:]+$", "", segment)
    segment = re.split(r"(?:^|\s)\d+\.\s+|[;\n]", segment)[-1]
    return _clean_name(segment, handle)


# --- the two kinds of result -------------------------------------------------------------------

def _from_listing(text: str) -> list[Candidate]:
    mentions = [(m.start(), m.end(), m.group(1)) for m in _MENTION.finditer(text)]
    found = []
    for index, (start, end, raw_handle) in enumerate(mentions):
        window_end = mentions[index + 1][0] if index + 1 < len(mentions) else len(text)
        followers = find_follower_count(text[end:window_end])
        handle = _valid_handle(raw_handle)
        if followers is None or handle is None:
            continue   # a bare @mention isn't evidence of a creator
        found.append(
            Candidate(
                handle=handle,
                name=_name_before(text, start, handle),
                followers=followers,
                text=text[max(0, start - 80): window_end],
                bio=None,
                is_profile=False,
            )
        )
    return found


def extract_candidates(results: list[dict]) -> list[Candidate]:
    """Every creator the search results say something about."""
    candidates: list[Candidate] = []
    for result in results:
        title = str(result.get("title") or "")
        snippet = str(result.get("snippet") or "")
        text = f"{title}\n{snippet}"

        handle, is_profile = handle_from_link(result.get("link"))
        if handle:
            candidates.append(
                Candidate(
                    handle=handle,
                    name=_name_from_title(title, handle),
                    followers=find_follower_count(text),
                    text=text,
                    bio=_bio_from_snippet(snippet),
                    is_profile=is_profile,
                )
            )
        else:
            candidates.extend(_from_listing(text))
    return candidates


def merge(into: dict[str, Candidate], new: Candidate) -> None:
    """Add a creator to the running list, combining what several searches
    know about the same handle."""
    existing = into.get(new.handle)
    if existing is None:
        into[new.handle] = new
        return
    existing.seen_in += 1
    existing.is_profile = existing.is_profile or new.is_profile
    if existing.followers is None:
        existing.followers = new.followers
    if existing.bio is None:
        existing.bio = new.bio
    if new.text not in existing.text and len(existing.text) < 800:
        existing.text += "\n" + new.text
    if existing.name == existing.handle and new.name != new.handle:
        existing.name = new.name