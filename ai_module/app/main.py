from fastapi import FastAPI, HTTPException

from app.schemas.feedback import FeedbackAnalysis, FeedbackRequest

from app.schemas.theme_extraction import (
    ThemeExtractionRequest,
    ThemeExtractionResult,
)

from app.schemas.pain_point import (
    PainPointExtractionRequest,
    PainPointExtractionResult,
)

from app.schemas.feature_clustering import (
    FeatureClusteringRequest,
    FeatureClusteringResult,
)

from app.schemas.trend_analysis import (
    TrendAnalysisRequest,
    TrendAnalysisResult,
)

from app.services import (
    feedback_analyzer,
    theme_extraction_agent,
    pain_point_agent,
    feature_clustering_agent,
    trend_analysis_agent,
)


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


@app.post(
    "/pain-points/identify",
    response_model=PainPointExtractionResult,
)
def identify_pain_points(
    request: PainPointExtractionRequest,
) -> PainPointExtractionResult:
    try:
        return pain_point_agent.identify_pain_points(request)

    except pain_point_agent.PainPointExtractionError:
        raise HTTPException(
            status_code=503,
            detail="Pain-point identification is temporarily unavailable.",
        ) from None


@app.post(
    "/features/cluster",
    response_model=FeatureClusteringResult,
)
def cluster_features(
    request: FeatureClusteringRequest,
) -> FeatureClusteringResult:
    try:
        return feature_clustering_agent.identify_feature_clusters(request)

    except feature_clustering_agent.FeatureClusteringError:
        raise HTTPException(
            status_code=503,
            detail="Feature clustering is temporarily unavailable.",
        ) from None


@app.post(
    "/trends/analyze",
    response_model=TrendAnalysisResult,
)
def analyze_trends(
    request: TrendAnalysisRequest,
) -> TrendAnalysisResult:
    try:
        return trend_analysis_agent.analyze_feedback_trends(request)

    except trend_analysis_agent.TrendAnalysisError:
        raise HTTPException(
            status_code=503,
            detail="Trend analysis is temporarily unavailable.",
        ) from None