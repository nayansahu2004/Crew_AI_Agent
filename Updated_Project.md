# Deploying Crew - Search Influencers (free, first time)

Plan: **website on Vercel**, **backend on Render**, using the database and
sign-in you already have (MongoDB Atlas, Supabase). Allow about an hour the
first time. Do the parts **in order**: later parts need web addresses you only
get from earlier ones.

```
Visitor's browser
      │
      ▼
 Vercel  ── the website (React)        https://crew-search-influencers.vercel.app
      │
      ▼
 Render  ── the backend (API)          https://crew-search-influencers-api.onrender.com
      │
      ├──► MongoDB Atlas   (your data)
      ├──► Supabase        (sign-in)
      ├──► Google          (Gmail connection)
      └──► Serper          (the creator search)
```

The backend is small (about 65 MB of memory), so Render's free plan is enough,
your code stays in a **private** repository, and there's nothing else to host.
One trade-off: Render's free service **goes to sleep after 15 minutes without
visitors**, and the next visit takes 30–60 seconds to wake it (Part 8 shows a
free way to keep it awake).

---

## Part 1 — Prepare the project (on your computer)

1. Run the tests once: `uv run pytest backend/test/ -q` — everything should pass.
2. **Pin the versions that work on your computer.** Without this the server
   installs the *newest* versions, which can behave differently from the ones
   you tested.
   ```powershell
   uv pip list | Select-String -Pattern "fastapi|uvicorn|pydantic|motor|pymongo|httpx|pyjwt|cryptography"
   ```
   In `requirements.txt`, change `>=` to `==` for those lines, using the versions
   shown (for example `fastapi>=0.115` becomes `fastapi==0.115.6`). Don't paste
   in your whole `pip freeze`: it contains Windows-only packages that fail on the server.
3. **Delete anything left over from the old CrewAI version**, if it's in your
   project: a `backend\crew\` folder, `backend\services\crew_service.py`,
   `backend\scripts\export_agents.py`, `backend\test\test_agent_loader.py`,
   `Dockerfile`, `.dockerignore`, `render.yaml`, and any old top-level scripts
   such as `agents.py`, `tasks.py`, `hand_rolled_agents.py`, `test.py`,
   `test_with_tools.py`.
4. Use a separate database for the live site so your test data stays out of
   it. Nothing to create: it appears when the first user signs up. You'll set
   `MONGODB_DATABASE=crew_ai_agent_prod` in Part 3.

---

## Part 2 — Put the code on GitHub

1. Install Git from <https://git-scm.com/download/win> and check with `git --version`.
2. Tell Git who you are. For privacy, use GitHub's no-reply address (GitHub →
   Settings → Emails → tick "Keep my email addresses private", then copy the
   `…@users.noreply.github.com` address it shows):
   ```powershell
   git config --global user.name "Nayan Kumar Sahu"
   git config --global user.email "<your-noreply-address>"
   ```
3. In the project folder:
   ```powershell
   cd E:\Programming\Crew_AI_Agent
   git init
   git add .
   git status
   ```
4. **Read the `git status` list carefully.** `.env` must **not** be in it. Confirm:
   ```powershell
   git check-ignore -v .env      # should print a .gitignore line
   ```
   Also look for files you don't recognise, or any file with a key in it, and
   remove them with `git rm --cached <file>` (or delete them). **If `.env` ever
   got committed, stop: every key in it must be replaced.**
5. Commit:
   ```powershell
   git commit -m "Initial commit"
   git branch -M main
   ```
6. On github.com click **New repository**. Name: `crew-search-influencers`.
   Choose **Private**. Leave "Add a README/.gitignore" **unticked**. Create it.
7. Connect and upload (a browser window opens to sign you in):
   ```powershell
   git remote add origin https://github.com/<your-github-username>/crew-search-influencers.git
   git push -u origin main
   ```

---

## Part 3 — The backend on Render

1. Sign up at <https://render.com> with your GitHub account.
2. **New → Web Service →** pick your `crew-search-influencers` repo (Render will
   ask permission to read it; private repos are fine).
3. Fill in:

   | Field | Value |
   |---|---|
   | Name | `crew-search-influencers-api` |
   | Region | The one nearest your users (Singapore for India) |
   | Branch | `main` |
   | Root Directory | leave **blank** |
   | Runtime | **Python 3** |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | **Free** |

4. Open **Advanced** and set **Health Check Path** to `/health`.
5. Add these **Environment Variables** (names exactly as written):

   | Name | Value |
   |---|---|
   | `PYTHON_VERSION` | `3.11.9` |
   | `SUPABASE_URL` | Same as your local `.env` |
   | `MONGODB_URI` | Same as your local `.env` |
   | `MONGODB_DATABASE` | `crew_ai_agent_prod` |
   | `SERPER_API_KEY` | Same as local |
   | `TOKEN_ENCRYPTION_KEY` | A **new** key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` — keep a copy |
   | `GOOGLE_CLIENT_ID` | Same as local |
   | `GOOGLE_CLIENT_SECRET` | Same as local |
   | `FREE_RUNS_FOR_NEW_USERS` | `2` |

   Three more come **after** the website exists (Part 6): `CORS_ORIGINS`,
   `FRONTEND_URL`, `GOOGLE_REDIRECT_URI`. Add `SUPABASE_JWT_SECRET` only if
   your Supabase project uses the old shared secret. Leave `PIPELINE_DEBUG_DUMP` unset.
