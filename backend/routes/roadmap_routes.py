"""Roadmap CRUD routes."""

from flask import Blueprint, request, session
from db import get_db
from helpers import ok, fail, generate_id, now_iso, mongo_doc_to_dict, mongo_docs_to_list

roadmap_bp = Blueprint("roadmap", __name__, url_prefix="/api/roadmap")


def _user_id():
    return session.get("user_id")


def _log_activity(user_id, text):
    get_db()["activity"].insert_one({
        "id": generate_id("act-"),
        "userId": user_id,
        "text": text,
        "at": now_iso(),
    })


@roadmap_bp.route("", methods=["GET"])
def get_all():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)
    items = mongo_docs_to_list(get_db()["roadmap"].find({"userId": uid}))
    return ok(items)


@roadmap_bp.route("", methods=["POST"])
def create():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    if not name:
        return fail("Name is required.")

    start = body.get("startDate", "")
    target = body.get("targetDate", "")
    if start and target and target < start:
        return fail("Target date cannot be before start date.")

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
    _log_activity(uid, f'Roadmap item "{item["name"]}" added')
    return ok(mongo_doc_to_dict(item), "Roadmap item created")


@roadmap_bp.route("/<item_id>", methods=["PUT"])
def update(item_id):
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    existing = db["roadmap"].find_one({"id": item_id, "userId": uid})
    if not existing:
        return fail("Roadmap item not found.", status=404)

    body = request.get_json(silent=True) or {}
    merged = {**existing, **body}

    start = merged.get("startDate", "")
    target = merged.get("targetDate", "")
    if start and target and target < start:
        return fail("Target date cannot be before start date.")

    updates = {}
    for field in ("name", "featureId", "startDate", "targetDate", "priority", "status", "owner", "theme"):
        if field in body:
            updates[field] = body[field]

    if updates:
        db["roadmap"].update_one({"id": item_id, "userId": uid}, {"$set": updates})

    updated = db["roadmap"].find_one({"id": item_id, "userId": uid})
    _log_activity(uid, f'Roadmap item "{updated["name"]}" updated')
    return ok(mongo_doc_to_dict(updated), "Roadmap item updated")


@roadmap_bp.route("/<item_id>", methods=["DELETE"])
def remove(item_id):
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    target = db["roadmap"].find_one({"id": item_id, "userId": uid})
    if not target:
        return fail("Roadmap item not found.", status=404)

    db["roadmap"].delete_one({"id": item_id, "userId": uid})
    _log_activity(uid, f'Roadmap item "{target["name"]}" deleted')
    return ok({"id": item_id}, "Roadmap item deleted")
