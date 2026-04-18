import os
from pathlib import Path

from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    llm_provider: str = "anthropic"  # "gemini", "anthropic", or "openai"
    llm_api_key: str = ""
    llm_model: str = "claude-sonnet-4-20250514"

    # Backend
    max_upload_size_mb: int = 50
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:3001"]

    model_config = {"env_prefix": "MTS_", "env_file": str(BACKEND_DIR / ".env")}


settings = Settings()
