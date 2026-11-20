
"""Batch execution and deterministic aggregation for large feedback datasets.

The existing four-agent pipeline accepts at most 500 records per invocation.
This module splits larger datasets into smaller batches, invokes that unchanged
pipeline sequentially, and merges its outputs.

Cross-batch matching is exact after case and whitespace normalization.
Semantically similar labels with different names remain separate.
"""

from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any, Callable

logger = logging.getLogger(__name__)

DEFAULT_BATCH_SIZE = 200
MAX_TOTAL_FEEDBACK_RECORDS = 10_000

AGENT_KEYS = (
    "themes",
    "pain_points",
    "feature_clusters",
    "trends",
)

SUCCESS_AGENT_STATUSES = {
    "completed",
    "completed_no_candidates",
}


class BatchAnalysisError(RuntimeError):
    """Raised when a batch run cannot be started safely."""


def _as_dict(value: Any) -> dict:
    if isinstance(value, dict):
        return dict(value)

    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")

    return {}


def _unique(values: list[Any]) -> list[Any]:
    seen = set()
    output = []

    for value in values:
        marker = repr(value)

        if marker not in seen:
            seen.add(marker)
            output.append(value)

    return output


def _normalized_key(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or "").strip()
    ).casefold()


def _merge_text(existing: Any, incoming: Any) -> str:
    values = _unique([
        str(value).strip()
        for value in (existing, incoming)
        if str(value or "").strip()
    ])

    return " / ".join(values)


def _merge_named_items(
    source_lists: list[list[dict]],
    *,
    name_field: str,
    merge_list_fields: tuple[str, ...],
    merge_text_fields: tuple[str, ...] = (),
    key_fields: tuple[str, ...] = (),
) -> list[dict]:

    merged: dict[tuple[str, ...], dict] = {}
    order: list[tuple[str, ...]] = []

    for items in source_lists:
        for raw in items:
            item = _as_dict(raw)
            name = item.get(name_field)

            if not name:
                continue

            key = tuple(
                _normalized_key(item.get(field))
                for field in (name_field, *key_fields)
            )

            if key not in merged:
                merged[key] = item
                order.append(key)

                for field in merge_list_fields:
                    merged[key][field] = list(
                        item.get(field) or []
                    )

            else:
                target = merged[key]

                for field in merge_list_fields:
                    target[field] = _unique(
                        list(target.get(field) or [])
                        + list(item.get(field) or [])
                    )

                for field in merge_text_fields:
                    target[field] = _merge_text(
                        target.get(field),
                        item.get(field),
                    )

                # Keep the most severe known pain-point classification.
                if "severity" in item and "severity" in target:
                    rank = {
                        "unknown": 0,
                        "low": 1,
                        "medium": 2,
                        "high": 3,
                    }

                    left = rank.get(
                        _normalized_key(target.get("severity")), 0
                    )

                    right = rank.get(
                        _normalized_key(item.get("severity")), 0
                    )

                    if right > left:
                        target["severity"] = item["severity"]

    output = []

    for key in order:
        item = merged[key]

        for field in (
            "feedback_ids",
            "evidence",
            "source_channels",
        ):
            if field in item:
                item[field] = _unique(item.get(field) or [])

        if "mention_count" in item and "feedback_ids" in item:
            item["mention_count"] = len(item["feedback_ids"])

        output.append(item)

    return output


def _merge_themes(
    items: list[dict],
    total_records: int,
) -> dict | None:

    available = [
        item for item in items
        if isinstance(item, dict)
    ]

    if not available:
        return None

    themes = _merge_named_items(
        [
            list(item.get("themes") or [])
            for item in available
        ],
        name_field="name",
        merge_list_fields=(
            "keywords",
            "feedback_ids",
        ),
        merge_text_fields=("description",),
    )

    return {
        "total_feedback_analyzed": total_records,
        "themes": themes,
    }


