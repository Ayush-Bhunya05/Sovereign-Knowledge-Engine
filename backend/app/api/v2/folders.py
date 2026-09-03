"""Folder endpoints v2."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.dependencies import get_db
from app.schemas.folder import FolderCreate, FolderResponse, FolderUpdate
from app.services.folder_service import folder_service
from app.services.workspace_service import workspace_service

router = APIRouter(prefix="/workspaces/{workspace_id}/folders", tags=["Folders (v2)"])


@router.post("", response_model=FolderResponse, status_code=201)
def create_folder(
    workspace_id: uuid.UUID, folder_in: FolderCreate, db: Session = Depends(get_db)
):
    if not workspace_service.get(db, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    try:
        return folder_service.create(db, workspace_id, folder_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("", response_model=list[FolderResponse])
def list_folders(workspace_id: uuid.UUID, db: Session = Depends(get_db)):
    if not workspace_service.get(db, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    return folder_service.list_in_workspace(db, workspace_id)


@router.get("/{folder_id}", response_model=FolderResponse)
def get_folder(workspace_id: uuid.UUID, folder_id: uuid.UUID, db: Session = Depends(get_db)):
    folder = folder_service.get(db, workspace_id, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    return folder


@router.patch("/{folder_id}", response_model=FolderResponse)
def update_folder(
    workspace_id: uuid.UUID, 
    folder_id: uuid.UUID, 
    folder_in: FolderUpdate, 
    db: Session = Depends(get_db)
):
    folder = folder_service.get(db, workspace_id, folder_id)
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
        
    try:
        return folder_service.update(db, workspace_id, folder, folder_in)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{folder_id}", status_code=204)
def delete_folder(workspace_id: uuid.UUID, folder_id: uuid.UUID, db: Session = Depends(get_db)):
    if not folder_service.delete(db, workspace_id, folder_id):
        raise HTTPException(status_code=404, detail="Folder not found")
