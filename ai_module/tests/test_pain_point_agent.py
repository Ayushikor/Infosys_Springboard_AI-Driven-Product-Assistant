
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.theme_extraction import FeedbackItem
from app.schemas.pain_point import (
    PainPointExtractionRequest,
    PainPointExtractionOutput,
    IdentifiedPainPoint,
)
from app.services import pain_point_agent as agent_module
from app.services.pain_point_agent import (
    PainPointExtractionError,
    _validate_pain_point_assignments,
)


def create_pain_point(*feedback_ids):
    return IdentifiedPainPoint(
        name="Slow Application",
        category="Performance",
        severity="High",
        description="Customers experience slow application loading.",
        feedback_ids=list(feedback_ids),
        evidence=[
            "The application takes too long to load."
        ],
    )


def test_valid_pain_point_request():
    request = PainPointExtractionRequest(
        feedback=[
            FeedbackItem(
                id="FB-001",
                title="App is slow",
            ),
            FeedbackItem(
                id="FB-002",
                title="Loading takes too long",
            ),
        ]
    )

    assert len(request.feedback) == 2


def test_duplicate_feedback_ids_rejected():
    with pytest.raises(ValidationError):
        PainPointExtractionRequest(
            feedback=[
                FeedbackItem(
                    id="FB-001",
                    title="App is slow",
                ),
                FeedbackItem(
                    id="FB-001",
                    title="App crashes",
                ),
            ]
        )


def test_invalid_severity_rejected():
    with pytest.raises(ValidationError):
        IdentifiedPainPoint(
            name="Slow Application",
            category="Performance",
            severity="Critical",
            description="Application loads slowly.",
            feedback_ids=["FB-001"],
            evidence=["Very slow loading."],
        )


def test_valid_pain_point_assignments():
    result = PainPointExtractionOutput(
        pain_points=[
            create_pain_point("FB-001", "FB-002")
        ]
    )

    _validate_pain_point_assignments(
        result,
        {"FB-001", "FB-002"},
    )


def test_missing_feedback_added_to_uncertain_classification():
    result = PainPointExtractionOutput(
        pain_points=[
            create_pain_point("FB-001")
        ]
    )

    input_evidence = {
        "FB-001": "App loads slowly.",
        "FB-002": "The interface looks great.",
    }

    _validate_pain_point_assignments(
        result,
        {"FB-001", "FB-002"},
        input_evidence,
    )

    assert "FB-002" in result.uncertain_feedback_ids

    pain_point_ids = {
        feedback_id
        for point in result.pain_points
        for feedback_id in point.feedback_ids
    }

    assert "FB-001" in pain_point_ids
    assert "FB-002" not in pain_point_ids

    assert not any(
        point.name == "Other / Unclassified - Review Required"
        for point in result.pain_points
    )


def test_unknown_feedback_id_rejected():
    result = PainPointExtractionOutput(
        pain_points=[
            create_pain_point("FB-999")
        ]
    )

    with pytest.raises(PainPointExtractionError):
        _validate_pain_point_assignments(
            result,
            {"FB-001"},
        )


def test_duplicate_feedback_assignment_rejected():
    result = PainPointExtractionOutput(
        pain_points=[
            create_pain_point("FB-001"),
            create_pain_point("FB-001"),
        ]
    )

    with pytest.raises(PainPointExtractionError):
        _validate_pain_point_assignments(
            result,
            {"FB-001"},
        )


def test_agent_execution_with_mocked_crewai(monkeypatch):
    fake_output = PainPointExtractionOutput(
        pain_points=[
            create_pain_point("FB-001", "FB-002")
        ]
    )

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
            self.kwargs = kwargs

        def kickoff(self, inputs):
            assert "feedback_records" in inputs
            return SimpleNamespace(pydantic=fake_output)

    monkeypatch.setattr(
        agent_module,
        "Crew",
        FakeCrew,
    )

    request = PainPointExtractionRequest(
        feedback=[
            FeedbackItem(
                id="FB-001",
                title="App loads slowly",
            ),
            FeedbackItem(
                id="FB-002",
                title="Loading is frustrating",
            ),
        ]
    )

    result = agent_module.identify_pain_points(request)

    assert result.total_feedback_analyzed == 2
    assert len(result.pain_points) == 1
    assert result.pain_points[0].name == "Slow Application"
