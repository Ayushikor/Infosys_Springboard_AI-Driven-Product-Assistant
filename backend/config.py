"""Configuration for the AI-Driven Product Assistant."""

import os
from dotenv import load_dotenv

# Load environment variables from the backend .env file.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class Config:
    """Base configuration for the AI-Driven Product Assistant."""

    # MongoDB connection
    MONGO_URI = os.getenv(
        "MONGO_URI",
        "mongodb://localhost:27017",
    )

    # MongoDB database name
    MONGO_DB_NAME = os.getenv(
        "MONGO_DB_NAME",
        "product_assistant_db",
    )

    # Secret key for session management
    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        "dev-secret-change-me",
    )

    # Application debug mode
    DEBUG = os.getenv(
        "DEBUG",
        "0",
    ) == "1"

    # FastAPI backend port
    PORT = int(os.getenv("PORT", "8000"))

    # Automatically create MongoDB indexes
    ENSURE_INDEXES = os.getenv(
        "ENSURE_INDEXES",
        "true",
    ).lower() in ("1", "true", "yes")