import json
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.schemas.feedback import FeedbackAnalysis
from app.services import feedback_analyzer


with Path(__file__).with_name("feedback_dataset.json").open() as dataset_file:
    FEEDBACK_DATASET: List[Dict[str, Any]] = json.load(dataset_file)


@pytest.mark.parametrize(
    "example",
    FEEDBACK_DATASET,
    ids=[example["name"] for example in FEEDBACK_DATASET],
)
def test_feedback_examples_produce_expected_schema_offline(
    example: Dict[str, Any],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.models.generate_content.return_value.text = json.dumps(
        example["analysis"]
    )
    monkeypatch.setattr(feedback_analyzer.settings, "gemini_api_key", "offline-test-key")
    monkeypatch.setattr(feedback_analyzer.settings, "gemini_model", "offline-test-model")
    client_factory = MagicMock(return_value=mock_client)
    monkeypatch.setattr(feedback_analyzer.genai, "Client", client_factory)

    result = feedback_analyzer.analyze_feedback(example["text"])

    assert isinstance(result, FeedbackAnalysis)
    assert result.model_dump() == example["analysis"]
    mock_client.models.generate_content.assert_called_once()
    assert example["text"] in mock_client.models.generate_content.call_args.kwargs["contents"]


@pytest.mark.parametrize("text", ["", "   ", "\n\t "])
def test_whitespace_feedback_is_rejected_before_provider_call(
    text: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client_factory = MagicMock()
    monkeypatch.setattr(feedback_analyzer.genai, "Client", client_factory)

    with pytest.raises(ValidationError):
        feedback_analyzer.analyze_feedback(text)

    client_factory.assert_not_called()


def test_very_long_feedback_uses_mocked_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    text = "Long feedback. " * 5000
    analysis = FEEDBACK_DATASET[0]["analysis"]
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.models.generate_content.return_value.text = json.dumps(analysis)
    monkeypatch.setattr(feedback_analyzer.settings, "gemini_api_key", "offline-test-key")
    client_factory = MagicMock(return_value=mock_client)
    monkeypatch.setattr(feedback_analyzer.genai, "Client", client_factory)

    result = feedback_analyzer.analyze_feedback(text)

    assert isinstance(result, FeedbackAnalysis)
    prompt = mock_client.models.generate_content.call_args.kwargs["contents"]
    assert prompt.endswith(text.strip())
    assert len(text.strip()) > 50000


def test_multiple_feature_requests_are_preserved(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    example = next(
        item for item in FEEDBACK_DATASET if item["name"] == "multiple feature requests"
    )
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.models.generate_content.return_value.text = json.dumps(
        example["analysis"]
    )
    monkeypatch.setattr(feedback_analyzer.settings, "gemini_api_key", "offline-test-key")
    monkeypatch.setattr(
        feedback_analyzer.genai,
        "Client",
        MagicMock(return_value=mock_client),
    )

    result = feedback_analyzer.analyze_feedback(example["text"])

    assert result.feature_requests == [
        "Add CSV export",
        "Allow scheduling weekly reports",
    ]
