import React, { useState, useEffect } from 'react';
import { createWorkspace, listFolders, createFolder, deleteFolder, deleteWorkspace } from '../api';

function Sidebar({ workspaces, currentWorkspace, onWorkspaceSelect, onWorkspacesChanged, currentFolder, onFolderSelect }) {
  const [folders, setFolders] = useState([]);
  const [newWsName, setNewWsName] = useState('');
  const [newFolderName, setNewFolderName] = useState('');

  useEffect(() => {
    if (currentWorkspace) {
      loadFolders();
    } else {
      setFolders([]);
    }
  }, [currentWorkspace]);

  const loadFolders = async () => {
    try {
      const data = await listFolders(currentWorkspace.id);
      setFolders(data);
    } catch (e) {
      console.error(e);
    }
  };

  const handleCreateWorkspace = async (e) => {
    e.preventDefault();
    if (!newWsName.trim()) return;
    try {
      const ws = await createWorkspace({ name: newWsName });
      setNewWsName('');
      onWorkspacesChanged();
      onWorkspaceSelect(ws);
    } catch (e) {
      alert("Error creating workspace: " + e.message);
    }
  };

  const handleDeleteWorkspace = async (id) => {
    if (!confirm("Are you sure? This will delete EVERYTHING in this workspace.")) return;
    try {
      await deleteWorkspace(id);
      onWorkspacesChanged();
      if (currentWorkspace?.id === id) onWorkspaceSelect(null);
    } catch (e) {
      alert(e.message);
    }
  };

  const handleCreateFolder = async (e) => {
    e.preventDefault();
    if (!newFolderName.trim() || !currentWorkspace) return;
    try {
      await createFolder(currentWorkspace.id, { name: newFolderName, parent_folder_id: null });
      setNewFolderName('');
      loadFolders();
    } catch (e) {
      alert("Error creating folder: " + e.message);
    }
  };

  const handleDeleteFolder = async (id) => {
    if (!confirm("Delete this folder?")) return;
    try {
      await deleteFolder(currentWorkspace.id, id);
      if (currentFolder?.id === id) onFolderSelect(null);
      loadFolders();
    } catch (e) {
      alert(e.message);
    }
  };

  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <h1>Sovereign Knowledge Engine</h1>
        <form onSubmit={handleCreateWorkspace} className="create-form">
          <input 
            type="text" 
            placeholder="New Workspace..." 
            value={newWsName}
            onChange={(e) => setNewWsName(e.target.value)}
            className="input-field"
          />
          <button type="submit" className="btn btn-primary btn-small">+</button>
        </form>
      </div>

      <div className="sidebar-content">
        <h2 className="sidebar-title">Workspaces</h2>
        <div className="workspace-list">
          {workspaces.map(ws => (
            <div key={ws.id} className="workspace-item-container">
              <div 
                className={`sidebar-item ${currentWorkspace?.id === ws.id ? 'active' : ''}`}
                onClick={() => onWorkspaceSelect(ws)}
              >
                <span className="sidebar-item-name">{ws.name}</span>
                <button onClick={(e) => { e.stopPropagation(); handleDeleteWorkspace(ws.id); }} className="btn-delete" title="Delete Workspace">&times;</button>
              </div>
              
              {currentWorkspace?.id === ws.id && (
                <div className="folder-section">
                  {ws.stats && (
                    <div className="workspace-stats">
                      <div>Folders: {ws.stats.total_folders}</div>
                      <div>Assets: {ws.stats.total_assets}</div>
                      <div>Chunks: {ws.stats.total_chunks}</div>
                    </div>
                  )}
                  <h3 className="sidebar-subtitle">Folders</h3>
                  <div 
                    className={`sidebar-subitem ${currentFolder === null ? 'active' : ''}`}
                    onClick={() => onFolderSelect(null)}
                  >
                    (Root)
                  </div>

                  {folders.map(f => (
                    <div 
                      key={f.id} 
                      className={`sidebar-subitem ${currentFolder?.id === f.id ? 'active' : ''}`}
                      onClick={() => onFolderSelect(f)}
                    >
                      <span className="sidebar-item-name">📁 {f.name}</span>
                      <button onClick={(e) => { e.stopPropagation(); handleDeleteFolder(f.id); }} className="btn-delete" title="Delete Folder">&times;</button>
                    </div>
                  ))}

                  <form onSubmit={handleCreateFolder} className="create-form mt-sm">
                    <input 
                      type="text" 
                      placeholder="New Folder..." 
                      value={newFolderName}
                      onChange={(e) => setNewFolderName(e.target.value)}
                      className="input-field"
                    />
                    <button type="submit" className="btn btn-primary btn-small">+</button>
                  </form>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default Sidebar;
