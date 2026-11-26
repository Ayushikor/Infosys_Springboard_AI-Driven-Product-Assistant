"""PRD CRUD routes using FastAPI."""

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
)

router = APIRouter(
    prefix="/api/prds",
    tags=["PRDs"],
)


# ---------------------------------------------------------
# ERROR HANDLING
# ---------------------------------------------------------


def _error_response(message, status_code=400):
    """Convert the existing fail() result to a FastAPI response."""

    body, status = fail(
        message,
        status=status_code,
    )

    return JSONResponse(
        content=body,
        status_code=status,
    )


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------


def _user_id(request: Request):
    """Get the logged-in user ID from the session."""
    return request.session.get("user_id")


# ---------------------------------------------------------
# ACTIVITY LOGGING
# ---------------------------------------------------------


def _log_activity(user_id, text):
    """Record an activity for the user."""

    get_db()["activity"].insert_one(
        {
            "id": generate_id("act-"),
            "userId": user_id,
            "text": text,
            "at": now_iso(),
        }
    )


# ---------------------------------------------------------
# NOTIFICATION HELPER
# ---------------------------------------------------------


def _create_prd_notification(
    user_id,
    title,
    event,
    message,
    prd_id=None,
):
    """
    Create a PRD notification.

    Notification failures must not affect the main PRD operation.
    """

    try:
        notification = {
            "id": generate_id("notif-"),
            "userId": user_id,
            "title": title,
            "message": message,
            "type": "success",
            "read": False,
            "isRead": False,
            "createdAt": now_iso(),
            "link": "/prds",
            "metadata": {
                "event": event,
                "prdId": prd_id,
            },
        }

        get_db()["notifications"].insert_one(notification)

    except Exception as exc:
        print(
            "[Notification] Failed to create PRD notification:",
            str(exc),
        )


# ---------------------------------------------------------
# GET ALL PRDS
# ---------------------------------------------------------


@router.get("")
def get_all(request: Request):
    """Return all PRDs belonging to the logged-in user."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            401,
        )

    items = mongo_docs_to_list(
        get_db()["prds"].find({
            "userId": uid,
        })
    )

    return ok(items)


# ---------------------------------------------------------
# CREATE PRD
# ---------------------------------------------------------


@router.post("")
def create(
    request: Request,
    body: dict | None = Body(default=None),
):
    """Create a new PRD."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            401,
        )

    body = body or {}

    title = (body.get("title") or "").strip()

    if not title:
        return _error_response(
            "PRD title is required.",
        )

    current_time = now_iso()

    prd = {
        "id": generate_id("prd-"),
        "userId": uid,
        "title": title,
        "featureId": body.get("featureId", ""),
        "version": body.get("version", "0.1"),
        "status": body.get("status", "Draft"),
        "createdAt": current_time,
        "updatedAt": current_time,
        "content": body.get("content"),
    }

    get_db()["prds"].insert_one(prd)

    # Log activity
    _log_activity(
        uid,
        f'PRD "{prd["title"]}" created',
    )

    # Create notification
    _create_prd_notification(
        user_id=uid,
        title="PRD Created Successfully",
        event="prd_created",
        message=f'Your PRD "{prd["title"]}" has been created successfully.',
        prd_id=prd["id"],
    )

    return ok(
        mongo_doc_to_dict(prd),
        "PRD created",
    )


# ---------------------------------------------------------
# UPDATE PRD
# ---------------------------------------------------------


@router.put("/{prd_id}")
def update(
    prd_id: str,
    request: Request,
    body: dict | None = Body(default=None),
):
    """Update an existing PRD."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            401,
        )

    db = get_db()

    existing = db["prds"].find_one(
        {
            "id": prd_id,
            "userId": uid,
        }
    )

    if not existing:
        return _error_response(
            "PRD not found.",
            404,
        )

    body = body or {}

    updates = {}

    for field in (
        "title",
        "featureId",
        "version",
        "status",
        "content",
    ):
        if field in body:
            updates[field] = body[field]

    # Validate title if supplied
    if "title" in updates:

        if (
            not isinstance(updates["title"], str)
            or not updates["title"].strip()
        ):
            return _error_response(
                "PRD title is required.",
            )

        updates["title"] = updates["title"].strip()

    updates["updatedAt"] = now_iso()

    db["prds"].update_one(
        {
            "id": prd_id,
            "userId": uid,
        },
        {
            "$set": updates,
        },
    )

    updated = db["prds"].find_one(
        {
            "id": prd_id,
            "userId": uid,
        }
    )

    # Log activity
    _log_activity(
        uid,
        f'PRD "{updated["title"]}" updated',
    )

    # Create notification
    _create_prd_notification(
        user_id=uid,
        title="PRD Updated Successfully",
        event="prd_updated",
        message=f'Your PRD "{updated["title"]}" has been saved successfully.',
        prd_id=prd_id,
    )

    return ok(
        mongo_doc_to_dict(updated),
        "PRD saved",
    )


# ---------------------------------------------------------
# DELETE PRD
# ---------------------------------------------------------


@router.delete("/{prd_id}")
def remove(
    prd_id: str,
    request: Request,
):
    """Delete a PRD belonging to the logged-in user."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            401,
        )

    db = get_db()

    target = db["prds"].find_one(
        {
            "id": prd_id,
            "userId": uid,
        }
    )

    if not target:
        return _error_response(
            "PRD not found.",
            404,
        )

    db["prds"].delete_one(
        {
            "id": prd_id,
            "userId": uid,
        }
    )

    # Log activity
    _log_activity(
        uid,
        f'PRD "{target["title"]}" deleted',
    )

    return ok(
        {
            "id": prd_id,
        },
        "PRD deleted",
    )