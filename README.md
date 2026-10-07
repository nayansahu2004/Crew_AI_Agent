# Crew AI Influencer Agency

A multi-user backend for running AI-driven influencer marketing campaigns.
Each signed-in user creates campaigns, kicks off an automated
Discovery -> Review -> Outreach pipeline (built on
[CrewAI](https://crewai.com)), and sees the results -- all scoped to
their own data.

---

## 1. Architecture

```
Frontend
   |
   | HTTPS + JWT (Authorization: Bearer <token>)
   v
FastAPI Backend
   |
   +----------------------+
   |                      |
   v                      v
Supabase Auth          MongoDB
(verifies the JWT)   (campaigns, influencers,
   |                  workflow_runs, users)
   |                      |
   +----------+-----------+
              |
              v
        CrewAI Workflow
              |
       +------+------+
       |      |      |
       v      v      v
   Discovery Review Outreach
       |
       v
Influencer / Campaign Results (persisted to MongoDB)
```

- **Supabase** handles sign-up, sign-in, sign-out, and session management
  entirely on the frontend. The backend never sees a password -- it only
  ever verifies an already-issued JWT.
- **MongoDB** holds all application data: users, campaigns, influencers,
  and workflow runs.
- **CrewAI** runs the actual AI pipeline, using Gemini by default with an
  automatic fallback to a local Ollama model if Gemini is unavailable.

### Request flow

```
User signs in with Supabase
        -> Frontend receives a JWT (access_token)
        -> Frontend sends it as Authorization: Bearer <token>
        -> FastAPI verifies the JWT and extracts the Supabase user ID
        -> That ID (never one sent by the client) is used for every
           ownership check and every database write
```

---

## 2. Project structure

```
backend/
|-- api/            # Thin HTTP-layer routers -- call into services/ only
|-- core/
|   |-- config.py     # Typed Settings object, reads .env once
|   |-- database.py   # Async MongoDB connection (Motor) + indexes
|   |-- security.py   # Supabase JWT verification (get_current_user)
|   `-- errors.py     # Centralized error response shape
|-- crew/
|   |-- agents.py     # Agent definitions + Gemini/Ollama fallback logic
|   |-- tasks.py       # Task builders, driven by campaign config
|   `-- workflow.py     # The single Crew().kickoff() entry point
|-- models/          # Plain DB-document shapes (one per Mongo collection)
|-- schemas/         # Pydantic API request/response contracts
|-- services/        # Business logic + ownership enforcement
|   |-- auth_service.py
|   |-- campaign_service.py
|   |-- influencer_service.py
|   |-- run_service.py
|   `-- crew_service.py   # Orchestrates a full campaign run
|-- test/            # pytest suite (CrewAI + MongoDB both mocked)
|-- logs/            # This app's own logs (app.log)
|-- outputs/         # Raw CrewAI run artifacts (discovery_progress.jsonl)
`-- main.py          # FastAPI app assembly

frontend/            # (planned: React + Vite + Supabase JS client)
```

**Why `models/` and `schemas/` are separate:** `models/` mirrors what's
actually stored in MongoDB; `schemas/` defines what the API accepts and
returns. Keeping them apart means an internal-only DB field never
accidentally leaks into a response, and an API contract change never
forces a DB migration.

**Why routes never query the database directly:** every service
function that touches a specific campaign/influencer/run takes the
*authenticated* user ID and enforces ownership itself (404 if the
resource doesn't exist, 403 if it exists but belongs to someone else).

---

## 3. Technology stack

| Layer | Choice |
|---|---|
| API framework | FastAPI + Uvicorn |
| Auth | Supabase Auth (JWT, verified via JWKS) |
| Database | MongoDB Atlas, via Motor (async) |
| AI orchestration | CrewAI |
| LLM | Gemini (primary), local Ollama (automatic fallback) |
| Search/scraping tools | Serper, Firecrawl, Tavily |
| Background jobs | FastAPI `BackgroundTasks` (no Redis/Celery -- see below) |

### Why `BackgroundTasks` instead of a task queue

A CrewAI run takes minutes, so it can't block an HTTP request.
`BackgroundTasks` runs it in a thread pool after the response is sent --
simple, no extra infrastructure to run or deploy. The tradeoff: a run is
lost if the server restarts mid-execution, and there's no built-in
retry. If that becomes a real problem, moving to Redis + RQ is a
contained change, mostly isolated to `crew_service.py` and the runs
route.

### Why `crew_service.py` uses a separate, synchronous MongoDB client

`BackgroundTasks` runs plain (non-async) functions in a thread pool, but
the app's main MongoDB client (Motor, async) isn't safe to use from a
different thread. `crew_service.py` opens its own `pymongo.MongoClient`
instead, scoped only to that file. Everywhere else in the app uses the
async Motor client via `core/database.py`.

### Why CrewAI is imported lazily

`crew_service.py` imports `crew/workflow.py` *inside* the function that
runs a campaign, not at module load time. Importing the real crew code
triggers a Gemini health check, an Ollama reachability check, and
fetches all three agents from the CrewAI repository (which needs a valid
`crewai login` session). If any of that failed at API startup, the
*entire* API would refuse to boot -- including routes that have nothing
to do with AI. Now, a crew-loading problem only fails that one run,
recorded as `status: "failed"` with the error message, while the rest of
the API keeps working.

---

## 4. Setup

### 4.1 Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com) project
- A [MongoDB Atlas](https://www.mongodb.com/atlas) cluster (or local MongoDB)
- API keys: [Serper](https://serper.dev), [Firecrawl](https://firecrawl.dev),
  [Tavily](https://tavily.com), and optionally
  [Gemini](https://ai.google.dev)
- [Ollama](https://ollama.com) installed locally, for the Gemini fallback
  (`ollama pull qwen2.5:3b-instruct`)
- A `crewai login` session (the agents are pulled from CrewAI's
  repository, not defined locally)

### 4.2 Environment variables

```
cp .env.example .env
```

Then fill in real values. See `.env.example` for the full list with
explanations of which are required vs. optional. The two most
easily-missed ones:

- `SUPABASE_URL` -- your project's API URL, **not** the Postgres
  connection string.
- `MONGODB_URI` -- get a fresh one from Atlas -> Connect -> Drivers, with
  the password already substituted in (and percent-encoded, if it
  contains special characters).

### 4.3 Install dependencies

```
uv pip install -r requirements.txt
uv pip install -r requirements-dev.txt   # only needed to run tests
```

### 4.4 Run the server

From the **project root** (the folder containing `backend/`), since all
imports use the `backend.` prefix:

```
uv run uvicorn backend.main:app --reload
```

Check:
- `http://localhost:8000/health` -> `{"status": "ok"}`
- `http://localhost:8000/docs` -> interactive API docs (Swagger)

### 4.5 Run the tests

```
uv run pytest backend/test/ -v
```

The test suite needs no real credentials or network access -- MongoDB is
mocked (`mongomock-motor`) and CrewAI execution is mocked at the route
level, so no Gemini/Serper/Ollama calls ever happen during testing.

---

## 5. Authentication

The frontend handles Supabase sign-up/sign-in entirely and sends the
resulting JWT on every request:

```
Authorization: Bearer <access_token>
```

`core/security.py`'s `get_current_user()` dependency verifies that token
two ways, depending on how your Supabase project signs tokens:

- **Asymmetric (ES256/RS256)** -- the default for newer projects.
  Verified against the project's public keys, fetched automatically from
  `<SUPABASE_URL>/auth/v1/.well-known/jwks.json`. No secret needed.
- **Legacy shared secret (HS256)** -- older projects. Requires
  `SUPABASE_JWT_SECRET` in `.env` (Supabase dashboard -> Project Settings
  -> JWT Keys -> Legacy JWT Secret).

Every protected route takes `user: AuthenticatedUser = Depends(get_current_user)`.
The user's ID always comes from the verified token -- **never** from a
request body or query parameter, even if the frontend sends one.

---

## 6. Database

### Collections

| Collection | Key fields |
|---|---|
| `users` | `supabase_user_id` (unique index), `email`, `name`, `company_name` |
| `campaigns` | `user_id`, `name`, `category`, `target_country`, `min_followers`, `max_followers`, `platform`, `status` |
| `influencers` | `campaign_id`, `user_id`, `name`, `username`, `followers`, `review_score`, `review_status`, `outreach_status` |
| `workflow_runs` | `campaign_id`, `user_id`, `status`, `current_stage`, `result_summary` |

Indexes are created automatically on startup (`core/database.py`):
`users.supabase_user_id` (unique), and `user_id`/`campaign_id` on the
other three collections.

### Error response shape

Every error from the API has the same JSON shape:

```json
{
  "success": false,
  "error": {
    "code": "CAMPAIGN_NOT_FOUND",
    "message": "Campaign not found."
  }
}
```

Internal errors (a real bug, a DB hiccup) are logged in full
server-side, but the client only ever sees a generic
`"An unexpected error occurred."` -- never a stack trace.

---

## 7. API endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/health`, `/api/health` | Health check |
| GET | `/api/users/me` | Get (or auto-create) the current user's profile |
| POST | `/api/users/me` | Update the current user's profile |
| POST | `/api/campaigns` | Create a campaign |
| GET | `/api/campaigns` | List the current user's campaigns |
| GET | `/api/campaigns/{id}` | Get one campaign |
| PATCH | `/api/campaigns/{id}` | Update a campaign |
| DELETE | `/api/campaigns/{id}` | Delete a campaign |
| GET | `/api/campaigns/{id}/influencers` | List influencers discovered for a campaign |
| GET | `/api/influencers/{id}` | Get one influencer |
| PATCH | `/api/influencers/{id}` | Update an influencer's review/outreach state |
| POST | `/api/campaigns/{id}/runs` | Start a campaign run (returns immediately, `202`) |
| GET | `/api/runs/{id}` | Poll a run's status |
| GET | `/api/campaigns/{id}/runs` | List a campaign's past runs |

Full interactive docs, with request/response schemas, at `/docs` once
the server is running.

---

## 8. The CrewAI pipeline

Three agents, pulled from CrewAI's Agent Repository (not defined
locally) via `from_repository`, run sequentially:

1. **Discovery** -- searches the web (via Serper) for creators matching
   the campaign's category/platform/country/follower range.
2. **Review** -- scores each discovered creator for campaign suitability
   (no web access).
3. **Outreach** -- drafts a personalized first-contact email per
   reviewed creator (no web access). **Nothing is ever actually sent** --
   this produces drafts only, stored with `outreach_status: "drafted"`.

### LLM strategy

`crew/agents.py` tries Gemini first with a real, minimal health-check
call. If that fails (quota, outage, bad model name), it checks for a
reachable local Ollama server and uses that instead. If neither is
available, the run fails with a clear error -- the rest of the API keeps
running regardless.

### A known limitation

Review and Outreach results are matched back to the influencer documents
Discovery created using `instagram_handle` / `name` -- the only fields
the agents currently echo consistently across stages. A typo or
differently-phrased name between stages will silently fail to match,
leaving that influencer's `review_score` or `outreach_status` unset. A
more robust version would have each stage pass through a stable ID
instead of matching on free-text fields.

---

## 9. Known limitations / possible next steps

- Run progress is coarse: the whole pipeline runs inside one blocking
  `crew.kickoff()` call, so `current_stage` doesn't update live
  stage-by-stage -- it jumps from `discovery` to `completed`.
- No retry or durability for a run interrupted by a server restart (see
  `BackgroundTasks` discussion above).
- The Reviewer's `score` is prompted as 1-10 but has been observed
  returning a 0-100 scale in some runs -- not yet strictly enforced.
- `frontend/` is not yet built.