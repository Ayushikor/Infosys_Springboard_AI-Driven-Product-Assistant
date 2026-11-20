
"""Feedback CRUD and AI analysis routes using FastAPI."""

import os
import httpx

from datetime import datetime

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


# ---------------------------------------------------------
# COMMON HELPERS
# ---------------------------------------------------------


def _user_id(request: Request):
    """Get the authenticated user's ID from the session."""
    return request.session.get("user_id")


def _error_response(
    message: str,
    status: int = 400,
    data=None,
):
    """Return an error using the existing frontend response format."""

    body, status_code = fail(
        message,
        data=data,
        status=status,
    )

    return JSONResponse(
        content=body,
        status_code=status_code,
    )


def _log_activity(user_id: str, text: str):
    """Record a user activity."""

    get_db()["activity"].insert_one({
        "id": generate_id("act-"),
        "userId": user_id,
        "text": text,
        "at": now_iso(),
    })


def _get_ai_service_url():
    """Return the configured AI service URL."""

    return os.getenv(
        "AI_SERVICE_URL",
        "http://127.0.0.1:8001",
    ).rstrip("/")


def _validate_feedback_ids(feedback_ids):
    """Validate optional feedback IDs for AI operations."""

    if feedback_ids is None:
        return None, None

    if (
        not isinstance(feedback_ids, list)
        or not feedback_ids
        or len(feedback_ids) > 500
        or not all(
            isinstance(item, str) and item.strip()
            for item in feedback_ids
        )
    ):
        return None, (
            "feedback_ids must be a non-empty array "
            "containing at most 500 valid IDs."
        )

    cleaned_ids = [
        item.strip()
        for item in feedback_ids
    ]

    if len(cleaned_ids) != len(set(cleaned_ids)):
        return None, "Feedback IDs must be unique."

    return cleaned_ids, None


def _load_user_feedback(
    uid: str,
    feedback_ids=None,
    minimum_records: int = 1,
):
    """Load feedback belonging to a user, optionally by IDs."""

    db = get_db()

    query = {
        "userId": uid,
    }

    if feedback_ids is not None:
        query["id"] = {
            "$in": feedback_ids,
        }

    documents = list(
        db["feedback"]
        .find(query)
        .sort("createdAt", -1)
        .limit(501)
    )

    if (
        feedback_ids is not None
        and len(documents) != len(feedback_ids)
    ):
        return None, (
            "Some feedback records were not found."
        ), 404

    if not documents:
        return None, "No feedback records found.", 404

    if len(documents) > 500:
        return None, (
            "Maximum 500 feedback records can be analyzed at once."
        ), 400

    if len(documents) < minimum_records:
        return None, (
            f"At least {minimum_records} feedback records are required."
        ), 400

    return documents, None, None


# ---------------------------------------------------------
# INDIVIDUAL FEEDBACK ANALYSIS
# ---------------------------------------------------------


@router.post("/{feedback_id}/analyze")
def analyze_feedback(
    feedback_id: str,
    request: Request,
):
    """Analyze saved feedback using the separate AI service."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    feedback = get_db()["feedback"].find_one({
        "id": feedback_id,
        "userId": uid,
    })

    if not feedback:
        return _error_response(
            "Feedback not found.",
            status=404,
        )

    feedback_text = str(
        feedback.get("message", "")
    ).strip()

    if not feedback_text:
        return _error_response(
            "Feedback message is empty.",
            status=400,
        )

    try:
        response = httpx.post(
            f"{_get_ai_service_url()}/feedback/analyze",
            json={
                "text": feedback_text,
            },
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

    return ok(
        {
            "feedback_id": feedback_id,
            "analysis": analysis,
        },
        "Feedback analyzed successfully",
    )


# ---------------------------------------------------------
# GET ALL FEEDBACK
# ---------------------------------------------------------


@router.get("")
def get_all(request: Request):
    """Get all feedback belonging to the authenticated user."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    items = mongo_docs_to_list(
        get_db()["feedback"]
        .find({
            "userId": uid,
        })
        .sort("createdAt", -1)
    )

    return ok(items)


# ---------------------------------------------------------
# GET UPLOADED DATASETS
# NEW ENDPOINT FOR DASHBOARD DATASET SELECTOR
# ---------------------------------------------------------


