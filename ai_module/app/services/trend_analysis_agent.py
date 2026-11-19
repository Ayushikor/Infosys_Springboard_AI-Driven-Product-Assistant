
"""
CrewAI service for the Trend Analysis Agent.

Agent 4 consumes:
- Theme context from Agent 1
- Pain-point context from Agent 2
- Feature-cluster context from Agent 3
- Original feedback IDs and timestamps

The service uses compact upstream context and calculates weekly
trend metadata from original timestamps.

Provider-reported token usage is tracked through token_usage.py.
Temporary provider failures are retried with exponential backoff.
"""

import json
import logging
import os
import time

from collections import Counter
from datetime import date, datetime, timedelta, timezone
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task
from pydantic import BaseModel, ValidationError

from app.core.config import settings

from app.schemas.trend_analysis import (
    TrendAnalysisRequest,
    TrendAnalysisOutput,
    TrendAnalysisResult,
    IdentifiedTrend,
    WeeklyTrendPoint,
)

from app.services.token_usage import kickoff_with_token_tracking


logger = logging.getLogger(__name__)


class TrendAnalysisError(RuntimeError):
    """Raised when trend analysis fails."""


# ---------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------


def _get_retry_settings() -> tuple[int, float]:
    """
    Read retry configuration from environment variables.

    TREND_ANALYSIS_MAX_ATTEMPTS:
        Maximum number of attempts, including the first attempt.

    TREND_ANALYSIS_RETRY_DELAY_SECONDS:
        Initial delay between retry attempts.
    """

    try:
        max_attempts = int(
            os.getenv(
                "TREND_ANALYSIS_MAX_ATTEMPTS",
                "3",
            )
        )
    except ValueError:
        max_attempts = 3

    try:
        retry_delay = float(
            os.getenv(
                "TREND_ANALYSIS_RETRY_DELAY_SECONDS",
                "2",
            )
        )
    except ValueError:
        retry_delay = 2.0

    # Keep retry settings within reasonable limits.
    max_attempts = max(1, min(max_attempts, 5))
    retry_delay = max(0.0, min(retry_delay, 30.0))

    return max_attempts, retry_delay


def _is_retryable_error(exc: Exception) -> bool:
    """Determine whether a provider error is likely temporary."""

    message = str(exc).lower()

    retryable_indicators = (
        "503",
        "502",
        "504",
        "429",
        "unavailable",
        "high demand",
        "temporarily unavailable",
        "resource_exhausted",
        "rate limit",
        "rate_limit",
        "timeout",
        "timed out",
        "connection reset",
        "connection error",
        "internal server error",
        "service unavailable",
    )

    return any(
        indicator in message
        for indicator in retryable_indicators
    )


# ---------------------------------------------------------
# GEMINI CONFIGURATION
# ---------------------------------------------------------


def _create_llm() -> LLM:
    """Create the Gemini LLM used by the CrewAI agent."""

    api_key = settings.gemini_api_key
    model_name = settings.gemini_model.strip()

    if not api_key:
        raise TrendAnalysisError(
            "Gemini API key is not configured."
        )

    if not model_name:
        raise TrendAnalysisError(
            "Gemini model is not configured."
        )

    if not model_name.startswith("gemini/"):
        model_name = f"gemini/{model_name}"

    return LLM(
        model=model_name,
        api_key=api_key,
        temperature=0.2,
    )


# ---------------------------------------------------------
# CREW OUTPUT PARSING
# ---------------------------------------------------------


def _parse_crew_output(
    result: Any,
) -> TrendAnalysisOutput:
    """Convert CrewAI output into the validated Pydantic schema."""

    try:

        structured_output = getattr(
            result,
            "pydantic",
            None,
        )

        if isinstance(
            structured_output,
            TrendAnalysisOutput,
        ):
            return structured_output

        if isinstance(structured_output, BaseModel):
            return TrendAnalysisOutput.model_validate(
                structured_output.model_dump(mode="python")
            )

        if structured_output is not None:
            return TrendAnalysisOutput.model_validate(
                structured_output
            )

        json_output = getattr(
            result,
            "json_dict",
            None,
        )

        if json_output:
            return TrendAnalysisOutput.model_validate(
                json_output
            )

        raw_output = getattr(
            result,
            "raw",
            None,
        )

        if not isinstance(raw_output, str) or not raw_output.strip():
            raw_output = str(result)

        cleaned = raw_output.strip()

        # Remove Markdown code fences if Gemini returns them.
        if cleaned.startswith("```"):

            lines = cleaned.splitlines()

            if lines and lines[0].strip().startswith("```"):
                lines = lines[1:]

            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]

            cleaned = "\n".join(lines).strip()

        return TrendAnalysisOutput.model_validate_json(
            cleaned
        )

    except (ValidationError, TypeError, ValueError) as exc:

        logger.exception(
            "Could not parse trend analysis output."
        )

        raise TrendAnalysisError(
            "The AI returned an invalid trend analysis response."
        ) from exc


