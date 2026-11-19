
"""Centralised MongoDB index definitions.

create_indexes(db) takes the database handle from backend/db.get_db();
this module never opens its own connection. It is idempotent and safe at startup:

- Unique indexes are only built if existing data has no duplicates.
- If MongoDB is unreachable, index creation stops after the first failure.
- Other per-index errors are logged without stopping application startup.
"""

import logging

from pymongo import ASCENDING, DESCENDING
from pymongo.collation import Collation
from pymongo.errors import ConnectionFailure

logger = logging.getLogger(__name__)

_CASE_INSENSITIVE = Collation(locale="en", strength=2)


INDEX_SPECS = [
    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    {
        "collection": "users",
        "name": "users_id_unique",
        "keys": [("id", ASCENDING)],
        "unique": True,
    },
    {
        "collection": "users",
        "name": "users_email_unique",
        "keys": [("email", ASCENDING)],
        "unique": True,
    },
    {
        "collection": "users",
        "name": "users_username_ci_unique",
        "keys": [("username", ASCENDING)],
        "unique": True,
        "collation": _CASE_INSENSITIVE,
        "dup_group": {
            "username": {"$toLower": "$username"}
        },
    },

    # -----------------------------------------------------
    # USER-OWNED COLLECTIONS
    # -----------------------------------------------------

    {
        "collection": "workspaces",
        "name": "workspaces_user_id_unique",
        "keys": [
            ("userId", ASCENDING),
            ("id", ASCENDING),
        ],
        "unique": True,
    },
    {
        "collection": "themes",
        "name": "themes_user_id_unique",
        "keys": [
            ("userId", ASCENDING),
            ("id", ASCENDING),
        ],
        "unique": True,
    },
    {
        "collection": "features",
        "name": "features_user_id_unique",
        "keys": [
            ("userId", ASCENDING),
            ("id", ASCENDING),
        ],
        "unique": True,
    },
    {
        "collection": "prds",
        "name": "prds_user_id_unique",
        "keys": [
            ("userId", ASCENDING),
            ("id", ASCENDING),
        ],
        "unique": True,
    },
    {
        "collection": "roadmap",
        "name": "roadmap_user_id_unique",
        "keys": [
            ("userId", ASCENDING),
            ("id", ASCENDING),
        ],
        "unique": True,
    },
    {
        "collection": "feedback",
        "name": "feedback_user_id_unique",
        "keys": [
            ("userId", ASCENDING),
            ("id", ASCENDING),
        ],
        "unique": True,
    },

    # Feedback list: find({userId}).sort(createdAt, -1)
    {
        "collection": "feedback",
        "name": "feedback_user_created",
        "keys": [
            ("userId", ASCENDING),
            ("createdAt", DESCENDING),
        ],
    },

    # -----------------------------------------------------
    # USER STATE
    # -----------------------------------------------------

    {
        "collection": "user_state",
        "name": "user_state_user_unique",
        "keys": [("userId", ASCENDING)],
        "unique": True,
    },

    # -----------------------------------------------------
    # PRODUCTS
    # -----------------------------------------------------

    {
        "collection": "products",
        "name": "products_id_unique",
        "keys": [("id", ASCENDING)],
        "unique": True,
    },
    {
        "collection": "products",
        "name": "products_created",
        "keys": [("createdAt", DESCENDING)],
    },

    # -----------------------------------------------------
    # ACTIVITY
    # -----------------------------------------------------

    {
        "collection": "activity",
        "name": "activity_user_at",
        "keys": [
            ("userId", ASCENDING),
            ("at", DESCENDING),
        ],
    },

    # -----------------------------------------------------
    # CHAT HISTORY
    # -----------------------------------------------------

    {
        "collection": "chat_messages",
        "name": "chat_user_id",
        "keys": [
            ("userId", ASCENDING),
            ("_id", ASCENDING),
        ],
    },

    # -----------------------------------------------------
    # AI ANALYSIS RUNS
    # -----------------------------------------------------

    # Every analysis run must have a unique run_id.
    {
        "collection": "analysis_runs",
        "name": "analysis_runs_run_id_unique",
        "keys": [("run_id", ASCENDING)],
        "unique": True,
    },

    # Retrieve a user's analysis history by creation date.
    {
        "collection": "analysis_runs",
        "name": "analysis_runs_user_created",
        "keys": [
            ("userId", ASCENDING),
            ("createdAt", DESCENDING),
        ],
    },

    # Retrieve analysis history for a specific workspace.
    {
        "collection": "analysis_runs",
        "name": "analysis_runs_workspace_created",
        "keys": [
            ("userId", ASCENDING),
            ("workspaceId", ASCENDING),
            ("createdAt", DESCENDING),
        ],
    },
]


# ---------------------------------------------------------
# DUPLICATE VALIDATION
# ---------------------------------------------------------


def _has_duplicates(collection, spec):
    """Check for duplicate values before creating a unique index."""

    group_id = (
        spec.get("dup_group")
        or {
            key: f"${key}"
            for key, _ in spec["keys"]
        }
    )

    pipeline = [
        {
            "$group": {
                "_id": group_id,
                "n": {"$sum": 1},
            }
        },
        {
            "$match": {
                "n": {"$gt": 1}
            }
        },
        {"$limit": 1},
    ]

    return next(iter(collection.aggregate(pipeline)), None) is not None


# ---------------------------------------------------------
# INDEX CREATION
# ---------------------------------------------------------


def create_indexes(db):
    """
    Ensure all configured indexes exist.

    Returns:
        {
            "ensured": [...],
            "skipped": [...],
            "failed": [...]
        }
    """

    summary = {
        "ensured": [],
        "skipped": [],
        "failed": [],
    }

    for spec in INDEX_SPECS:

        name = spec["name"]
        collection = db[spec["collection"]]

        try:

            # Check existing data before creating unique indexes.
            if spec.get("unique") and _has_duplicates(
                collection,
                spec,
            ):

                logger.warning(
                    "Skipping unique index %s: existing duplicate values.",
                    name,
                )

                summary["skipped"].append(name)
                continue

            options = {
                "name": name,
            }

            if spec.get("unique"):
                options["unique"] = True

            if spec.get("collation") is not None:
                options["collation"] = spec["collation"]

            collection.create_index(
                spec["keys"],
                **options,
            )

            summary["ensured"].append(name)

            logger.info(
                "MongoDB index ensured: %s",
                name,
            )

        except ConnectionFailure as exc:

            logger.warning(
                "MongoDB unreachable, skipping index creation: %s",
                exc,
            )

            summary["failed"].append(name)
            break

        except Exception as exc:

            logger.warning(
                "Could not create index %s: %s",
                name,
                exc,
            )

            summary["failed"].append(name)

    logger.info(
        "MongoDB index creation summary: %s",
        summary,
    )

    return summary
