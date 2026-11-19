
"""
Sequential orchestrator for the four AI feedback analysis agents.

Pipeline:

    Agent 1: Theme Extraction
        |
        v
    Agent 2: Pain Point Identification
        |
        v
    Agent 3: Feature Clustering
        |
        v
    Agent 4: Trend Analysis

Each agent receives relevant structured output from preceding agents.
Original feedback is retrieved by ID whenever evidence is required.

Failure handling:
- A failed agent is marked as failed.
- Dependent downstream agents are skipped.
- Successful upstream results are preserved.
- Invalid agent outputs are treated as agent failures.
"""

import logging
from collections import Counter
from typing import Any

from app.schemas.theme_extraction import (
    FeedbackItem,
    ThemeExtractionRequest,
)

from app.schemas.pain_point import (
    PainPointExtractionRequest,
)

from app.schemas.feature_clustering import (
    FeatureFeedbackItem,
    FeatureClusteringRequest,
)

from app.schemas.trend_analysis import (
    TrendFeedbackItem,
    TrendAnalysisRequest,
)

from app.services.dataset_loader import load_feedback_dataset

from app.services import (
    theme_extraction_agent,
    pain_point_agent,
    feature_clustering_agent,
    trend_analysis_agent,
)

from app.services.token_usage import capture_token_usage


logger = logging.getLogger(__name__)


class OrchestrationError(RuntimeError):
    """Raised when the overall orchestration cannot start."""


# ---------------------------------------------------------
# GENERIC HELPERS
# ---------------------------------------------------------


def _get_value(
    item: Any,
    field: str,
    default: Any = None,
) -> Any:
    """Read a field from a dictionary or object."""

    if isinstance(item, dict):
        return item.get(field, default)

    return getattr(item, field, default)


def _require_field(
    result: Any,
    field: str,
    agent_name: str,
) -> Any:
    """Ensure an agent returned a required field."""

    value = _get_value(result, field)

    if value is None:
        raise ValueError(
            f"{agent_name} returned an invalid result: "
            f"missing '{field}'."
        )

    return value


def _require_list_field(
    result: Any,
    field: str,
    agent_name: str,
) -> list:
    """Ensure an agent returned a list for a required field."""

    value = _require_field(
        result,
        field,
        agent_name,
    )

    if not isinstance(value, (list, tuple)):
        raise ValueError(
            f"{agent_name} returned an invalid '{field}' field. "
            "Expected a list."
        )

    return list(value)


def _serialize_result(result: Any) -> Any:
    """Convert Pydantic results into JSON-compatible data."""

    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")

    if isinstance(result, dict):
        return result

    return result


def _build_common_feedback(
    records: list[dict],
) -> list[FeedbackItem]:
    """Create normalized feedback objects once."""

    return [
        FeedbackItem(
            id=record["feedback_id"],
            title=record.get("title") or "",
            message=(
                record.get("message")
                or record.get("raw_text")
                or ""
            ),
        )
        for record in records
    ]


def _get_original_feedback_text(
    record: dict,
) -> str:
    """Retrieve original feedback text from a dataset record."""

    return (
        record.get("raw_text")
        or record.get("message")
        or record.get("title")
        or ""
    )


# ---------------------------------------------------------
# FAILURE HANDLING
# ---------------------------------------------------------


def _skip_downstream_agents(
    agent_status: dict,
    errors: dict,
    results: dict,
    downstream: list[tuple[str, str]],
    failed_agent: str,
) -> None:
    """Mark dependent agents as skipped after upstream failure."""

    for key, agent_name in downstream:

        agent_status[key] = "skipped_dependency"
        results[key] = None

        errors[key] = (
            f"{agent_name} was skipped because "
            f"{failed_agent} did not complete successfully."
        )

        logger.warning(
            "%s skipped because %s failed.",
            agent_name,
            failed_agent,
        )


def _mark_agent_failed(
    agent_key: str,
    agent_name: str,
    exc: Exception,
    agent_status: dict,
    errors: dict,
    results: dict,
) -> None:
    """Record failure and clear the invalid result."""

    agent_status[agent_key] = "failed"
    results[agent_key] = None

    errors[agent_key] = (
        f"{agent_name} failed: {str(exc)}"
    )


