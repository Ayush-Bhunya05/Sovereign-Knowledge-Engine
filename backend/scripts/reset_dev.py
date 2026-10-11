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

    # 3. Drop and recreate Vector collection
    print("Resetting Vector collection...")
    try:
        from app.dependencies import get_vector_service
        vector_service = get_vector_service()
        vector_service.recreate_collection()
        print(f"Vector collection reset successfully ({type(vector_service).__name__}).")
    except Exception as e:
        print(f"Failed to reset Vector DB: {e}")

    print("Development environment has been completely reset.")

if __name__ == "__main__":
    reset_dev()
