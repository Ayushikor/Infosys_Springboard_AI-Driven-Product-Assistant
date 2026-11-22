
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


# =========================================================
# FEATURE CANDIDATE
# =========================================================

class FeatureCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_id: str = Field(
        ...,
        min_length=1,
        description="Unique identifier for the feature.",
    )

    feature_name: str = Field(
        ...,
        min_length=2,
        description="Name of the proposed feature.",
    )

    description: str = Field(
        ...,
        min_length=5,
        description="Description of the feature.",
    )

    category: str | None = None

    mention_count: int = Field(
        default=0,
        ge=0,
        description="Number of feedback mentions associated with this feature.",
    )

    feedback_ids: list[str] = Field(default_factory=list)

    source_channels: list[str] = Field(default_factory=list)


# =========================================================
# PRIORITIZATION CONTEXT
# =========================================================

class PrioritizationContext(BaseModel):
    model_config = ConfigDict(extra="allow")

    themes: list[dict[str, Any]] = Field(default_factory=list)

    pain_points: list[dict[str, Any]] = Field(default_factory=list)

    trends: list[dict[str, Any]] = Field(default_factory=list)

    additional_context: str | None = None


# =========================================================
# FEATURE PRIORITIZATION REQUEST
# =========================================================

class FeaturePrioritizationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_name: str = Field(
        ...,
        min_length=2,
        description="Name of the product being analyzed.",
    )

    product_context: str | None = Field(
        default=None,
        description="Additional product and business context.",
    )

    features: list[FeatureCandidate] = Field(
        ...,
        min_length=1,
        description="Features that need to be prioritized.",
    )

    analysis_context: PrioritizationContext = Field(
        default_factory=PrioritizationContext,
        description="Context from the existing feedback analysis agents.",
    )

    business_goals: list[str] = Field(default_factory=list)

    available_resources: str | None = None

    prioritization_strategy: Literal[
        "balanced",
        "customer_value",
        "business_impact",
        "quick_wins",
    ] = "balanced"

    @field_validator("features")
    @classmethod
    def validate_unique_features(
        cls,
        features: list[FeatureCandidate],
    ) -> list[FeatureCandidate]:

        feature_ids = [feature.feature_id for feature in features]

        if len(feature_ids) != len(set(feature_ids)):
            raise ValueError("Feature IDs must be unique.")

        return features


# =========================================================
# PRIORITIZATION SCORE
# =========================================================

class PrioritizationScore(BaseModel):
    model_config = ConfigDict(extra="forbid")

    customer_impact: int = Field(
        ...,
        ge=1,
        le=5,
        description="Expected positive impact on customers.",
    )

    business_value: int = Field(
        ...,
        ge=1,
        le=5,
        description="Expected contribution to business objectives.",
    )

    urgency: int = Field(
        ...,
        ge=1,
        le=5,
        description="How urgently the feature should be implemented.",
    )

    implementation_effort: int = Field(
        ...,
        ge=1,
        le=5,
        description="Estimated implementation effort. Higher means more effort.",
    )

    confidence: int = Field(
        ...,
        ge=1,
        le=5,
        description="Confidence in the evidence supporting this feature.",
    )

    weighted_score: float = Field(
        ...,
        ge=0,
        le=100,
        description="Final weighted prioritization score.",
    )

    @field_validator("weighted_score")
    @classmethod
    def round_weighted_score(cls, value: float) -> float:
        return round(value, 2)


# =========================================================
# PRIORITIZED FEATURE
# =========================================================

