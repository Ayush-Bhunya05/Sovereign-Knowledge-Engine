"""Pydantic schemas for search."""

import uuid
from typing import Any

from pydantic import BaseModel, ConfigDict


class SearchQuery(BaseModel):
    query: str
    folder_id: uuid.UUID | None = None
    asset_id: uuid.UUID | None = None
    top_k: int = 10


class SearchResultItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: uuid.UUID
    asset_id: uuid.UUID
    filename: str
    document_type: str
    page_number: int | None
    chunk_index: int
    chunk_text: str
    similarity_score: float
