"""
CrewAI service for the Trend Analysis Agent.

Analyzes changes in customer feedback topics over time.
"""

import json
import logging
from collections import Counter
from datetime import date, datetime, timedelta
from typing import Any

from crewai import Agent, Crew, LLM, Process, Task

from app.core.config import settings
from app.schemas.trend_analysis import (
    TrendAnalysisRequest,
    TrendAnalysisOutput,
    TrendAnalysisResult,
    IdentifiedTrend,
    WeeklyTrendPoint,
)

logger = logging.getLogger(__name__)


class TrendAnalysisError(Exception):
    """Raised when trend analysis fails."""


def _create_llm() -> LLM:
    """Create the Gemini LLM used by the CrewAI agent."""

    api_key = settings.gemini_api_key
    model_name = settings.gemini_model.strip()

    if not api_key:
        raise TrendAnalysisError(
            "Gemini API key is not configured."
        )

    if not model_name.startswith("gemini/"):
        model_name = f"gemini/{model_name}"

    return LLM(
        model=model_name,
        api_key=api_key,
        temperature=0.2,
    )


def _parse_crew_output(result: Any) -> TrendAnalysisOutput:
    """Convert CrewAI output into the validated Pydantic schema."""

    try:
        if getattr(result, "pydantic", None) is not None:
            return TrendAnalysisOutput.model_validate(
                result.pydantic
            )

        if getattr(result, "json_dict", None):
            return TrendAnalysisOutput.model_validate(
                result.json_dict
            )

        raw_output = getattr(result, "raw", str(result))
        parsed = json.loads(raw_output)

        return TrendAnalysisOutput.model_validate(parsed)

    except Exception as exc:
        logger.exception("Could not parse trend analysis output.")

        raise TrendAnalysisError(
            "The AI returned an invalid trend analysis response."
        ) from exc


def _week_start(timestamp: datetime) -> date:
    """Return the Monday date for the timestamp's week."""

    current_date = timestamp.date()
    return current_date - timedelta(days=current_date.weekday())


def _normalize_datetime(timestamp: datetime) -> datetime:
    """Normalize timestamps to UTC for consistent comparison."""

    if timestamp.tzinfo is None:
        raise TrendAnalysisError(
            "Every feedback timestamp must include a timezone."
        )

    return timestamp.astimezone(
        datetime.now().astimezone().tzinfo
    )


def _calculate_trend_direction(
    weekly_counts: list[WeeklyTrendPoint],
) -> str:
    """
    Calculate trend direction using the first and second
    halves of the observed weekly counts.
    """

    if len(weekly_counts) < 2:
        return "Insufficient Data"

    midpoint = len(weekly_counts) // 2

    first_half = weekly_counts[:midpoint]
    second_half = weekly_counts[midpoint:]

    first_total = sum(point.mention_count for point in first_half)
    second_total = sum(point.mention_count for point in second_half)

    if first_total == 0 and second_total > 0:
        return "Emerging"

    if first_total == 0 and second_total == 0:
        return "Insufficient Data"

    if second_total > first_total:
        return "Increasing"

    if second_total < first_total:
        return "Decreasing"

    return "Stable"


