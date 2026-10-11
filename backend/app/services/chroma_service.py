"""ChromaDB service — handles embedded vector storage and retrieval.

Replaces Milvus with an in-process, persistent ChromaDB instance.
Runs cross-platform without Docker containers.
"""

import logging
from pathlib import Path
from typing import Any

import chromadb

logger = logging.getLogger(__name__)


class ChromaService:
    """Service to interact with ChromaDB for vector storage.

    Manages the persistent client, collection lifecycle, indexing,
    insertion, deletion, and semantic cosine search for document vectors.
    """

    VECTOR_DIM = 384
    COLLECTION_NAME = "document_vectors"

    def __init__(self, persist_dir: str = "chroma_db", **kwargs: Any) -> None:
        """Initialize persistent ChromaDB client.

        Args:
            persist_dir: Local directory path to persist vector index files.
            kwargs: Absorbs any extra arguments (like host/port) for drop-in compatibility.
        """
        self.persist_dir = Path(persist_dir).resolve()
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.client: chromadb.PersistentClient | None = None
        self.collection: Any = None
        self._init_collection()

    def _init_collection(self) -> None:
        """Create or load the persistent Chroma collection and cosine index."""
        try:
            logger.info("Initializing ChromaDB at %s...", self.persist_dir)
            self.client = chromadb.PersistentClient(path=str(self.persist_dir))
            
            # Use cosine distance space to match standard sentence embeddings
            self.collection = self.client.get_or_create_collection(
                name=self.COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "ChromaDB collection '%s' ready. Entity count: %d",
                self.COLLECTION_NAME,
                self.collection.count(),
            )
        except Exception as e:
            logger.error("Failed to initialize ChromaDB collection: %s", e)

    def _ensure_collection(self) -> None:
        """Ensure client and collection are initialized."""
        if self.client is None or self.collection is None:
            logger.info("ChromaDB not initialized, re-initializing...")
            self._init_collection()
            if self.collection is None:
                raise RuntimeError("Failed to initialize ChromaDB collection.")

    def recreate_collection(self) -> None:
        """Drop and recreate the entire Chroma collection."""
        try:
            self._ensure_collection()
            logger.info("Dropping existing ChromaDB collection: %s", self.COLLECTION_NAME)
            try:
                self.client.delete_collection(name=self.COLLECTION_NAME)
            except Exception as e:
                logger.warning("Could not delete collection %s (may not exist): %s", self.COLLECTION_NAME, e)
            self._init_collection()
        except Exception as e:
            logger.error("Failed to recreate ChromaDB collection: %s", e)

    def insert_vectors(
        self, chunk_ids: list[str], asset_id: str, vectors: list[list[float]]
    ) -> None:
        """Insert or upsert vectors into the collection.

        Args:
            chunk_ids: List of UUID strings (chunk IDs).
            asset_id: UUID string of parent asset.
            vectors: List of float vectors.
        """
        if not chunk_ids or not vectors:
            return

        if len(chunk_ids) != len(vectors):
            raise ValueError("Mismatched chunk_ids and vectors lengths.")

        self._ensure_collection()

        logger.info("Inserting %d vectors into ChromaDB for asset %s...", len(chunk_ids), asset_id)

        # Batch upsert to guard against large batch constraints
        batch_size = 500
        for i in range(0, len(chunk_ids), batch_size):
            batch_ids = [str(cid) for cid in chunk_ids[i : i + batch_size]]
            batch_vectors = vectors[i : i + batch_size]
            batch_metadatas = [{"asset_id": str(asset_id)} for _ in batch_ids]

            self.collection.upsert(
                ids=batch_ids,
                embeddings=batch_vectors,
                metadatas=batch_metadatas,
            )

        logger.info("Successfully inserted %d vectors into ChromaDB.", len(chunk_ids))

    def delete_asset_vectors(self, asset_id: str) -> None:
        """Delete all vectors associated with an asset ID."""
        try:
            self._ensure_collection()
            logger.info("Deleting vectors for asset %s from ChromaDB...", asset_id)
            self.collection.delete(where={"asset_id": str(asset_id)})
            logger.info("Deleted vectors for asset %s from ChromaDB.", asset_id)
        except Exception as e:
            logger.error("Failed to delete vectors for asset %s: %s", asset_id, e)

    def search_vectors(
        self, query_vector: list[float], top_k: int, metric_type: str = "COSINE"
    ) -> list[tuple[str, float]]:
        """Search the collection for similar vectors using cosine distance.

        Args:
            query_vector: A single float vector representing the query embedding.
            top_k: Number of closest matches to return.
            metric_type: Unused, kept for Milvus API compatibility.

        Returns:
            A list of tuples: (chunk_id, distance_score).
        """
        try:
            self._ensure_collection()
            total_count = self.collection.count()
            if total_count == 0 or top_k <= 0:
                return []

            n_results = min(top_k, total_count)
            results = self.collection.query(
                query_embeddings=[query_vector],
                n_results=n_results,
            )

            if not results or not results.get("ids") or not results["ids"][0]:
                return []

            matched_ids = results["ids"][0]
            distances = (
                results["distances"][0]
                if results.get("distances")
                else [0.0] * len(matched_ids)
            )

            matched_chunks = [(str(cid), float(dist)) for cid, dist in zip(matched_ids, distances)]
            logger.info(
                "ChromaDB search returned %d results for Top-K=%d",
                len(matched_chunks),
                top_k,
            )
            return matched_chunks

        except Exception as e:
            logger.error("ChromaDB search failed: %s", e)
            raise

    def check_health(self) -> dict[str, Any]:
        """Return the health status of ChromaDB."""
        try:
            self._ensure_collection()
            count = self.collection.count()
            return {
                "status": "ok",
                "provider": "chromadb",
                "collection": self.COLLECTION_NAME,
                "entity_count": count,
                "persist_dir": str(self.persist_dir),
            }
        except Exception as e:
            return {"status": "error", "provider": "chromadb", "error": str(e)}
