"""Feature (prioritization) CRUD routes."""

from flask import Blueprint, request, session
from db import get_db
from helpers import (
    ok, fail, generate_id, now_iso,
    mongo_doc_to_dict, mongo_docs_to_list, normalize_feature,
)

feature_bp = Blueprint("features", __name__, url_prefix="/api/features")


def _user_id():
    return session.get("user_id")


def _log_activity(user_id, text):
    get_db()["activity"].insert_one({
        "id": generate_id("act-"),
        "userId": user_id,
        "text": text,
        "at": now_iso(),
    })


@feature_bp.route("", methods=["GET"])
def get_all():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)
    items = mongo_docs_to_list(get_db()["features"].find({"userId": uid}))
    return ok(items)


@feature_bp.route("", methods=["POST"])
def create():
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    body = request.get_json(silent=True) or {}
    record, error = normalize_feature(body)
    if error:
        return fail(error)

    record["id"] = generate_id("ft-")
    record["userId"] = uid

    get_db()["features"].insert_one(record)
    _log_activity(uid, f'Feature "{record["name"]}" added')
    return ok(mongo_doc_to_dict(record), "Feature created")


@feature_bp.route("/<feature_id>", methods=["PUT"])
def update(feature_id):
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    existing = db["features"].find_one({"id": feature_id, "userId": uid})
    if not existing:
        return fail("Feature not found.", status=404)

    body = request.get_json(silent=True) or {}
    record, error = normalize_feature(body, existing)
    if error:
        return fail(error)

    record["id"] = feature_id
    record["userId"] = uid
    db["features"].update_one({"id": feature_id, "userId": uid}, {"$set": record})
    _log_activity(uid, f'Feature "{record["name"]}" updated')
    return ok(
        mongo_doc_to_dict(db["features"].find_one({"id": feature_id})),
        "Feature updated",
    )


@feature_bp.route("/<feature_id>", methods=["DELETE"])
def remove(feature_id):
    uid = _user_id()
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    target = db["features"].find_one({"id": feature_id, "userId": uid})
    if not target:
        return fail("Feature not found.", status=404)

    db["features"].delete_one({"id": feature_id, "userId": uid})
    _log_activity(uid, f'Feature "{target["name"]}" deleted')
    return ok({"id": feature_id}, "Feature deleted")
