"""Service for managing assets."""

import uuid
from typing import Sequence

from fastapi import UploadFile, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.models.asset import Asset
from app.models.folder import Folder
from app.services.storage_service import LocalStorageService
from app.services.ingestion.orchestrator import IngestionOrchestrator
from app.utils.file_utils import validate_file_type, validate_file_size, generate_document_id
from app.database import SessionLocal


class AssetService:
    def __init__(
        self, 
        storage_service: LocalStorageService,
        ingestion_orchestrator: IngestionOrchestrator | None = None
    ):
        self.storage = storage_service
        self.orchestrator = ingestion_orchestrator

    def upload_asset(
        self, 
        db: Session, 
        workspace_id: uuid.UUID, 
        folder_id: uuid.UUID | None, 
        file: UploadFile, 
        max_upload_size_bytes: int,
        background_tasks: BackgroundTasks | None = None
    ) -> Asset:
        # 1. Validate file
        extension, document_type = validate_file_type(file.filename)
        file.file.seek(0, 2)
        file_size = file.file.tell()
        file.file.seek(0)
        validate_file_size(file_size, max_upload_size_bytes)
        
        # 3. Save file
        asset_id = generate_document_id()
        storage_path = self.storage.save(file, str(asset_id), extension)
        
        asset_type = "image" if document_type == "image" else "document"
        if document_type in ("csv", "xlsx"):
            asset_type = "dataset"

        # 4. Create record
        asset = Asset(
            id=asset_id,
            workspace_id=workspace_id,
            folder_id=folder_id,
            filename=file.filename or "unnamed",
            asset_type=asset_type,
            document_type=document_type,
            mime_type=file.content_type or "application/octet-stream",
            file_size=file_size,
            processing_status="pending",
            storage_path=storage_path,
        )
        
        db.add(asset)
        db.commit()
        db.refresh(asset)
        
        # 5. Trigger ingestion async
        print(f"DEBUG: orchestrator={self.orchestrator}, background_tasks={background_tasks}")
        if self.orchestrator and background_tasks:
            print("DEBUG: Adding background task for ingestion...")
            def run_ingestion(asset_id: uuid.UUID):
                print(f"DEBUG: Background task started for {asset_id}")
                try:
                    with SessionLocal() as async_db:
                        self.orchestrator.process_asset(async_db, asset_id)
                    print(f"DEBUG: Background task finished for {asset_id}")
                except Exception as e:
                    print(f"DEBUG: Background task failed: {e}")
            
            background_tasks.add_task(run_ingestion, asset.id)

        return asset

    def get(self, db: Session, asset_id: uuid.UUID) -> Asset | None:
        return db.query(Asset).filter(Asset.id == asset_id).first()

    def list_in_workspace(self, db: Session, workspace_id: uuid.UUID, folder_id: uuid.UUID | None = None) -> Sequence[Asset]:
        query = db.query(Asset).filter(Asset.workspace_id == workspace_id)
        if folder_id:
            query = query.filter(Asset.folder_id == folder_id)
        return query.order_by(Asset.created_at.desc()).all()

    def delete(self, db: Session, asset_id: uuid.UUID) -> bool:
        asset = self.get(db, asset_id)
        if not asset:
            return False
            
        # Delete file from storage
        self.storage.delete(asset.storage_path)
        
        # Delete vectors from Milvus
        if self.orchestrator and self.orchestrator.milvus:
            try:
                self.orchestrator.milvus.delete_asset_vectors(str(asset_id))
            except Exception as e:
                print(f"Warning: Failed to delete Milvus vectors for asset {asset_id}: {e}")
        
        db.delete(asset)
        db.commit()
        return True

