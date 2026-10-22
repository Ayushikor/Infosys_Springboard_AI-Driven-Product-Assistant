"""Authentication routes using FastAPI and session-based authentication."""

import re

import bcrypt
from fastapi import APIRouter, Request, Body
from fastapi.responses import JSONResponse

from db import get_db
from helpers import ok, fail, generate_id, now_iso

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


def _error_response(message, data=None, status_code=400):
    """Convert the existing Flask-style fail() result to an HTTP response."""
    body, status = fail(message, data, status=status_code)
    return JSONResponse(content=body, status_code=status)


def _sanitize_user(doc):
    """Return only the user fields expected by the frontend."""
    return {
        "id": doc["id"],
        "username": doc["username"],
        "email": doc["email"],
        "name": doc["name"],
        "role": doc.get("role", "Product Manager"),
        "createdAt": doc.get("createdAt", ""),
    }


def _validate_email(email):
    """Validate the basic format of an email address."""
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def _validate_password(password):
    """Check password requirements."""
    if len(password) < 8:
        return "Password must be at least 8 characters."

    if not re.search(r"[A-Z]", password):
        return "Password must include an uppercase letter."

    if not re.search(r"[a-z]", password):
        return "Password must include a lowercase letter."

    if not re.search(r"[0-9]", password):
        return "Password must include a number."

    return None


def _seed_empty_user_data(user_id, name):
    """Create a default workspace, themes, and user state for a new user."""
    db = get_db()

    workspace_id = generate_id("ws-")
    first_name = name.split()[0] if name.split() else "User"

    workspace = {
        "id": workspace_id,
        "userId": user_id,
        "name": f"{first_name}'s Workspace",
        "description": "Describe what this workspace is for.",
        "createdAt": now_iso(),
    }

    db["workspaces"].insert_one(workspace)

    db["user_state"].insert_one(
        {
            "userId": user_id,
            "activeWorkspaceId": workspace_id,
            "preferences": {
                "theme": "light",
                "compactTables": False,
            },
        }
    )

    default_themes = [
        {
            "id": "th-ux",
            "userId": user_id,
            "name": "User Experience",
            "keywords": [
                "ux",
                "confusing",
                "navigation",
                "layout",
                "intuitive",
                "design",
                "settings",
                "onboarding",
                "dark mode",
            ],
            "description": (
                "Usability, navigation and clarity of the interface."
            ),
        },
        {
            "id": "th-perf",
            "userId": user_id,
            "name": "Performance",
            "keywords": [
                "slow",
                "loading",
                "lag",
                "timeout",
                "speed",
                "freeze",
                "fast",
                "times out",
            ],
            "description": (
                "Load times, responsiveness and stability."
            ),
        },
        {
            "id": "th-auth",
            "userId": user_id,
            "name": "Authentication and Security",
            "keywords": [
                "login",
                "password",
                "2fa",
                "security",
                "sso",
                "permission",
                "access",
                "saml",
            ],
            "description": (
                "Sign-in, access control and account safety."
            ),
        },
        {
            "id": "th-reports",
            "userId": user_id,
            "name": "Reporting and Analytics",
            "keywords": [
                "report",
                "analytics",
                "export",
                "chart",
                "dashboard",
                "metrics",
                "filter",
            ],
            "description": (
                "Dashboards, reports, and data exports."
            ),
        },
        {
            "id": "th-integ",
            "userId": user_id,
            "name": "Integrations",
            "keywords": [
                "slack",
                "integration",
                "api",
                "webhook",
                "jira",
                "zapier",
                "connect",
                "sync",
            ],
            "description": (
                "Third-party tools and API connectivity."
            ),
        },
        {
            "id": "th-mobile",
            "userId": user_id,
            "name": "Mobile Experience",
            "keywords": [
                "mobile",
                "android",
                "ios",
                "phone",
                "notification",
                "tablet",
                "push",
            ],
            "description": (
                "Mobile app quality and push notifications."
            ),
        },
        {
            "id": "th-billing",
            "userId": user_id,
            "name": "Billing",
            "keywords": [
                "invoice",
                "billing",
                "price",
                "pricing",
                "charge",
                "refund",
                "subscription",
                "payment",
                "vat",
                "tax",
            ],
            "description": (
                "Pricing, invoices, and payment issues."
            ),
        },
    ]

    db["themes"].insert_many(default_themes)


@router.post("/login")
def login(
    request: Request,
    body: dict | None = Body(default=None),
):
    """Authenticate a user and create a session."""
    body = body or {}

    email = body.get("email") or ""
    password = body.get("password") or ""

    if not isinstance(email, str):
        return _error_response("Enter a valid email address.")

    if not isinstance(password, str):
        return _error_response("Password is required.")

    email = email.strip().lower()

    if not _validate_email(email):
        return _error_response("Enter a valid email address.")

    if not password:
        return _error_response("Password is required.")

    user = get_db()["users"].find_one({"email": email})

    if not user:
        return _error_response(
            "No account found with that email. Please register first."
        )

    password_hash = user.get("passwordHash", "")

    try:
        password_matches = bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except (ValueError, TypeError, AttributeError):
        password_matches = False

    if not password_matches:
        return _error_response("Incorrect password.")

    request.session["user_id"] = user["id"]

    return ok(
        {"user": _sanitize_user(user)},
        "Logged in successfully",
    )


@router.post("/register")
def register(
    request: Request,
    body: dict | None = Body(default=None),
):
    """Register a new user."""
    body = body or {}

    name = body.get("name") or ""
    username = body.get("username") or ""
    email = body.get("email") or ""
    password = body.get("password") or ""
    confirm = body.get("confirmPassword") or ""
    role = body.get("role") or "Product Manager"

    errors = {}

    if not isinstance(name, str) or len(name.strip()) < 2:
        errors["name"] = "Full name must be at least 2 characters."
    else:
        name = name.strip()

    if not isinstance(username, str):
        username = ""

    username = username.strip()

    if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
        errors["username"] = (
            "Username: 3-20 letters, numbers or underscores."
        )

    if not isinstance(email, str):
        email = ""

    email = email.strip().lower()

    if not _validate_email(email):
        errors["email"] = "Enter a valid email address."

    if not isinstance(password, str):
        password = ""

    if not isinstance(confirm, str):
        confirm = ""

    password_error = _validate_password(password)

    if password_error:
        errors["password"] = password_error

    if password != confirm:
        errors["confirmPassword"] = "Passwords do not match."

    if errors:
        return _error_response(
            "Please fix the highlighted fields.",
            {"errors": errors},
        )

    users = get_db()["users"]

    if users.find_one({"email": email}):
        return _error_response(
            "Email already registered.",
            {"errors": {"email": "This email is already registered."}},
        )

    existing_username = users.find_one(
        {
            "username": {
                "$regex": f"^{re.escape(username)}$",
                "$options": "i",
            }
        }
    )

    if existing_username:
        return _error_response(
            "Username taken.",
            {"errors": {"username": "This username is taken."}},
        )

    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(),
    ).decode("utf-8")

    user_id = generate_id("usr-")

    user_doc = {
        "id": user_id,
        "username": username,
        "email": email,
        "name": name,
        "role": role if isinstance(role, str) else "Product Manager",
        "createdAt": now_iso(),
        "passwordHash": hashed_password,
    }

    users.insert_one(user_doc)

    _seed_empty_user_data(user_id, name)

    return ok(
        {"user": _sanitize_user(user_doc)},
        "Account created. You can now sign in.",
    )


@router.post("/logout")
def logout(request: Request):
    """Log out the current user."""
    request.session.pop("user_id", None)

    return ok(None, "Logged out")