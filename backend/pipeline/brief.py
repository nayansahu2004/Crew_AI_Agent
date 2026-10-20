# File path: backend/pipeline/brief.py
"""
Turns a campaign (category, country, follower range) into what the search
needs: a few search terms, the country to search in, words that count as a
match, and the queries themselves.
"""

import re
from dataclasses import dataclass

# Words that aren't a niche on their own.
_STOPWORDS = {
    "the", "and", "for", "with", "who", "are", "aged", "interested", "people",
    "creators", "creator", "influencer", "influencers", "content", "audience",
}

# Words that mean roughly the same thing. A creator whose profile says "ootd"
# is a match for a campaign about "fashion". Each group is (words that map to
# this group, words that count as a match).
_SYNONYM_GROUPS = [
    ({"fashion", "style", "styling", "apparel", "clothing"},
     {"fashion", "style", "stylist", "outfit", "outfits", "ootd", "streetwear", "fashionista", "clothing"}),
    ({"beauty", "makeup", "skincare", "cosmetics", "grooming"},
     {"beauty", "makeup", "skincare", "cosmetics", "mua", "grooming", "hairstyle"}),
    ({"fitness", "gym", "workout", "wellness", "health"},
     {"fitness", "gym", "workout", "trainer", "yoga", "wellness", "health", "athlete"}),
    ({"travel", "tourism", "adventure"},
     {"travel", "traveller", "traveler", "wanderlust", "tourism", "adventure", "explorer"}),
    ({"food", "foodie", "cooking", "recipe", "recipes", "culinary"},
     {"food", "foodie", "chef", "recipe", "recipes", "cooking", "restaurant", "baking"}),
    ({"tech", "technology", "gadgets", "gadget", "electronics"},
     {"tech", "technology", "gadgets", "gadget", "unboxing", "electronics"}),
    ({"gaming", "games", "esports"}, {"gaming", "gamer", "games", "esports", "streamer"}),
    ({"lifestyle", "vlog", "vlogs", "vlogger"}, {"lifestyle", "vlog", "vlogger"}),
    ({"finance", "investing", "money", "trading", "stocks"},
     {"finance", "investing", "investor", "money", "trading", "stocks"}),
    ({"parenting", "family", "mom", "mother"}, {"parenting", "mom", "mommy", "mother", "family"}),
    ({"music", "singer", "dance", "dancer"}, {"music", "singer", "musician", "dance", "dancer"}),
    ({"comedy", "humor", "humour", "memes", "entertainment"},
     {"comedy", "comedian", "humor", "humour", "memes", "entertainment", "funny"}),
    ({"education", "learning", "study", "students"},
     {"education", "educator", "teacher", "learning", "study", "students"}),
    ({"sports", "sport", "cricket", "football", "athlete"},
     {"sports", "sport", "cricket", "football", "athlete"}),
    ({"business", "entrepreneur", "startup", "marketing"},
     {"business", "entrepreneur", "startup", "founder", "marketing"}),
    ({"photography", "photographer", "photo"}, {"photography", "photographer", "photo"}),
]
_SYNONYMS: dict[str, frozenset[str]] = {}
for _words, _matches in _SYNONYM_GROUPS:
    for _word in _words:
        _SYNONYMS[_word] = frozenset(_matches)

# (name for searching, Google country code, how to say it in a sentence,
#  aliases matched in any case, aliases matched only in CAPITALS)
_COUNTRIES = [
    ("India", "in", "India", ["india"], []),
    ("United States", "us", "the United States", ["united states", "america"], ["USA", "US"]),
    ("United Kingdom", "gb", "the United Kingdom", ["united kingdom", "britain", "england"], ["UK"]),
    ("Canada", "ca", "Canada", ["canada"], []),
    ("Australia", "au", "Australia", ["australia"], []),
    ("United Arab Emirates", "ae", "the UAE", ["united arab emirates", "dubai"], ["UAE"]),
    ("Nepal", "np", "Nepal", ["nepal"], []),
    ("Bangladesh", "bd", "Bangladesh", ["bangladesh"], []),
    ("Sri Lanka", "lk", "Sri Lanka", ["sri lanka"], []),
    ("Pakistan", "pk", "Pakistan", ["pakistan"], []),
    ("Singapore", "sg", "Singapore", ["singapore"], []),
    ("Malaysia", "my", "Malaysia", ["malaysia"], []),
    ("Indonesia", "id", "Indonesia", ["indonesia"], []),
    ("Philippines", "ph", "the Philippines", ["philippines"], []),
    ("Germany", "de", "Germany", ["germany"], []),
    ("France", "fr", "France", ["france"], []),
    ("Spain", "es", "Spain", ["spain"], []),
    ("Italy", "it", "Italy", ["italy"], []),
    ("Brazil", "br", "Brazil", ["brazil"], []),
    ("Mexico", "mx", "Mexico", ["mexico"], []),
    ("South Africa", "za", "South Africa", ["south africa"], []),
    ("Nigeria", "ng", "Nigeria", ["nigeria"], []),
    ("Saudi Arabia", "sa", "Saudi Arabia", ["saudi arabia"], []),
    ("Japan", "jp", "Japan", ["japan"], []),
]

