"""
Application configuration loaded from environment variables.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=False)


class Settings:
    """Application settings loaded from .env file."""

    OLLAMA_API_KEY: str = os.getenv("OLLAMA_API_KEY", "")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3.5:cloud")
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "https://ollama.com")
    REQUEST_TIMEOUT_SECONDS: int = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
    APP_ENV: str = os.getenv("APP_ENV", "development")

    # Maximum HTML content size to fetch (5MB)
    MAX_CONTENT_SIZE: int = 5 * 1024 * 1024

    # --- V2 ---
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/analyzer.db")
    MAX_MULTI_PAGE_URLS: int = int(os.getenv("MAX_MULTI_PAGE_URLS", "10"))
    MULTI_PAGE_CONCURRENCY: int = int(os.getenv("MULTI_PAGE_CONCURRENCY", "3"))
    RATE_LIMIT_ANALYZE: str = os.getenv("RATE_LIMIT_ANALYZE", "10/minute")
    RATE_LIMIT_MULTI_PAGE: str = os.getenv("RATE_LIMIT_MULTI_PAGE", "3/minute")
    AI_STREAM_TIMEOUT_SECONDS: int = int(os.getenv("AI_STREAM_TIMEOUT_SECONDS", "90"))


settings = Settings()
