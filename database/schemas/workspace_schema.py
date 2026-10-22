"""``workspaces`` collection (``routes/workspace_routes.py``, seeded at registration)."""

from ._validation import document_validator, optional_iso, optional_str, require_str

COLLECTION = "workspaces"

FIELDS = {
    "id": "str, required. 'ws-' + 10 hex chars. Unique per user.",
    "userId": "str, required. References users.id.",
    "name": "str, required. At least 2 characters.",
    "description": "str, optional. May be empty.",
    "createdAt": "str, optional. ISO-8601 UTC timestamp. There is no updatedAt.",
}

EXAMPLE = {
    "id": "ws-0a1b2c3d4e",
    "userId": "usr-1a2b3c4d5e",
    "name": "Jane's Workspace",
    "description": "Describe what this workspace is for.",
    "createdAt": "2026-01-15T09:30:00.000000+00:00",
}


@document_validator
def validate_workspace(doc, errors):
    require_str(doc, "id", errors)
    require_str(doc, "userId", errors)
    require_str(doc, "name", errors, min_len=2)
    optional_str(doc, "description", errors)
    optional_iso(doc, "createdAt", errors)
