import React, { memo } from 'react';

/**
 * Key Metrics Grid Component
 * Displays the most important metrics in a grid layout
 */
export const MetricsGrid = memo(function MetricsGrid({ data }) {
  return (
    <section className="metrics-grid">
      <div className="metric-card large">
        <div className="metric-icon">📊</div>
        <div className="metric-content">
          <div className="metric-label">Total Requests</div>
          <div className="metric-value">{data.total_requests.toLocaleString()}</div>
        </div>
      </div>

      <div className="metric-card large">
        <div className="metric-icon">⚡</div>
        <div className="metric-content">
          <div className="metric-label">Avg Latency</div>
          <div className={`metric-value ${data.overall_avg_latency_ms > 1000 ? 'warning' : ''}`}>
            {data.overall_avg_latency_ms.toFixed(0)}ms
          </div>
        </div>
      </div>

      <div className="metric-card large">
        <div className="metric-icon">❌</div>
        <div className="metric-content">
          <div className="metric-label">Error Rate</div>
          <div className={`metric-value ${data.overall_error_rate > 0.05 ? 'error' : ''}`}>
            {(data.overall_error_rate * 100).toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="metric-card large">
        <div className="metric-icon">🔌</div>
        <div className="metric-content">
          <div className="metric-label">Active Connections</div>
          <div className="metric-value">{data.active_connections}</div>
        </div>
      </div>
    </section>
  );
});