def _merge_pain_points(
    items: list[dict],
    total_records: int,
) -> dict | None:

    available = [
        item for item in items
        if isinstance(item, dict)
    ]

    if not available:
        return None

    pain_points = _merge_named_items(
        [
            list(item.get("pain_points") or [])
            for item in available
        ],
        name_field="name",
        key_fields=("category",),
        merge_list_fields=(
            "feedback_ids",
            "evidence",
        ),
        merge_text_fields=("description",),
    )

    output: dict[str, Any] = {
        "total_feedback_analyzed": total_records,
        "pain_points": pain_points,
    }

    for field in (
        "feature_request_feedback_ids",
        "non_pain_feedback_ids",
        "uncertain_feedback_ids",
        "unclassified_feedback_ids",
    ):
        values = []

        for item in available:
            values.extend(item.get(field) or [])

        if values or any(field in item for item in available):
            output[field] = _unique(values)

    return output


def _merge_feature_clusters(
    items: list[dict],
) -> dict | None:

    available = [
        item for item in items
        if isinstance(item, dict)
    ]

    if not available:
        return None

    clusters = _merge_named_items(
        [
            list(item.get("clusters") or [])
            for item in available
        ],
        name_field="feature_name",
        key_fields=("category",),
        merge_list_fields=(
            "feedback_ids",
            "source_channels",
        ),
        merge_text_fields=("description",),
    )

    unclustered = []
    total_feedback = 0

    for item in available:
        unclustered.extend(
            item.get("unclustered_feedback_ids") or []
        )

        total_feedback += int(
            item.get("total_feedback_analyzed") or 0
        )

    total_requests = sum(
        int(cluster.get("mention_count") or 0)
        for cluster in clusters
    )

    return {
        "total_feedback_analyzed": total_feedback,
        "total_feature_clusters": len(clusters),
        "total_feature_requests": total_requests,
        "clusters": clusters,
        "unclustered_feedback_ids": _unique(unclustered),
    }


def _trend_direction(weekly_counts: list[dict]) -> str:
    points = sorted(
        weekly_counts,
        key=lambda item: str(item.get("week_start", "")),
    )

    counts = [
        int(point.get("mention_count") or 0)
        for point in points
    ]

    if len(counts) < 2:
        return "Insufficient Data"

    first_window = sum(counts[:2]) / len(counts[:2])
    last_window = sum(counts[-2:]) / len(counts[-2:])

    if first_window == 0 and last_window > 0:
        return "Emerging"

    if last_window > first_window * 1.2:
        return "Increasing"

    if last_window < first_window * 0.8:
        return "Decreasing"

    return "Stable"


def _merge_trends(
    items: list[dict],
    total_records: int,
) -> dict | None:

    available = [
        item for item in items
        if isinstance(item, dict)
    ]

    if not available:
        return None

    trend_sources = [
        list(item.get("trends") or [])
        for item in available
    ]

    trends = _merge_named_items(
        trend_sources,
        name_field="topic",
        key_fields=("category",),
        merge_list_fields=("feedback_ids",),
        merge_text_fields=("description",),
    )

    # Aggregate weekly counts across disjoint batches.
    weekly_by_topic: dict[
        tuple[str, str],
        dict[str, int]
    ] = {}

    for source in trend_sources:
        for trend in source:
            key = (
                _normalized_key(trend.get("topic")),
                _normalized_key(trend.get("category")),
            )

            bucket = weekly_by_topic.setdefault(key, {})

            for point in trend.get("weekly_counts") or []:
                week = str(point.get("week_start", ""))

                if week:
                    bucket[week] = (
                        bucket.get(week, 0)
                        + int(point.get("mention_count") or 0)
                    )

    for trend in trends:
        key = (
            _normalized_key(trend.get("topic")),
            _normalized_key(trend.get("category")),
        )

        weekly = [
            {
                "week_start": week,
                "mention_count": count,
            }
            for week, count in sorted(
                weekly_by_topic.get(key, {}).items()
            )
        ]

        trend["weekly_counts"] = weekly
        trend["total_mentions"] = len(
            trend.get("feedback_ids") or []
        )
        trend["trend_direction"] = _trend_direction(weekly)

    starts = [
        str(item["analysis_period_start"])
        for item in available
        if item.get("analysis_period_start")
    ]

    ends = [
        str(item["analysis_period_end"])
        for item in available
        if item.get("analysis_period_end")
    ]

    summaries = _unique([
        str(item.get("overall_summary", "")).strip()
        for item in available
        if str(item.get("overall_summary", "")).strip()
    ])

    emerging = []
    recurring = []
    notes = []

    for item in available:
        emerging.extend(item.get("emerging_topics") or [])
        recurring.extend(item.get("recurring_topics") or [])
        notes.extend(item.get("data_quality_notes") or [])

    notes = _unique(notes)

    notes.append(
        "Large-dataset results were merged from disjoint batches. "
        "Identical topic labels were combined; differently named but "
        "semantically similar topics may remain separate."
    )

    return {
        "total_feedback_analyzed": total_records,
        "analysis_period_start": min(starts) if starts else None,
        "analysis_period_end": max(ends) if ends else None,
        "total_trends_identified": len(trends),
        "trends": trends,
        "overall_summary": (
            f"Combined trend analysis across {len(available)} batch(es). "
            + " | ".join(summaries[:8])
        ),
        "emerging_topics": _unique(emerging),
        "recurring_topics": _unique(recurring),
        "data_quality_notes": notes,
    }