6. Click **Create Web Service**. The first build takes 2–4 minutes; watch the
   **Logs** tab. It ends with "Your service is live".
7. Your backend's address is at the top of the page, like
   `https://crew-search-influencers-api.onrender.com`. Open `<address>/health`
   — you should see `{"status":"ok"}`. Write the address down: it's your **backend URL**.

---

## Part 4 — MongoDB Atlas must accept the server

Atlas → **Network Access → Add IP Address → Allow access from anywhere
(0.0.0.0/0) → Confirm.** Render's addresses change, so a fixed one can't be
listed. Your database is still protected by its username and password.

---

## Part 5 — The website on Vercel

### 5.1 Check the terms first

Vercel's free **Hobby** plan is, as far as I know, for **personal,
non-commercial use**. Crew asks users to pay you for more searches, which is
commercial. If that applies, use **Cloudflare Pages** or **Netlify** instead
(both have free plans; check their current terms). The steps are nearly the
same: connect the GitHub repo, set the root folder to `frontend`, build command
`npm run build`, output folder `dist`, and add the same environment variables.
`vercel.json` and `_redirects` are already in the project for all three.

### 5.2 Deploy

1. Sign up at <https://vercel.com> with your GitHub account.
2. **Add New → Project →** pick the `crew-search-influencers` repo.
3. Set **Root Directory** to `frontend`. Framework should show **Vite**.
4. Name the project `crew-search-influencers` (this decides the free address:
   `https://crew-search-influencers.vercel.app`; if taken, Vercel adds letters,
   so use whatever address it shows).
5. Under **Environment Variables** add:

   | Name | Value |
   |---|---|
   | `VITE_SUPABASE_URL` | Same as `frontend\.env` |
   | `VITE_SUPABASE_PUBLISHABLE_KEY` | Same as `frontend\.env` |
   | `VITE_API_BASE_URL` | Your **backend URL** from Part 3 (no trailing `/`) |
   | `VITE_SITE_URL` | Your Vercel address, e.g. `https://crew-search-influencers.vercel.app` |
   | `VITE_FREE_SEARCHES` | `2` |

6. Click **Deploy**. After a minute you get the site's address: your **website
   URL**. If it differs from what you put in `VITE_SITE_URL`, fix that variable
   (Settings → Environment Variables) and **Redeploy**.

---

## Part 6 — Connect everything (don't skip: sign-up and Gmail break without this)

1. **Render** → your service → **Environment**. Add:

   | Name | Value |
   |---|---|
   | `CORS_ORIGINS` | Your website URL, no trailing `/` |
   | `FRONTEND_URL` | Your website URL, no trailing `/` |
   | `GOOGLE_REDIRECT_URI` | `<backend URL>/api/gmail/callback` |

   Render restarts the service by itself when you save.

2. **Supabase** → **Authentication → URL Configuration**: set **Site URL** to your
   website URL, and add `<website URL>/**` under **Redirect URLs**. Without this,
   the confirmation email's link points to `localhost`.

3. **Supabase email sending.** The built-in sender allows only a few emails an
   hour for the whole project, so sign-ups will stall. Either:
   - turn off **Confirm email** (Authentication → Sign In / Providers → Email) for
     the launch (easiest, but people can sign up with any address); or
   - set up your own sender under **Authentication → SMTP Settings** (a free
     account at Brevo or similar works).

4. **Google Cloud** → **APIs & Services → Credentials →** your OAuth client →
   under **Authorized redirect URIs** add `<backend URL>/api/gmail/callback`
   (exactly the same as `GOOGLE_REDIRECT_URI`). Keep the localhost one for testing.
   Add anyone who should be able to connect Gmail under **Audience → Test users**.

