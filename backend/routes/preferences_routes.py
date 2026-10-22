
"""User preferences routes using FastAPI."""

from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse

from db import get_db
from helpers import ok, fail


router = APIRouter(prefix="/api/preferences", tags=["Preferences"])


def _error_response(message, status_code=400):
    """Convert the existing Flask-style fail() result to a FastAPI response."""

    body, status = fail(message, status=status_code)
    return JSONResponse(content=body, status_code=status)


@router.put("")
def update_preferences(
    request: Request,
    body: dict | None = Body(default=None),
):
    uid = request.session.get("user_id")

    if not uid:
        return _error_response("Not authenticated.", 401)

    body = body or {}
    db = get_db()

    # Load the user's existing state and preferences.
    state = db["user_state"].find_one({"userId": uid}) or {}

    existing_prefs = state.get(
        "preferences",
        {"theme": "light", "compactTables": False},
    )

    # Copy existing preferences before merging new values.
    prefs = dict(existing_prefs)
    prefs.update(body)

    db["user_state"].update_one(
        {"userId": uid},
        {"$set": {"preferences": prefs}},
        upsert=True,
    )

    return ok(prefs, "Preferences saved")
