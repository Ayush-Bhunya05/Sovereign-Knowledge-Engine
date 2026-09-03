import React, { useState, useEffect } from 'react';
import { getAssetText, getAssetChunks } from '../api';

function AssetDetailModal({ asset, onClose }) {
  const [activeTab, setActiveTab] = useState('metadata');
  const [text, setText] = useState('');
  const [chunks, setChunks] = useState([]);
  const [expandedChunk, setExpandedChunk] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (activeTab === 'text' && !text) {
      loadText();
    }
    if (activeTab === 'chunks' && chunks.length === 0) {
      loadChunks();
    }
  }, [activeTab]);

  const loadText = async () => {
    setLoading(true);
    try {
      const data = await getAssetText(asset.workspace_id, asset.id);
      setText(data.extracted_text || 'No text extracted.');
    } catch (e) {
      setText('Failed to load text.');
    }
    setLoading(false);
  };

  const loadChunks = async () => {
    setLoading(true);
    try {
      const data = await getAssetChunks(asset.workspace_id, asset.id);
      setChunks(data);
    } catch (e) {
      setChunks([]);
    }
    setLoading(false);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{asset.filename}</h2>
          <button className="btn-delete" onClick={onClose}>&times;</button>
        </div>
        
        <div className="modal-body">
          <div className="detail-tabs">
            <button 
              className={`tab-btn ${activeTab === 'metadata' ? 'active' : ''}`}
              onClick={() => setActiveTab('metadata')}
            >
              Metadata
            </button>
            <button 
              className={`tab-btn ${activeTab === 'text' ? 'active' : ''}`}
              onClick={() => setActiveTab('text')}
            >
              Extracted Text
            </button>
            <button 
              className={`tab-btn ${activeTab === 'chunks' ? 'active' : ''}`}
              onClick={() => setActiveTab('chunks')}
            >
              Chunks ({asset.chunk_count})
            </button>
          </div>

          {activeTab === 'metadata' && (
            <div>
              <div className="modal-meta">
                <div className="meta-item">
                  <div className="label">Status</div>
                  <div className={`value ${asset.processing_status === 'completed' ? 'text-success' : 'text-warning'}`}>
                    {asset.processing_status}
                  </div>
                </div>
                <div className="meta-item">
                  <div className="label">Type</div>
                  <div className="value">{asset.document_type}</div>
                </div>
                <div className="meta-item">
                  <div className="label">Size</div>
                  <div className="value">{(asset.file_size / 1024).toFixed(1)} KB</div>
                </div>
                <div className="meta-item">
                  <div className="label">Pages</div>
                  <div className="value">{asset.page_count || 'N/A'}</div>
                </div>
                <div className="meta-item">
                  <div className="label">Language</div>
                  <div className="value">{asset.language || 'Unknown'}</div>
                </div>
              </div>
              
              {asset.parser_metadata && (
                <div className="mb-4">
                  <h3 className="sidebar-subtitle" style={{padding:0}}>Parser Metadata</h3>
                  <pre className="extracted-text" style={{padding: '10px', fontSize: '0.8rem'}}>
                    {JSON.stringify(asset.parser_metadata, null, 2)}
                  </pre>
                </div>
              )}
            </div>
          )}

          {activeTab === 'text' && (
            <div>
              {loading ? <p>Loading text...</p> : (
                <div className="extracted-text">
                  {text}
                </div>
              )}
            </div>
          )}

          {activeTab === 'chunks' && (
            <div>
              {loading ? <p>Loading chunks...</p> : (
                <div className="chunk-list">
                  {chunks.map(chunk => (
                    <div 
                      key={chunk.id} 
                      className={`chunk-card ${expandedChunk === chunk.id ? 'expanded' : ''}`}
                      onClick={() => setExpandedChunk(expandedChunk === chunk.id ? null : chunk.id)}
                    >
                      <div className="chunk-header">
                        <span className="chunk-index">#{chunk.chunk_index}</span>
                        {chunk.page_number && <span className="chunk-page">Page {chunk.page_number}</span>}
                        <span className="chunk-chars">{chunk.character_count} chars</span>
                      </div>
                      <div className="chunk-preview">
                        {expandedChunk === chunk.id ? chunk.chunk_text : chunk.chunk_text.substring(0, 150) + '...'}
                      </div>
                    </div>
                  ))}
                  {chunks.length === 0 && <p className="text-secondary">No chunks found.</p>}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default AssetDetailModal;
