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

def _parse_prd_document_text(document):

    """Extract a title and named PRD sections from generated document text."""

    import re

    if not isinstance(document, str) or not document.strip():

        return {}

    aliases = {

        "overview": ["Executive Summary", "Product Overview", "Overview"],

        "problem": ["Problem Statement", "User Problem"],

        "solution": ["Proposed Solution", "Solution"],

        "objectives": ["Goals and Objectives", "Objectives", "Goals"],

        "users": ["Target Users", "User Personas", "Target Audience"],

        "user_stories": ["User Stories", "Use Cases"],

        "requirements": ["Functional Requirements", "Requirements", "Features", "Scope"],

        "non_functional_requirements": ["Non-Functional Requirements", "NFRs"],

        "metrics": ["Success Metrics", "Acceptance Criteria", "KPIs"],

        "risks": ["Risks", "Assumptions", "Dependencies", "Constraints"],

        "timeline": ["Timeline", "Milestones", "Implementation Plan"],

        "technical_requirements": ["Technical Requirements", "Technical Architecture"],

    }

    heading_map = {

        heading.casefold(): target

        for target, headings in aliases.items()

        for heading in headings

    }

    heading_pattern = "|".join(

        re.escape(heading)

        for headings in aliases.values()

        for heading in sorted(headings, key=len, reverse=True)

    )

    # Accept Markdown headings, bold headings, and plain "Heading:" lines.

    pattern = re.compile(

        rf"(?im)^[ \t]\*(?:#+[ \t]\*)?(?:\\\*\\\*)?"

        rf"(?P<heading>{heading_pattern})"

        rf"(?:\\\*\\\*)?[ \t]\*:?[ \t]\*$"

    )

    matches = list(pattern.finditer(document))

    sections = {}

    for index, match in enumerate(matches):

        target = heading_map[match.group("heading").casefold()]

        start = match.end()

        end = matches[index + 1].start() if index + 1 < len(matches) else len(document)

        value = document[start:end].strip()

        if value:

            sections[target] = value

    # A leading Markdown H1 is a useful title if the artifact omitted one.

    title_match = re.search(r"(?m)^[ \t]\*#\s+(.+?)\s\*#\*\s\*$", document)

    if title_match:

        sections["_document_title"] = title_match.group(1).strip()

    return sections

def _is_meaningful_prd_title(value):

    """Reject generic labels that are not useful document titles."""

    if not isinstance(value, str):

        return False

    cleaned = value.strip()

    if not cleaned:

        return False

    generic = {

        "product",

        "prd",

        "product requirements document",

        "product requirement document",

        "untitled",

        "untitled prd",

        "none",

        "null",

    }

    return cleaned.casefold() not in generic

def _first_meaningful_text(*values):

    for value in values:

        if _is_meaningful_prd_title(value):

            return value.strip()

    return None

def _build_prd_viewer_content(artifact):

    """Normalize PRD result envelopes and preserve structured story data."""

    if not isinstance(artifact, dict):

        return {}

    source = artifact.get("content") if isinstance(artifact.get("content"), dict) else artifact

    source = dict(source)

    document = source.get("document")

    if isinstance(document, str):

        parsed = _parse_prd_document_text(document)

        source.pop("document", None)

        source = {**parsed, **source}

    elif isinstance(document, dict):

        source = {**document, **source}

    # Story output lives beside the wrapped PRD document in the chat artifact.

    if isinstance(artifact.get("user_stories"), list):

        source["user_stories"] = artifact["user_stories"]

    if artifact.get("story_generation_notes"):

        source["story_generation_notes"] = artifact["story_generation_notes"]

    aliases = {

        "overview": ("overview", "executive_summary", "summary", "product_overview"),

        "problem": ("problem", "problem_statement", "user_problem"),

        "objectives": ("objectives", "goals", "business_goals"),

        "users": ("users", "target_users", "user_personas", "target_audience"),

        "requirements": ("requirements", "functional_requirements", "features", "scope"),

        "user_stories": ("user_stories", "stories", "use_cases"),

        "non_functional_requirements": ("non_functional_requirements", "nfrs", "quality_attributes"),

        "metrics": ("metrics", "success_metrics", "kpis", "success_criteria"),

        "risks": ("risks", "assumptions", "dependencies", "constraints"),

        "timeline": ("timeline", "milestones", "rollout_plan", "implementation_plan"),

        "solution": ("solution", "proposed_solution"),

        "technical_requirements": ("technical_requirements", "technical_architecture"),

    }

    normalized = {}

    consumed = set()

    for target, candidates in aliases.items():

        for candidate in candidates:

            if candidate in source and source[candidate] is not None:

                normalized[target] = source[candidate]

                consumed.add(candidate)

                break

    excluded = {

        "title", "prd_title", "document_title", "name", "product_name",

        "prd_id", "id", "content", "document", "featureId", "feature_id",

    }

    for key, value in source.items():

        if key not in consumed and key not in excluded and value is not None:

            normalized.setdefault(key, value)

    return normalized

