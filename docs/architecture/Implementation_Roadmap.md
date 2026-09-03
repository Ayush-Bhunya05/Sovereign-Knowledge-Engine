# Implementation Roadmap

Extracted from Architecture Design Document v2.1.

### Milestone 1: Foundation — Database & Workspace CRUD *(Week 1–2)*
**Goal**: New database schema live, workspace/folder/asset CRUD working, file upload scoped to workspaces. No retrieval changes yet.
1. `models/workspace.py`, `models/folder.py`
2. `models/asset.py`
3. `models/asset_chunk.py`
4. Database migration script
5. `services/workspace_service.py`, `services/folder_service.py`
6. `services/asset_service.py`
7. `api/v2/workspaces.py`, `api/v2/folders.py`, `api/v2/assets.py`

### Milestone 2: Ingestion Pipeline Refactor *(Week 3)*
**Goal**: Ingestion pipeline decomposed into `IngestionOrchestrator`. Context-preserving chunking, content hashing, and embedding versioning.

### Milestone 3: Scoped Milvus & Retrieval *(Week 4)*
**Goal**: New Milvus collection with scope fields. Search respects scope.

### Milestone 4: Structured Data *(Week 5–6)*
**Goal**: CSV/XLSX upload, schema detection, dynamic SQL tables, dataset summaries embedded.

### Milestone 5: Query Planner *(Week 7)*
**Goal**: Intelligent query routing with confidence scoring.

### Milestone 6: Chat & LLM *(Week 8)*
**Goal**: Conversational RAG with history and source attribution.

### Milestone 7: Polish & Hardening *(Week 9–10)*
**Goal**: Production-ready quality (error handling, API docs, performance).
