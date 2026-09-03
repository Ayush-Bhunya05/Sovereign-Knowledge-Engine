"""Dataset model for structured data (CSV/XLSX)."""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.models.base import Base

class Dataset(Base):
    """A structured dataset derived from an asset."""
    __tablename__ = "datasets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False)
    folder_id = Column(UUID(as_uuid=True), ForeignKey("folders.id", ondelete="CASCADE"), nullable=True)
    
    name = Column(String, nullable=False)
    table_name = Column(String, unique=True, nullable=False)
    source_type = Column(String, nullable=False) # "csv" or "xlsx"
    source_sheet = Column(String, nullable=True) 
    source_range = Column(String, nullable=True) 
    
    row_count = Column(Integer, nullable=False, default=0)
    column_count = Column(Integer, nullable=False, default=0)
    
    schema_definition = Column(JSONB, nullable=True)
    column_stats = Column(JSONB, nullable=True)
    summary = Column(Text, nullable=True)
    parser_metadata = Column(JSONB, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
