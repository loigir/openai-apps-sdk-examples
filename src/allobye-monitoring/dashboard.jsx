import React, { useState, useEffect } from 'react';
import { ToolUsageChart } from './tool-usage-chart';
import { ErrorsList } from './errors-list';
import { MetricsGrid } from './metrics-grid';
import { AlertsPanel } from './alerts-panel';
import { SystemHealth } from './system-health';
import './dashboard.css';

/**
 * Real-time monitoring dashboard for AllôBye MCP server
 *
 * Displays:
 * - System health status
 * - Request metrics (total, error rate, latency)
 * - Tool usage analytics with bar charts
 * - Recent errors list
 * - Active alerts
 * - Database performance metrics
 */
const MonitoringDashboard = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [autoRefresh, setAutoRefresh] = useState(true);

  // Extract data from MCP tool response
  useEffect(() => {
    try {
      // In a real MCP widget, this data comes from the tool response _meta
      // For now, we'll check if it's available in window or use mock data
      const dashboardData = window.__ALLOBYE_MONITORING_DATA__ || getMockData();
      setData(dashboardData);
      setLoading(false);
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }, []);

  // Auto-refresh every 5 seconds if enabled
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      try {
        const dashboardData = window.__ALLOBYE_MONITORING_DATA__ || data;
        setData(dashboardData);
      } catch (err) {
        console.error('Auto-refresh error:', err);
      }
    }, 5000);

    return () => clearInterval(interval);
  }, [autoRefresh, data]);

  if (loading) {
    return (
      <div className="monitoring-dashboard loading">
        <div className="spinner"></div>
        <p>Loading monitoring data...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="monitoring-dashboard error">
        <h2>Error Loading Dashboard</h2>
        <p>{error}</p>
      </div>
    );
  }

  const uptimeHours = (data.uptime_seconds / 3600).toFixed(1);
  const uptimeDays = (data.uptime_seconds / 86400).toFixed(1);
  const displayUptime = uptimeDays >= 1 ? `${uptimeDays}d` : `${uptimeHours}h`;

  return (
    <div className="monitoring-dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-left">
          <h1>AllôBye Monitoring Dashboard</h1>
          <p className="subtitle">Real-time observability and performance metrics</p>
        </div>
        <div className="header-right">
          <label className="auto-refresh-toggle">
            <input
              type="checkbox"
              checked={autoRefresh}
              onChange={(e) => setAutoRefresh(e.target.checked)}
            />
            Auto-refresh (5s)
          </label>
          <div className="uptime-badge">
            Uptime: {displayUptime}
          </div>
        </div>
      </header>

      {/* System Health Status */}
      <SystemHealth data={data} />

      {/* Key Metrics Grid */}
      <MetricsGrid data={data} />

      {/* Tool Usage Analytics */}
      <section className="dashboard-section">
        <h2>Tool Usage Analytics</h2>
        <ToolUsageChart tools={data.top_tools} />
      </section>

      {/* Active Alerts */}
      {data.alerts && data.alerts.length > 0 && (
        <AlertsPanel alerts={data.alerts} />
      )}

      {/* Recent Errors */}
      <section className="dashboard-section">
        <h2>Recent Errors</h2>
        <ErrorsList errors={data.recent_errors} />
      </section>

      {/* Database Metrics */}
      <section className="dashboard-section database-metrics">
        <h2>Database Performance</h2>
        <div className="metrics-row">
          <div className="metric-card">
            <div className="metric-label">Total Queries</div>
            <div className="metric-value">{data.database.query_count}</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Avg Query Time</div>
            <div className="metric-value">{data.database.avg_latency_ms.toFixed(0)}ms</div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Error Rate</div>
            <div className={`metric-value ${data.database.error_rate > 0.05 ? 'warning' : ''}`}>
              {(data.database.error_rate * 100).toFixed(1)}%
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-label">Consecutive Failures</div>
            <div className={`metric-value ${data.database.consecutive_failures > 0 ? 'error' : ''}`}>
              {data.database.consecutive_failures}
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="dashboard-footer">
        <p>Last updated: {new Date().toLocaleTimeString()}</p>
        <p>Total Requests: {data.total_requests} | Active Connections: {data.active_connections}</p>
      </footer>
    </div>
  );
};

// Mock data for development/testing
function getMockData() {
  return {
    uptime_seconds: 3600,
    total_requests: 1234,
    active_connections: 5,
    overall_error_rate: 0.02,
    overall_avg_latency_ms: 245,
    top_tools: [
      { name: 'pickup-schedule-create', call_count: 456, avg_latency_ms: 312, error_rate: 0.01 },
      { name: 'school-dashboard-fetch', call_count: 234, avg_latency_ms: 189, error_rate: 0.0 },
      { name: 'delegate-authorize', call_count: 123, avg_latency_ms: 267, error_rate: 0.03 },
      { name: 'emergency-declare', call_count: 45, avg_latency_ms: 523, error_rate: 0.0 },
      { name: 'monitoring-dashboard-fetch', call_count: 12, avg_latency_ms: 98, error_rate: 0.0 },
    ],
    recent_errors: [
      {
        timestamp: new Date().toISOString(),
        tool: 'pickup-schedule-create',
        error: 'Database connection timeout',
        latency_ms: 5023,
      },
      {
        timestamp: new Date(Date.now() - 300000).toISOString(),
        tool: 'delegate-authorize',
        error: 'Validation error: Invalid child ID',
        latency_ms: 45,
      },
    ],
    alerts: [
      {
        timestamp: new Date().toISOString(),
        type: 'latency_high',
        severity: 'warning',
        message: 'Tool pickup-schedule-create latency 1523ms exceeds threshold 1000ms',
      },
    ],
    database: {
      query_count: 5678,
      error_count: 12,
      avg_latency_ms: 34.5,
      error_rate: 0.002,
      consecutive_failures: 0,
    },
    tool_details: {},
  };
}

export default MonitoringDashboard;
