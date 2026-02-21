"""Application configuration with environment-based settings."""

from __future__ import annotations

from enum import Enum
from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class VectorStoreProvider(str, Enum):
    CHROMA = "chroma"
    PINECONE = "pinecone"


class Settings(BaseSettings):
    """Central configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: Environment = Environment.DEVELOPMENT
    app_name: str = "Secure Financial Insights Copilot"
    app_version: str = "0.1.0"
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # OpenAI
    openai_api_key: SecretStr = Field(default=SecretStr(""))
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536
    max_token_output: int = 4096

    # Vector Store
    vector_store_provider: VectorStoreProvider = VectorStoreProvider.CHROMA
    chroma_persist_directory: str = "./chroma_db"
    pinecone_api_key: SecretStr = Field(default=SecretStr(""))
    pinecone_environment: str = ""
    pinecone_index_name: str = "financial-insights"

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/financial_insights"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # SEC EDGAR
    sec_edgar_user_agent: str = "FinancialInsights research@example.com"

    # Monitoring
    prometheus_enabled: bool = True

    # Guardrails
    pii_detection_enabled: bool = True
    content_filter_enabled: bool = True

    # Evaluation thresholds
    hallucination_threshold: float = 0.7
    consistency_threshold: float = 0.8
    min_confidence_score: float = 0.6

    # RAG settings
    chunk_size: int = 512
    chunk_overlap: int = 64
    retrieval_top_k: int = 8
    rerank_top_k: int = 4
    hybrid_search_alpha: float = 0.7  # weight for semantic vs keyword

    @property
    def is_production(self) -> bool:
        return self.app_env == Environment.PRODUCTION


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
