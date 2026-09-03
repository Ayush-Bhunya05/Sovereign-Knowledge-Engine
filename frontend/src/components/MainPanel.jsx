import React, { useState, useEffect, useRef } from 'react';
import { uploadAsset, listAssets, deleteAsset, askQuestion, listFolders } from '../api';
import AssetDetailModal from './AssetDetailModal';
import ReactMarkdown from 'react-markdown';

function MainPanel({ workspace, folder, onWorkspaceUpdated }) {
  const [activeTab, setActiveTab] = useState('manager'); // 'manager' | 'search'
  
  // Asset Manager State
  const [assets, setAssets] = useState([]);
  const [allFolders, setAllFolders] = useState([]);
  const [expandedFolders, setExpandedFolders] = useState({ root: true });
  const [uploading, setUploading] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState(null);

  // Chat State
  const [searchQuery, setSearchQuery] = useState('');
  const [searchScope, setSearchScope] = useState('workspace'); // 'workspace' | 'folder'
  const [chatHistory, setChatHistory] = useState([]); // Array of { role: 'user'|'ai', content: string, strategy?: string, sql_query?: string, sql_results?: array, citations?: object }
  const [isSearching, setIsSearching] = useState(false);
  
  const chatEndRef = useRef(null);

  // Auto-scroll chat to bottom
  useEffect(() => {
    if (activeTab === 'search' && chatEndRef.current) {
      chatEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [chatHistory, activeTab]);

  // Poll assets periodically for live status updates
  useEffect(() => {
    if (!workspace) return;
    loadAssets();
    const interval = setInterval(loadAssets, 3000);
    return () => clearInterval(interval);
  }, [workspace, folder]);

  const loadAssets = async () => {
    if (!workspace) return;
    try {
      // Fetch all folders and all assets for the workspace to build the tree
      const [foldersData, assetsData] = await Promise.all([
        listFolders(workspace.id),
        listAssets(workspace.id)
      ]);
      setAllFolders(foldersData);
      setAssets(assetsData);
    } catch (e) {
      console.error(e);
    }
  };

  const toggleFolder = (folderId) => {
    setExpandedFolders(prev => ({ ...prev, [folderId]: !prev[folderId] }));
  };

  const handleFileUpload = async (e) => {
    const files = e.target.files;
    if (!files || files.length === 0 || !workspace) return;
    
    setUploading(true);
    try {
      const promises = Array.from(files).map(file => 
        uploadAsset(workspace.id, folder?.id || null, file)
      );
      await Promise.all(promises);
      loadAssets();
      onWorkspaceUpdated(); // Refresh stats
    } catch (e) {
      alert("Upload failed: " + e.message);
    } finally {
      setUploading(false);
      e.target.value = null; // reset file input
    }
  };

  const handleDeleteAsset = async (e, assetId) => {
    e.stopPropagation(); // prevent opening modal
    if (!confirm("Delete asset?")) return;
    try {
      await deleteAsset(workspace.id, assetId);
      loadAssets();
      onWorkspaceUpdated();
    } catch (e) {
      alert(e.message);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim() || !workspace || isSearching) return;

    const query = searchQuery.trim();
    setSearchQuery('');
    
    // Add user message to history
    setChatHistory(prev => [...prev, { role: 'user', content: query }]);
    setIsSearching(true);
    
    try {
      let folderId = null;
      let assetId = null;
      
      if (searchScope === 'folder') {
        folderId = folder?.id;
      } else if (searchScope.startsWith('asset:')) {
        assetId = searchScope.split(':')[1];
      }
      
      const response = await askQuestion(workspace.id, query, folderId, assetId);
      
        setChatHistory(prev => [...prev, { 
        role: 'ai', 
        content: response.answer,
        strategy: response.strategy,
        sql_query: response.sql_query,
        sql_results: response.sql_results,
        strategy_log: response.strategy_log,
        citations: response.citations
      }]);
    } catch (e) {
      setChatHistory(prev => [...prev, { 
        role: 'ai', 
        content: `**Error:** ${e.message || 'An unexpected backend error occurred.'}`,
        strategy: 'ERROR'
      }]);
    } finally {
      setIsSearching(false);
    }
  };

  const toggleSqlPreview = (index) => {
    setChatHistory(prev => prev.map((msg, i) => {
      if (i === index) {
        return { ...msg, sqlExpanded: !msg.sqlExpanded };
      }
      return msg;
    }));
  };

  const toggleStrategyLog = (index) => {
    setChatHistory(prev => prev.map((msg, i) => {
      if (i === index) {
        return { ...msg, logExpanded: !msg.logExpanded };
      }
      return msg;
    }));
  };

  if (!workspace) {
    return (
      <div className="empty-state-full">
        Select or create a Workspace to begin.
      </div>
    );
  }

  return (
    <div className="main-panel">
      {selectedAsset && (
        <AssetDetailModal 
          asset={selectedAsset} 
          onClose={() => setSelectedAsset(null)} 
        />
      )}
      <div className="main-panel-header" style={{ marginBottom: '16px' }}>
        <h2 className="main-title">
          {workspace.name} <span className="text-secondary">{folder ? `> ${folder.name}` : '> (Root)'}</span>
        </h2>
        <div>
          <label className={`btn btn-primary ${uploading ? 'btn-disabled' : ''}`}>
            {uploading ? 'Uploading...' : 'Upload Files'}
            <input type="file" multiple className="hidden-input" onChange={handleFileUpload} disabled={uploading} />
          </label>
        </div>
      </div>
      
      <div className="detail-tabs" style={{ marginBottom: '24px' }}>
        <button 
          className={`tab-btn ${activeTab === 'manager' ? 'active' : ''}`}
          onClick={() => setActiveTab('manager')}
        >
          Asset Manager
        </button>
        <button 
          className={`tab-btn ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => setActiveTab('search')}
        >
          Ask Assistant
        </button>
      </div>

      {activeTab === 'manager' && (
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>Filename</th>
                <th>Status</th>
                <th>Type</th>
                <th>Size</th>
                <th>Pages</th>
                <th>Chunks</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {/* Root Assets */}
              <tr 
                className="folder-row" 
                onClick={() => toggleFolder('root')} 
                style={{ cursor: 'pointer', backgroundColor: 'var(--color-bg-secondary)', fontWeight: 'bold' }}
              >
                <td colSpan="7">
                  <span style={{ marginLeft: '8px' }}>
                    {expandedFolders['root'] ? '📂' : '📁'} (Root) <span className="text-secondary" style={{fontWeight: 'normal', fontSize: '0.9em'}}>({assets.filter(a => !a.folder_id).length} assets)</span>
                  </span>
                </td>
              </tr>
              {expandedFolders['root'] && assets.filter(a => !a.folder_id).map(asset => (
                <tr 
                  key={asset.id} 
                  onClick={() => setSelectedAsset(asset)}
                  style={{ cursor: 'pointer' }}
                >
                  <td className="cell-filename" title={asset.filename} style={{ paddingLeft: '32px' }}>📄 {asset.filename}</td>
                  <td>
                    <span className={`status-badge-inline ${asset.processing_status}`}>
                      {asset.processing_status}
                    </span>
                  </td>
                  <td className="text-secondary">{asset.document_type}</td>
                  <td className="text-secondary">{(asset.file_size / 1024).toFixed(1)} KB</td>
                  <td className="text-secondary">{asset.page_count || 0}</td>
                  <td className="text-secondary">{asset.chunk_count || 0}</td>
                  <td>
                    <button onClick={(e) => handleDeleteAsset(e, asset.id)} className="btn btn-danger btn-small">Delete</button>
                  </td>
                </tr>
              ))}
              {expandedFolders['root'] && assets.filter(a => !a.folder_id).length === 0 && (
                <tr>
                  <td colSpan="7" className="empty-state-row" style={{ paddingLeft: '32px' }}>
                    No assets in Root.
                  </td>
                </tr>
              )}

              {/* Subfolders */}
              {allFolders.map(f => {
                const folderAssets = assets.filter(a => a.folder_id === f.id);
                const isExpanded = expandedFolders[f.id];
                return (
                  <React.Fragment key={f.id}>
                    <tr 
                      className="folder-row" 
                      onClick={() => toggleFolder(f.id)} 
                      style={{ cursor: 'pointer', backgroundColor: 'var(--color-bg-secondary)', fontWeight: 'bold' }}
                    >
                      <td colSpan="7">
                        <span style={{ marginLeft: '8px' }}>
                          {isExpanded ? '📂' : '📁'} {f.name} <span className="text-secondary" style={{fontWeight: 'normal', fontSize: '0.9em'}}>({folderAssets.length} assets)</span>
                        </span>
                      </td>
                    </tr>
                    {isExpanded && folderAssets.map(asset => (
                      <tr 
                        key={asset.id} 
                        onClick={() => setSelectedAsset(asset)}
                        style={{ cursor: 'pointer' }}
                      >
                        <td className="cell-filename" title={asset.filename} style={{ paddingLeft: '32px' }}>📄 {asset.filename}</td>
                        <td>
                          <span className={`status-badge-inline ${asset.processing_status}`}>
                            {asset.processing_status}
                          </span>
                        </td>
                        <td className="text-secondary">{asset.document_type}</td>
                        <td className="text-secondary">{(asset.file_size / 1024).toFixed(1)} KB</td>
                        <td className="text-secondary">{asset.page_count || 0}</td>
                        <td className="text-secondary">{asset.chunk_count || 0}</td>
                        <td>
                          <button onClick={(e) => handleDeleteAsset(e, asset.id)} className="btn btn-danger btn-small">Delete</button>
                        </td>
                      </tr>
                    ))}
                    {isExpanded && folderAssets.length === 0 && (
                      <tr>
                        <td colSpan="7" className="empty-state-row" style={{ paddingLeft: '32px' }}>
                          No assets in this folder.
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
              
              {allFolders.length === 0 && assets.length === 0 && (
                <tr>
                  <td colSpan="7" className="empty-state-row">
                    No folders or assets in this workspace.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'search' && (
        <div className="chat-container">
          <div className="chat-history">
            {chatHistory.length === 0 && (
              <div className="empty-state-full" style={{ border: 'none', height: '100%' }}>
                <p>Hello! I am your AI Data Assistant.</p>
                <p style={{ fontSize: '0.9rem', color: 'var(--color-text-secondary)', marginTop: '8px' }}>
                  Ask me questions about your uploaded documents or structured datasets.
                </p>
              </div>
            )}
            
            {chatHistory.map((msg, idx) => (
              <div key={idx} className={`chat-message ${msg.role}`}>
                {msg.role === 'ai' && msg.strategy && msg.strategy !== 'ORCHESTRATOR' && (
                  <div>
                    <span className={`strategy-badge badge-${msg.strategy}`}>
                      {msg.strategy}
                    </span>
                  </div>
                )}
                
                {msg.role === 'ai' ? (
                  <div className="markdown-body">
                    <ReactMarkdown>{msg.content || ""}</ReactMarkdown>
                  </div>
                ) : (
                  <div>{msg.content || ""}</div>
                )}
                
                {/* Expandable SQL Preview */}
                {msg.role === 'ai' && msg.sql_query && (
                  <div className="sql-preview">
                    <div className="sql-preview-header" onClick={() => toggleSqlPreview(idx)}>
                      <span>SQL Generation & Results</span>
                      <span>{msg.sqlExpanded ? '▼' : '▶'}</span>
                    </div>
                    {msg.sqlExpanded && (
                      <div>
                        <div className="sql-preview-content">{msg.sql_query}</div>
                        {msg.sql_results && msg.sql_results.length > 0 && (
                          <div style={{ overflowX: 'auto' }}>
                            <table className="sql-results-table">
                              <thead>
                                <tr>
                                  {Object.keys(msg.sql_results[0]).map(k => (
                                    <th key={k}>{k}</th>
                                  ))}
                                </tr>
                              </thead>
                              <tbody>
                                {msg.sql_results.map((row, rowIdx) => (
                                  <tr key={rowIdx}>
                                    {Object.values(row).map((val, valIdx) => (
                                      <td key={valIdx}>{String(val)}</td>
                                    ))}
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        )}
                        {msg.sql_results && msg.sql_results.length === 0 && (
                          <div style={{ padding: '8px', color: '#a0a0a0', fontSize: '0.8rem' }}>No rows returned.</div>
                        )}
                      </div>
                    )}
                  </div>
                )}
                
                {/* Citations and Strategy Log Expandable */}
                {msg.role === 'ai' && Array.isArray(msg.strategy_log) && msg.strategy_log.length > 0 && (
                  <div className="sql-preview">
                    <div className="sql-preview-header" onClick={() => toggleStrategyLog(idx)}>
                      <span>Tool Execution & Strategy Log</span>
                      <span>{msg.logExpanded ? '▼' : '▶'}</span>
                    </div>
                    {msg.logExpanded && (
                      <div style={{ padding: '8px', fontSize: '0.85rem', color: '#ccc', backgroundColor: '#222' }}>
                        {msg.strategy_log.map((logItem, logIdx) => (
                          <div key={logIdx} style={{ marginBottom: '8px', borderBottom: '1px solid #444', paddingBottom: '4px' }}>
                            {logItem.action === 'tool_call' ? (
                              <div>
                                <strong>Tool:</strong> {logItem.tool} <br/>
                                <strong>Args:</strong> {JSON.stringify(logItem.args || {})}
                              </div>
                            ) : (
                              <div>
                                <strong>Result:</strong> {String(logItem.result)}
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
                {msg.role === 'ai' && msg.citations && (msg.citations.datasets?.length > 0 || msg.citations.documents?.length > 0) && (
                  <div className="citations">
                    <strong>Sources:</strong>
                    <div className="citation-list">
                      {msg.citations.datasets?.map(ds => (
                        <span key={ds} className="citation-tag dataset" title="Structured Dataset">📊 {ds}</span>
                      ))}
                      {msg.citations.documents?.map(doc => (
                        <span key={doc} className="citation-tag" title="Text Document">📄 {doc}</span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
            
            {isSearching && (
              <div className="chat-message ai">
                <div style={{ fontStyle: 'italic', color: 'var(--color-text-secondary)' }}>
                  Thinking...
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          <form onSubmit={handleSearch} style={{ display: 'flex', gap: '12px' }}>
            <input 
              type="text" 
              className="input-field" 
              style={{ borderRadius: '6px' }}
              placeholder="Ask a question..." 
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              disabled={isSearching}
            />
            <select 
              className="input-field" 
              style={{ flex: '0 0 200px', borderRadius: '6px' }}
              value={searchScope}
              onChange={e => setSearchScope(e.target.value)}
              disabled={isSearching}
            >
              <option value="workspace">Entire Workspace</option>
              <option value="folder" disabled={!folder}>Current Folder Only</option>
              {assets.length > 0 && (
                <optgroup label="Specific File">
                  {assets.map(a => (
                    <option key={a.id} value={`asset:${a.id}`}>
                      📄 {a.filename}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>
            <button type="submit" className="btn btn-primary" style={{ borderRadius: '6px' }} disabled={isSearching || !searchQuery.trim()}>
              Send
            </button>
          </form>
        </div>
      )}
    </div>
  );
}

export default MainPanel;
