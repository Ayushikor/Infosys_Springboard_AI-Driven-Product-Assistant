"""``themes`` collection (seeded per user at registration; keywords editable)."""

from ._validation import document_validator, optional_list_of_str, optional_str, require_str

COLLECTION = "themes"

FIELDS = {
    "id": "str, required. e.g. 'th-ux'. Unique per user only (every user is seeded with the same ids).",
    "userId": "str, required. References users.id.",
    "name": "str, required.",
    "keywords": "list[str], optional. Edited via PUT /api/themes/<id>/keywords.",
    "description": "str, optional.",
}

EXAMPLE = {
    "id": "th-perf",
    "userId": "usr-1a2b3c4d5e",
    "name": "Performance",
    "keywords": ["slow", "loading", "lag"],
    "description": "Load times, responsiveness and stability.",
}


@document_validator
def validate_theme(doc, errors):
    require_str(doc, "id", errors)
    require_str(doc, "userId", errors)
    require_str(doc, "name", errors)
    optional_list_of_str(doc, "keywords", errors)
    optional_str(doc, "description", errors)
