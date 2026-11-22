
"""Chat routes for MongoDB-grounded AI conversations and persistent artifacts."""

import logging

from datetime import datetime, timezone

from uuid import uuid4

import httpx

from fastapi import APIRouter, Request, Body

from fastapi.responses import JSONResponse

from db import get_db

from helpers import ok, fail, mongo_docs_to_list, generate_id, now_iso

from config import AI_SERVICE_URL, AI_SERVICE_TIMEOUT_SECONDS

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

COLLECTION_LIMIT = 1000

ARTIFACT_COLLECTION = "chat_artifacts"

SUPPORTED_ARTIFACT_TYPES = {
    "prd": "prd",
    "product_requirements_document": "prd",
    "prd_generation": "prd",
    "prd_generation_agent": "prd",
    "user_story": "user_stories",
    "user-stories": "user_stories",
    "user_story_generation": "user_stories",
    "user_story_agent": "user_stories",
    "user_stories": "user_stories",
    "user-story": "user_stories",
    "user_stories_generation": "user_stories",
    "feature_prioritization": "feature_prioritization",
    "feature-prioritization": "feature_prioritization",
    "feature_prioritization_agent": "feature_prioritization",
    "prioritization": "feature_prioritization",
}

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
                    "id": (

                        record.get("feedback_id")

                        or record.get("id")

                        or record.get("ticket_id")

                        or record.get("review_id")

                    ),
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
    """Retrieve the authenticated user's application data from MongoDB."""

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

    for collection_name in collection_names:

        context["collections"][collection_name] = _load_user_collection(

            db,

            collection_name,

            user_id,

        )

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

    context["data_inventory"] = {

        name: {
            "total_records": data["total_records"],
            "loaded_records": data["loaded_records"],
            "truncated": data["truncated"],
        }

        for name, data in context["collections"].items()
    }

    return context

def _get_conversation_id(body: dict) -> str:
    """Get or create a stable conversation ID."""

    conversation_id = (

        body.get("conversation_id")

        or body.get("conversationId")

    )

    if conversation_id is None:

        return f"conversation-{uuid4()}"

    if not isinstance(conversation_id, str):

        raise ValueError("conversation_id must be a string.")

    conversation_id = conversation_id.strip()

    if not conversation_id or len(conversation_id) > 200:

        raise ValueError("Invalid conversation_id.")

    return conversation_id

def _load_conversation_artifacts(

    db,

    user_id: str,

    conversation_id: str,

) -> dict:
    """

    Retrieve previously generated artifacts.

    Artifacts are scoped to both the authenticated user

    and the conversation.
    """

    documents = db[ARTIFACT_COLLECTION].find(

        {
            "userId": user_id,
            "conversationId": conversation_id,
        },

        {
            "_id": 0,
            "artifactType": 1,
            "artifact": 1,
        },

    )

    artifacts = {
        "prd": None,
        "user_stories": None,
        "feature_prioritization": None,
    }

    for document in documents:

        artifact_type = document.get("artifactType")

        artifact_key = SUPPORTED_ARTIFACT_TYPES.get(artifact_type)

        if artifact_key and isinstance(document.get("artifact"), dict):

            artifacts[artifact_key] = document["artifact"]

    return artifacts

def _save_generated_artifact(

    db,

    user_id: str,

    conversation_id: str,

    artifact_type: str,

    artifact: dict,

):
    """Persist a successfully generated artifact in MongoDB."""

    normalized_type = SUPPORTED_ARTIFACT_TYPES.get(

        artifact_type.strip().lower()

    )

    if not normalized_type:

        logger.warning(
            "Unsupported chat artifact type: %s",

            artifact_type,

        )

        return

    if not isinstance(artifact, dict) or not artifact:

        logger.warning(
            "Empty or invalid artifact received: %s",

            normalized_type,

        )

        return

    now = datetime.now(timezone.utc)

    db[ARTIFACT_COLLECTION].update_one(

        {
            "userId": user_id,
            "conversationId": conversation_id,
            "artifactType": normalized_type,
        },

        {
            "$set": {
                "artifact": artifact,
                "updatedAt": now,
            },
            "$setOnInsert": {
                "userId": user_id,
                "conversationId": conversation_id,
                "artifactType": normalized_type,
                "createdAt": now,
            },
        },

        upsert=True,

    )

    logger.info(
        "CHAT ARTIFACT SAVED | user=%s | conversation=%s | type=%s",

        user_id,

        conversation_id,

        normalized_type,

    )


