from fastapi import FastAPI, HTTPException

from app.schemas.feedback import FeedbackAnalysis, FeedbackRequest
from app.services import feedback_analyzer

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
