"""Chat history persistence routes using FastAPI.

The actual chat logic (rule-based answers) lives in the frontend.
This endpoint only stores and retrieves conversation history.
"""

from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse

from db import get_db
from helpers import ok, fail, mongo_docs_to_list


router = APIRouter(prefix="/api/chat", tags=["Chat"])


def _error_response(message, status_code=400):
    """Convert the existing Flask-style fail() result to a FastAPI response."""

    body, status = fail(message, status=status_code)
    return JSONResponse(content=body, status_code=status)


@router.get("")
def get_history(request: Request):
    uid = request.session.get("user_id")

    if not uid:
        return _error_response("Not authenticated.", 401)

    messages = mongo_docs_to_list(
        get_db()["chat_messages"]
        .find({"userId": uid})
        .sort("_id", 1)
    )

    return ok(messages)


@router.put("")
def save_history(
    request: Request,
    body: dict | None = Body(default=None),
):
    uid = request.session.get("user_id")

    if not uid:
        return _error_response("Not authenticated.", 401)

    body = body or {}
    messages = body.get("messages", [])

    if not isinstance(messages, list):
        return _error_response("messages must be an array.")

    # Validate the items before changing stored history.
    if not all(isinstance(message, dict) for message in messages):
        return _error_response("Each message must be an object.")

    db = get_db()

    # Replace all chat messages belonging to this user.
    db["chat_messages"].delete_many({"userId": uid})

    if messages:
        docs = [
            {"userId": uid, **message}
            for message in messages
        ]
        db["chat_messages"].insert_many(docs)

    return ok(messages)


@router.delete("")
def clear(request: Request):
    uid = request.session.get("user_id")

    if not uid:
        return _error_response("Not authenticated.", 401)

    get_db()["chat_messages"].delete_many({"userId": uid})

    return ok([], "Conversation cleared")
