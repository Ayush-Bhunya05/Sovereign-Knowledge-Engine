"""Milvus service — handles vector storage and retrieval.

Uses `pymilvus` directly to interact with the Milvus vector database.
"""

import logging
from typing import Any

from pymilvus import (
    Collection,
    CollectionSchema,
    DataType,
    FieldSchema,
    MilvusClient,
    connections,
    utility,
)

logger = logging.getLogger(__name__)


class MilvusService:
    """Service to interact with Milvus for vector storage.

    Manages the connection, collection creation, indexing, insertion,
    and deletion of document vectors.
    """

    # We use a 384-dimension vector for BAAI/bge-small-en-v1.5
    VECTOR_DIM = 384
    COLLECTION_NAME = "document_vectors"
    INDEX_NAME = "vector_index"
    
    def __init__(self, host: str, port: int) -> None:
        self.host = host
        self.port = port
        self.alias = "default"
        self._connect()
        self._init_collection()

    def _connect(self) -> None:
        """Connect to the Milvus server."""
        try:
            logger.info("Connecting to Milvus at %s:%d", self.host, self.port)
            connections.connect(
                alias=self.alias,
                host=self.host,
                port=self.port,
            )
            logger.info("Connected to Milvus successfully.")
        except Exception as e:
            logger.error("Failed to connect to Milvus: %s", e)
            # We don't raise here so the app can still start if Milvus is down.
            # Operations will fail later when attempting to use the connection.

    def _init_collection(self) -> None:
        """Create the collection and index if they do not exist."""
        try:
            # Check if collection exists
            if utility.has_collection(self.COLLECTION_NAME, using=self.alias):
                self.collection = Collection(self.COLLECTION_NAME, using=self.alias)
                logger.info("Loaded existing Milvus collection: %s", self.COLLECTION_NAME)
            else:
                # Create schema
                fields = [
                    FieldSchema(
                        name="chunk_id",
                        dtype=DataType.VARCHAR,
                        max_length=36,
                        is_primary=True,
                        description="UUID of the chunk (matches PostgreSQL)",
                    ),
                    FieldSchema(
                        name="asset_id",
                        dtype=DataType.VARCHAR,
                        max_length=36,
                        description="UUID of the parent asset",
                    ),
                    FieldSchema(
                        name="vector",
                        dtype=DataType.FLOAT_VECTOR,
                        dim=self.VECTOR_DIM,
                        description="Semantic embedding of the chunk",
                    ),
                ]
                schema = CollectionSchema(
                    fields,
                    description="Document chunk vectors for semantic search",
                )
                
                self.collection = Collection(
                    name=self.COLLECTION_NAME,
                    schema=schema,
                    using=self.alias,
                )
                logger.info("Created new Milvus collection: %s", self.COLLECTION_NAME)

            # Create index if needed
            index_params = {
                "metric_type": "COSINE",
                "index_type": "HNSW",
                "params": {"M": 8, "efConstruction": 64},
            }
            if not self.collection.has_index():
                logger.info("Creating index for collection...")
                self.collection.create_index(
                    field_name="vector",
                    index_params=index_params,
                    index_name=self.INDEX_NAME,
                )
                logger.info("Index created successfully.")
            
            # Load collection into memory
            self.collection.load()
            logger.info("Collection %s loaded into memory.", self.COLLECTION_NAME)

        except Exception as e:
            logger.error("Failed to initialize Milvus collection: %s", e)

    def recreate_collection(self) -> None:
        """Drop and recreate the entire Milvus collection."""
        try:
            if utility.has_collection(self.COLLECTION_NAME, using=self.alias):
                utility.drop_collection(self.COLLECTION_NAME, using=self.alias)
                logger.info("Dropped existing Milvus collection: %s", self.COLLECTION_NAME)
            self._init_collection()
        except Exception as e:
            logger.error("Failed to recreate Milvus collection: %s", e)

    def _ensure_collection(self):
        if not hasattr(self, 'collection'):
            logger.info("Collection not initialized, attempting to re-initialize...")
            self._connect()
            self._init_collection()
            if not hasattr(self, 'collection'):
                raise RuntimeError("Failed to initialize Milvus collection.")

    def insert_vectors(self, chunk_ids: list[str], asset_id: str, vectors: list[list[float]]) -> None:
        """Insert vectors into the collection.
        
        Args:
            chunk_ids: List of UUID strings (chunk IDs).
            asset_id: UUID string of the parent asset.
            vectors: List of float vectors.
        """
        if not chunk_ids or not vectors:
            return

        if len(chunk_ids) != len(vectors):
            raise ValueError("Mismatched chunk_ids and vectors lengths.")

        self._ensure_collection()

        # Milvus requires columnar data insertion format
        data = [
            chunk_ids,
            [asset_id] * len(chunk_ids),
            vectors,
        ]

        logger.info("Inserting %d vectors into Milvus...", len(chunk_ids))
        self.collection.insert(data)
        # Flush is required in older Milvus versions to make data immediately searchable.
        # It's optional in newer versions, but safe to call.
        self.collection.flush()
        logger.info("Successfully inserted %d vectors.", len(chunk_ids))

    def delete_asset_vectors(self, asset_id: str) -> None:
        """Delete all vectors associated with an asset ID."""
        expr = f"asset_id == '{asset_id}'"
        try:
            self._ensure_collection()
            logger.info("Deleting vectors for asset %s...", asset_id)
            self.collection.delete(expr)
            self.collection.flush()
            logger.info("Deleted vectors for asset %s.", asset_id)
        except Exception as e:
            logger.error("Failed to delete vectors for asset %s: %s", asset_id, e)

    def check_health(self) -> dict[str, Any]:
        """Return the health status of the Milvus connection."""
        try:
            if utility.has_collection(self.COLLECTION_NAME, using=self.alias):
                count = self.collection.num_entities
                return {"status": "ok", "collection": self.COLLECTION_NAME, "entity_count": count}
            return {"status": "error", "error": "Collection not found"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def search_vectors(
        self, query_vector: list[float], top_k: int, metric_type: str = "COSINE"
    ) -> list[tuple[str, float]]:
        """Search the Milvus collection for similar vectors.

        Args:
            query_vector: A single float vector representing the query embedding.
            top_k: The number of closest matches to return.
            metric_type: Similarity metric to use.

        Returns:
            A list of tuples, each containing (chunk_id, similarity_score).
        """
        # HNSW search parameters; 'ef' determines search precision vs speed.
        search_params = {
            "metric_type": metric_type,
            "params": {"ef": 64},
        }

        try:
            # We search for 1 query vector at a time, hence `data=[query_vector]`
            results = self.collection.search(
                data=[query_vector],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                expr=None,
                output_fields=[],  # primary key is always returned
            )

            # Results is a list of Hits. Since we only passed 1 query vector, we want results[0]
            if not results:
                return []

            hits = results[0]
            
            # Extract id (which is our chunk_id) and distance/score
            matched_chunks = [(str(hit.id), float(hit.distance)) for hit in hits]
            
            logger.info(
                "Milvus search returned %d results for Top-K=%d", len(matched_chunks), top_k
            )
            return matched_chunks

        except Exception as e:
            logger.error("Milvus search failed: %s", e)
            raise
