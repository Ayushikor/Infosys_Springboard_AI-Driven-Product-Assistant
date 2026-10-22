"""Workspace CRUD routes."""

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
    prefix="/api/workspaces",
    tags=["Workspaces"],
)


def _user_id(request: Request):
    """Return the authenticated user's ID from the session."""
    return request.session.get("user_id")


def _error_response(message: str, status: int = 400, data=None):
    """Return an error using the existing frontend response format."""
    body, status_code = fail(message, data=data, status=status)

    return JSONResponse(
        content=body,
        status_code=status_code,
    )


def _log_activity(user_id: str, text: str):
    """Record a workspace activity."""
    get_db()["activity"].insert_one({
        "id": generate_id("act-"),
        "userId": user_id,
        "text": text,
        "at": now_iso(),
    })


@router.get("")
def get_all(request: Request):
    """Return the authenticated user's workspaces."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    db = get_db()

    items = mongo_docs_to_list(
        db["workspaces"].find({"userId": uid})
    )

    state = db["user_state"].find_one(
        {"userId": uid}
    ) or {}

    return ok({
        "items": items,
        "activeId": state.get("activeWorkspaceId", ""),
    })


@router.post("")
def create(
    request: Request,
    body: dict = Body(default={}),
):
    """Create a workspace and make it active."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    name = (body.get("name") or "").strip()

    if len(name) < 2:
        return _error_response(
            "Workspace name must be at least 2 characters."
        )

    ws = {
        "id": generate_id("ws-"),
        "userId": uid,
        "name": name,
        "description": (
            body.get("description") or ""
        ).strip(),
        "createdAt": now_iso(),
    }

    db = get_db()

    db["workspaces"].insert_one(ws)

    db["user_state"].update_one(
        {"userId": uid},
        {"$set": {"activeWorkspaceId": ws["id"]}},
    )

    _log_activity(
        uid,
        f'Workspace "{ws["name"]}" created',
    )

    return ok(
        mongo_doc_to_dict(ws),
        "Workspace created",
    )


@router.put("/{ws_id}")
def update(
    ws_id: str,
    request: Request,
    body: dict = Body(default={}),
):
    """Update an existing workspace."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    db = get_db()

    ws = db["workspaces"].find_one({
        "id": ws_id,
        "userId": uid,
    })

    if not ws:
        return _error_response(
            "Workspace not found.",
            status=404,
        )

    updates = {}

    if "name" in body:
        name = (body["name"] or "").strip()

        if len(name) < 2:
            return _error_response(
                "Workspace name must be at least 2 characters."
            )

        updates["name"] = name

    if "description" in body:
        updates["description"] = (
            body["description"] or ""
        ).strip()

    if updates:
        db["workspaces"].update_one(
            {
                "id": ws_id,
                "userId": uid,
            },
            {"$set": updates},
        )

    updated = db["workspaces"].find_one({
        "id": ws_id,
        "userId": uid,
    })

    _log_activity(
        uid,
        f'Workspace "{updated["name"]}" updated',
    )

    return ok(
        mongo_doc_to_dict(updated),
        "Workspace updated",
    )


@router.post("/{ws_id}/switch")
def switch_to(
    ws_id: str,
    request: Request,
):
    """Switch the active workspace."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    db = get_db()

    ws = db["workspaces"].find_one({
        "id": ws_id,
        "userId": uid,
    })

    if not ws:
        return _error_response(
            "Workspace not found.",
            status=404,
        )

    db["user_state"].update_one(
        {"userId": uid},
        {"$set": {"activeWorkspaceId": ws_id}},
    )

    return ok(
        {"activeId": ws_id},
        "Workspace switched",
    )