# ---------------------------------------------------------
# TIMESTAMP NORMALIZATION
# ---------------------------------------------------------


def _normalize_datetime(
    timestamp: datetime,
) -> datetime:
    """Normalize timezone-aware timestamps to UTC."""

    if timestamp.tzinfo is None:
        raise TrendAnalysisError(
            "Every feedback timestamp must include a timezone."
        )

    return timestamp.astimezone(timezone.utc)


def _week_start(timestamp: datetime) -> date:
    """Return the Monday date for the timestamp's UTC week."""

    current_date = timestamp.date()

    return current_date - timedelta(
        days=current_date.weekday()
    )


def _build_week_range(
    start_date: date,
    end_date: date,
) -> list[date]:
    """Return every Monday between the two dates, inclusive."""

    current_week = (
        start_date
        - timedelta(days=start_date.weekday())
    )

    final_week = (
        end_date
        - timedelta(days=end_date.weekday())
    )

    weeks = []

    while current_week <= final_week:
        weeks.append(current_week)
        current_week += timedelta(days=7)

    return weeks


# ---------------------------------------------------------
# COMPACT UPSTREAM CONTEXT
# ---------------------------------------------------------


def _serialize_context_items(
    items: list[dict[str, Any]],
    source_agent: str,
    feedback_by_id: dict[str, Any],
    all_weeks: list[date],
) -> list[dict[str, Any]]:
    """
    Build compact topic summaries from an upstream agent.

    Original feedback text is not repeated here. The upstream agent
    has already interpreted that evidence.

    Python calculates:
    - Total mentions
    - Weekly mention counts
    - Source channels
    """

    serialized = []

    for item in items:

        if not isinstance(item, dict):
            raise TrendAnalysisError(
                f"{source_agent} supplied invalid context."
            )

        topic_name = (
            item.get("name")
            or item.get("feature_name")
            or item.get("topic")
        )

        if not topic_name:
            logger.warning(
                "%s supplied a context item without a topic name.",
                source_agent,
            )
            continue

        feedback_ids = list(
            dict.fromkeys(
                item.get("feedback_ids") or []
            )
        )

        if not feedback_ids:
            continue

        unknown_ids = (
            set(feedback_ids) - set(feedback_by_id)
        )

        if unknown_ids:
            raise TrendAnalysisError(
                f"{source_agent} supplied unknown feedback IDs "
                f"for '{topic_name}': {sorted(unknown_ids)}"
            )

        weekly_counter = Counter()
        source_channels = set()

        for feedback_id in feedback_ids:

            feedback = feedback_by_id[feedback_id]

            timestamp = _normalize_datetime(
                feedback.timestamp
            )

            weekly_counter[
                _week_start(timestamp)
            ] += 1

            source_channels.add(
                feedback.source_channel
            )

        weekly_counts = [
            {
                "week_start": week.isoformat(),
                "mention_count": weekly_counter[week],
            }
            for week in all_weeks
        ]

        serialized.append(
            {
                "topic": topic_name,
                "category": item.get(
                    "category",
                    "General",
                ),
                "description": item.get(
                    "description",
                    "",
                ),
                "source_agent": source_agent,
                "total_mentions": len(feedback_ids),
                "feedback_ids": feedback_ids,
                "source_channels": sorted(source_channels),
                "weekly_counts": weekly_counts,
            }
        )

    return serialized


