"""Workspace endpoints v2."""

import uuid
from typing import Sequence

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse, WorkspaceUpdate
from app.services.workspace_service import workspace_service

router = APIRouter(prefix="/workspaces", tags=["Workspaces (v2)"])


@router.post("", response_model=WorkspaceResponse, status_code=201)
def create_workspace(workspace_in: WorkspaceCreate, db: Session = Depends(get_db)):
    return workspace_service.create(db, workspace_in)


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    workspaces = workspace_service.list_all(db, skip=skip, limit=limit)
    for ws in workspaces:
        ws.stats = workspace_service.get_stats(db, ws.id)
    return workspaces


@router.get("/{workspace_id}", response_model=WorkspaceResponse)
def get_workspace(workspace_id: uuid.UUID, db: Session = Depends(get_db)):
    workspace = workspace_service.get(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace.stats = workspace_service.get_stats(db, workspace.id)
    return workspace


@router.patch("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: uuid.UUID, workspace_in: WorkspaceUpdate, db: Session = Depends(get_db)
):
    workspace = workspace_service.get(db, workspace_id)
    if not workspace:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace_service.update(db, workspace, workspace_in)


from app.dependencies import get_asset_service
from app.services.asset_service import AssetService

@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(
    workspace_id: uuid.UUID, 
    db: Session = Depends(get_db),
    asset_svc: AssetService = Depends(get_asset_service)
):
    if not workspace_service.delete(db, workspace_id, asset_svc):
        raise HTTPException(status_code=404, detail="Workspace not found")
