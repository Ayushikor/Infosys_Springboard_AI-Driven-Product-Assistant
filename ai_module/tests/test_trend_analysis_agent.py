
from datetime import datetime
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.trend_analysis import (
    TrendFeedbackItem,
    TrendAnalysisRequest,
    IdentifiedTrend,
    TrendAnalysisOutput,
)
from app.services import trend_analysis_agent as agent_module
from app.services.trend_analysis_agent import (
    TrendAnalysisError,
    _build_result,
)


def create_request():
    return TrendAnalysisRequest(
        feedback=[
            TrendFeedbackItem(
                feedback_id="FB-001",
                source_channel="App Review",
                raw_text="Checkout is slow.",
                timestamp="2026-10-05T10:00:00+05:30",
            ),
            TrendFeedbackItem(
                feedback_id="FB-002",
                source_channel="Support Ticket",
                raw_text="Checkout takes too long.",
                timestamp="2026-10-12T10:00:00+05:30",
            ),
            TrendFeedbackItem(
                feedback_id="FB-003",
                source_channel="App Review",
                raw_text="Checkout loading is slow.",
                timestamp="2026-10-13T10:00:00+05:30",
            ),
        ]
    )


def create_trend(*feedback_ids):
    return IdentifiedTrend(
        topic="Slow Checkout",
        category="Performance",
        description="Customers report slow checkout performance.",
        trend_direction="Insufficient Data",
        total_mentions=len(feedback_ids),
        weekly_counts=[],
        feedback_ids=list(feedback_ids),
    )


def create_output():
    return TrendAnalysisOutput(
        trends=[
            create_trend("FB-001", "FB-002", "FB-003")
        ],
        overall_summary="Checkout performance complaints increased.",
        recurring_topics=["Slow Checkout"],
        data_quality_notes=[],
    )


def test_valid_trend_analysis_request():
    request = create_request()

    assert len(request.feedback) == 3


def test_duplicate_feedback_ids_rejected():
    with pytest.raises(ValidationError):
        TrendAnalysisRequest(
            feedback=[
                TrendFeedbackItem(
                    feedback_id="FB-001",
                    source_channel="App Review",
                    raw_text="Slow checkout.",
                    timestamp="2026-10-05T10:00:00+05:30",
                ),
                TrendFeedbackItem(
                    feedback_id="FB-001",
                    source_channel="Support Ticket",
                    raw_text="Checkout is slow.",
                    timestamp="2026-10-06T10:00:00+05:30",
                ),
            ]
        )


def test_increasing_trend_direction():
    result = _build_result(create_output(), create_request())

    trend = result.trends[0]

    assert trend.trend_direction == "Increasing"
    assert trend.total_mentions == 3


def test_weekly_counts_calculated_from_timestamps():
    result = _build_result(create_output(), create_request())

    weekly_counts = result.trends[0].weekly_counts

    assert len(weekly_counts) == 2
    assert weekly_counts[0].mention_count == 1
    assert weekly_counts[1].mention_count == 2


def test_unknown_feedback_id_rejected():
    request = create_request()

    output = TrendAnalysisOutput(
        trends=[
            create_trend("FB-001", "FB-999")
        ],
        overall_summary="Test summary.",
    )

    with pytest.raises(TrendAnalysisError):
        _build_result(output, request)


def test_duplicate_feedback_ids_within_trend_rejected():
    request = create_request()

    output = TrendAnalysisOutput(
        trends=[
            create_trend("FB-001", "FB-001")
        ],
        overall_summary="Test summary.",
    )

    with pytest.raises(TrendAnalysisError):
        _build_result(output, request)


def test_feedback_not_belonging_to_a_trend_is_allowed():
    request = create_request()

    output = TrendAnalysisOutput(
        trends=[
            create_trend("FB-001")
        ],
        overall_summary="Only one recurring topic was identified.",
    )

    result = _build_result(output, request)

    assert result.total_feedback_analyzed == 3
    assert result.total_trends_identified == 1
    assert result.trends[0].feedback_ids == ["FB-001"]


def test_naive_timestamp_rejected():
    request = TrendAnalysisRequest(
        feedback=[
            TrendFeedbackItem(
                feedback_id="FB-001",
                source_channel="App Review",
                raw_text="Slow checkout.",
                timestamp=datetime(2026, 10, 5, 10, 0),
            ),
            TrendFeedbackItem(
                feedback_id="FB-002",
                source_channel="Support Ticket",
                raw_text="Checkout is slow.",
                timestamp=datetime(2026, 10, 6, 10, 0),
            ),
        ]
    )

    output = TrendAnalysisOutput(
        trends=[],
        overall_summary="Test summary.",
    )

    with pytest.raises(TrendAnalysisError):
        _build_result(output, request)


def test_agent_execution_with_mocked_crewai(monkeypatch):
    fake_output = create_output()

    monkeypatch.setattr(
        agent_module,
        "_create_llm",
        lambda: object(),
    )

    monkeypatch.setattr(
        agent_module,
        "Agent",
        lambda **kwargs: object(),
    )

    monkeypatch.setattr(
        agent_module,
        "Task",
        lambda **kwargs: object(),
    )

    class FakeCrew:
        def __init__(self, **kwargs):
            pass

        def kickoff(self):
            return SimpleNamespace(pydantic=fake_output)

    monkeypatch.setattr(
        agent_module,
        "Crew",
        FakeCrew,
    )

    request = create_request()

    result = agent_module.analyze_feedback_trends(request)

    assert result.total_feedback_analyzed == 3
    assert result.total_trends_identified == 1
    assert result.trends[0].topic == "Slow Checkout"
    assert result.trends[0].trend_direction == "Increasing"
