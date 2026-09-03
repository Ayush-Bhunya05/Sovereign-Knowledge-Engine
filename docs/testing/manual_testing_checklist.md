# Manual Testing Checklist - Milestone 2.5

This document is the official regression testing checklist before every milestone to verify platform stability.

## 1. Workspace Operations

### 1.1 Create Workspace
**Purpose:** Verify a new Workspace can be created.
**Steps:**
1. Click "New Workspace" in the UI sidebar.
2. Enter a valid name (e.g., "Engineering Docs").
3. Submit the form.
**Expected Result:** The Workspace appears in the sidebar and is automatically selected.
**Actual Result:** 
**Status:** 

### 1.2 Rename Workspace
**Purpose:** Verify a Workspace can be renamed.
**Steps:**
1. Select a Workspace.
2. Click the "Rename" button.
3. Enter a new name and submit.
**Expected Result:** The Workspace name updates in the UI and sidebar immediately.
**Actual Result:** 
**Status:** 

### 1.3 Delete Workspace
**Purpose:** Verify Workspace deletion and cascade cleanup.
**Steps:**
1. Select a Workspace containing Folders and Assets.
2. Click "Delete Workspace".
3. Acknowledge the warning (Folders, Assets, Chunks, Embeddings, Milvus vectors).
4. Confirm deletion.
**Expected Result:** The Workspace is removed from the UI. All associated PostgreSQL records and Milvus vectors are deleted.
**Actual Result:** 
**Status:** 

## 2. Folder Operations

### 2.1 Create Folder
**Purpose:** Verify Folders can be created in a Workspace.
**Steps:**
1. Select a Workspace.
2. Click "New Folder".
3. Enter a name and submit.
**Expected Result:** The Folder appears in the current view.
**Actual Result:** 
**Status:** 

### 2.2 Nested Folders
**Purpose:** Verify Folders can be created inside other Folders.
**Steps:**
1. Open a Folder.
2. Click "New Folder".
3. Enter a name and submit.
**Expected Result:** The sub-folder is created and navigable.
**Actual Result:** 
**Status:** 

### 2.3 Delete Folder
**Purpose:** Verify Folder deletion cleans up contents.
**Steps:**
1. Select a Folder containing sub-folders and Assets.
2. Click "Delete".
3. Confirm deletion.
**Expected Result:** The Folder and all children (Folders and Assets) are removed. Associated chunks/vectors are deleted.
**Actual Result:** 
**Status:** 

## 3. Asset Operations & Ingestion

### 3.1 Upload Asset (Simple)
**Purpose:** Verify basic upload and ingestion flow.
**Steps:**
1. Upload a simple text file (`.txt`) or PDF.
2. Observe the UI processing status.
**Expected Result:** Status transitions: Pending -> Extracting -> Chunking -> Embedding -> Indexing -> Completed. Stats update correctly.
**Actual Result:** 
**Status:** 

### 3.2 Upload Asset (Large File)
**Purpose:** Verify the system handles large documents without timing out.
**Steps:**
1. Upload a large PDF (> 100 pages).
**Expected Result:** The file is chunked into many parts and completes successfully.
**Actual Result:** 
**Status:** 

### 3.3 Upload Asset (Empty File)
**Purpose:** Verify empty files fail gracefully.
**Steps:**
1. Upload a 0-byte `.txt` file.
**Expected Result:** Status reaches Completed with 0 chunks.
**Actual Result:** 
**Status:** 

### 3.4 Duplicate Uploads
**Purpose:** Verify uploading the same file creates a distinct Asset (since versioning is removed).
**Steps:**
1. Upload "report.pdf".
2. Upload "report.pdf" again in the same folder.
**Expected Result:** Two separate Assets appear.
**Actual Result:** 
**Status:** 

### 3.5 Delete Asset
**Purpose:** Verify single Asset deletion.
**Steps:**
1. Delete an uploaded Asset.
**Expected Result:** The Asset is removed from the UI. PostgreSQL chunks and Milvus vectors are deleted. Local file is removed.
**Actual Result:** 
**Status:** 

## 4. Metadata & Data Verification

### 4.1 Asset Metadata Generation
**Purpose:** Verify Docling extracts metadata properly.
**Steps:**
1. Upload a document.
2. Open the Developer Info Panel in the UI.
**Expected Result:** Page count, Chunk count, Embedding count, and language are displayed correctly.
**Actual Result:** 
**Status:** 

### 4.2 Chunking & Embeddings (PostgreSQL)
**Purpose:** Verify chunk and embedding persistence in Postgres.
**Steps:**
1. Connect to PostgreSQL.
2. Run `SELECT COUNT(*) FROM asset_chunks WHERE asset_id = '<uuid>';`
**Expected Result:** The count matches the UI. The `embedding_model` is populated.
**Actual Result:** 
**Status:** 

### 4.3 Indexing (Milvus)
**Purpose:** Verify vectors are inserted in Milvus.
**Steps:**
1. Connect to Milvus (or check API health endpoint).
2. Check entity count for `document_vectors` collection.
**Expected Result:** The count increases matching the chunk count of the uploaded file.
**Actual Result:** 
**Status:** 

## 5. UI and API Verification

### 5.1 Multiple Uploads Queue
**Purpose:** Verify multiple files can be uploaded concurrently.
**Steps:**
1. Select 3 files and upload them simultaneously.
**Expected Result:** One or more process while others wait or process concurrently. All eventually complete.
**Actual Result:** 
**Status:** 

### 5.2 Live Status Updates
**Purpose:** Verify the UI updates dynamically.
**Steps:**
1. Start a large upload.
2. Watch the status column.
**Expected Result:** Status updates automatically without manual page refresh.
**Actual Result:** 
**Status:** 

### 5.3 V1 API Eradication
**Purpose:** Ensure no legacy endpoints are hit.
**Steps:**
1. Open Browser Network Tab.
2. Perform all standard operations.
**Expected Result:** No requests to `/api/v1/documents`. All requests go to `/api/v2/*`.
**Actual Result:** 
**Status:** 
