
from typing import Optional

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):

    # Gemini configuration
    llm_provider: str = "gemini"
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.6-flash"

    # MongoDB Atlas configuration
    mongodb_uri: Optional[str] = None
    mongodb_database: str = "ai_feedback_intelligence"
    mongodb_analysis_collection: str = "analysis_runs"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()