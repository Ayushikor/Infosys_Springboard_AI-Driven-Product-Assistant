"""``features`` collection (RICE prioritisation). Rules mirror ``helpers.normalize_feature``."""

from ._validation import document_validator, optional_number, optional_str, require_str

COLLECTION = "features"

FIELDS = {
    "id": "str, required. 'ft-' + 10 hex chars. Unique per user.",
    "userId": "str, required. References users.id.",
    "name": "str, required, non-empty.",
    "theme": "str, optional. Defaults to 'Uncategorized'.",
    "reach": "number >= 0, optional.",
    "impact": "number 0.25-3, optional.",
    "confidence": "number 0-1, optional.",
    "effort": "number >= 0.1, optional.",
    "status": "str, optional. Defaults to 'Backlog'.",
    "description": "str, optional.",
}

EXAMPLE = {
    "id": "ft-5a4b3c2d1e",
    "userId": "usr-1a2b3c4d5e",
    "name": "Faster dashboard load",
    "theme": "Performance",
    "reach": 1200,
    "impact": 2,
    "confidence": 0.8,
    "effort": 3,
    "status": "Backlog",
    "description": "Cache dashboard queries.",
}


@document_validator
def validate_feature(doc, errors):
    require_str(doc, "id", errors)
    require_str(doc, "userId", errors)
    require_str(doc, "name", errors)
    optional_str(doc, "theme", errors)
    optional_str(doc, "status", errors)
    optional_str(doc, "description", errors)
    optional_number(doc, "reach", errors, minimum=0)
    optional_number(doc, "impact", errors, minimum=0.25, maximum=3)
    optional_number(doc, "confidence", errors, minimum=0, maximum=1)
    optional_number(doc, "effort", errors, minimum=0.1)
