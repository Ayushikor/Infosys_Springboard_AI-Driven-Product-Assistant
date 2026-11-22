"""
Pydantic schemas for the PRD Generation Agent.

The PRD Generation Agent consumes:
- Selected feature-cluster information from Agent 3
- Original customer feedback supporting the feature
- Theme context from Agent 1
- Pain-point context from Agent 2

It produces a structured Product Requirements Document (PRD).

User stories and feature prioritization are handled by separate agents.
"""

from datetime import datetime, timezone
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# ---------------------------------------------------------
# ORIGINAL FEEDBACK
# ---------------------------------------------------------


class PRDFeedbackItem(BaseModel):
    """Original customer feedback supporting the selected feature."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    feedback_id: str = Field(..., min_length=1)
    source_channel: str = Field(default="Unknown", min_length=1)
    raw_text: str = Field(..., min_length=1)

    @field_validator("feedback_id", "source_channel", "raw_text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("This field cannot be empty.")

        return value


# ---------------------------------------------------------
# SELECTED FEATURE CONTEXT FROM AGENT 3
# ---------------------------------------------------------


class PRDFeatureContext(BaseModel):
    """Selected feature cluster used as the basis for PRD generation."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    feature_name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)

    mention_count: int = Field(..., ge=1)

    feedback_ids: list[str] = Field(
        ...,
        min_length=1,
    )

    source_channels: list[str] = Field(default_factory=list)

    @field_validator("feedback_ids")
    @classmethod
    def validate_feedback_ids(cls, values: list[str]) -> list[str]:
        cleaned = [value.strip() for value in values]

        if any(not value for value in cleaned):
            raise ValueError("Feature feedback IDs cannot be empty.")

        if len(cleaned) != len(set(cleaned)):
            raise ValueError("Duplicate feedback IDs inside the feature.")

        return cleaned

    @model_validator(mode="after")
    def validate_mention_count(self):
        if self.mention_count != len(self.feedback_ids):
            raise ValueError(
                "Feature mention_count must equal the number of feedback IDs."
            )

        return self


# ---------------------------------------------------------
# UPSTREAM THEME CONTEXT FROM AGENT 1
# ---------------------------------------------------------


class PRDThemeContext(BaseModel):
    """Theme information produced by Agent 1."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)

    keywords: list[str] = Field(default_factory=list)
    feedback_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_feedback_ids(self):
        if len(self.feedback_ids) != len(set(self.feedback_ids)):
            raise ValueError(
                "Duplicate feedback IDs inside a theme context."
            )

        return self


# ---------------------------------------------------------
# UPSTREAM PAIN-POINT CONTEXT FROM AGENT 2
# ---------------------------------------------------------


class PRDPainPointContext(BaseModel):
    """Pain-point information produced by Agent 2."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    name: str = Field(..., min_length=1)
    category: str = Field(..., min_length=1)

    severity: Literal["Low", "Medium", "High", "Unknown"]

    description: str = Field(..., min_length=1)
    feedback_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_unique_feedback_ids(self):
        if len(self.feedback_ids) != len(set(self.feedback_ids)):
            raise ValueError(
                "Duplicate feedback IDs inside a pain-point context."
            )

        return self


# ---------------------------------------------------------
# PRD GENERATION REQUEST
# ---------------------------------------------------------


