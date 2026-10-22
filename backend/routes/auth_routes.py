"""Authentication routes.

Simple session-based auth using bcrypt password hashing.
The user collection stores: id, username, email, name, role, createdAt,
passwordHash (bcrypt).
"""

import re
from flask import Blueprint, request, session
from db import get_db
from helpers import ok, fail, generate_id, now_iso

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")


def _sanitize_user(doc):
    """Return only the fields the frontend expects."""
    return {
        "id": doc["id"],
        "username": doc["username"],
        "email": doc["email"],
        "name": doc["name"],
        "role": doc.get("role", "Product Manager"),
        "createdAt": doc.get("createdAt", ""),
    }


def _validate_email(email):
    return bool(re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email))


def _validate_password(pw):
    if len(pw) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r"[A-Z]", pw):
        return "Password must include an uppercase letter."
    if not re.search(r"[a-z]", pw):
        return "Password must include a lowercase letter."
    if not re.search(r"[0-9]", pw):
        return "Password must include a number."
    return None


@auth_bp.route("/login", methods=["POST"])
def login():
    import bcrypt

    body = request.get_json(silent=True) or {}
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""

    if not _validate_email(email):
        return fail("Enter a valid email address.")
    if not password:
        return fail("Password is required.")

    users = get_db()["users"]
    user = users.find_one({"email": email})
    if not user:
        return fail("No account found with that email. Please register first.")

    if not bcrypt.checkpw(
        password.encode("utf-8"), user["passwordHash"].encode("utf-8")
    ):
        return fail("Incorrect password.")

    session["user_id"] = user["id"]
    return ok({"user": _sanitize_user(user)}, "Logged in successfully")


@auth_bp.route("/register", methods=["POST"])
def register():
    import bcrypt

    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip().lower()
    password = body.get("password") or ""
    confirm = body.get("confirmPassword") or ""
    role = body.get("role") or "Product Manager"

    errors = {}
    if not name or len(name) < 2:
        errors["name"] = "Full name must be at least 2 characters."
    if not re.match(r"^[a-zA-Z0-9_]{3,20}$", username):
        errors["username"] = "Username: 3-20 letters, numbers or underscores."
    if not _validate_email(email):
        errors["email"] = "Enter a valid email address."
    pw_err = _validate_password(password)
    if pw_err:
        errors["password"] = pw_err
    if password != confirm:
        errors["confirmPassword"] = "Passwords do not match."

    if errors:
        return fail("Please fix the highlighted fields.", {"errors": errors})

    users = get_db()["users"]
    if users.find_one({"email": email}):
        return fail(
            "Email already registered.",
            {"errors": {"email": "This email is already registered."}},
        )
    if users.find_one(
        {"username": {"$regex": f"^{re.escape(username)}$", "$options": "i"}}
    ):
        return fail(
            "Username taken.",
            {"errors": {"username": "This username is taken."}},
        )

    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    user_id = generate_id("usr-")
    user_doc = {
        "id": user_id,
        "username": username,
        "email": email,
        "name": name,
        "role": role,
        "createdAt": now_iso(),
        "passwordHash": hashed,
    }
    users.insert_one(user_doc)

    # Create default user data
    _seed_empty_user_data(user_id, name)

    return ok(
        {"user": _sanitize_user(user_doc)},
        "Account created. You can now sign in.",
    )


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.pop("user_id", None)
    return ok(None, "Logged out")


def _seed_empty_user_data(user_id, name):
    """Create default workspace, themes and user_state for a new user."""
    db = get_db()
    ws_id = generate_id("ws-")
    workspace = {
        "id": ws_id,
        "userId": user_id,
        "name": f"{name.split(' ')[0]}'s Workspace",
        "description": "Describe what this workspace is for.",
        "createdAt": now_iso(),
    }
    db["workspaces"].insert_one(workspace)

    db["user_state"].insert_one(
        {
            "userId": user_id,
            "activeWorkspaceId": ws_id,
            "preferences": {"theme": "light", "compactTables": False},
        }
    )

    # Seed default themes (same as the frontend mock data)
    default_themes = [
        {"id": "th-ux", "userId": user_id, "name": "User Experience", "keywords": ["ux", "confusing", "navigation", "layout", "intuitive", "design", "settings", "onboarding", "dark mode"], "description": "Usability, navigation and clarity of the interface."},
        {"id": "th-perf", "userId": user_id, "name": "Performance", "keywords": ["slow", "loading", "lag", "timeout", "speed", "freeze", "fast", "times out"], "description": "Load times, responsiveness and stability."},
        {"id": "th-auth", "userId": user_id, "name": "Authentication and Security", "keywords": ["login", "password", "2fa", "security", "sso", "permission", "access", "saml"], "description": "Sign-in, access control and account safety."},
        {"id": "th-reports", "userId": user_id, "name": "Reporting and Analytics", "keywords": ["report", "analytics", "export", "chart", "dashboard", "metrics", "filter"], "description": "Dashboards, reports, and data exports."},
        {"id": "th-integ", "userId": user_id, "name": "Integrations", "keywords": ["slack", "integration", "api", "webhook", "jira", "zapier", "connect", "sync"], "description": "Third-party tools and API connectivity."},
        {"id": "th-mobile", "userId": user_id, "name": "Mobile Experience", "keywords": ["mobile", "android", "ios", "phone", "notification", "tablet", "push"], "description": "Mobile app quality and push notifications."},
        {"id": "th-billing", "userId": user_id, "name": "Billing", "keywords": ["invoice", "billing", "price", "pricing", "charge", "refund", "subscription", "payment", "vat", "tax"], "description": "Pricing, invoices, and payment issues."},
    ]
    db["themes"].insert_many(default_themes)
