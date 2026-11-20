"""Streaming analysis execution and MongoDB persistence service."""

import logging
from datetime import datetime, timezone
from math import ceil

import httpx
from pymongo import ASCENDING, DESCENDING
from pymongo.errors import PyMongoError

from config import Config
from db import get_db
from helpers import (
    generate_id,
    now_iso,
    mongo_doc_to_dict,
    mongo_docs_to_list,
)

logger = logging.getLogger(__name__)

MAX_FEEDBACK_RECORDS = 10_000
DEFAULT_ANALYSIS_BATCH_SIZE = 200

AGENT_KEYS = (
    "themes",
    "pain_points",
    "feature_clusters",
    "trends",
)


class AnalysisServiceError(RuntimeError):
    """Raised when analysis execution or persistence fails."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def _mark_failed(collection, run_id: str, message: str) -> None:
    """Mark a previously created analysis run as failed."""

    try:
        collection.update_one(
            {"run_id": run_id},
            {
                "$set": {
                    "status": "failed",
                    "success": False,
                    "errors": {"pipeline": message},
                    "completedAt": now_iso(),
                    "updatedAt": now_iso(),
                }
            },
        )
    except PyMongoError:
        logger.exception(
            "Could not update failed analysis run %s.",
            run_id,
        )


def _build_feedback_query(
    user_id: str,
    workspace_id: str | None = None,
) -> dict:
    """Build a user-scoped query, including legacy workspace-less records."""

    workspace_scope = [
        {"workspaceId": {"$exists": False}},
        {"workspaceId": None},
    ]

    if workspace_id:
        workspace_scope.insert(0, {"workspaceId": workspace_id})

    return {
        "userId": user_id,
        "$or": workspace_scope,
    }


def _validate_feedback_count(total: int) -> None:
    """Validate the total number of feedback records before processing."""

    if total < 2:
        raise AnalysisServiceError(
            "At least two feedback records are required "
            "for the four-agent analysis pipeline.",
            422,
        )

    if total > MAX_FEEDBACK_RECORDS:
        raise AnalysisServiceError(
            f"The analysis limit is {MAX_FEEDBACK_RECORDS:,} "
            "feedback records per run.",
            422,
        )


def _iter_document_batches(
    cursor,
    total_records: int,
    batch_size: int = DEFAULT_ANALYSIS_BATCH_SIZE,
):
    """
    Lazily yield balanced batches from a MongoDB cursor.

    The iterator never materializes the complete feedback collection.
    It holds at most one batch of documents in memory.
    """

    if total_records < 1:
        return

    if batch_size < 2 or batch_size > 500:
        raise ValueError("Batch size must be between 2 and 500.")

    batch_count = ceil(total_records / batch_size)
    base_size, remainder = divmod(total_records, batch_count)

    iterator = iter(cursor)

    for batch_index in range(1, batch_count + 1):
        current_size = base_size + (
            1 if batch_index <= remainder else 0
        )

        batch = []

        for _ in range(current_size):
            try:
                batch.append(next(iterator))
            except StopIteration:
                raise RuntimeError(
                    "MongoDB returned fewer feedback records than counted."
                ) from None

        yield batch_index, batch


def _normalize_timestamp(value, feedback_id: str) -> str:
    """Convert MongoDB timestamps into timezone-aware ISO strings."""

    if isinstance(value, datetime):
        timestamp = value

        # PyMongo can return BSON dates as naive UTC datetimes.
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)

        return timestamp.isoformat()

    if isinstance(value, str):
        try:
            timestamp = datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )

            if (
                timestamp.tzinfo is None
                or timestamp.utcoffset() is None
            ):
                raise ValueError("Timezone information is missing.")

            return timestamp.isoformat()

        except (ValueError, TypeError):
            raise ValueError(
                f"Feedback record {feedback_id} has an invalid "
                "createdAt timestamp."
            ) from None

    raise ValueError(
        f"Feedback record {feedback_id} is missing a valid createdAt."
    )


def _normalize_feedback_document(document: dict) -> dict:
    """Convert a MongoDB feedback document into the AI input format."""

    feedback_id = str(document.get("id") or "").strip()

    if not feedback_id:
        raise ValueError(
            "A MongoDB feedback record is missing its id."
        )

    title = str(document.get("title") or "").strip()
    message = str(document.get("message") or "").strip()
    raw_text = message or title

    if not raw_text:
        raise ValueError(
            f"Feedback record {feedback_id} has no usable text."
        )

    timestamp = _normalize_timestamp(
        document.get("createdAt"),
        feedback_id,
    )

    return {
        "feedback_id": feedback_id,
        "id": feedback_id,
        "title": title,
        "message": message or title,
        "raw_text": raw_text,
        "source_channel": str(
            document.get("source") or "unknown"
        ).strip() or "unknown",
        "timestamp": timestamp,
        "dataset": str(
            document.get("dataset") or "user_feedback"
        ).strip() or "user_feedback",
    }


def _failed_batch_response(
    records: list[dict],
    message: str,
) -> dict:
    """Build a safe, persistable response when one AI request fails."""

    feedback_ids = [
        record["feedback_id"]
        for record in records
    ]

    return {
        "success": False,
        "status": "failed",
        "total_feedback_analyzed": len(records),
        "agent_status": {
            key: "failed" for key in AGENT_KEYS
        },
        "errors": {
            key: message for key in AGENT_KEYS
        },
        "results": {
            key: None for key in AGENT_KEYS
        },
        "token_usage": {},
        "execution_order": [],
        "data_flow": {},
        "_feedback_ids": feedback_ids,
    }


def _call_ai_batch(
    records: list[dict],
    timeout: httpx.Timeout,
) -> dict:
    """Send one bounded batch to the AI module."""

    endpoint = (
        f"{Config.AI_SERVICE_URL.rstrip('/')}/analysis/run-all"
    )

    response = httpx.post(
        endpoint,
        json={
            "feedback_records": records,
            "batch_size": len(records),
        },
        timeout=timeout,
    )

    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError("AI service returned an invalid response.")

    if not isinstance(payload.get("results"), dict):
        raise ValueError("AI response is missing analysis results.")

    if not isinstance(payload.get("agent_status"), dict):
        raise ValueError("AI response is missing agent statuses.")

    if not isinstance(payload.get("success"), bool):
        raise ValueError("AI response is missing its success status.")

    if not isinstance(payload.get("errors"), dict):
        raise ValueError("AI response is missing its error details.")

    payload["total_feedback_analyzed"] = len(records)
    payload["_feedback_ids"] = [
        record["feedback_id"] for record in records
    ]

    return payload


def _save_batch_document(
    *,
    db,
    run_id: str,
    user_id: str,
    workspace_id: str | None,
    batch_index: int,
    response: dict,
) -> str:
    """Persist one batch immediately using a stable idempotent key."""

    batch_id = f"{run_id}-batch-{batch_index}"

    batch_document = {
        "id": batch_id,
        "run_id": run_id,
        "userId": user_id,
        "workspaceId": workspace_id,
        "batch_index": batch_index,
        "record_count": response.get(
            "total_feedback_analyzed", 0
        ),
        "feedback_ids": response.get("_feedback_ids", []),
        "status": response.get("status", "failed"),
        "success": bool(response.get("success", False)),
        "agent_status": response.get("agent_status", {}),
        "errors": response.get("errors", {}),
        "results": response.get("results", {}),
        "token_usage": response.get("token_usage", {}),
        "createdAt": now_iso(),
        "updatedAt": now_iso(),
    }

    db["analysis_batches"].replace_one(
        {
            "run_id": run_id,
            "batch_index": batch_index,
        },
        batch_document,
        upsert=True,
    )

    return batch_id


def _build_aggregation_response(response: dict) -> dict:
    """Keep only the fields needed by the no-LLM aggregation endpoint."""

    return {
        "success": bool(response.get("success", False)),
        "status": response.get("status", "failed"),
        "total_feedback_analyzed": response.get(
            "total_feedback_analyzed", 0
        ),
        "agent_status": response.get("agent_status", {}),
        "errors": response.get("errors", {}),
        "results": response.get("results", {}),
        "token_usage": response.get("token_usage", {}),
        "execution_order": response.get("execution_order", []),
        "data_flow": response.get("data_flow", {}),
        "_feedback_ids": response.get("_feedback_ids", []),
    }


def _aggregate_saved_batches(
    *,
    batch_responses: list[dict],
    source_counts: dict,
    total_records: int,
    batch_size: int,
    timeout: httpx.Timeout,
) -> dict:
    """
    Ask the AI module to merge already-completed batch outputs.

    This endpoint performs deterministic Python aggregation only.
    It does not invoke Gemini or any of the four AI agents.
    """

    endpoint = (
        f"{Config.AI_SERVICE_URL.rstrip('/')}"
        "/analysis/aggregate-batches"
    )

    response = httpx.post(
        endpoint,
        json={
            "total_feedback_analyzed": total_records,
            "source_counts": source_counts,
            "batch_size": batch_size,
            "batch_responses": [
                _build_aggregation_response(item)
                for item in batch_responses
            ],
        },
        timeout=timeout,
    )

    response.raise_for_status()
    payload = response.json()

    if not isinstance(payload, dict):
        raise ValueError("AI aggregation returned an invalid response.")

    if not isinstance(payload.get("results"), dict):
        raise ValueError("AI aggregation is missing merged results.")

    return payload


def run_and_save_analysis(
    user_id: str,
    workspace_id: str | None = None,
) -> dict:
    """
    Stream MongoDB feedback through the existing four-agent pipeline.

    Only one feedback batch is held in memory at a time. Each batch
    is persisted before the next batch is fetched.
    """

    db = get_db()
    run_collection = db["analysis_runs"]

    run_id = generate_id("analysis-")
    created_at = now_iso()

    initial_document = {
        "id": run_id,
        "run_id": run_id,
        "userId": user_id,
        "workspaceId": workspace_id,
        "input_source": "mongodb",
        "input_record_count": 0,
        "batch_size": DEFAULT_ANALYSIS_BATCH_SIZE,
        "total_batches": 0,
        "completed_batches": 0,
        "partial_or_failed_batches": 0,
        "batch_ids": [],
        "status": "running",
        "success": False,
        "createdAt": created_at,
        "updatedAt": created_at,
        "startedAt": created_at,
        "completedAt": None,
        "total_feedback_analyzed": 0,
        "agent_status": {},
        "results": {},
        "token_usage": {},
        "errors": {},
    }

    try:
        run_collection.insert_one(initial_document)
    except PyMongoError as exc:
        logger.exception("Could not create analysis run.")
        raise AnalysisServiceError(
            "Could not create the analysis record.",
            503,
        ) from exc

    query = _build_feedback_query(user_id, workspace_id)

    projection = {
        "_id": 0,
        "id": 1,
        "title": 1,
        "message": 1,
        "source": 1,
        "createdAt": 1,
        "dataset": 1,
    }

    try:
        total_records = db["feedback"].count_documents(query)
        _validate_feedback_count(total_records)

        cursor = (
            db["feedback"]
            .find(query, projection)
            .sort([
                ("createdAt", ASCENDING),
                ("id", ASCENDING),
            ])
            .batch_size(DEFAULT_ANALYSIS_BATCH_SIZE)
        )

    except AnalysisServiceError as exc:
        _mark_failed(run_collection, run_id, str(exc))
        raise

    except PyMongoError as exc:
        logger.exception("Could not count or read feedback records.")
        message = "Could not retrieve feedback records from MongoDB."
        _mark_failed(run_collection, run_id, message)
        raise AnalysisServiceError(message, 503) from exc

    total_batches = ceil(
        total_records / DEFAULT_ANALYSIS_BATCH_SIZE
    )

    try:
        run_collection.update_one(
            {"run_id": run_id, "userId": user_id},
            {
                "$set": {
                    "input_record_count": total_records,
                    "total_batches": total_batches,
                    "updatedAt": now_iso(),
                }
            },
        )
    except PyMongoError as exc:
        _mark_failed(
            run_collection,
            run_id,
            "Could not update analysis input metadata.",
        )
        raise AnalysisServiceError(
            "Could not update analysis input metadata.",
            503,
        ) from exc

    timeout = httpx.Timeout(
        Config.AI_SERVICE_TIMEOUT_SECONDS,
        connect=10.0,
    )

    source_counts = {}
    batch_responses = []
    batch_ids = []
    completed_batches = 0
    partial_or_failed_batches = 0
    processed_records = 0
    seen_feedback_ids = set()

    # -----------------------------------------------------
    # STREAM, ANALYSE AND SAVE ONE BATCH AT A TIME
    # -----------------------------------------------------

    try:
        for batch_index, documents in _iter_document_batches(
            cursor,
            total_records,
            DEFAULT_ANALYSIS_BATCH_SIZE,
        ):
            try:
                batch_records = [
                    _normalize_feedback_document(doc)
                    for doc in documents
                ]

                for record in batch_records:
                    feedback_id = record["feedback_id"]

                    if feedback_id in seen_feedback_ids:
                        raise ValueError(
                            f"Duplicate feedback ID found: {feedback_id}"
                        )

                    seen_feedback_ids.add(feedback_id)

                response = _call_ai_batch(batch_records, timeout)

            except httpx.TimeoutException:
                logger.exception(
                    "AI batch %d timed out.",
                    batch_index,
                )
                response = _failed_batch_response(
                    [
                        {
                            "feedback_id": str(
                                doc.get("id") or f"unknown-{batch_index}"
                            )
                        }
                        for doc in documents
                    ],
                    "The AI analysis service timed out for this batch.",
                )

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "AI batch %d returned HTTP %s.",
                    batch_index,
                    exc.response.status_code,
                )
                response = _failed_batch_response(
                    [
                        {
                            "feedback_id": str(
                                doc.get("id") or f"unknown-{batch_index}"
                            )
                        }
                        for doc in documents
                    ],
                    "The AI analysis service returned an error for this batch.",
                )

            except httpx.RequestError:
                logger.exception(
                    "Could not reach AI service for batch %d.",
                    batch_index,
                )
                response = _failed_batch_response(
                    [
                        {
                            "feedback_id": str(
                                doc.get("id") or f"unknown-{batch_index}"
                            )
                        }
                        for doc in documents
                    ],
                    "The AI analysis service was unavailable for this batch.",
                )

            except (ValueError, TypeError) as exc:
                logger.exception(
                    "Invalid input or response in batch %d.",
                    batch_index,
                )
                response = _failed_batch_response(
                    [
                        {
                            "feedback_id": str(
                                doc.get("id") or f"unknown-{batch_index}"
                            )
                        }
                        for doc in documents
                    ],
                    str(exc),
                )

            # Track source counts without retaining the full dataset.
            for document in documents:
                dataset = str(
                    document.get("dataset") or "user_feedback"
                ).strip() or "user_feedback"
                source_counts[dataset] = (
                    source_counts.get(dataset, 0) + 1
                )

            processed_records += len(documents)

            try:
                batch_id = _save_batch_document(
                    db=db,
                    run_id=run_id,
                    user_id=user_id,
                    workspace_id=workspace_id,
                    batch_index=batch_index,
                    response=response,
                )
            except PyMongoError as exc:
                logger.exception(
                    "Could not persist batch %d.",
                    batch_index,
                )
                message = (
                    f"Could not persist analysis batch {batch_index}. "
                    "Previously saved batches have been preserved."
                )
                _mark_failed(run_collection, run_id, message)
                raise AnalysisServiceError(message, 503) from exc

            batch_ids.append(batch_id)
            batch_responses.append(response)

            if response.get("success"):
                completed_batches += 1
            else:
                partial_or_failed_batches += 1

            logger.info(
                "Saved analysis batch %d/%d (%d records, status=%s).",
                batch_index,
                total_batches,
                len(documents),
                response.get("status"),
            )

    except (RuntimeError, AnalysisServiceError) as exc:
        _mark_failed(run_collection, run_id, str(exc))
        if isinstance(exc, AnalysisServiceError):
            raise
        raise AnalysisServiceError(str(exc), 503) from exc

    if processed_records != total_records:
        message = (
            "The feedback collection changed during analysis. "
            "The number of processed records did not match the initial count."
        )
        _mark_failed(run_collection, run_id, message)
        raise AnalysisServiceError(message, 409)

    # -----------------------------------------------------
    # MERGE THE SAVED BATCH OUTPUTS (NO GEMINI CALL)
    # -----------------------------------------------------

    aggregation_error = None
    aggregate_payload = {}

    try:
        aggregate_payload = _aggregate_saved_batches(
            batch_responses=batch_responses,
            source_counts=source_counts,
            total_records=total_records,
            batch_size=DEFAULT_ANALYSIS_BATCH_SIZE,
            timeout=timeout,
        )
    except (
        httpx.TimeoutException,
        httpx.HTTPStatusError,
        httpx.RequestError,
        ValueError,
        TypeError,
    ):
        logger.exception(
            "Could not merge batch outputs for run %s.",
            run_id,
        )
        aggregation_error = (
            "Batch outputs were saved, but aggregate results "
            "could not be generated."
        )

    aggregate_success = bool(
        aggregate_payload.get("success", False)
    )

    aggregate_status = aggregate_payload.get(
        "status",
        "partial_success",
    )

    if aggregation_error:
        aggregate_status = "partial_success"
        aggregate_success = False

    errors = aggregate_payload.get("errors", {})

    if not isinstance(errors, dict):
        errors = {}

    if aggregation_error:
        errors["aggregation"] = aggregation_error

    analysis_fields = {
        "input_source": "mongodb",
        "input_record_count": total_records,
        "batch_size": DEFAULT_ANALYSIS_BATCH_SIZE,
        "total_batches": total_batches,
        "completed_batches": completed_batches,
        "partial_or_failed_batches": partial_or_failed_batches,
        "batch_ids": batch_ids,
        "status": aggregate_status,
        "success": aggregate_success,
        "pipeline_type": "sequential_streaming_batched",
        "total_feedback_analyzed": aggregate_payload.get(
            "total_feedback_analyzed",
            processed_records,
        ),
        "source_counts": source_counts,
        "execution_order": aggregate_payload.get(
            "execution_order",
            [],
        ),
        "data_flow": aggregate_payload.get("data_flow", {}),
        "agent_status": aggregate_payload.get("agent_status", {}),
        "errors": errors,
        "results": aggregate_payload.get("results", {}),
        "token_usage": aggregate_payload.get("token_usage", {}),
        "batch_summary": aggregate_payload.get(
            "batch_summary",
            {
                "batch_size": DEFAULT_ANALYSIS_BATCH_SIZE,
                "total_batches": total_batches,
                "completed_batches": completed_batches,
                "partial_or_failed_batches": partial_or_failed_batches,
            },
        ),
        "completedAt": now_iso(),
        "updatedAt": now_iso(),
    }

    try:
        run_collection.update_one(
            {
                "run_id": run_id,
                "userId": user_id,
            },
            {
                "$set": analysis_fields,
            },
        )

        saved_document = run_collection.find_one({
            "run_id": run_id,
            "userId": user_id,
        })

        if saved_document is None:
            raise RuntimeError(
                "Analysis record was not found after saving."
            )

        logger.info(
            "Streaming analysis %s finished: %d records, "
            "%d/%d batches successful, status=%s.",
            run_id,
            total_records,
            completed_batches,
            total_batches,
            aggregate_status,
        )

        return mongo_doc_to_dict(saved_document)

    except (PyMongoError, RuntimeError) as exc:
        logger.exception(
            "Analysis batches were saved, but parent run update failed."
        )
        message = (
            "Analysis batches were saved, but the parent run "
            "could not be updated."
        )
        _mark_failed(run_collection, run_id, message)
        raise AnalysisServiceError(message, 503) from exc


def list_analysis_runs(
    user_id: str,
    workspace_id: str | None = None,
    limit: int = 20,
) -> list:
    """Return compact analysis history for one authenticated user."""

    query = {"userId": user_id}

    if workspace_id:
        query["workspaceId"] = workspace_id

    cursor = (
        get_db()["analysis_runs"]
        .find(
            query,
            {
                "results": 0,
                "errors": 0,
                "token_usage": 0,
            },
        )
        .sort("createdAt", DESCENDING)
        .limit(limit)
    )

    return mongo_docs_to_list(cursor)


def get_latest_analysis_run(
    user_id: str,
    workspace_id: str | None = None,
) -> dict | None:
    """Return the latest analysis document for a user."""

    query = {"userId": user_id}

    if workspace_id:
        query["workspaceId"] = workspace_id

    document = get_db()["analysis_runs"].find_one(
        query,
        sort=[("createdAt", DESCENDING)],
    )

    return mongo_doc_to_dict(document)


def get_analysis_run(
    user_id: str,
    run_id: str,
) -> dict | None:
    """Retrieve one analysis run belonging to the user."""

    document = get_db()["analysis_runs"].find_one({
        "run_id": run_id,
        "userId": user_id,
    })

    return mongo_doc_to_dict(document)


def list_analysis_batches(
    user_id: str,
    run_id: str,
) -> list:
    """Return batch records belonging to one user's analysis run."""

    cursor = (
        get_db()["analysis_batches"]
        .find({
            "userId": user_id,
            "run_id": run_id,
        })
        .sort("batch_index", ASCENDING)
    )

    return mongo_docs_to_list(cursor)