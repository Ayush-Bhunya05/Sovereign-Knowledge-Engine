"""Asset endpoints v2."""

import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Form, BackgroundTasks
from sqlalchemy.orm import Session

from app.dependencies import get_db, get_asset_service
from app.schemas.asset import AssetResponse, AssetUploadResponse
from app.services.asset_service import AssetService
from app.services.workspace_service import workspace_service
from app.services.folder_service import folder_service

router = APIRouter(prefix="/workspaces/{workspace_id}/assets", tags=["Assets (v2)"])

MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/upload", response_model=AssetUploadResponse, status_code=201)
def upload_asset(
    workspace_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    folder_id: uuid.UUID | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    asset_svc: AssetService = Depends(get_asset_service),
):
    if not workspace_service.get(db, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    if folder_id and not folder_service.get(db, workspace_id, folder_id):
        raise HTTPException(status_code=404, detail="Folder not found in workspace")

    try:
        return asset_svc.upload_asset(
            db=db,
            workspace_id=workspace_id,
            folder_id=folder_id,
            file=file,
            max_upload_size_bytes=MAX_UPLOAD_SIZE,
            background_tasks=background_tasks
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")


@router.get("", response_model=list[AssetResponse])
def list_assets(
    workspace_id: uuid.UUID, 
    folder_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    asset_svc: AssetService = Depends(get_asset_service),
):
    if not workspace_service.get(db, workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
        
    return asset_svc.list_in_workspace(db, workspace_id, folder_id)


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset(workspace_id: uuid.UUID, asset_id: uuid.UUID, db: Session = Depends(get_db), asset_svc: AssetService = Depends(get_asset_service)):
    asset = asset_svc.get(db, asset_id)
    if not asset or asset.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    return asset


@router.delete("/{asset_id}", status_code=204)
def delete_asset(workspace_id: uuid.UUID, asset_id: uuid.UUID, db: Session = Depends(get_db), asset_svc: AssetService = Depends(get_asset_service)):
    asset = asset_svc.get(db, asset_id)
    if not asset or asset.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    if not asset_svc.delete(db, asset_id):
        raise HTTPException(status_code=404, detail="Asset not found")


@router.get("/{asset_id}/text")
def get_asset_text(workspace_id: uuid.UUID, asset_id: uuid.UUID, db: Session = Depends(get_db), asset_svc: AssetService = Depends(get_asset_service)):
    asset = asset_svc.get(db, asset_id)
    if not asset or asset.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Asset not found")
    return {"extracted_text": asset.extracted_text}


@router.get("/{asset_id}/chunks")
def get_asset_chunks(workspace_id: uuid.UUID, asset_id: uuid.UUID, db: Session = Depends(get_db), asset_svc: AssetService = Depends(get_asset_service)):
    from app.models.asset_chunk import AssetChunk
    from app.schemas.asset_chunk import AssetChunkResponse
    
    asset = asset_svc.get(db, asset_id)
    if not asset or asset.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    chunks = db.query(AssetChunk).filter(AssetChunk.asset_id == asset_id).order_by(AssetChunk.chunk_index).all()
    return [AssetChunkResponse.model_validate(c) for c in chunks]
