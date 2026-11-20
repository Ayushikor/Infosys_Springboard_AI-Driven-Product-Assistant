"""Schema and validator for individual AI analysis batches."""

from ._validation import (
    document_validator,
    optional_dict,
    optional_iso,
    optional_list_of_str,
    optional_number,
    optional_str,
    require_str,
)

COLLECTION = "analysis_batches"

FIELDS = {
    "id": "str, required. Unique batch document identifier.",
    "run_id": "str, required. Parent analysis run identifier.",
    "userId": "str, required. Owner of the parent run.",
    "workspaceId": "str, optional.",
    "batch_index": "number >= 1.",
    "record_count": "number >= 0.",
    "feedback_ids": "list of strings.",
    "status": "str, required.",
    "success": "bool, optional.",
    "agent_status": "object, optional.",
    "errors": "object, optional.",
    "results": "object, optional.",
    "token_usage": "object, optional.",
    "createdAt": "ISO-8601 timestamp, optional.",
    "updatedAt": "ISO-8601 timestamp, optional.",
}

EXAMPLE = {
    "id": "analysis-example-batch-1",
    "run_id": "analysis-example",
    "userId": "usr-example",
    "workspaceId": "ws-example",
    "batch_index": 1,
    "record_count": 200,
    "feedback_ids": ["FB-001", "FB-002"],
    "status": "completed",
    "success": True,
    "agent_status": {"themes": "completed"},
    "errors": {},
    "results": {"themes": {"themes": []}},
    "token_usage": {"total_tokens": 20000},
    "createdAt": "2026-11-19T10:00:00+00:00",
    "updatedAt": "2026-11-19T10:05:00+00:00",
}


@document_validator
def validate_analysis_batch(doc, errors):
    require_str(doc, "id", errors)
    require_str(doc, "run_id", errors)
    require_str(doc, "userId", errors)
    require_str(doc, "status", errors)

    optional_str(doc, "workspaceId", errors)
    optional_number(doc, "batch_index", errors, minimum=1)
    optional_number(doc, "record_count", errors, minimum=0)
    optional_list_of_str(doc, "feedback_ids", errors)

    for field in ("agent_status", "errors", "results", "token_usage"):
        if doc.get(field) is not None:
            optional_dict(doc, field, errors)

    if doc.get("success") is not None and not isinstance(
        doc["success"], bool
    ):
        errors.append("success: must be a boolean")

    for field in ("createdAt", "updatedAt"):
        if doc.get(field) is not None:
            optional_iso(doc, field, errors)