class PRDGenerationRequest(BaseModel):
    """
    Input supplied to the PRD Generation Agent.

    The selected feature cluster determines what the PRD describes.
    Original feedback provides the evidence for requirements.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    product_name: str = Field(
        ...,
        min_length=1,
        description="Name of the product for which the PRD is generated.",
    )

    product_context: str = Field(
        default="",
        description="Optional background information about the product.",
    )

    feature: PRDFeatureContext = Field(
        ...,
        description="Selected feature cluster from Agent 3.",
    )

    feedback: list[PRDFeedbackItem] = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Original feedback records supporting the selected feature.",
    )

    theme_context: list[PRDThemeContext] = Field(
        default_factory=list,
        description="Relevant themes identified by Agent 1.",
    )

    pain_point_context: list[PRDPainPointContext] = Field(
        default_factory=list,
        description="Relevant pain points identified by Agent 2.",
    )

    @model_validator(mode="after")
    def validate_request(self):
        """Ensure all upstream references belong to the supplied feedback."""

        feedback_ids = [
            item.feedback_id
            for item in self.feedback
        ]

        if len(feedback_ids) != len(set(feedback_ids)):
            raise ValueError("Duplicate feedback IDs are not allowed.")

        valid_ids = set(feedback_ids)

        feature_ids = set(self.feature.feedback_ids)

        unknown_feature_ids = feature_ids - valid_ids

        if unknown_feature_ids:
            raise ValueError(
                "Selected feature contains unknown feedback IDs: "
                f"{sorted(unknown_feature_ids)}"
            )

        if len(feature_ids) != self.feature.mention_count:
            raise ValueError(
                "Selected feature mention count does not match its feedback IDs."
            )

        for context_name, contexts in (
            ("theme_context", self.theme_context),
            ("pain_point_context", self.pain_point_context),
        ):
            for context in contexts:
                unknown_ids = set(context.feedback_ids) - valid_ids

                if unknown_ids:
                    raise ValueError(
                        f"{context_name} contains unknown feedback IDs: "
                        f"{sorted(unknown_ids)}"
                    )

        return self


# ---------------------------------------------------------
# FUNCTIONAL REQUIREMENT
# ---------------------------------------------------------


class FunctionalRequirement(BaseModel):
    """One functional requirement in the generated PRD."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    requirement_id: str = Field(..., min_length=1)

    title: str = Field(..., min_length=1)

    description: str = Field(..., min_length=1)

    priority: Literal[
        "Must Have",
        "Should Have",
        "Could Have",
        "Won't Have",
    ]

    source_feedback_ids: list[str] = Field(
        default_factory=list,
        description="Original feedback IDs supporting this requirement.",
    )

    @field_validator("source_feedback_ids")
    @classmethod
    def validate_source_feedback_ids(
        cls,
        values: list[str],
    ) -> list[str]:
        cleaned = [value.strip() for value in values]

        if any(not value for value in cleaned):
            raise ValueError("Source feedback IDs cannot be empty.")

        if len(cleaned) != len(set(cleaned)):
            raise ValueError(
                "Duplicate source feedback IDs are not allowed."
            )

        return cleaned


# ---------------------------------------------------------
# NON-FUNCTIONAL REQUIREMENT
# ---------------------------------------------------------


class NonFunctionalRequirement(BaseModel):
    """One quality, performance, security, or operational requirement."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    requirement_id: str = Field(..., min_length=1)

    category: Literal[
        "Performance",
        "Security",
        "Scalability",
        "Reliability",
        "Usability",
        "Accessibility",
        "Compatibility",
        "Maintainability",
        "Other",
    ]

    description: str = Field(..., min_length=1)

    measurable_target: str = Field(
        default="Not specified",
        description="Measurable target, if supported by available evidence.",
    )


# ---------------------------------------------------------
# TARGET USER
# ---------------------------------------------------------


class TargetUser(BaseModel):
    """A user group that may benefit from the proposed feature."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    user_type: str = Field(..., min_length=1)

    description: str = Field(..., min_length=1)

    needs: list[str] = Field(
        default_factory=list,
        description="Needs relevant to the selected feature.",
    )


# ---------------------------------------------------------
# SUCCESS METRIC
# ---------------------------------------------------------


class SuccessMetric(BaseModel):
    """A metric used to evaluate the success of the feature."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    metric_name: str = Field(..., min_length=1)

    description: str = Field(..., min_length=1)

    measurement_method: str = Field(..., min_length=1)

    target: str = Field(
        default="To be determined",
        description="Target value, if supported by available information.",
    )


# ---------------------------------------------------------
# PRD SCOPE
# ---------------------------------------------------------


class PRDScope(BaseModel):
    """Defines what is included and excluded from the feature."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    in_scope: list[str] = Field(
        default_factory=list,
        description="Capabilities included in the proposed feature.",
    )

    out_of_scope: list[str] = Field(
        default_factory=list,
        description="Capabilities explicitly excluded from this feature.",
    )


