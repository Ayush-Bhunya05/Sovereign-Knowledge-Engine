"""Asset Chunk model."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class AssetChunk(Base):
    """A text chunk from an asset, with embedding metadata."""

    __tablename__ = "asset_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    
    # Denormalized scope references for faster Milvus filtering
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=True)
    chunk_text = Column(Text, nullable=False)
    character_count = Column(Integer, nullable=False)
    content_hash = Column(String(64), nullable=False) # SHA-256
    
    # Structural Context
    heading_context = Column(String, nullable=True)
    section_context = Column(String, nullable=True)
    chunk_metadata = Column(JSON, nullable=True)
    
    # Embedding Traceability
    embedding_model = Column(String, nullable=True)
    embedding_model_version = Column(String, nullable=True)
    embedding_dimension = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
