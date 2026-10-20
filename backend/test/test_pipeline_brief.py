# File path: backend/test/test_pipeline_brief.py
import pytest

from backend.pipeline import brief as b


@pytest.mark.parametrize("category, expected", [
    ("fashion and beauty", ["fashion", "beauty"]),
    ("Technology, Gadgets, Productivity", ["technology", "gadgets", "productivity"]),
    ("Sports • Sports Analysis • Gaming • Entertainment • Adult Lifestyle",
     ["sports", "sports analysis", "gaming", "entertainment", "adult lifestyle"]),
    ("fitness / wellness | yoga", ["fitness", "wellness", "yoga"]),
    ("", []),
    (None, []),
    ("a", []),
    ("one two three four five six words in a sentence", []),   # a sentence isn't a niche
    ("fashion, fashion, Fashion", ["fashion"]),
])
def test_category_terms(category, expected):
    assert b.category_terms(category) == expected


def test_category_terms_are_capped():
    assert len(b.category_terms("a1x, b2x, c3x, d4x, e5x, f6x, g7x, h8x")) == 6


@pytest.mark.parametrize("text, expected", [
    ("Mumbai | OOTD & makeup", ["fashion", "beauty"]),
    ("Gym rat, yoga teacher", ["fitness"]),
    ("I love puppies", []),
    ("fashionable people", []),          # not the same word
    ("Fashion", ["fashion"]),
])
def test_matching_uses_whole_words_and_synonyms(text, expected):
    brief = b.build_brief({"category": "fashion, beauty, fitness", "country": "", "min_followers": 1, "max_followers": 9})
    assert [t for t in brief.matched_terms(text) if t in expected] == expected
    if not expected:
        assert brief.matched_terms(text) == []


def test_a_multi_word_term_matches_as_a_phrase():
    brief = b.build_brief({"category": "sports analysis", "country": "", "min_followers": 1, "max_followers": 9})
    assert brief.matched_terms("I do sports analysis on Sundays") == ["sports analysis"]
    assert brief.matched_terms("sports only") == []


def test_the_country_is_found_inside_a_long_sentence():
    text = "Gen Z and young professionals aged 18–30 in India who are interested in technology, gadgets"
    assert [c.name for c in b.detect_countries(text)] == ["India"]


def test_several_countries_keep_their_order():
    found = b.detect_countries("India, Bangladesh, Nepal, Sri Lanka")
    assert [c.name for c in found] == ["India", "Bangladesh", "Nepal"]     # capped at 3
    assert found[0].code == "in"


def test_short_country_names_need_capitals():
    assert b.detect_countries("tell us about the market") == []
    assert [c.name for c in b.detect_countries("creators in the US and UK")] == ["United States", "United Kingdom"]
    assert b.detect_countries("") == [] and b.detect_countries(None) == []


def test_country_phrase_reads_naturally():
    one = b.build_brief({"category": "x1x", "country": "India", "min_followers": 1, "max_followers": 9})
    three = b.build_brief({"category": "x1x", "country": "India, Bangladesh, Nepal", "min_followers": 1, "max_followers": 9})
    none = b.build_brief({"category": "x1x", "country": "somewhere", "min_followers": 1, "max_followers": 9})
    assert one.country_phrase == " in India"
    assert three.country_phrase == " in India, Bangladesh and Nepal"
    assert none.country_phrase == "" and none.country_code is None
    assert one.country_code == "in"


def test_a_missing_category_falls_back_to_a_generic_term():
    brief = b.build_brief({"category": "", "country": "", "min_followers": 1, "max_followers": 9})
    assert brief.terms == ("influencer",) and brief.niche == "influencer"


def test_the_follower_range():
    brief = b.build_brief({"category": "x1x", "country": "", "min_followers": 20_000, "max_followers": 100_000})
    assert brief.in_range(20_000) and brief.in_range(100_000) and brief.in_range(54_321)
    assert not brief.in_range(19_999) and not brief.in_range(100_001)


def test_queries_cover_the_brief_and_respect_the_limit():
    brief = b.build_brief({"category": "fashion and beauty", "country": "India", "min_followers": 1, "max_followers": 9})
    queries = b.build_queries(brief, 5)

    assert len(queries) == 5 and len(set(queries)) == 5
    assert queries[0] == 'site:instagram.com "fashion" India creator'
    assert any('"beauty"' in q for q in queries[:3])      # the second term is searched early too
    assert all("India" in q for q in queries)
    assert len(b.build_queries(brief, 100)) <= len(b.QUERY_TEMPLATES) * 2 * 1


def test_queries_without_a_country_have_no_stray_spaces():
    brief = b.build_brief({"category": "fashion", "country": "", "min_followers": 1, "max_followers": 9})
    for query in b.build_queries(brief, 10):
        assert "  " not in query and query == query.strip()