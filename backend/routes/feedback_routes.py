"""Feedback CRUD routes using FastAPI."""
import os
import httpx

from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse

from db import get_db
from helpers import (
    ok,
    fail,
    generate_id,
    now_iso,
    mongo_doc_to_dict,
    mongo_docs_to_list,
    normalize_feedback,
)

router = APIRouter(
    prefix="/api/feedback",
    tags=["Feedback"],
)

@router.post("/{feedback_id}/analyze")
def analyze_feedback(feedback_id: str, request: Request):
    """Analyze saved feedback using the separate AI service."""

    # 1. Verify authentication.
    uid = request.session.get("user_id")

    if not uid:
        return _error_response("Not authenticated.", status=401)

    # 2. Find feedback belonging to the logged-in user.
    feedback = get_db()["feedback"].find_one({
        "id": feedback_id,
        "userId": uid,
    })

    if not feedback:
        return _error_response("Feedback not found.", status=404)

    # 3. Get the actual feedback message.
    feedback_text = str(feedback.get("message", "")).strip()

    if not feedback_text:
        return _error_response(
            "Feedback message is empty.",
            status=400,
        )

    # 4. Read the AI service URL from the environment.
    ai_service_url = os.getenv(
        "AI_SERVICE_URL",
        "http://127.0.0.1:8001",
    ).rstrip("/")

    # 5. Call the AI service.
    try:
        response = httpx.post(
            f"{ai_service_url}/feedback/analyze",
            json={"text": feedback_text},
            timeout=30.0,
        )

        response.raise_for_status()

        analysis = response.json()

    except httpx.TimeoutException:
        return _error_response(
            "AI analysis timed out. Please try again.",
            status=504,
        )

    except httpx.HTTPStatusError:
        return _error_response(
            "AI analysis service returned an error.",
            status=502,
        )

    except httpx.RequestError:
        return _error_response(
            "Could not connect to the AI analysis service.",
            status=503,
        )

    except ValueError:
        return _error_response(
            "AI analysis service returned an invalid response.",
            status=502,
        )

    # 6. Return the analysis using your existing response format.
    return ok(
        {
            "feedback_id": feedback_id,
            "analysis": analysis,
        },
        "Feedback analyzed successfully",
    )


def _user_id(request: Request):
    """Get the authenticated user's ID from the session."""
    return request.session.get("user_id")


def _error_response(message: str, status: int = 400, data=None):
    """Return an error in the existing frontend response format."""
    body, status_code = fail(message, data=data, status=status)
    return JSONResponse(content=body, status_code=status_code)


def _log_activity(user_id: str, text: str):
    """Record a feedback-related activity."""
    get_db()["activity"].insert_one({
        "id": generate_id("act-"),
        "userId": user_id,
        "text": text,
        "at": now_iso(),
    })


@router.get("")
def get_all(request: Request):
    """Get all feedback belonging to the authenticated user."""

    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", status=401)

    items = mongo_docs_to_list(
        get_db()["feedback"]
        .find({"userId": uid})
        .sort("createdAt", -1)
    )

    return ok(items)


@router.post("")
def create(
    request: Request,
    body: dict = Body(default={}),
):
    """Create a feedback record."""

    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", status=401)

    record, error = normalize_feedback(body)

    if error:
        return _error_response(error)

    record["id"] = generate_id("fb-")
    record["userId"] = uid

    db = get_db()
    db["feedback"].insert_one(record)

    _log_activity(
        uid,
        f'Feedback "{record["title"]}" added',
    )

    return ok(
        mongo_doc_to_dict(record),
        "Feedback created",
    )


@router.put("/{feedback_id}")
def update(
    feedback_id: str,
    request: Request,
    body: dict = Body(default={}),
):
    """Update an existing feedback record."""

    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", status=401)

    db = get_db()

    existing = db["feedback"].find_one({
        "id": feedback_id,
        "userId": uid,
    })

    if not existing:
        return _error_response(
            "Feedback not found.",
            status=404,
        )

    record, error = normalize_feedback(body, existing)

    if error:
        return _error_response(error)

    record["id"] = feedback_id
    record["userId"] = uid

    db["feedback"].update_one(
        {
            "id": feedback_id,
            "userId": uid,
        },
        {"$set": record},
    )

    updated = db["feedback"].find_one({
        "id": feedback_id,
        "userId": uid,
    })

    _log_activity(
        uid,
        f'Feedback "{record["title"]}" updated',
    )

    return ok(
        mongo_doc_to_dict(updated),
        "Feedback updated",
    )


