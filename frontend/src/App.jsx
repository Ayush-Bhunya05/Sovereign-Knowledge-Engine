import React, { useState, useEffect } from 'react';
import Sidebar from './components/Sidebar';
import MainPanel from './components/MainPanel';
import HealthDashboard from './components/HealthDashboard';
import { listWorkspaces } from './api';
import './index.css';

function App() {
  const [workspaces, setWorkspaces] = useState([]);
  const [currentWorkspace, setCurrentWorkspace] = useState(null);
  const [currentFolder, setCurrentFolder] = useState(null);

  useEffect(() => {
    loadWorkspaces();
  }, []);

  const loadWorkspaces = async () => {
    try {
      const data = await listWorkspaces();
      setWorkspaces(data);
      if (!currentWorkspace && data.length > 0) {
        setCurrentWorkspace(data[0]);
      }
    } catch (e) {
      console.error("Failed to load workspaces", e);
    }
  };

  const handleWorkspaceChange = (ws) => {
    setCurrentWorkspace(ws);
    setCurrentFolder(null);
  };

  return (
    <div className="app-container">
      <Sidebar 
        workspaces={workspaces} 
        currentWorkspace={currentWorkspace} 
        onWorkspaceSelect={handleWorkspaceChange}
        onWorkspacesChanged={loadWorkspaces}
        currentFolder={currentFolder}
        onFolderSelect={setCurrentFolder}
      />
      <div className="main-content-wrapper">
        <HealthDashboard />
        <MainPanel 
          workspace={currentWorkspace}
          folder={currentFolder}
          onWorkspaceUpdated={loadWorkspaces}
        />
      </div>
    </div>
  );
}

export default App;
