"""Pydantic schemas for folders."""

from datetime import datetime
import uuid

from pydantic import BaseModel, ConfigDict, Field


class FolderBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)


class FolderCreate(FolderBase):
    parent_folder_id: uuid.UUID | None = None


class FolderUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=100)
    parent_folder_id: uuid.UUID | None = None


class FolderResponse(FolderBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    parent_folder_id: uuid.UUID | None
    path: str
    depth: int
    created_at: datetime
    updated_at: datetime
