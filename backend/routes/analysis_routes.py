"""AI analysis execution and retrieval routes."""

from datetime import datetime, timezone
from uuid import uuid4

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
# NOTIFICATION HELPER
# ---------------------------------------------------------


def _create_analysis_notification(
    user_id: str,
    result: dict,
    workspace_id: str | None = None,
):
    """
    Create a notification after analysis completes.

    Notification failures must never interrupt or invalidate
    a successfully completed analysis.
    """

    try:
        db = get_db()

        status = result.get("status", "completed")

        if status == "completed":
            title = "Analysis Completed"
            message = "Your AI feedback analysis has completed successfully."
            notification_type = "success"

        else:
            title = "Analysis Completed with Partial Results"
            message = (
                "Your AI feedback analysis has completed, "
                "but some agents or results may be incomplete."
            )
            notification_type = "warning"

        run_id = (
            result.get("run_id")
            or result.get("runId")
            or result.get("id")
            or result.get("analysisId")
        )

        notification = {
            "id": str(uuid4()),
            "userId": user_id,
            "title": title,
            "message": message,
            "type": notification_type,
            "read": False,
            "isRead": False,
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "link": "/analysis",
            "metadata": {
                "event": "analysis_completed",
                "status": status,
                "runId": run_id,
                "workspaceId": workspace_id,
            },
        }

        db["notifications"].insert_one(notification)

    except Exception as exc:
        # Notification failure must not break the main analysis.
        print(
            "[Notification] Failed to create analysis notification:",
            str(exc),
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

    A request may select one imported dataset by importId or one
    historical dataset by datasetName.

    Omitting both preserves the existing workspace-based
    analysis behaviour.
    """

    uid = _user_id(request)

    if not uid:
        return _error_response(
            "Not authenticated.",
            401,
        )

    body = body or {}

    # -----------------------------------------------------
    # 1. VALIDATE SELECTED DATASET AND OWNERSHIP
    # -----------------------------------------------------

    import_id = body.get("importId")
    dataset_name = body.get("datasetName")

    if import_id is not None and dataset_name is not None:
        return _error_response(
            "Select either an uploaded or historical dataset, not both.",
            400,
        )

    # Validate uploaded dataset
    if import_id is not None:

        if not isinstance(import_id, str) or not import_id.strip():
            return _error_response(
                "Invalid import ID.",
                400,
            )

        import_id = import_id.strip()

        owned_dataset = get_db()["feedback"].find_one(
            {
                "userId": uid,
                "import_id": import_id,
            },
            {
                "_id": 1,
            },
        )

        if not owned_dataset:
            return _error_response(
                "Uploaded dataset not found or does not belong to you.",
                404,
            )

    # Validate historical dataset
    if dataset_name is not None:

        if not isinstance(dataset_name, str) or not dataset_name.strip():
            return _error_response(
                "Invalid historical dataset name.",
                400,
            )

        dataset_name = dataset_name.strip()

        owned_dataset = get_db()["feedback"].find_one(
            {
                "userId": uid,
                "dataset": dataset_name,
                "$or": [
                    {
                        "import_id": {
                            "$exists": False,
                        }
                    },
                    {
                        "import_id": None,
                    },
                    {
                        "import_id": "",
                    },
                ],
            },
            {
                "_id": 1,
            },
        )

        if not owned_dataset:
            return _error_response(
                "Historical dataset not found or does not belong to you.",
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
            dataset_name=dataset_name,
        )

        # -------------------------------------------------
        # 4. CREATE NOTIFICATION
        # -------------------------------------------------

        _create_analysis_notification(
            user_id=uid,
            result=result,
            workspace_id=workspace_id,
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