import React, { useState, useEffect } from 'react';
import { healthCheck } from '../api';

function HealthDashboard() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 5000);
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const data = await healthCheck();
      setHealth(data);
    } catch (e) {
      setHealth({ status: "error", error: e.message });
    }
  };

  if (!health) return null;

  return (
    <div className="health-dashboard">
      <div className="health-metrics">
        <span className="health-title">System Health</span>
        <span className="health-item">
          <span className={`status-dot ${health.status === 'ok' ? 'ok' : 'error'}`}></span>
          API: {health.status}
        </span>
        <span className="health-item">
          <span className={`status-dot ${health.database === 'ok' ? 'ok' : 'error'}`}></span>
          DB: {health.database || 'unknown'}
        </span>
        <span className="health-item">
          <span className={`status-dot ${health.milvus?.status === 'ok' ? 'ok' : 'error'}`}></span>
          Milvus: {health.milvus?.status || 'unknown'}
        </span>
      </div>
      <div>
        {health.milvus?.entity_count !== undefined && (
          <span className="health-vectors">Total Vectors: {health.milvus.entity_count}</span>
        )}
      </div>
    </div>
  );
}

export default HealthDashboard;
