"""Shared helpers for API routes."""

import uuid
from datetime import datetime, timezone


def ok(data, message="Operation completed successfully"):
    """Standard success envelope matching the frontend contract."""
    return {"success": True, "data": data, "message": message}


def fail(message, data=None, status=400):
    """Standard error envelope.  Returns (body, status_code)."""
    return {"success": False, "data": data, "message": message}, status


def generate_id(prefix=""):
    """Generate a short unique id, optionally prefixed (e.g. 'fb-')."""
    short = uuid.uuid4().hex[:10]
    return f"{prefix}{short}" if prefix else short


def now_iso():
    """Current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


def mongo_doc_to_dict(doc):
    """Convert a MongoDB document to a JSON-safe dict by stringifying _id."""
    if doc is None:
        return None
    doc = dict(doc)
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc


def mongo_docs_to_list(cursor):
    """Convert a MongoDB cursor to a list of JSON-safe dicts."""
    return [mongo_doc_to_dict(d) for d in cursor]


VALID_SENTIMENTS = {"positive", "neutral", "negative"}


def normalize_feedback(data, existing=None):
    """Validate and normalise a feedback record's fields.

    Returns (record_dict, None) on success or (None, error_string) on failure.
    """
    base = dict(existing) if existing else {}
    base.update(data)

    title = str(base.get("title", "")).strip()
    message = str(base.get("message", "")).strip()

    if not title:
        return None, "Title is required."
    if not message:
        return None, "Message is required."

    sentiment = str(base.get("sentiment", "neutral")).lower()
    if sentiment not in VALID_SENTIMENTS:
        sentiment = "neutral"

    votes = base.get("votes", 0)
    try:
        votes = max(0, round(float(votes)))
    except (TypeError, ValueError):
        votes = 0

    record = {
        "title": title,
        "message": message,
        "customer": str(base.get("customer", "Unknown")).strip() or "Unknown",
        "source": str(base.get("source", "Manual")).strip() or "Manual",
        "sentiment": sentiment,
        "theme": str(base.get("theme", "Uncategorized")).strip() or "Uncategorized",
        "votes": votes,
    }

    # Preserve or set createdAt
    created = base.get("createdAt")
    if created:
        try:
            datetime.fromisoformat(str(created).replace("Z", "+00:00"))
            record["createdAt"] = str(created)
        except ValueError:
            record["createdAt"] = now_iso()
    else:
        record["createdAt"] = now_iso()

    return record, None


def normalize_feature(data, existing=None):
    """Validate and normalise a feature record.

    Returns (record_dict, None) on success or (None, error_string) on failure.
    """
    base = dict(existing) if existing else {}
    base.update(data)

    name = str(base.get("name", "")).strip()
    if not name:
        return None, "Feature name is required."

    reach = base.get("reach", 0)
    try:
        reach = max(0, float(reach))
    except (TypeError, ValueError):
        reach = 0

    impact = base.get("impact", 1)
    try:
        impact = min(3, max(0.25, float(impact)))
    except (TypeError, ValueError):
        impact = 1

    confidence = base.get("confidence", 0)
    try:
        confidence = min(1, max(0, float(confidence)))
    except (TypeError, ValueError):
        confidence = 0

    effort = base.get("effort", 1)
    try:
        effort = max(0.1, float(effort))
    except (TypeError, ValueError):
        effort = 1

    return {
        "name": name,
        "theme": base.get("theme", "Uncategorized") or "Uncategorized",
        "reach": reach,
        "impact": impact,
        "confidence": confidence,
        "effort": effort,
        "status": base.get("status", "Backlog") or "Backlog",
        "description": base.get("description", "") or "",
    }, None
