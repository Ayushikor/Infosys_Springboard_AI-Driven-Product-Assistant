from app.schemas.prd import PRDGenerationOutput, PRDGenerationRequest, build_prd_result
from app.schemas.user_story import (
    UserStoryGenerationOutput,
    UserStoryGenerationRequest,
    build_user_story_result,
)


def _request_and_prd():
    request = PRDGenerationRequest(
        product_name="Demo",
        feature={
            "feature_name": "Login",
            "description": "Account sign-in",
            "category": "Authentication",
            "mention_count": 2,
            "feedback_ids": ["FB-1", "FB-2"],
        },
        feedback=[
            {"feedback_id": "FB-1", "raw_text": "Login fails"},
            {"feedback_id": "FB-2", "raw_text": "Need password reset"},
        ],
    )
    prd = PRDGenerationOutput(
        title="Login PRD",
        executive_summary="Improve account access.",
        problem_statement="Users cannot reliably access accounts.",
        proposed_solution="Provide reliable sign-in and password reset.",
        objectives=["Improve account access"],
        scope={"in_scope": ["Sign in", "Password reset"], "out_of_scope": []},
        functional_requirements=[
            {"requirement_id": "FR-001", "title": "Sign in", "description": "Allow account sign-in.", "priority": "Must Have", "source_feedback_ids": ["FB-1"]},
            {"requirement_id": "FR-002", "title": "Password reset", "description": "Allow password reset.", "priority": "Should Have", "source_feedback_ids": ["FB-2"]},
        ],
    )
    return request, prd


def test_prd_rejects_feedback_ids_outside_selected_feature():
    request, prd = _request_and_prd()
    bad = prd.model_copy(update={
        "functional_requirements": [
            prd.functional_requirements[0].model_copy(update={"source_feedback_ids": ["NOT-REAL"]})
        ]
    })
    try:
        build_prd_result(request, bad, "prd-test")
    except ValueError as exc:
        assert "outside the selected feature" in str(exc)
    else:
        raise AssertionError("Unknown feedback ID was accepted")


def test_story_inherits_priority_and_feedback_traceability():
    _, prd = _request_and_prd()
    output = UserStoryGenerationOutput(user_stories=[{
        "story_id": "US-001",
        "title": "Sign in",
        "user_type": "Customer",
        "user_story": "As a customer, I want to sign in, so that I can access my account.",
        "requirement_ids": ["FR-001"],
        "priority": "Could Have",
        "acceptance_criteria": [{"criterion_id": "AC-001", "given": "I have an active account", "when": "I submit valid credentials", "then": "I am signed in"}],
    }])
    result = build_user_story_result(UserStoryGenerationRequest(product_name="Demo", prd=prd), output)
    story = result.user_stories[0]
    assert story.priority == "Must Have"
    assert story.source_feedback_ids == ["FB-1"]


def test_story_rejects_unknown_requirement_reference():
    _, prd = _request_and_prd()
    output = UserStoryGenerationOutput(user_stories=[{
        "story_id": "US-001",
        "title": "Sign in",
        "user_type": "Customer",
        "user_story": "As a customer, I want to sign in, so that I can access my account.",
        "requirement_ids": ["FR-999"],
        "priority": "Must Have",
        "acceptance_criteria": [{"criterion_id": "AC-001", "given": "I have an account", "when": "I sign in", "then": "I access my account"}],
    }])
    try:
        build_user_story_result(UserStoryGenerationRequest(product_name="Demo", prd=prd), output)
    except ValueError as exc:
        assert "unknown PRD requirements" in str(exc)
    else:
        raise AssertionError("Unknown requirement ID was accepted")
