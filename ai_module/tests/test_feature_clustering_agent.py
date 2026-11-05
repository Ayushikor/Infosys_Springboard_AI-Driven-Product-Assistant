
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.feature_clustering import (
    FeatureFeedbackItem,
    FeatureClusteringRequest,
    FeatureCluster,
    FeatureClusteringOutput,
    build_result,
)
from app.services import feature_clustering_agent as agent_module
from app.services.feature_clustering_agent import (
    FeatureClusteringError,
    _validate_feedback_assignments,
)


def create_cluster(feedback_ids):
    return FeatureCluster(
        feature_name="Dark Mode",
        description="Customers want a dark mode option.",
        category="UI",
        mention_count=len(feedback_ids),
        feedback_ids=feedback_ids,
        source_channels=["App Review", "Support Ticket"],
    )


def create_request():
    return FeatureClusteringRequest(
        feedback=[
            FeatureFeedbackItem(
                feedback_id="FB-001",
                source_channel="App Review",
                raw_text="Please add dark mode.",
            ),
            FeatureFeedbackItem(
                feedback_id="FB-002",
                source_channel="Support Ticket",
                raw_text="A dark theme would be useful.",
            ),
            FeatureFeedbackItem(
                feedback_id="FB-003",
                source_channel="Customer Feedback",
                raw_text="The application looks great.",
            ),
        ]
    )


def test_valid_feature_clustering_request():
    request = create_request()

    assert len(request.feedback) == 3


def test_duplicate_feedback_ids_rejected():
    with pytest.raises(ValidationError):
        FeatureClusteringRequest(
            feedback=[
                FeatureFeedbackItem(
                    feedback_id="FB-001",
                    source_channel="App Review",
                    raw_text="Add dark mode.",
                ),
                FeatureFeedbackItem(
                    feedback_id="FB-001",
                    source_channel="Support Ticket",
                    raw_text="Add dark theme.",
                ),
            ]
        )


def test_valid_feature_assignments():
    request = create_request()

    output = FeatureClusteringOutput(
        feature_clusters=[
            create_cluster(["FB-001", "FB-002"])
        ],
        unclustered_feedback_ids=["FB-003"],
    )

    _validate_feedback_assignments(output, request)


def test_missing_feedback_assignment_rejected():
    request = create_request()

    output = FeatureClusteringOutput(
        feature_clusters=[
            create_cluster(["FB-001"])
        ],
        unclustered_feedback_ids=["FB-003"],
    )

    with pytest.raises(FeatureClusteringError):
        _validate_feedback_assignments(output, request)


def test_unknown_feedback_id_rejected():
    request = create_request()

    output = FeatureClusteringOutput(
        feature_clusters=[
            create_cluster(["FB-001", "FB-999"])
        ],
        unclustered_feedback_ids=["FB-003"],
    )

    with pytest.raises(FeatureClusteringError):
        _validate_feedback_assignments(output, request)


def test_duplicate_assignment_rejected():
    request = create_request()

    output = FeatureClusteringOutput(
        feature_clusters=[
            create_cluster(["FB-001", "FB-002"])
        ],
        unclustered_feedback_ids=["FB-002", "FB-003"],
    )

    with pytest.raises(FeatureClusteringError):
        _validate_feedback_assignments(output, request)


def test_build_result_recalculates_source_channels():
    request = create_request()

    output = FeatureClusteringOutput(
        feature_clusters=[
            FeatureCluster(
                feature_name="Dark Mode",
                description="Customers want dark mode.",
                category="UI",
                mention_count=2,
                feedback_ids=["FB-001", "FB-002"],
                source_channels=[],
            )
        ],
        unclustered_feedback_ids=["FB-003"],
    )

    result = build_result(request, output)

    assert result.total_feedback_analyzed == 3
    assert result.total_feature_clusters == 1
    assert result.total_feature_requests == 2

    assert result.clusters[0].source_channels == [
        "App Review",
        "Support Ticket",
    ]

    assert result.unclustered_feedback_ids == ["FB-003"]


def test_agent_execution_with_mocked_crewai(monkeypatch):
    fake_output = FeatureClusteringOutput(
        feature_clusters=[
            create_cluster(["FB-001", "FB-002"])
        ],
        unclustered_feedback_ids=["FB-003"],
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
            pass

        def kickoff(self):
            return SimpleNamespace(pydantic=fake_output)

    monkeypatch.setattr(agent_module, "Crew", FakeCrew)

    request = create_request()

    result = agent_module.identify_feature_clusters(request)

    assert result.total_feedback_analyzed == 3
    assert result.total_feature_clusters == 1
    assert result.total_feature_requests == 2
    assert result.clusters[0].feature_name == "Dark Mode"
    assert result.unclustered_feedback_ids == ["FB-003"]