# ---------------------------------------------------------
# GEMINI PRD OUTPUT
# ---------------------------------------------------------


class PRDGenerationOutput(BaseModel):
    """
    Structured draft output generated by Gemini.

    This schema deliberately excludes user stories and acceptance criteria.
    Those are generated by the separate User Story Agent.
    """

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(
        ...,
        min_length=1,
        description="Clear title of the Product Requirements Document.",
    )

    executive_summary: str = Field(
        ...,
        min_length=1,
        description="Short overview of the proposed feature and its purpose.",
    )

    problem_statement: str = Field(
        ...,
        min_length=1,
        description="Customer problem supported by the supplied feedback.",
    )

    proposed_solution: str = Field(
        ...,
        min_length=1,
        description="Proposed product capability addressing the problem.",
    )

    objectives: list[str] = Field(
        ...,
        min_length=1,
        description="Specific objectives of the proposed feature.",
    )

    scope: PRDScope

    target_users: list[TargetUser] = Field(
        default_factory=list,
    )

    functional_requirements: list[FunctionalRequirement] = Field(
        ...,
        min_length=1,
    )

    non_functional_requirements: list[NonFunctionalRequirement] = Field(
        default_factory=list,
    )

    success_metrics: list[SuccessMetric] = Field(
        default_factory=list,
    )

    assumptions: list[str] = Field(
        default_factory=list,
    )

    dependencies: list[str] = Field(
        default_factory=list,
    )

    risks: list[str] = Field(
        default_factory=list,
    )

    open_questions: list[str] = Field(
        default_factory=list,
        description="Unresolved questions requiring product-team input.",
    )

    @model_validator(mode="after")
    def validate_requirement_ids(self):
        """Ensure functional requirement IDs are unique."""

        requirement_ids = [
            item.requirement_id
            for item in self.functional_requirements
        ]

        if len(requirement_ids) != len(set(requirement_ids)):
            raise ValueError(
                "Functional requirement IDs must be unique."
            )

        return self


# ---------------------------------------------------------
# FINAL VALIDATED PRD RESULT
# ---------------------------------------------------------


class PRDGenerationResult(BaseModel):
    """Final validated PRD returned by the PRD Generation Agent."""

    model_config = ConfigDict(extra="forbid")

    prd_id: str = Field(..., min_length=1)

    product_name: str = Field(..., min_length=1)

    feature_name: str = Field(..., min_length=1)

    generated_at: datetime

    total_feedback_analyzed: int = Field(..., ge=1)

    document: PRDGenerationOutput

    @model_validator(mode="after")
    def validate_generated_at(self):
        if self.generated_at.tzinfo is None:
            raise ValueError(
                "generated_at must include timezone information."
            )

        return self


# ---------------------------------------------------------
# BUILD FINAL PRD RESULT
# ---------------------------------------------------------


def build_prd_result(
    request: PRDGenerationRequest,
    output: PRDGenerationOutput,
    prd_id: str,
) -> PRDGenerationResult:
    """
    Build the final PRD result using the original request.

    Validates that:
    - The PRD has a valid identifier.
    - Every referenced feedback ID exists in the original request.
    - Functional requirements are supported by supplied feedback.
    - The final result contains the original feature and product context.
    """

    prd_id = prd_id.strip()

    if not prd_id:
        raise ValueError("PRD ID cannot be empty.")

    valid_feedback_ids = {
        item.feedback_id
        for item in request.feedback
    }

    for requirement in output.functional_requirements:
        unknown_ids = (
            set(requirement.source_feedback_ids)
            - valid_feedback_ids
        )

        if unknown_ids:
            raise ValueError(
                f"Requirement '{requirement.requirement_id}' "
                f"contains unknown feedback IDs: {sorted(unknown_ids)}"
            )

    return PRDGenerationResult(
        prd_id=prd_id,
        product_name=request.product_name,
        feature_name=request.feature.feature_name,
        generated_at=datetime.now(timezone.utc),
        total_feedback_analyzed=len(request.feedback),
        document=output,
    )