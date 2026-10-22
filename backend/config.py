"""Configuration for the AI-Driven Product Assistant."""

import os
from dotenv import load_dotenv

# Load environment variables from the backend .env file.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))


class Config:
    """Base configuration for the AI-Driven Product Assistant."""

    MONGO_URI = os.getenv(
        "MONGO_URI",
        "mongodb://localhost:27017",
    )

    MONGO_DB_NAME = os.getenv(
        "MONGO_DB_NAME",
        "product_assistant_db",
    )

    SECRET_KEY = os.getenv(
        "SECRET_KEY",
        os.getenv("FLASK_SECRET_KEY", "dev-secret-change-me"),
    )

    DEBUG = os.getenv(
        "DEBUG",
        os.getenv("FLASK_DEBUG", "0"),
    ) == "1"

    PORT = int(os.getenv("PORT", "8000"))

    ENSURE_INDEXES = os.getenv(
        "ENSURE_INDEXES",
        "true",
    ).lower() in ("1", "true", "yes")