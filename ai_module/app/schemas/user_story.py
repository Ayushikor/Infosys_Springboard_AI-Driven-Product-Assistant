"""Pydantic schemas for traceable user stories and acceptance criteria."""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from app.schemas.prd import PRDGenerationOutput, Priority

class AcceptanceCriterion(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    criterion_id: str = Field(..., min_length=1)
    given: str = Field(..., min_length=1)
    when: str = Field(..., min_length=1)
    then: str = Field(..., min_length=1)

    @field_validator("criterion_id", "given", "when", "then")
    @classmethod
    def clean_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Acceptance criterion fields cannot be empty.")
        return value

class UserStory(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    story_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    user_type: str = Field(..., min_length=1)
    user_story: str = Field(..., min_length=1, description="As a [user], I want [capability], so that [benefit].")
    requirement_ids: list[str] = Field(..., min_length=1)
    priority: Priority
    acceptance_criteria: list[AcceptanceCriterion] = Field(..., min_length=1)
    source_feedback_ids: list[str] = Field(default_factory=list, description="Derived from linked PRD requirements; never independently invented by the story agent.")
    dependencies: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)

    @field_validator("requirement_ids", "source_feedback_ids", "dependencies", "notes")
    @classmethod
    def clean_lists(cls, values: list[str]) -> list[str]:
        cleaned = [v.strip() for v in values]
        if any(not v for v in cleaned):
            raise ValueError("List entries cannot be empty.")
        return list(dict.fromkeys(cleaned))

    @model_validator(mode="after")
    def validate_story(self):
        ids = [c.criterion_id for c in self.acceptance_criteria]
        if len(ids) != len(set(ids)):
            raise ValueError("Acceptance criterion IDs must be unique within a story.")
        if self.story_id in self.dependencies:
            raise ValueError("A user story cannot depend on itself.")
        return self

class UserStoryGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_name: str = Field(..., min_length=1)
    prd: PRDGenerationOutput

class UserStoryGenerationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_stories: list[UserStory] = Field(..., min_length=1)
    generation_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_story_graph(self):
        ids = [s.story_id for s in self.user_stories]
        if len(ids) != len(set(ids)):
            raise ValueError("User story IDs must be unique.")
        known = set(ids)
        graph = {story.story_id: set(story.dependencies) for story in self.user_stories}
        for story_id, dependencies in graph.items():
            unknown = dependencies - known
            if unknown:
                raise ValueError(f"Story '{story_id}' references unknown dependencies: {sorted(unknown)}")

        # Reject cycles so a generated implementation plan is schedulable.
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(story_id: str) -> None:
            if story_id in visiting:
                raise ValueError("User story dependencies must not contain cycles.")
            if story_id in visited:
                return
            visiting.add(story_id)
            for dependency in graph[story_id]:
                visit(dependency)
            visiting.remove(story_id)
            visited.add(story_id)

        for story_id in graph:
            visit(story_id)
        return self

class UserStoryGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_name: str = Field(..., min_length=1)
    prd_title: str = Field(..., min_length=1)
    total_user_stories: int = Field(..., ge=1)
    total_acceptance_criteria: int = Field(..., ge=1)
    user_stories: list[UserStory] = Field(..., min_length=1)
    generation_notes: list[str] = Field(default_factory=list)

def build_user_story_result(request: UserStoryGenerationRequest, output: UserStoryGenerationOutput) -> UserStoryGenerationResult:
    requirements = {r.requirement_id: r for r in request.prd.functional_requirements}
    valid_feedback = {fid for r in requirements.values() for fid in r.source_feedback_ids}
    normalized = []
    for story in output.user_stories:
        unknown_req = set(story.requirement_ids) - set(requirements)
        if unknown_req:
            raise ValueError(f"Story '{story.story_id}' references unknown PRD requirements: {sorted(unknown_req)}")
        linked = [requirements[rid] for rid in story.requirement_ids]
        # Priority must be inherited, not independently invented.
        priority_order = {"Must Have": 0, "Should Have": 1, "Could Have": 2, "Won't Have": 3}
        inherited_priority = min((r.priority for r in linked), key=lambda p: priority_order[p])
        # Feedback traceability is derived deterministically from linked requirements.
        feedback_ids = list(dict.fromkeys(fid for req in linked for fid in req.source_feedback_ids))
        unknown_feedback = set(feedback_ids) - valid_feedback
        if unknown_feedback:
            raise ValueError(f"Story '{story.story_id}' contains unknown feedback IDs: {sorted(unknown_feedback)}")
        normalized.append(story.model_copy(update={"priority": inherited_priority, "source_feedback_ids": feedback_ids}))
    criteria_count = sum(len(s.acceptance_criteria) for s in normalized)
    return UserStoryGenerationResult(product_name=request.product_name, prd_title=request.prd.title, total_user_stories=len(normalized), total_acceptance_criteria=criteria_count, user_stories=normalized, generation_notes=output.generation_notes)
