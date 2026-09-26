# from dotenv import load_dotenv
# import os
# from google import genai

# load_dotenv()

# api_key = os.getenv("GEMINI_API_KEY")

# if not api_key:
#     raise ValueError("GEMINI_API_KEY not found in .env")

# print("API key loaded successfully.")

# client = genai.Client(api_key=api_key)

# print("Sending request to Gemini...")

# response = client.models.generate_content(
#     model="gemini-3.5-flash",
#     contents="Tell me a very short joke."
# )

# print("\nGemini response:")
# print(response.text)


"""
test.py -- Step 6 sanity check.

Runs ONLY the discovery_agent, with a trivial task that needs no web search,
so we can confirm three things in isolation before spending time on a full
crew run:
  1. The agent instantiates correctly (from_repository + local Ollama model)
  2. reasoning=False actually prevents the create_reasoning_plan loop
  3. The model can follow instructions and return real, non-empty output

Run with:  python test.py
"""

from dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Task, Crew, Process

model = "ollama/qwen2.5:3b-instruct"

discovery_agent = Agent(
    from_repository="influencer-model-discovery-specialist",
    llm=model,
    reasoning=False,           # should stop the create_reasoning_plan loop entirely
    max_reasoning_attempts=1,  # backup cap, in case reasoning=False isn't fully honored
)

# Deliberately trivial and tool-free -- if this fails, the problem is the
# model/agent setup itself, not Serper, not the real task's complexity.
test_task = Task(
    description=(
        "Without using any tools or searching the web, list 3 EXAMPLE "
        "Indian fashion/beauty Instagram influencer profiles (made-up names "
        "are fine for this test). Return ONLY a JSON list, each item with "
        "keys: name, instagram_handle, follower_count, niche."
    ),
    expected_output="A JSON list of 3 example creator objects.",
    agent=discovery_agent,
)

crew = Crew(
    agents=[discovery_agent],
    tasks=[test_task],
    process=Process.sequential,
    verbose=True,
)

result = crew.kickoff()

print("\n" + "=" * 60)
print("RAW RESULT:")
print(result)
print("=" * 60)

# Quick automated sanity check -- catches the "Task Completed but empty"
# problem you hit last time, instead of eyeballing it.
result_str = str(result).strip()
if not result_str or "(no result)" in result_str or result_str == "[]":
    print("\n[FAIL] Got an empty/placeholder result. reasoning or tool-calling "
          "is likely still broken -- do not proceed to the full crew yet.")
else:
    print("\n[PASS] Got a non-empty response. Check above that it's actually "
          "valid JSON with 3 real-looking items, then move on to the full "
          "pipeline.")