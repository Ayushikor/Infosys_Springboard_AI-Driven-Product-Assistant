"""PRD CRUD routes."""

from flask import Blueprint, request, session
from db import get_db
from helpers import ok, fail, generate_id, now_iso, mongo_doc_to_dict, mongo_docs_to_list

prd_bp = Blueprint("prds", __name__, url_prefix="/api/prds")


def _user_id():
    return session.get("user_id")


def _log_activity(user_id, text):
    get_db()["activity"].insert_one({
        "id": generate_id("act-"),
        "userId": user_id,
        "text": text,
        "at": now_iso(),
    })


@prd_bp.route("", methods=["GET"])
def get_all():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)
    items = mongo_docs_to_list(get_db()["prds"].find({"userId": uid}))
    return ok(items)


@prd_bp.route("", methods=["POST"])
def create():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    if not title:
        return fail("PRD title is required.")

    prd = {
        "id": generate_id("prd-"),
        "userId": uid,
        "title": title,
        "featureId": body.get("featureId", ""),
        "version": body.get("version", "0.1"),
        "status": body.get("status", "Draft"),
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
        "content": body.get("content"),
    }

    get_db()["prds"].insert_one(prd)
    _log_activity(uid, f'PRD "{prd["title"]}" created')
    return ok(mongo_doc_to_dict(prd), "PRD created")


@prd_bp.route("/<prd_id>", methods=["PUT"])
def update(prd_id):
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    existing = db["prds"].find_one({"id": prd_id, "userId": uid})
    if not existing:
        return fail("PRD not found.", status=404)

    body = request.get_json(silent=True) or {}
    updates = {}
    for field in ("title", "featureId", "version", "status", "content"):
        if field in body:
            updates[field] = body[field]
    updates["updatedAt"] = now_iso()

    db["prds"].update_one({"id": prd_id, "userId": uid}, {"$set": updates})
    updated = db["prds"].find_one({"id": prd_id, "userId": uid})
    _log_activity(uid, f'PRD "{updated["title"]}" updated')
    return ok(mongo_doc_to_dict(updated), "PRD saved")


@prd_bp.route("/<prd_id>", methods=["DELETE"])
def remove(prd_id):
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    target = db["prds"].find_one({"id": prd_id, "userId": uid})
    if not target:
        return fail("PRD not found.", status=404)

    db["prds"].delete_one({"id": prd_id, "userId": uid})
    _log_activity(uid, f'PRD "{target["title"]}" deleted')
    return ok({"id": prd_id}, "PRD deleted")
