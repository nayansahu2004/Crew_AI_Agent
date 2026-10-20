Ran 5 commands, shared files
A few things worth noting about the design choices here:

serialize_doc() in models/__init__.py is the bridge between raw Mongo documents (with ObjectId and _id) and the schemas above (which expect a plain id: str). Services (Phase 4) will call this before handing data to a schema — e.g. CampaignResponse(**serialize_doc(mongo_doc)).
Ownership fields (user_id) are on models/ but never in schemas/*Create or *Update — deliberately. A CampaignCreate request body has no user_id field at all; the route always sets it from AuthenticatedUser.supabase_user_id (from get_current_user()), never from anything the client sends. This is the concrete enforcement of the spec's "never trust a user_id from the frontend" rule.
RunStatusResponse includes campaign_id even though the architecture doc's example JSON for GET /api/runs/{run_id} didn't show it — added it since the frontend will need it to link back to the campaign page, and it costs nothing. Flag it if you'd rather keep the response minimal and match the doc's example exactly.
No progress percentage field yet in RunStatusResponse, even though the doc mentions the frontend eventually wanting one ("progress": 35). Computing a meaningful percentage depends on how you want to weight the three stages, which is a Phase 4/5 decision (inside crew_service.py), not a schema one — the schema has current_stage which the frontend can map to a rough progress bar for now. Easy to add progress: int | None here later once that logic exists.

Building these now — one important design decision to flag before the code: crew_service.py needs to persist data during a long-running, blocking CrewAI call. FastAPI's BackgroundTasks runs plain (non-async) functions in a thread pool, but your app's Motor client (async MongoDB driver) isn't safe to use from a different thread. To keep this simple and reliable — the spec's explicit priority for v1 — crew_service.py uses a second, synchronous PyMongo client, scoped only to this file, instead of Motor. Everywhere else in the app stays async/Motor as before. I'll flag this clearly in the code too.

Two things worth reading carefully before moving on, both flagged in the code comments too:

The sync-PyMongo-vs-async-Motor split in crew_service.py — a real, deliberate tradeoff to keep the first version simple per the spec's own instruction not to reach for Celery/Redis yet. It means this one file has its own DB client, separate from core/database.py. Fine for now; worth reconsidering if you ever add a proper task queue.
The name/handle matching between stages is fragile — Review and Outreach results get matched back to the influencer documents Discovery created using instagram_handle/name as the join key, since that's the only thing the agents currently echo consistently between stages. If an agent phrases a name slightly differently between Discovery and Outreach, that influencer's outreach_status just silently stays not_started — no error, just a missed update. Worth watching for in testing; a more robust fix later would have each stage's task explicitly pass through a stable ID rather than relying on name matching.

Worth clarifying before I build Phase 5/6, since it's a real fork in what gets written — let me lay out what Redis would and wouldn't actually fix here, since "free" isn't the only cost worth weighing.

What BackgroundTasks (current plan) actually loses vs. Redis + a worker (RQ):

If your server process restarts/crashes mid-run, a BackgroundTasks job is just gone — no record, no retry. A queued job in Redis survives that.
BackgroundTasks runs inside the same process as your API — under real load, a long CrewAI run could compete for resources with incoming requests. A separate worker process avoids that.
No built-in retry/backoff on failure with BackgroundTasks; RQ gives you that for free.

What Redis would not fix — the specific thing I flagged:
The sync-PyMongo-vs-async-Motor split exists because a blocking CrewAI call can't safely share the app's async Motor client. That's still true with an RQ worker — an RQ job is also a plain synchronous function, running in its own separate process. You'd still use synchronous PyMongo inside the worker for exactly the same reason. Redis solves job durability and process separation, not this particular async/sync mismatch — crew_service.py's design here wouldn't meaningfully change.

The real cost of adding it now: a Redis instance (Redis Cloud's free tier — 30MB — works fine for this), an rq dependency, a separate worker process to run alongside FastAPI (meaning two things to start/deploy instead of one), and enqueue/dequeue code replacing the simple BackgroundTasks call. Your original spec explicitly called this out too — "do not introduce Redis/Celery unless necessary for the first working version."

Given that, my honest read: for a first working version, BackgroundTasks is the better fit — the durability/scaling gains from Redis matter more once you have real concurrent users, not during initial development. But it's genuinely your call, so:

Your earlier sign-up problem

Supabase’s built-in email sender allows only a few emails per hour, and the limit is per project, not per person. If your sign-up was failing or going quiet, that’s the likeliest cause, and it gets worse in production. Before real users arrive, set up your own email sender (SMTP, for example Resend or SendGrid) under Authentication → Emails in the Supabase dashboard. If the error was something else, send me the message and I’ll look.

Gmail (Phase B)

Google needs to approve this, and your decisions shape the build. Three things first:

Consent screen: While your Google app is in “Testing” mode, only up to 100 test users you list by hand can connect, and their access expires every 7 days. Letting anyone connect means passing Google’s app verification, which needs a public privacy policy and a verified domain. That takes days to weeks, so start it early.
Recipient addresses: The pipeline finds Instagram handles, not email addresses, so the app can’t send to anyone yet. The plan is for you to paste each creator’s email on their entry, then send.
Where tokens live: Gmail access tokens will be stored encrypted in your database with a key kept in the server’s environment, never in the browser.

The question that decides the build: