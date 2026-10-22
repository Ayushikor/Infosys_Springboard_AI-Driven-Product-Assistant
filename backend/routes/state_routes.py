"""State route -- returns all user data in a single request.

The frontend calls GET /api/state after login to hydrate every context
provider in one round trip.
"""

from flask import Blueprint, session
from db import get_db
from helpers import ok, fail, mongo_docs_to_list

state_bp = Blueprint("state", __name__, url_prefix="/api")


@state_bp.route("/state", methods=["GET"])
def load_state():
    user_id = session.get("user_id")
    if not user_id:
        return fail("Not authenticated. Please log in.", status=401)

    db = get_db()
    user_state = db["user_state"].find_one({"userId": user_id}) or {}

    data = {
        "themes": mongo_docs_to_list(db["themes"].find({"userId": user_id})),
        "feedback": mongo_docs_to_list(
            db["feedback"].find({"userId": user_id}).sort("createdAt", -1)
        ),
        "features": mongo_docs_to_list(db["features"].find({"userId": user_id})),
        "prds": mongo_docs_to_list(db["prds"].find({"userId": user_id})),
        "roadmap": mongo_docs_to_list(db["roadmap"].find({"userId": user_id})),
        "workspaces": mongo_docs_to_list(db["workspaces"].find({"userId": user_id})),
        "activeWorkspaceId": user_state.get("activeWorkspaceId", ""),
        "activity": mongo_docs_to_list(
            db["activity"].find({"userId": user_id}).sort("at", -1).limit(50)
        ),
        "chat": mongo_docs_to_list(
            db["chat_messages"].find({"userId": user_id}).sort("_id", 1)
        ),
        "preferences": user_state.get(
            "preferences", {"theme": "light", "compactTables": False}
        ),
    }
    return ok(data)
