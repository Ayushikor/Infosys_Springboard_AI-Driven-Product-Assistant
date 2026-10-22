"""``prds`` collection (``routes/prd_routes.py``)."""

from ._validation import document_validator, optional_iso, optional_str, require_str

COLLECTION = "prds"

FIELDS = {
    "id": "str, required. 'prd-' + 10 hex chars. Unique per user.",
    "userId": "str, required. References users.id.",
    "title": "str, required, non-empty.",
    "featureId": "str, optional. Soft reference to features.id; '' means none. Not cleaned up on delete.",
    "version": "str, optional. Defaults to '0.1'.",
    "status": "str, optional. Defaults to 'Draft'. Any string is accepted today.",
    "createdAt": "str, optional. ISO-8601 UTC timestamp.",
    "updatedAt": "str, optional. ISO-8601 UTC timestamp, set on every update.",
    "content": "any JSON value or null, as sent by the frontend editor.",
}

EXAMPLE = {
    "id": "prd-1f2e3d4c5b",
    "userId": "usr-1a2b3c4d5e",
    "title": "Faster dashboard PRD",
    "featureId": "ft-5a4b3c2d1e",
    "version": "0.1",
    "status": "Draft",
    "createdAt": "2026-02-02T10:00:00.000000+00:00",
    "updatedAt": "2026-02-02T10:00:00.000000+00:00",
    "content": None,
}


@document_validator
def validate_prd(doc, errors):
    require_str(doc, "id", errors)
    require_str(doc, "userId", errors)
    require_str(doc, "title", errors)
    optional_str(doc, "featureId", errors)
    optional_str(doc, "version", errors)
    optional_str(doc, "status", errors)
    optional_iso(doc, "createdAt", errors)
    optional_iso(doc, "updatedAt", errors)