def _build_topic_context(
    request: TrendAnalysisRequest,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """
    Build trend topics from the three preceding agents.

    Returns:
        topic_context
        overall_weekly_activity
        legacy_feedback_data

    Raw feedback is only included as a fallback when upstream
    topic context is completely unavailable.
    """

    feedback_by_id = {
        item.feedback_id: item
        for item in request.feedback
    }

    normalized_timestamps = {
        item.feedback_id: _normalize_datetime(item.timestamp)
        for item in request.feedback
    }

    # Build the complete time range.
    all_dates = [
        timestamp.date()
        for timestamp in normalized_timestamps.values()
    ]

    all_weeks = _build_week_range(
        min(all_dates),
        max(all_dates),
    )

    # Build overall weekly feedback activity.
    weekly_activity_counter = Counter()

    for timestamp in normalized_timestamps.values():
        weekly_activity_counter[
            _week_start(timestamp)
        ] += 1

    overall_weekly_activity = [
        {
            "week_start": week.isoformat(),
            "total_feedback": weekly_activity_counter[week],
        }
        for week in all_weeks
    ]

    # Agent 1 context.
    theme_context = _serialize_context_items(
        request.theme_context,
        "Agent 1 - Theme Extraction",
        feedback_by_id,
        all_weeks,
    )

    # Agent 2 context.
    pain_context = _serialize_context_items(
        request.pain_point_context,
        "Agent 2 - Pain Point Identification",
        feedback_by_id,
        all_weeks,
    )

    # Agent 3 context.
    feature_context = _serialize_context_items(
        request.feature_context,
        "Agent 3 - Feature Clustering",
        feedback_by_id,
        all_weeks,
    )

    topic_context = (
        theme_context
        + pain_context
        + feature_context
    )

    # Backward-compatible fallback for requests without
    # any upstream context.
    legacy_feedback_data = []

    if not topic_context:

        legacy_feedback_data = [
            {
                "feedback_id": item.feedback_id,
                "source_channel": item.source_channel,
                "raw_text": item.raw_text,
                "timestamp": (
                    normalized_timestamps[item.feedback_id].isoformat()
                ),
            }
            for item in request.feedback
        ]

    return (
        topic_context,
        overall_weekly_activity,
        legacy_feedback_data,
    )


# ---------------------------------------------------------
# TREND DIRECTION CALCULATION
# ---------------------------------------------------------


def _calculate_trend_direction(
    weekly_counts: list[WeeklyTrendPoint],
) -> str:
    """
    Calculate trend direction using the first and second
    halves of the weekly counts.

    The minimum requirement is two weeks of observations.
    """

    if len(weekly_counts) < 2:
        return "Insufficient Data"

    midpoint = len(weekly_counts) // 2

    first_half = weekly_counts[:midpoint]
    second_half = weekly_counts[midpoint:]

    first_total = sum(
        point.mention_count
        for point in first_half
    )

    second_total = sum(
        point.mention_count
        for point in second_half
    )

    if first_total == 0 and second_total > 0:
        return "Emerging"

    if first_total == 0 and second_total == 0:
        return "Insufficient Data"

    if second_total > first_total:
        return "Increasing"

    if second_total < first_total:
        return "Decreasing"

    return "Stable"


# ---------------------------------------------------------
# BUILD FINAL RESULT
# ---------------------------------------------------------


def _build_result(
    output: TrendAnalysisOutput,
    request: TrendAnalysisRequest,
) -> TrendAnalysisResult:
    """
    Validate AI evidence and calculate trend metadata from original data.

    Python determines:
    - Weekly mention counts
    - Trend direction
    - Total mentions
    - Analysis period
    - Emerging topics
    - Recurring topics
    """

    feedback_by_id = {
        item.feedback_id: item
        for item in request.feedback
    }

    timestamps = [
        _normalize_datetime(item.timestamp)
        for item in request.feedback
    ]

    period_start = min(timestamps)
    period_end = max(timestamps)

    all_weeks = _build_week_range(
        period_start.date(),
        period_end.date(),
    )

    validated_trends = []

    for trend in output.trends:

        # Reject duplicate feedback IDs.
        if (
            len(trend.feedback_ids)
            != len(set(trend.feedback_ids))
        ):
            raise TrendAnalysisError(
                f"Duplicate feedback IDs found in trend: {trend.topic}"
            )

        # Reject IDs not present in original records.
        unknown_ids = (
            set(trend.feedback_ids)
            - set(feedback_by_id)
        )

        if unknown_ids:
            raise TrendAnalysisError(
                f"Unknown feedback IDs found in trend: {trend.topic}"
            )

        # Validate the LLM's mention count.
        if trend.total_mentions != len(trend.feedback_ids):
            raise TrendAnalysisError(
                f"Incorrect mention count for trend: {trend.topic}"
            )

        # Calculate weekly counts from original timestamps.
        counts_by_week = Counter()

        for feedback_id in trend.feedback_ids:

            timestamp = _normalize_datetime(
                feedback_by_id[feedback_id].timestamp
            )

            counts_by_week[
                _week_start(timestamp)
            ] += 1

        # Include zero-mention weeks for consistent analysis.
        weekly_counts = [
            WeeklyTrendPoint(
                week_start=week,
                mention_count=counts_by_week[week],
            )
            for week in all_weeks
        ]

        direction = _calculate_trend_direction(
            weekly_counts
        )

        validated_trends.append(
            IdentifiedTrend(
                topic=trend.topic,
                category=trend.category,
                description=trend.description,
                trend_direction=direction,
                total_mentions=len(trend.feedback_ids),
                weekly_counts=weekly_counts,
                feedback_ids=trend.feedback_ids,
            )
        )

    # Derive emerging and recurring topics from calculated data.
    emerging_topics = [
        trend.topic
        for trend in validated_trends
        if trend.trend_direction == "Emerging"
    ]

    recurring_topics = [
        trend.topic
        for trend in validated_trends
        if sum(
            1
            for point in trend.weekly_counts
            if point.mention_count > 0
        ) >= 2
    ]

    return TrendAnalysisResult(
        total_feedback_analyzed=len(request.feedback),
        analysis_period_start=period_start,
        analysis_period_end=period_end,
        total_trends_identified=len(validated_trends),
        trends=validated_trends,
        overall_summary=output.overall_summary,
        emerging_topics=emerging_topics,
        recurring_topics=recurring_topics,
        data_quality_notes=output.data_quality_notes,
    )


# ---------------------------------------------------------
# CREATE AGENT CREW
# ---------------------------------------------------------


def _create_trend_crew(
    llm: LLM,
) -> Crew:
    """Create a fresh CrewAI crew for one execution attempt."""

    agent = Agent(
        role="Product Feedback Trend Analyst",

        goal=(
            "Analyze themes, pain points and feature clusters produced "
            "by previous agents. Identify how these topics change over "
            "time using evidence-based weekly activity."
        ),

        backstory=(
            "You are an experienced product analytics specialist. "
            "You analyze structured findings from previous customer "
            "feedback agents to discover recurring topics, emerging "
            "concerns and changes in customer needs."
        ),

        llm=llm,
        verbose=False,
        allow_delegation=False,
    )

    task = Task(
        description="""

You are Agent 4 in a sequential product feedback analysis pipeline.

You receive structured analysis from three preceding agents.


AGENT 1 - THEME EXTRACTION:

{theme_context}


AGENT 2 - PAIN POINT IDENTIFICATION:

{pain_point_context}


AGENT 3 - FEATURE CLUSTERING:

{feature_context}


OVERALL WEEKLY FEEDBACK ACTIVITY:

{weekly_activity}


RAW FEEDBACK FALLBACK:

{feedback_data}


YOUR RESPONSIBILITIES:


PART A - ANALYZE UPSTREAM FINDINGS

1. Review the themes produced by Agent 1.

2. Review the pain points produced by Agent 2.

3. Review the feature clusters produced by Agent 3.

4. Understand how customer needs and product concerns
   relate to one another.

5. Treat upstream findings as evidence-based context,
   not unquestionable facts.


PART B - IDENTIFY TEMPORAL PATTERNS

1. Identify topics that appear repeatedly across different weeks.

2. Identify topics whose weekly frequency increases.

3. Identify topics whose weekly frequency decreases.

4. Identify emerging topics supported by the available data.

5. Distinguish stable topics from topics with insufficient evidence.

6. Use the supplied weekly counts and original feedback IDs.

7. Never invent dates, feedback IDs, counts or topics.


PART C - CONSOLIDATE TOPICS

1. Avoid identifying the same underlying issue as multiple
   unrelated trends.

2. Semantically similar topics may be consolidated.

3. Preserve distinct issues even when they belong
   to the same broader theme.

4. Do not count the same feedback ID twice inside a trend.

5. Different trends may refer to overlapping feedback
   when the feedback genuinely supports distinct topics.


PART D - STRUCTURED OUTPUT

For every trend provide:

- topic
- category
- description
- feedback_ids
- total_mentions equal to the number of feedback IDs
- trend_direction set to "Insufficient Data"
- weekly_counts as an empty list

The application calculates weekly counts and trend direction
from original feedback timestamps.

Also provide:

- overall_summary
- emerging_topics
- recurring_topics
- data_quality_notes


IMPORTANT RULES:

- Use upstream findings as the primary source of topic context.
- Use original feedback only when it is supplied as fallback.
- Do not invent customer concerns.
- Do not invent evidence or feedback IDs.
- Do not calculate fake weekly counts.
- Never claim a trend is increasing based only on one isolated mention.
- Mention data limitations when evidence is insufficient.

Return a valid structured TrendAnalysisOutput.

""",

        expected_output=(
            "A structured TrendAnalysisOutput containing evidence-based "
            "topics, original feedback IDs and an overall trend summary. "
            "Weekly counts and directions must be left for Python."
        ),

        agent=agent,
        output_pydantic=TrendAnalysisOutput,
    )

    return Crew(
        agents=[agent],
        tasks=[task],
        process=Process.sequential,
        verbose=False,
    )


# ---------------------------------------------------------
# MAIN TREND ANALYSIS EXECUTION
# ---------------------------------------------------------


def analyze_feedback_trends(
    request: TrendAnalysisRequest,
) -> TrendAnalysisResult:
    """
    Analyze feedback topics and their changes over time.

    Sequential input:
        Agent 1 themes
        Agent 2 pain points
        Agent 3 feature clusters
        Original feedback timestamps

    Returns:
        TrendAnalysisResult with Python-calculated trend metadata.
    """

    if len(request.feedback) < 2:
        raise TrendAnalysisError(
            "At least two feedback records are required for trend analysis."
        )

    try:

        # -------------------------------------------------
        # PREPARE COMPACT UPSTREAM CONTEXT
        # -------------------------------------------------

        (
            topic_context,
            overall_weekly_activity,
            legacy_feedback_data,
        ) = _build_topic_context(request)

        theme_context = [
            item
            for item in topic_context
            if item["source_agent"].startswith("Agent 1")
        ]

        pain_point_context = [
            item
            for item in topic_context
            if item["source_agent"].startswith("Agent 2")
        ]

        feature_context = [
            item
            for item in topic_context
            if item["source_agent"].startswith("Agent 3")
        ]

        logger.info(
            "Agent 4 received %d feedback records, "
            "%d themes, %d pain points and %d feature clusters.",
            len(request.feedback),
            len(theme_context),
            len(pain_point_context),
            len(feature_context),
        )

        # -------------------------------------------------
        # SERIALIZE PROMPT DATA
        # -------------------------------------------------

        inputs = {
            "theme_context": json.dumps(
                theme_context,
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "pain_point_context": json.dumps(
                pain_point_context,
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "feature_context": json.dumps(
                feature_context,
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "weekly_activity": json.dumps(
                overall_weekly_activity,
                ensure_ascii=False,
                separators=(",", ":"),
            ),

            "feedback_data": json.dumps(
                legacy_feedback_data,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        }

        # -------------------------------------------------
        # CREATE LLM
        # -------------------------------------------------

        llm = _create_llm()

        # -------------------------------------------------
        # RETRY SETTINGS
        # -------------------------------------------------

        max_attempts, retry_delay = _get_retry_settings()

        output = None
        last_error = None

        # -------------------------------------------------
        # EXECUTE WITH TOKEN TRACKING AND RETRIES
        # -------------------------------------------------

        for attempt in range(1, max_attempts + 1):

            try:

                logger.info(
                    "Starting Agent 4 attempt %d/%d.",
                    attempt,
                    max_attempts,
                )

                # Build a fresh crew for each attempt.
                crew = _create_trend_crew(llm)

                # Token usage is captured through the shared tracker.
                crew_result = kickoff_with_token_tracking(
                    crew,
                    "trend_analysis",
                    model=settings.gemini_model,
                    inputs=inputs,
                )

                output = _parse_crew_output(
                    crew_result
                )

                break

            except Exception as exc:

                last_error = exc

                retryable = _is_retryable_error(exc)

                if (
                    not retryable
                    or attempt >= max_attempts
                ):
                    logger.exception(
                        "Agent 4 failed on attempt %d/%d.",
                        attempt,
                        max_attempts,
                    )
                    raise

                delay = min(
                    retry_delay * (2 ** (attempt - 1)),
                    30.0,
                )

                logger.warning(
                    "Agent 4 encountered a temporary provider error. "
                    "Retrying attempt %d/%d in %.1f seconds. Error: %s",
                    attempt + 1,
                    max_attempts,
                    delay,
                    exc,
                )

                time.sleep(delay)

        if output is None:
            raise TrendAnalysisError(
                "Trend analysis did not produce a valid output."
            ) from last_error

        # -------------------------------------------------
        # BUILD FINAL RESULT
        # -------------------------------------------------

        final_result = _build_result(
            output,
            request,
        )

        logger.info(
            "Agent 4 completed: %d feedback records, "
            "%d trends identified.",
            final_result.total_feedback_analyzed,
            final_result.total_trends_identified,
        )

        return final_result

    except TrendAnalysisError:
        raise

    except Exception as exc:

        logger.exception(
            "Trend analysis failed."
        )

        raise TrendAnalysisError(
            "Trend analysis could not be completed."
        ) from exc
