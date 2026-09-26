from crewai import Task
from agents import discovery_agent, reviewer_agent, outreach_agent


discovery_task = Task(
    description="""
    Find Indian fashion and beauty influencers suitable for a paid advertising campaign.
    Requirements: Instagram, India, 20K-500K followers, Fashion and beauty.
    Perform at most 2 search queries total.

    IMPORTANT - FOLLOWER RANGE:
    ONLY include creators whose follower_count is BETWEEN 20000 and 500000
    (inclusive). If a creator's follower count is below 20000 or above
    500000, DO NOT include them in your output at all, even if they seem
    like a good fit otherwise.

    IMPORTANT - OUTPUT FORMAT:
    Your FINAL output must be ONLY a JSON array. Each item in the array must
    have EXACTLY these 4 fields, and no others:
      - name
      - instagram_handle
      - follower_count
      - niche

    Do NOT include search result metadata such as titles, links, snippets,
    search_summary, campaign_requirements, or any other wrapper object.
    Do NOT return the raw search results. You must READ the search snippets
    and PULL OUT the actual creator names, handles, follower counts, and
    niches into the 4 fields above. If a field is not available for a given
    creator, use null for that field -- do not omit the creator entirely
    (unless they fail the follower range check above).

    Example of the EXACT shape required:
    [
      {"name": "Example Name", "instagram_handle": "@examplehandle", "follower_count": 150000, "niche": "Fashion"}
    ]
    """,
    expected_output=(
        "A JSON array of creator objects, each with exactly the fields "
        "name, instagram_handle, follower_count, niche, where every "
        "follower_count is between 20000 and 500000. No other fields, "
        "no wrapper object, no raw search data."
    ),
    agent=discovery_agent,
)

review_task = Task(
    description="""
    Review the creators discovered by the previous task.
    Analyze their content, categories, campaign suitability and overall score.

    IMPORTANT - OUTPUT FORMAT:
    Your FINAL output must be ONLY a JSON array. Each item must have EXACTLY
    these fields, and no others: name, instagram_handle, follower_count,
    niche, score (an integer 1-10), reasoning (one short sentence).
    Do NOT search the web. Do NOT include any extra wrapper object or
    metadata -- only the array.
    """,
    expected_output=(
        "A JSON array of reviewed creator objects with fields: name, "
        "instagram_handle, follower_count, niche, score, reasoning."
    ),
    agent=reviewer_agent,
)

outreach_task = Task(
    description="""
    Create personalized first-contact emails for the creators approved by the reviewer.
    Ask for availability and approximate collaboration rates/rate card.

    IMPORTANT - OUTPUT FORMAT:
    Your FINAL output must be ONLY a JSON object of this exact shape:
    {"emails": [{"creator_name": "...", "subject": "...", "body": "..."}]}
    Do NOT search the web. Do NOT include any other fields or wrapper
    structure beyond what's shown above.
    """,
    expected_output=(
        'A JSON object: {"emails": [{"creator_name", "subject", "body"}]}'
    ),
    agent=outreach_agent,
)