# API Design v2

This document extracts the API Design from the Architecture Design Document v2.1.

## API v2 Endpoints

### Workspaces
| Method | Path | Description |
|---|---|---|
| POST | `/api/v2/workspaces` | Create workspace |
| GET | `/api/v2/workspaces` | List workspaces |
| GET | `/api/v2/workspaces/{id}` | Get workspace details + stats |
| PATCH | `/api/v2/workspaces/{id}` | Update workspace |
| DELETE | `/api/v2/workspaces/{id}` | Delete workspace (cascade) |

### Folders
| Method | Path | Description |
|---|---|---|
| POST | `/api/v2/workspaces/{wid}/folders` | Create folder |
| GET | `/api/v2/workspaces/{wid}/folders` | List folders (flat or tree) |
| GET | `/api/v2/workspaces/{wid}/folders/{fid}` | Get folder + contents |
| GET | `/api/v2/workspaces/{wid}/folders/{fid}/tree` | Get full subtree |
| PATCH | `/api/v2/workspaces/{wid}/folders/{fid}` | Rename / move folder |
| DELETE | `/api/v2/workspaces/{wid}/folders/{fid}` | Delete folder (cascade) |

### Assets
| Method | Path | Description |
|---|---|---|
| POST | `/api/v2/workspaces/{wid}/assets/upload` | Upload file (auto-detect version) |
| GET | `/api/v2/workspaces/{wid}/assets` | List assets (filterable by folder) |
| GET | `/api/v2/assets/{id}` | Get asset detail |
| GET | `/api/v2/assets/{id}/chunks` | Get chunks |
| GET | `/api/v2/assets/{id}/versions` | List all versions |
| DELETE | `/api/v2/assets/{id}` | Delete asset (or specific version) |
| POST | `/api/v2/assets/{id}/move` | Move to different folder |
| POST | `/api/v2/assets/{id}/reprocess` | Re-run ingestion pipeline |

### Search & Chat
| Method | Path | Description |
|---|---|---|
| POST | `/api/v2/search` | Semantic search (scoped) |
| POST | `/api/v2/chat/sessions` | Create chat session |
| GET | `/api/v2/chat/sessions` | List sessions |
| POST | `/api/v2/chat/sessions/{sid}/query` | Ask question |
| GET | `/api/v2/chat/sessions/{sid}/messages` | Get history |
| DELETE | `/api/v2/chat/sessions/{sid}` | Delete session |

### Datasets
| Method | Path | Description |
|---|---|---|
| GET | `/api/v2/datasets/{id}` | Get dataset metadata |
| GET | `/api/v2/datasets/{id}/sheets` | List sheets |
| GET | `/api/v2/datasets/{id}/sheets/{sid}/preview` | Preview rows (paginated) |
| POST | `/api/v2/datasets/{id}/sheets/{sid}/query` | Execute validated SQL |

### System
| Method | Path | Description |
|---|---|---|
| GET | `/api/v2/health` | Health check (all services) |
| GET | `/api/v2/system/embedding-status` | Current embedding model + chunk counts per model |
| POST | `/api/v2/system/reindex` | Trigger re-indexing (admin) |

## API Versioning Strategy
The current v1 API continues to work unchanged during migration. The v2 API is the new workspace-aware surface. Once v2 is stable, v1 is deprecated with a 2-release sunset period.
