"""Pydantic schemas for asset chunks."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict


class AssetChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    asset_id: uuid.UUID
    chunk_index: int
    page_number: int | None = None
    chunk_text: str
    character_count: int
    content_hash: str
    heading_context: str | None = None
    section_context: str | None = None
    chunk_metadata: dict[str, Any] | None = None
    created_at: datetime
