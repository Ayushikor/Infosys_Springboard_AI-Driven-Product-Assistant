"""``feedback`` collection. Rules mirror ``helpers.normalize_feedback``."""

from ._validation import (
    document_validator, optional_enum, optional_iso, optional_number,
    optional_str, require_str,
)

COLLECTION = "feedback"

# Mirrors helpers.VALID_SENTIMENTS (duplicated to avoid importing backend code).
VALID_SENTIMENTS = {"positive", "neutral", "negative"}

FIELDS = {
    "id": "str, required. 'fb-' + 10 hex chars (or client-supplied on import). Unique per user.",
    "userId": "str, required. References users.id.",
    "title": "str, required, non-empty.",
    "message": "str, required, non-empty.",
    "customer": "str, optional. Defaults to 'Unknown'.",
    "source": "str, optional. Defaults to 'Manual'.",
    "sentiment": "str, optional. One of positive / neutral / negative.",
    "theme": "str, optional. Theme name; defaults to 'Uncategorized'. Not enforced as a reference.",
    "votes": "int >= 0, optional.",
    "createdAt": "str, optional. ISO-8601 timestamp; kept if valid, otherwise set to now.",
}

EXAMPLE = {
    "id": "fb-9f8e7d6c5b",
    "userId": "usr-1a2b3c4d5e",
    "title": "App is slow on startup",
    "message": "Takes about 10 seconds to load the dashboard.",
    "customer": "Customer A",
    "source": "Manual",
    "sentiment": "negative",
    "theme": "Performance",
    "votes": 3,
    "createdAt": "2026-02-01T12:00:00.000000+00:00",
}


@document_validator
def validate_feedback(doc, errors):
    require_str(doc, "id", errors)
    require_str(doc, "userId", errors)
    require_str(doc, "title", errors)
    require_str(doc, "message", errors)
    optional_str(doc, "customer", errors)
    optional_str(doc, "source", errors)
    optional_str(doc, "theme", errors)
    optional_enum(doc, "sentiment", VALID_SENTIMENTS, errors)
    optional_number(doc, "votes", errors, minimum=0)
    optional_iso(doc, "createdAt", errors)
