import sys
import shutil
from pathlib import Path

from app.database import SessionLocal, engine
from app.models.workspace import Workspace
from app.services.milvus_service import MilvusService
from app.config import get_settings

def flush_all():
    settings = get_settings()
    
    print("1. Flushing PostgreSQL database...")
    db = SessionLocal()
    try:
        # Get all workspaces and delete them (cascade handles the rest)
        workspaces = db.query(Workspace).all()
        print(f"Found {len(workspaces)} workspaces. Deleting...")
        for ws in workspaces:
            db.delete(ws)
        
        # If there are any orphaned assets, they might be left behind if workspace was deleted directly 
        # without cascade (though cascade is ON). Just to be sure, let's delete them.
        from app.models.asset import Asset
        from app.models.folder import Folder
        from app.models.asset_chunk import AssetChunk
        from app.models.dataset import Dataset
        
        db.query(Dataset).delete()
        db.query(AssetChunk).delete()
        db.query(Asset).delete()
        db.query(Folder).delete()
        db.query(Workspace).delete()
        
        db.commit()
        print("PostgreSQL tables cleared.")
    except Exception as e:
        db.rollback()
        print(f"Error clearing PostgreSQL: {e}")
    finally:
        db.close()

    print("2. Flushing Milvus database...")
    try:
        milvus = MilvusService(host=settings.milvus_host, port=settings.milvus_port)
        milvus.recreate_collection()
        print("Milvus collection recreated and flushed.")
    except Exception as e:
        print(f"Error flushing Milvus: {e}")
        
    print("3. Flushing local uploads directory...")
    try:
        uploads_dir = Path(settings.upload_dir)
        if uploads_dir.exists():
            for item in uploads_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            print(f"Cleared {uploads_dir}")
        else:
            print(f"{uploads_dir} does not exist.")
    except Exception as e:
        print(f"Error clearing uploads: {e}")
        
    print("Flush complete.")

if __name__ == "__main__":
    flush_all()
