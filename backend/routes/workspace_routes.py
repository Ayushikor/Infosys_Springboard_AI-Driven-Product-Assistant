"""Workspace CRUD routes."""

from flask import Blueprint, request, session
from db import get_db
from helpers import ok, fail, generate_id, now_iso, mongo_doc_to_dict, mongo_docs_to_list

workspace_bp = Blueprint("workspaces", __name__, url_prefix="/api/workspaces")


def _user_id():
    return session.get("user_id")


def _log_activity(user_id, text):
    get_db()["activity"].insert_one({
        "id": generate_id("act-"),
        "userId": user_id,
        "text": text,
        "at": now_iso(),
    })


@workspace_bp.route("", methods=["GET"])
def get_all():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)
    db = get_db()
    items = mongo_docs_to_list(db["workspaces"].find({"userId": uid}))
    state = db["user_state"].find_one({"userId": uid}) or {}
    return ok({"items": items, "activeId": state.get("activeWorkspaceId", "")})


@workspace_bp.route("", methods=["POST"])
def create():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if len(name) < 2:
        return fail("Workspace name must be at least 2 characters.")

    ws = {
        "id": generate_id("ws-"),
        "userId": uid,
        "name": name,
        "description": (body.get("description") or "").strip(),
        "createdAt": now_iso(),
    }
    db = get_db()
    db["workspaces"].insert_one(ws)
    db["user_state"].update_one(
        {"userId": uid}, {"$set": {"activeWorkspaceId": ws["id"]}}
    )
    _log_activity(uid, f'Workspace "{ws["name"]}" created')
    return ok(mongo_doc_to_dict(ws), "Workspace created")


@workspace_bp.route("/<ws_id>", methods=["PUT"])
def update(ws_id):
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    ws = db["workspaces"].find_one({"id": ws_id, "userId": uid})
    if not ws:
        return fail("Workspace not found.", status=404)

    body = request.get_json(silent=True) or {}
    updates = {}
    if "name" in body:
        name = (body["name"] or "").strip()
        if len(name) < 2:
            return fail("Workspace name must be at least 2 characters.")
        updates["name"] = name
    if "description" in body:
        updates["description"] = (body["description"] or "").strip()

    if updates:
        db["workspaces"].update_one({"id": ws_id, "userId": uid}, {"$set": updates})

    updated = db["workspaces"].find_one({"id": ws_id, "userId": uid})
    _log_activity(uid, f'Workspace "{updated["name"]}" updated')
    return ok(mongo_doc_to_dict(updated), "Workspace updated")


@workspace_bp.route("/<ws_id>/switch", methods=["POST"])
def switch_to(ws_id):
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    ws = db["workspaces"].find_one({"id": ws_id, "userId": uid})
    if not ws:
        return fail("Workspace not found.", status=404)

    db["user_state"].update_one(
        {"userId": uid}, {"$set": {"activeWorkspaceId": ws_id}}
    )
    return ok({"activeId": ws_id}, "Workspace switched")
