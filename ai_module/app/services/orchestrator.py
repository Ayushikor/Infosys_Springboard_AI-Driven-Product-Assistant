
"""
Orchestrates the four AI feedback analysis agents.

Reads feedback exclusively from the three local JSON datasets.
An individual agent failure is recorded without stopping the
remaining agents. Successful results are preserved.
"""

import logging
from collections import Counter

from app.schemas.theme_extraction import (
    FeedbackItem,
    ThemeExtractionRequest,
)
from app.schemas.pain_point import PainPointExtractionRequest
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

logger = logging.getLogger(__name__)


class OrchestrationError(RuntimeError):
    """Raised when the overall orchestration cannot start."""


def _serialize_result(result):
    """Convert a Pydantic result into JSON-compatible data."""

    if hasattr(result, "model_dump"):
        return result.model_dump(mode="json")

    return result


def run_all_analyses() -> dict:
    """
    Run all four agents against the same local JSON dataset.

    Individual agent failures are recorded. Other agents continue.
    """

    # Load the three local JSON datasets.
    try:
        records = load_feedback_dataset()
    except Exception as exc:
        logger.exception("Could not load feedback datasets.")
        raise OrchestrationError(
            "The local feedback datasets could not be loaded."
        ) from exc

    if not records:
        raise OrchestrationError(
            "No feedback records were found in the datasets."
        )

    if len(records) > 500:
        raise OrchestrationError(
            "The dataset exceeds the 500-record agent limit."
        )

    # Build common information from the original records.
    source_counts = dict(
        Counter(
            record.get("dataset", "unknown")
            for record in records
        )
    )

    try:
        theme_request = ThemeExtractionRequest(
            feedback=[
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
        )

        pain_point_request = PainPointExtractionRequest(
            feedback=[
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
        )

        feature_request = FeatureClusteringRequest(
            feedback=[
                FeatureFeedbackItem(
                    feedback_id=record["feedback_id"],
                    source_channel=record["source_channel"],
                    raw_text=record["raw_text"],
                )
                for record in records
            ]
        )

        trend_request = TrendAnalysisRequest(
            feedback=[
                TrendFeedbackItem(
                    feedback_id=record["feedback_id"],
                    source_channel=record["source_channel"],
                    raw_text=record["raw_text"],
                    timestamp=record["timestamp"],
                )
                for record in records
            ]
        )

    except Exception as exc:
        logger.exception(
            "Could not prepare the agent input requests."
        )
        raise OrchestrationError(
            "The feedback records could not be prepared for analysis."
        ) from exc

    results = {
        "themes": None,
        "pain_points": None,
        "feature_clusters": None,
        "trends": None,
    }

    agent_status = {}
    errors = {}

    execution_order = [
        ("themes", "Agent 1 - Theme Extraction",
         lambda: theme_extraction_agent.extract_themes(theme_request)),

        ("pain_points", "Agent 2 - Pain Point Identification",
         lambda: pain_point_agent.identify_pain_points(pain_point_request)),

        ("feature_clusters", "Agent 3 - Feature Clustering",
         lambda: feature_clustering_agent.identify_feature_clusters(feature_request)),

        ("trends", "Agent 4 - Trend Analysis",
         lambda: trend_analysis_agent.analyze_feedback_trends(trend_request)),
    ]

    # Run agents independently so one failure does not stop the workflow.
    for key, agent_name, operation in execution_order:
        logger.info("Starting %s.", agent_name)

        try:
            agent_result = operation()

            results[key] = _serialize_result(agent_result)
            agent_status[key] = "completed"

            logger.info("%s completed successfully.", agent_name)

        except Exception:
            logger.exception("%s failed.", agent_name)

            agent_status[key] = "failed"
            errors[key] = (
                f"{agent_name} failed. "
                "Its owning implementation needs review."
            )

    all_completed = all(
        status == "completed"
        for status in agent_status.values()
    )

    return {
        "success": all_completed,
        "status": (
            "completed"
            if all_completed
            else "partial_success"
        ),
        "total_feedback_analyzed": len(records),
        "source_counts": source_counts,
        "execution_order": [
            agent_name
            for _, agent_name, _ in execution_order
        ],
        "agent_status": agent_status,
        "errors": errors,
        "results": results,
    }
