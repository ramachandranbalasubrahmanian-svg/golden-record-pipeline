from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    openai_api_key: str = "sk-placeholder"
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/golden_record"
    sync_database_url: str = "postgresql://postgres:password@localhost:5432/golden_record"
    api_key: str = "demo-key-2026"
    openai_embedding_model: str = "text-embedding-3-small"
    openai_chat_model: str = "gpt-4o-mini"
    embedding_dimensions: int = 1536
    max_rag_chunks: int = 10
    environment: str = "development"

    @field_validator("database_url", mode="before")
    @classmethod
    def ensure_asyncpg(cls, v: str) -> str:
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    @field_validator("sync_database_url", mode="before")
    @classmethod
    def ensure_sync(cls, v: str) -> str:
        return v.replace("postgresql+asyncpg://", "postgresql://", 1)


settings = Settings()
