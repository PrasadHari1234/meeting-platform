from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_KEY: str

    # AI
    ANTHROPIC_API_KEY: str
    OPENAI_API_KEY: str          # for Whisper transcription

    # Auth
    SECRET_KEY: str              # random string for session signing
    GOOGLE_CLIENT_ID: str        # from Google Cloud Console
    GOOGLE_CLIENT_SECRET: str

    # App
    APP_URL: str = "http://localhost:8000"
    ENVIRONMENT: str = "development"

    # Claude model
    CLAUDE_MODEL: str = "claude-sonnet-4-6"

    # Default meeting buckets
    DEFAULT_BUCKETS: list[str] = [
        "Engineering / Tech",
        "Product / Design",
        "Marketing / GTM",
    ]

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
