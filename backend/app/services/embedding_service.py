"""Embedding service — generates vector embeddings from text chunks.

Uses `sentence-transformers` for fast, local embedding generation.
The model is loaded once at startup to avoid high initialization costs
on each request.
"""

import logging
from typing import Any

from sentence_transformers import SentenceTransformer

from app.schemas.ingestion.schemas import EmbeddingResult

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generates text embeddings using a local SentenceTransformer model.

    This service holds the loaded model in memory. It should be instantiated
    once during application startup and reused.
    """

    def __init__(self, model_name: str) -> None:
        self.model_name = model_name
        self.model: SentenceTransformer | None = None
        self._load_model()

    def _load_model(self) -> None:
        """Load the embedding model into memory."""
        logger.info("Loading embedding model: %s", self.model_name)
        try:
            self.model = SentenceTransformer(self.model_name)
            logger.info("Embedding model loaded successfully.")
        except Exception as e:
            logger.error("Failed to load embedding model %s: %s", self.model_name, e)
            raise

    def embed_texts(self, texts: list[str]) -> EmbeddingResult:
        """Generate embeddings for a list of text strings.

        Args:
            texts: List of strings to embed.

        Returns:
            EmbeddingResult containing vectors and metadata.
        """
        from app.schemas.ingestion.schemas import EmbeddingResult

        if not texts:
            return EmbeddingResult(
                vectors=[],
                embedding_model=self.model_name,
                embedding_model_version="1.0",
                embedding_dimension=self.model.get_sentence_embedding_dimension() if self.model else 0
            )

        if self.model is None:
            raise RuntimeError("Embedding model is not loaded.")

        logger.info("Generating embeddings for %d texts...", len(texts))
        
        # We explicitly cast the output to lists of floats for pymilvus
        embeddings = self.model.encode(texts, show_progress_bar=False)
        vectors = [emb.tolist() for emb in embeddings]

        return EmbeddingResult(
            vectors=vectors,
            embedding_model=self.model_name,
            embedding_model_version="1.0",
            embedding_dimension=self.model.get_sentence_embedding_dimension()
        )

    def embed_query(self, query: str) -> list[float]:
        """Generate an embedding for a single search query.

        Applies the BGE-specific instruction prefix for optimal retrieval.
        """
        if self.model is None:
            raise RuntimeError("Embedding model is not loaded.")

        # BGE models require a specific instruction for queries in asymmetric retrieval
        prefix = "Represent this sentence for searching relevant passages: "
        formatted_query = f"{prefix}{query}"

        logger.info("Generating embedding for query...")
        embedding = self.model.encode(formatted_query, show_progress_bar=False)
        return embedding.tolist()

    def check_health(self) -> dict[str, Any]:
        """Return the health status of the embedding model."""
        if self.model is not None:
            return {"status": "ok", "model": self.model_name}
        return {"status": "error", "error": "Model not loaded"}
