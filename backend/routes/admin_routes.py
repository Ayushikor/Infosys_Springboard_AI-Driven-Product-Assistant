
"""Administrative user and role management endpoints."""

from datetime import datetime, timezone

from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse

from db import get_db
from helpers import ok, fail, now_iso
from role_permissions import ROLES, normalize_role


router = APIRouter(prefix="/api/admin", tags=["Administration"])


def _error(message, status=400):
    body, code = fail(message, status=status)
    return JSONResponse(content=body, status_code=code)


def _admin_user(request):
    user_id = request.session.get("user_id")

    if not user_id:
        return None, _error("Authentication required.", 401)

    user = get_db()["users"].find_one({"id": user_id})

    if not user:
        return None, _error("User account not found.", 401)

    if user.get("isActive", True) is False:
        request.session.clear()
        return None, _error("Your account is inactive.", 403)

    if normalize_role(user.get("role")) != "Admin":
        return None, _error("Administrator permission required.", 403)

    return user, None


def _public_user(user):
    return {
        "id": user.get("id"),
        "name": user.get("name", ""),
        "username": user.get("username", ""),
        "email": user.get("email", ""),
        "role": normalize_role(user.get("role")),
        "designation": user.get("designation", ""),
        "isActive": user.get("isActive", True),
        "createdAt": user.get("createdAt", ""),
        "lastRoleUpdatedAt": user.get("lastRoleUpdatedAt"),
    }


def _audit(actor, action, target_id, details=None):
    get_db()["audit_logs"].insert_one({
        "actorUserId": actor.get("id"),
        "actorEmail": actor.get("email"),
        "action": action,
        "targetUserId": target_id,
        "details": details or {},
        "createdAt": now_iso(),
    })


def _active_admin_count(users):
    return sum(
        1
        for item in users.find(
            {},
            {"role": 1, "isActive": 1}
        )
        if normalize_role(item.get("role")) == "Admin"
        and item.get("isActive", True)
    )


@router.get("/users")
def list_users(request: Request):
    actor, error = _admin_user(request)

    if error:
        return error

    users = list(
        get_db()["users"]
        .find({}, {"_id": 0})
        .sort("createdAt", -1)
    )

    return ok(
        {
            "users": [_public_user(user) for user in users],
            "roles": list(ROLES),
        },
        "Users retrieved.",
    )


@router.patch("/users/{user_id}/role")
def update_user_role(
    request: Request,
    user_id: str,
    body: dict = Body(...),
):
    actor, error = _admin_user(request)

    if error:
        return error

    role = body.get("role") if isinstance(body, dict) else None

    if role not in ROLES:
        return _error(
            "Choose a valid role: Admin, Product Manager, Developer, or Executive."
        )

    users = get_db()["users"]
    target = users.find_one({"id": user_id})

    if not target:
        return _error("User not found.", 404)

    old_role = normalize_role(target.get("role"))

    if old_role == "Admin" and role != "Admin":
        if _active_admin_count(users) <= 1:
            return _error(
                "The last active administrator cannot be demoted.",
                409,
            )

    timestamp = datetime.now(timezone.utc).isoformat()

    users.update_one(
        {"id": user_id},
        {
            "$set": {
                "role": role,
                "lastRoleUpdatedAt": timestamp,
            }
        },
    )

    _audit(
        actor,
        "user.role_updated",
        user_id,
        {"from": old_role, "to": role},
    )

    updated = users.find_one({"id": user_id})

    return ok(
        {"user": _public_user(updated)},
        "User role updated.",
    )


@router.patch("/users/{user_id}/status")
def update_user_status(
    request: Request,
    user_id: str,
    body: dict = Body(...),
):
    actor, error = _admin_user(request)

    if error:
        return error

    is_active = body.get("isActive") if isinstance(body, dict) else None

    if not isinstance(is_active, bool):
        return _error("isActive must be true or false.")

    if user_id == actor.get("id") and not is_active:
        return _error(
            "You cannot deactivate your own administrator account.",
            409,
        )

    users = get_db()["users"]
    target = users.find_one({"id": user_id})

    if not target:
        return _error("User not found.", 404)

    if (
        not is_active
        and normalize_role(target.get("role")) == "Admin"
        and target.get("isActive", True)
    ):
        if _active_admin_count(users) <= 1:
            return _error(
                "The last active administrator cannot be deactivated.",
                409,
            )

    users.update_one(
        {"id": user_id},
        {"$set": {"isActive": is_active}},
    )

    _audit(
        actor,
        "user.status_updated",
        user_id,
        {"isActive": is_active},
    )

    return ok(
        {"user": _public_user(users.find_one({"id": user_id}))},
        "User status updated.",
    )


@router.delete("/users/{user_id}")
def delete_user(request: Request, user_id: str):
    """Permanently delete a user and their owned application data."""

    actor, error = _admin_user(request)

    if error:
        return error

    # An administrator cannot delete their own account.
    if user_id == actor.get("id"):
        return _error(
            "You cannot delete your own administrator account.",
            409,
        )

    db = get_db()
    users = db["users"]

    target = users.find_one({"id": user_id})

    if not target:
        return _error("User not found.", 404)

    # Protect the last active administrator.
    if (
        normalize_role(target.get("role")) == "Admin"
        and target.get("isActive", True)
    ):
        if _active_admin_count(users) <= 1:
            return _error(
                "The last active administrator cannot be deleted.",
                409,
            )

    # These collections store user-owned records using userId.
    user_collections = [
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
        "chat_messages",
        "chat_conversations",
        "chat_artifacts",
    ]

    deletion_counts = {}

    # Delete only records belonging to the selected user.
    for collection_name in user_collections:
        result = db[collection_name].delete_many(
            {"userId": user_id}
        )
        deletion_counts[collection_name] = result.deleted_count

    # Remove user-specific preferences and active workspace state.
    state_result = db["user_state"].delete_many(
        {"userId": user_id}
    )
    deletion_counts["user_state"] = state_result.deleted_count

    # Remove the account itself.
    user_result = users.delete_one({"id": user_id})

    if user_result.deleted_count != 1:
        return _error(
            "The user account could not be deleted.",
            500,
        )

    # Keep the audit record even after deleting the account.
    _audit(
        actor,
        "user.deleted",
        user_id,
        {
            "deletedEmail": target.get("email", ""),
            "deletedName": target.get("name", ""),
            "deletedRole": normalize_role(target.get("role")),
            "deletionCounts": deletion_counts,
        },
    )

    return ok(
        {
            "deletedUserId": user_id,
            "deletionCounts": deletion_counts,
        },
        "User account and associated data deleted successfully.",
    )


@router.get("/audit-logs")
def list_audit_logs(request: Request):
    actor, error = _admin_user(request)

    if error:
        return error

    logs = list(
        get_db()["audit_logs"]
        .find({}, {"_id": 0})
        .sort("createdAt", -1)
        .limit(100)
    )

    return ok(
        {"logs": logs},
        "Audit logs retrieved.",
    )