# ---------------------------------------------------------
# AGENT 1 CONTEXT
# ---------------------------------------------------------


def _build_theme_context_for_agent_3(
    theme_result: Any,
    allowed_ids: set[str],
) -> list[dict]:
    """Build compact Agent 1 context for Agent 3."""

    context = []

    for theme in theme_result.themes:

        relevant_ids = [
            feedback_id
            for feedback_id in theme.feedback_ids
            if feedback_id in allowed_ids
        ]

        if not relevant_ids:
            continue

        context.append(
            {
                "name": theme.name,
                "description": theme.description,
                "keywords": theme.keywords,
                "feedback_ids": relevant_ids,
            }
        )

    return context


# ---------------------------------------------------------
# AGENT 2 CONTEXT
# ---------------------------------------------------------


def _build_pain_context_for_agent_3(
    pain_result: Any,
    allowed_ids: set[str],
) -> list[dict]:
    """Build compact Agent 2 context for Agent 3."""

    context = []

    for point in pain_result.pain_points:

        relevant_ids = [
            feedback_id
            for feedback_id in point.feedback_ids
            if feedback_id in allowed_ids
        ]

        if not relevant_ids:
            continue

        context.append(
            {
                "name": point.name,
                "category": point.category,
                "severity": point.severity,
                "description": point.description,
                "feedback_ids": relevant_ids,
            }
        )

    return context


# ---------------------------------------------------------
# AGENT 4 CONTEXT
# ---------------------------------------------------------


def _build_pain_context_for_agent_4(
    pain_result: Any,
) -> list[dict]:
    """Create compact pain-point summaries for trend analysis."""

    return [
        {
            "name": point.name,
            "category": point.category,
            "severity": point.severity,
            "description": point.description,
            "feedback_ids": point.feedback_ids,
        }
        for point in pain_result.pain_points
    ]


def _build_feature_context_for_agent_4(
    feature_result: Any,
) -> list[dict]:
    """Create compact feature-cluster summaries for trend analysis."""

    if feature_result is None:
        return []

    clusters = _get_value(
        feature_result,
        "clusters",
        [],
    )

    return [
        {
            "feature_name": _get_value(
                cluster,
                "feature_name",
            ),
            "description": _get_value(
                cluster,
                "description",
            ),
            "category": _get_value(
                cluster,
                "category",
            ),
            "mention_count": _get_value(
                cluster,
                "mention_count",
            ),
            "feedback_ids": _get_value(
                cluster,
                "feedback_ids",
                [],
            ),
        }
        for cluster in clusters
    ]


# ---------------------------------------------------------
# MAIN SEQUENTIAL ORCHESTRATOR
# ---------------------------------------------------------


