"""Test script for Milestone 1: Workspace/Folder/Asset CRUD."""

import requests
import json
import uuid

API_URL = "http://localhost:8000/api/v2"

def main():
    print("=== Testing Workspaces ===")
    # Create
    resp = requests.post(f"{API_URL}/workspaces", json={"name": "Test WS", "description": "A workspace for testing"})
    assert resp.status_code == 201
    ws = resp.json()
    ws_id = ws["id"]
    print(f"Created Workspace: {ws_id}")

    # List
    resp = requests.get(f"{API_URL}/workspaces")
    assert resp.status_code == 200
    workspaces = resp.json()
    print(f"Listed {len(workspaces)} workspaces")
    
    # Update
    resp = requests.patch(f"{API_URL}/workspaces/{ws_id}", json={"name": "Updated WS"})
    assert resp.status_code == 200
    print(f"Updated workspace name: {resp.json()['name']}")

    print("\n=== Testing Folders ===")
    # Create Root Folder
    resp = requests.post(f"{API_URL}/workspaces/{ws_id}/folders", json={"name": "RootFolder"})
    assert resp.status_code == 201
    root_folder = resp.json()
    root_id = root_folder["id"]
    print(f"Created Root Folder: {root_id} | Path: {root_folder['path']}")

    # Create Sub Folder
    resp = requests.post(f"{API_URL}/workspaces/{ws_id}/folders", json={"name": "SubFolder", "parent_folder_id": root_id})
    assert resp.status_code == 201
    sub_folder = resp.json()
    sub_id = sub_folder["id"]
    print(f"Created Sub Folder: {sub_id} | Path: {sub_folder['path']}")

    # List Folders
    resp = requests.get(f"{API_URL}/workspaces/{ws_id}/folders")
    assert resp.status_code == 200
    print(f"Listed {len(resp.json())} folders")

    print("\n=== Testing Assets ===")
    # Upload Asset
    with open("small_test.txt", "w") as f:
        f.write("This is a small test file for upload via v2 API.")
        
    with open("small_test.txt", "rb") as f:
        files = {"file": ("small_test.txt", f, "text/plain")}
        data = {"folder_id": root_id}
        resp = requests.post(f"{API_URL}/workspaces/{ws_id}/assets/upload", files=files, data=data)
        
    assert resp.status_code == 201
    asset = resp.json()
    asset_id = asset["id"]
    print(f"Uploaded Asset: {asset_id} | Name: {asset['filename']} | Folder: {asset['folder_id']}")

    # List Assets
    resp = requests.get(f"{API_URL}/workspaces/{ws_id}/assets")
    assert resp.status_code == 200
    assets = resp.json()
    print(f"Listed {len(assets)} assets in workspace")

    print("\n=== Testing Deletion ===")
    # Delete Asset
    resp = requests.delete(f"{API_URL}/workspaces/{ws_id}/assets/{asset_id}")
    assert resp.status_code == 204
    print("Deleted Asset")

    # Delete Workspace (Cascade should kill folders)
    resp = requests.delete(f"{API_URL}/workspaces/{ws_id}")
    assert resp.status_code == 204
    print("Deleted Workspace (cascaded)")

    print("\n✅ All tests passed!")

if __name__ == "__main__":
    main()