5. **Make yourself unlimited** (the live database doesn't have your account yet).
   Sign up on the live site first, then on your computer:
   ```powershell
   $env:MONGODB_DATABASE = "crew_ai_agent_prod"
   uv run python -m backend.scripts.grant_credits <your-email> --unlimited
   Remove-Item Env:MONGODB_DATABASE
   ```

---

## Part 7 — Test it like a new visitor

Open the website in a private window and check each one:

- [ ] The front page loads, and so does `/how-it-works` after pressing **refresh**
- [ ] Create an account (and confirm the email, if you left that on)
- [ ] Sign in; the details form appears if needed
- [ ] Settings → **Connect Gmail** → Google → back with "Gmail connected"
- [ ] Create a campaign and **Run pipeline**: the progress strip moves through
      Discovery, Review and Outreach within a minute
- [ ] Creators appear with scores; a creator's email draft opens and is signed with your details
- [ ] **Save to Gmail drafts** works
- [ ] After 2 runs that find creators, the next shows the "get in touch" notice with your details

**Your first real run is the real test of the search.** The pipeline reads what
Google shows for Instagram pages, so it's worth trying a few campaigns. If one
finds little, add `PIPELINE_DEBUG_DUMP=true` on your own computer, run it, and
look at `backend\outputs\search_debug.jsonl` to see exactly what came back.

**When something fails:** Render's **Logs** tab shows what the backend saw; the
browser's DevTools (F12) → Console/Network shows what the website saw.

---

## Part 8 — After launch

- **Keep the backend awake (recommended).** A free monitor such as UptimeRobot
  can request `<backend URL>/health` every 5 minutes so the first visitor of the
  day doesn't wait a minute for it to wake. The free plan has enough hours for
  one service to run all month.
- **Google Search Console** (<https://search.google.com/search-console>): add your
  site, verify it, submit `<website URL>/sitemap.xml`, and use "Request indexing"
  on the front page.
- **Update the site:** change the code, then
  `git add . ; git commit -m "..." ; git push origin main`. Vercel and Render both
  redeploy by themselves.

---

## What is and isn't free

| Piece | Cost | Limit to know |
|---|---|---|
| Website (Vercel/Cloudflare/Netlify) | Free | Vercel Hobby: non-commercial (see 5.1) |
| Backend (Render) | Free | Sleeps after 15 min idle (see Part 8) |
| Database (Atlas free tier) | Free | 512 MB storage |
| Sign-in (Supabase free) | Free | **Pauses after about 7 days with no activity**: sign in at least weekly, or upgrade; limited emails |
| **Creator search (Serper)** | Free credits, then paid | Each run makes up to 8 searches (`PIPELINE_MAX_QUERIES`) and each search costs one credit. Check serper.dev for the free amount and the price after |
| Gmail connection | Free | While the Google app is in Testing mode: 100 listed users, access expires every 7 days |
| Domain | `.vercel.app` is free | A custom domain (about ₹800–1,000/year) is the one thing worth paying for: it helps search ranking and looks more trustworthy |

There is no AI bill: the search uses no AI service.

---

## Troubleshooting

| What you see | Likely cause and fix |
|---|---|
| Render build fails | Read the last lines of the **Logs** tab. Most often a pinned version in `requirements.txt` that doesn't exist: fix the pin and push again |
| Service shows **Failed** / crashes at startup | A required variable is missing or misspelled. The Logs tab names it (usually `SUPABASE_URL`, `MONGODB_URI` or `SERPER_API_KEY`) |
| Website says "Can't reach the server" | Wrong `VITE_API_BASE_URL`, or the backend is waking up: open `<backend URL>/health` and wait a minute |
| First page load takes about a minute | The free backend was asleep (Part 8) |
| Browser console: **CORS error** | `CORS_ORIGINS` doesn't exactly match the website URL (check `https`, spelling, no trailing `/`) |
| Confirmation email links to `localhost` | Supabase Site URL / Redirect URLs not set (Part 6, step 2) |
| Google: `redirect_uri_mismatch` | The redirect address in Google Cloud and `GOOGLE_REDIRECT_URI` aren't identical |
| "The search service (Serper) refused the request…" | Wrong `SERPER_API_KEY`, or its credits have run out |
| A campaign finds no creators | The result says "this search wasn't used". Try broader category words or a wider follower range |
| Refreshing `/how-it-works` shows "not found" | The rewrite file wasn't deployed: check `frontend/vercel.json` exists in the repo |