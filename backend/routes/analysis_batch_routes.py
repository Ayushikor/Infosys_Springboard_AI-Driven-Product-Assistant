
"""API routes for retrieving AI analysis batch details."""

from fastapi import APIRouter, HTTPException, Query, Request

from helpers import ok
from services.analysis_service import (
    get_analysis_run,
    list_analysis_batches,
)

router = APIRouter(
    prefix="/api/analysis",
    tags=["Analysis Batches"],
)


def _public_batch(batch, include_results=False):
    """
    Return only fields intended for the frontend.

    Internal MongoDB identifiers, ownership metadata,
    feedback IDs, and token usage are never exposed.
    """

    public = {
        "batch_index": batch.get("batch_index"),
        "record_count": batch.get("record_count"),
        "status": batch.get("status"),
        "success": batch.get("success"),
        "agent_status": batch.get("agent_status", {}),
        "errors": batch.get("errors", {}),
        "createdAt": batch.get("createdAt"),
        "updatedAt": batch.get("updatedAt"),
    }

    # Include full agent results only when explicitly requested.
    if include_results:
        public["results"] = batch.get("results", {})

    # Exclude fields that are not available.
    return {
        key: value
        for key, value in public.items()
        if value is not None
    }


@router.get("/runs/{run_id}/batches")
def get_analysis_batches(
    run_id: str,
    request: Request,
    include_results: bool = Query(
        default=False,
        description="Include full agent results for every batch.",
    ),
):
    """
    Retrieve batch-level details for an analysis run.

    Only the authenticated owner of the analysis run can access it.
    By default, large agent result payloads are excluded.
    """

    user_id = request.session.get("user_id")

    if not user_id:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated.",
        )

    # Verify that this run belongs to the authenticated user.
    analysis_run = get_analysis_run(user_id, run_id)

    if analysis_run is None:
        raise HTTPException(
            status_code=404,
            detail="Analysis run not found.",
        )

    # Retrieve the original batch documents.
    batches = list_analysis_batches(user_id, run_id)

    # Convert database documents into safe API responses.
    public_batches = [
        _public_batch(batch, include_results)
        for batch in batches
    ]

    return ok(
        {
            "run_id": run_id,
            "status": analysis_run.get("status"),
            "total_batches": analysis_run.get(
                "total_batches",
                len(batches),
            ),
            "completed_batches": analysis_run.get(
                "completed_batches",
                0,
            ),
            "partial_or_failed_batches": analysis_run.get(
                "partial_or_failed_batches",
                0,
            ),
            "batches": public_batches,
        },
        "Analysis batch details retrieved successfully.",
    )
