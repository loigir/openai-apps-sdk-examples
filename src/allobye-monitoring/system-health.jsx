import React from 'react';

/**
 * System Health Status Component
 * Displays overall system health with color-coded indicators
 */
export const SystemHealth = ({ data }) => {
  const getHealthStatus = () => {
    if (data.overall_error_rate > 0.05) return 'unhealthy';
    if (data.overall_error_rate > 0.02 || data.overall_avg_latency_ms > 1000) return 'degraded';
    return 'healthy';
  };

  const status = getHealthStatus();
  const statusColors = {
    healthy: '#10b981',
    degraded: '#f59e0b',
    unhealthy: '#ef4444',
  };

  const statusLabels = {
    healthy: 'Healthy',
    degraded: 'Degraded',
    unhealthy: 'Unhealthy',
  };

  return (
    <section className="system-health">
      <div className="health-indicator">
        <div
          className={`health-status-circle ${status}`}
          style={{ backgroundColor: statusColors[status] }}
        ></div>
        <div className="health-text">
          <h2>System Status: <span className={status}>{statusLabels[status]}</span></h2>
          {status !== 'healthy' && (
            <p className="health-message">
              {status === 'degraded'
                ? 'System performance is degraded. Monitor for issues.'
                : 'System is experiencing critical issues. Immediate attention required.'}
            </p>
          )}
        </div>
      </div>
    </section>
  );
};
