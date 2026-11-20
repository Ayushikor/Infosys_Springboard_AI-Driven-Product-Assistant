
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


# ---------------------------------------------------------
# AUTHENTICATION AND ERROR HANDLING
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# WORKSPACE VALIDATION
# ---------------------------------------------------------

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
    """
    Execute AI analysis.

    When importId is provided, only feedback records belonging
    to that uploaded dataset are analysed.

    When importId is omitted, the legacy workspace-based
    analysis behaviour is retained.
    """

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            401,
        )

    body = body or {}

    # -----------------------------------------------------
    # 1. VALIDATE THE SELECTED IMPORT ID
    # -----------------------------------------------------

    import_id = body.get("importId")

    if import_id is not None:

        if not isinstance(import_id, str):
            return _error_response(
                "Invalid import ID.",
                400,
            )

        import_id = import_id.strip()

        if not import_id:
            return _error_response(
                "Import ID cannot be empty.",
                400,
            )

        # Verify dataset ownership before starting analysis.
        dataset = get_db()["feedback"].find_one(
            {
                "userId": uid,
                "import_id": import_id,
            },
            {
                "_id": 1,
            },
        )

        if not dataset:
            return _error_response(
                "Uploaded dataset not found or does not belong to you.",
                404,
            )

    # -----------------------------------------------------
    # 2. RESOLVE THE WORKSPACE
    # -----------------------------------------------------

    workspace_id, workspace_error = _resolve_workspace(
        uid,
        body.get("workspaceId"),
    )

    if workspace_error:
        return _error_response(
            workspace_error,
            404,
        )

    # -----------------------------------------------------
    # 3. EXECUTE ANALYSIS
    # -----------------------------------------------------

    try:
        result = run_and_save_analysis(
            user_id=uid,
            workspace_id=workspace_id,
            import_id=import_id,
        )

        message = (
            "Analysis completed successfully."
            if result.get("status") == "completed"
            else "Analysis saved with partial results."
        )

        return ok(
            result,
            message,
        )

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
