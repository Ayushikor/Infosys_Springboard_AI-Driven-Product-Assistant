"""Promote an existing account to Admin.

Run from backend/: python scripts/promote_admin.py --email you@example.com
The script requires an explicit interactive confirmation.
"""
import argparse
import os
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from config import Config
from db import init_db, get_db, close_client


def main():
    parser = argparse.ArgumentParser(description="Promote an existing Stratov user to Admin")
    parser.add_argument("--email", required=True, help="Email of an existing account")
    args = parser.parse_args()

    email = args.email.strip().lower()
    confirmation = input(f"Promote {email} to Admin? Type PROMOTE to continue: ")
    if confirmation != "PROMOTE":
        print("Cancelled. No changes made.")
        return

    init_db(Config.MONGO_URI, Config.MONGO_DB_NAME)
    try:
        users = get_db()["users"]
        result = users.update_one(
            {"email": email},
            {"$set": {"role": "Admin", "isActive": True}},
        )
        if result.matched_count == 0:
            print("No account found for that email. Register the account first.")
            raise SystemExit(1)
        print(f"{email} is now an active Admin. Sign out and sign in again.")
    finally:
        close_client()


if __name__ == "__main__":
    main()
