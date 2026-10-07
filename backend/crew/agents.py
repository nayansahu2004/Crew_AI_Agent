# File path: backend/crew/agents.py
"""
Agent definitions with automatic LLM fallback.

Strategy at import time:
  1. Try a minimal real call to Gemini. If it succeeds, use Gemini for
     all three agents.
  2. If Gemini fails (retired model, quota, auth, network), fall back to
     a local Ollama model -- but only if an Ollama server is reachable.
  3. If neither is available, raise with a clear message.

This module is imported lazily (on the first campaign run, from
crew_service.py), NOT when the API boots, so a problem here never stops
the API from starting.

The model names are overridable from .env without touching code:
    GEMINI_MODEL=gemini/gemini-3.8-flash
    OLLAMA_MODEL=ollama/qwen2.5:3b-instruct
Google retires model names over time; if the Gemini check starts failing
with a 404 "no longer available", update GEMINI_MODEL.
"""

import json
import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

from crewai import Agent

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini/gemini-3.8-flash")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "ollama/qwen2.5:3b-instruct")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# backend/outputs/ regardless of where uvicorn is started from.
OUTPUTS_DIR = Path(__file__).resolve().parent.parent / "outputs"


def _gemini_available() -> bool:
    """Minimal real completion call to check Gemini is usable right now
    (valid key, model exists, has quota, reachable)."""
    if not os.getenv("GEMINI_API_KEY"):
        logger.warning("GEMINI_API_KEY not set -- skipping Gemini, trying Ollama.")
        return False

    try:
        import litellm

        litellm.completion(
            model=GEMINI_MODEL,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        return True
    except Exception as exc:
        logger.warning("Gemini unavailable (%s) -- falling back to Ollama.", exc)
        return False


def _ollama_available() -> bool:
    """Is a local Ollama server up and reachable?"""
    try:
        resp = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=3)
        return resp.status_code == 200
    except Exception as exc:
        logger.warning("Ollama unavailable at %s (%s).", OLLAMA_BASE_URL, exc)
        return False


def _select_model() -> str:
    if _gemini_available():
        logger.info("Using Gemini (%s).", GEMINI_MODEL)
        return GEMINI_MODEL

    if _ollama_available():
        logger.info("Gemini unavailable -- using local Ollama (%s).", OLLAMA_MODEL)
        return OLLAMA_MODEL

    raise RuntimeError(
        "No usable LLM backend found. Gemini failed (check GEMINI_API_KEY, "
        "GEMINI_MODEL, quota, network) and no local Ollama server is "
        f"reachable at {OLLAMA_BASE_URL} (start it with `ollama serve`)."
    )


model = _select_model()


def log_discovery_step(step_output):
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    with open(OUTPUTS_DIR / "discovery_progress.jsonl", "a", encoding="utf-8") as f:
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