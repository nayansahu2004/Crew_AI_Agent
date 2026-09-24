AI Influencer Discovery & Outreach Platform

1. Project Overview

This project is an AI-powered influencer marketing platform designed to automate and streamline influencer discovery, profile analysis, and personalized outreach.

The platform uses a multi-agent CrewAI workflow:

Discovery — finds Indian fashion/beauty Instagram influencers within a specified follower range.

Review — analyzes and evaluates discovered creators using additional web data.

Outreach — generates personalized first-contact messages asking about availability and rates.

The updated system adds a real-time frontend so users can see qualified influencers as they are discovered instead of waiting for the entire CrewAI workflow to finish.

2. Core Product Idea

The central architecture is:

The frontend controls the workflow, the backend manages state and streaming, CrewAI handles agentic reasoning, and external tools provide real-world data.

The product flow is:

Discover → Review → Approve → Outreach

Instead of a terminal-only workflow:

Run Crew → Wait → Inspect output

the user gets a live application where qualified influencers appear as cards during discovery.

3. Overall System Architecture

                         ┌─────────────────────────┐
                         │       USER / BRAND      │
                         └────────────┬────────────┘
                                      │
                                      ▼
                         ┌─────────────────────────┐
                         │      React Frontend      │
                         │      Vite + Tailwind     │
                         │                          │
                         │ • Search configuration   │
                         │ • Live influencer cards │
                         │ • Review dashboard       │
                         │ • Outreach dashboard     │
                         └────────────┬────────────┘
                                      │
                         REST API     │     SSE
                                      ▼
                    ┌─────────────────────────────────┐
                    │          FastAPI Backend        │
                    │                                 │
                    │ • API endpoints                 │
                    │ • Job/session management        │
                    │ • Event streaming               │
                    │ • Validation                    │
                    │ • Database access               │
                    └───────────────┬─────────────────┘
                                    │
                                    ▼
                    ┌─────────────────────────────────┐
                    │         CrewAI Orchestrator     │
                    │                                 │
                    │  Discovery → Review → Outreach  │
                    └───────┬──────────┬──────────┬───┘
                            │          │          │
                    ┌───────▼───┐ ┌────▼─────┐ ┌──▼─────────┐
                    │ Discovery │ │ Reviewer  │ │ Outreach   │
                    │   Agent   │ │   Agent   │ │   Agent    │
                    └─────┬─────┘ └────┬──────┘ └────┬──────┘
                          │             │             │
                ┌─────────┴───┐    ┌────┴────┐       │
                │             │    │         │       │
             Serper       Web/Social Firecrawl│     LLM
             Search        Data     Tavily   │
                                              │
                                              ▼
                                      ┌─────────────┐
                                      │   Gemini    │
                                      │  3.6 Flash  │
                                      └─────────────┘

                         ┌─────────────────────────┐
                         │       PostgreSQL         │
                         │                         │
                         │ Influencers             │
                         │ Searches                │
                         │ Reviews                 │
                         │ Outreach                │
                         │ Campaigns               │
                         └─────────────────────────┘

4. Role of Each Layer

4.1 Frontend

The React frontend is the main user interface and control center.

It should allow users to:

Configure influencer searches

See live discovery progress

View influencer cards as they are found

Review individual creators

Select creators for outreach

View generated outreach messages

Edit/copy/send outreach messages

See agent activity and progress

The frontend should not perform the AI reasoning itself.

5. Discovery Interface

The user can configure a search such as:

Niche:
[ Fashion ▼ ]

Location:
[ India ]

Followers:
[20K] — [500K]

Platform:
[ Instagram ]

                     [ Find Influencers ]

Once the search begins:

Discovery running...

✓ 8 influencers found
🔎 Searching...

Qualified influencers appear immediately as cards.

Example:

┌─────────────────────────┐
│         PHOTO           │
│                         │
│ @creator_1              │
│ 125K followers          │
│ Fashion                 │
│ India                   │
│                         │
│ [Review] [Select ✓]     │
└─────────────────────────┘

6. Why Real-Time Discovery Is Important

The original terminal workflow could look like:

CrewAI is running...
CrewAI is running...
CrewAI is running...

The user cannot easily tell:

What the agent is currently doing

