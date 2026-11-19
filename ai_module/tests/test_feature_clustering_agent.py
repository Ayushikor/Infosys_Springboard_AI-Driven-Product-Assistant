
from types import SimpleNamespace
import json

import pytest
from pydantic import ValidationError

from app.schemas.feature_clustering import (
    FeatureFeedbackItem,
    FeatureThemeContext,
    FeaturePainPointContext,
    FeatureClusteringRequest,
    FeatureClusterDraft,
    FeatureClusteringOutput,
    build_result,
)

from app.services import feature_clustering_agent as agent_module

from app.services.feature_clustering_agent import (
    FeatureClusteringError,
    _validate_feedback_assignments,
    _normalize_duplicate_assignments,
)


# ---------------------------------------------------------
# TEST HELPERS
# ---------------------------------------------------------

def create_draft(*feedback_ids):
    """Create Gemini-style feature cluster output."""

    return FeatureClusterDraft(
        feature_name="Dark Mode",
        description="Customers want a dark mode option.",
        category="UI",
        feedback_ids=list(feedback_ids),
    )


def create_request():
    """Create a sample request with Agent 1 and Agent 2 context."""

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
        ],

        theme_context=[
            FeatureThemeContext(
                name="User Interface",
                description="Feedback about application appearance.",
                keywords=["UI", "design", "appearance"],
                feedback_ids=["FB-001", "FB-002"],
            )
        ],

        pain_point_context=[
            FeaturePainPointContext(
                name="Limited Appearance Options",
                category="Usability",
                severity="Medium",
                description="Users want more appearance customization.",
                feedback_ids=["FB-001", "FB-002"],
            )
        ],
    )


def create_internal_output(
    clusters,
    unclustered=None,
):
    """Create permissive internal Gemini output."""

    return agent_module._LLMFeatureClusteringOutput(
        feature_clusters=clusters,
        unclustered_feedback_ids=unclustered or [],
    )


def create_internal_cluster(
    name,
    feedback_ids,
):
    return agent_module._LLMFeatureCluster(
        feature_name=name,
        description=f"Customers request {name}.",
        category="UI",
        feedback_ids=feedback_ids,
    )


# ---------------------------------------------------------
# REQUEST VALIDATION TESTS
# ---------------------------------------------------------

def test_valid_feature_clustering_request():

    request = create_request()

    assert len(request.feedback) == 3
    assert len(request.theme_context) == 1
    assert len(request.pain_point_context) == 1


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


def test_unknown_context_feedback_ids_rejected():

    with pytest.raises(ValidationError):

        FeatureClusteringRequest(
            feedback=[
                FeatureFeedbackItem(
                    feedback_id="FB-001",
                    source_channel="App Review",
                    raw_text="Add dark mode.",
                )
            ],

            theme_context=[
                FeatureThemeContext(
                    name="User Interface",
                    description="Appearance feedback.",
                    keywords=["UI"],
                    feedback_ids=["FB-999"],
                )
            ],
        )


# ---------------------------------------------------------
# FEATURE ASSIGNMENT TESTS
# ---------------------------------------------------------

def test_valid_feature_assignments():

    request = create_request()

    output = FeatureClusteringOutput(
        feature_clusters=[
            create_draft("FB-001", "FB-002")
        ],
        unclustered_feedback_ids=["FB-003"],
    )

    missing_ids = _validate_feedback_assignments(
        output,
        request,
    )

    assert missing_ids == []


def test_missing_feedback_assignment_preserved_as_unclustered():

    request = create_request()

    output = FeatureClusteringOutput(
        feature_clusters=[
            create_draft("FB-001")
        ],
        unclustered_feedback_ids=["FB-003"],
    )

    missing_ids = _validate_feedback_assignments(
        output,
        request,
    )

    assert missing_ids == ["FB-002"]

    result = build_result(request, output)

    assert set(result.unclustered_feedback_ids) == {
        "FB-002",
        "FB-003",
    }


def test_unknown_feedback_id_rejected():

    request = create_request()

    output = FeatureClusteringOutput(
        feature_clusters=[
            create_draft("FB-001", "FB-999")
        ],
        unclustered_feedback_ids=["FB-003"],
    )

    with pytest.raises(FeatureClusteringError):

        _validate_feedback_assignments(
            output,
            request,
        )


def test_duplicate_assignment_rejected():

    with pytest.raises(ValidationError):

        FeatureClusteringOutput(
            feature_clusters=[
                create_draft("FB-001", "FB-002")
            ],
            unclustered_feedback_ids=[
                "FB-002",
                "FB-003",
            ],
        )


def test_duplicate_assignment_across_clusters_rejected():

    with pytest.raises(ValidationError):

        FeatureClusteringOutput(
            feature_clusters=[
                create_draft("FB-001"),
                create_draft("FB-001"),
            ],
            unclustered_feedback_ids=[
                "FB-002",
                "FB-003",
            ],
        )


# ---------------------------------------------------------
# DUPLICATE RECOVERY TESTS
# ---------------------------------------------------------

def test_duplicate_ids_inside_one_cluster_are_deduplicated():

    raw_output = create_internal_output(
        clusters=[
            create_internal_cluster(
                "Dark Mode",
                ["FB-001", "FB-001", "FB-002"],
            )
        ]
    )

    output = _normalize_duplicate_assignments(raw_output)

    assert output.feature_clusters[0].feedback_ids == [
        "FB-001",
        "FB-002",
    ]

    assert output.unclustered_feedback_ids == []


