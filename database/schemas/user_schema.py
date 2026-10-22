"""``users`` collection (written by ``routes/auth_routes.py``)."""

import re

from ._validation import document_validator, optional_iso, optional_str, require_str

COLLECTION = "users"

FIELDS = {
    "id": "str, required. App id, 'usr-' + 10 hex chars. Unique.",
    "username": "str, required. 3-20 letters, digits or underscores. Unique, case-insensitive.",
    "email": "str, required. Stored lowercased. Unique.",
    "name": "str, required. At least 2 characters.",
    "role": "str, optional. Defaults to 'Product Manager' in the API.",
    "createdAt": "str, optional. ISO-8601 UTC timestamp.",
    "passwordHash": "str, required. bcrypt hash; never returned by the API.",
}

EXAMPLE = {
    "id": "usr-1a2b3c4d5e",
    "username": "jane_doe",
    "email": "jane@example.com",
    "name": "Jane Doe",
    "role": "Product Manager",
    "createdAt": "2026-01-15T09:30:00.000000+00:00",
    "passwordHash": "<bcrypt hash>",
}

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,20}$")


@document_validator
def validate_user(doc, errors):
    require_str(doc, "id", errors)
    require_str(doc, "name", errors, min_len=2)
    require_str(doc, "passwordHash", errors)
    if not isinstance(doc.get("username"), str) or not _USERNAME_RE.match(doc["username"]):
        errors.append("username: 3-20 letters, numbers or underscores")
    email = doc.get("email")
    if not isinstance(email, str) or not re.match(r"^[^\s@]+@[^\s@]+\.[^\s@]+$", email):
        errors.append("email: must be a valid email address")
    elif email != email.lower():
        errors.append("email: must be stored lowercase")
    optional_str(doc, "role", errors)
    optional_iso(doc, "createdAt", errors)
