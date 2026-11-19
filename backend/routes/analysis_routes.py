
"""AI analysis execution and retrieval routes."""

from fastapi import APIRouter, Request, Body, Query
from fastapi.responses import JSONResponse

from db import get_db
from helpers import ok, fail

from services.analysis_service import (
    AnalysisServiceError,
    run_and_save_analysis,
    list_analysis_runs,
    get_latest_analysis_run,
    get_analysis_run,
)


router = APIRouter(
    prefix="/api/analysis",
    tags=["AI Analysis"],
)


def _user_id(request: Request):
    """Return the authenticated user's ID from the session."""
    return request.session.get("user_id")


def _error_response(
    message: str,
    status: int = 400,
):
    """Return an error using the existing frontend response format."""

    body, status_code = fail(
        message,
        status=status,
    )

    return JSONResponse(
        content=body,
        status_code=status_code,
    )


def _resolve_workspace(
    user_id: str,
    requested_workspace_id: str | None = None,
):
    """
    Validate requested workspace ownership.

    If no workspace is supplied, use the user's active workspace
    when it exists and belongs to that user.
    """

    db = get_db()

    if requested_workspace_id:
        workspace = db["workspaces"].find_one({
            "id": requested_workspace_id,
            "userId": user_id,
        })

        if not workspace:
            return None, "Workspace not found."

        return requested_workspace_id, None

    state = db["user_state"].find_one({
        "userId": user_id,
    }) or {}

    active_id = state.get("activeWorkspaceId")

    if not active_id:
        return None, None

    workspace = db["workspaces"].find_one({
        "id": active_id,
        "userId": user_id,
    })

    if not workspace:
        return None, None

    return active_id, None


def _validate_workspace_filter(
    user_id: str,
    workspace_id: str | None,
):
    """Validate an optional workspace filter for GET requests."""

    if not workspace_id:
        return None

    workspace = get_db()["workspaces"].find_one({
        "id": workspace_id,
        "userId": user_id,
    })

    if not workspace:
        return None

    return workspace_id


# ---------------------------------------------------------
# RUN COMPLETE FOUR-AGENT ANALYSIS
# ---------------------------------------------------------


@router.post("/run")
def run_analysis(
    request: Request,
    body: dict | None = Body(default=None),
):
    """Execute the AI module and save its complete response."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            401,
        )

    body = body or {}

    workspace_id, workspace_error = _resolve_workspace(
        uid,
        body.get("workspaceId"),
    )

    if workspace_error:
        return _error_response(
            workspace_error,
            404,
        )

    try:
        result = run_and_save_analysis(
            user_id=uid,
            workspace_id=workspace_id,
        )

        message = (
            "Analysis completed successfully."
            if result.get("status") == "completed"
            else "Analysis saved with partial results."
        )

        return ok(result, message)

    except AnalysisServiceError as exc:
        return _error_response(
            str(exc),
            exc.status_code,
        )


# ---------------------------------------------------------
# LIST ANALYSIS HISTORY
# ---------------------------------------------------------


@router.get("/runs")
def get_analysis_history(
    request: Request,
    workspaceId: str | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
):
    """Retrieve analysis history belonging to the current user."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            401,
        )

    workspace_id = _validate_workspace_filter(
        uid,
        workspaceId,
    )

    if workspaceId and not workspace_id:
        return _error_response(
            "Workspace not found.",
            404,
        )

    items = list_analysis_runs(
        user_id=uid,
        workspace_id=workspace_id,
        limit=limit,
    )

    return ok({
        "items": items,
        "count": len(items),
    })


# ---------------------------------------------------------
# RETRIEVE LATEST ANALYSIS
# ---------------------------------------------------------


@router.get("/runs/latest")
def get_latest_analysis(
    request: Request,
    workspaceId: str | None = Query(default=None),
):
    """Retrieve the latest analysis run for the current user."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            401,
        )

    workspace_id = _validate_workspace_filter(
        uid,
        workspaceId,
    )

    if workspaceId and not workspace_id:
        return _error_response(
            "Workspace not found.",
            404,
        )

    result = get_latest_analysis_run(
        user_id=uid,
        workspace_id=workspace_id,
    )

    if not result:
        return _error_response(
            "No analysis runs were found.",
            404,
        )

    return ok(result)


# ---------------------------------------------------------
# RETRIEVE SPECIFIC ANALYSIS RUN
# ---------------------------------------------------------


@router.get("/runs/{run_id}")
def get_analysis_details(
    run_id: str,
    request: Request,
):
    """Retrieve a specific run belonging to the current user."""

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            401,
        )

    result = get_analysis_run(
        user_id=uid,
        run_id=run_id,
    )

    if not result:
        return _error_response(
            "Analysis run not found.",
            404,
        )

    return ok(result)
