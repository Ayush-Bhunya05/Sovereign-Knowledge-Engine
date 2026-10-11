"""Integration test to verify ChromaService operations."""

import shutil
import tempfile
from pathlib import Path

from app.services.chroma_service import ChromaService


def test_chroma_lifecycle():
    temp_dir = tempfile.mkdtemp(prefix="test_chroma_")
    try:
        service = ChromaService(persist_dir=temp_dir)
        
        # 1. Health check on empty collection
        health = service.check_health()
        print("Initial Health:", health)
        assert health["status"] == "ok"
        assert health["entity_count"] == 0

        # 2. Insert vectors
        chunk_ids = ["chunk-1", "chunk-2", "chunk-3"]
        asset_id_1 = "asset-aaa"
        asset_id_2 = "asset-bbb"

        # 384-dimensional dummy vectors
        v1 = [1.0] + [0.0] * 383
        v2 = [0.9] + [0.1] * 383
        v3 = [0.0] + [1.0] * 383

        service.insert_vectors(
            chunk_ids=["chunk-1", "chunk-2"],
            asset_id=asset_id_1,
            vectors=[v1, v2],
        )
        service.insert_vectors(
            chunk_ids=["chunk-3"],
            asset_id=asset_id_2,
            vectors=[v3],
        )

        health = service.check_health()
        print("Health after insertion:", health)
        assert health["entity_count"] == 3

        # 3. Search vectors
        # Query close to v1
        query_v = [0.95] + [0.05] * 383
        results = service.search_vectors(query_vector=query_v, top_k=2)
        print("Search results:", results)
        assert len(results) == 2
        # chunk-1 or chunk-2 should be closest (lowest distance)
        assert results[0][0] in ["chunk-1", "chunk-2"]

        # 4. Delete vectors for asset-aaa
        service.delete_asset_vectors(asset_id=asset_id_1)
        health = service.check_health()
        print("Health after deleting asset-aaa:", health)
        assert health["entity_count"] == 1

        # 5. Recreate collection
        service.recreate_collection()
        health = service.check_health()
        print("Health after recreate_collection:", health)
        assert health["entity_count"] == 0

        print("\nALL CHROMASERVICE INTEGRATION TESTS PASSED SUCCESSFULLY!")

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    test_chroma_lifecycle()
