from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    ENV: str = Field(default="local")
    DEBUG: bool = Field(default=True)

    APP_NAME: str = "Conversational CV Builder"
    API_PREFIX: str = "/api/v1"

    OPENAI_API_KEY: Optional[str] = Field(default=None)
    OPENAI_MODEL: str = Field(default="gpt-4.1-mini")
    OPENAI_EMBEDDING_MODEL: str = Field(default="text-embedding-3-small")
    OPENAI_TEMPERATURE: float = Field(default=0.1)
    OPENAI_MAX_TOKENS: int = Field(default=4000)
    OPENAI_VERIFY_SSL: bool = Field(default=True)

    AZURE_OPENAI_ENDPOINT: Optional[str] = None
    AZURE_OPENAI_API_KEY: Optional[str] = None
    AZURE_OPENAI_DEPLOYMENT: Optional[str] = None
    AZURE_OPENAI_EMBEDDING_DEPLOYMENT: Optional[str] = None

    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=3306)
    DB_NAME: str = Field(default="cv_builder")
    DB_USER: str = Field(default="root")
    DB_PASSWORD: str = Field(default="password")

    STORAGE_TYPE: str = Field(default="local")
    LOCAL_STORAGE_PATH: str = Field(default="./data/storage")

    TEMPLATE_BASE_PATH: str = Field(default="./src/templates")
    DEFAULT_TEMPLATE: str = Field(default="standard_nttdata")
    QUESTIONNAIRE_PATH: str = Field(default="./config/questionnaire")

    ENABLE_RAG: bool = Field(default=True)
    ENABLE_VOICE: bool = Field(default=True)
    ENABLE_REVIEW: bool = Field(default=False)
    ENABLE_RBAC: bool = Field(default=False)

    LOG_LEVEL: str = Field(default="INFO")
    SECRET_KEY: str = Field(default="super-secret-key")
    TOKEN_EXPIRE_MINUTES: int = Field(default=60)

    SPEECH_PROVIDER: str = Field(default="whisper")
    WHISPER_MODEL: str = Field(default="whisper-1")
    AZURE_SPEECH_KEY: Optional[str] = None
    AZURE_SPEECH_REGION: Optional[str] = None
    AZURE_SPEECH_LANGUAGE: str = Field(default="en-US")

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
