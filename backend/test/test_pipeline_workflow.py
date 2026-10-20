# File path: backend/test/test_pipeline_workflow.py
import json

import httpx
import pytest

from backend.core.config import settings
from backend.pipeline import search as search_module
from backend.pipeline import workflow
from backend.test import serper_fixtures as fx

CAMPAIGN = {
    "campaign_id": "c1", "user_id": "u1", "platform": "instagram",
    "category": "fashion and beauty",
    "country": "Gen Z and young professionals in India interested in fashion",
    "min_followers": 20_000, "max_followers": 100_000,
}


@pytest.fixture
def searches(monkeypatch):
    """Replaces the web search. `searches.reply(*results)` sets what every
    search returns; `searches.calls` records what was asked."""

    class Fake:
        calls: list = []
        results: list = []

        def reply(self, *results):
            self.results = list(results)

        def __call__(self, query, *, country_code=None, num=10):
            self.calls.append((query, country_code))
            return self.results

    fake = Fake()
    fake.calls = []
    monkeypatch.setattr(workflow, "search", fake)
    return fake


def handles(creators):
    return [c["handle"] for c in creators]


def test_a_realistic_batch_comes_out_right(searches):
    searches.reply(fx.PROFILE_VANI, fx.PROFILE_RITU_WITH_BIO, fx.PROFILE_TOO_BIG, fx.PROFILE_TOO_SMALL,
                   fx.FEEDSPOT_LIST, fx.REEL_WITHOUT_HANDLE, fx.POST_NO_COUNT, fx.LIST_MID_SIZE, fx.NOISE)
    creators = workflow.run_campaign_workflow(CAMPAIGN)

    found = set(handles(creators))
    assert {"vanimir", "ritujain", "kavyarao", "ishanair"} <= found          # in range, kept
    assert not found & {"mrunu", "nagmamirajkar", "newcreator"}              # known to be out of range
    assert "aditi_banerjee" in found                                          # count unknown: kept, but...
    unknown = next(c for c in creators if c["handle"] == "aditi_banerjee")
    assert unknown["followers"] is None and unknown["score"] <= 6.0
    assert creators[-1]["handle"] == "aditi_banerjee"                         # ...ranked behind the verified ones

    scores = [c["score"] for c in creators]
    assert scores == sorted(scores, reverse=True)

    ritu = next(c for c in creators if c["handle"] == "ritujain")
    assert ritu["name"] == "Ritu Jain" and ritu["followers"] == 94_200
    assert ritu["niche"] == "fashion, beauty" and ritu["bio"].startswith("Fashion & beauty")
    assert ritu["location"] == "India"
    assert 0 <= ritu["score"] <= 10 and ritu["reasoning"].endswith(".")
    assert set(ritu["email"]) == {"subject", "body"} and "@ritujain" in ritu["email"]["body"]


def test_every_search_is_aimed_at_the_campaigns_country(searches):
    searches.reply(fx.PROFILE_VANI)
    workflow.run_campaign_workflow(CAMPAIGN)
    assert {code for _, code in searches.calls} == {"in"}
    assert all("India" in query for query, _ in searches.calls)


def test_it_stops_searching_once_it_has_enough(searches, monkeypatch):
    monkeypatch.setattr(settings, "pipeline_max_creators", 2)
    searches.reply(fx.PROFILE_VANI, fx.PROFILE_RITU_WITH_BIO, fx.LIST_MID_SIZE)
    creators = workflow.run_campaign_workflow(CAMPAIGN)
    assert len(searches.calls) == 1 and len(creators) == 2


def test_it_never_searches_more_than_the_budget(searches, monkeypatch):
    monkeypatch.setattr(settings, "pipeline_max_queries", 3)
    searches.reply(fx.NOISE)
    assert workflow.run_campaign_workflow(CAMPAIGN) == []
    assert len(searches.calls) == 3