@router.get("/datasets")
def get_uploaded_datasets(request: Request):
    """
    Return uploaded datasets belonging to the authenticated user.

    Records are grouped by import_id, so one upload appears
    as one dataset regardless of its record count.
    """

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    pipeline = [
        {
            "$match": {
                "userId": uid,
                "import_id": {
                    "$exists": True,
                    "$ne": None,
                },
            }
        },
        {
            "$group": {
                "_id": "$import_id",
                "fileName": {
                    "$first": "$import_filename",
                },
                "recordCount": {
                    "$sum": 1,
                },
                "importedAt": {
                    "$max": "$importedAt",
                },
            }
        },
        {
            "$project": {
                "_id": 0,
                "import_id": "$_id",
                "fileName": 1,
                "recordCount": 1,
                "importedAt": 1,
            }
        },
        {
            "$sort": {
                "importedAt": -1,
            }
        },
    ]

    datasets = list(
        get_db()["feedback"].aggregate(pipeline)
    )

    return ok(
        datasets,
        "Uploaded datasets retrieved successfully.",
    )


# ---------------------------------------------------------
# CREATE FEEDBACK
# ---------------------------------------------------------


@router.post("")
def create(
    request: Request,
    body: dict = Body(default={}),
):
    """Create an individual feedback record."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

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


# ---------------------------------------------------------
# UPDATE FEEDBACK
# ---------------------------------------------------------


@router.put("/{feedback_id}")
def update(
    feedback_id: str,
    request: Request,
    body: dict = Body(default={}),
):
    """Update an existing feedback record."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

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

    record, error = normalize_feedback(
        body,
        existing,
    )

    if error:
        return _error_response(error)

    record["id"] = feedback_id
    record["userId"] = uid

    # Preserve the original import metadata when updating
    # an uploaded feedback record.
    for field in (
        "import_id",
        "import_filename",
        "importedAt",
    ):
        if field in existing:
            record[field] = existing[field]

    db["feedback"].update_one(
        {
            "id": feedback_id,
            "userId": uid,
        },
        {
            "$set": record,
        },
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


# ---------------------------------------------------------
# DELETE FEEDBACK
# ---------------------------------------------------------


@router.delete("/{feedback_id}")
def remove(
    feedback_id: str,
    request: Request,
):
    """Delete an existing feedback record."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

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
        {
            "id": feedback_id,
        },
        "Feedback deleted",
    )


# ---------------------------------------------------------
# IMPORT FEEDBACK / CSV / JSON
# UPDATED: GENERATE IMPORT ID
# ---------------------------------------------------------


@router.post("/import")
def import_many(
    request: Request,
    body: dict = Body(default={}),
):
    """
    Import multiple feedback records.

    One unique import_id is assigned to every successfully
    inserted record from the same upload.
    """

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    records = body.get("records", [])

    if not isinstance(records, list):
        return _error_response(
            "records must be an array."
        )

    if not records:
        return _error_response(
            "No records were supplied."
        )

    file_name = str(
        body.get("fileName") or "Uploaded dataset"
    ).strip()

    if not file_name:
        file_name = "Uploaded dataset"

    db = get_db()

    existing_ids = {
        doc["id"]
        for doc in db["feedback"].find(
            {
                "userId": uid,
            },
            {
                "id": 1,
            },
        )
        if doc.get("id")
    }

    # Generate one ID per import operation.
    import_id = generate_id("import-")
    imported_at = now_iso()

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

        if not isinstance(record_id, str):
            skipped += 1
            continue

        record_id = record_id.strip()

        if not record_id:
            record_id = generate_id("fb-")

        if record_id in existing_ids:
            skipped += 1
            continue

        record["id"] = record_id
        record["userId"] = uid

        # Attach upload metadata to every inserted record.
        record["import_id"] = import_id
        record["import_filename"] = file_name
        record["importedAt"] = imported_at

        db["feedback"].insert_one(record)

        existing_ids.add(record_id)
        added += 1

    _log_activity(
        uid,
        f"Imported {added} feedback record(s) from {file_name}",
    )

    result = {
        "added": added,
        "skipped": skipped,
        "import_id": import_id if added > 0 else None,
        "fileName": file_name,
        "importedAt": imported_at if added > 0 else None,
    }

    return ok(
        result,
        f"Imported {added} record(s)",
    )


# ---------------------------------------------------------
# AGENT 2: PAIN POINT IDENTIFICATION
# ---------------------------------------------------------


@router.post("/pain-points/identify")
def identify_pain_points(
    request: Request,
    body: dict = Body(default={}),
):
    """Identify customer pain points using Agent 2."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    feedback_ids, validation_error = _validate_feedback_ids(
        body.get("feedback_ids")
    )

    if validation_error:
        return _error_response(
            validation_error,
            status=400,
        )

    feedback_documents, error, status = _load_user_feedback(
        uid,
        feedback_ids,
        minimum_records=1,
    )

    if error:
        return _error_response(
            error,
            status=status,
        )

    feedback_records = [
        {
            "id": str(item["id"]),
            "title": str(item.get("title", "")),
            "message": str(item.get("message", "")),
        }
        for item in feedback_documents
    ]

    try:
        response = httpx.post(
            f"{_get_ai_service_url()}/pain-points/identify",
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

    return ok(
        {
            "total_feedback_analyzed": len(feedback_records),
            "pain_points": result.get("pain_points", []),
        },
        "Customer pain points identified successfully.",
    )


# ---------------------------------------------------------
# AGENT 3: FEATURE CLUSTERING
# ---------------------------------------------------------


@router.post("/features/cluster")
def cluster_features(
    request: Request,
    body: dict = Body(default={}),
):
    """Cluster similar customer feature requests using Agent 3."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    feedback_ids, validation_error = _validate_feedback_ids(
        body.get("feedback_ids")
    )

    if validation_error:
        return _error_response(
            validation_error,
            status=400,
        )

    feedback_documents, error, status = _load_user_feedback(
        uid,
        feedback_ids,
        minimum_records=1,
    )

    if error:
        return _error_response(
            error,
            status=status,
        )

    feedback_records = [
        {
            "feedback_id": str(item["id"]),
            "source_channel": str(
                item.get("source") or "Customer Feedback"
            ),
            "raw_text": str(
                item.get("message") or item.get("title") or ""
            ).strip(),
        }
        for item in feedback_documents
    ]

    feedback_records = [
        item
        for item in feedback_records
        if item["raw_text"]
    ]

    if not feedback_records:
        return _error_response(
            "No feedback contains usable text.",
            status=400,
        )

    try:
        response = httpx.post(
            f"{_get_ai_service_url()}/features/cluster",
            json={
                "feedback": feedback_records,
            },
            timeout=120.0,
        )

        response.raise_for_status()
        result = response.json()

    except httpx.TimeoutException:
        return _error_response(
            "Feature clustering timed out.",
            status=504,
        )

    except httpx.HTTPStatusError:
        return _error_response(
            "AI feature clustering service returned an error.",
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

    return ok(
        result,
        "Feature requests clustered successfully.",
    )


# ---------------------------------------------------------
# AGENT 4: TREND ANALYSIS
# ---------------------------------------------------------


@router.post("/trends/analyze")
def analyze_trends(
    request: Request,
    body: dict = Body(default={}),
):
    """Analyze feedback trends over time using Agent 4."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            status=401,
        )

    feedback_ids, validation_error = _validate_feedback_ids(
        body.get("feedback_ids")
    )

    if validation_error:
        return _error_response(
            validation_error,
            status=400,
        )

    feedback_documents, error, status = _load_user_feedback(
        uid,
        feedback_ids,
        minimum_records=2,
    )

    if error:
        return _error_response(
            error,
            status=status,
        )

    feedback_records = []

    for item in feedback_documents:

        timestamp = item.get("createdAt")

        if not timestamp:
            return _error_response(
                "Some feedback records are missing creation dates. "
                "Trend analysis requires timestamps.",
                status=400,
            )

        if isinstance(timestamp, datetime):
            timestamp = timestamp.isoformat()
        else:
            timestamp = str(timestamp).strip()

        try:
            datetime.fromisoformat(
                timestamp.replace("Z", "+00:00")
            )

        except ValueError:
            return _error_response(
                "A feedback record contains an invalid creation date.",
                status=400,
            )

        raw_text = str(
            item.get("message") or item.get("title") or ""
        ).strip()

        if not raw_text:
            continue

        feedback_records.append({
            "feedback_id": str(item["id"]),
            "source_channel": str(
                item.get("source") or "Customer Feedback"
            ),
            "raw_text": raw_text,
            "timestamp": timestamp,
        })

    if len(feedback_records) < 2:
        return _error_response(
            "At least 2 valid, timestamped feedback records are required.",
            status=400,
        )

    try:
        response = httpx.post(
            f"{_get_ai_service_url()}/trends/analyze",
            json={
                "feedback": feedback_records,
            },
            timeout=120.0,
        )

        response.raise_for_status()
        result = response.json()

    except httpx.TimeoutException:
        return _error_response(
            "Trend analysis timed out.",
            status=504,
        )

    except httpx.HTTPStatusError:
        return _error_response(
            "AI trend analysis service returned an error.",
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

    return ok(
        result,
        "Feedback trends analyzed successfully.",
    )
