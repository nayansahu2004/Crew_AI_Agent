"""---------THIS IS THE GEMINI CODE ON THE TOP------"""

# import json
# import os

# from dotenv import load_dotenv
# from crewai import Agent


# # ---------------------------------------------------------
# # Load environment variables from .env
# # ---------------------------------------------------------
# load_dotenv()


# # ---------------------------------------------------------
# # Verify Gemini API key
# # ---------------------------------------------------------
# GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# if not GEMINI_API_KEY:
#     raise ValueError(
#         "GEMINI_API_KEY was not found. "
#         "Make sure it is defined in your .env file."
#     )


# # ---------------------------------------------------------
# # MODEL
# # ---------------------------------------------------------
# model = "gemini-3.8-flash"


# # ---------------------------------------------------------
# # Logging callback
# # ---------------------------------------------------------
# def log_discovery_step(step_output):
#     os.makedirs("outputs", exist_ok=True)

#     with open(
#         "outputs/discovery_progress.jsonl",
#         "a",
#         encoding="utf-8"
#     ) as f:
#         f.write(
#             json.dumps(
#                 {"step": str(step_output)},
#                 ensure_ascii=False
#             ) + "\n"
#         )


# # ---------------------------------------------------------
# # DISCOVERY AGENT
# # ---------------------------------------------------------
# discovery_agent = Agent(
#     from_repository="influencer-model-discovery-specialist",
#     llm=model,
#     step_callback=log_discovery_step,
#     planning=False,
#     reasoning= False,
#     max_reasoning_attempts=1
# )


# # ---------------------------------------------------------
# # REVIEWER AGENT
# # ---------------------------------------------------------
# reviewer_agent = Agent(
#     from_repository="influencer-model-profile-reviewer",
#     llm=model,
#     step_callback=log_discovery_step,
#     planning=False,
#     reasoning= False,
#     max_reasoning_attempts=1
# )


# # ---------------------------------------------------------
# # OUTREACH AGENT
# # ---------------------------------------------------------
# outreach_agent = Agent(
#     from_repository="influencer-outreach-partnership-specialist",
#     llm=model,
#     step_callback=log_discovery_step,
#     planning=False,
#     reasoning= False,
#     max_reasoning_attempts=1
# )


"""---------THIS IS THE OLLAMA QWEN CODE ON THE TOP------"""

from dotenv import load_dotenv
import json
import os

load_dotenv()

from crewai import Agent

model = "ollama/qwen2.5:3b-instruct"

def log_discovery_step(step_output):
    os.makedirs("outputs", exist_ok=True)
    with open("outputs/discovery_progress.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"step": str(step_output)}, ensure_ascii=False) + "\n")


discovery_agent = Agent(
    from_repository="influencer-model-discovery-specialist",
    llm=model,
    reasoning=False,
    max_reasoning_attempts=1,
    step_callback=log_discovery_step,
)

reviewer_agent = Agent(
    from_repository="influencer-model-profile-reviewer",
    llm=model,
    reasoning=False,
    max_reasoning_attempts=1,
)

outreach_agent = Agent(
    from_repository="influencer-outreach-partnership-specialist",
    llm=model,
    reasoning=False,
    max_reasoning_attempts=1,
)