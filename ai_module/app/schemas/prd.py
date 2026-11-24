"""Pydantic schemas for evidence-grounded PRD generation."""
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Priority = Literal["Must Have", "Should Have", "Could Have", "Won't Have"]

class PRDFeedbackItem(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    feedback_id: str = Field(..., min_length=1)
    source_channel: str = Field(default="Unknown", min_length=1)
    raw_text: str = Field(..., min_length=1)

    @field_validator("feedback_id", "source_channel", "raw_text")
    @classmethod
    def nonempty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be empty.")
        return value

class PRDFeatureContext(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    feature_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    mention_count: int = Field(..., ge=1)
    feedback_ids: list[str] = Field(..., min_length=1)
    source_channels: list[str] = Field(default_factory=list)

    @field_validator("feedback_ids")
    @classmethod
    def unique_ids(cls, values: list[str]) -> list[str]:
        cleaned = [v.strip() for v in values]
        if any(not v for v in cleaned) or len(cleaned) != len(set(cleaned)):
            raise ValueError("Feature feedback IDs must be nonempty and unique.")
        return cleaned

    @model_validator(mode="after")
    def count_matches(self):
        if self.mention_count != len(self.feedback_ids):
            raise ValueError("Feature mention_count must equal the number of feedback IDs.")
        return self

class PRDThemeContext(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    keywords: list[str] = Field(default_factory=list)
    feedback_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_ids(self):
        if len(self.feedback_ids) != len(set(self.feedback_ids)):
            raise ValueError("Duplicate feedback IDs inside a theme context.")
        return self

class PRDPainPointContext(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    name: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)
    severity: Literal["Low", "Medium", "High", "Unknown"]
    description: str = Field(..., min_length=1)
    feedback_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_ids(self):
        if len(self.feedback_ids) != len(set(self.feedback_ids)):
            raise ValueError("Duplicate feedback IDs inside a pain-point context.")
        return self

class PRDGenerationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    product_name: str = Field(..., min_length=1)
    product_context: str = ""
    feature: PRDFeatureContext
    feedback: list[PRDFeedbackItem] = Field(..., min_length=1, max_length=500)
    theme_context: list[PRDThemeContext] = Field(default_factory=list)
    pain_point_context: list[PRDPainPointContext] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_evidence_references(self):
        ids = [item.feedback_id for item in self.feedback]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate feedback IDs are not allowed.")
        valid = set(ids)
        unknown_feature = set(self.feature.feedback_ids) - valid
        if unknown_feature:
            raise ValueError(f"Selected feature contains unknown feedback IDs: {sorted(unknown_feature)}")
        for label, contexts in (("theme_context", self.theme_context), ("pain_point_context", self.pain_point_context)):
            for context in contexts:
                unknown = set(context.feedback_ids) - valid
                if unknown:
                    raise ValueError(f"{label} contains unknown feedback IDs: {sorted(unknown)}")
        return self

class FunctionalRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    requirement_id: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    priority: Priority
    source_feedback_ids: list[str] = Field(default_factory=list, description="Original feedback IDs supporting this requirement.")

    @field_validator("source_feedback_ids")
    @classmethod
    def clean_source_ids(cls, values: list[str]) -> list[str]:
        cleaned = [v.strip() for v in values]
        if any(not v for v in cleaned) or len(cleaned) != len(set(cleaned)):
            raise ValueError("Source feedback IDs must be nonempty and unique.")
        return cleaned

class NonFunctionalRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    requirement_id: str = Field(..., min_length=1)
    category: Literal["Performance", "Security", "Scalability", "Reliability", "Usability", "Accessibility", "Compatibility", "Maintainability", "Other"]
    description: str = Field(..., min_length=1)
    measurable_target: str = "Not specified"

class TargetUser(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    user_type: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    needs: list[str] = Field(default_factory=list)

class SuccessMetric(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    metric_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    measurement_method: str = Field(..., min_length=1)
    target: str = Field(default="To be determined", description="Evidence-backed target or explicitly provisional target requiring stakeholder validation.")
    target_status: Literal["Evidence-backed", "Proposed for validation", "To be determined"] = "To be determined"
    target_rationale: str = ""

class PRDScope(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    in_scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)

class PRDGenerationOutput(BaseModel):
    """Core PRD document; stories are generated by the separate story agent."""
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    title: str = Field(..., min_length=1)
    executive_summary: str = Field(..., min_length=1)
    problem_statement: str = Field(..., min_length=1)
    proposed_solution: str = Field(..., min_length=1)
    objectives: list[str] = Field(..., min_length=1)
    scope: PRDScope
    target_users: list[TargetUser] = Field(default_factory=list)
    functional_requirements: list[FunctionalRequirement] = Field(..., min_length=1)
    non_functional_requirements: list[NonFunctionalRequirement] = Field(default_factory=list)
    success_metrics: list[SuccessMetric] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_requirement_ids(self):
        ids = [x.requirement_id for x in self.functional_requirements]
        if len(ids) != len(set(ids)):
            raise ValueError("Functional requirement IDs must be unique.")
        nfr_ids = [x.requirement_id for x in self.non_functional_requirements]
        if len(nfr_ids) != len(set(nfr_ids)):
            raise ValueError("Non-functional requirement IDs must be unique.")
        return self

class PRDGenerationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    prd_id: str = Field(..., min_length=1)
    product_name: str = Field(..., min_length=1)
    feature_name: str = Field(..., min_length=1)
    generated_at: datetime
    total_feedback_analyzed: int = Field(..., ge=1)
    document: PRDGenerationOutput

    @model_validator(mode="after")
    def timezone_required(self):
        if self.generated_at.tzinfo is None:
            raise ValueError("generated_at must include timezone information.")
        return self

def build_prd_result(request: PRDGenerationRequest, output: PRDGenerationOutput, prd_id: str) -> PRDGenerationResult:
    prd_id = prd_id.strip()
    if not prd_id:
        raise ValueError("PRD ID cannot be empty.")
    valid_ids = set(request.feature.feedback_ids)
    for requirement in output.functional_requirements:
        unknown = set(requirement.source_feedback_ids) - valid_ids
        if unknown:
            raise ValueError(f"Requirement '{requirement.requirement_id}' contains feedback IDs outside the selected feature: {sorted(unknown)}")
        if not requirement.source_feedback_ids:
            raise ValueError(f"Requirement '{requirement.requirement_id}' must cite at least one source feedback ID.")
    return PRDGenerationResult(prd_id=prd_id, product_name=request.product_name, feature_name=request.feature.feature_name, generated_at=datetime.now(timezone.utc), total_feedback_analyzed=len(request.feature.feedback_ids), document=output)
