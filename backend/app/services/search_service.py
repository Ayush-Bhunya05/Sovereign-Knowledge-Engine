"""Search service."""

import logging
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.asset_chunk import AssetChunk
from app.models.asset import Asset
from app.models.dataset import Dataset
from app.services.embedding_service import EmbeddingService
from app.services.milvus_service import MilvusService

logger = logging.getLogger(__name__)


class SearchService:
    """Service to handle semantic search queries."""

    def __init__(self, milvus_service: MilvusService, embedding_service: EmbeddingService):
        self.milvus = milvus_service
        self.embedding = embedding_service

    def search_documents(
        self,
        db: Session,
        workspace_id: uuid.UUID,
        query: str,
        folder_id: uuid.UUID | None = None,
        asset_id: uuid.UUID | None = None,
        top_k: int = 10,
    ) -> list[dict[str, Any]]:
        """Perform semantic search across indexed document chunks.
        
        Scope filters:
        - workspace_id is ALWAYS applied.
        - folder_id (optional): limit to a specific folder.
        - asset_id (optional): limit to a specific asset.
        """
        if not query.strip():
            return []

        # 1. Embed the query
        logger.info("Embedding search query: '%s'", query)
        query_vector = self.embedding.embed_query(query)

        # 2. Search Milvus (which returns top matching chunk_ids and scores)
        # Note: We over-fetch from Milvus to apply Postgres filtering later if needed.
        # Alternatively, we could filter natively in Milvus, but our Milvus schema 
        # currently only has chunk_id and asset_id. For now, we fetch more and filter in DB.
        fetch_k = top_k * 5 if (folder_id or asset_id) else top_k
        milvus_results = self.milvus.search_vectors(query_vector=query_vector, top_k=fetch_k)

        if not milvus_results:
            return []

        # milvus_results is [(chunk_id_str, distance_float), ...]
        chunk_scores = {chunk_id: score for chunk_id, score in milvus_results}
        chunk_ids = [uuid.UUID(c_id) for c_id in chunk_scores.keys()]

        # 3. Fetch from Postgres and apply filters
        db_query = db.query(AssetChunk, Asset).join(
            Asset, AssetChunk.asset_id == Asset.id
        ).filter(
            AssetChunk.id.in_(chunk_ids),
            AssetChunk.workspace_id == workspace_id
        )

        if folder_id:
            db_query = db_query.filter(AssetChunk.folder_id == folder_id)
        if asset_id:
            db_query = db_query.filter(AssetChunk.asset_id == asset_id)

        rows = db_query.all()

        # 4. Format results
        results = []
        for chunk, asset in rows:
            # Re-map the score
            score = chunk_scores[str(chunk.id)]
            
            # Since metric is COSINE distance (0 is identical, 2 is opposite),
            # we can convert it to a similarity percentage roughly for UI.
            # similarity = 1 - (distance / 2)
            # but Milvus COSINE often returns cosine similarity directly or 1 - cosine similarity.
            # Assuming 0 is perfect match, lower is better.
            
            results.append({
                "chunk_id": chunk.id,
                "asset_id": chunk.asset_id,
                "filename": asset.filename,
                "document_type": asset.document_type,
                "page_number": chunk.page_number,
                "chunk_index": chunk.chunk_index,
                "chunk_text": chunk.chunk_text,
                "similarity_score": score,
            })

        # Sort by best score (assuming lower distance is better)
        results.sort(key=lambda x: x["similarity_score"])
        
        return results[:top_k]

    def discover_datasets(
        self,
        db: Session,
        workspace_id: uuid.UUID,
        query: str,
        folder_id: uuid.UUID | None = None,
        asset_id: uuid.UUID | None = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """Perform deterministic + semantic search for structured datasets.
        
        Applies ScopeContext BEFORE discovery to prevent global-then-filter.
        """
        # 1. Fetch allowed Dataset IDs from Postgres (Scope Enforcement)
        dataset_query = db.query(Dataset, Asset).join(Asset, Dataset.asset_id == Asset.id).filter(Dataset.workspace_id == workspace_id)
        if folder_id:
            dataset_query = dataset_query.filter(Dataset.folder_id == folder_id)
        if asset_id:
            dataset_query = dataset_query.filter(Dataset.asset_id == asset_id)
            
        allowed_datasets = dataset_query.all()
        if not allowed_datasets:
            return []
            
        allowed_dataset_ids = {ds.id: (ds, asset) for ds, asset in allowed_datasets}

        if not query.strip():
            # If no query, just return the allowed datasets
            return [
                {
                    "dataset_id": ds.id,
                    "asset_id": ds.asset_id,
                    "filename": asset.filename,
                    "table_name": ds.table_name,
                    "schema_definition": ds.schema_definition,
                    "similarity_score": 0.0,
                }
                for ds, asset in allowed_datasets[:top_k]
            ]

        # 2. Embed the query for semantic matching
        logger.info("Embedding dataset discovery query: '%s'", query)
        query_vector = self.embedding.embed_query(query)

        # 3. Search Milvus (only fetch enough to find matches, or we could pass expression)
        # We still have to search Milvus and then intersect with allowed_dataset_ids
        fetch_k = top_k * 5 if (folder_id or asset_id) else top_k
        milvus_results = self.milvus.search_vectors(query_vector=query_vector, top_k=fetch_k)
        
        chunk_scores = {}
        if milvus_results:
            chunk_scores = {uuid.UUID(chunk_id_str): score for chunk_id_str, score in milvus_results}

        datasets = []
        for ds_id, (ds, asset) in allowed_dataset_ids.items():
            # Hybrid scoring: 
            # Check for exact keyword match in table name or schema
            query_lower = query.lower()
            keyword_bonus = 0.0
            if query_lower in ds.table_name.lower():
                keyword_bonus = 0.3
            if ds.schema_definition and query_lower in str(ds.schema_definition).lower():
                keyword_bonus = 0.2
                
            # Semantic score from Milvus
            semantic_score = chunk_scores.get(ds_id, 1.0) # 1.0 is bad in cosine distance
            
            # Combine score (lower is better, so we subtract bonus)
            final_score = semantic_score - keyword_bonus
            
            datasets.append({
                "dataset_id": ds.id,
                "asset_id": ds.asset_id,
                "filename": asset.filename,
                "table_name": ds.table_name,
                "schema_definition": ds.schema_definition,
                "similarity_score": final_score,
            })
            
        datasets.sort(key=lambda x: x["similarity_score"])
        return datasets[:top_k]


