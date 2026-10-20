# File path: backend/scripts/grant_credits.py
"""
Top up a user's searches after they've paid you (or make them unlimited).

Run from the project root:

    uv run python -m backend.scripts.grant_credits someone@example.com --show
    uv run python -m backend.scripts.grant_credits someone@example.com 10
    uv run python -m backend.scripts.grant_credits someone@example.com --unlimited

(You can also edit `run_credits` on the user's document in MongoDB Atlas by
hand: a number means that many searches left; deleting the field makes the
account unlimited.)
"""

import argparse
import re
import sys
from datetime import UTC, datetime


def find_user(db, email: str) -> dict | None:
    pattern = f"^{re.escape(email.strip())}$"
    return db.users.find_one({"email": {"$regex": pattern, "$options": "i"}})


def describe(user: dict) -> str:
    if "run_credits" not in user:
        return f"{user['email']}: unlimited"
    return f"{user['email']}: {user['run_credits']} search(es) left"


def add_credits(db, email: str, amount: int) -> dict:
    """Add searches. Returns the updated user. Raises LookupError if there is
    no such user, ValueError for a bad amount or an unlimited account (adding
    a number to one would quietly make it metered)."""
    if amount <= 0:
        raise ValueError("The amount must be a positive number.")
    user = find_user(db, email)
    if user is None:
        raise LookupError(f"No user with the email {email}.")
    if "run_credits" not in user:
        raise ValueError(f"{user['email']} is unlimited already; nothing to add.")
    db.users.update_one(
        {"_id": user["_id"]},
        {"$inc": {"run_credits": amount}, "$set": {"updated_at": datetime.now(UTC)}},
    )
    return db.users.find_one({"_id": user["_id"]})


def set_unlimited(db, email: str) -> dict:
    user = find_user(db, email)
    if user is None:
        raise LookupError(f"No user with the email {email}.")
    db.users.update_one(
        {"_id": user["_id"]},
        {"$unset": {"run_credits": ""}, "$set": {"updated_at": datetime.now(UTC)}},
    )
    return db.users.find_one({"_id": user["_id"]})


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Top up or inspect a user's free searches.")
    parser.add_argument("email", help="The email the user signed up with")
    parser.add_argument("amount", nargs="?", type=int, help="How many searches to add")
    parser.add_argument("--unlimited", action="store_true", help="Remove the limit entirely")
    parser.add_argument("--show", action="store_true", help="Just show the current balance")
    args = parser.parse_args(argv)

    if not (args.amount or args.unlimited or args.show):
        parser.error("give an amount to add, or --unlimited, or --show")

    from pymongo import MongoClient

    from backend.core.config import settings

    db = MongoClient(settings.mongodb_uri)[settings.mongodb_database]
    try:
        if args.show:
            user = find_user(db, args.email)
            if user is None:
                raise LookupError(f"No user with the email {args.email}.")
        elif args.unlimited:
            user = set_unlimited(db, args.email)
        else:
            user = add_credits(db, args.email, args.amount)
    except (LookupError, ValueError) as exc:
        print(exc)
        return 1

    print(describe(user))
    return 0


if __name__ == "__main__":
    sys.exit(main())