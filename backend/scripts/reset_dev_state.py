#!/usr/bin/env python
"""
reset_dev_state.py

Destructive script for developers to cleanly reset the entire development state
for the AI-Document-RAG backend.

Actions:
1. Drops the Postgres public schema and recreates it.
2. Runs Alembic upgrade head to recreate all tables.
3. Flushes the Milvus collection.
4. Clears the local uploads directory.
5. Sets up the rag_readonly PostgreSQL role for secure SQL execution.
6. Creates a "Default Workspace".

WARNING: DO NOT RUN THIS IN PRODUCTION. IT DELETES ALL DATA.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

# Add backend directory to sys.path so we can import app modules
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from sqlalchemy import text
from app.database import engine, SessionLocal
from app.config import get_settings
from app.services.milvus_service import MilvusService
from app.services.workspace_service import WorkspaceService
from app.schemas.workspace import WorkspaceCreate

def reset_postgres():
    print("Dropping and recreating PostgreSQL public schema...")
    with engine.connect() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE;"))
        conn.execute(text("CREATE SCHEMA public;"))
        conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
        
        # Setup the read-only role for RAG
        print("Setting up rag_readonly role...")
        try:
            # We use a DO block to only create the role if it doesn't exist
            conn.execute(text("""
                DO $$
                BEGIN
                  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'rag_readonly') THEN
                    CREATE ROLE rag_readonly WITH LOGIN PASSWORD 'rag_readonly';
                  END IF;
                END
                $$;
            """))
        except Exception as e:
            print(f"Error creating role: {e}")
        
        # Grant schema usage
        conn.execute(text("GRANT USAGE ON SCHEMA public TO rag_readonly;"))
        
        # Explicitly revoke any default CREATE privileges
        conn.execute(text("REVOKE CREATE ON SCHEMA public FROM rag_readonly;"))
        conn.commit()

def run_alembic():
    print("Running alembic upgrade head...")
    result = subprocess.run(
        ["../.venv/bin/alembic", "upgrade", "head"],
        cwd=backend_dir,
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print("Alembic failed:")
        print(result.stdout)
        print(result.stderr)
        sys.exit(1)
    print("Alembic upgrade successful.")

def reset_milvus():
    print("Resetting Milvus collection...")
    settings = get_settings()
    # If milvus isn't running, this will log an error but won't crash if we catch it
    try:
        milvus = MilvusService(host=settings.milvus_host, port=settings.milvus_port)
        milvus.recreate_collection()
        print("Milvus reset successful.")
    except Exception as e:
        print(f"Failed to reset Milvus: {e}")

def reset_uploads():
    print("Resetting uploads directory...")
    settings = get_settings()
    upload_path = backend_dir / settings.upload_dir
    if upload_path.exists():
        shutil.rmtree(upload_path)
    upload_path.mkdir(parents=True, exist_ok=True)
    print("Uploads directory cleared.")

def create_default_workspace():
    print("Creating Default Workspace...")
    db = SessionLocal()
    try:
        ws_service = WorkspaceService()
        # Check if one already exists (it shouldn't, we just dropped the DB)
        ws_list = ws_service.list_all(db)
        if not ws_list:
            ws_service.create(
                db,
                WorkspaceCreate(
                    name="Default Workspace",
                    description="Automatically created by dev reset."
                )
            )
            print("Default Workspace created.")
    except Exception as e:
        print(f"Error creating Default Workspace: {e}")
    finally:
        db.close()

def main():
    print("=== AI-Document-RAG Dev State Reset ===")
    reset_postgres()
    run_alembic()
    reset_milvus()
    reset_uploads()
    create_default_workspace()
    print("=== Reset Complete! ===")

if __name__ == "__main__":
    main()
