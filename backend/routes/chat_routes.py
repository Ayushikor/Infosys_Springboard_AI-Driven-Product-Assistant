"""Chat routes for MongoDB-grounded AI conversations and history."""

import logging

import httpx
from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse

from db import get_db
from helpers import ok, fail, mongo_docs_to_list
from config import AI_SERVICE_URL, AI_SERVICE_TIMEOUT_SECONDS


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

# Maximum records loaded from an individual collection.
# Counts are also sent so Gemini can distinguish complete from
# partially retrieved collections.
COLLECTION_LIMIT = 1000


def _error_response(message: str, status_code: int = 400):
    """Return an error using the existing API response format."""
    body, status = fail(message, status=status_code)
    return JSONResponse(content=body, status_code=status)



def _load_user_collection(db, collection_name: str, user_id: str):
    """Load only records owned by the authenticated user."""
    collection = db[collection_name]
    query = {"userId": user_id}

    total = collection.count_documents(query)

    cursor = (
        collection.find(query)
        .sort("_id", -1)
        .limit(COLLECTION_LIMIT)
    )

    records = mongo_docs_to_list(cursor)

    logger.info(
        "COLLECTION CHECK | name=%s | authenticated_user=%s | "
        "matched=%s | loaded=%s",
        collection_name,
        user_id,
        total,
        len(records),
    )

    if collection_name in (
        "customer_feedback",
        "support_tickets",
        "user_reviews",
        "analysis_runs",
    ):
        logger.info(
            "COLLECTION SAMPLE | name=%s | sample=%s",
            collection_name,
            [
                {
                    "id": record.get("feedback_id")
                         or record.get("id")
                         or record.get("ticket_id")
                         or record.get("review_id"),
                    "userId": record.get("userId"),
                }
                for record in records[:3]
            ],
        )

    return {
        "total_records": total,
        "loaded_records": len(records),
        "truncated": total > len(records),
        "records": records,
    }



def _build_database_context(user_id: str):
    """
    Retrieve the authenticated user's application data from MongoDB.

    Sensitive authentication records are deliberately excluded.
    """
    db = get_db()

    collection_names = [
        "workspaces",
        "products",
        "feedback",
        "customer_feedback",
        "support_tickets",
        "user_reviews",
        "themes",
        "features",
        "prds",
        "roadmap",
        "activity",
        "analysis_runs",
        "analysis_batches",
    ]

    context = {
        "source": "MongoDB",
        "user_scope": "authenticated_user",
        "collections": {},
    }

    # Load the user's application and original feedback collections.
    for collection_name in collection_names:
        context["collections"][collection_name] = _load_user_collection(
            db,
            collection_name,
            user_id,
        )

    # User preferences and active workspace.
    user_state = db["user_state"].find_one(
        {"userId": user_id},
        {"_id": 0},
    )

    context["collections"]["user_state"] = {
        "total_records": 1 if user_state else 0,
        "loaded_records": 1 if user_state else 0,
        "truncated": False,
        "records": [user_state] if user_state else [],
    }

    # Include a compact inventory for transparency.
    context["data_inventory"] = {
        name: {
            "total_records": data["total_records"],
            "loaded_records": data["loaded_records"],
            "truncated": data["truncated"],
        }
        for name, data in context["collections"].items()
    }

    return context


@router.post("")
def chat_with_ai(
    request: Request,
    body: dict | None = Body(default=None),
):
    """Retrieve MongoDB context and forward the message to Gemini."""
    user_id = request.session.get("user_id")

    if not user_id:
        return _error_response("Not authenticated.", 401)

    body = body or {}
    message = body.get("message")

    if not isinstance(message, str) or not message.strip():
        return _error_response("A chat message is required.")

    try:
        # Always retrieve fresh database records.
        # Do not trust database context supplied by the frontend.
        database_context = _build_database_context(user_id)

        # Copy the request so that the original body is not modified.
        ai_payload = dict(body)

        # The backend is the source of truth for database context.
        ai_payload["database_context"] = database_context

        # Do not expose the authenticated user's internal ID to Gemini.
        ai_payload.pop("user_id", None)
        ai_payload.pop("userId", None)

        logger.info(
            "Sending grounded chatbot request. Loaded data inventory: %s",
            database_context["data_inventory"],
        )

        response = httpx.post(
            f"{AI_SERVICE_URL.rstrip('/')}/chat",
            json=ai_payload,
            timeout=AI_SERVICE_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        ai_response = response.json()

        return ok(ai_response)

    except httpx.TimeoutException:
        logger.exception("AI chatbot request timed out.")
        return _error_response(
            "The AI assistant took too long to respond. Please try again.",
            504,
        )

    except httpx.HTTPStatusError as exc:
        logger.exception(
            "AI module returned an error: %s",
            exc.response.status_code,
        )
        return _error_response(
            "The AI assistant could not process your request.",
            502,
        )

    except httpx.RequestError:
        logger.exception("Could not connect to the AI module.")
        return _error_response(
            "The AI service is currently unavailable.",
            503,
        )

    except Exception:
        logger.exception("Unexpected chatbot route error.")
        return _error_response(
            "An unexpected chatbot error occurred.",
            500,
        )


@router.get("")
def get_history(request: Request):
    """Retrieve the authenticated user's chat history."""
    user_id = request.session.get("user_id")

    if not user_id:
        return _error_response("Not authenticated.", 401)

    messages = mongo_docs_to_list(
        get_db()["chat_messages"]
        .find({"userId": user_id})
        .sort("_id", 1)
    )

    return ok(messages)


@router.put("")
def save_history(
    request: Request,
    body: dict | None = Body(default=None),
):
    """Replace the authenticated user's chat history."""
    user_id = request.session.get("user_id")

    if not user_id:
        return _error_response("Not authenticated.", 401)

    body = body or {}
    messages = body.get("messages", [])

    if not isinstance(messages, list):
        return _error_response("messages must be an array.")

    if not all(isinstance(message, dict) for message in messages):
        return _error_response("Each message must be an object.")

    db = get_db()
    db["chat_messages"].delete_many({"userId": user_id})

    if messages:
        # Set userId last so a client-supplied userId cannot override it.
        documents = [
            {**message, "userId": user_id}
            for message in messages
        ]
        db["chat_messages"].insert_many(documents)

    return ok(messages)


@router.delete("")
def clear(request: Request):
    """Clear the authenticated user's conversation history."""
    user_id = request.session.get("user_id")

    if not user_id:
        return _error_response("Not authenticated.", 401)

    get_db()["chat_messages"].delete_many({"userId": user_id})
    return ok([], "Conversation cleared")
