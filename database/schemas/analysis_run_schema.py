"""Schema and validator for persisted AI analysis runs."""

from ._validation import (
    document_validator,
    optional_dict,
    optional_iso,
    optional_list_of_str,
    optional_number,
    optional_str,
    require_str,
)

COLLECTION = "analysis_runs"

FIELDS = {
    "id": "str, required. Unique analysis run identifier.",
    "userId": "str, required. References users.id.",
    "workspaceId": "str, optional. References workspaces.id.",
    "status": "str, required. Pipeline execution status.",
    "success": "bool, optional.",
    "input_source": "str, optional. mongodb or local_json.",
    "input_record_count": "number >= 0, optional.",
    "total_feedback_analyzed": "number >= 0, optional.",
    "source_counts": "object, optional.",
    "agent_status": "object, optional.",
    "errors": "object, optional.",
    "results": "object, optional.",
    "token_usage": "object, optional.",
    "execution_order": "list of strings, optional.",
    "data_flow": "object, optional.",
    "createdAt": "ISO-8601 timestamp, optional.",
    "updatedAt": "ISO-8601 timestamp, optional.",
    "startedAt": "ISO-8601 timestamp, optional.",
    "completedAt": "ISO-8601 timestamp, optional.",
}

EXAMPLE = {
    "id": "analysis-ff6e76c744",
    "userId": "usr-1a2b3c4d5e",
    "workspaceId": "ws-example",
    "status": "completed",
    "success": True,
    "input_source": "mongodb",
    "input_record_count": 300,
    "total_feedback_analyzed": 300,
    "source_counts": {
        "customer_feedback": 100,
        "user_reviews": 100,
        "support_tickets": 100,
    },
    "agent_status": {
        "themes": "completed",
        "pain_points": "completed",
        "feature_clusters": "completed",
        "trends": "completed",
    },
    "errors": {},
    "results": {
        "themes": {},
        "pain_points": {},
        "feature_clusters": {},
        "trends": {},
    },
    "token_usage": {
        "total_tokens": 100419,
    },
    "execution_order": [
        "Agent 1 - Theme Extraction",
        "Agent 2 - Pain Point Identification",
        "Agent 3 - Feature Clustering",
        "Agent 4 - Trend Analysis",
    ],
    "data_flow": {},
    "createdAt": "2026-11-19T10:00:00.000000+00:00",
    "updatedAt": "2026-11-19T10:30:00.000000+00:00",
}


@document_validator
def validate_analysis_run(doc, errors):
    """Validate an analysis run document."""

    require_str(doc, "id", errors)
    require_str(doc, "userId", errors)
    require_str(doc, "status", errors)

    optional_str(doc, "workspaceId", errors)
    optional_str(doc, "input_source", errors)

    optional_number(
        doc,
        "input_record_count",
        errors,
        minimum=0,
    )

    optional_number(
        doc,
        "total_feedback_analyzed",
        errors,
        minimum=0,
    )

    for field in (
        "source_counts",
        "agent_status",
        "errors",
        "results",
        "token_usage",
        "data_flow",
    ):
        if doc.get(field) is not None:
            optional_dict(doc, field, errors)

    if doc.get("execution_order") is not None:
        optional_list_of_str(
            doc,
            "execution_order",
            errors,
        )

    if doc.get("success") is not None:
        if not isinstance(doc["success"], bool):
            errors.append("success: must be a boolean")

    for field in (
        "createdAt",
        "updatedAt",
        "startedAt",
        "completedAt",
    ):
        if doc.get(field) is not None:
            optional_iso(doc, field, errors)