def test_the_same_creator_found_twice_is_listed_once_and_scores_higher(searches, monkeypatch):
    monkeypatch.setattr(settings, "pipeline_max_queries", 2)
    searches.reply(fx.PROFILE_RITU_WITH_BIO)
    creators = workflow.run_campaign_workflow(CAMPAIGN)
    assert handles(creators) == ["ritujain"]
    assert creators[0]["score"] == 10.0     # in range 4 + both categories 4 + profile, bio, seen twice 2


def test_nothing_found_is_an_empty_list_not_an_error(searches):
    searches.reply(fx.NOISE, fx.REEL_WITHOUT_HANDLE)
    assert workflow.run_campaign_workflow(CAMPAIGN) == []


def test_progress_is_reported_in_order(searches):
    searches.reply(fx.PROFILE_VANI)
    stages = []
    workflow.run_campaign_workflow(CAMPAIGN, on_stage=stages.append)
    assert stages == ["review", "outreach"]


def test_creators_with_unknown_counts_cannot_crowd_out_verified_ones(searches, monkeypatch):
    monkeypatch.setattr(settings, "pipeline_max_creators", 6)           # allows max(3, 6 // 3) = 3 unknown
    unknown = [{"title": f"P{i} on Instagram", "link": f"https://www.instagram.com/p{i}x/reel/ABC/", "snippet": "a post"} for i in range(8)]
    searches.reply(fx.PROFILE_VANI, fx.PROFILE_RITU_WITH_BIO, *unknown)
    creators = workflow.run_campaign_workflow(CAMPAIGN)
    assert sum(c["followers"] is None for c in creators) == 3
    assert {"vanimir", "ritujain"} <= set(handles(creators))


def test_two_creators_with_the_same_display_name_are_told_apart(searches):
    twin_a = {**fx.PROFILE_VANI}
    twin_b = {"title": "Vani Mir (@vani.official) • Instagram photos and videos", "link": "https://www.instagram.com/vani.official/",
              "snippet": "40K Followers, 1 Following, 9 Posts - See Instagram photos and videos from Vani Mir (@vani.official)"}
    searches.reply(twin_a, twin_b)
    names = [c["name"] for c in workflow.run_campaign_workflow(CAMPAIGN)]
    assert len(set(n.lower() for n in names)) == 2
    assert any("(@" in n for n in names)


def test_a_failed_search_is_not_swallowed(monkeypatch):
    def broken(*args, **kwargs):
        raise search_module.SearchError("Serper search failed (HTTP 403): Unauthorized")
    monkeypatch.setattr(workflow, "search", broken)
    with pytest.raises(search_module.SearchError, match="403"):
        workflow.run_campaign_workflow(CAMPAIGN)


def test_the_raw_results_are_saved_only_when_asked(searches, monkeypatch, tmp_path):
    searches.reply(fx.PROFILE_VANI)
    monkeypatch.setattr(workflow, "OUTPUTS_DIR", tmp_path)

    monkeypatch.setattr(settings, "pipeline_debug_dump", False)
    workflow.run_campaign_workflow(CAMPAIGN)
    assert not (tmp_path / "search_debug.jsonl").exists()

    monkeypatch.setattr(settings, "pipeline_debug_dump", True)
    workflow.run_campaign_workflow(CAMPAIGN)
    lines = (tmp_path / "search_debug.jsonl").read_text().splitlines()
    assert lines and json.loads(lines[0])["results"][0]["link"] == fx.PROFILE_VANI["link"]


def test_the_whole_thing_through_the_real_search_client(monkeypatch):
    """Same run, but the search goes through search.py's HTTP code to a fake Serper."""
    def serper(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"organic": [fx.PROFILE_VANI, fx.PROFILE_TOO_BIG, fx.NOISE]})

    monkeypatch.setattr(search_module, "_transport", httpx.MockTransport(serper))
    monkeypatch.setattr(settings, "pipeline_max_queries", 2)
    creators = workflow.run_campaign_workflow(CAMPAIGN)
    assert handles(creators) == ["vanimir"]