@router.delete("/{feedback_id}")
def remove(
    feedback_id: str,
    request: Request,
):
    """Delete an existing feedback record."""

    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", status=401)

    db = get_db()

    target = db["feedback"].find_one({
        "id": feedback_id,
        "userId": uid,
    })

    if not target:
        return _error_response(
            "Feedback not found.",
            status=404,
        )

    db["feedback"].delete_one({
        "id": feedback_id,
        "userId": uid,
    })

    _log_activity(
        uid,
        f'Feedback "{target["title"]}" deleted',
    )

    return ok(
        {"id": feedback_id},
        "Feedback deleted",
    )


@router.post("/import")
def import_many(
    request: Request,
    body: dict = Body(default={}),
):
    """Import multiple feedback records."""

    uid = _user_id(request)

    if not uid:
        return _error_response("Not authenticated.", status=401)

    records = body.get("records", [])

    if not isinstance(records, list):
        return _error_response("records must be an array.")

    db = get_db()

    existing_ids = {
        doc["id"]
        for doc in db["feedback"].find(
            {"userId": uid},
            {"id": 1},
        )
    }

    added = 0
    skipped = 0

    for raw in records:
        if not isinstance(raw, dict):
            skipped += 1
            continue

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

    _log_activity(
        uid,
        f"Imported {added} feedback record(s)",
    )

    return ok(
        {"added": added, "skipped": skipped},
        f"Imported {added} record(s)",
    )

@router.post("/pain-points/identify")
def identify_pain_points(
    request: Request,
    body: dict = Body(default={}),
):
    """Identify customer pain points using Agent 2."""

    # 1. Verify authentication.
    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    # 2. Get optional feedback IDs.
    feedback_ids = body.get("feedback_ids")

    if feedback_ids is not None:
        if (
            not isinstance(feedback_ids, list)
            or not feedback_ids
            or len(feedback_ids) > 500
            or not all(
                isinstance(item, str) and item.strip()
                for item in feedback_ids
            )
        ):
            return _error_response(
                "feedback_ids must be a non-empty array "
                "containing at most 500 valid IDs.",
                status=400,
            )

        feedback_ids = [
            item.strip() for item in feedback_ids
        ]

        if len(feedback_ids) != len(set(feedback_ids)):
            return _error_response(
                "Feedback IDs must be unique.",
                status=400,
            )

    # 3. Fetch feedback belonging to the logged-in user.
    db = get_db()

    query = {"userId": uid}

    if feedback_ids is not None:
        query["id"] = {"$in": feedback_ids}

    feedback_documents = list(
        db["feedback"]
        .find(query)
        .sort("createdAt", -1)
        .limit(501)
    )

    if feedback_ids is not None:
        if len(feedback_documents) != len(feedback_ids):
            return _error_response(
                "Some feedback records were not found.",
                status=404,
            )

    if not feedback_documents:
        return _error_response(
            "No feedback records found.",
            status=404,
        )

    if len(feedback_documents) > 500:
        return _error_response(
            "Maximum 500 feedback records can be analyzed at once.",
            status=400,
        )

    # 4. Prepare feedback for Agent 2.
    feedback_records = [
        {
            "id": str(item["id"]),
            "title": str(item.get("title", "")),
            "message": str(item.get("message", "")),
        }
        for item in feedback_documents
    ]

    # 5. Read AI service URL.
    ai_service_url = os.getenv(
        "AI_SERVICE_URL",
        "http://127.0.0.1:8001",
    ).rstrip("/")

    # 6. Send feedback to Agent 2.
    try:
        response = httpx.post(
            f"{ai_service_url}/pain-points/identify",
            json={
                "feedback": feedback_records,
            },
            timeout=120.0,
        )

        response.raise_for_status()

        result = response.json()

    except httpx.TimeoutException:
        return _error_response(
            "Pain-point identification timed out. Please try again.",
            status=504,
        )

    except httpx.HTTPStatusError:
        return _error_response(
            "AI pain-point identification service returned an error.",
            status=502,
        )

    except httpx.RequestError:
        return _error_response(
            "Could not connect to the AI service.",
            status=503,
        )

    except ValueError:
        return _error_response(
            "AI service returned an invalid response.",
            status=502,
        )

    # 7. Return results to the frontend.
    return ok(
        {
            "total_feedback_analyzed": len(feedback_records),
            "pain_points": result.get("pain_points", []),
        },
        "Customer pain points identified successfully.",
    )