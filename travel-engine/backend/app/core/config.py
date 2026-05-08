import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    PROJECT_NAME: str = "Travel Planning Engine"
    API_V1_STR: str = "/api/v1"
    
    # DB
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./traveldb.sqlite")

    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Google Services
    USE_MOCK_GOOGLE: bool = os.getenv("USE_MOCK_GOOGLE", "true").lower() == "true"
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "test-project")
    
    # Auth
    FIREBASE_CREDENTIALS_PATH: str | None = os.getenv("FIREBASE_CREDENTIALS_PATH", None)

    class Config:
        case_sensitive = True

settings = Settings()
