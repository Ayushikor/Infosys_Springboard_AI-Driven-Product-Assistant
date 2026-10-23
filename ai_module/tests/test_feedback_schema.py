import pytest
from pydantic import ValidationError

from app.schemas.feedback import FeedbackAnalysis, FeedbackRequest


def test_feedback_request_accepts_non_empty_text() -> None:
    request = FeedbackRequest(text="The checkout process was confusing.")

    assert request.text == "The checkout process was confusing."


@pytest.mark.parametrize("text", ["", "   "])
def test_feedback_request_rejects_empty_text(text: str) -> None:
    with pytest.raises(ValidationError):
        FeedbackRequest(text=text)


def test_feedback_analysis_accepts_valid_data() -> None:
    analysis = FeedbackAnalysis(
        sentiment="positive",
        category="usability",
        pain_points=[],
        feature_requests=["Add dark mode"],
        summary="The user likes the product and requests dark mode.",
    )

    assert analysis.sentiment == "positive"
    assert analysis.feature_requests == ["Add dark mode"]


def test_feedback_analysis_rejects_invalid_sentiment() -> None:
    with pytest.raises(ValidationError):
        FeedbackAnalysis(
            sentiment="mixed",
            category="usability",
            pain_points=[],
            feature_requests=[],
            summary="Feedback summary.",
        )
