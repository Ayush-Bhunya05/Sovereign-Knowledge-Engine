"""Pydantic schemas for assets."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict


class AssetResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    folder_id: uuid.UUID | None
    filename: str
    asset_type: str
    document_type: str
    mime_type: str
    file_size: int
    processing_status: str
    page_count: int | None = None
    has_ocr: bool
    chunk_count: int
    language: str | None = None
    parser_metadata: dict[str, Any] | None = None
    extraction_metadata: dict[str, Any] | None = None
    created_at: datetime
    updated_at: datetime


class AssetUploadResponse(AssetResponse):
    """Schema for upload response, might include extra fields if needed."""
    pass
