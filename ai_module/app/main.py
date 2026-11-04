
from fastapi import FastAPI, HTTPException

from app.schemas.feedback import FeedbackAnalysis, FeedbackRequest
from app.schemas.theme_extraction import (
    ThemeExtractionRequest,
    ThemeExtractionResult,
)

from app.services import feedback_analyzer, theme_extraction_agent


app = FastAPI(title="AI Feedback Intelligence")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "ai_module"}


@app.post("/feedback/analyze", response_model=FeedbackAnalysis)
def analyze_feedback(request: FeedbackRequest) -> FeedbackAnalysis:
    try:
        return feedback_analyzer.analyze_feedback(request.text)
    except feedback_analyzer.FeedbackAnalysisError:
        raise HTTPException(
            status_code=503,
            detail="Feedback analysis is temporarily unavailable.",
        ) from None


@app.post(
    "/themes/extract",
    response_model=ThemeExtractionResult,
)
def extract_themes(
    request: ThemeExtractionRequest,
) -> ThemeExtractionResult:
    try:
        return theme_extraction_agent.extract_themes(request)

    except theme_extraction_agent.ThemeExtractionError:
        raise HTTPException(
            status_code=503,
            detail="Theme extraction is temporarily unavailable.",
        ) from None
