# File path: backend/test/test_runs.py
"""
Tests the run-creation API surface, with CrewAI execution fully mocked
via the mock_execute_campaign_run fixture -- no real agents, no network
calls, no real pymongo writes.
"""

import pytest

from backend.test.test_campaigns import VALID_CAMPAIGN_BODY


@pytest.mark.asyncio
async def test_start_run_returns_202_and_queued_status(client, mock_execute_campaign_run):
    create_response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    campaign_id = create_response.json()["id"]

    response = await client.post(f"/api/campaigns/{campaign_id}/runs")
    assert response.status_code == 202
    body = response.json()
    assert body["status"] == "queued"
    assert "run_id" in body


@pytest.mark.asyncio
async def test_start_run_schedules_background_task_with_correct_config(
    client, mock_execute_campaign_run
):
    create_response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    campaign_id = create_response.json()["id"]

    response = await client.post(f"/api/campaigns/{campaign_id}/runs")
    run_id = response.json()["run_id"]

    # mock_execute_campaign_run recorded every call made to the
    # (faked) background function -- confirm it was called exactly
    # once, with the run_id just created and the campaign fields
    # correctly mapped (note target_country -> country).
    assert len(mock_execute_campaign_run) == 1
    called_run_id, called_config = mock_execute_campaign_run[0]
    assert called_run_id == run_id
    assert called_config["campaign_id"] == campaign_id
    assert called_config["category"] == VALID_CAMPAIGN_BODY["category"]
    assert called_config["country"] == VALID_CAMPAIGN_BODY["target_country"]
    assert called_config["min_followers"] == VALID_CAMPAIGN_BODY["min_followers"]
    assert called_config["max_followers"] == VALID_CAMPAIGN_BODY["max_followers"]


@pytest.mark.asyncio
async def test_start_run_for_nonexistent_campaign_returns_404(
    client, mock_execute_campaign_run
):
    response = await client.post("/api/campaigns/" + "a" * 24 + "/runs")
    assert response.status_code == 404
    # The background task must NEVER be scheduled for a campaign that
    # doesn't exist/isn't owned by the caller.
    assert len(mock_execute_campaign_run) == 0


@pytest.mark.asyncio
async def test_get_run_status(client, mock_execute_campaign_run):
    create_response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    campaign_id = create_response.json()["id"]

    run_response = await client.post(f"/api/campaigns/{campaign_id}/runs")
    run_id = run_response.json()["run_id"]

    response = await client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id
    assert body["campaign_id"] == campaign_id
    # Since execute_campaign_run is mocked to a no-op, status should
    # still be "queued" -- the real stage transitions never ran.
    assert body["status"] == "queued"


@pytest.mark.asyncio
async def test_list_runs_for_campaign(client, mock_execute_campaign_run):
    create_response = await client.post("/api/campaigns", json=VALID_CAMPAIGN_BODY)
    campaign_id = create_response.json()["id"]

    await client.post(f"/api/campaigns/{campaign_id}/runs")
    await client.post(f"/api/campaigns/{campaign_id}/runs")

    response = await client.get(f"/api/campaigns/{campaign_id}/runs")
    assert response.status_code == 200
    assert len(response.json()) == 2