from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


AGENT_STATUS = {
    "themes": "completed",
    "pain_points": "completed",
    "feature_clusters": "completed",
    "trends": "completed",
}


def make_batch(feedback_ids):
    return {
        "success": True,
        "status": "completed",
        "total_feedback_analyzed": len(feedback_ids),
        "agent_status": AGENT_STATUS,
        "errors": {},
        "execution_order": [
            "Agent 1",
            "Agent 2",
            "Agent 3",
            "Agent 4",
        ],
        "data_flow": {},
        "token_usage": {"total_tokens": 100},
        "_feedback_ids": feedback_ids,
        "results": {
            "themes": {
                "themes": [
                    {
                        "name": "Performance",
                        "description": "Application speed issues",
                        "keywords": ["slow", "loading"],
                        "feedback_ids": feedback_ids,
                    }
                ]
            },
            "pain_points": {
                "pain_points": [],
            },
            "feature_clusters": {
                "total_feedback_analyzed": len(feedback_ids),
                "total_feature_clusters": 0,
                "total_feature_requests": 0,
                "clusters": [],
                "unclustered_feedback_ids": feedback_ids,
            },
            "trends": {
                "total_feedback_analyzed": len(feedback_ids),
                "total_trends_identified": 0,
                "trends": [],
                "analysis_period_start": "2026-01-01",
                "analysis_period_end": "2026-01-07",
                "overall_summary": "No trends identified.",
                "emerging_topics": [],
                "recurring_topics": [],
                "data_quality_notes": [],
            },
        },
    }


def test_aggregate_two_batches_without_gemini():
    response = client.post(
        "/analysis/aggregate-batches",
        json={
            "total_feedback_analyzed": 4,
            "source_counts": {
                "customer_feedback": 4,
            },
            "batch_size": 2,
            "batch_responses": [
                make_batch(["FB-001", "FB-002"]),
                make_batch(["FB-003", "FB-004"]),
            ],
        },
    )

    assert response.status_code == 200

    result = response.json()

    assert result["success"] is True
    assert result["status"] == "completed"
    assert result["total_feedback_analyzed"] == 4

    assert result["batch_summary"]["total_batches"] == 2
    assert result["batch_summary"]["completed_batches"] == 2

    themes = result["results"]["themes"]["themes"]

    assert len(themes) == 1
    assert len(themes[0]["feedback_ids"]) == 4

    assert result["token_usage"]["total_tokens"] == 200


def test_aggregation_rejects_wrong_source_count():
    response = client.post(
        "/analysis/aggregate-batches",
        json={
            "total_feedback_analyzed": 4,
            "source_counts": {
                "customer_feedback": 3,
            },
            "batch_size": 2,
            "batch_responses": [
                make_batch(["FB-001", "FB-002"]),
                make_batch(["FB-003", "FB-004"]),
            ],
        },
    )

    assert response.status_code == 422


def test_aggregation_rejects_missing_batch():
    response = client.post(
        "/analysis/aggregate-batches",
        json={
            "total_feedback_analyzed": 4,
            "source_counts": {
                "customer_feedback": 4,
            },
            "batch_size": 2,
            "batch_responses": [
                make_batch(["FB-001", "FB-002"]),
            ],
        },
    )

    assert response.status_code == 422