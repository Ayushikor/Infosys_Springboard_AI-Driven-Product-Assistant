from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.schemas.feedback import FeedbackAnalysis
from app.services.feedback_analyzer import FeedbackAnalysisError


client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "ai_module"}


def test_analyze_feedback_returns_analysis() -> None:
    analysis = FeedbackAnalysis(
        sentiment="positive",
        category="usability",
        pain_points=[],
        feature_requests=["Add dark mode"],
        summary="The user likes the app and requests dark mode.",
    )
    with patch(
        "app.main.feedback_analyzer.analyze_feedback",
        return_value=analysis,
    ) as analyze:
        response = client.post(
            "/feedback/analyze",
            json={"text": "I like the app. Please add dark mode."},
        )

    assert response.status_code == 200
    assert response.json() == analysis.model_dump()
    analyze.assert_called_once_with("I like the app. Please add dark mode.")


def test_analyze_feedback_returns_safe_error_for_service_failure() -> None:
    with patch(
        "app.main.feedback_analyzer.analyze_feedback",
        side_effect=FeedbackAnalysisError("provider details and secrets"),
    ):
        response = client.post(
            "/feedback/analyze",
            json={"text": "The app is slow."},
        )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Feedback analysis is temporarily unavailable."
    }
    assert "provider details and secrets" not in response.text