def _merge_token_usage(reports: list[Any]) -> dict:
    """Sum numeric token counters recursively."""

    dicts = [
        _as_dict(report)
        for report in reports
        if report is not None
    ]

    if not dicts:
        return {}

    def merge_values(values: list[Any]) -> Any:
        values = [
            value for value in values
            if value is not None
        ]

        if not values:
            return None

        if all(isinstance(value, bool) for value in values):
            return values[-1]

        if all(
            isinstance(value, (int, float))
            and not isinstance(value, bool)
            for value in values
        ):
            return sum(values)

        if all(isinstance(value, dict) for value in values):
            keys = set().union(
                *(value.keys() for value in values)
            )

            return {
                key: merge_values([
                    value.get(key)
                    for value in values
                ])
                for key in keys
            }

        if all(isinstance(value, list) for value in values):
            return _unique([
                entry
                for value in values
                for entry in value
            ])

        return values[-1]

    return merge_values(dicts)


def _aggregate_batch_responses(
    records: list[dict],
    batch_responses: list[dict],
    batch_size: int,
) -> dict:

    batch_count = len(batch_responses)

    source_counts = dict(
        Counter(
            record.get("dataset", "unknown")
            for record in records
        )
    )

    agent_status = {}
    errors: dict[str, str] = {}

    for key in AGENT_KEYS:
        statuses = [
            response.get("agent_status", {}).get(key, "failed")
            for response in batch_responses
        ]

        successes = sum(
            status in SUCCESS_AGENT_STATUSES
            for status in statuses
        )

        if successes == batch_count:
            agent_status[key] = "completed"

        elif successes:
            agent_status[key] = "partial_success"

        elif any(status == "failed" for status in statuses):
            agent_status[key] = "failed"

        else:
            agent_status[key] = "skipped_dependency"

        messages = []

        for index, response in enumerate(
            batch_responses,
            start=1,
        ):
            message = (response.get("errors") or {}).get(key)

            if message:
                messages.append(
                    f"Batch {index}: {message}"
                )

        if messages:
            errors[key] = "\n".join(messages)

    all_batch_success = all(
        bool(response.get("success"))
        for response in batch_responses
    )

    results_by_key = {
        key: [
            (response.get("results") or {}).get(key)
            for response in batch_responses
        ]
        for key in AGENT_KEYS
    }

    themes = _merge_themes(
        results_by_key["themes"],
        len(records),
    )

    pain_points = _merge_pain_points(
        results_by_key["pain_points"],
        len(records),
    )

    feature_clusters = _merge_feature_clusters(
        results_by_key["feature_clusters"],
    )

    trends = _merge_trends(
        results_by_key["trends"],
        len(records),
    )

    batch_summary = []

    for index, response in enumerate(
        batch_responses,
        start=1,
    ):
        batch_summary.append({
            "batch_index": index,
            "record_count": response.get(
                "total_feedback_analyzed", 0
            ),
            "status": response.get("status", "failed"),
            "success": bool(response.get("success")),
            "agent_status": response.get("agent_status", {}),
            "errors": response.get("errors", {}),
        })

    first = (
        batch_responses[0]
        if batch_responses
        else {}
    )

    merged_results = {
        "themes": themes,
        "pain_points": pain_points,
        "feature_clusters": feature_clusters,
        "trends": trends,
    }

    return {
        "success": all_batch_success,
        "status": (
            "completed"
            if all_batch_success
            else "partial_success"
        ),
        "pipeline_type": "sequential_batched",
        "total_feedback_analyzed": len(records),
        "source_counts": source_counts,
        "execution_order": first.get("execution_order", []),
        "data_flow": first.get("data_flow", {}),
        "agent_status": agent_status,
        "errors": errors,
        "results": merged_results,
        "token_usage": _merge_token_usage([
            response.get("token_usage")
            for response in batch_responses
        ]),
        "batch_summary": {
            "batch_size": batch_size,
            "total_batches": batch_count,
            "completed_batches": sum(
                bool(response.get("success"))
                for response in batch_responses
            ),
            "partial_or_failed_batches": sum(
                not bool(response.get("success"))
                for response in batch_responses
            ),
            "batches": batch_summary,
        },
        # Persist these separately in the backend's analysis_batches
        # collection, not inside the parent analysis_runs document.
        "batch_results": [
            {
                "batch_index": index,
                "record_count": response.get(
                    "total_feedback_analyzed", 0
                ),
                "feedback_ids": response.get(
                    "_feedback_ids", []
                ),
                "status": response.get("status", "failed"),
                "success": bool(response.get("success")),
                "agent_status": response.get("agent_status", {}),
                "errors": response.get("errors", {}),
                "results": response.get("results", {}),
                "token_usage": response.get("token_usage", {}),
            }
            for index, response in enumerate(
                batch_responses,
                start=1,
            )
        ],
    }


