
from types import SimpleNamespace

import pytest

from app.schemas.theme_extraction import (
    ExtractedTheme,
    ThemeExtractionResult,
)
from app.services import orchestrator


# ---------------------------------------------------------
# SAMPLE DATA
# ---------------------------------------------------------


def sample_records():
    return [
        {
            "feedback_id": "FB-001",
            "id": "FB-001",
            "title": "Slow application",
            "message": "The application is slow.",
            "raw_text": "The application is slow.",
            "source_channel": "Customer Feedback",
            "timestamp": "2026-10-05T10:00:00+00:00",
            "dataset": "customer_feedback",
        },
        {
            "feedback_id": "REV-001",
            "id": "REV-001",
            "title": "Dark mode",
            "message": "Please add dark mode.",
            "raw_text": "Please add dark mode.",
            "source_channel": "App Review",
            "timestamp": "2026-10-12T10:00:00+00:00",
            "dataset": "user_reviews",
        },
        {
            "feedback_id": "TKT-001",
            "id": "TKT-001",
            "title": "Export problem",
            "message": "Please improve export options.",
            "raw_text": "Please improve export options.",
            "source_channel": "Support Ticket",
            "timestamp": "2026-10-13T10:00:00+00:00",
            "dataset": "support_tickets",
        },
    ]


# ---------------------------------------------------------
# MOCK AGENT RESULTS
# ---------------------------------------------------------


def fake_theme_result():
    """Return a valid Agent 1 result."""

    return ThemeExtractionResult(
        total_feedback_analyzed=3,
        themes=[
            ExtractedTheme(
                name="Dark Mode",
                description="Customers request dark appearance options.",
                keywords=["dark mode", "dark theme"],
                feedback_ids=["REV-001"],
            )
        ],
    )


def fake_pain_result():
    """Return an Agent 2 result with a feature-request candidate."""

    pain_point = SimpleNamespace(
        name="Limited Appearance Options",
        category="Usability",
        severity="Medium",
        description="Users want additional appearance options.",
        feedback_ids=["REV-001"],
    )

    return SimpleNamespace(
        total_feedback_analyzed=3,
        pain_points=[pain_point],
        non_pain_feedback_ids=["FB-001", "TKT-001"],
        uncertain_feedback_ids=[],
        feature_request_feedback_ids=["REV-001"],
        model_dump=lambda mode="json": {
            "total_feedback_analyzed": 3,
            "pain_points": [
                {
                    "name": "Limited Appearance Options",
                    "category": "Usability",
                    "severity": "Medium",
                    "description": "Users want additional appearance options.",
                    "feedback_ids": ["REV-001"],
                }
            ],
            "non_pain_feedback_ids": ["FB-001", "TKT-001"],
            "uncertain_feedback_ids": [],
            "feature_request_feedback_ids": ["REV-001"],
        },
    )


def fake_feature_result():
    """Return an Agent 3 result."""

    cluster = SimpleNamespace(
        feature_name="Dark Mode",
        description="Customers want a dark mode option.",
        category="UI",
        mention_count=1,
        feedback_ids=["REV-001"],
    )

    return SimpleNamespace(
        total_feedback_analyzed=1,
        total_feature_clusters=1,
        total_feature_requests=1,
        clusters=[cluster],
        unclustered_feedback_ids=[],
        model_dump=lambda mode="json": {
            "total_feedback_analyzed": 1,
            "total_feature_clusters": 1,
            "total_feature_requests": 1,
            "clusters": [
                {
                    "feature_name": "Dark Mode",
                    "description": "Customers want a dark mode option.",
                    "category": "UI",
                    "mention_count": 1,
                    "feedback_ids": ["REV-001"],
                    "source_channels": ["App Review"],
                }
            ],
            "unclustered_feedback_ids": [],
        },
    )


def fake_trend_result():
    """Return an Agent 4 result."""

    return SimpleNamespace(
        total_feedback_analyzed=3,
        total_trends_identified=1,
        model_dump=lambda mode="json": {
            "total_feedback_analyzed": 3,
            "total_trends_identified": 1,
            "trends": [],
        },
    )


# ---------------------------------------------------------
# TEST 1: ALL FOUR AGENTS EXECUTE SEQUENTIALLY
# ---------------------------------------------------------


