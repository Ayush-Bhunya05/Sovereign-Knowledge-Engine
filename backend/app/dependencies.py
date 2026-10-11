"""FastAPI dependency injection functions.

All shared dependencies (DB sessions, service instances) are defined here
so that API routes remain thin and testable.
"""

from collections.abc import Generator
from functools import lru_cache

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.services.ingestion.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.ingestion.extraction_service import ExtractionService
from app.services.milvus_service import MilvusService
from app.services.chroma_service import ChromaService
from app.services.ingestion.orchestrator import IngestionOrchestrator
from app.services.asset_service import AssetService
from app.services.storage_service import LocalStorageService
from app.services.search_service import SearchService
from app.services.ingestion.structured_data_service import StructuredDataService


# ------------------------------------------------------------------
# Database session
# ------------------------------------------------------------------

def get_db() -> Generator[Session, None, None]:
    """Yield a database session, ensuring it is closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------------------------------------------------
# Service singletons
# ------------------------------------------------------------------

@lru_cache
def get_storage_service() -> LocalStorageService:
    settings = get_settings()
    return LocalStorageService(settings.upload_dir)


@lru_cache
def get_extraction_service() -> ExtractionService:
    settings = get_settings()
    api_key = settings.gemini_api_key
    return ExtractionService(
        api_key=api_key,
        vision_model=settings.gemini_vision_model
    )


@lru_cache
def get_chunking_service() -> ChunkingService:
    settings = get_settings()
    return ChunkingService(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )


@lru_cache
def get_embedding_service() -> EmbeddingService:
    settings = get_settings()
    return EmbeddingService(model_name=settings.embedding_model_name)


@lru_cache
def get_chroma_service() -> ChromaService:
    settings = get_settings()
    return ChromaService(persist_dir=settings.chroma_persist_dir)


@lru_cache
def get_vector_service() -> ChromaService | MilvusService:
    settings = get_settings()
    if settings.vector_db_provider.lower() == "milvus":
        return MilvusService(
            host=settings.milvus_host,
            port=settings.milvus_port,
        )
    return get_chroma_service()


@lru_cache
def get_milvus_service() -> ChromaService | MilvusService:
    """Backward-compatible dependency alias pointing to active vector service."""
    return get_vector_service()


@lru_cache
def get_structured_data_service() -> StructuredDataService:
    return StructuredDataService(
        embedding_service=get_embedding_service(),
        milvus_service=get_vector_service(),
    )


@lru_cache
def get_ingestion_orchestrator() -> IngestionOrchestrator:
    """Return configured IngestionOrchestrator."""
    return IngestionOrchestrator(
        extraction_service=get_extraction_service(),
        chunking_service=get_chunking_service(),
        embedding_service=get_embedding_service(),
        milvus_service=get_vector_service(),
        storage_service=get_storage_service(),
        structured_data_service=get_structured_data_service(),
    )


@lru_cache
def get_asset_service() -> AssetService:
    return AssetService(
        storage_service=get_storage_service(),
        ingestion_orchestrator=get_ingestion_orchestrator()
    )


@lru_cache
def get_search_service() -> SearchService:
    return SearchService(
        milvus_service=get_vector_service(),
        embedding_service=get_embedding_service()
    )


@lru_cache
def get_query_planner_service() -> "QueryPlannerService":
    import os
    import logging
    from langchain_google_genai import ChatGoogleGenerativeAI
    from app.services.query_planner_service import QueryPlannerService
    from app.config import get_settings
    
    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        logger = logging.getLogger(__name__)
        logger.warning("GEMINI_API_KEY not set. QueryPlannerService will fail on execution.")
        api_key = "DUMMY_KEY_TO_PREVENT_CRASH"
        
    llm = ChatGoogleGenerativeAI(model=settings.gemini_planner_model, temperature=0, api_key=api_key)
    return QueryPlannerService(llm=llm)


@lru_cache
def get_agentic_orchestrator_service() -> "AgenticOrchestratorService":
    from app.services.orchestrator.engine import AgenticOrchestratorService
    from app.services.orchestrator.provider import GeminiProvider
    from app.config import get_settings
    import logging
    
    settings = get_settings()
    api_key = settings.gemini_api_key
    if not api_key:
        logger = logging.getLogger(__name__)
        logger.warning("GEMINI_API_KEY not set. AgenticOrchestratorService will fail on execution.")
        api_key = "DUMMY_KEY_TO_PREVENT_CRASH"
        
    # Use GeminiProvider natively supporting tool calling
    provider = GeminiProvider(model_name=settings.gemini_planner_model, api_key=api_key, temperature=0.0)
    return AgenticOrchestratorService(provider=provider)
