
"""
FastAPI application for the AI-Driven Product Assistant.
"""

import os
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware


# Make backend and project root importable.
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(1, PROJECT_ROOT)


from config import Config
from db import init_db, get_client, get_db, close_client
from database import create_indexes

from routes.auth_routes import router as auth_router
from routes.state_routes import router as state_router
from routes.feedback_routes import router as feedback_router
from routes.workspace_routes import router as workspace_router
from routes.theme_routes import router as theme_router
from routes.feature_routes import router as feature_router
from routes.prd_routes import router as prd_router
from routes.roadmap_routes import router as roadmap_router
from routes.dashboard_routes import router as dashboard_router
from routes.preferences_routes import router as preferences_router
from routes.chat_routes import router as chat_router
from routes.product_routes import router as product_router


ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
]


def create_app(test_config=None):
    """Create and configure a FastAPI application."""

    settings = {
        "SECRET_KEY": Config.SECRET_KEY,
        "MONGO_URI": Config.MONGO_URI,
        "MONGO_DB_NAME": Config.MONGO_DB_NAME,
        "ENSURE_INDEXES": getattr(Config, "ENSURE_INDEXES", True),
        "TESTING": False,
    }

    if test_config:
        settings.update(test_config)

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        """Initialize MongoDB and indexes when the application starts."""

        print("Initializing MongoDB connection...")

        init_db(
            mongo_uri=settings["MONGO_URI"],
            db_name=settings["MONGO_DB_NAME"],
        )

        if settings["ENSURE_INDEXES"]:
            create_indexes(get_db())

        print("MongoDB initialization completed.")

        try:
            yield
        finally:
            close_client()
            print("MongoDB connection closed.")

    application = FastAPI(
        title="AI-Driven Product Assistant API",
        description="Backend API for the AI-Driven Product Assistant.",
        version="1.0.0",
        lifespan=lifespan,
    )

    application.state.settings = settings
    application.state.testing = settings["TESTING"]

    # Allow requests from the React frontend.
    application.add_middleware(
        CORSMiddleware,
        allow_origins=ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Cookie-based sessions.
    application.add_middleware(
        SessionMiddleware,
        secret_key=settings["SECRET_KEY"],
        same_site="lax",
        https_only=False,
    )

    # Register API routes.
    application.include_router(auth_router)
    application.include_router(state_router)
    application.include_router(feedback_router)
    application.include_router(workspace_router)
    application.include_router(theme_router)
    application.include_router(feature_router)
    application.include_router(prd_router)
    application.include_router(roadmap_router)
    application.include_router(dashboard_router)
    application.include_router(preferences_router)
    application.include_router(chat_router)
    application.include_router(product_router)

    @application.get("/")
    def index():
        """Return basic API information."""

        return {
            "success": True,
            "message": (
                "AI-Driven Product Assistant Backend API is running."
            ),
            "endpoints": "/api/health",
            "docs": "/docs",
        }

    @application.get("/api/health")
    def health():
        """Check API availability and MongoDB connectivity."""

        try:
            client = get_client()

            if client is None:
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "degraded",
                        "database": "not_initialized",
                        "message": "MongoDB client is not initialized.",
                    },
                )

            client.admin.command("ping")

            return {
                "status": "healthy",
                "database": "connected",
                "db_name": settings["MONGO_DB_NAME"],
            }

        except Exception:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "unhealthy",
                    "database": "disconnected",
                    "message": "Could not connect to MongoDB.",
                },
            )

    @application.exception_handler(HTTPException)
    async def http_exception_handler(
        request: Request,
        exc: HTTPException,
    ):
        """Return consistent HTTP errors."""

        message = (
            exc.detail
            if isinstance(exc.detail, str)
            else "The request could not be completed."
        )

        return JSONResponse(
            status_code=exc.status_code,
            content={
                "success": False,
                "data": None,
                "message": message,
            },
            headers=exc.headers,
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ):
        """Return consistent validation errors."""

        return JSONResponse(
            status_code=422,
            content={
                "success": False,
                "data": None,
                "message": "Validation error",
                "errors": exc.errors(),
            },
        )

    return application


# Application instance used by Uvicorn.
app = create_app()
