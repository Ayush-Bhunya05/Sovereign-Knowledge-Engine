"""Reset script for development environment."""

import os
import shutil
from pathlib import Path
from sqlalchemy import text
from app.database import engine
from app.services.milvus_service import MilvusService
from app.config import get_settings

def reset_dev():
    settings = get_settings()
    print("Starting development environment reset...")
    
    # 1. Clear PostgreSQL data
    print("Clearing PostgreSQL data...")
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE workspaces CASCADE;"))
    print("PostgreSQL tables truncated successfully.")

    # 2. Clear Uploads directory
    print("Clearing local uploads...")
    upload_dir = Path("uploads")
    if upload_dir.exists():
        for item in upload_dir.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
    print("Local uploads cleared.")

    # 3. Drop and recreate Milvus collection
    print("Resetting Milvus collection...")
    milvus = MilvusService(
        host=settings.milvus_host,
        port=settings.milvus_port,
    )
    # Recreate collection drops the existing one implicitly
    milvus.recreate_collection()
    print("Milvus collection reset successfully.")

    print("Development environment has been completely reset.")

if __name__ == "__main__":
    reset_dev()
