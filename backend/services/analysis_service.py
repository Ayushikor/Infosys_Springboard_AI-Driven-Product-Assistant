
"""Analysis execution and MongoDB persistence service."""

import logging

import httpx
from pymongo import DESCENDING
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


class AnalysisServiceError(RuntimeError):
    """Raised when analysis execution or persistence fails."""

    def __init__(self, message: str, status_code: int = 503):
        super().__init__(message)
        self.status_code = status_code


def _mark_failed(collection, run_id: str, message: str) -> None:
    """Mark a previously created analysis run as failed."""

    collection.update_one(
        {"run_id": run_id},
        {
            "$set": {
                "status": "failed",
                "success": False,
                "errors": {"pipeline": message},
                "completedAt": now_iso(),
            }
        },
    )


def run_and_save_analysis(
    user_id: str,
    workspace_id: str | None = None,
) -> dict:
    """
    Execute the four-agent AI pipeline and persist its response.

    A running document is created before calling the AI service,
    so failed attempts are also represented in analysis history.
    """

    collection = get_db()["analysis_runs"]

    run_id = generate_id("analysis-")
    created_at = now_iso()

    initial_document = {
        "run_id": run_id,
        "userId": user_id,
        "workspaceId": workspace_id,
        "status": "running",
        "success": False,
        "createdAt": created_at,
        "startedAt": created_at,
        "completedAt": None,
        "total_feedback_analyzed": 0,
        "agent_status": {},
        "results": {},
        "token_usage": {},
        "errors": {},
    }

    try:
        collection.insert_one(initial_document)

    except PyMongoError as exc:
        logger.exception("Could not create analysis run in MongoDB.")

        raise AnalysisServiceError(
            "Could not create the analysis record.",
            503,
        ) from exc

    # -----------------------------------------------------
    # CALL THE AI MODULE
    # -----------------------------------------------------

    endpoint = f"{Config.AI_SERVICE_URL}/analysis/run-all"

    try:
        timeout = httpx.Timeout(
            Config.AI_SERVICE_TIMEOUT_SECONDS,
            connect=10.0,
        )

        response = httpx.post(
            endpoint,
            json={},
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

    except httpx.TimeoutException as exc:
        message = "The AI analysis service timed out."
        _mark_failed(collection, run_id, message)

        raise AnalysisServiceError(message, 504) from exc

    except httpx.HTTPStatusError as exc:
        logger.error(
            "AI service returned HTTP %s.",
            exc.response.status_code,
        )

        message = "The AI analysis service returned an error."
        _mark_failed(collection, run_id, message)

        raise AnalysisServiceError(message, 502) from exc

    except httpx.RequestError as exc:
        logger.exception("Could not reach the AI analysis service.")

        message = "The AI analysis service is unavailable."
        _mark_failed(collection, run_id, message)

        raise AnalysisServiceError(message, 503) from exc

    except (ValueError, TypeError) as exc:
        logger.exception("Invalid response from AI analysis service.")

        message = "The AI analysis service returned invalid results."
        _mark_failed(collection, run_id, message)

        raise AnalysisServiceError(message, 502) from exc

    # -----------------------------------------------------
    # SAVE ALL AGENT RESULTS
    # -----------------------------------------------------

    analysis_fields = {
        "status": payload.get("status", "unknown"),
        "success": bool(payload.get("success", False)),
        "pipeline_type": payload.get("pipeline_type", "sequential"),
        "total_feedback_analyzed": payload.get(
            "total_feedback_analyzed", 0
        ),
        "source_counts": payload.get("source_counts", {}),
        "execution_order": payload.get("execution_order", []),
        "data_flow": payload.get("data_flow", {}),
        "agent_status": payload.get("agent_status", {}),
        "errors": payload.get("errors", {}),
        "results": payload.get("results", {}),
        "token_usage": payload.get("token_usage", {}),
        "completedAt": now_iso(),
    }

    try:
        collection.update_one(
            {"run_id": run_id, "userId": user_id},
            {"$set": analysis_fields},
        )

        saved_document = collection.find_one({
            "run_id": run_id,
            "userId": user_id,
        })

        if saved_document is None:
            raise RuntimeError(
                "Analysis record was not found after saving."
            )

        logger.info(
            "Analysis run %s saved with status %s.",
            run_id,
            analysis_fields["status"],
        )

        return mongo_doc_to_dict(saved_document)

    except (PyMongoError, RuntimeError) as exc:
        logger.exception(
            "Analysis completed, but its results could not be saved."
        )

        raise AnalysisServiceError(
            "Analysis completed, but its results could not be saved.",
            503,
        ) from exc


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
    """Return the latest complete document for a user."""

    query = {"userId": user_id}

    if workspace_id:
        query["workspaceId"] = workspace_id

    document = (
        get_db()["analysis_runs"]
        .find_one(
            query,
            sort=[("createdAt", DESCENDING)],
        )
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
