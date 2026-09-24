from crewai import Task
from agents import discovery_agent, reviewer_agent, outreach_agent


discovery_task = Task(
    description="""
    Find Indian fashion and beauty influencers suitable for a paid advertising campaign.
    Requirements: Instagram, India, 20K-500K followers, Fashion and beauty.
    """,
    expected_output="Structured JSON list of relevant creators",
    agent=discovery_agent
)

review_task = Task(
    description="""
    Review the creators discovered by the previous task.
    Analyze their content, categories, campaign suitability and overall score.
    """,
    expected_output="Structured JSON review of each creator",
    agent=reviewer_agent
)

outreach_task = Task(
    description="""
    Create personalized first-contact emails for the creators approved by the reviewer.
    Ask for availability and approximate collaboration rates/rate card.
    """,
    expected_output="Personalized email drafts in JSON",
    agent=outreach_agent
)