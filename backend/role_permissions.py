"""Role-based authorization for the Stratov API.

Authentication remains session-based. This middleware adds server-side
permissions without changing the existing route handlers or ownership rules.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


ROLE_ALIASES = {
    "admin": "Admin",
    "administrator": "Admin",
    "product manager": "Product Manager",
    "senior product manager": "Product Manager",
    "product owner": "Product Manager",
    "product lead": "Product Manager",
    "analyst": "Executive",
    "executive": "Executive",
    "developer": "Developer",
}

ROLES = ("Admin", "Product Manager", "Developer", "Executive")


def normalize_role(value):
    """Normalize legacy role labels into the supported RBAC roles."""
    if not isinstance(value, str):
        return "Developer"
    return ROLE_ALIASES.get(value.strip().lower(), "Developer")


def _json_error(status_code, message):
    return JSONResponse(
        status_code=status_code,
        content={"success": False, "data": None, "message": message},
    )


class RoleAccessMiddleware(BaseHTTPMiddleware):
    """Enforce role policy for API writes; route handlers still enforce login."""

    async def dispatch(self, request, call_next):
        path = request.url.path
        method = request.method.upper()

        # The admin API performs its own authentication and admin checks.
        if not path.startswith("/api/") or path.startswith("/api/auth/"):
            return await call_next(request)

        user_id = request.session.get("user_id")
        if not user_id:
            return await call_next(request)

        try:
            from db import get_db
            user = get_db()["users"].find_one(
                {"id": user_id}, {"role": 1, "isActive": 1, "_id": 0}
            )
        except Exception:
            # Let the route's normal database handling report connection errors.
            return await call_next(request)

        if not user or user.get("isActive", True) is False:
            request.session.clear()
            return _json_error(401, "Your account is unavailable. Please sign in again.")

        role = normalize_role(user.get("role"))
        if role == "Admin" or method in {"GET", "HEAD", "OPTIONS"}:
            return await call_next(request)

        # Product Managers can manage product work. Admin-only operations are
        # isolated under /api/admin and are never granted here.
        if role == "Product Manager":
            return await call_next(request)

        # Developers can update delivery artifacts, but cannot administer users
        # or mutate feedback, analysis, product strategy, or account settings.
        if role == "Developer":
            developer_write_prefixes = ("/api/roadmap", "/api/features")
            if method in {"PUT", "PATCH"} and path.startswith(developer_write_prefixes):
                return await call_next(request)

        # Executives are read-only. Developers are also read-only outside the
        # explicitly allowed delivery endpoints above.
        return _json_error(403, f"Your {role} role does not have permission to perform this action.")
