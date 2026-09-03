"""Service for managing workspaces."""

import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from app.models.workspace import Workspace
from app.schemas.workspace import WorkspaceCreate, WorkspaceUpdate


class WorkspaceService:
    def create(self, db: Session, workspace_in: WorkspaceCreate) -> Workspace:
        workspace = Workspace(
            name=workspace_in.name,
            description=workspace_in.description,
            settings=workspace_in.settings,
        )
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        return workspace

    def get(self, db: Session, workspace_id: uuid.UUID) -> Workspace | None:
        return db.query(Workspace).filter(Workspace.id == workspace_id).first()

    def get_stats(self, db: Session, workspace_id: uuid.UUID) -> dict:
        from app.models.folder import Folder
        from app.models.asset import Asset
        from app.models.asset_chunk import AssetChunk
        from sqlalchemy import func

        folders_count = db.query(func.count(Folder.id)).filter(Folder.workspace_id == workspace_id).scalar() or 0
        assets_count = db.query(func.count(Asset.id)).filter(Asset.workspace_id == workspace_id).scalar() or 0
        chunks_count = db.query(func.count(AssetChunk.id)).filter(AssetChunk.workspace_id == workspace_id).scalar() or 0
        
        # In our case, 1 chunk = 1 embedding. So embeddings_count = chunks_count
        return {
            "total_folders": folders_count,
            "total_assets": assets_count,
            "total_chunks": chunks_count,
            "total_embeddings": chunks_count
        }

    def list_all(self, db: Session, skip: int = 0, limit: int = 100) -> Sequence[Workspace]:
        return db.query(Workspace).order_by(Workspace.created_at.desc()).offset(skip).limit(limit).all()

    def update(self, db: Session, workspace: Workspace, workspace_in: WorkspaceUpdate) -> Workspace:
        update_data = workspace_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(workspace, field, value)
        db.add(workspace)
        db.commit()
        db.refresh(workspace)
        return workspace

    def delete(self, db: Session, workspace_id: uuid.UUID, asset_svc=None) -> bool:
        workspace = self.get(db, workspace_id)
        if not workspace:
            return False
            
        if asset_svc:
            from app.models.asset import Asset
            assets = db.query(Asset).filter(Asset.workspace_id == workspace_id).all()
            for asset in assets:
                asset_svc.delete(db, asset.id)
                
        db.delete(workspace)
        db.commit()
        return True


workspace_service = WorkspaceService()
