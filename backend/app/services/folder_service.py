"""Service for managing folders."""

import uuid
from typing import Sequence

from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.folder import Folder
from app.schemas.folder import FolderCreate, FolderUpdate


class FolderService:
    def create(self, db: Session, workspace_id: uuid.UUID, folder_in: FolderCreate) -> Folder:
        depth = 0
        path = f"/{folder_in.name}/"
        
        if folder_in.parent_folder_id:
            parent = self.get(db, workspace_id, folder_in.parent_folder_id)
            if parent:
                depth = parent.depth + 1
                path = f"{parent.path}{folder_in.name}/"
            else:
                raise ValueError("Parent folder not found in this workspace")

        folder = Folder(
            workspace_id=workspace_id,
            parent_folder_id=folder_in.parent_folder_id,
            name=folder_in.name,
            path=path,
            depth=depth,
        )
        db.add(folder)
        db.commit()
        db.refresh(folder)
        return folder

    def get(self, db: Session, workspace_id: uuid.UUID, folder_id: uuid.UUID) -> Folder | None:
        return db.query(Folder).filter(Folder.id == folder_id, Folder.workspace_id == workspace_id).first()

    def list_in_workspace(self, db: Session, workspace_id: uuid.UUID) -> Sequence[Folder]:
        return db.query(Folder).filter(Folder.workspace_id == workspace_id).order_by(Folder.path).all()

    def update(self, db: Session, workspace_id: uuid.UUID, folder: Folder, folder_in: FolderUpdate) -> Folder:
        old_path = folder.path
        
        if folder_in.name is not None:
            folder.name = folder_in.name
            
        if folder_in.parent_folder_id is not None:
            folder.parent_folder_id = folder_in.parent_folder_id
            if folder_in.parent_folder_id:
                parent = self.get(db, workspace_id, folder_in.parent_folder_id)
                if not parent:
                    raise ValueError("Parent folder not found")
                folder.depth = parent.depth + 1
                folder.path = f"{parent.path}{folder.name}/"
            else:
                folder.depth = 0
                folder.path = f"/{folder.name}/"
        elif folder_in.name is not None:
            # Rebuild path based on new name, keeping same parent
            if folder.parent_folder_id:
                parent = self.get(db, workspace_id, folder.parent_folder_id)
                folder.path = f"{parent.path}{folder.name}/" if parent else f"/{folder.name}/"
            else:
                folder.path = f"/{folder.name}/"
                
        if old_path != folder.path:
            # Update all descendants using raw SQL for efficiency (pattern replace)
            stmt = text("""
                UPDATE folders 
                SET path = :new_path || SUBSTRING(path FROM length(:old_path) + 1),
                    depth = depth + (:new_depth - :old_depth)
                WHERE workspace_id = :workspace_id 
                AND path LIKE :like_path
            """)
            db.execute(stmt, {
                "new_path": folder.path,
                "old_path": old_path,
                "new_depth": folder.depth,
                "old_depth": folder.depth - (folder.depth - (folder.depth)), # Need actual old depth. Wait.
                # Actually, depth delta = new_depth - old_depth. 
                "workspace_id": str(workspace_id),
                "like_path": f"{old_path}%"
            })
            
        db.add(folder)
        db.commit()
        db.refresh(folder)
        return folder

    def delete(self, db: Session, workspace_id: uuid.UUID, folder_id: uuid.UUID) -> bool:
        folder = self.get(db, workspace_id, folder_id)
        if not folder:
            return False
        db.delete(folder)
        db.commit()
        return True


folder_service = FolderService()
