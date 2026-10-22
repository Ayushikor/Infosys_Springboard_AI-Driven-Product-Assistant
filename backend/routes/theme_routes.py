"""Theme routes."""

from flask import Blueprint, request, session
from db import get_db
from helpers import ok, fail, mongo_doc_to_dict, mongo_docs_to_list

theme_bp = Blueprint("themes", __name__, url_prefix="/api/themes")


@theme_bp.route("", methods=["GET"])
def get_all():
    uid = session.get("user_id")
    if not uid:
        return fail("Not authenticated.", status=401)
    items = mongo_docs_to_list(get_db()["themes"].find({"userId": uid}))
    return ok(items)


@theme_bp.route("/<theme_id>/keywords", methods=["PUT"])
def save_keywords(theme_id):
    uid = session.get("user_id")
    if not uid:
        return fail("Not authenticated.", status=401)

    db = get_db()
    theme = db["themes"].find_one({"id": theme_id, "userId": uid})
    if not theme:
        return fail("Theme not found.", status=404)

    body = request.get_json(silent=True) or {}
    keywords = body.get("keywords", [])
    if not isinstance(keywords, list):
        return fail("keywords must be an array.")

    db["themes"].update_one(
        {"id": theme_id, "userId": uid}, {"$set": {"keywords": keywords}}
    )
    updated = db["themes"].find_one({"id": theme_id, "userId": uid})
    return ok(mongo_doc_to_dict(updated), "Theme keywords saved")
