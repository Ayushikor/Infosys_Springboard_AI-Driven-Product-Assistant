from typing import Literal

from pydantic import BaseModel, Field, field_validator


class FeedbackRequest(BaseModel):
    text: str = Field(min_length=1, description="Feedback text to analyze")

    @field_validator("text")
    @classmethod
    def reject_whitespace_only(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Feedback text must not be empty")
        return value


class FeedbackAnalysis(BaseModel):
    sentiment: Literal["positive", "negative", "neutral"]
    category: str
    pain_points: list[str]
    feature_requests: list[str]
    summary: str
