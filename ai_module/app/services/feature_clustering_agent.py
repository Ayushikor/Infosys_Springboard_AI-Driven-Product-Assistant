"""
CrewAI service for the Feature Clustering Agent.

Groups similar feature requests from customer feedback,
user reviews, and support tickets.
"""

import json
import logging
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task

from app.core.config import settings
from app.schemas.feature_clustering import (
    FeatureClusteringRequest,
    FeatureClusteringOutput,
    FeatureClusteringResult,
)

logger = logging.getLogger(__name__)


class FeatureClusteringError(Exception):
    """Raised when feature clustering fails."""


def _create_llm() -> LLM:
    """Create the Gemini LLM used by the CrewAI agent."""

    api_key = settings.gemini_api_key
    model_name = settings.gemini_model.strip()

    if not api_key:
        raise FeatureClusteringError(
            "Gemini API key is not configured."
        )

    if not model_name.startswith("gemini/"):
        model_name = f"gemini/{model_name}"

    return LLM(
        model=model_name,
        api_key=api_key,
        temperature=0.2,
    )


def _parse_crew_output(result: Any) -> FeatureClusteringOutput:
    """Convert CrewAI output into the validated Pydantic schema."""

    try:
        # CrewAI may return a Pydantic object directly.
        if getattr(result, "pydantic", None) is not None:
            return FeatureClusteringOutput.model_validate(
                result.pydantic
            )

        # It may also return structured JSON.
        if getattr(result, "json_dict", None):
            return FeatureClusteringOutput.model_validate(
                result.json_dict
            )

        raw_output = getattr(result, "raw", str(result))

        parsed = json.loads(raw_output)

        return FeatureClusteringOutput.model_validate(parsed)

    except Exception as exc:
        logger.exception("Could not parse feature clustering output.")
        raise FeatureClusteringError(
            "The AI returned an invalid feature clustering response."
        ) from exc


def _validate_feedback_assignments(
    output: FeatureClusteringOutput,
    request: FeatureClusteringRequest,
) -> None:
    """
    Ensure every feedback record is accounted for exactly once.

    Each record must either belong to one feature cluster
    or appear in unclustered_feedback_ids.
    """

    input_ids = {
        item.feedback_id for item in request.feedback
    }

    assigned_ids = []

    for cluster in output.feature_clusters:
        if cluster.mention_count != len(cluster.feedback_ids):
            raise FeatureClusteringError(
                f"Incorrect mention count for {cluster.feature_name}."
            )

        assigned_ids.extend(cluster.feedback_ids)

    assigned_ids.extend(output.unclustered_feedback_ids)

    if len(assigned_ids) != len(set(assigned_ids)):
        raise FeatureClusteringError(
            "A feedback record was assigned more than once."
        )

    if set(assigned_ids) != input_ids:
        raise FeatureClusteringError(
            "Some feedback records are missing or contain unknown IDs."
        )


def identify_feature_clusters(
    request: FeatureClusteringRequest,
) -> FeatureClusteringResult:
    """
    Analyze feedback and group similar feature requests.

    Args:
        request: Validated feedback records.

    Returns:
        FeatureClusteringResult containing feature clusters.
    """

    try:
        llm = _create_llm()

        agent = Agent(
            role="Product Feature Clustering Specialist",
            goal=(
                "Identify genuine customer feature requests and "
                "group semantically similar requests into meaningful "
                "feature clusters."
            ),
            backstory=(
                "You are an experienced product analytics specialist. "
                "You analyze customer feedback, app reviews, and support "
                "tickets to discover features customers want. You "
                "understand that different customers may describe the "
                "same feature using different words."
            ),
            llm=llm,
            verbose=False,
            allow_delegation=False,
        )

        feedback_data = [
            {
                "feedback_id": item.feedback_id,
                "source_channel": item.source_channel,
                "raw_text": item.raw_text,
            }
            for item in request.feedback
        ]

        task = Task(
            description=f"""
Analyze the following customer feedback records.

FEEDBACK DATA:
{json.dumps(feedback_data, ensure_ascii=False)}

YOUR RESPONSIBILITIES:

1. Read every feedback record carefully.

2. Identify genuine feature requests.
   A feature request means the customer is asking for a new
   capability, integration, improvement, or product functionality.

3. Group semantically similar feature requests together.
   Different wording can describe the same requested feature.

4. Do not create separate clusters for requests that mean
   essentially the same thing.

5. Do not treat ordinary complaints, bug reports, general
   praise, or unrelated comments as feature requests unless
   the customer explicitly requests a product capability.

6. Give every cluster:
   - A short, meaningful feature_name.
   - A clear description.
   - An appropriate category.
   - The original feedback IDs supporting the cluster.
   - The source channels supporting the cluster.
   - An accurate mention_count.

7. Feedback that does not contain a feature request must be
   included in unclustered_feedback_ids.

8. Every input feedback_id must appear exactly once:
   either in one feature cluster or in unclustered_feedback_ids.

9. Never invent feedback IDs, customer requests, or evidence.

10. Do not calculate feature priority or business value.
    Your responsibility is feature clustering only.

Return the result using the required structured output schema.
""",
            expected_output=(
                "A valid structured FeatureClusteringOutput containing "
                "feature clusters and unclustered feedback IDs."
            ),
            agent=agent,
            output_pydantic=FeatureClusteringOutput,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

        result = crew.kickoff()

        output = _parse_crew_output(result)

        _validate_feedback_assignments(output, request)

        total_requests = sum(
            cluster.mention_count
            for cluster in output.feature_clusters
        )

        return FeatureClusteringResult(
            total_feedback_analyzed=len(request.feedback),
            total_feature_clusters=len(output.feature_clusters),
            total_feature_requests=total_requests,
            clusters=output.feature_clusters,
            unclustered_feedback_ids=output.unclustered_feedback_ids,
        )

    except FeatureClusteringError:
        raise

    except Exception as exc:
        logger.exception("Feature clustering failed.")

        raise FeatureClusteringError(
            "Feature clustering could not be completed."
        ) from exc