def _build_result(
    output: TrendAnalysisOutput,
    request: TrendAnalysisRequest,
) -> TrendAnalysisResult:
    """Validate AI evidence and calculate counts from real timestamps."""

    feedback_by_id = {
        item.feedback_id: item
        for item in request.feedback
    }

    validated_trends = []

    for trend in output.trends:
        if len(trend.feedback_ids) != len(set(trend.feedback_ids)):
            raise TrendAnalysisError(
                f"Duplicate feedback IDs found in trend: {trend.topic}"
            )

        unknown_ids = set(trend.feedback_ids) - set(feedback_by_id)

        if unknown_ids:
            raise TrendAnalysisError(
                f"Unknown feedback IDs found in trend: {trend.topic}"
            )

        if trend.total_mentions != len(trend.feedback_ids):
            raise TrendAnalysisError(
                f"Incorrect mention count for trend: {trend.topic}"
            )

        # Calculate weekly counts from the original timestamps.
        counts_by_week = Counter()

        for feedback_id in trend.feedback_ids:
            timestamp = _normalize_datetime(
                feedback_by_id[feedback_id].timestamp
            )
            counts_by_week[_week_start(timestamp)] += 1

        weekly_counts = [
            WeeklyTrendPoint(
                week_start=week,
                mention_count=counts_by_week[week],
            )
            for week in sorted(counts_by_week)
        ]

        # Calculate direction from actual weekly counts.
        direction = _calculate_trend_direction(weekly_counts)

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

    timestamps = [
        _normalize_datetime(item.timestamp)
        for item in request.feedback
    ]

    return TrendAnalysisResult(
        total_feedback_analyzed=len(request.feedback),
        analysis_period_start=min(timestamps),
        analysis_period_end=max(timestamps),
        total_trends_identified=len(validated_trends),
        trends=validated_trends,
        overall_summary=output.overall_summary,
        emerging_topics=[
            trend.topic
            for trend in validated_trends
            if trend.trend_direction == "Emerging"
        ],
        recurring_topics=output.recurring_topics,
        data_quality_notes=output.data_quality_notes,
    )


def analyze_feedback_trends(
    request: TrendAnalysisRequest,
) -> TrendAnalysisResult:
    """
    Analyze feedback topics and their changes over time.

    Args:
        request: Feedback records with timestamps.

    Returns:
        TrendAnalysisResult containing identified trends.
    """

    try:
        llm = _create_llm()

        agent = Agent(
            role="Product Feedback Trend Analyst",
            goal=(
                "Identify recurring feedback topics and explain "
                "how customer concerns change over time."
            ),
            backstory=(
                "You are an experienced product analytics specialist. "
                "You analyze customer feedback, user reviews, and "
                "support tickets to discover recurring topics and "
                "changes in customer concerns."
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
                "timestamp": item.timestamp.isoformat(),
            }
            for item in request.feedback
        ]

        task = Task(
            description=f"""
Analyze the following feedback records.

FEEDBACK DATA:
{json.dumps(feedback_data, ensure_ascii=False)}

YOUR RESPONSIBILITIES:

1. Read all feedback records.

2. Identify meaningful recurring topics and concerns.

3. Group feedback records that discuss the same topic.

4. Use timestamps to understand when topics appeared.

5. Identify topics that appear repeatedly across different
   dates or weeks.

6. Identify emerging topics only when the data supports them.

7. Do not invent feedback IDs, dates, counts, or evidence.

8. For every trend:
   - Provide a short topic name.
   - Provide a category.
   - Explain the observed pattern.
   - Include the original feedback IDs.
   - Set total_mentions equal to the number of IDs.
   - Set weekly_counts to an empty list.
   - Use "Insufficient Data" for trend_direction.
     The application calculates weekly counts and trend direction
     from the original timestamps.

9. Do not call a topic increasing or decreasing based only
   on one isolated mention.

10. Mention limitations in data_quality_notes when the
    available dates or records are insufficient.

11. Provide an overall summary of the feedback patterns.

12. Include recurring topic names in recurring_topics.

Return a valid structured TrendAnalysisOutput.
""",
            expected_output=(
                "A structured TrendAnalysisOutput containing "
                "feedback trends, evidence IDs, and a summary."
            ),
            agent=agent,
            output_pydantic=TrendAnalysisOutput,
        )

        crew = Crew(
            agents=[agent],
            tasks=[task],
            process=Process.sequential,
            verbose=False,
        )

        result = crew.kickoff()

        output = _parse_crew_output(result)

        return _build_result(output, request)

    except TrendAnalysisError:
        raise

    except Exception as exc:
        logger.exception("Trend analysis failed.")

        raise TrendAnalysisError(
            "Trend analysis could not be completed."
        ) from exc