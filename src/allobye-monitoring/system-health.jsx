import React, { memo, useMemo } from 'react';

// Constants moved outside component
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

const getHealthStatus = (errorRate, avgLatency) => {
  if (errorRate > 0.05) return 'unhealthy';
  if (errorRate > 0.02 || avgLatency > 1000) return 'degraded';
  return 'healthy';
};

/**
 * System Health Status Component
 * Displays overall system health with color-coded indicators
 */
export const SystemHealth = memo(function SystemHealth({ data }) {
  const status = useMemo(
    () => getHealthStatus(data.overall_error_rate, data.overall_avg_latency_ms),
    [data.overall_error_rate, data.overall_avg_latency_ms]
  );

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
});
