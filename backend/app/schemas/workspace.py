"""Pydantic schemas for workspaces."""

from datetime import datetime
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field


class WorkspaceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str | None = None
    settings: dict[str, Any] | None = None


class WorkspaceCreate(WorkspaceBase):
    pass


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    description: str | None = None
    settings: dict[str, Any] | None = None


class WorkspaceStats(BaseModel):
    total_folders: int = 0
    total_assets: int = 0
    total_chunks: int = 0
    total_embeddings: int = 0


class WorkspaceResponse(WorkspaceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    stats: WorkspaceStats | None = None
