"""Internal schemas for the ingestion pipeline."""

import dataclasses
import uuid
from typing import Any

@dataclasses.dataclass
class ExtractionResult:
    """Output from the ExtractionService."""
    markdown: str
    page_count: int | None
    language: str | None
    parser_metadata: dict[str, Any]
    extraction_metadata: dict[str, Any]

@dataclasses.dataclass
class EnrichedChunkData:
    """Data container for a generated text chunk with metadata."""
    chunk_index: int
    page_number: int | None
    chunk_text: str
    character_count: int
    content_hash: str
    heading_context: str | None
    section_context: str | None
    workspace_id: uuid.UUID
    folder_id: uuid.UUID | None
    asset_id: uuid.UUID
    
@dataclasses.dataclass
class EmbeddingResult:
    """Output from the EmbeddingService."""
    vectors: list[list[float]]
    embedding_model: str
    embedding_model_version: str
    embedding_dimension: int
