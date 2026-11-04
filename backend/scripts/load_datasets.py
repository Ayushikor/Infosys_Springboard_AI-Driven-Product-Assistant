"""Load the sample datasets (customer feedback, reviews, support tickets) into MongoDB.

Run from the backend/ folder, after registering a user in the app:

    python scripts/load_datasets.py --email you@example.com
    python scripts/load_datasets.py --email you@example.com --dry-run
    python scripts/load_datasets.py --email you@example.com --reset

Records are stored as normal feedback documents for that user. They are unanalysed on
purpose (sentiment 'neutral', theme 'Uncategorized') so the AI agents have work to do.
The script is idempotent: records already loaded are skipped.
"""

import argparse
import json
import os
import re
import sys

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from config import Config  # noqa: E402
from db import close_client, get_db, init_db  # noqa: E402
from helpers import generate_id, normalize_feedback, now_iso  # noqa: E402

DEFAULT_DIR = os.path.join(os.path.dirname(BACKEND_DIR), "datasets")
DATASET_FILES = {
    "customer_feedback": "customer_feedback.json",
    "user_reviews": "user_reviews.json",
    "support_tickets": "support_tickets.json",
}
ID_PATTERN = re.compile(r"^(FB|REV|TKT)-\d{3}$")


def derive_title(text, limit=80):
    """First sentence of the text, shortened at a word boundary."""
    first = re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0].strip(" .!?")
    if len(first) <= limit:
        return first
    return first[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "..."


def to_feedback_document(item, dataset, user_id):
    """Convert one dataset row to a feedback document, using the backend's own normaliser."""
    record, error = normalize_feedback({
        "title": derive_title(item["raw_text"]),
        "message": item["raw_text"],
        "source": item["source_channel"],
        "createdAt": item["timestamp"],
    })
    if error:
        raise ValueError(f"{item.get('feedback_id')}: {error}")
    return {"id": item["feedback_id"], "userId": user_id, "dataset": dataset, **record}


def load_rows(directory):
    rows = []
    for dataset, filename in DATASET_FILES.items():
        path = os.path.join(directory, filename)
        with open(path, encoding="utf-8") as handle:
            for item in json.load(handle):
                rows.append((dataset, item))
    return rows


def run(email, directory=DEFAULT_DIR, dry_run=False, reset=False):
    """Load the datasets for the user with this e-mail. Returns a summary dict."""
    db = get_db()
    user = db["users"].find_one({"email": email.strip().lower()})
    if not user:
        raise SystemExit(f"No user with e-mail {email!r}. Register in the app first, then re-run.")
    user_id = user["id"]

    removed = 0
    if reset and not dry_run:
        removed = db["feedback"].delete_many(
            {"userId": user_id, "id": {"$regex": ID_PATTERN.pattern}}
        ).deleted_count

    existing = {d["id"] for d in db["feedback"].find({"userId": user_id}, {"id": 1})}
    documents, skipped = [], 0
    for dataset, item in load_rows(directory):
        if item["feedback_id"] in existing:
            skipped += 1
            continue
        documents.append(to_feedback_document(item, dataset, user_id))

    if documents and not dry_run:
        db["feedback"].insert_many(documents)
        db["activity"].insert_one({
            "id": generate_id("act-"), "userId": user_id,
            "text": f"Loaded {len(documents)} sample feedback records", "at": now_iso(),
        })
    return {"user": user_id, "added": len(documents), "skipped": skipped,
            "removed": removed, "dry_run": dry_run}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--email", required=True, help="E-mail of an already registered user")
    parser.add_argument("--datasets-dir", default=DEFAULT_DIR)
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen; write nothing")
    parser.add_argument("--reset", action="store_true", help="Delete this user's previously loaded sample records first")
    args = parser.parse_args()

    init_db(Config.MONGO_URI, Config.MONGO_DB_NAME)
    try:
        print(run(args.email, args.datasets_dir, args.dry_run, args.reset))
    finally:
        close_client()


if __name__ == "__main__":
    main()