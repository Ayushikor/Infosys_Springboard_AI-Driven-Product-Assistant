"""``roadmap`` collection (``routes/roadmap_routes.py``). No timestamps are stored."""

from ._validation import (
    document_validator, optional_date_or_empty, optional_str, require_str,
)

COLLECTION = "roadmap"

FIELDS = {
    "id": "str, required. 'rm-' + 10 hex chars. Unique per user.",
    "userId": "str, required. References users.id.",
    "name": "str, required, non-empty.",
    "featureId": "str, optional. Soft reference to features.id; '' means none.",
    "startDate": "str, optional. '' or YYYY-MM-DD.",
    "targetDate": "str, optional. '' or YYYY-MM-DD; must not be before startDate.",
    "priority": "str, optional. Defaults to 'Medium'.",
    "status": "str, optional. Defaults to 'Planned'.",
    "owner": "str, optional. Defaults to 'Unassigned'.",
    "theme": "str, optional. Free text.",
}

EXAMPLE = {
    "id": "rm-6a5b4c3d2e",
    "userId": "usr-1a2b3c4d5e",
    "featureId": "ft-5a4b3c2d1e",
    "name": "Dashboard performance work",
    "startDate": "2026-03-01",
    "targetDate": "2026-04-15",
    "priority": "High",
    "status": "Planned",
    "owner": "Unassigned",
    "theme": "Performance",
}


@document_validator
def validate_roadmap(doc, errors):
    require_str(doc, "id", errors)
    require_str(doc, "userId", errors)
    require_str(doc, "name", errors)
    for field in ("featureId", "priority", "status", "owner", "theme"):
        optional_str(doc, field, errors)
    optional_date_or_empty(doc, "startDate", errors)
    optional_date_or_empty(doc, "targetDate", errors)
    start, target = doc.get("startDate", ""), doc.get("targetDate", "")
    if start and target and isinstance(start, str) and isinstance(target, str) and target < start:
        errors.append("targetDate: cannot be before startDate")
