"""User preferences routes."""

from flask import Blueprint, request, session
from db import get_db
from helpers import ok, fail

preferences_bp = Blueprint("preferences", __name__, url_prefix="/api/preferences")


@preferences_bp.route("", methods=["PUT"])
def update_preferences():
    uid = session.get("user_id")
    if not uid:
        return fail("Not authenticated.", status=401)

    body = request.get_json(silent=True) or {}
    db = get_db()

    # Merge with existing preferences
    state = db["user_state"].find_one({"userId": uid}) or {}
    prefs = state.get("preferences", {"theme": "light", "compactTables": False})
    prefs.update(body)

    db["user_state"].update_one(
        {"userId": uid},
        {"$set": {"preferences": prefs}},
        upsert=True,
    )
    return ok(prefs, "Preferences saved")
