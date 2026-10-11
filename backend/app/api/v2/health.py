"""Health-check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.dependencies import get_db, get_embedding_service, get_vector_service
from app.services.embedding_service import EmbeddingService

router = APIRouter(prefix="/health", tags=["Health"])


@router.get(
    "",
    summary="Basic health check",
    description="Returns application status and version.",
)
def health_check(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    vector_service = Depends(get_vector_service),
):
    # Check DB
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {str(e)}"

    vector_status = vector_service.check_health()

    return {
        "status": "healthy" if db_status == "ok" and vector_status.get("status") == "ok" else "degraded",
        "app_name": settings.app_name,
        "version": settings.app_version,
        "database": db_status,
        "embedding_model": embedding_service.check_health(),
        "vector_db": vector_status,
        "milvus": vector_status,  # Kept for backward compatibility
    }