def _find_nested_text(data, keys):

    """Find a meaningful value under any matching key, recursively."""

    wanted = {str(key).casefold().replace(" ", "_").replace("-", "_") for key in keys}

    if isinstance(data, dict):

        for key, value in data.items():

            normalized_key = str(key).casefold().replace(" ", "_").replace("-", "_")

            if normalized_key in wanted and _is_meaningful_prd_title(value):

                return value.strip()

        for value in data.values():

            found = _find_nested_text(value, keys)

            if found:

                return found

    elif isinstance(data, list):

        for item in data:

            found = _find_nested_text(item, keys)

            if found:

                return found

    return None

def _find_feature_object_name(data):

    """Find feature.name when the AI schema nests the name under feature."""

    if isinstance(data, dict):

        for key, value in data.items():

            normalized_key = str(key).casefold().replace(" ", "_").replace("-", "_")

            if normalized_key == "feature" and isinstance(value, dict):

                candidate = _first_meaningful_text(

                    value.get("feature_name"),

                    value.get("featureName"),

                    value.get("name"),

                    value.get("title"),

                )

                if candidate:

                    return candidate

        for value in data.values():

            found = _find_feature_object_name(value)

            if found:

                return found

    elif isinstance(data, list):

        for item in data:

            found = _find_feature_object_name(item)

            if found:

                return found

    return None

def _extract_prd_title(artifact):

    """Choose the feature-specific title instead of generic product metadata."""

    if not isinstance(artifact, dict):

        return "Untitled PRD"

    source = artifact.get("content")

    if not isinstance(source, dict):

        source = artifact

    document = source.get("document")

    parsed_document = (

        _parse_prd_document_text(document)

        if isinstance(document, str)

        else document if isinstance(document, dict) else {}

    )

    # Feature name has priority over product_name/title because the latter

    # may be the generic label "Product" in the AI response.

    feature_title = (

        _find_nested_text(artifact, ("feature_name", "featureName", "Feature name"))

        or _find_nested_text(parsed_document, ("feature_name", "featureName", "Feature name"))

        or _find_feature_object_name(artifact)

        or _find_feature_object_name(parsed_document)

    )

    if feature_title:

        return feature_title

    # A Markdown H1 in the actual PRD document is a better fallback than

    # generic outer metadata.

    document_title = (

        parsed_document.get("_document_title")

        if isinstance(parsed_document, dict)

        else None

    )

    if _is_meaningful_prd_title(document_title):

        return document_title.strip()

    explicit_title = _first_meaningful_text(

        source.get("prd_title"),

        source.get("document_title"),

        source.get("title"),

        artifact.get("prd_title"),

        artifact.get("document_title"),

        artifact.get("title"),

        artifact.get("name"),

    )

    if explicit_title:

        return explicit_title

    return "Untitled PRD"