def _value_to_text(value):
    """Convert structured AI output into text the PRD Viewer can render."""
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        lines = []
        for item in value:
            if isinstance(item, dict):
                lines.append(
                    " | ".join(
                        f"{key}: {_value_to_text(val)}"
                        for key, val in item.items()
                        if val is not None
                    )
                )
            else:
                lines.append(str(item))
        return "\n".join(f"- {line}" for line in lines if line)
    if isinstance(value, dict):
        return "\n".join(
            f"{key.replace('_', ' ').title()}: {_value_to_text(val)}"
            for key, val in value.items()
            if val is not None
        )
    return str(value)


def _build_prd_viewer_content(artifact):
    """Normalize an AI PRD artifact into the section map used by PRDViewer."""
    source = artifact.get("content") if isinstance(artifact.get("content"), dict) else artifact
    aliases = {
        "overview": ("overview", "executive_summary", "summary", "product_overview"),
        "problem": ("problem", "problem_statement", "user_problem", "背景"),
        "objectives": ("objectives", "goals", "business_goals", "success_metrics"),
        "users": ("users", "target_users", "user_personas", "target_audience"),
        "requirements": ("requirements", "functional_requirements", "features", "scope"),
        "user_stories": ("user_stories", "stories", "use_cases"),
        "non_functional_requirements": ("non_functional_requirements", "nfrs", "quality_attributes"),
        "metrics": ("metrics", "kpis", "success_criteria", "acceptance_criteria"),
        "risks": ("risks", "assumptions", "dependencies", "constraints"),
        "timeline": ("timeline", "milestones", "rollout_plan", "implementation_plan"),
    }

    normalized = {}
    consumed = set()
    for target, candidates in aliases.items():
        for candidate in candidates:
            if candidate in source and source[candidate] is not None:
                normalized[target] = _value_to_text(source[candidate])
                consumed.add(candidate)
                break

    # Preserve all additional AI-generated sections instead of discarding them.
    for key, value in source.items():
        if key not in consumed and key not in ("title", "prd_id", "id", "content") and value is not None:
            normalized.setdefault(key, _value_to_text(value))

    return normalized


def _save_prd_for_viewer(db, user_id, conversation_id, artifact):
    """Create/update the user-visible PRD record consumed by /api/prds."""
    if not isinstance(artifact, dict) or not artifact:
        return None

    title = (
        artifact.get("title")
        or artifact.get("name")
        or artifact.get("product_name")
        or "AI-Generated Product Requirements Document"
    )
    if not isinstance(title, str):
        title = str(title)

    now = now_iso()
    content = _build_prd_viewer_content(artifact)
    feature_id = artifact.get("featureId") or artifact.get("feature_id") or ""

    # One chatbot-generated PRD per conversation is updated in place.
    existing = db["prds"].find_one({
        "userId": user_id,
        "chatConversationId": conversation_id,
    })

    if existing:
        db["prds"].update_one(
            {"_id": existing["_id"], "userId": user_id},
            {"$set": {
                "title": title,
                "content": content,
                "featureId": feature_id,
                "updatedAt": now,
                "source": "chatbot",
            }},
        )
        prd_id = existing.get("id")
    else:
        prd_id = generate_id("prd-")
        db["prds"].insert_one({
            "id": prd_id,
            "userId": user_id,
            "title": title,
            "featureId": feature_id,
            "version": "1.0",
            "status": "Draft",
            "createdAt": now,
            "updatedAt": now,
            "content": content,
            "chatConversationId": conversation_id,
            "source": "chatbot",
        })

    logger.info(
        "CHAT PRD PUBLISHED | user=%s | conversation=%s | prd_id=%s",
        user_id, conversation_id, prd_id,
    )
    return prd_id


