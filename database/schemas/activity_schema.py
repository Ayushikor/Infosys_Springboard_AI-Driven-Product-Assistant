"""``activity`` collection: append-only log written by the CRUD routes."""

from ._validation import document_validator, optional_iso, require_str

COLLECTION = "activity"

FIELDS = {
    "id": "str, required. 'act-' + 10 hex chars.",
    "userId": "str, required. References users.id.",
    "text": "str, required. Human-readable event, e.g. 'Feature \"X\" added'.",
    "at": "str, required. ISO-8601 UTC timestamp; the API sorts on it.",
}

EXAMPLE = {
    "id": "act-4d3c2b1a0f",
    "userId": "usr-1a2b3c4d5e",
    "text": 'Feature "Faster dashboard load" added',
    "at": "2026-02-02T10:05:00.000000+00:00",
}


@document_validator
def validate_activity(doc, errors):
    require_str(doc, "id", errors)
    require_str(doc, "userId", errors)
    require_str(doc, "text", errors)
    require_str(doc, "at", errors)
    optional_iso(doc, "at", errors)
