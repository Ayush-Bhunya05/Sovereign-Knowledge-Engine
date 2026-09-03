"""Ingestion orchestrator — Coordinates the entire document ingestion lifecycle."""

import logging
import uuid
from typing import Sequence

from sqlalchemy.orm import Session

from app.models.asset import Asset
from app.models.asset_chunk import AssetChunk
from app.services.ingestion.extraction_service import ExtractionService
from app.services.ingestion.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService
from app.services.milvus_service import MilvusService
from app.services.storage_service import LocalStorageService
from app.services.ingestion.structured_data_service import StructuredDataService
from pathlib import Path

logger = logging.getLogger(__name__)

class IngestionOrchestrator:
    """Coordinates the ingestion pipeline: extract -> chunk -> embed -> index."""

    def __init__(
        self,
        extraction_service: ExtractionService,
        chunking_service: ChunkingService,
        embedding_service: EmbeddingService,
        milvus_service: MilvusService,
        storage_service: LocalStorageService,
        structured_data_service: StructuredDataService = None,
    ):
        self.extraction = extraction_service
        self.chunking = chunking_service
        self.embedding = embedding_service
        self.milvus = milvus_service
        self.storage = storage_service
        self.structured_data = structured_data_service

    def process_asset(self, db: Session, asset_id: uuid.UUID) -> None:
        """Run the ingestion pipeline for a given asset ID."""
        
        asset = db.query(Asset).filter(Asset.id == asset_id).first()
        if not asset:
            logger.error("Asset %s not found for ingestion.", asset_id)
            return

        logger.info("Starting ingestion for asset %s (%s)", asset_id, asset.filename)

        try:
            # 1. Mark as EXTRACTING
            asset.processing_status = "extracting"
            db.commit()

            file_path = asset.storage_path
            ext = Path(file_path).suffix.lower()

            # Route based on structured vs unstructured
            if ext in [".csv", ".xlsx"]:
                if not self.structured_data:
                    raise RuntimeError("StructuredDataService not initialized.")
                logger.info("Routing asset %s to StructuredDataService...", asset_id)
                self.structured_data.process_structured_asset(db, asset_id)
                return

            # 2. Extract (Unstructured)
            logger.info("Extracting text for asset %s...", asset_id)
            ext_result = self.extraction.extract(file_path, asset.document_type)

            asset.extracted_text = ext_result.markdown
            asset.page_count = ext_result.page_count
            asset.language = ext_result.language
            asset.parser_metadata = ext_result.parser_metadata
            asset.extraction_metadata = ext_result.extraction_metadata

            if not ext_result.markdown or not ext_result.markdown.strip():
                logger.warning("Empty text extracted for asset %s.", asset_id)
                asset.processing_status = "completed"
                asset.chunk_count = 0
                db.commit()
                return

            # 3. Chunk
            asset.processing_status = "chunking"
            db.commit()
            
            logger.info("Chunking text for asset %s...", asset_id)
            chunk_data_list = self.chunking.chunk_markdown(
                markdown=ext_result.markdown,
                workspace_id=asset.workspace_id,
                folder_id=asset.folder_id,
                asset_id=asset.id,
                page_count=ext_result.page_count
            )
            
            asset.chunk_count = len(chunk_data_list)
            if not chunk_data_list:
                asset.processing_status = "completed"
                db.commit()
                return

            # 4. Embed
            asset.processing_status = "embedding"
            db.commit()
            
            logger.info("Embedding %d chunks for asset %s...", len(chunk_data_list), asset_id)
            texts_to_embed = [c.chunk_text for c in chunk_data_list]
            emb_result = self.embedding.embed_texts(texts_to_embed)

            # 5. Persist to DB (PostgreSQL)
            logger.info("Saving chunks to database for asset %s...", asset_id)
            db_chunks = []
            chunk_ids = []
            for i, chunk_data in enumerate(chunk_data_list):
                chunk_id = uuid.uuid4()
                chunk_ids.append(str(chunk_id))
                db_chunks.append(
                    AssetChunk(
                        id=chunk_id,
                        asset_id=chunk_data.asset_id,
                        workspace_id=chunk_data.workspace_id,
                        folder_id=chunk_data.folder_id,
                        chunk_index=chunk_data.chunk_index,
                        page_number=chunk_data.page_number,
                        chunk_text=chunk_data.chunk_text,
                        character_count=chunk_data.character_count,
                        content_hash=chunk_data.content_hash,
                        heading_context=chunk_data.heading_context,
                        section_context=chunk_data.section_context,
                        embedding_model=emb_result.embedding_model,
                        embedding_model_version=emb_result.embedding_model_version,
                        embedding_dimension=emb_result.embedding_dimension,
                    )
                )

            # Delete existing chunks if this is a re-run
            db.query(AssetChunk).filter(AssetChunk.asset_id == asset_id).delete()
            db.bulk_save_objects(db_chunks)
            db.commit()

            # 6. Persist to Milvus
            asset.processing_status = "indexing"
            db.commit()
            
            logger.info("Indexing vectors to Milvus for asset %s...", asset_id)
            self.milvus.delete_asset_vectors(str(asset_id))
            self.milvus.insert_vectors(
                chunk_ids=chunk_ids,
                asset_id=str(asset_id),
                vectors=emb_result.vectors
            )

            # 7. Mark as COMPLETED
            asset.processing_status = "completed"
            db.commit()
            logger.info("Ingestion completed successfully for asset %s.", asset_id)

        except Exception as e:
            logger.exception("Ingestion failed for asset %s: %s", asset_id, e)
            db.rollback()
            asset = db.query(Asset).filter(Asset.id == asset_id).first()
            if asset:
                asset.processing_status = "failed"
                db.commit()
