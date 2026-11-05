
from types import SimpleNamespace
from datetime import datetime, timezone

import pytest

from app.services import orchestrator


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


def fake_result(name):
    return SimpleNamespace(
        model_dump=lambda mode="python": {
            "agent": name,
            "status": "mocked_success",
        }
    )


def test_orchestrator_executes_all_four_agents(monkeypatch):
    records = sample_records()
    calls = []

    monkeypatch.setattr(
        orchestrator,
        "load_feedback_dataset",
        lambda: records,
    )

    def fake_theme(request):
        calls.append(("themes", len(request.feedback)))
        return fake_result("themes")

    def fake_pain(request):
        calls.append(("pain_points", len(request.feedback)))
        return fake_result("pain_points")

    def fake_features(request):
        calls.append(("features", len(request.feedback)))
        return fake_result("features")

    def fake_trends(request):
        calls.append(("trends", len(request.feedback)))
        return fake_result("trends")

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
    assert result["total_feedback_analyzed"] == 3

    assert result["source_counts"] == {
        "customer_feedback": 1,
        "user_reviews": 1,
        "support_tickets": 1,
    }

    assert len(result["results"]) == 4

    assert calls == [
        ("themes", 3),
        ("pain_points", 3),
        ("features", 3),
        ("trends", 3),
    ]


def test_orchestrator_stops_if_an_agent_fails(monkeypatch):
    monkeypatch.setattr(
        orchestrator,
        "load_feedback_dataset",
        sample_records,
    )

    def failing_agent(request):
        raise RuntimeError("Mocked agent failure")

    monkeypatch.setattr(
        orchestrator.theme_extraction_agent,
        "extract_themes",
        failing_agent,
    )

    with pytest.raises(
        orchestrator.OrchestrationError,
        match="Agent 1",
    ):
        orchestrator.run_all_analyses()


def test_orchestrator_rejects_more_than_500_records(monkeypatch):
    records = sample_records() * 167

    monkeypatch.setattr(
        orchestrator,
        "load_feedback_dataset",
        lambda: records,
    )

    with pytest.raises(
        orchestrator.OrchestrationError,
        match="maximum of 500",
    ):
        orchestrator.run_all_analyses()
