
import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field

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

from app.schemas.prd import (
    PRDGenerationRequest,
    PRDGenerationResult,
)

from app.schemas.prd import (
    PRDGenerationRequest,
    PRDGenerationResult,
)

from app.schemas.user_story import (
    UserStoryGenerationRequest,
    UserStoryGenerationResult,
)

from app.schemas.feature_prioritization import (
    FeaturePrioritizationRequest,
    FeaturePrioritizationResult,
)

from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
)

from app.services.chat_orchestrator import (
    ChatOrchestrationError,
    process_chat,
)

from app.services import (
    feedback_analyzer,
    theme_extraction_agent,
    pain_point_agent,
    feature_clustering_agent,
    trend_analysis_agent,
    prd_generation_agent,
    user_story_agent,
    feature_prioritization_agent,
)
from app.services.orchestrator import (
    OrchestrationError,
    run_all_analyses,
)

from app.services.batch_orchestrator import (
    BatchAnalysisError,
    DEFAULT_BATCH_SIZE,
    MAX_TOTAL_FEEDBACK_RECORDS,
    run_batched_analyses,
    aggregate_batch_responses,
)

logger = logging.getLogger(__name__)


# =========================================================
# REQUEST MODELS
# =========================================================

class AnalysisRunRequest(BaseModel):
    """Feedback records supplied by the authenticated main backend."""

    model_config = ConfigDict(extra="forbid")

    feedback_records: list[dict[str, Any]] = Field(
        ...,
        min_length=2,
        max_length=MAX_TOTAL_FEEDBACK_RECORDS,
        description="Normalized feedback records (2 to 10,000).",
    )

    batch_size: int = Field(
        default=DEFAULT_BATCH_SIZE,
        ge=2,
        le=500,
        description="Maximum feedback records per AI batch.",
    )


class BatchAggregationRequest(BaseModel):
    """Request to merge previously completed AI batch outputs."""

    model_config = ConfigDict(extra="forbid")

    batch_responses: list[dict[str, Any]] = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Previously completed batch analysis responses.",
    )

    total_feedback_analyzed: int = Field(
        ...,
        ge=2,
        le=MAX_TOTAL_FEEDBACK_RECORDS,
    )

    source_counts: dict[str, int]

    batch_size: int = Field(
        default=DEFAULT_BATCH_SIZE,
        ge=2,
        le=500,
    )


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="AI Feedback Intelligence",
    description=(
        "AI-powered customer feedback analysis using four "
        "specialized sequential agents, batch execution, "
        "and deterministic batch aggregation."
    ),
    version="1.3.0",
)


# =========================================================
# HEALTH CHECK
# =========================================================

@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "ai_module",
    }


# =========================================================
# SINGLE FEEDBACK ANALYSIS
# =========================================================

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


# =========================================================
# AGENT 1: THEME EXTRACTION
# =========================================================

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


# =========================================================
# AGENT 2: PAIN POINT IDENTIFICATION
# =========================================================

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


# =========================================================
# AGENT 3: FEATURE CLUSTERING
# =========================================================

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


# =========================================================
# AGENT 4: TREND ANALYSIS
# =========================================================

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

# =========================================================
# AGENT 5: PRD GENERATION
# =========================================================


@app.post(
    "/prd/generate",
    response_model=PRDGenerationResult,
)
def generate_product_requirements(
    request: PRDGenerationRequest,
) -> PRDGenerationResult:
    """
    Generate a Product Requirements Document.

    Consumes:
        Selected feature cluster from Agent 3.
        Original customer feedback.
        Theme context from Agent 1.
        Pain-point context from Agent 2.

    Returns:
        A structured and validated Product Requirements Document.
    """

    try:
        return prd_generation_agent.generate_prd(request)

    except prd_generation_agent.PRDGenerationError:
        logger.exception(
            "PRD generation failed."
        )

        raise HTTPException(
            status_code=503,
            detail="PRD generation is temporarily unavailable.",
        ) from None

    except Exception:
        logger.exception(
            "Unexpected error during PRD generation."
        )

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during PRD generation.",
        ) from None

# =========================================================
# AGENT 6: USER STORY AND ACCEPTANCE CRITERIA GENERATION
# =========================================================

@app.post(
    "/user-stories/generate",
    response_model=UserStoryGenerationResult,
)
def generate_user_stories(
    request: UserStoryGenerationRequest,
) -> UserStoryGenerationResult:

    try:
        return user_story_agent.generate_user_stories(request)

    except user_story_agent.UserStoryGenerationError:
        logger.exception("User story generation failed.")

        raise HTTPException(
            status_code=503,
            detail="User story generation is temporarily unavailable.",
        ) from None

    except Exception:
        logger.exception(
            "Unexpected error during user story generation."
        )

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during user story generation.",
        ) from None

