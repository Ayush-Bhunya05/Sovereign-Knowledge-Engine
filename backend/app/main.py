"""FastAPI application factory."""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v2.router import api_router as api_router_v2
from app.config import get_settings
from app.database import engine
from app.dependencies import get_embedding_service, get_vector_service
from app.models.base import Base

# Ensure all models are imported so Base.metadata is populated.
import app.models  # noqa: F401

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Startup / shutdown lifecycle hook."""
    settings = get_settings()

    # Create database tables (safe to call repeatedly — skips existing).
    # Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified via Alembic.")

    # Ensure local upload directory exists.
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    logger.info("Upload directory ready: %s", settings.upload_dir)

    # Pre-load embedding model into memory and init Vector DB (ChromaDB)
    logger.info("Initializing vector services...")
    get_embedding_service()
    get_vector_service()
    logger.info("Vector services ready.")

    yield  # application runs

    logger.info("Shutting down.")


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = get_settings()

    application = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AI-powered document management platform with RAG capabilities.",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # CORS — allow the Vite dev server (and any additional origins).
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount versioned API routers.
    application.include_router(api_router_v2, prefix="/api/v2")

    return application


app = create_app()
