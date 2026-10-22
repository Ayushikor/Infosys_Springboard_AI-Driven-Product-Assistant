"""Feedback CRUD routes."""

from flask import Blueprint, request, session
from db import get_db
from helpers import (
    ok, fail, generate_id, now_iso,
    mongo_doc_to_dict, mongo_docs_to_list, normalize_feedback,
)

feedback_bp = Blueprint("feedback", __name__, url_prefix="/api/feedback")


def _user_id():
    return session.get("user_id")


def _log_activity(user_id, text):
    get_db()["activity"].insert_one({
        "id": generate_id("act-"),
        "userId": user_id,
        "text": text,
        "at": now_iso(),
    })


@feedback_bp.route("", methods=["GET"])
def get_all():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)
    items = mongo_docs_to_list(
        get_db()["feedback"].find({"userId": uid}).sort("createdAt", -1)
    )
    return ok(items)


@feedback_bp.route("", methods=["POST"])
def create():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    body = request.get_json(silent=True) or {}
    record, error = normalize_feedback(body)
    if error:
        return fail(error)

    record["id"] = generate_id("fb-")
    record["userId"] = uid

    get_db()["feedback"].insert_one(record)
    _log_activity(uid, f'Feedback "{record["title"]}" added')
    return ok(mongo_doc_to_dict(record), "Feedback created")


@feedback_bp.route("/<feedback_id>", methods=["PUT"])
def update(feedback_id):
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    existing = db["feedback"].find_one({"id": feedback_id, "userId": uid})
    if not existing:
        return fail("Feedback not found.", status=404)

    body = request.get_json(silent=True) or {}
    record, error = normalize_feedback(body, existing)
    if error:
        return fail(error)

    record["id"] = feedback_id
    record["userId"] = uid
    db["feedback"].update_one({"id": feedback_id, "userId": uid}, {"$set": record})
    _log_activity(uid, f'Feedback "{record["title"]}" updated')
    return ok(
        mongo_doc_to_dict(db["feedback"].find_one({"id": feedback_id})),
        "Feedback updated",
    )


@feedback_bp.route("/<feedback_id>", methods=["DELETE"])
def remove(feedback_id):
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    target = db["feedback"].find_one({"id": feedback_id, "userId": uid})
    if not target:
        return fail("Feedback not found.", status=404)

    db["feedback"].delete_one({"id": feedback_id, "userId": uid})
    _log_activity(uid, f'Feedback "{target["title"]}" deleted')
    return ok({"id": feedback_id}, "Feedback deleted")


@feedback_bp.route("/import", methods=["POST"])
def import_many():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    body = request.get_json(silent=True) or {}
    records = body.get("records", [])
    if not isinstance(records, list):
        return fail("records must be an array.")

    db = get_db()
    existing_ids = set(
        doc["id"] for doc in db["feedback"].find({"userId": uid}, {"id": 1})
    )

    added = 0
    skipped = 0
    for raw in records:
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

    _log_activity(uid, f"Imported {added} feedback record(s)")
    return ok({"added": added, "skipped": skipped}, f"Imported {added} record(s)")
