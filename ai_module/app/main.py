
import logging

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

from app.services.orchestrator import (
    OrchestrationError,
    run_all_analyses,
)


# ---------------------------------------------------------
# LOGGING CONFIGURATION
# ---------------------------------------------------------

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# FASTAPI APPLICATION
# ---------------------------------------------------------

app = FastAPI(
    title="AI Feedback Intelligence",
    description=(
        "AI-powered customer feedback analysis using "
        "four specialized AI agents and three project datasets."
    ),
    version="1.0.0",
)


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ai_module",
    }


# ---------------------------------------------------------
# INDIVIDUAL FEEDBACK ANALYZER
# ---------------------------------------------------------

@app.post(
    "/feedback/analyze",
    response_model=FeedbackAnalysis,
)
def analyze_feedback(
    request: FeedbackRequest,
) -> FeedbackAnalysis:

    try:
        return feedback_analyzer.analyze_feedback(request.text)

    except feedback_analyzer.FeedbackAnalysisError:
        raise HTTPException(
            status_code=503,
            detail="Feedback analysis is temporarily unavailable.",
        ) from None


# ---------------------------------------------------------
# AGENT 1 - THEME EXTRACTION
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# AGENT 2 - PAIN POINT IDENTIFICATION
# ---------------------------------------------------------

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


# ---------------------------------------------------------
# AGENT 3 - FEATURE CLUSTERING
# ---------------------------------------------------------

@app.post(
    "/features/cluster",
    response_model=FeatureClusteringResult,
)
def cluster_features(
    request: FeatureClusteringRequest,
) -> FeatureClusteringResult:

    try:
        return feature_clustering_agent.identify_feature_clusters(
            request
        )

    except feature_clustering_agent.FeatureClusteringError:
        raise HTTPException(
            status_code=503,
            detail="Feature clustering is temporarily unavailable.",
        ) from None


# ---------------------------------------------------------
# AGENT 4 - TREND ANALYSIS
# ---------------------------------------------------------

@app.post(
    "/trends/analyze",
    response_model=TrendAnalysisResult,
)
def analyze_trends(
    request: TrendAnalysisRequest,
) -> TrendAnalysisResult:

    try:
        return trend_analysis_agent.analyze_feedback_trends(
            request
        )

    except trend_analysis_agent.TrendAnalysisError:
        raise HTTPException(
            status_code=503,
            detail="Trend analysis is temporarily unavailable.",
        ) from None


# ---------------------------------------------------------
# MULTI-AGENT ORCHESTRATOR
# ---------------------------------------------------------

@app.post("/analysis/run-all")
def run_complete_analysis() -> dict:
    """
    Automatically load all three project JSON datasets
    and execute all four AI agents sequentially.

    Data sources:
        1. customer_feedback.json
        2. user_reviews.json
        3. support_tickets.json

    MongoDB Atlas is not used as an input source.

    No manual feedback JSON is required.
    """

    try:
        logger.info("Starting complete multi-agent analysis.")

        result = run_all_analyses()

        logger.info(
            "Multi-agent analysis completed successfully."
        )

        return result

    except OrchestrationError as exc:
        logger.exception(
            "Multi-agent orchestration failed."
        )

        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from None

    except Exception:
        logger.exception(
            "Unexpected error during multi-agent analysis."
        )

        raise HTTPException(
            status_code=500,
            detail=(
                "An unexpected error occurred during "
                "multi-agent analysis."
            ),
        ) from None
