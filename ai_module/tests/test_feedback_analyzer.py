from unittest.mock import MagicMock

import pytest
from google.genai import errors

from app.schemas.feedback import FeedbackAnalysis
from app.services import feedback_analyzer


VALID_RESPONSE = (
    '{"sentiment":"negative","category":"checkout",'
    '"pain_points":["Checkout is slow"],'
    '"feature_requests":["Add guest checkout"],'
    '"summary":"The checkout experience is slow and needs guest checkout."}'
)


@pytest.fixture
def mock_gemini(monkeypatch: pytest.MonkeyPatch) -> MagicMock:
    monkeypatch.setattr(feedback_analyzer.settings, "gemini_api_key", "test-api-key")
    monkeypatch.setattr(feedback_analyzer.settings, "gemini_model", "test-model")

    client = MagicMock()
    client.__enter__.return_value = client
    client.models.generate_content.return_value.text = VALID_RESPONSE
    monkeypatch.setattr(feedback_analyzer.genai, "Client", MagicMock(return_value=client))
    return client


def test_analyze_feedback_returns_validated_analysis(
    mock_gemini: MagicMock,
) -> None:
    analysis = feedback_analyzer.analyze_feedback("Checkout is slow.")

    assert isinstance(analysis, FeedbackAnalysis)
    assert analysis.sentiment == "negative"
    assert analysis.feature_requests == ["Add guest checkout"]

    call = mock_gemini.models.generate_content.call_args
    assert call.kwargs["model"] == "test-model"
    assert call.kwargs["config"].response_mime_type == "application/json"
    assert call.kwargs["config"].response_schema is FeedbackAnalysis


def test_analyze_feedback_rejects_malformed_json(
    mock_gemini: MagicMock,
) -> None:
    mock_gemini.models.generate_content.return_value.text = "not JSON"

    with pytest.raises(feedback_analyzer.FeedbackAnalysisError, match="malformed JSON"):
        feedback_analyzer.analyze_feedback("Checkout is slow.")


def test_analyze_feedback_rejects_invalid_analysis_schema(
    mock_gemini: MagicMock,
) -> None:
    mock_gemini.models.generate_content.return_value.text = (
        '{"sentiment":"mixed","category":"checkout","pain_points":[],'
        '"feature_requests":[],"summary":"Mixed sentiment."}'
    )

    with pytest.raises(feedback_analyzer.FeedbackAnalysisError, match="does not match"):
        feedback_analyzer.analyze_feedback("Checkout is slow.")


def test_analyze_feedback_handles_provider_errors_without_exposing_details(
    mock_gemini: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    mock_gemini.models.generate_content.side_effect = errors.APIError(
        500,
        {"message": "provider failure: test-api-key user-feedback-secret"},
    )

    with pytest.raises(
        feedback_analyzer.FeedbackAnalysisError,
        match="Gemini provider request failed",
    ) as error:
        feedback_analyzer.analyze_feedback(
            "Feedback includes user-feedback-secret."
        )

    assert "test-api-key" not in str(error.value)
    assert "test-api-key" not in caplog.text
    assert "user-feedback-secret" not in caplog.text
    assert "APIError" in caplog.text
    assert "status=500" in caplog.text
    assert "category=provider_availability" in caplog.text
    assert "Gemini provider returned a server error" in caplog.text


def test_analyze_feedback_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    monkeypatch.setattr(feedback_analyzer.settings, "gemini_api_key", None)
    client_factory = MagicMock()
    monkeypatch.setattr(feedback_analyzer.genai, "Client", client_factory)

    with pytest.raises(
        feedback_analyzer.FeedbackAnalysisError,
        match="API key is not configured",
    ):
        feedback_analyzer.analyze_feedback("Checkout is slow.")

    client_factory.assert_not_called()
    assert "Gemini configuration failure" in caplog.text
    assert "API key is not configured" in caplog.text
    assert "Checkout is slow." not in caplog.text
