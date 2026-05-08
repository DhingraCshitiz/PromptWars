from pathlib import Path
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_BACKEND_ROOT = Path(__file__).resolve().parent.parent.parent
_DOTENV_PATH = _BACKEND_ROOT / ".env"


def _settings_config() -> SettingsConfigDict:
    """Load `backend/.env` when present; env vars still override file values."""
    cfg: dict[str, Any] = {
        "case_sensitive": True,
        "extra": "ignore",
    }
    if _DOTENV_PATH.is_file():
        cfg["env_file"] = _DOTENV_PATH
        cfg["env_file_encoding"] = "utf-8"
    return SettingsConfigDict(**cfg)


class Settings(BaseSettings):
    model_config = _settings_config()

    PROJECT_NAME: str = "Travel Planning Engine"
    API_V1_STR: str = "/api/v1"

    # Comma-separated origins, or * for all origins (allow_credentials=False per CORS rules).
    # Tighten before production: e.g. https://app.example.com,http://localhost:4200
    CORS_ORIGINS: str = "*"

    DATABASE_URL: str = "sqlite+aiosqlite:///./traveldb.sqlite"
    SQLALCHEMY_ECHO: bool = False

    REDIS_URL: str = "redis://localhost:6379"

    # Google AI Studio / Gemini API (recommended for real itineraries)
    GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "gemini-1.5-flash"

    # Legacy Vertex path when no API key and USE_MOCK_GOOGLE is false
    USE_MOCK_GOOGLE: bool = True
    GOOGLE_CLOUD_PROJECT: str = "test-project"

    FIREBASE_CREDENTIALS_PATH: str | None = None

    @field_validator("SQLALCHEMY_ECHO", "USE_MOCK_GOOGLE", mode="before")
    @classmethod
    def bool_from_env_string(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v.lower() == "true"
        return v

    @field_validator("GEMINI_API_KEY", mode="before")
    @classmethod
    def empty_gemini_key(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, str):
            stripped = v.strip()
            if not stripped:
                return None
            if len(stripped) >= 2 and stripped[0] == stripped[-1] and stripped[0] in {'"', "'"}:
                stripped = stripped[1:-1].strip()
            return stripped if stripped else None
        return v


settings = Settings()
