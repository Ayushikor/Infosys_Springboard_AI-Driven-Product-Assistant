"""Feedback CRUD routes using FastAPI."""

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
    normalize_feedback,
)

router = APIRouter(
    prefix="/api/feedback",
    tags=["Feedback"],
)


def _user_id(request: Request):
    """Get the authenticated user's ID from the session."""
    return request.session.get("user_id")


def _error_response(message: str, status: int = 400, data=None):
    """Return an error in the existing frontend response format."""
    body, status_code = fail(message, data=data, status=status)
    return JSONResponse(content=body, status_code=status_code)


def _log_activity(user_id: str, text: str):
    """Record a feedback-related activity."""
    get_db()["activity"].insert_one({
        "id": generate_id("act-"),
        "userId": user_id,
        "text": text,
        "at": now_iso(),
    })


@router.get("")
def get_all(request: Request):
    """Get all feedback belonging to the authenticated user."""

    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", status=401)

    items = mongo_docs_to_list(
        get_db()["feedback"]
        .find({"userId": uid})
        .sort("createdAt", -1)
    )

    return ok(items)


@router.post("")
def create(
    request: Request,
    body: dict = Body(default={}),
):
    """Create a feedback record."""

    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", status=401)

    record, error = normalize_feedback(body)

    if error:
        return _error_response(error)

    record["id"] = generate_id("fb-")
    record["userId"] = uid

    db = get_db()
    db["feedback"].insert_one(record)

    _log_activity(
        uid,
        f'Feedback "{record["title"]}" added',
    )

    return ok(
        mongo_doc_to_dict(record),
        "Feedback created",
    )


@router.put("/{feedback_id}")
def update(
    feedback_id: str,
    request: Request,
    body: dict = Body(default={}),
):
    """Update an existing feedback record."""

    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", status=401)

    db = get_db()

    existing = db["feedback"].find_one({
        "id": feedback_id,
        "userId": uid,
    })

    if not existing:
        return _error_response(
            "Feedback not found.",
            status=404,
        )

    record, error = normalize_feedback(body, existing)

    if error:
        return _error_response(error)

    record["id"] = feedback_id
    record["userId"] = uid

    db["feedback"].update_one(
        {
            "id": feedback_id,
            "userId": uid,
        },
        {"$set": record},
    )

    updated = db["feedback"].find_one({
        "id": feedback_id,
        "userId": uid,
    })

    _log_activity(
        uid,
        f'Feedback "{record["title"]}" updated',
    )

    return ok(
        mongo_doc_to_dict(updated),
        "Feedback updated",
    )


@router.delete("/{feedback_id}")
def remove(
    feedback_id: str,
    request: Request,
):
    """Delete an existing feedback record."""

    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", status=401)

    db = get_db()

    target = db["feedback"].find_one({
        "id": feedback_id,
        "userId": uid,
    })

    if not target:
        return _error_response(
            "Feedback not found.",
            status=404,
        )

    db["feedback"].delete_one({
        "id": feedback_id,
        "userId": uid,
    })

    _log_activity(
        uid,
        f'Feedback "{target["title"]}" deleted',
    )

    return ok(
        {"id": feedback_id},
        "Feedback deleted",
    )


@router.post("/import")
def import_many(
    request: Request,
    body: dict = Body(default={}),
):
    """Import multiple feedback records."""

    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", status=401)

    records = body.get("records", [])

    if not isinstance(records, list):
        return _error_response("records must be an array.")

    db = get_db()

    existing_ids = {
        doc["id"]
        for doc in db["feedback"].find(
            {"userId": uid},
            {"id": 1},
        )
    }

    added = 0
    skipped = 0

    for raw in records:
        if not isinstance(raw, dict):
            skipped += 1
            continue

        record, error = normalize_feedback(raw)

        if error:
            skipped += 1
            continue

        record_id = raw.get("id") or generate_id("fb-")

        if record_id in existing_ids:
            skipped += 1
            continue

        record["id"] = record_id
        record["userId"] = uid

        db["feedback"].insert_one(record)
        existing_ids.add(record_id)
        added += 1

    _log_activity(
        uid,
        f"Imported {added} feedback record(s)",
    )

    return ok(
        {"added": added, "skipped": skipped},
        f"Imported {added} record(s)",
    )