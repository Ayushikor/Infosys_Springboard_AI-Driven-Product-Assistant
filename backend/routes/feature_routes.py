"""Feature (prioritization) CRUD routes using FastAPI."""

from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse

from db import get_db
from helpers import (
    ok,
    fail,
    generate_id,
    now_iso,
    mongo_doc_to_dict,
    mongo_docs_to_list,
    normalize_feature,
)

router = APIRouter(prefix="/api/features", tags=["Features"])


def _error_response(message, status_code=400):
    """Convert the existing fail() response to FastAPI JSON."""
    body, status = fail(message, status=status_code)
    return JSONResponse(content=body, status_code=status)


def _user_id(request: Request):
    """Get the logged-in user ID from the session."""
    return request.session.get("user_id")


def _log_activity(user_id, text):
    """Record a feature-related activity."""
    get_db()["activity"].insert_one(
        {
            "id": generate_id("act-"),
            "userId": user_id,
            "text": text,
            "at": now_iso(),
        }
    )


@router.get("")
def get_all(request: Request):
    """Get all features belonging to the logged-in user."""
    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", 401)

    items = mongo_docs_to_list(
        get_db()["features"].find({"userId": uid})
    )

    return ok(items)


@router.post("")
def create(
    request: Request,
    body: dict | None = Body(default=None),
):
    """Create a feature for the logged-in user."""
    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", 401)

    body = body or {}
    record, error = normalize_feature(body)

    if error:
        return _error_response(error)

    record["id"] = generate_id("ft-")
    record["userId"] = uid

    get_db()["features"].insert_one(record)

    _log_activity(uid, f'Feature "{record["name"]}" added')

    return ok(mongo_doc_to_dict(record), "Feature created")


@router.put("/{feature_id}")
def update(
    feature_id: str,
    request: Request,
    body: dict | None = Body(default=None),
):
    """Update an existing feature belonging to the logged-in user."""
    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", 401)

    db = get_db()

    existing = db["features"].find_one(
        {
            "id": feature_id,
            "userId": uid,
        }
    )

    if not existing:
        return _error_response("Feature not found.", 404)

    body = body or {}
    record, error = normalize_feature(body, existing)

    if error:
        return _error_response(error)

    record["id"] = feature_id
    record["userId"] = uid

    db["features"].update_one(
        {
            "id": feature_id,
            "userId": uid,
        },
        {"$set": record},
    )

    _log_activity(uid, f'Feature "{record["name"]}" updated')

    updated = db["features"].find_one(
        {
            "id": feature_id,
            "userId": uid,
        }
    )

    return ok(mongo_doc_to_dict(updated), "Feature updated")


@router.delete("/{feature_id}")
def remove(feature_id: str, request: Request):
    """Delete a feature belonging to the logged-in user."""
    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", 401)

    db = get_db()

    target = db["features"].find_one(
        {
            "id": feature_id,
            "userId": uid,
        }
    )

    if not target:
        return _error_response("Feature not found.", 404)

    db["features"].delete_one(
        {
            "id": feature_id,
            "userId": uid,
        }
    )

    _log_activity(uid, f'Feature "{target["name"]}" deleted')

    return ok({"id": feature_id}, "Feature deleted")