def split_records(
    records: list[dict],
    batch_size: int,
) -> list[list[dict]]:
    """Split records into balanced batches, each with at least two items."""

    if not records:
        return []

    if not isinstance(batch_size, int) or batch_size < 2:
        raise BatchAnalysisError(
            "Batch size must be an integer of at least 2."
        )

    batch_count = (
        len(records) + batch_size - 1
    ) // batch_size

    base_size, remainder = divmod(
        len(records),
        batch_count,
    )

    batches = []
    offset = 0

    for index in range(batch_count):
        current_size = (
            base_size + (1 if index < remainder else 0)
        )

        batches.append(
            records[offset:offset + current_size]
        )

        offset += current_size

    return batches


def run_batched_analyses(
    records: list[dict] | None,
    single_batch_runner: Callable[[list[dict]], dict],
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict:
    """Execute the existing four-agent pipeline over multiple batches."""

    if records is None:
        # Preserve the existing local JSON development fallback.
        return single_batch_runner(None)

    if not isinstance(records, list):
        raise BatchAnalysisError(
            "Feedback records must be supplied as a list."
        )

    if len(records) < 2:
        raise BatchAnalysisError(
            "At least two feedback records are required."
        )

    if len(records) > MAX_TOTAL_FEEDBACK_RECORDS:
        raise BatchAnalysisError(
            f"The analysis limit is {MAX_TOTAL_FEEDBACK_RECORDS:,} "
            "feedback records per run."
        )

    if (
        not isinstance(batch_size, int)
        or batch_size < 2
        or batch_size > 500
    ):
        raise BatchAnalysisError(
            "Batch size must be between 2 and 500."
        )

    seen_ids = set()

    for index, record in enumerate(records, start=1):
        if not isinstance(record, dict):
            raise BatchAnalysisError(
                f"Feedback record {index} is not an object."
            )

        feedback_id = str(
            record.get("feedback_id") or ""
        ).strip()

        if not feedback_id:
            raise BatchAnalysisError(
                f"Feedback record {index} is missing feedback_id."
            )

        if feedback_id in seen_ids:
            raise BatchAnalysisError(
                f"Duplicate feedback ID found: {feedback_id}"
            )

        seen_ids.add(feedback_id)

    batches = split_records(records, batch_size)

    logger.info(
        "Starting batched analysis: %d records, %d batches, "
        "%d records per batch.",
        len(records),
        len(batches),
        batch_size,
    )

    responses = []

    for index, batch in enumerate(batches, start=1):
        logger.info(
            "Running analysis batch %d/%d (%d records).",
            index,
            len(batches),
            len(batch),
        )

        try:
            response = single_batch_runner(batch)

            if not isinstance(response, dict):
                raise RuntimeError(
                    "The single-batch pipeline returned an invalid response."
                )

            response = dict(response)

            response["_feedback_ids"] = [
                record["feedback_id"]
                for record in batch
            ]

            responses.append(response)

        except Exception as exc:
            # Continue so successful batches are not discarded.
            logger.exception(
                "Analysis batch %d/%d failed.",
                index,
                len(batches),
            )

            responses.append({
                "success": False,
                "status": "failed",
                "total_feedback_analyzed": len(batch),
                "agent_status": {
                    key: "failed"
                    for key in AGENT_KEYS
                },
                "errors": {
                    key: f"Batch execution failed: {exc}"
                    for key in AGENT_KEYS
                },
                "results": {
                    key: None
                    for key in AGENT_KEYS
                },
                "token_usage": {},
                "execution_order": [],
                "data_flow": {},
                "_feedback_ids": [
                    record["feedback_id"]
                    for record in batch
                ],
            })

    response = _aggregate_batch_responses(
        records,
        responses,
        batch_size,
    )

    logger.info(
        "Batched analysis finished: %s (%d/%d batches completed).",
        response["status"],
        response["batch_summary"]["completed_batches"],
        response["batch_summary"]["total_batches"],
    )

    return response
def aggregate_batch_responses(
    batch_responses: list[dict],
    *,
    total_feedback_analyzed: int,
    source_counts: dict[str, int],
    batch_size: int = DEFAULT_BATCH_SIZE,
) -> dict:
    """
    Merge previously completed batch responses.

    Uses the existing deterministic merger.
    Does not execute Gemini or any AI agent.
    """

    if not isinstance(batch_responses, list) or not batch_responses:
        raise BatchAnalysisError(
            "At least one batch response is required."
        )

    if (
        not isinstance(total_feedback_analyzed, int)
        or isinstance(total_feedback_analyzed, bool)
        or not 2 <= total_feedback_analyzed <= MAX_TOTAL_FEEDBACK_RECORDS
    ):
        raise BatchAnalysisError(
            "Total feedback count must be between 2 and 10,000."
        )

    if (
        not isinstance(batch_size, int)
        or isinstance(batch_size, bool)
        or not 2 <= batch_size <= 500
    ):
        raise BatchAnalysisError(
            "Batch size must be between 2 and 500."
        )

    if not isinstance(source_counts, dict):
        raise BatchAnalysisError(
            "Source counts must be an object."
        )

    for source, count in source_counts.items():
        if (
            not isinstance(source, str)
            or not source.strip()
            or not isinstance(count, int)
            or isinstance(count, bool)
            or count < 0
        ):
            raise BatchAnalysisError(
                "Source counts contain an invalid entry."
            )

    if sum(source_counts.values()) != total_feedback_analyzed:
        raise BatchAnalysisError(
            "Source counts do not match the total feedback count."
        )

    expected_batches = (
        total_feedback_analyzed + batch_size - 1
    ) // batch_size

    if len(batch_responses) != expected_batches:
        raise BatchAnalysisError(
            f"Expected {expected_batches} batch responses, "
            f"received {len(batch_responses)}."
        )

    normalized_responses = []

    for index, batch in enumerate(batch_responses, start=1):
        if not isinstance(batch, dict):
            raise BatchAnalysisError(
                f"Batch response {index} must be an object."
            )

        if not isinstance(batch.get("results"), dict):
            raise BatchAnalysisError(
                f"Batch {index} has invalid results."
            )

        if not isinstance(batch.get("agent_status"), dict):
            raise BatchAnalysisError(
                f"Batch {index} has invalid agent statuses."
            )

        normalized = dict(batch)

        normalized["batch_index"] = index
        normalized["total_feedback_analyzed"] = batch.get(
            "total_feedback_analyzed",
            batch.get("record_count", 0),
        )
        normalized["_feedback_ids"] = batch.get(
            "_feedback_ids",
            batch.get("feedback_ids", []),
        )

        normalized_responses.append(normalized)

    # The existing merger expects records to calculate total counts
    # and source counts. Only dataset labels are needed here.
    source_records = [
        {"dataset": source}
        for source, count in source_counts.items()
        for _ in range(count)
    ]

    # IMPORTANT: Existing function signature is:
    # _aggregate_batch_responses(records, batch_responses, batch_size)
    return _aggregate_batch_responses(
        source_records,
        normalized_responses,
        batch_size,
    )