def test_orchestrator_executes_all_four_agents(monkeypatch):

    records = sample_records()
    calls = []

    monkeypatch.setattr(
        orchestrator,
        "load_feedback_dataset",
        lambda: records,
    )

    def fake_theme(request):

        calls.append(
            ("themes", len(request.feedback))
        )

        return fake_theme_result()

    def fake_pain(request):

        calls.append(
            (
                "pain_points",
                len(request.feedback),
                bool(request.theme_context),
            )
        )

        return fake_pain_result()

    def fake_features(request):

        calls.append(
            (
                "features",
                len(request.feedback),
                bool(request.theme_context),
                bool(request.pain_point_context),
            )
        )

        return fake_feature_result()

    def fake_trends(request):

        calls.append(
            (
                "trends",
                len(request.feedback),
                bool(request.theme_context),
                bool(request.pain_point_context),
                bool(request.feature_context),
            )
        )

        return fake_trend_result()

    monkeypatch.setattr(
        orchestrator.theme_extraction_agent,
        "extract_themes",
        fake_theme,
    )

    monkeypatch.setattr(
        orchestrator.pain_point_agent,
        "identify_pain_points",
        fake_pain,
    )

    monkeypatch.setattr(
        orchestrator.feature_clustering_agent,
        "identify_feature_clusters",
        fake_features,
    )

    monkeypatch.setattr(
        orchestrator.trend_analysis_agent,
        "analyze_feedback_trends",
        fake_trends,
    )

    result = orchestrator.run_all_analyses()

    assert result["success"] is True
    assert result["status"] == "completed"

    assert result["total_feedback_analyzed"] == 3

    assert result["source_counts"] == {
        "customer_feedback": 1,
        "user_reviews": 1,
        "support_tickets": 1,
    }

    assert result["agent_status"] == {
        "themes": "completed",
        "pain_points": "completed",
        "feature_clusters": "completed",
        "trends": "completed",
    }

    # Confirm actual sequential handoffs.
    assert calls == [
        ("themes", 3),
        ("pain_points", 3, True),
        ("features", 1, True, True),
        ("trends", 3, True, True, True),
    ]


# ---------------------------------------------------------
# TEST 2: DOWNSTREAM AGENTS SKIPPED AFTER FAILURE
# ---------------------------------------------------------


def test_orchestrator_skips_downstream_if_agent_1_fails(
    monkeypatch,
):

    calls = []

    monkeypatch.setattr(
        orchestrator,
        "load_feedback_dataset",
        sample_records,
    )

    def failing_theme(request):

        calls.append("themes")

        raise RuntimeError(
            "Mocked Agent 1 failure"
        )

    def fake_pain(request):

        calls.append("pain_points")
        return fake_pain_result()

    def fake_features(request):

        calls.append("features")
        return fake_feature_result()

    def fake_trends(request):

        calls.append("trends")
        return fake_trend_result()

    monkeypatch.setattr(
        orchestrator.theme_extraction_agent,
        "extract_themes",
        failing_theme,
    )

    monkeypatch.setattr(
        orchestrator.pain_point_agent,
        "identify_pain_points",
        fake_pain,
    )

    monkeypatch.setattr(
        orchestrator.feature_clustering_agent,
        "identify_feature_clusters",
        fake_features,
    )

    monkeypatch.setattr(
        orchestrator.trend_analysis_agent,
        "analyze_feedback_trends",
        fake_trends,
    )

    result = orchestrator.run_all_analyses()

    assert result["success"] is False
    assert result["status"] == "partial_success"

    assert result["agent_status"] == {
        "themes": "failed",
        "pain_points": "skipped_dependency",
        "feature_clusters": "skipped_dependency",
        "trends": "skipped_dependency",
    }

    # No downstream agent should execute.
    assert calls == ["themes"]

    assert result["results"]["themes"] is None
    assert result["results"]["pain_points"] is None
    assert result["results"]["feature_clusters"] is None
    assert result["results"]["trends"] is None


# ---------------------------------------------------------
# TEST 3: MALFORMED AGENT RESULT MUST NOT FLOW DOWNSTREAM
# ---------------------------------------------------------


def test_orchestrator_skips_downstream_after_invalid_theme_result(
    monkeypatch,
):

    calls = []

    monkeypatch.setattr(
        orchestrator,
        "load_feedback_dataset",
        sample_records,
    )

    def invalid_theme(request):

        calls.append("themes")

        # Simulates an agent returning an object without the
        # required themes field.
        return SimpleNamespace(
            unexpected_field="invalid"
        )

    def fake_pain(request):

        calls.append("pain_points")
        return fake_pain_result()

    monkeypatch.setattr(
        orchestrator.theme_extraction_agent,
        "extract_themes",
        invalid_theme,
    )

    monkeypatch.setattr(
        orchestrator.pain_point_agent,
        "identify_pain_points",
        fake_pain,
    )

    result = orchestrator.run_all_analyses()

    assert result["status"] == "partial_success"

    assert result["agent_status"]["themes"] == "failed"

    assert result["agent_status"]["pain_points"] == "skipped_dependency"

    assert result["agent_status"]["feature_clusters"] == "skipped_dependency"

    assert result["agent_status"]["trends"] == "skipped_dependency"

    assert calls == ["themes"]


# ---------------------------------------------------------
# TEST 4: DATASET SIZE LIMIT
# ---------------------------------------------------------


def test_orchestrator_rejects_more_than_500_records(
    monkeypatch,
):

    records = sample_records() * 167

    monkeypatch.setattr(
        orchestrator,
        "load_feedback_dataset",
        lambda: records,
    )

    with pytest.raises(
        orchestrator.OrchestrationError,
        match="500-record",
    ):

        orchestrator.run_all_analyses()