def _save_prd_for_viewer(db, user_id, conversation_id, artifact):

    """Create/update the user-visible PRD record consumed by /api/prds."""

    if not isinstance(artifact, dict) or not artifact:

        return None

    title = _extract_prd_title(artifact)

    content = _build_prd_viewer_content(artifact)

    feature = artifact.get("feature")

    if not isinstance(feature, dict):

        feature = artifact.get("content", {}).get("feature", {}) if isinstance(

            artifact.get("content"), dict

        ) else {}

    feature_id = (

        artifact.get("featureId")

        or artifact.get("feature_id")

        or (feature.get("id") if isinstance(feature, dict) else None)

        or ""

    )

    now = now_iso()

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

        "CHAT PRD PUBLISHED | user=%s | conversation=%s | prd_id=%s | title=%s",

        user_id, conversation_id, prd_id, title,

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

            # Keep a dedicated story artifact as well as the merged PRD.

            if (

                artifact_type.strip().lower() in ("prd", "product_requirements_document", "prd_generation", "prd_generation_agent")

                and isinstance(artifact.get("user_stories"), list)

                and artifact.get("user_stories")

            ):

                _save_generated_artifact(

                    db=db,

                    user_id=user_id,

                    conversation_id=response_conversation_id,

                    artifact_type="user_stories",

                    artifact={

                        "product_name": artifact.get("product_name"),

                        "prd_title": _extract_prd_title(artifact),

                        "user_stories": artifact.get("user_stories", []),

                        "generation_notes": artifact.get("story_generation_notes", []),

                        "total_user_stories": artifact.get("total_user_stories", len(artifact.get("user_stories", []))),

                        "total_acceptance_criteria": artifact.get("total_acceptance_criteria", 0),

                    },

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


def _conversation_title(messages: list[dict], fallback: str = "New chat") -> str:
    first_user = next(
        (
            m for m in messages
            if (
                (m.get("role") == "user" and (m.get("text") or m.get("content")))
                or m.get("user_message")
            )
        ),
        None,
    )
    if not first_user:
        return fallback
    raw_title = first_user.get("text") or first_user.get("content") or first_user.get("user_message") or ""
    value = " ".join(str(raw_title).split())
    return value[:72] + ("…" if len(value) > 72 else "")


def _conversation_summary(document: dict) -> dict:
    return {
        "conversationId": document.get("conversationId"),
        "title": document.get("title") or "New chat",
        "createdAt": document.get("createdAt"),
        "updatedAt": document.get("updatedAt"),
        "messageCount": int(document.get("messageCount") or 0),
        "preview": document.get("preview") or "",
    }


def _legacy_message_time(message: dict):
    """Best-effort timestamp for grouping pre-conversation-index chat records."""
    for key in ("at", "createdAt", "created_at", "timestamp", "generated_at"):
        value = message.get(key)
        if isinstance(value, datetime):
            return value.replace(tzinfo=value.tzinfo or timezone.utc)
        if isinstance(value, (int, float)):
            try:
                return datetime.fromtimestamp(value, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                pass
        if isinstance(value, str) and value.strip():
            try:
                parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
                return parsed.replace(tzinfo=parsed.tzinfo or timezone.utc)
            except ValueError:
                pass
    object_id = message.get("_id")
    generated = getattr(object_id, "generation_time", None)
    if generated:
        return generated
    return None


def _migrate_legacy_chat_messages(db, user_id: str):
    """Assign stable conversation IDs to old messages, splitting by inactivity.

    Old records did not carry a conversation ID. A 60-minute inactivity gap is
    used as a conservative session boundary. Original message documents are
    updated in place; message text and artifacts are not rewritten.
    """
    collection = db["chat_messages"]
    # First normalize records that already have the old snake_case field.
    collection.update_many(
        {
            "userId": user_id,
            "conversationId": {"$in": [None, ""]},
            "conversation_id": {"$exists": True, "$nin": [None, ""]},
        },
        [{"$set": {"conversationId": "$conversation_id"}}],
    )
    legacy = list(collection.find({
        "userId": user_id,
        "$or": [
            {"conversationId": {"$exists": False}},
            {"conversationId": None},
            {"conversationId": ""},
        ],
    }).sort("_id", 1))
    if not legacy:
        return

    groups = []
    current = []
    previous_time = None
    gap_seconds = 60 * 60
    for message in legacy:
        message_time = _legacy_message_time(message)
        if current and message_time and previous_time:
            if (message_time - previous_time).total_seconds() > gap_seconds:
                groups.append(current)
                current = []
        current.append(message)
        if message_time:
            previous_time = message_time

    if current:
        groups.append(current)

    for group in groups:
        first_id = str(group[0].get("_id", uuid4().hex))
        conversation_id = f"legacy-{first_id}"
        for message in group:
            message_time = _legacy_message_time(message)
            collection.update_one(
                {"_id": message["_id"], "userId": user_id},
                {"$set": {
                    "conversationId": conversation_id,
                    "createdAt": message.get("createdAt") or (message_time.isoformat() if message_time else now_iso()),
                }},
            )
        created_at = _legacy_message_time(group[0])
        updated_at = _legacy_message_time(group[-1]) or created_at
        created_value = created_at.isoformat() if created_at else now_iso()
        updated_value = updated_at.isoformat() if updated_at else created_value
        db["chat_conversations"].update_one(
            {"userId": user_id, "conversationId": conversation_id},
            {"$set": {
                "title": _conversation_title(group),
                "createdAt": created_value,
                "updatedAt": updated_value,
                "messageCount": len(group),
                "preview": str(group[-1].get("text") or group[-1].get("content") or group[-1].get("assistant_message") or "")[:160],
            }, "$setOnInsert": {"userId": user_id, "conversationId": conversation_id}},
            upsert=True,
        )


@router.get("/conversations")
def list_conversations(request: Request):
    """List conversations belonging to the authenticated user."""
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response("Not authenticated.", 401)

    db = get_db()
    # Migrate old messages before building the list so each can be loaded and deleted.
    _migrate_legacy_chat_messages(db, user_id)
    # Reconcile summaries from message records. This recovers chats saved by
    # older frontend versions that wrote messages but never created an index row.
    all_messages = mongo_docs_to_list(
        db["chat_messages"].find({"userId": user_id}).sort("_id", 1)
    )
    grouped = {}
    for message in all_messages:
        conversation_id = message.get("conversationId") or message.get("conversation_id")
        if conversation_id:
            grouped.setdefault(str(conversation_id), []).append(message)

    for conversation_id, group in grouped.items():
        first_time = _legacy_message_time(group[0])
        last_time = _legacy_message_time(group[-1]) or first_time
        created_at = first_time.isoformat() if first_time else now_iso()
        updated_at = last_time.isoformat() if last_time else created_at
        db["chat_conversations"].update_one(
            {"userId": user_id, "conversationId": conversation_id},
            {"$set": {
                "title": _conversation_title(group),
                "createdAt": created_at,
                "updatedAt": updated_at,
                "messageCount": len(group),
                "preview": str(group[-1].get("text") or group[-1].get("content") or group[-1].get("assistant_message") or "")[:160],
            }, "$setOnInsert": {"userId": user_id, "conversationId": conversation_id}},
            upsert=True,
        )

    documents = mongo_docs_to_list(
        db["chat_conversations"].find({"userId": user_id}).sort("updatedAt", -1).limit(200)
    )
    return ok([_conversation_summary(item) for item in documents])


@router.get("/conversations/{conversation_id}")
def get_conversation(request: Request, conversation_id: str):
    """Load one conversation and its messages."""
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response("Not authenticated.", 401)

    db = get_db()
    conversation = db["chat_conversations"].find_one(
        {"userId": user_id, "conversationId": conversation_id},
        {"_id": 0},
    )
    messages = mongo_docs_to_list(
        db["chat_messages"]
        .find({"userId": user_id, "conversationId": conversation_id})
        .sort("createdAt", 1)
    )
    if not messages:
        messages = mongo_docs_to_list(
            db["chat_messages"]
            .find({"userId": user_id, "conversationId": conversation_id})
            .sort("_id", 1)
        )
    if not conversation and not messages:
        return _error_response("Conversation not found.", 404)
    return ok({
        "conversation": conversation or {
            "conversationId": conversation_id,
            "title": _conversation_title(messages),
        },
        "messages": messages,
    })


@router.put("/conversations/{conversation_id}")
def save_conversation(
    request: Request,
    conversation_id: str,
    body: dict | None = Body(default=None),
):
    """Save one conversation without deleting any other conversation."""
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response("Not authenticated.", 401)
    if not conversation_id or len(conversation_id) > 200:
        return _error_response("Invalid conversation ID.")

    body = body or {}
    messages = body.get("messages", [])
    if not isinstance(messages, list) or not all(isinstance(m, dict) for m in messages):
        return _error_response("messages must be an array of message objects.")

    now = now_iso()
    title = str(body.get("title") or _conversation_title(messages)).strip()[:100] or "New chat"
    normalized = []
    for index, message in enumerate(messages):
        item = dict(message)
        item.pop("_id", None)
        message_id = str(item.get("id") or item.get("messageId") or f"message-{index}")
        item.update({
            "id": message_id,
            "messageId": message_id,
            "userId": user_id,
            "conversationId": conversation_id,
            "createdAt": item.get("at") or item.get("createdAt") or now,
        })
        normalized.append(item)

    db = get_db()
    db["chat_conversations"].update_one(
        {"userId": user_id, "conversationId": conversation_id},
        {
            "$set": {
                "title": title,
                "updatedAt": now,
                "messageCount": len(normalized),
                "preview": str(normalized[-1].get("text") or normalized[-1].get("content") or "")[:160] if normalized else "",
            },
            "$setOnInsert": {
                "userId": user_id,
                "conversationId": conversation_id,
                "createdAt": now,
            },
        },
        upsert=True,
    )

    # Replace only the messages belonging to this one conversation.
    db["chat_messages"].delete_many({"userId": user_id, "conversationId": conversation_id})
    if normalized:
        db["chat_messages"].insert_many(normalized)

    return ok({
        "conversationId": conversation_id,
        "title": title,
        "messageCount": len(normalized),
        "updatedAt": now,
    })


@router.delete("/conversations/{conversation_id}")
def delete_conversation(request: Request, conversation_id: str):
    """Delete one conversation and its chat artifacts only."""
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response("Not authenticated.", 401)
    db = get_db()
    db["chat_messages"].delete_many({
        "userId": user_id,
        "$or": [
            {"conversationId": conversation_id},
            {"conversation_id": conversation_id},
        ],
    })
    db["chat_conversations"].delete_one({"userId": user_id, "conversationId": conversation_id})
    db[ARTIFACT_COLLECTION].delete_many({"userId": user_id, "conversationId": conversation_id})
    return ok({"conversationId": conversation_id}, "Conversation deleted")


# Backward-compatible endpoints for older frontend builds.
@router.get("")
def get_history(request: Request):
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response("Not authenticated.", 401)
    messages = mongo_docs_to_list(
        get_db()["chat_messages"].find({"userId": user_id}).sort("_id", 1)
    )
    return ok(messages)


@router.put("")
def save_history(request: Request, body: dict | None = Body(default=None)):
    """Legacy save endpoint. It no longer deletes all user messages."""
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response("Not authenticated.", 401)
    body = body or {}
    messages = body.get("messages", [])
    if not isinstance(messages, list) or not all(isinstance(m, dict) for m in messages):
        return _error_response("messages must be an array of message objects.")

    db = get_db()
    grouped = {}
    for message in messages:
        conversation_id = message.get("conversationId") or message.get("conversation_id") or "legacy-conversation"
        grouped.setdefault(conversation_id, []).append(message)

    for conversation_id, group in grouped.items():
        now = now_iso()
        db["chat_conversations"].update_one(
            {"userId": user_id, "conversationId": conversation_id},
            {"$set": {
                "title": _conversation_title(group),
                "updatedAt": now,
                "messageCount": len(group),
                "preview": str(group[-1].get("text") or "")[:160],
            }, "$setOnInsert": {
                "userId": user_id,
                "conversationId": conversation_id,
                "createdAt": now,
            }},
            upsert=True,
        )
        for index, message in enumerate(group):
            item = dict(message)
            item.pop("_id", None)
            message_id = str(item.get("id") or f"message-{index}")
            item.update({
                "id": message_id,
                "messageId": message_id,
                "userId": user_id,
                "conversationId": conversation_id,
                "createdAt": item.get("at") or now,
            })
            db["chat_messages"].update_one(
                {"userId": user_id, "conversationId": conversation_id, "messageId": message_id},
                {"$set": item},
                upsert=True,
            )
    return ok(messages)


@router.delete("")
def clear(request: Request):
    """Explicit clear-all endpoint retained for backwards compatibility."""
    user_id = request.session.get("user_id")
    if not user_id:
        return _error_response("Not authenticated.", 401)
    db = get_db()
    db["chat_messages"].delete_many({"userId": user_id})
    db["chat_conversations"].delete_many({"userId": user_id})
    db[ARTIFACT_COLLECTION].delete_many({"userId": user_id})
    return ok([], "All conversations cleared")
