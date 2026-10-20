# File path: backend/test/test_pipeline_extract.py
import pytest

from backend.pipeline import extract
from backend.pipeline.extract import Candidate, extract_candidates, find_follower_count, handle_from_link
from backend.test import serper_fixtures as fx


@pytest.mark.parametrize("text, expected", [
    ("96K Followers, 1,203 Following", 96_000),
    ("1.2M followers", 1_200_000),
    ("12,345 Followers", 12_345),
    ("94.2K Followers", 94_200),
    ("Instagram Followers 8.1M Follower Growth", 8_100_000),
    ("Followers 12,345", 12_345),
    ("2.5 million followers", 2_500_000),
    ("310 Following, 40 Posts", None),        # following is not followers
    ("no numbers here", None),
    ("100K followers 1,598", 100_000),         # the first count wins
])
def test_follower_counts(text, expected):
    assert find_follower_count(text) == expected


@pytest.mark.parametrize("link, expected", [
    ("https://www.instagram.com/vanimir/", ("vanimir", True)),
    ("https://instagram.com/vanimir", ("vanimir", True)),
    ("https://www.instagram.com/VaniMir/?hl=en", ("vanimir", True)),
    ("https://www.instagram.com/vanimir/reel/ABC123/", ("vanimir", False)),
    ("https://www.instagram.com/vanimir/p/ABC123/", ("vanimir", False)),
    ("https://www.instagram.com/stories/vanimir/12345/", ("vanimir", False)),
    ("https://www.instagram.com/reel/DP6Kh_cki3W/", (None, False)),   # whose reel? unknown
    ("https://www.instagram.com/explore/tags/fashion/", (None, False)),
    ("https://www.instagram.com/p/ABC123/", (None, False)),
    ("https://www.instagram.com/instagram/", (None, False)),          # Instagram's own account
    ("https://www.youtube.com/@vanimir", (None, False)),
    ("https://instagram.com.evil.test/vanimir/", (None, False)),       # look-alike address
    ("", (None, False)),
    (None, (None, False)),
])
def test_handles_from_addresses(link, expected):
    assert handle_from_link(link) == expected


def test_a_profile_result_gives_the_creator_whole():
    [vani] = extract_candidates([fx.PROFILE_VANI])
    assert (vani.handle, vani.name, vani.followers) == ("vanimir", "Vani Mir", 96_000)
    assert vani.is_profile is True
    assert vani.bio is None


def test_a_bio_is_read_from_the_snippet():
    [ritu] = extract_candidates([fx.PROFILE_RITU_WITH_BIO])
    assert ritu.followers == 94_200
    assert ritu.bio == "Fashion & beauty creator | OOTD | Delhi 📍"
    assert "OOTD" in ritu.text


def test_a_post_gives_the_handle_but_no_follower_count():
    [aditi] = extract_candidates([fx.POST_NO_COUNT])
    assert aditi.handle == "aditi_banerjee"
    assert aditi.name == "Aditi Banerjee"
    assert aditi.followers is None
    assert aditi.is_profile is False


def test_a_reel_with_no_handle_in_its_address_is_skipped():
    # The real snippet from your run mentions "100K followers" but not whose it is.
    assert extract_candidates([fx.REEL_WITHOUT_HANDLE]) == []


def test_a_list_page_gives_each_creator_their_own_count():
    found = {c.handle: c for c in extract_candidates([fx.FEEDSPOT_LIST])}
    assert set(found) == {"nagmamirajkar", "mrunu"}
    assert found["nagmamirajkar"].followers == 8_100_000
    assert found["mrunu"].followers == 6_100_000
    assert found["nagmamirajkar"].name == "Nagma Mirajkar"
    assert found["mrunu"].name == "Mrunal Panchal"


def test_mid_sized_creators_on_a_list_page():
    found = {c.handle: c.followers for c in extract_candidates([fx.LIST_MID_SIZE])}
    assert found == {"kavyarao": 45_300, "ishanair": 61_000}


def test_a_bare_mention_or_an_email_is_not_a_creator():
    assert extract_candidates([fx.MENTION_WITHOUT_COUNT]) == []
    assert extract_candidates([fx.NOISE]) == []


def test_nothing_is_invented_from_empty_results():
    assert extract_candidates([]) == []
    assert extract_candidates([{}]) == []
    assert extract_candidates([{"title": None, "link": None, "snippet": None}]) == []


def test_merging_combines_what_several_searches_know():
    found: dict[str, Candidate] = {}
    extract.merge(found, Candidate("aditi", "aditi", None, "text one", None, False))
    extract.merge(found, Candidate("aditi", "Aditi Banerjee", 52_000, "text two", "Makeup artist", True))

    [merged] = found.values()
    assert merged.seen_in == 2
    assert merged.followers == 52_000
    assert merged.name == "Aditi Banerjee"       # the real name replaces the bare handle
    assert merged.bio == "Makeup artist"
    assert merged.is_profile is True
    assert "text one" in merged.text and "text two" in merged.text


def test_merging_never_overwrites_a_known_count():
    found: dict[str, Candidate] = {}
    extract.merge(found, Candidate("x", "X", 40_000, "t", None, True))
    extract.merge(found, Candidate("x", "X", 90_000, "t", None, True))
    assert found["x"].followers == 40_000