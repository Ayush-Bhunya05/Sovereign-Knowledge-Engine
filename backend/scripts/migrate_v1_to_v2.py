"""Script to migrate existing documents and chunks into the v2 assets and workspaces."""

import hashlib
import sys
import uuid
from sqlalchemy.orm import Session

# Ensure we can import app modules
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import SessionLocal, engine
from app.models.workspace import Workspace
from app.models.folder import Folder
from app.models.asset import Asset
from app.models.asset_chunk import AssetChunk
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.base import Base

def get_content_hash(text: str) -> str:
    """Helper to compute deterministic chunk hashes."""
    return hashlib.sha256(text.encode('utf-8')).hexdigest()

def migrate_data():
    """Migrate documents -> assets, document_chunks -> asset_chunks in a Default workspace."""
    
    db: Session = SessionLocal()
    try:
        # Create Default Workspace if not exists
        default_workspace = db.query(Workspace).filter(Workspace.name == "Default Workspace").first()
        if not default_workspace:
            default_workspace = Workspace(
                name="Default Workspace",
                description="Auto-generated workspace from v1 migration.",
                settings={}
            )
            db.add(default_workspace)
            db.commit()
            db.refresh(default_workspace)
            print(f"Created Default Workspace: {default_workspace.id}")
        else:
            print(f"Found Default Workspace: {default_workspace.id}")

        # Migrate Documents
        documents = db.query(Document).all()
        print(f"Found {len(documents)} legacy documents to migrate.")
        
        migrated_asset_ids = set()

        for doc in documents:
            # Check if already migrated
            existing_asset = db.query(Asset).filter(Asset.id == doc.id).first()
            if existing_asset:
                migrated_asset_ids.add(doc.id)
                continue
                
            # Create Asset
            asset = Asset(
                id=doc.id,
                workspace_id=default_workspace.id,
                folder_id=None,
                version_group_id=uuid.uuid4(),
                version_number=1,
                previous_version_id=None,
                is_latest=True,
                filename=doc.filename,
                asset_type="document",
                document_type=doc.document_type,
                mime_type=doc.mime_type,
                file_size=doc.file_size,
                processing_status=doc.processing_status,
                storage_path=doc.storage_path,
                page_count=doc.page_count,
                has_ocr=doc.has_ocr,
                chunk_count=doc.chunk_count,
                extracted_text=doc.extracted_text,
                language=doc.language,
                parser_metadata={"parser_name": "unknown_v1_legacy"},
                extraction_metadata=doc.extraction_metadata,
                created_at=doc.created_at,
                updated_at=doc.updated_at
            )
            db.add(asset)
            migrated_asset_ids.add(doc.id)
        
        db.commit()
        print("Migrated Documents to Assets.")

        # Migrate Chunks
        chunks_migrated = 0
        all_chunks = db.query(DocumentChunk).all()
        print(f"Found {len(all_chunks)} legacy chunks to migrate.")
        
        # Batch inserting chunks for performance
        asset_chunks_to_insert = []
        for chunk in all_chunks:
            if chunk.document_id not in migrated_asset_ids:
                print(f"Warning: Chunk {chunk.id} references missing document {chunk.document_id}")
                continue
                
            existing_asset_chunk = db.query(AssetChunk).filter(AssetChunk.id == chunk.id).first()
            if existing_asset_chunk:
                continue
                
            asset_chunk = AssetChunk(
                id=chunk.id,
                asset_id=chunk.document_id,
                workspace_id=default_workspace.id,
                folder_id=None,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                chunk_text=chunk.chunk_text,
                character_count=chunk.character_count,
                content_hash=get_content_hash(chunk.chunk_text),
                heading_context=None,
                section_context=None,
                chunk_metadata=None,
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_model_version="unknown_v1",
                embedding_dimension=384,
                created_at=chunk.created_at
            )
            asset_chunks_to_insert.append(asset_chunk)
            
            if len(asset_chunks_to_insert) >= 500:
                db.bulk_save_objects(asset_chunks_to_insert)
                db.commit()
                chunks_migrated += len(asset_chunks_to_insert)
                asset_chunks_to_insert.clear()
        
        if asset_chunks_to_insert:
            db.bulk_save_objects(asset_chunks_to_insert)
            db.commit()
            chunks_migrated += len(asset_chunks_to_insert)

        print(f"Successfully migrated {chunks_migrated} DocumentChunks to AssetChunks.")
        print("Migration complete. (Old tables have not been dropped to ensure safe rollback)")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate_data()
