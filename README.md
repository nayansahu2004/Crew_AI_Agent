# Influencer Outreach Agent Pipeline

A multi-agent system that automates the front end of an influencer marketing
campaign: finding relevant creators, evaluating them, and drafting
personalized first-contact emails — built on [CrewAI](https://crewai.com),
running fully locally on [Ollama](https://ollama.com).

---

## 1. What this does

Given a campaign brief (currently hardcoded as "Indian fashion and beauty
influencers, Instagram, 20K–500K followers"), the pipeline runs three agents
in sequence:

```
Discovery  →  Review  →  Outreach
```

1. **Discovery** searches the web and produces a filtered, structured list
   of candidate creators.
2. **Review** scores each candidate for campaign suitability, reasoning
   over the data with no further web access.
3. **Outreach** drafts a personalized first-contact email for each
   reviewed creator, asking about availability and rates.

The end result is a JSON object of draft emails, meant for **human review
before sending** — nothing in this pipeline sends email on its own.

---

## 2. Architecture

### 2.1 High-level flow

```
                     ┌─────────────────┐
                     │   main.py       │
                     │  (Crew, kickoff)│
                     └────────┬────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                      ▼
  ┌───────────┐        ┌────────────┐        ┌──────────────┐
  │ Discovery │  ──▶   │  Review    │  ──▶   │  Outreach     │
  │  Agent    │ output │  Agent     │ output │  Agent        │
  └─────┬─────┘        └────────────┘        └───────────────┘
        │
        ▼
  search_the_internet_with_serper
  (web search tool)
```

`Process.sequential` means each task's output is automatically passed as
context into the next task — you don't have to manually thread data between
agents.

### 2.2 Files

| File | Responsibility |
|---|---|
| `agents.py` | Defines the three `Agent` objects (pulled from the CrewAI dashboard via `from_repository`), the LLM config, and a step-logging callback. |
| `tasks.py` | Defines the three `Task` objects — campaign instructions, output-format contracts, and which agent runs each one. |
| `main.py` | Wires everything into a `Crew` and calls `.kickoff()`. |
| `.env` | API keys (see [Configuration](#4-configuration)). |
| `outputs/` | Run artifacts: step logs, saved results. |

### 2.3 Agents

The three agents are **not defined in this codebase** — they live in the
CrewAI dashboard's Agent Repository and are pulled in by name via
`from_repository=`. This means their role, goal, backstory, and attached
tools are configured centrally and shared across any project that
references them.

| Agent | Repository slug | Tools attached (dashboard-configured) |
|---|---|---|
| Discovery | `influencer-model-discovery-specialist` | Serper web search |
| Reviewer | `influencer-model-profile-reviewer` | Firecrawl (scraping), Tavily (extraction) — currently unused by the task as written |
| Outreach | `influencer-outreach-partnership-specialist` | none |

Each agent is instantiated locally with two important overrides:

```python
Agent(
    from_repository="...",
    llm=model,                   # overrides the dashboard's default LLM
    reasoning=False,             # disables CrewAI's internal planning step
    max_reasoning_attempts=1,    # safety cap if reasoning can't be fully disabled
)
```

### 2.4 Why `reasoning=False`

CrewAI agents have an optional internal "reasoning" feature that, before
executing a task, asks the LLM to generate a multi-step plan
(`create_reasoning_plan`) and then evaluates each step afterward
(`planner_observer`). In testing, this added **several extra LLM calls per
task** on top of the actual work, and on a small local model it produced
malformed function calls that crashed the run entirely. Disabling it:

- Removes 3+ hidden LLM calls per task
- Removes a class of crashes tied to the small model misusing the
  planning tool's arguments
- Makes the number of LLM calls per run predictable

### 2.5 Why the task descriptions are unusually explicit

Smaller local models (this project currently targets **3B-parameter**
models) are less reliable at inferring format requirements from
naturally-written instructions. Two failure modes were observed and fixed
by making task descriptions more explicit and structured:

- **Raw data pass-through**: the Discovery agent, when using the search
  tool, would sometimes return the raw Serper API response instead of
  extracting structured fields. Fixed by adding a dedicated, all-caps
  `IMPORTANT - OUTPUT FORMAT` block naming the exact fields required and
  explicitly forbidding the raw-response fields.
- **Ignored filters**: numeric constraints (e.g. follower range) stated
  only in prose were sometimes not applied. Fixed by giving the constraint
  its own explicit block with a hard rule ("DO NOT include... even if they
  seem like a good fit otherwise").

**Takeaway for future task-writing in this project:** don't rely on a
single sentence buried in a paragraph for anything that must be enforced
exactly (output shape, numeric ranges, forbidden fields). Give it its own
labeled block.

---

## 3. LLM strategy

This project has run against three different backends over its
development; the tradeoffs are documented here for future reference.

| Backend | Outcome |
|---|---|
| Groq (`llama-3.3-70b-versatile`) | Worked, but hit daily free-tier quota quickly. |
| Gemini (`gemini-2.0-flash` and others) | Worked, but hit a very tight per-minute free-tier quota (as low as 5 requests/minute), which combined with CrewAI's internal reasoning/observer calls made even a single task run unreliable. |
| **Ollama, local (`qwen2.5:3b-instruct`)** | **Current default.** No quota, unlimited iteration, but requires local compute (tested on 8GB RAM + RTX 3050) and a smaller model, which needs the explicit-prompting mitigations above. |

The model is set in one place, `agents.py`:

```python
model = "ollama/qwen2.5:3b-instruct"
```

Swapping providers only requires changing this string (plus the matching
API key in `.env`), since CrewAI routes all providers through LiteLLM
under a common interface.

**A smaller model (`qwen2.5:0.5b`) was tried first and rejected** — it
could not reliably produce correctly-structured tool calls (wrong argument
names to CrewAI's internal functions) and eventually returned empty LLM
responses. 3B is the current practical floor for this pipeline's
tool-calling and formatting requirements on this hardware.

---

## 4. Configuration

### 4.1 `.env`

```
SERPER_API_KEY=...       # web search — get from serper.dev
FIRECRAWL_API_KEY=...    # scraping — get from firecrawl.dev (Reviewer agent)
TAVILY_API_KEY=...       # extraction — get from tavily.com (Reviewer agent)

# Only needed if using a cloud LLM instead of local Ollama:
# GROQ_API_KEY=...
# GEMINI_API_KEY=...
```

### 4.2 Local model setup (Ollama)

```
ollama pull qwen2.5:3b-instruct
```

Ollama must be running (`ollama serve`, or as a background service)
before `main.py` is run. LiteLLM expects it at `http://localhost:11434`
by default.

### 4.3 CrewAI platform auth

`from_repository=` requires being logged into the CrewAI platform CLI:

```
uv run crewai login
```

This is a **separate auth layer** from any LLM provider key — it's what
lets this codebase pull agent definitions from the dashboard. Sessions can
expire; if you see `AuthError: No token found`, run `crewai login` again.

---

## 5. Running it

```
python main.py
```

To capture full output to a file (recommended — terminal scrollback is
limited and errors can be long):

```
python main.py *>&1 | Tee-Object -FilePath run_log.txt      # PowerShell
```

### 5.1 Incremental testing

Before running the full three-agent pipeline, it's strongly recommended to
test in isolation — this project's development history shows most bugs
are much easier to diagnose one agent at a time:

- **`test.py`** — runs only the Discovery agent, with a trivial,
  tool-free task, to confirm the model/agent setup itself works.
- **`test_with_tools.py`** — runs only the Discovery agent with the real
  task and Serper enabled, to confirm tool-calling and output-formatting
  work together before adding the other two agents back in.

Both scripts include an automated `[PASS]`/`[FAIL]` check on the result,
since **`Task Completed` in CrewAI's logs does not guarantee the output
contains real data** — an empty or placeholder result can still report as
completed.

---

## 6. Known limitations / things to revisit

- **Reviewer's score scale**: the task asks for an integer 1–10, but the
  model has been observed returning a 1–100 scale instead. Not yet
  enforced strictly.
- **Reviewer's attached tools (Firecrawl, Tavily) are unused** by the
  current task description, which explicitly forbids web access during
  review. If deeper profile verification is wanted later, the task
  description would need to opt back into using them.
- **Small sample sizes during testing**: Discovery is currently capped at
  2 search queries for cost/speed reasons. Real campaign runs will need
  more searches, which should be re-validated against the follower-range
  and output-format instructions, since a 3B model's reliability can shift
  with longer/more complex context.
- **No retry/rate-limit handling for local inference** — a local model
  won't hit HTTP 429s, but very long runs on limited hardware can be slow;
  there's currently no timeout tuning beyond CrewAI's defaults.
- **No email-sending integration** — output is a draft JSON object only,
  by design, pending human review.

---

## 7. Alternative: hand-rolled version (for comparison)

A minimal, framework-free version of this same pipeline (direct API calls
+ a manual tool-calling loop, no CrewAI) exists alongside this project as
`hand_rolled_agents.py`, written to make CrewAI's internal behavior
(the agentic loop, tool-call parsing, task chaining) explicit and directly
controllable. It trades CrewAI's `from_repository` convenience and nicer
tracing UI for full visibility into exactly how many LLM calls each stage
makes — useful context if free-tier/local compute limits become a
recurring constraint.