def run_all_analyses() -> dict:
    """
    Run the four AI agents as a sequential data pipeline.

    Agent 1 output -> Agent 2 input
    Agent 2 output -> Agent 3 input
    Agent 3 output -> Agent 4 input

    Successful results are preserved.
    Dependent agents are skipped when an upstream agent fails.

    Agent failures produce a partial_success response rather than
    raising an exception. OrchestrationError is reserved for failures
    that prevent the pipeline from starting.
    """

    # -----------------------------------------------------
    # STEP 1: LOAD DATASETS
    # -----------------------------------------------------

    try:
        records = load_feedback_dataset()

    except Exception as exc:
        logger.exception(
            "Could not load feedback datasets."
        )

        raise OrchestrationError(
            "The local feedback datasets could not be loaded."
        ) from exc

    if not records:
        raise OrchestrationError(
            "No feedback records were found."
        )

    if len(records) > 500:
        raise OrchestrationError(
    "The dataset exceeds the 500-record limit "
    "(maximum of 500 records per agent)."
)

    # -----------------------------------------------------
    # STEP 2: VALIDATE ORIGINAL RECORDS
    # -----------------------------------------------------

    try:

        feedback_by_id = {}

        for record in records:

            if not isinstance(record, dict):
                raise ValueError(
                    "A feedback dataset record is not a dictionary."
                )

            feedback_id = record.get("feedback_id")

            if not feedback_id:
                raise ValueError(
                    "A feedback record is missing feedback_id."
                )

            feedback_by_id[feedback_id] = record

        if len(feedback_by_id) != len(records):
            raise ValueError(
                "Duplicate feedback IDs were found."
            )

        # Ensure original feedback text is available.
        for record in records:

            if not _get_original_feedback_text(record):
                raise ValueError(
                    "A feedback record is missing its original text: "
                    f"{record['feedback_id']}"
                )

        source_counts = dict(
            Counter(
                record.get("dataset", "unknown")
                for record in records
            )
        )

        # Normalize common feedback once.
        common_feedback = _build_common_feedback(records)

    except Exception as exc:

        logger.exception(
            "Feedback dataset validation or normalization failed."
        )

        raise OrchestrationError(
            "The feedback dataset contains invalid records."
        ) from exc

    # -----------------------------------------------------
    # STEP 3: INITIALIZE RESULTS
    # -----------------------------------------------------

    results = {
        "themes": None,
        "pain_points": None,
        "feature_clusters": None,
        "trends": None,
    }

    agent_status = {}
    errors = {}

    execution_order = [
        "Agent 1 - Theme Extraction",
        "Agent 2 - Pain Point Identification",
        "Agent 3 - Feature Clustering",
        "Agent 4 - Trend Analysis",
    ]

    # -----------------------------------------------------
    # STEP 4: TRACK TOKEN USAGE FOR THIS PIPELINE RUN
    # -----------------------------------------------------

    with capture_token_usage(
        "sequential_feedback_analysis"
    ) as token_usage:

        theme_result = None
        pain_result = None
        feature_result = None
        trend_result = None

        # =================================================
        # AGENT 1 - THEME EXTRACTION
        # =================================================

        logger.info(
            "Starting Agent 1 - Theme Extraction."
        )

        try:

            theme_request = ThemeExtractionRequest(
                feedback=common_feedback,
            )

            theme_result = (
                theme_extraction_agent.extract_themes(
                    theme_request
                )
            )

            # Validate output before allowing downstream use.
            themes = _require_list_field(
                theme_result,
                "themes",
                "Agent 1",
            )

            results["themes"] = _serialize_result(
                theme_result
            )

            agent_status["themes"] = "completed"

            logger.info(
                "Agent 1 completed: %d themes extracted.",
                len(themes),
            )

        except Exception as exc:

            logger.exception(
                "Agent 1 - Theme Extraction failed."
            )

            # Clear any invalid or partially assigned output.
            theme_result = None

            _mark_agent_failed(
                "themes",
                "Theme extraction",
                exc,
                agent_status,
                errors,
                results,
            )

            _skip_downstream_agents(
                agent_status,
                errors,
                results,
                [
                    (
                        "pain_points",
                        "Agent 2 - Pain Point Identification",
                    ),
                    (
                        "feature_clusters",
                        "Agent 3 - Feature Clustering",
                    ),
                    (
                        "trends",
                        "Agent 4 - Trend Analysis",
                    ),
                ],
                "Agent 1",
            )

        # =================================================
        # AGENT 2 - PAIN POINT IDENTIFICATION
        # =================================================

        if theme_result is not None:

            logger.info(
                "Starting Agent 2 with Agent 1 theme context."
            )

            try:

                # Agent 1 output becomes Agent 2 input.
                pain_request = PainPointExtractionRequest(
                    feedback=common_feedback,
                    theme_context=theme_result.themes,
                )

                pain_result = (
                    pain_point_agent.identify_pain_points(
                        pain_request
                    )
                )

                # Validate output before allowing downstream use.
                pain_points = _require_list_field(
                    pain_result,
                    "pain_points",
                    "Agent 2",
                )

                feature_request_ids = _require_list_field(
                    pain_result,
                    "feature_request_feedback_ids",
                    "Agent 2",
                )

                uncertain_ids = _require_list_field(
                    pain_result,
                    "uncertain_feedback_ids",
                    "Agent 2",
                )

                results["pain_points"] = _serialize_result(
                    pain_result
                )

                agent_status["pain_points"] = "completed"

                logger.info(
                    "Agent 2 completed: %d pain-point groups, "
                    "%d feature-request candidates and "
                    "%d uncertain records.",
                    len(pain_points),
                    len(feature_request_ids),
                    len(uncertain_ids),
                )

            except Exception as exc:

                logger.exception(
                    "Agent 2 - Pain Point Identification failed."
                )

                # Clear any invalid or partially assigned output.
                pain_result = None

                _mark_agent_failed(
                    "pain_points",
                    "Pain-point identification",
                    exc,
                    agent_status,
                    errors,
                    results,
                )

                _skip_downstream_agents(
                    agent_status,
                    errors,
                    results,
                    [
                        (
                            "feature_clusters",
                            "Agent 3 - Feature Clustering",
                        ),
                        (
                            "trends",
                            "Agent 4 - Trend Analysis",
                        ),
                    ],
                    "Agent 2",
                )

        # =================================================
        # AGENT 3 - FEATURE CLUSTERING
        # =================================================

        if pain_result is not None:

            logger.info(
                "Starting Agent 3 with Agent 1 and Agent 2 context."
            )

            try:

                # Agent 2 identifies likely feature requests.
                # Uncertain records are also included for review.
                candidate_ids = (
                    set(pain_result.feature_request_feedback_ids)
                    | set(pain_result.uncertain_feedback_ids)
                )

                # Reject candidate IDs not present in original data.
                unknown_candidate_ids = (
                    candidate_ids - set(feedback_by_id)
                )

                if unknown_candidate_ids:
                    raise ValueError(
                        "Agent 2 returned feedback IDs absent from "
                        "the original dataset: "
                        f"{sorted(unknown_candidate_ids)}"
                    )

                # Preserve original dataset order.
                candidate_records = [
                    record
                    for record in records
                    if record["feedback_id"] in candidate_ids
                ]

                selected_ids = {
                    record["feedback_id"]
                    for record in candidate_records
                }

                if not candidate_records:

                    # No model call is necessary if there are
                    # no feature-request or uncertain candidates.
                    feature_result = {
                        "total_feedback_analyzed": 0,
                        "total_feature_clusters": 0,
                        "total_feature_requests": 0,
                        "clusters": [],
                        "unclustered_feedback_ids": [],
                    }

                    results["feature_clusters"] = feature_result

                    agent_status["feature_clusters"] = (
                        "completed_no_candidates"
                    )

                    logger.info(
                        "Agent 3 skipped its LLM call: "
                        "Agent 2 returned no feature candidates."
                    )

                else:

                    # Retrieve original feedback using the IDs.
                    feature_feedback = [
                        FeatureFeedbackItem(
                            feedback_id=record["feedback_id"],
                            source_channel=(
                                record.get("source_channel")
                                or record.get("dataset")
                                or "unknown"
                            ),
                            raw_text=_get_original_feedback_text(
                                record
                            ),
                        )
                        for record in candidate_records
                    ]

                    # Filter Agent 1 themes to selected IDs.
                    theme_context = (
                        _build_theme_context_for_agent_3(
                            theme_result,
                            selected_ids,
                        )
                    )

                    # Filter Agent 2 pain points to selected IDs.
                    pain_point_context = (
                        _build_pain_context_for_agent_3(
                            pain_result,
                            selected_ids,
                        )
                    )

                    # Agent 1 + Agent 2 outputs become Agent 3 input.
                    feature_request = FeatureClusteringRequest(
                        feedback=feature_feedback,
                        theme_context=theme_context,
                        pain_point_context=pain_point_context,
                    )

                    feature_result = (
                        feature_clustering_agent.identify_feature_clusters(
                            feature_request
                        )
                    )

                    # Validate Agent 3 output before Agent 4 uses it.
                    feature_clusters = _require_list_field(
                        feature_result,
                        "clusters",
                        "Agent 3",
                    )

                    _require_field(
                        feature_result,
                        "total_feature_clusters",
                        "Agent 3",
                    )

                    _require_field(
                        feature_result,
                        "total_feature_requests",
                        "Agent 3",
                    )

                    results["feature_clusters"] = _serialize_result(
                        feature_result
                    )

                    agent_status["feature_clusters"] = "completed"

                    logger.info(
                        "Agent 3 completed: %d candidate records, "
                        "%d feature clusters.",
                        len(candidate_records),
                        len(feature_clusters),
                    )

            except Exception as exc:

                logger.exception(
                    "Agent 3 - Feature Clustering failed."
                )

                # Clear any invalid or partially assigned output.
                feature_result = None

                _mark_agent_failed(
                    "feature_clusters",
                    "Feature clustering",
                    exc,
                    agent_status,
                    errors,
                    results,
                )

                _skip_downstream_agents(
                    agent_status,
                    errors,
                    results,
                    [
                        (
                            "trends",
                            "Agent 4 - Trend Analysis",
                        ),
                    ],
                    "Agent 3",
                )

        # =================================================
        # AGENT 4 - TREND ANALYSIS
        # =================================================

        if (
            theme_result is not None
            and pain_result is not None
            and feature_result is not None
        ):

            logger.info(
                "Starting Agent 4 with combined upstream context."
            )

            try:

                # Agent 1 context.
                theme_context = [
                    {
                        "name": theme.name,
                        "description": theme.description,
                        "keywords": theme.keywords,
                        "feedback_ids": theme.feedback_ids,
                    }
                    for theme in theme_result.themes
                ]

                # Agent 2 context.
                pain_context = _build_pain_context_for_agent_4(
                    pain_result
                )

                # Agent 3 context.
                feature_context = _build_feature_context_for_agent_4(
                    feature_result
                )

                # Verify Agent 4 context fields are available.
                for theme in theme_context:
                    if not theme["feedback_ids"]:
                        continue

                # Agent 4 receives timestamps and original feedback
                # along with compact upstream findings.
                trend_feedback = [
                    TrendFeedbackItem(
                        feedback_id=record["feedback_id"],
                        source_channel=(
                            record.get("source_channel")
                            or record.get("dataset")
                            or "unknown"
                        ),
                        raw_text=_get_original_feedback_text(
                            record
                        ),
                        timestamp=record["timestamp"],
                    )
                    for record in records
                ]

                trend_request = TrendAnalysisRequest(
                    feedback=trend_feedback,
                    theme_context=theme_context,
                    pain_point_context=pain_context,
                    feature_context=feature_context,
                )

                trend_result = (
                    trend_analysis_agent.analyze_feedback_trends(
                        trend_request
                    )
                )

                # Validate Agent 4 output.
                _require_field(
                    trend_result,
                    "total_trends_identified",
                    "Agent 4",
                )

                results["trends"] = _serialize_result(
                    trend_result
                )

                agent_status["trends"] = "completed"

                logger.info(
                    "Agent 4 completed: %d trends identified.",
                    trend_result.total_trends_identified,
                )

            except Exception as exc:

                logger.exception(
                    "Agent 4 - Trend Analysis failed."
                )

                # Clear invalid or partially assigned output.
                trend_result = None

                _mark_agent_failed(
                    "trends",
                    "Trend analysis",
                    exc,
                    agent_status,
                    errors,
                    results,
                )

        # -------------------------------------------------
        # FINAL STATUS
        # -------------------------------------------------

        successful_statuses = {
            "completed",
            "completed_no_candidates",
        }

        all_completed = (
            len(agent_status) == 4
            and all(
                status in successful_statuses
                for status in agent_status.values()
            )
        )

        response = {
            "success": all_completed,

            "status": (
                "completed"
                if all_completed
                else "partial_success"
            ),

            "pipeline_type": "sequential",

            "total_feedback_analyzed": len(records),

            "source_counts": source_counts,

            "execution_order": execution_order,

            "data_flow": {
                "agent_1_to_agent_2": (
                    "theme_context"
                    if theme_result is not None
                    else "unavailable"
                ),

                "agent_2_to_agent_3": (
                    "pain_point_context_and_feature_request_ids"
                    if pain_result is not None
                    else "unavailable"
                ),

                "agent_3_to_agent_4": (
                    "feature_cluster_context"
                    if feature_result is not None
                    else "unavailable"
                ),
            },

            "agent_status": agent_status,

            "errors": errors,

            "results": results,

            "token_usage": token_usage.report(),
        }

    logger.info(
        "Sequential pipeline finished with status: %s",
        response["status"],
    )

    return response
