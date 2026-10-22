"""Roadmap CRUD routes using FastAPI."""

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

router = APIRouter(prefix="/api/roadmap", tags=["Roadmap"])


def _error_response(message, status_code=400):
    """Convert the existing Flask-style fail() result to a FastAPI response."""
    body, status = fail(message, status=status_code)
    return JSONResponse(content=body, status_code=status)


def _user_id(request: Request):
    """Get the logged-in user's ID."""
    return request.session.get("user_id")


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


@router.get("")
def get_all(request: Request):
    """Return all roadmap items for the logged-in user."""
    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", 401)

    items = mongo_docs_to_list(
        get_db()["roadmap"].find({"userId": uid})
    )

    return ok(items)


@router.post("")
def create(
    request: Request,
    body: dict | None = Body(default=None),
):
    """Create a roadmap item."""
    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", 401)

    body = body or {}

    name = body.get("name") or ""

    if not isinstance(name, str):
        return _error_response("Name is required.")

    name = name.strip()

    if not name:
        return _error_response("Name is required.")

    start = body.get("startDate", "")
    target = body.get("targetDate", "")

    if start and target and target < start:
        return _error_response(
            "Target date cannot be before start date."
        )

    item = {
        "id": generate_id("rm-"),
        "userId": uid,
        "featureId": body.get("featureId", ""),
        "name": name,
        "startDate": start,
        "targetDate": target,
        "priority": body.get("priority", "Medium"),
        "status": body.get("status", "Planned"),
        "owner": body.get("owner", "Unassigned"),
        "theme": body.get("theme", ""),
    }

    get_db()["roadmap"].insert_one(item)

    _log_activity(
        uid,
        f'Roadmap item "{item["name"]}" added',
    )

    return ok(mongo_doc_to_dict(item), "Roadmap item created")


@router.put("/{item_id}")
def update(
    item_id: str,
    request: Request,
    body: dict | None = Body(default=None),
):
    """Update an existing roadmap item."""
    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", 401)

    db = get_db()

    existing = db["roadmap"].find_one(
        {
            "id": item_id,
            "userId": uid,
        }
    )

    if not existing:
        return _error_response("Roadmap item not found.", 404)

    body = body or {}
    merged = {**existing, **body}

    start = merged.get("startDate", "")
    target = merged.get("targetDate", "")

    if start and target and target < start:
        return _error_response(
            "Target date cannot be before start date."
        )

    allowed_fields = (
        "name",
        "featureId",
        "startDate",
        "targetDate",
        "priority",
        "status",
        "owner",
        "theme",
    )

    updates = {
        field: body[field]
        for field in allowed_fields
        if field in body
    }

    if "name" in updates:
        if (
            not isinstance(updates["name"], str)
            or not updates["name"].strip()
        ):
            return _error_response("Name is required.")

        updates["name"] = updates["name"].strip()

    if updates:
        db["roadmap"].update_one(
            {
                "id": item_id,
                "userId": uid,
            },
            {"$set": updates},
        )

    updated = db["roadmap"].find_one(
        {
            "id": item_id,
            "userId": uid,
        }
    )

    _log_activity(
        uid,
        f'Roadmap item "{updated["name"]}" updated',
    )

    return ok(
        mongo_doc_to_dict(updated),
        "Roadmap item updated",
    )


@router.delete("/{item_id}")
def remove(item_id: str, request: Request):
    """Delete a roadmap item."""
    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", 401)

    db = get_db()

    target = db["roadmap"].find_one(
        {
            "id": item_id,
            "userId": uid,
        }
    )

    if not target:
        return _error_response("Roadmap item not found.", 404)

    db["roadmap"].delete_one(
        {
            "id": item_id,
            "userId": uid,
        }
    )

    _log_activity(
        uid,
        f'Roadmap item "{target["name"]}" deleted',
    )

    return ok(
        {"id": item_id},
        "Roadmap item deleted",
    )