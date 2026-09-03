"""Test script for Milestone 2: Modular Ingestion Pipeline."""

import time
import requests
import uuid
import os

API_URL = "http://localhost:8000/api/v2"

def wait_for_asset(workspace_id: str, asset_id: str, timeout: int = 60) -> dict:
    """Poll the API until the asset processing status is not 'pending' or 'processing'."""
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{API_URL}/workspaces/{workspace_id}/assets/{asset_id}")
        assert resp.status_code == 200, f"Failed to get asset: {resp.text}"
        asset = resp.json()
        if asset["processing_status"] in ("completed", "failed"):
            return asset
        time.sleep(2)
    raise TimeoutError(f"Asset {asset_id} did not finish processing in {timeout} seconds.")

def upload_file(workspace_id: str, filepath: str) -> dict:
    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f)}
        resp = requests.post(f"{API_URL}/workspaces/{workspace_id}/assets/upload", files=files)
        assert resp.status_code == 201, f"Failed to upload {filepath}: {resp.text}"
        return resp.json()

def main():
    print("=== Setting up Workspace ===")
    resp = requests.post(f"{API_URL}/workspaces", json={"name": "Test M2", "description": "M2 tests"})
    assert resp.status_code == 201
    ws = resp.json()
    ws_id = ws["id"]
    print(f"Created Workspace: {ws_id}")

    try:
        # Create test files
        with open("test.txt", "w") as f:
            f.write("# Hello\n\nThis is a simple text file.")
        
        with open("empty.txt", "w") as f:
            pass

        with open("large.txt", "w") as f:
            for i in range(1000):
                f.write(f"This is line {i} of the large text file, ensuring it takes some time and chunks.\n")
                
        with open("multilingual.txt", "w") as f:
            f.write("Hello world.\nBonjour le monde.\nHola mundo.\nこんにちは世界.")

        print("\n=== Testing Simple Text ===")
        asset_info = upload_file(ws_id, "test.txt")
        asset = wait_for_asset(ws_id, asset_info["id"])
        print(f"Simple Text -> Status: {asset['processing_status']} | Chunks: {asset['chunk_count']}")
        assert asset["processing_status"] == "completed"
        assert asset["chunk_count"] > 0

        print("\n=== Testing Empty File ===")
        empty_info = upload_file(ws_id, "empty.txt")
        empty_asset = wait_for_asset(ws_id, empty_info["id"])
        print(f"Empty File -> Status: {empty_asset['processing_status']} | Chunks: {empty_asset['chunk_count']}")
        assert empty_asset["processing_status"] == "completed"
        assert empty_asset["chunk_count"] == 0

        print("\n=== Testing Large File ===")
        large_info = upload_file(ws_id, "large.txt")
        large_asset = wait_for_asset(ws_id, large_info["id"])
        print(f"Large File -> Status: {large_asset['processing_status']} | Chunks: {large_asset['chunk_count']}")
        assert large_asset["processing_status"] == "completed"
        assert large_asset["chunk_count"] > 1

        print("\n=== Testing Multilingual File ===")
        multi_info = upload_file(ws_id, "multilingual.txt")
        multi_asset = wait_for_asset(ws_id, multi_info["id"])
        print(f"Multilingual File -> Status: {multi_asset['processing_status']} | Chunks: {multi_asset['chunk_count']}")
        assert multi_asset["processing_status"] == "completed"
        
        print("\n=== Testing Versioning & Duplicate Content ===")
        version2_info = upload_file(ws_id, "test.txt")
        v2_asset = wait_for_asset(ws_id, version2_info["id"])
        print(f"Version 2 -> Status: {v2_asset['processing_status']} | Version: {v2_asset['version_number']}")
        assert v2_asset["processing_status"] == "completed"
        assert v2_asset["version_number"] > 1
        assert v2_asset["previous_version_id"] == asset["id"]
        assert v2_asset["is_latest"] is True
        
        # Verify old version is not latest
        resp = requests.get(f"{API_URL}/workspaces/{ws_id}/assets/{asset['id']}")
        assert resp.status_code == 200
        old_asset = resp.json()
        assert old_asset["is_latest"] is False
        print("Versioning assertions passed.")

        # Real documents if they exist
        for doc in ["notes.pdf", "eval_medical.docx", "eval_finance.pptx"]:
            if os.path.exists(doc):
                print(f"\n=== Testing {doc} ===")
                doc_info = upload_file(ws_id, doc)
                doc_asset = wait_for_asset(ws_id, doc_info["id"], timeout=120)
                print(f"{doc} -> Status: {doc_asset['processing_status']} | Chunks: {doc_asset['chunk_count']}")
                assert doc_asset["processing_status"] == "completed"
                assert doc_asset["chunk_count"] > 0
            else:
                print(f"\n[SKIP] {doc} not found in current directory.")

        print("\n✅ All ingestion tests passed!")

    finally:
        print("\n=== Cleanup ===")
        requests.delete(f"{API_URL}/workspaces/{ws_id}")
        for f in ["test.txt", "empty.txt", "large.txt", "multilingual.txt"]:
            if os.path.exists(f):
                os.remove(f)

if __name__ == "__main__":
    main()