# =========================================================
# AGENT 7: FEATURE PRIORITIZATION
# =========================================================

@app.post(
    "/features/prioritize",
    response_model=FeaturePrioritizationResult,
)
def prioritize_product_features(
    request: FeaturePrioritizationRequest,
) -> FeaturePrioritizationResult:

    try:
        return feature_prioritization_agent.prioritize_features(
            request
        )

    except feature_prioritization_agent.FeaturePrioritizationError:
        logger.exception("Feature prioritization failed.")

        raise HTTPException(
            status_code=503,
            detail="Feature prioritization is temporarily unavailable.",
        ) from None

    except Exception:
        logger.exception(
            "Unexpected error during feature prioritization."
        )

        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred during feature prioritization.",
        ) from None

# =========================================================
# UNIFIED PRODUCT ASSISTANT CHATBOT
# =========================================================

@app.post(
    "/chat",
    response_model=ChatResponse,
)
def unified_product_assistant(
    request: ChatRequest,
) -> ChatResponse:

    try:
        return process_chat(request)

    except ChatOrchestrationError:
        logger.exception(
            "Unified Product Assistant request failed."
        )

        raise HTTPException(
            status_code=503,
            detail="The Product Assistant is temporarily unavailable.",
        ) from None

    except Exception:
        logger.exception(
            "Unexpected unified chatbot error."
        )

        raise HTTPException(
            status_code=500,
            detail="An unexpected chatbot error occurred.",
        ) from None

# =========================================================
# COMPLETE FOUR-AGENT PIPELINE
# =========================================================

@app.post("/analysis/run-all")
def run_complete_analysis(
    request: AnalysisRunRequest | None = None,
) -> dict:
    """
    Execute the four-agent sequential analysis pipeline.

    Production:
        The main backend supplies feedback records.
        Records are processed in bounded batches.

    Streaming backend:
        Sends one MongoDB batch per request.

    Development:
        An empty request body uses local JSON datasets.
    """

    try:
        # Local development fallback.
        if request is None:

            logger.info(
                "Starting four-agent analysis using local JSON datasets."
            )

            result = run_all_analyses()

        else:

            records = request.feedback_records
            batch_size = request.batch_size

            logger.info(
                "Starting AI analysis: %d records, batch size %d.",
                len(records),
                batch_size,
            )

            # Preserve compatibility with requests containing up to
            # 10,000 records. The backend streaming service sends
            # only one bounded batch in each request.
            result = run_batched_analyses(
                records=records,
                single_batch_runner=lambda batch: run_all_analyses(
                    records=batch
                ),
                batch_size=batch_size,
            )

        logger.info(
            "Analysis finished: status=%s, records=%s, batches=%s.",
            result.get("status"),
            result.get("total_feedback_analyzed"),
            (result.get("batch_summary") or {}).get(
                "total_batches",
                1,
            ),
        )

        return result

    except (OrchestrationError, BatchAnalysisError) as exc:

        logger.exception(
            "Analysis orchestration could not start."
        )

        raise HTTPException(
            status_code=422,
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


# =========================================================
# DETERMINISTIC BATCH AGGREGATION
# =========================================================

@app.post("/analysis/aggregate-batches")
def aggregate_streamed_batches(
    request: BatchAggregationRequest,
) -> dict:
    """
    Merge already-completed batch results.

    This endpoint does not execute Gemini or any AI agent.
    It performs deterministic Python aggregation only.

    Used by the main backend after all MongoDB batches
    have been independently processed and persisted.
    """

    try:

        result = aggregate_batch_responses(
            request.batch_responses,
            total_feedback_analyzed=request.total_feedback_analyzed,
            source_counts=request.source_counts,
            batch_size=request.batch_size,
        )

        # Batch documents are already persisted by the main backend.
        # Avoid returning a second copy of all individual batch results.
        result.pop("batch_results", None)

        return result

    except BatchAnalysisError as exc:

        logger.warning(
            "Invalid batch aggregation request: %s",
            exc,
        )

        raise HTTPException(
            status_code=422,
            detail=str(exc),
        ) from None

    except Exception:

        logger.exception(
            "Could not aggregate streamed analysis batches."
        )

        raise HTTPException(
            status_code=500,
            detail="Could not merge the analysis batches.",
        ) from None
