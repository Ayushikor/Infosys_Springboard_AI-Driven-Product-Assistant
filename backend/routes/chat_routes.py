"""Chat history persistence routes.

The actual chat logic (rule-based answers) lives in the frontend.
This endpoint just stores / retrieves the conversation history.
"""

from flask import Blueprint, request, session
from db import get_db
from helpers import ok, fail, mongo_docs_to_list

chat_bp = Blueprint("chat", __name__, url_prefix="/api/chat")


@chat_bp.route("", methods=["GET"])
def get_history():
    uid = session.get("user_id")
    if not uid:
        return fail("Not authenticated.", status=401)

    messages = mongo_docs_to_list(
        get_db()["chat_messages"].find({"userId": uid}).sort("_id", 1)
    )
    return ok(messages)


@chat_bp.route("", methods=["PUT"])
def save_history():
    uid = session.get("user_id")
    if not uid:
        return fail("Not authenticated.", status=401)

    body = request.get_json(silent=True) or {}
    messages = body.get("messages", [])
    if not isinstance(messages, list):
        return fail("messages must be an array.")

    db = get_db()
    # Replace all chat messages for this user
    db["chat_messages"].delete_many({"userId": uid})
    if messages:
        docs = [{"userId": uid, **msg} for msg in messages]
        db["chat_messages"].insert_many(docs)

    return ok(messages)


@chat_bp.route("", methods=["DELETE"])
def clear():
    uid = session.get("user_id")
    if not uid:
        return fail("Not authenticated.", status=401)

    get_db()["chat_messages"].delete_many({"userId": uid})
    return ok([], "Conversation cleared")