_SPLIT = re.compile(r"[,;|/•·\n]+|\s&\s|\band\b|\bor\b|\+", re.IGNORECASE)

QUERY_TEMPLATES = (
    'site:instagram.com "{term}" {country} creator',
    'site:instagram.com "{term}" {country} influencer',
    "{term} instagram influencers {country} followers",
    'site:instagram.com "{term}" {country} blogger',
)


@dataclass(frozen=True)
class Country:
    name: str      # for searching: "United States"
    code: str      # Google's country code: "us"
    display: str   # in a sentence: "the United States"


@dataclass(frozen=True)
class Brief:
    terms: tuple[str, ...]
    keywords: dict
    countries: tuple[Country, ...]
    min_followers: int
    max_followers: int

    @property
    def niche(self) -> str:
        return " and ".join(self.terms[:2])

    @property
    def country_code(self) -> str | None:
        return self.countries[0].code if self.countries else None

    @property
    def country_phrase(self) -> str:
        names = [c.display for c in self.countries]
        if not names:
            return ""
        joined = names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]
        return f" in {joined}"

    def matched_terms(self, text: str) -> list[str]:
        """The campaign's terms that this text mentions (or a synonym of)."""
        lowered = text.lower()
        return [
            term
            for term in self.terms
            if any(
                re.search(rf"(?<![a-z0-9]){re.escape(word)}(?![a-z0-9])", lowered)
                for word in self.keywords[term]
            )
        ]

    def in_range(self, followers: int) -> bool:
        if self.max_followers and followers > self.max_followers:
            return False
        return followers >= self.min_followers


def category_terms(category: str | None, limit: int = 6) -> list[str]:
    """'Sports • Gaming, fashion and beauty' -> ['sports', 'gaming', 'fashion', 'beauty']"""
    terms: list[str] = []
    for piece in _SPLIT.split(category or ""):
        term = " ".join(piece.lower().split()).strip(" .-–—'\"()")
        if len(term) < 3 or len(term) > 40 or len(term.split()) > 4 or term in _STOPWORDS:
            continue
        if term not in terms:
            terms.append(term)
    return terms[:limit]


def keywords_for(term: str) -> tuple[str, ...]:
    """The words that count as a mention of this term. A single word like
    "fashion" also counts its synonyms ("ootd", "stylist"...). A phrase like
    "sports analysis" must appear as that phrase: matching it on "sports"
    alone would claim something the creator's profile never said."""
    words = [w for w in re.findall(r"[a-z0-9]+", term) if w not in _STOPWORDS]
    if len(words) != 1:
        return (term,)
    return tuple(sorted({term, words[0]} | _SYNONYMS.get(words[0], frozenset())))


def detect_countries(text: str | None, limit: int = 3) -> list[Country]:
    """Countries named in free text, in the order they appear."""
    text = text or ""
    lowered = text.lower()
    found: list[tuple[int, Country]] = []
    for name, code, display, aliases, capital_aliases in _COUNTRIES:
        positions = []
        for alias in aliases:
            match = re.search(rf"(?<![a-z]){re.escape(alias)}(?![a-z])", lowered)
            if match:
                positions.append(match.start())
        for alias in capital_aliases:
            match = re.search(rf"(?<![A-Za-z]){re.escape(alias)}(?![A-Za-z])", text)
            if match:
                positions.append(match.start())
        if positions:
            found.append((min(positions), Country(name, code, display)))
    return [country for _, country in sorted(found, key=lambda item: item[0])][:limit]


def build_brief(campaign: dict) -> Brief:
    terms = category_terms(campaign.get("category")) or ["influencer"]
    return Brief(
        terms=tuple(terms),
        keywords={term: keywords_for(term) for term in terms},
        countries=tuple(detect_countries(str(campaign.get("country") or ""))),
        min_followers=int(campaign.get("min_followers") or 0),
        max_followers=int(campaign.get("max_followers") or 0),
    )


def build_queries(brief: Brief, limit: int) -> list[str]:
    """The searches to run, best first. Each template is tried across the
    campaign's terms and countries before the next template, so the first
    few searches already cover the whole brief."""
    countries = [c.name for c in brief.countries[:2]] or [""]
    queries: list[str] = []
    for template in QUERY_TEMPLATES:
        for term in brief.terms[:3]:
            for country in countries:
                query = " ".join(template.format(term=term, country=country).split())
                if query not in queries:
                    queries.append(query)
    return queries[:limit]