import os

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional


def _env_file_candidates() -> tuple[str, ...]:
    """Load .env.<ENV> first and fall back to .env for shared defaults."""
    env_name = os.getenv("ENV", "local").strip().lower()
    if not env_name:
        env_name = "local"
    return (f".env.{env_name}", ".env")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=_env_file_candidates(), case_sensitive=True)

    ENV: str = Field(default="local")
    DEBUG: bool = Field(default=True)

    APP_NAME: str = "Conversational CV Builder"
    API_PREFIX: str = "/api/v1"
    CORS_ORIGINS: list[str] = Field(
        default_factory=lambda: ["http://localhost:8000", "http://127.0.0.1:8000"]
    )

    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4.1-mini")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    OPENAI_TEMPERATURE: float = Field(default=0.1)
    OPENAI_MAX_TOKENS: int = Field(default=4000)
    OPENAI_VERIFY_SSL: bool = Field(default=True)

    # LLM Enhancement Settings
    LLM_ENHANCEMENT_MODEL: str = Field(default="gpt-4o-mini")
    LLM_ENHANCEMENT_TEMPERATURE: float = Field(default=0.3)
    LLM_ENHANCEMENT_MAX_TOKENS: int = Field(default=2000)
    LLM_SUMMARY_MAX_TOKENS: int = Field(default=500)
    LLM_ACHIEVEMENT_MAX_TOKENS: int = Field(default=500)

    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: Optional[str] = None

    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=3306)
    DB_NAME: str = Field(default="cv_builder")
    DB_USER: str = Field(default="root")
    DB_PASSWORD: str = Field(default="")

    STORAGE_TYPE: str = Field(default="local")
    LOCAL_STORAGE_PATH: str = Field(default="./data/storage")

    TEMPLATE_BASE_PATH: str = Field(default="./src/templates")
    DEFAULT_TEMPLATE: str = Field(default="standard_nttdata")
    QUESTIONNAIRE_PATH: str = Field(default="./config/questionnaire")

    ENABLE_RAG: bool = Field(default=True)
    ENABLE_VOICE: bool = Field(default=True)
    ENABLE_REVIEW: bool = Field(default=False)
    ENABLE_RBAC: bool = Field(default=False)
    
    # LLM Extraction and Normalization (Phase 5)
    ENABLE_LLM_EXTRACTION: bool = Field(default=False)
    ENABLE_LLM_NORMALIZATION: bool = Field(default=False)
    
    SESSION_REPOSITORY_BACKEND: str = Field(default="memory")
    SESSION_FILE_STORE_PATH: str = Field(default="./data/storage/sessions")

    LOG_LEVEL: str = Field(default="INFO")
    LOG_TO_FILE: bool = Field(default=True)
    LOG_FILE_PATH: str = Field(default="./log/app.log")
    LOG_NEWEST_FIRST: bool = Field(default=True)
    SUPPRESS_CONSOLE_PRINTS: bool = Field(default=True)
    SECRET_KEY: str = Field(default="replace-with-env-secret-key")
    ALGORITHM: str = Field(default="HS256")
    TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    SPEECH_PROVIDER: str = Field(default="whisper")
    WHISPER_MODEL: str = Field(default="whisper-1")
    AZURE_SPEECH_KEY: Optional[str] = None
    AZURE_SPEECH_REGION: Optional[str] = None
    AZURE_SPEECH_LANGUAGE: str = Field(default="en-US")

settings = Settings()
