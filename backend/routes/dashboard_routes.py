"""Dashboard / activity routes."""

from flask import Blueprint, session
from db import get_db
from helpers import ok, fail, mongo_docs_to_list

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api")


@dashboard_bp.route("/activity", methods=["GET"])
def get_activity():
    uid = session.get("user_id")
    if not uid:
        return fail("Not authenticated.", status=401)

    items = mongo_docs_to_list(
        get_db()["activity"].find({"userId": uid}).sort("at", -1).limit(50)
    )
    return ok(items)
