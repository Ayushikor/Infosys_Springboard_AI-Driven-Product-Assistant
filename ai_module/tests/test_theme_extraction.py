
import pytest
from pydantic import ValidationError

from app.schemas.theme_extraction import (
    FeedbackItem,
    ThemeExtractionRequest,
    ThemeExtractionOutput,
)

from app.services.theme_extraction_agent import (
    ThemeExtractionError,
    _validate_theme_assignments,
)


def test_valid_feedback_request():
    request = ThemeExtractionRequest(
        feedback=[
            FeedbackItem(id="FB-001", title="Slow loading"),
            FeedbackItem(id="FB-002", title="App is slow"),
        ]
    )
    assert len(request.feedback) == 2


def test_duplicate_feedback_ids_rejected():
    with pytest.raises(ValidationError):
        ThemeExtractionRequest(
            feedback=[
                FeedbackItem(id="FB-001", title="Slow loading"),
                FeedbackItem(id="FB-001", title="App is slow"),
            ]
        )


def test_valid_theme_assignments():
    result = ThemeExtractionOutput(
        themes=[
            {
                "name": "Performance",
                "description": "Application speed issues",
                "keywords": ["slow loading"],
                "feedback_ids": ["FB-001", "FB-002"],
            }
        ]
    )

    _validate_theme_assignments(result, {"FB-001", "FB-002"})


def test_missing_feedback_assignment_rejected():
    result = ThemeExtractionOutput(
        themes=[
            {
                "name": "Performance",
                "description": "Application speed issues",
                "keywords": ["slow loading"],
                "feedback_ids": ["FB-001"],
            }
        ]
    )

    with pytest.raises(ThemeExtractionError):
        _validate_theme_assignments(result, {"FB-001", "FB-002"})


def test_unknown_feedback_id_rejected():
    result = ThemeExtractionOutput(
        themes=[
            {
                "name": "Performance",
                "description": "Application speed issues",
                "keywords": ["slow loading"],
                "feedback_ids": ["FB-999"],
            }
        ]
    )

    with pytest.raises(ThemeExtractionError):
        _validate_theme_assignments(result, {"FB-001"})

from types import SimpleNamespace
import app.services.theme_extraction_agent as agent_module


def test_agent_execution_without_api_key(monkeypatch):
    fake_output = ThemeExtractionOutput(
        themes=[
            {
                "name": "Performance",
                "description": "Application speed issues",
                "keywords": ["slow loading"],
                "feedback_ids": ["FB-001", "FB-002"],
            }
        ]
    )

    monkeypatch.setattr(
        agent_module, "_create_llm", lambda: object()
    )
    monkeypatch.setattr(
        agent_module, "Agent", lambda **kwargs: object()
    )
    monkeypatch.setattr(
        agent_module, "Task", lambda **kwargs: object()
    )

    class FakeCrew:
        def __init__(self, **kwargs):
            pass

        def kickoff(self, inputs):
            return SimpleNamespace(pydantic=fake_output)

    monkeypatch.setattr(agent_module, "Crew", FakeCrew)

    request = ThemeExtractionRequest(
        feedback=[
            FeedbackItem(id="FB-001", title="Slow loading"),
            FeedbackItem(id="FB-002", title="Pages load slowly"),
        ]
    )

    result = agent_module.extract_themes(request)

    assert result.total_feedback_analyzed == 2
    assert len(result.themes) == 1
    assert result.themes[0].name == "Performance"