Whether a tool call has completed

Why another search is being performed

Which influencers have already been found

Why an influencer was rejected

The updated frontend exposes this process.

The system can show:

Discovery Activity

✓ @creator1       125K   Fashion   → MATCH
✓ @creator2        87K   Beauty    → MATCH
✕ @creator3       1.2M   Fashion   → Rejected: >500K
✕ @creator4        12K   Beauty    → Rejected: <20K
✕ @creator5        91K   Food      → Rejected: wrong niche

This makes the agent's behavior observable.

7. CrewAI's Role

CrewAI remains the orchestration and agentic reasoning layer.

It does not get replaced by the frontend.

The system becomes:

Frontend
   ↓
FastAPI
   ↓
CrewAI
   ↓
Agents + Tools + LLM

CrewAI manages:

Agent definitions

Tasks

Agent-to-agent workflow

Tool usage

LLM reasoning

Structured task execution

The three primary agents are:

Discovery Agent

Finds and qualifies potential influencers.

Reviewer Agent

Analyzes selected creators using additional information.

Outreach Agent

Creates personalized outreach messages.

8. Discovery Agent Flow

User requirements
       ↓
Discovery Agent
       ↓
Serper
       ↓
Search results
       ↓
Qualification layer
       ↓
Qualified influencer
       ↓
Frontend card

The Discovery Agent can reason about:

Whether the creator is relevant

Whether the creator is based in India

Whether the creator fits the fashion/beauty niche

Whether the result represents an actual creator

Whether enough information is available

However, simple numerical checks should preferably be deterministic.

For example:

if 20_000 <= followers <= 500_000:
    qualified = True

The LLM should be used for reasoning-heavy decisions rather than simple arithmetic or range checking.

9. Recommended Qualification Architecture

             SEARCH
               │
               ▼
          Raw results
               │
               ▼
       Deterministic filters
               │
       ┌───────┴────────┐
       │                │
    Reject            Pass
       │                │
       │                ▼
       │          Discovery LLM
       │                │
       │                ▼
       │          Qualified
       │                │
       └───────┐        ▼
               │      CARD
               ▼
            Database

This reduces unnecessary LLM calls and makes filtering more predictable.

10. Structured Influencer Output

Each qualified influencer should be represented in a standard structure:

{
  "id": "inf_001",
  "name": "Creator Name",
  "username": "@creator",
  "platform": "instagram",
  "followers": 125000,
  "category": "fashion",
  "location": "India",
  "profile_url": "...",
  "source": "serper",
  "qualification": {
    "location": true,
    "category": true,
    "followers": true
  }
}

This structure becomes the contract between the backend, database, agents, and frontend.

11. Backend Architecture

FastAPI is recommended as the backend.

It acts as the bridge between React, CrewAI, external tools, and the database.

Example API:

POST /api/search

This starts a discovery job.

Example response:

{
  "job_id": "search_123"
}

The frontend can then subscribe to the job's events.

12. Server-Sent Events (SSE)

SSE is recommended for the first version because most updates flow from the backend to the frontend.

The event flow can be:

SEARCH_STARTED
       ↓
TOOL_STARTED
       ↓
TOOL_COMPLETED
       ↓
INFLUENCER_FOUND
       ↓
INFLUENCER_FOUND
       ↓
INFLUENCER_REJECTED
       ↓
INFLUENCER_FOUND
       ↓
DISCOVERY_COMPLETED

Example event:

{
  "event": "influencer_found",
  "data": {
    "id": "inf_001",
    "username": "@creator",
    "followers": 125000,
    "category": "Fashion",
    "location": "India"
  }
}

React receives the event and renders the card immediately.

13. Why SSE Instead of WebSockets Initially

The application's primary real-time data flow is one-way:

Backend ───────────────► Frontend

influencer found
tool started
tool completed
influencer rejected
review completed
discovery completed

User actions can use normal REST endpoints:

POST /search
POST /influencers/{id}/review
POST /influencers/{id}/approve
POST /influencers/{id}/outreach

Therefore SSE is simpler than introducing WebSockets for the initial version.

14. Database

PostgreSQL is recommended for persistent application state.

The application should not depend entirely on live CrewAI execution.

Recommended tables:

users
campaigns
searches
influencers
influencer_reviews
outreach_messages
agent_runs
agent_events

Campaign

campaign
──────────────
id
name
niche
location
min_followers
max_followers
created_at

Influencer

influencer
──────────────
id
name
username
platform
followers
category
location
profile_url
avatar_url
status
created_at

Review

review
──────────────
id
influencer_id
engagement_score
brand_fit
audience_fit
content_quality
summary
created_at

15. Review Stage

Review should be independently triggerable.

Flow:

Influencer Card
       │
       ▼
    [Review]
       │
       ▼
Reviewer Agent
       │
 ┌─────┼───────────┐
 ▼     ▼           ▼
Firecrawl Tavily  Gemini
       │
       ▼
    Analysis
       │
       ▼
     Database
       │
       ▼
    Frontend

The review panel could show:

┌──────────────────────────────────┐
│ @creator                         │
│ 125K followers                   │
│                                  │
│ Engagement       4.8%            │
│ Brand Fit        High            │
│ Audience Fit     Strong          │
│                                  │
│ Content: Fashion / Lifestyle     │
│                                  │
│ Review summary                   │
│ ...                              │
│                                  │
│ [Generate Outreach]              │
└──────────────────────────────────┘

16. Outreach Stage

The user selects creators:

☑ @creator1
☑ @creator2
☐ @creator3

Then selects:

[Generate Outreach]

Flow:

Selected influencer
        │
        ▼
Outreach Agent
        │
        ▼
Gemini
        │
        ▼
Personalized message
        │
        ▼
Frontend

The generated message can include:

Creator name

Relevant content/category

Brand/campaign context

Collaboration request

Availability request

Rate request

The user can then:

[Edit] [Copy] [Send]

17. Agent Event System

Every important agent/tool action should produce an event.

Example:

{
  "event": "tool_started",
  "agent": "discovery",
  "tool": "serper"
}

Then:

{
  "event": "tool_completed",
  "agent": "discovery",
  "tool": "serper",
  "results": 10
}

Then:

{
  "event": "influencer_found",
  "agent": "discovery",
  "influencer_id": "inf_123"
}

And:

{
  "event": "influencer_rejected",
  "reason": "followers_above_limit"
}

This creates an agent observability layer.

18. Agent Activity Panel

A useful UI component is:

Agent Activity

21:14:03  Discovery started
21:14:04  Serper search started
21:14:07  10 results received
21:14:08  3 influencers qualified
21:14:08  4 rejected
21:14:09  Searching for additional creators...

This directly answers questions such as:

Why is the agent still searching?

Which tool is running?

How many results were received?

Why was a creator rejected?

Has the current tool execution completed?

19. Independent Agent Stages

Rather than always running the complete Crew sequentially, the stages should be independently triggerable.

              ┌──────────────┐
              │  Discovery   │
              └──────┬───────┘
                     │
              User selects
                     │
              ┌──────▼───────┐
              │    Review    │
              └──────┬───────┘
                     │
              User approves
                     │
              ┌──────▼───────┐
              │   Outreach   │
              └──────────────┘

This gives the user control over the process and avoids unnecessarily running later agents.

20. CrewAI Architecture

The existing CrewAI concept can remain:

Crew(
    agents=[
        discovery_agent,
        reviewer_agent,
        outreach_agent
    ],
    tasks=[
        discovery_task,
        review_task,
        outreach_task
    ],
    process=Process.sequential
)

However, the application should not necessarily execute the entire Crew for every user interaction.

The preferred product-level workflow is:

Discovery
    ↓
User selects creators
    ↓
Review
    ↓
User approves
    ↓
Outreach

This makes the system human-in-the-loop.

21. Recommended Project Structure

