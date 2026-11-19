
"""
Pydantic schemas for the Trend Analysis Agent.

Agent 4 consumes:
- Original feedback records and timestamps
- Theme context from Agent 1
- Pain-point context from Agent 2
- Feature-cluster context from Agent 3

Analyzes how customer feedback topics change over time.
"""

from datetime import datetime, date
from typing import Any, Literal

from pydantic import (
    BaseModel,
    Field,
    ConfigDict,
    model_validator,
)


# ---------------------------------------------------------
# ORIGINAL FEEDBACK
# ---------------------------------------------------------


class TrendFeedbackItem(BaseModel):
    """One feedback record used for trend analysis."""

    model_config = ConfigDict(extra="forbid")

    feedback_id: str = Field(
        ...,
        min_length=1,
        description="Original feedback ID.",
    )

    source_channel: str = Field(
        ...,
        min_length=1,
        description="Original feedback source.",
    )

    raw_text: str = Field(
        ...,
        min_length=1,
        description="Original feedback text.",
    )

    timestamp: datetime = Field(
        ...,
        description="Date and time when feedback was received.",
    )


# ---------------------------------------------------------
# AGENT 4 REQUEST
# ---------------------------------------------------------


class TrendAnalysisRequest(BaseModel):
    """
    Original feedback plus structured context from Agents 1, 2 and 3.
    """

    model_config = ConfigDict(extra="forbid")

    feedback: list[TrendFeedbackItem] = Field(
        ...,
        min_length=2,
        max_length=500,
    )

    theme_context: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Theme summaries produced by Agent 1.",
    )

    pain_point_context: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Pain-point summaries produced by Agent 2.",
    )

    feature_context: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Feature-cluster summaries produced by Agent 3.",
    )

    @model_validator(mode="after")
    def validate_request(self):
        """Validate feedback IDs and upstream context references."""

        feedback_ids = [
            item.feedback_id
            for item in self.feedback
        ]

        if len(feedback_ids) != len(set(feedback_ids)):
            raise ValueError(
                "Duplicate feedback IDs are not allowed."
            )

        valid_ids = set(feedback_ids)

        contexts = (
            ("theme_context", self.theme_context),
            ("pain_point_context", self.pain_point_context),
            ("feature_context", self.feature_context),
        )

        for context_name, context_items in contexts:

            for context in context_items:

                if not isinstance(context, dict):
                    raise ValueError(
                        f"{context_name} entries must be dictionaries."
                    )

                context_ids = context.get("feedback_ids", [])

                if not isinstance(context_ids, list):
                    raise ValueError(
                        f"{context_name} feedback_ids must be a list."
                    )

                unknown_ids = set(context_ids) - valid_ids

                if unknown_ids:
                    raise ValueError(
                        f"{context_name} contains feedback IDs "
                        f"not present in the original dataset: "
                        f"{sorted(unknown_ids)}"
                    )

        return self


# ---------------------------------------------------------
# WEEKLY TREND DATA
# ---------------------------------------------------------


class WeeklyTrendPoint(BaseModel):
    """Feedback count for a particular week."""

    model_config = ConfigDict(extra="forbid")

    week_start: date = Field(
        ...,
        description="Monday of the week.",
    )

    mention_count: int = Field(
        ...,
        ge=0,
        description="Number of feedback mentions during that week.",
    )


# ---------------------------------------------------------
# IDENTIFIED TREND
# ---------------------------------------------------------


class IdentifiedTrend(BaseModel):
    """One topic whose feedback changes over time."""

    model_config = ConfigDict(extra="forbid")

    topic: str = Field(
        ...,
        min_length=1,
        description="Name of the feedback topic.",
    )

    category: str = Field(
        ...,
        min_length=1,
        description="Category of the topic.",
    )

    description: str = Field(
        ...,
        min_length=1,
        description="Explanation of the observed trend.",
    )

    trend_direction: Literal[
        "Increasing",
        "Decreasing",
        "Stable",
        "Emerging",
        "Insufficient Data",
    ] = Field(
        ...,
        description="Direction of the feedback trend.",
    )

    total_mentions: int = Field(
        ...,
        ge=1,
        description="Total feedback mentions for this topic.",
    )

    weekly_counts: list[WeeklyTrendPoint] = Field(
        default_factory=list,
        description="Weekly feedback counts for this topic.",
    )

    feedback_ids: list[str] = Field(
        ...,
        min_length=1,
        description="Original feedback IDs supporting the trend.",
    )

    @model_validator(mode="after")
    def validate_unique_feedback_ids(self):

        if len(self.feedback_ids) != len(set(self.feedback_ids)):
            raise ValueError(
                "Duplicate feedback IDs inside a trend."
            )

        return self


# ---------------------------------------------------------
# GEMINI OUTPUT
# ---------------------------------------------------------


class TrendAnalysisOutput(BaseModel):
    """Structured output generated by the AI agent."""

    model_config = ConfigDict(extra="forbid")

    trends: list[IdentifiedTrend] = Field(
        default_factory=list,
        description="Topics and their observed trends.",
    )

    overall_summary: str = Field(
        ...,
        min_length=1,
        description="Overall summary of feedback trends.",
    )

    emerging_topics: list[str] = Field(
        default_factory=list,
        description="Topics appearing as new or growing concerns.",
    )

    recurring_topics: list[str] = Field(
        default_factory=list,
        description="Topics repeatedly mentioned over time.",
    )

    data_quality_notes: list[str] = Field(
        default_factory=list,
        description="Limitations or observations about the data.",
    )


# ---------------------------------------------------------
# FINAL TREND RESULT
# ---------------------------------------------------------


class TrendAnalysisResult(BaseModel):
    """Final result returned by the Trend Analysis service."""

    model_config = ConfigDict(extra="forbid")

    total_feedback_analyzed: int = Field(
        ...,
        ge=0,
    )

    analysis_period_start: datetime

    analysis_period_end: datetime

    total_trends_identified: int = Field(
        ...,
        ge=0,
    )

    trends: list[IdentifiedTrend] = Field(
        default_factory=list,
    )

    overall_summary: str = Field(
        ...,
        min_length=1,
    )

    emerging_topics: list[str] = Field(
        default_factory=list,
    )

    recurring_topics: list[str] = Field(
        default_factory=list,
    )

    data_quality_notes: list[str] = Field(
        default_factory=list,
    )

    @model_validator(mode="after")
    def validate_analysis_period(self):

        if self.analysis_period_start > self.analysis_period_end:
            raise ValueError(
                "Analysis start date cannot be after end date."
            )

        if self.total_trends_identified != len(self.trends):
            raise ValueError(
                "Total trend count does not match the trends list."
            )

        return self
