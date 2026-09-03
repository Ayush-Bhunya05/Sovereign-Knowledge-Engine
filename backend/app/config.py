"""Application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralised application settings.

    Values are read from environment variables and the ``.env`` file located
    in the working directory (``backend/.env`` during development).
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application -----------------------------------------------------------
    app_name: str = "AI Document RAG"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Vision (Sprint 2.3) ---------------------------------------------------
    gemini_api_key: str | None = None
    gemini_vision_model: str | None = None
    gemini_planner_model: str = "gemini-3.5-flash-lite"

    # Database --------------------------------------------------------------
    database_url: str = "postgresql://docrag:docrag@localhost:5433/docrag"

    # Milvus (Phase 3 -> Sprint 2.2) -----------------------------------------
    milvus_host: str = "localhost"
    milvus_port: int = 19530
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"

    # Storage ---------------------------------------------------------------
    upload_dir: str = "uploads"
    max_upload_size_mb: int = 50

    # Chunking (Sprint 2.1) -------------------------------------------------
    chunk_size: int = 512
    chunk_overlap: int = 64

    # Search (Phase 3) ------------------------------------------------------
    search_default_top_k: int = 5
    search_similarity_metric: str = "COSINE"
    search_min_score: float = 0.65

    # CORS ------------------------------------------------------------------
    cors_origins: str = "http://localhost:5173"



    # Derived helpers -------------------------------------------------------
    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return a cached settings instance (singleton)."""
    return Settings()
