/**
 * API client for communicating with the FastAPI backend.
 */

const API_BASE = "/api/v2";

async function request(endpoint, options = {}) {
  const url = `${API_BASE}${endpoint}`;
  const response = await fetch(url, options);

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export async function healthCheck() {
  return request("/health");
}

// Workspaces
export async function listWorkspaces() {
  return request("/workspaces");
}

export async function createWorkspace(data) {
  return request("/workspaces", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function getWorkspace(workspaceId) {
  return request(`/workspaces/${workspaceId}`);
}

export async function deleteWorkspace(workspaceId) {
  return request(`/workspaces/${workspaceId}`, { method: "DELETE" });
}

export async function renameWorkspace(workspaceId, name) {
  return request(`/workspaces/${workspaceId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

// Folders
export async function listFolders(workspaceId) {
  return request(`/workspaces/${workspaceId}/folders`);
}

export async function createFolder(workspaceId, data) {
  return request(`/workspaces/${workspaceId}/folders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
}

export async function deleteFolder(workspaceId, folderId) {
  return request(`/workspaces/${workspaceId}/folders/${folderId}`, { method: "DELETE" });
}

export async function renameFolder(workspaceId, folderId, name) {
  return request(`/workspaces/${workspaceId}/folders/${folderId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
}

// Assets
export async function uploadAsset(workspaceId, folderId, file) {
  const formData = new FormData();
  formData.append("file", file);
  if (folderId) {
    formData.append("folder_id", folderId);
  }

  return request(`/workspaces/${workspaceId}/assets/upload`, {
    method: "POST",
    body: formData,
  });
}

export async function listAssets(workspaceId, folderId = null) {
  let url = `/workspaces/${workspaceId}/assets`;
  if (folderId) {
    url += `?folder_id=${folderId}`;
  }
  return request(url);
}

export async function getAsset(workspaceId, assetId) {
  return request(`/workspaces/${workspaceId}/assets/${assetId}`);
}

export async function getAssetText(workspaceId, assetId) {
  return request(`/workspaces/${workspaceId}/assets/${assetId}/text`);
}

export async function getAssetChunks(workspaceId, assetId) {
  return request(`/workspaces/${workspaceId}/assets/${assetId}/chunks`);
}

export async function deleteAsset(workspaceId, assetId) {
  return request(`/workspaces/${workspaceId}/assets/${assetId}`, { method: "DELETE" });
}

// -----------------------------------------------------------------------------
// Search (V2)
// -----------------------------------------------------------------------------

export async function askQuestion(workspaceId, query, folderId = null, assetId = null, topK = 10) {
  return request(`/workspaces/${workspaceId}/search/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      query,
      folder_id: folderId,
      asset_id: assetId,
      top_k: topK
    })
  });
}