influencer-ai/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── SearchForm.jsx
│   │   │   ├── InfluencerCard.jsx
│   │   │   ├── InfluencerGrid.jsx
│   │   │   ├── ReviewPanel.jsx
│   │   │   ├── OutreachPanel.jsx
│   │   │   └── AgentActivity.jsx
│   │   │
│   │   ├── pages/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── Discovery.jsx
│   │   │   └── Campaign.jsx
│   │   │
│   │   ├── services/
│   │   │   └── api.js
│   │   │
│   │   └── App.jsx
│   │
│   └── package.json
│
├── backend/
│   ├── api/
│   │   ├── search.py
│   │   ├── review.py
│   │   └── outreach.py
│   │
│   ├── agents/
│   │   ├── discovery.py
│   │   ├── reviewer.py
│   │   └── outreach.py
│   │
│   ├── tasks/
│   │   ├── discovery.py
│   │   ├── review.py
│   │   └── outreach.py
│   │
│   ├── tools/
│   │   ├── serper.py
│   │   ├── firecrawl.py
│   │   └── tavily.py
│   │
│   ├── services/
│   │   ├── crew_service.py
│   │   ├── event_service.py
│   │   └── influencer_service.py
│   │
│   ├── models/
│   │   └── database.py
│   │
│   └── main.py
│
├── database/
│
├── .env
├── docker-compose.yml
└── README.md

22. Recommended Technology Stack

Layer

Technology

Frontend

React + Vite

Styling

Tailwind CSS

Backend

FastAPI

Agent Framework

CrewAI

LLM

Gemini 3.6 Flash

Search

Serper

Web Scraping

Firecrawl

Web Extraction

Tavily

Database

PostgreSQL

ORM

SQLAlchemy

Live Updates

SSE

API

REST

Environment

uv

Deployment

Docker

Frontend Deployment

Vercel

Backend Deployment

Railway / Render / similar

Redis/Celery can be introduced later if background workloads become heavy. They are not necessary for the first version.

23. Complete Data Flow

USER
 │
 │ Search:
 │ Fashion + India + 20K–500K
 ▼
REACT
 │
 │ POST /search
 ▼
FASTAPI
 │
 │ Create search job
 ▼
CREWAI
 │
 ▼
DISCOVERY AGENT
 │
 ├──────────────► SERPER
 │                   │
 │                   ▼
 │              Search results
 │                   │
 │◄──────────────────┘
 │
 ▼
Qualification
 │
 ├── Reject ──────────► DB
 │
 └── Qualified
          │
          ├──────────► DB
          │
          └──────────► SSE
                           │
                           ▼
                       REACT
                           │
                           ▼
                    INFLUENCER CARD
                           │
                           │ User clicks Review
                           ▼
                    REVIEW AGENT
                           │
                    Firecrawl/Tavily
                           │
                           ▼
                       Analysis
                           │
                           ▼
                         DB
                           │
                           ▼
                       REACT
                           │
                           │ User approves
                           ▼
                    OUTREACH AGENT
                           │
                           ▼
                        Gemini
                           │
                           ▼
                  Personalized message
                           │
                           ▼
                        REACT

24. Development Roadmap

Phase 1 — Core Discovery

Build:

React
  ↓
FastAPI
  ↓
CrewAI Discovery
  ↓
Serper
  ↓
Influencer cards

Goal:

Search → live qualified influencer cards.

Phase 2 — Review

Add:

Card → Review → Firecrawl/Tavily → Analysis

Goal:

User can inspect a creator before selecting them.

Phase 3 — Outreach

Add:

Review → Select → Outreach → Generated message

Goal:

Generate personalized outreach for approved creators.

Phase 4 — Persistence

Add PostgreSQL for:

Campaigns

Saved influencers

Search history

Reviews

Outreach messages

Agent execution history

Phase 5 — Production Features

Potential additions:

Authentication

Campaign management

Email integration

Rate limiting

Agent monitoring

Retry handling

Caching

Background jobs

Better error handling

25. Core Design Principle

The most important architectural distinction is:

CrewAI is not the entire application. It is one service inside the application.

                 YOUR PRODUCT
                     │
       ┌─────────────┼──────────────┐
       │             │              │
    Frontend       Backend       Database
       │             │
       │             └──── CrewAI
       │                    │
       │              ┌─────┼─────┐
       │              │     │     │
       │          Discovery Review Outreach
       │
       └──────── Live agent events ────────►

This turns the project from a simple CrewAI demonstration into an actual agentic influencer-marketing platform featuring:

Real-time agent execution

Tool orchestration

Structured data extraction

Deterministic qualification

LLM-based reasoning

Human-in-the-loop review

Persistent campaign state

Personalized outreach

Agent observability