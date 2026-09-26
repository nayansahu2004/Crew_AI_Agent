"""
test_with_tools.py -- v2, with a much more explicit/forceful final
instruction about output format, since the model was previously just
dumping raw Serper search results instead of extracting structured data.
"""

from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew, Process

model = "ollama/qwen2.5:3b-instruct"

discovery_agent = Agent(
    from_repository="influencer-model-discovery-specialist",
    llm=model,
    reasoning=False,
    max_reasoning_attempts=1,
)

discovery_task = Task(
    description="""
    Find Indian fashion and beauty influencers suitable for a paid advertising campaign.
    Requirements: Instagram, India, 20K-500K followers, Fashion and beauty.
    Perform at most 2 search queries total.

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
    creator, use null for that field -- do not omit the creator entirely.

    Example of the EXACT shape required:
    [
      {"name": "Example Name", "instagram_handle": "@examplehandle", "follower_count": 150000, "niche": "Fashion"}
    ]
    """,
    expected_output=(
        "A JSON array of creator objects, each with exactly the fields "
        "name, instagram_handle, follower_count, niche. No other fields, "
        "no wrapper object, no raw search data."
    ),
    agent=discovery_agent,
)

crew = Crew(
    agents=[discovery_agent],
    tasks=[discovery_task],
    process=Process.sequential,
    verbose=True,
)

result = crew.kickoff()

print("\n" + "=" * 60)
print("RAW RESULT:")
print(result)
print("=" * 60)

result_str = str(result).strip()

if not result_str or "(no result)" in result_str or result_str == "[]":
    print("\n[FAIL] Empty/placeholder result.")
elif "search_summary" in result_str or "organic_results" in result_str or "snippet" in result_str:
    print("\n[FAIL] Still returning raw search data instead of extracted "
          "fields. The model may not be following the format instruction "
          "even when it's explicit -- may need a stronger model or a "
          "separate post-processing step.")
else:
    print("\n[PASS] Got extracted, structured creator data. Safe to move "
          "on to the full 3-agent crew now.")