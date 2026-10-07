"""
Task builders for the influencer discovery/review/outreach pipeline.

Unlike the original script version, these are now FUNCTIONS that take a
`campaign` dict and build the Task's description from it, instead of a
hardcoded campaign description. Everything else -- wording, structure, the
blunt "IMPORTANT - OUTPUT FORMAT" instructions that were needed to keep the
local model well-behaved -- is unchanged from the original tasks.py.

Expected `campaign` dict shape (matches the campaign config described in
the architecture doc):
{
    "campaign_id": "...",
    "category": "fashion",       # e.g. "fashion", "beauty", "fashion and beauty"
    "platform": "instagram",
    "country": "India",
    "min_followers": 20000,
    "max_followers": 500000,
}
"""

from crewai import Task
from backend.crew.agents import discovery_agent, reviewer_agent, outreach_agent


def build_discovery_task(campaign: dict) -> Task:
    category = campaign["category"]
    platform = campaign["platform"].capitalize()
    country = campaign["country"]
    min_followers = campaign["min_followers"]
    max_followers = campaign["max_followers"]

    description = f"""
    Find {country} {category} influencers suitable for a paid advertising campaign.
    Requirements: {platform}, {country}, {min_followers}-{max_followers} followers, {category}.
    Perform at most 2 search queries total.

    IMPORTANT - FOLLOWER RANGE:
    ONLY include creators whose follower_count is BETWEEN {min_followers} and {max_followers}
    (inclusive). If a creator's follower count is below {min_followers} or above
    {max_followers}, DO NOT include them in your output at all, even if they seem
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
      {{"name": "Example Name", "instagram_handle": "@examplehandle", "follower_count": 150000, "niche": "{category}"}}
    ]
    """

    return Task(
        description=description,
        expected_output=(
            f"A JSON array of creator objects, each with exactly the fields "
            f"name, instagram_handle, follower_count, niche, where every "
            f"follower_count is between {min_followers} and {max_followers}. "
            f"No other fields, no wrapper object, no raw search data."
        ),
        agent=discovery_agent,
    )


def build_review_task(campaign: dict) -> Task:
    # No campaign-specific values needed in the description itself --
    # kept as a function for consistency and in case per-campaign review
    # criteria are added later.
    description = """
    Review the creators discovered by the previous task.
    Analyze their content, categories, campaign suitability and overall score.

    IMPORTANT - OUTPUT FORMAT:
    Your FINAL output must be ONLY a JSON array. Each item must have EXACTLY
    these fields, and no others: name, instagram_handle, follower_count,
    niche, score (an integer 1-10), reasoning (one short sentence).
    Do NOT search the web. Do NOT include any extra wrapper object or
    metadata -- only the array.
    """

    return Task(
        description=description,
        expected_output=(
            "A JSON array of reviewed creator objects with fields: name, "
            "instagram_handle, follower_count, niche, score, reasoning."
        ),
        agent=reviewer_agent,
    )


def build_outreach_task(campaign: dict) -> Task:
    description = """
    Create personalized first-contact emails for the creators approved by the reviewer.
    Ask for availability and approximate collaboration rates/rate card.

    IMPORTANT - OUTPUT FORMAT:
    Your FINAL output must be ONLY a JSON object of this exact shape:
    {"emails": [{"creator_name": "...", "subject": "...", "body": "..."}]}
    Do NOT search the web. Do NOT include any other fields or wrapper
    structure beyond what's shown above.
    """

    return Task(
        description=description,
        expected_output=(
            'A JSON object: {"emails": [{"creator_name", "subject", "body"}]}'
        ),
        agent=outreach_agent,
    )

# from crewai import Task
# from backend.crew.agents import discovery_agent, reviewer_agent, outreach_agent


# discovery_task = Task(
#     description="""
#     Find Indian fashion and beauty influencers suitable for a paid advertising campaign.
#     Requirements: Instagram, India, 20K-500K followers, Fashion and beauty.
#     Perform at most 2 search queries total.

#     IMPORTANT - FOLLOWER RANGE:
#     ONLY include creators whose follower_count is BETWEEN 20000 and 500000
#     (inclusive). If a creator's follower count is below 20000 or above
#     500000, DO NOT include them in your output at all, even if they seem
#     like a good fit otherwise.

#     IMPORTANT - OUTPUT FORMAT:
#     Your FINAL output must be ONLY a JSON array. Each item in the array must
#     have EXACTLY these 4 fields, and no others:
#       - name
#       - instagram_handle
#       - follower_count
#       - niche

#     Do NOT include search result metadata such as titles, links, snippets,
#     search_summary, campaign_requirements, or any other wrapper object.
#     Do NOT return the raw search results. You must READ the search snippets
#     and PULL OUT the actual creator names, handles, follower counts, and
#     niches into the 4 fields above. If a field is not available for a given
#     creator, use null for that field -- do not omit the creator entirely
#     (unless they fail the follower range check above).

#     Example of the EXACT shape required:
#     [
#       {"name": "Example Name", "instagram_handle": "@examplehandle", "follower_count": 150000, "niche": "Fashion"}
#     ]
#     """,
#     expected_output=(
#         "A JSON array of creator objects, each with exactly the fields "
#         "name, instagram_handle, follower_count, niche, where every "
#         "follower_count is between 20000 and 500000. No other fields, "
#         "no wrapper object, no raw search data."
#     ),
#     agent=discovery_agent,
# )

# review_task = Task(
#     description="""
#     Review the creators discovered by the previous task.
#     Analyze their content, categories, campaign suitability and overall score.

#     IMPORTANT - OUTPUT FORMAT:
#     Your FINAL output must be ONLY a JSON array. Each item must have EXACTLY
#     these fields, and no others: name, instagram_handle, follower_count,
#     niche, score (an integer 1-10), reasoning (one short sentence).
#     Do NOT search the web. Do NOT include any extra wrapper object or
#     metadata -- only the array.
#     """,
#     expected_output=(
#         "A JSON array of reviewed creator objects with fields: name, "
#         "instagram_handle, follower_count, niche, score, reasoning."
#     ),
#     agent=reviewer_agent,
# )

# outreach_task = Task(
#     description="""
#     Create personalized first-contact emails for the creators approved by the reviewer.
#     Ask for availability and approximate collaboration rates/rate card.

#     IMPORTANT - OUTPUT FORMAT:
#     Your FINAL output must be ONLY a JSON object of this exact shape:
#     {"emails": [{"creator_name": "...", "subject": "...", "body": "..."}]}
#     Do NOT search the web. Do NOT include any other fields or wrapper
#     structure beyond what's shown above.
#     """,
#     expected_output=(
#         'A JSON object: {"emails": [{"creator_name", "subject", "body"}]}'
#     ),
#     agent=outreach_agent,
# )