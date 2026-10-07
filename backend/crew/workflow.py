"""
Single entry point for running the Discovery -> Review -> Outreach pipeline.

This replaces the old top-level script (backend/main.py) as the place
where Crew(...).kickoff() actually gets called. Nothing outside this file
should import Crew/Process directly -- services/crew_service.py (added in
a later phase) will call run_campaign_workflow() from a background task.
"""

from crewai import Crew, Process

from backend.crew.tasks import (
    build_discovery_task,
    build_review_task,
    build_outreach_task,
)


def run_campaign_workflow(campaign: dict) -> dict:
    """
    Runs the full discovery/review/outreach pipeline for a single campaign.

    Args:
        campaign: dict with keys campaign_id, category, platform, country,
                  min_followers, max_followers (see tasks.py for the exact
                  shape expected).

    Returns:
        A dict with the raw output of each stage, e.g.:
        {
            "discovery_result": <str or parsed JSON>,
            "review_result": <str or parsed JSON>,
            "outreach_result": <str or parsed JSON>,
        }

        NOTE: This function does NOT touch MongoDB. Persisting each stage's
        result is the responsibility of the caller (crew_service.py),
        which should update the workflow_run's status/current_stage before
        and after each stage, and save influencer/outreach data as it
        becomes available -- not just at the very end.
    """
    discovery_task = build_discovery_task(campaign)
    review_task = build_review_task(campaign)
    outreach_task = build_outreach_task(campaign)

    crew = Crew(
        agents=[
            discovery_task.agent,
            review_task.agent,
            outreach_task.agent,
        ],
        tasks=[discovery_task, review_task, outreach_task],
        process=Process.sequential,
        verbose=True,
    )

    crew.kickoff()

    return {
        "discovery_result": discovery_task.output.raw if discovery_task.output else None,
        "review_result": review_task.output.raw if review_task.output else None,
        "outreach_result": outreach_task.output.raw if outreach_task.output else None,
    }