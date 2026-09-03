"""Asset model."""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, Integer, String, JSON, Index, Text
from sqlalchemy.dialects.postgresql import UUID

from app.models.base import Base


class Asset(Base):
    """A versioned document or dataset asset."""

    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    

    # Core Metadata
    filename = Column(String, nullable=False)
    asset_type = Column(String, nullable=False) # document | dataset | image
    document_type = Column(String, nullable=False) # pdf | docx | csv | xlsx | ...
    mime_type = Column(String, nullable=False)
    file_size = Column(BigInteger, nullable=False)
    processing_status = Column(String, nullable=False, default="pending")
    storage_path = Column(String, nullable=False)
    
    # Extraction outputs
    page_count = Column(Integer, nullable=True)
    has_ocr = Column(Boolean, nullable=False, default=False)
    chunk_count = Column(Integer, nullable=False, default=0)
    extracted_text = Column(Text, nullable=True)
    language = Column(String, nullable=True)
    
    # Pipeline Metadata
    parser_metadata = Column(JSON, nullable=True)
    extraction_metadata = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

