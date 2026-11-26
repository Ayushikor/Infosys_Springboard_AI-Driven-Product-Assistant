"""
Notification API routes.

Notifications are stored in MongoDB and scoped to the
authenticated user's session.
"""

from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

from db import get_db
from helpers import ok, fail, generate_id, now_iso


router = APIRouter(
    prefix="/api/notifications",
    tags=["Notifications"],
)


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------


def _get_user_id(request: Request):
    """Return the authenticated user's ID."""
    return request.session.get("user_id")


def _error_response(
    message: str,
    status: int = 400,
    data=None,
):
    """Return the application's standard error response."""

    body, status_code = fail(
        message,
        data=data,
        status=status,
    )

    return JSONResponse(
        content=body,
        status_code=status_code,
    )


# ---------------------------------------------------------
# CREATE NOTIFICATION
# ---------------------------------------------------------


def create_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str = "info",
    link: str | None = None,
    metadata: dict | None = None,
):
    """
    Create a notification for a specific user.

    This helper can be imported by other backend routes
    to generate notifications after successful events.
    """

    if not user_id:
        return None

    notification = {
        "id": generate_id("notif-"),
        "userId": user_id,
        "title": title,
        "message": message,
        "type": notification_type,
        "read": False,
        "isRead": False,
        "createdAt": now_iso(),
        "link": link,
        "metadata": metadata or {},
    }

    try:
        get_db()["notifications"].insert_one(notification)
    except Exception as exc:
        print("[Notification] Failed to save notification:", str(exc))
        return None

    return notification


# ---------------------------------------------------------
# GET ALL NOTIFICATIONS
# ---------------------------------------------------------


@router.get("")
def get_notifications(
    request: Request,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
):
    """Return notifications belonging to the current user."""

    user_id = _get_user_id(request)

    if not user_id:
        return _error_response(
            "Authentication required.",
            status=401,
        )

    notifications = list(
        get_db()["notifications"]
        .find(
            {"userId": user_id},
            {"_id": 0},
        )
        .sort("createdAt", -1)
        .limit(limit)
    )

    unread_count = get_db()["notifications"].count_documents(
        {
            "userId": user_id,
            "$or": [
                {"read": False},
                {"isRead": False},
            ],
        }
    )

    return ok(
        {
            "notifications": notifications,
            "count": len(notifications),
            "unreadCount": unread_count,
        },
        "Notifications retrieved successfully.",
    )


# ---------------------------------------------------------
# UNREAD COUNT
# ---------------------------------------------------------


@router.get("/unread-count")
def get_unread_count(request: Request):
    """Return unread notification count for current user."""

    user_id = _get_user_id(request)

    if not user_id:
        return _error_response(
            "Authentication required.",
            status=401,
        )

    count = get_db()["notifications"].count_documents(
        {
            "userId": user_id,
            "$or": [
                {"read": False},
                {"isRead": False},
            ],
        }
    )

    return ok(
        {"count": count},
        "Unread notification count retrieved.",
    )


# ---------------------------------------------------------
# MARK ONE AS READ
# ---------------------------------------------------------


@router.patch("/{notification_id}/read")
def mark_as_read(
    notification_id: str,
    request: Request,
):
    """Mark a notification as read."""

    user_id = _get_user_id(request)

    if not user_id:
        return _error_response(
            "Authentication required.",
            status=401,
        )

    result = get_db()["notifications"].update_one(
        {
            "id": notification_id,
            "userId": user_id,
        },
        {
            "$set": {
                "read": True,
                "isRead": True,
                "readAt": now_iso(),
            }
        },
    )

    if result.matched_count == 0:
        return _error_response(
            "Notification not found.",
            status=404,
        )

    return ok(
        {"id": notification_id},
        "Notification marked as read.",
    )


# ---------------------------------------------------------
# MARK ALL AS READ
# ---------------------------------------------------------


@router.patch("/read-all")
def mark_all_as_read(request: Request):
    """Mark all current user's notifications as read."""

    user_id = _get_user_id(request)

    if not user_id:
        return _error_response(
            "Authentication required.",
            status=401,
        )

    result = get_db()["notifications"].update_many(
        {
            "userId": user_id,
            "$or": [
                {"read": False},
                {"isRead": False},
            ],
        },
        {
            "$set": {
                "read": True,
                "isRead": True,
                "readAt": now_iso(),
            }
        },
    )

    return ok(
        {
            "modifiedCount": result.modified_count,
        },
        "All notifications marked as read.",
    )


# ---------------------------------------------------------
# DELETE ONE NOTIFICATION
# ---------------------------------------------------------


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: str,
    request: Request,
):
    """Delete one notification belonging to the current user."""

    user_id = _get_user_id(request)

    if not user_id:
        return _error_response(
            "Authentication required.",
            status=401,
        )

    result = get_db()["notifications"].delete_one(
        {
            "id": notification_id,
            "userId": user_id,
        }
    )

    if result.deleted_count == 0:
        return _error_response(
            "Notification not found.",
            status=404,
        )

    return ok(
        {"id": notification_id},
        "Notification deleted successfully.",
    )


# ---------------------------------------------------------
# DELETE ALL NOTIFICATIONS
# ---------------------------------------------------------


@router.delete("")
def delete_all_notifications(request: Request):
    """Delete all notifications belonging to current user."""

    user_id = _get_user_id(request)

    if not user_id:
        return _error_response(
            "Authentication required.",
            status=401,
        )

    result = get_db()["notifications"].delete_many(
        {"userId": user_id}
    )

    return ok(
        {
            "deletedCount": result.deleted_count,
        },
        "All notifications deleted.",
    )


# ---------------------------------------------------------
# TEST NOTIFICATION
# ---------------------------------------------------------


@router.post("/test")
def create_test_notification(request: Request):
    """Create a test notification for the current user."""

    user_id = _get_user_id(request)

    if not user_id:
        return _error_response(
            "Authentication required.",
            status=401,
        )

    notification = create_notification(
        user_id=user_id,
        title="Notification system test",
        message=(
            "Your Stratov notification system is working. "
            "This notification was successfully saved to MongoDB."
        ),
        notification_type="success",
        metadata={
            "source": "notification_test",
        },
    )

    if notification is None:
        return _error_response(
            "Failed to create test notification.",
            status=500,
        )

    return ok(
        {
            "notification": notification,
        },
        "Test notification created successfully.",
    )