def test_duplicate_ids_across_clusters_are_preserved_unclustered():

    raw_output = create_internal_output(
        clusters=[
            create_internal_cluster(
                "Mobile Notifications",
                ["FB-001", "FB-002"],
            ),
            create_internal_cluster(
                "Notification Preferences",
                ["FB-001", "FB-003"],
            ),
        ]
    )

    output = _normalize_duplicate_assignments(raw_output)

    assigned_ids = [
        feedback_id
        for cluster in output.feature_clusters
        for feedback_id in cluster.feedback_ids
    ]

    assert "FB-001" in output.unclustered_feedback_ids
    assert "FB-001" not in assigned_ids

    assert set(assigned_ids) == {
        "FB-002",
        "FB-003",
    }

    assert len(assigned_ids) == len(set(assigned_ids))


def test_cluster_and_unclustered_overlap_preserved_unclustered():

    raw_output = create_internal_output(
        clusters=[
            create_internal_cluster(
                "Dark Mode",
                ["FB-001", "FB-002"],
            )
        ],
        unclustered=["FB-001"],
    )

    output = _normalize_duplicate_assignments(raw_output)

    assigned_ids = [
        feedback_id
        for cluster in output.feature_clusters
        for feedback_id in cluster.feedback_ids
    ]

    assert "FB-001" not in assigned_ids
    assert "FB-001" in output.unclustered_feedback_ids

    assert output.feature_clusters[0].feedback_ids == [
        "FB-002"
    ]


def test_empty_clusters_removed_after_duplicate_recovery():

    raw_output = create_internal_output(
        clusters=[
            create_internal_cluster(
                "Feature A",
                ["FB-001"],
            ),
            create_internal_cluster(
                "Feature B",
                ["FB-001"],
            ),
        ]
    )

    output = _normalize_duplicate_assignments(raw_output)

    assert output.feature_clusters == []
    assert output.unclustered_feedback_ids == ["FB-001"]


# ---------------------------------------------------------
# FINAL RESULT TESTS
# ---------------------------------------------------------

def test_build_result_recalculates_metadata():

    request = create_request()

    output = FeatureClusteringOutput(
        feature_clusters=[
            create_draft("FB-001", "FB-002")
        ],
        unclustered_feedback_ids=["FB-003"],
    )

    result = build_result(
        request=request,
        output=output,
    )

    assert result.total_feedback_analyzed == 3

    assert result.total_feature_clusters == 1

    assert result.total_feature_requests == 2

    assert result.clusters[0].mention_count == 2

    assert result.clusters[0].source_channels == [
        "App Review",
        "Support Ticket",
    ]

    assert result.unclustered_feedback_ids == ["FB-003"]


def test_build_result_rejects_unknown_feedback_ids():

    request = create_request()

    output = FeatureClusteringOutput(
        feature_clusters=[
            create_draft("FB-001", "FB-999")
        ],
        unclustered_feedback_ids=["FB-002", "FB-003"],
    )

    with pytest.raises(ValueError):

        build_result(
            request=request,
            output=output,
        )


# ---------------------------------------------------------
# MOCKED AGENT EXECUTION TEST
# ---------------------------------------------------------

def test_agent_execution_with_mocked_crewai(monkeypatch):

    fake_output = FeatureClusteringOutput(
        feature_clusters=[
            create_draft("FB-001", "FB-002")
        ],
        unclustered_feedback_ids=["FB-003"],
    )

    # Mock Gemini configuration.
    monkeypatch.setattr(
        agent_module,
        "_create_llm",
        lambda: object(),
    )

    # Mock CrewAI agent.
    monkeypatch.setattr(
        agent_module,
        "Agent",
        lambda **kwargs: object(),
    )

    # Mock CrewAI task.
    monkeypatch.setattr(
        agent_module,
        "Task",
        lambda **kwargs: object(),
    )

    # Mock Crew.
    class FakeCrew:

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(
        agent_module,
        "Crew",
        FakeCrew,
    )

    # Mock token-tracked CrewAI execution.
    def fake_kickoff_with_tracking(
        crew,
        agent_name,
        model=None,
        inputs=None,
    ):

        assert agent_name == "feature_clustering"
        assert inputs is not None

        assert "feedback_data" in inputs
        assert "theme_context" in inputs
        assert "pain_point_context" in inputs

        # Verify Agent 1 context.
        theme_data = json.loads(
            inputs["theme_context"]
        )

        assert theme_data[0]["name"] == "User Interface"

        # Verify Agent 2 context.
        pain_data = json.loads(
            inputs["pain_point_context"]
        )

        assert pain_data[0]["name"] == "Limited Appearance Options"

        return SimpleNamespace(
            pydantic=fake_output
        )

    monkeypatch.setattr(
        agent_module,
        "kickoff_with_token_tracking",
        fake_kickoff_with_tracking,
    )

    request = create_request()

    result = agent_module.identify_feature_clusters(
        request
    )

    assert result.total_feedback_analyzed == 3
    assert result.total_feature_clusters == 1
    assert result.total_feature_requests == 2

    assert result.clusters[0].feature_name == "Dark Mode"
    assert result.clusters[0].mention_count == 2

    assert result.unclustered_feedback_ids == ["FB-003"]


# ---------------------------------------------------------
# RETRY CONFIGURATION TESTS
# ---------------------------------------------------------

def test_retryable_gemini_503_detected():

    error = RuntimeError(
        "503 UNAVAILABLE: model currently experiencing high demand"
    )

    assert agent_module._is_retryable_error(error) is True


def test_invalid_output_error_not_treated_as_retryable():

    error = FeatureClusteringError(
        "The AI returned an invalid feature clustering response."
    )

    assert agent_module._is_retryable_error(error) is False
