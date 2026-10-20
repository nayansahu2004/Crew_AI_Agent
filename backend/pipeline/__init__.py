# File path: backend/pipeline/__init__.py
"""
The search pipeline: Discovery -> Review -> Outreach, with no AI service.

    search.py   asks Serper (Google search) for results
    brief.py    turns a campaign into search terms, a country and keywords
    extract.py  pulls Instagram handles and follower counts out of results
    score.py    scores each creator with a fixed formula
    emails.py   fills an email template for each creator
    workflow.py runs the three steps; the one function the app calls
"""