# Crew - Search Influencers

A multi-user website and backend for finding Instagram creators for an
influencer campaign. Each signed-in user creates campaigns and runs a search
pipeline -- Discovery -> Review -> Outreach -- that finds matching creators in
public search results, scores each one, and drafts a first email they can save
to their own Gmail or send. Everything is scoped to the user's own account.

There is no AI service in the search: it uses Google search results (through
[Serper](https://serper.dev)), pattern matching, a fixed scoring formula and
email templates. See section 8.

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
                      workflow_runs, users)
   |
   v
Search pipeline (backend/pipeline/)
   |
   +------+------+
   |      |      |
   v      v      v
Discovery Review Outreach  ---->  Serper (Google search results)
   |
   v
Creators, scores and email drafts (saved to MongoDB)
```

- **Supabase** handles sign-up, sign-in, sign-out, and session management
  entirely on the frontend. The backend never sees a password -- it only
  ever verifies an already-issued JWT.
- **MongoDB** holds all application data: users, campaigns, influencers,
  and workflow runs.
- **The search pipeline** is plain Python (section 8). Its only outside
  service is Serper.

## 2. Project structure

```
backend/
|-- api/            # Thin HTTP-layer routers -- call into services/ only
|-- core/
|   |-- config.py     # Typed Settings object, reads .env once
|   |-- database.py   # Async MongoDB connection (Motor) + indexes
|   |-- security.py   # Supabase JWT verification (get_current_user)
|   |-- errors.py     # Centralized error response shape
|   `-- friendly_errors.py  # Plain-English messages for failed runs
|-- pipeline/
|   |-- search.py     # Serper client (the only outside service)
|   |-- brief.py      # Campaign -> search terms, country, queries
|   |-- extract.py    # Handles + follower counts out of search results
|   |-- score.py      # The scoring formula
|   |-- emails.py     # Email templates
|   `-- workflow.py   # Runs the three steps; the one function the app calls
|-- models/          # Plain DB-document shapes (one per Mongo collection)
|-- schemas/         # Pydantic API request/response contracts
|-- services/        # Business logic + ownership enforcement
|   |-- auth_service.py, campaign_service.py, influencer_service.py
|   |-- run_service.py, credit_service.py
|   |-- gmail_service.py, google_client.py
|   `-- pipeline_service.py   # Runs a campaign and saves the creators
|-- scripts/         # grant_credits.py (top up a user's searches)
|-- test/            # pytest suite (no network, no real database)
|-- logs/            # This app's own logs (app.log)
|-- outputs/         # Raw search results, if PIPELINE_DEBUG_DUMP is on
`-- main.py          # FastAPI app assembly

frontend/            # React + Vite + Supabase JS client
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
| Creator search | Serper (Google search results) + plain Python |
| Background jobs | FastAPI `BackgroundTasks` (no Redis/Celery -- see below) |

### Why `BackgroundTasks` instead of a task queue

A run makes several web searches, so it can't block an HTTP request.
`BackgroundTasks` runs it in a thread pool after the response is sent --
simple, no extra infrastructure to run or deploy. A run takes seconds, so
the usual weakness (a run is lost if the server restarts mid-way) is small.
If it ever matters, moving to Redis + RQ is a contained change, mostly
isolated to `pipeline_service.py` and the runs route.

### Why `pipeline_service.py` uses a separate, synchronous MongoDB client

`BackgroundTasks` runs plain (non-async) functions in a thread pool, but
the app's main MongoDB client (Motor, async) isn't safe to use from a
different thread. `pipeline_service.py` opens its own `pymongo.MongoClient`
instead, scoped only to that file. Everywhere else in the app uses the
async Motor client via `core/database.py`.

---

## 4. Setup

### 4.1 Prerequisites

- Python 3.11+
- A [Supabase](https://supabase.com) project
- A [MongoDB Atlas](https://www.mongodb.com/atlas) cluster (or local MongoDB)
- A [Serper](https://serper.dev) API key (free credits on sign-up). That is
  the only outside service the search needs.

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
mocked (`mongomock-motor`) and the web search is replaced with canned
results, so no real request is ever made during testing.

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

## 8. The search pipeline

There is no AI in it. It runs three steps in plain Python (`backend/pipeline/`):

1. **Discovery.** The campaign's category, country and follower range become a
   handful of Google searches (mostly `site:instagram.com "<term>" <country>
   creator`), run through Serper -- at most `PIPELINE_MAX_QUERIES` (8) of them,
   stopping early once enough creators are found. Creators are then read out of
   the results: the handle from an `instagram.com/<handle>/` address, the
   follower count from the page description Instagram publishes ("96K
   Followers, ..."), the bio when it's shown. **Only what the results actually
   say is used**, so a handle or count can never be made up. Creators whose
   count is known to be outside the range are dropped.
2. **Review.** Each creator is scored out of 10 by a fixed formula and the best
   `PIPELINE_MAX_CREATORS` (15) are kept: up to 4 for a follower count in range,
   up to 4 for the campaign's category words appearing in their profile text,
   up to 2 for evidence (their own Instagram page found, a bio found, found by
   more than one search). A creator whose follower count wasn't in the results
   is kept but capped at 6 and marked "check it yourself".
3. **Outreach.** An email template is filled in for each creator. It says only
   true things (their page "came up in our search"; it names a topic only when
   their profile text does) and asks for availability, rates and a media kit.
   `[Your Name]` and `[Agency Name]` are then replaced by the signed-in user's
   own details. **Nothing is ever sent by the pipeline** -- drafts only.

`run_campaign_workflow(campaign, on_stage)` returns the finished creators, each
with its score and email attached, and `pipeline_service.py` saves them. The
`on_stage` callback is what makes the website's progress strip move in real time.

### What to expect

Results depend on what Google shows for Instagram pages, and Instagram is never
visited or scraped. Expect fewer creators than a human researcher would find,
and some without a follower count. A run that finds nothing isn't charged
(section 12). If a campaign finds little, broader category words or a wider
follower range usually help. To see exactly what a search returned, set
`PIPELINE_DEBUG_DUMP=true` and read `backend/outputs/search_debug.jsonl`.

## 9. Known limitations / possible next steps

- Follower counts come from search-result text, so they can be out of date.
- Only Instagram profiles that Google has indexed with a visible follower line
  (or that appear on a list page that gives one) can be found.
- An optional step that asks an AI model (e.g. Groq) to write a more personal
  opening line for each email could be added behind `emails.py` without
  changing anything else.
- No retry for a run interrupted by a server restart (rare, since runs take
  seconds).

---

## 10. Users, profiles and sign-up

Supabase remains the login system (passwords, user IDs). Everything else
about a person lives in our own `users` collection. The sign-up form collects
**full name, job title, company and phone**; they travel with the new account
and are saved to the profile on first sign-in. Anyone whose details are
incomplete (for example accounts that pre-date this) sees a modal they can't
dismiss until they fill them in, and can edit them later under **Settings**.

These details sign each user's own outreach emails. Running a campaign is
refused (`409 PROFILE_INCOMPLETE`) until they're complete, and the drafted
emails use the profile of the user who ran the campaign -- never anyone
else's.

Before real users arrive, configure your own email sender (SMTP) in the
Supabase dashboard (Authentication -> Emails). The built-in sender allows
only a few emails per hour for the whole project, which breaks sign-up
confirmation emails as soon as a few people register.

## 11. Gmail

Each user can connect their own Gmail account (Settings, or the one-time
prompt after sign-up). From a creator's entry they can then:

- **Save to Gmail drafts** -- puts the email in their Gmail drafts to review
  and edit there.
- **Send email** -- sends it from their account, after a confirmation. If a
  draft was saved first, that saved version is what gets sent.

Nothing is ever sent automatically: every send is one click, on one
creator's email, with a confirm step. The pipeline itself still only drafts.
The creator's email address is typed in by the user (the pipeline finds
Instagram handles, not addresses).

### How it works

Standard OAuth "authorization code" flow. `GET /api/gmail/connect` returns
Google's consent URL; Google returns the browser to
`GET /api/gmail/callback`, which stores the account's **refresh token
encrypted** (`TOKEN_ENCRYPTION_KEY`) in the `gmail_connections` collection and
redirects back to Settings. The token never reaches the browser or the logs.
The callback has no login token, so the OAuth `state` value -- HMAC-signed,
10-minute expiry -- is what ties it to the user who started the connection.

Safeguards: sends are claimed atomically (a double-click can't send twice),
capped per user per 24 hours (`GMAIL_DAILY_SEND_LIMIT`), checked for
ownership, and header-injection-safe (newlines in subjects/recipients can't
add headers). A revoked or expired connection is detected and the user is
asked to reconnect.

### Setting it up

1. In [Google Cloud Console](https://console.cloud.google.com), create a
   project and enable the **Gmail API** (APIs & Services -> Library).
2. **OAuth consent screen**: choose **Internal** if your organisation uses
   Google Workspace (no verification needed, tokens don't expire weekly);
   otherwise **External**. Add the scope
   `https://www.googleapis.com/auth/gmail.compose` (plus `openid` and
   `email`). While an External app is in *Testing*, only the test users you
   list can connect (max 100) and their access expires after 7 days.
3. **Credentials -> Create credentials -> OAuth client ID -> Web
   application.** Add the authorized redirect URI
   `http://localhost:8000/api/gmail/callback` (and your production backend's
   `/api/gmail/callback` later). Copy the client ID and secret.
4. Generate an encryption key and put everything in `.env`:
   ```
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
   ```
   GOOGLE_CLIENT_ID=...
   GOOGLE_CLIENT_SECRET=...
   TOKEN_ENCRYPTION_KEY=...
   ```
5. Restart the backend. **Settings -> Connect Gmail** should now open Google.

### Going public

`gmail.compose` is classed by Google as a *restricted* scope (check Google's
current scope list). An External app that anyone can connect must pass
Google's OAuth verification -- which needs a public privacy policy and a
verified domain -- and, for restricted scopes, an annual third-party security
assessment. If that's too heavy, dropping the "Save to Gmail drafts" button
and requesting only `gmail.send` (a lower tier) is a small code change in
`services/google_client.py`.

---

## 12. Free searches (and getting paid)

Every new account starts with 2 free searches (`FREE_RUNS_FOR_NEW_USERS`). A
**search is one run of the pipeline** on a campaign: re-running a campaign
uses another, and a run that fails is refunded. When a user has none left,
starting a run returns `402 NO_CREDITS` and the site shows how to contact the
owner. There is no payment code, on purpose: payment happens offline.

How it's stored: `users.run_credits` is a number of searches left. An account
**without** that field is unlimited -- that's everyone who signed up before this
feature, and anyone you make unlimited.

### After someone pays you

```
uv run python -m backend.scripts.grant_credits someone@example.com --show
uv run python -m backend.scripts.grant_credits someone@example.com 10
uv run python -m backend.scripts.grant_credits someone@example.com --unlimited
```

Or open the user in MongoDB Atlas (`users` collection) and edit `run_credits`
by hand (delete the field for unlimited).

### Changing the number

Set `FREE_RUNS_FOR_NEW_USERS` in the backend `.env` for new accounts, and
`VITE_FREE_SEARCHES` in the frontend `.env` so the wording on the site
matches. Existing accounts keep the balance they already have.

## 13. Public pages, owner details and search engines

`/` is the front page for visitors (signed-in users are sent to `/campaigns`),
with `/how-it-works` and `/contact`. The owner's name, role and contact details
live in **one place**, `frontend/src/lib/siteConfig.js` -- edit it there and the
footer, contact page and "out of searches" notice all follow.

For search engines the site has, on every public page, a unique title,
description and canonical link (`components/Seo.jsx`); `robots.txt` that keeps the
app, sign-in and sign-up pages out; a `sitemap.xml`; and structured data
(JSON-LD) naming the site and its owner. The last three are generated at build
time and need the site's real address:

```
VITE_SITE_URL=https://your-domain.example   # in frontend/.env, before building
```

After deploying, add the site in **Google Search Console** (verify the domain,
then submit `https://your-domain.example/sitemap.xml`) and use "Request
indexing" on the front page. Hosting must send every path to `index.html`
(on Render static sites: a rewrite from `/*` to `/index.html`).

Page content is rendered in the browser. Google handles that, but social-media
link previews and some other crawlers only read the static `index.html` --
generating the public pages ahead of time (prerendering) is the next step if
that matters to you.