@router.post("")

def chat_with_ai(

    request: Request,

    body: dict | None = Body(default=None),

):
    """Retrieve database context, restore artifacts, and call the AI service."""

    user_id = request.session.get("user_id")

    if not user_id:

        return _error_response("Not authenticated.", 401)

    body = body or {}

    message = body.get("message")

    if not isinstance(message, str) or not message.strip():

        return _error_response("A chat message is required.")

    try:

        db = get_db()

        # Every conversation receives a stable ID.

        conversation_id = _get_conversation_id(body)

        # Retrieve fresh, authenticated-user-scoped application data.

        database_context = _build_database_context(user_id)

        # Retrieve persistent artifacts from MongoDB.

        saved_artifacts = _load_conversation_artifacts(

            db,

            user_id,

            conversation_id,

        )

        # Preserve additional artifact fields supplied by the frontend,

        # but MongoDB remains authoritative for saved generated artifacts.

        frontend_artifacts = body.get("generated_artifacts") or {}

        if not isinstance(frontend_artifacts, dict):

            frontend_artifacts = {}

        generated_artifacts = {

            **frontend_artifacts,

            **saved_artifacts,
        }

        ai_payload = dict(body)

        # Backend-owned context must never be overridden by the frontend.

        ai_payload["conversation_id"] = conversation_id

        ai_payload["database_context"] = database_context

        ai_payload["generated_artifacts"] = generated_artifacts

        # Do not expose internal authenticated user IDs to the AI service.

        ai_payload.pop("user_id", None)

        ai_payload.pop("userId", None)

        logger.info(
            "CHAT REQUEST | conversation=%s | artifacts=%s | inventory=%s",

            conversation_id,

            {

                key: value is not None

                for key, value in generated_artifacts.items()

                if key in (
                    "prd",
                    "user_stories",
                    "feature_prioritization",

                )
            },

            database_context["data_inventory"],

        )

        response = httpx.post(

            f"{AI_SERVICE_URL.rstrip('/')}/chat",

            json=ai_payload,

            timeout=AI_SERVICE_TIMEOUT_SECONDS,

        )

        response.raise_for_status()

        ai_response = response.json()

        if not isinstance(ai_response, dict):

            logger.error("AI service returned an invalid response format.")

            return _error_response(
                "The AI assistant returned an invalid response.",

                502,

            )

        # Persist any newly generated artifact.

        artifact_type = ai_response.get("artifact_type")

        artifact = ai_response.get("artifact")

        response_conversation_id = (

            ai_response.get("conversation_id")

            or conversation_id

        )

        if (

            ai_response.get("success", True)

            and isinstance(artifact_type, str)

            and isinstance(artifact, dict)

        ):

            _save_generated_artifact(

                db=db,

                user_id=user_id,

                conversation_id=response_conversation_id,

                artifact_type=artifact_type,

                artifact=artifact,

            )

            normalized_artifact_type = SUPPORTED_ARTIFACT_TYPES.get(
                artifact_type.strip().lower()
            )
            if normalized_artifact_type == "prd":
                prd_id = _save_prd_for_viewer(
                    db=db,
                    user_id=user_id,
                    conversation_id=response_conversation_id,
                    artifact=artifact,
                )
                if prd_id:
                    ai_response["saved_prd_id"] = prd_id

        # Always return the stable conversation ID to the frontend.

        ai_response["conversation_id"] = response_conversation_id

        return ok(ai_response)

    except ValueError as exc:

        return _error_response(str(exc), 400)

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

        documents = [

            {**message, "userId": user_id}

            for message in messages

        ]

        db["chat_messages"].insert_many(documents)

    return ok(messages)

@router.delete("")

def clear(request: Request):
    """Clear the authenticated user's conversation history and artifacts."""

    user_id = request.session.get("user_id")

    if not user_id:

        return _error_response("Not authenticated.", 401)

    db = get_db()

    db["chat_messages"].delete_many({"userId": user_id})

    # Clear persisted artifacts belonging to this user as well.

    db[ARTIFACT_COLLECTION].delete_many({"userId": user_id})

    return ok([], "Conversation cleared")