class PrioritizedFeature(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feature_id: str

    feature_name: str

    description: str

    rank: int = Field(..., ge=1)

    priority: Literal[
        "P0 - Critical",
        "P1 - High",
        "P2 - Medium",
        "P3 - Low",
    ]

    recommended_release: Literal[
        "Immediate",
        "Next Release",
        "Future Release",
        "Backlog",
    ]

    score: PrioritizationScore

    rationale: str = Field(
        ...,
        min_length=10,
        description="Explanation of why this feature received its priority.",
    )

    customer_evidence: list[str] = Field(default_factory=list)

    business_justification: str

    dependencies: list[str] = Field(default_factory=list)

    risks: list[str] = Field(default_factory=list)

    implementation_considerations: list[str] = Field(
        default_factory=list
    )


# =========================================================
# PRIORITIZATION SUMMARY
# =========================================================

class PrioritizationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_features: int = Field(..., ge=0)

    critical_features: int = Field(default=0, ge=0)

    high_priority_features: int = Field(default=0, ge=0)

    medium_priority_features: int = Field(default=0, ge=0)

    low_priority_features: int = Field(default=0, ge=0)

    recommended_focus: str = Field(
        ...,
        min_length=10,
        description="Summary of which features should receive attention first.",
    )

    strategic_observations: list[str] = Field(default_factory=list)

    resource_recommendations: list[str] = Field(default_factory=list)


# =========================================================
# FEATURE PRIORITIZATION OUTPUT
# =========================================================

class FeaturePrioritizationOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prioritization_method: str

    scoring_explanation: str

    prioritized_features: list[PrioritizedFeature] = Field(
        ...,
        min_length=1,
    )

    summary: PrioritizationSummary

    @model_validator(mode="after")
    def validate_prioritization(self):

        features = self.prioritized_features

        feature_ids = [feature.feature_id for feature in features]
        ranks = [feature.rank for feature in features]

        if len(feature_ids) != len(set(feature_ids)):
            raise ValueError("Duplicate feature IDs in prioritization output.")

        if len(ranks) != len(set(ranks)):
            raise ValueError("Feature ranks must be unique.")

        if sorted(ranks) != list(range(1, len(features) + 1)):
            raise ValueError("Feature ranks must be consecutive, starting at 1.")

        if self.summary.total_features != len(features):
            raise ValueError(
                "Summary total_features must match the number of prioritized features."
            )

        priority_counts = {
            "P0 - Critical": 0,
            "P1 - High": 0,
            "P2 - Medium": 0,
            "P3 - Low": 0,
        }

        for feature in features:
            priority_counts[feature.priority] += 1

        if self.summary.critical_features != priority_counts["P0 - Critical"]:
            raise ValueError("Critical feature count does not match output.")

        if self.summary.high_priority_features != priority_counts["P1 - High"]:
            raise ValueError("High priority feature count does not match output.")

        if self.summary.medium_priority_features != priority_counts["P2 - Medium"]:
            raise ValueError("Medium priority feature count does not match output.")

        if self.summary.low_priority_features != priority_counts["P3 - Low"]:
            raise ValueError("Low priority feature count does not match output.")

        return self


# =========================================================
# FINAL API RESPONSE
# =========================================================

class FeaturePrioritizationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    success: bool = True

    product_name: str

    prioritization_id: str

    generated_at: str

    result: FeaturePrioritizationOutput


# =========================================================
# RESULT BUILDER
# =========================================================

def build_feature_prioritization_result(
    product_name: str,
    output: FeaturePrioritizationOutput,
    prioritization_id: str,
    generated_at: str,
) -> FeaturePrioritizationResult:

    input_feature_ids = {
        feature.feature_id
        for feature in output.prioritized_features
    }

    for feature in output.prioritized_features:
        unknown_dependencies = (
            set(feature.dependencies) - input_feature_ids
        )

        if unknown_dependencies:
            raise ValueError(
                f"Feature '{feature.feature_id}' references unknown "
                f"dependencies: {sorted(unknown_dependencies)}"
            )

        if feature.feature_id in feature.dependencies:
            raise ValueError(
                f"Feature '{feature.feature_id}' cannot depend on itself."
            )

    return FeaturePrioritizationResult(
        success=True,
        product_name=product_name,
        prioritization_id=prioritization_id,
        generated_at=generated_at,
        result=output,
    )
