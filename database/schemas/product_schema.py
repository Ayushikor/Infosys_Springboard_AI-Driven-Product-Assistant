"""``products`` collection (``routes/product_routes.py``).

Products created while logged out have no userId and act as a shared catalog.
"""

from ._validation import (
    document_validator, optional_dict, optional_iso, optional_list_of_str,
    optional_str, require_str,
)

COLLECTION = "products"

FIELDS = {
    "id": "str, required. 'prod-' + 10 hex chars. Unique across the collection.",
    "userId": "str, optional. References users.id; absent for shared catalog products.",
    "name": "str, required, non-empty.",
    "description": "str, optional.",
    "category": "str, optional. Defaults to 'General'.",
    "status": "str, optional. Defaults to 'Active'.",
    "tags": "list[str], optional.",
    "attributes": "object, optional. Free-form key/values.",
    "createdAt": "str, optional. ISO-8601 UTC timestamp.",
    "updatedAt": "str, optional. ISO-8601 UTC timestamp.",
}

EXAMPLE = {
    "id": "prod-7a6b5c4d3e",
    "name": "Analytics Dashboard",
    "description": "Customer-facing reporting.",
    "category": "General",
    "status": "Active",
    "tags": ["analytics", "reports"],
    "attributes": {},
    "createdAt": "2026-01-10T08:00:00.000000+00:00",
    "updatedAt": "2026-01-10T08:00:00.000000+00:00",
}


@document_validator
def validate_product(doc, errors):
    require_str(doc, "id", errors)
    require_str(doc, "name", errors)
    for field in ("userId", "description", "category", "status"):
        optional_str(doc, field, errors)
    optional_list_of_str(doc, "tags", errors)
    optional_dict(doc, "attributes", errors)
    optional_iso(doc, "createdAt", errors)
    optional_iso(doc, "updatedAt", errors)
