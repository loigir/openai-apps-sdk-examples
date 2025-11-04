import React from 'react';

/**
 * Alerts Panel Component
 * Displays active system alerts with severity indicators
 */
export const AlertsPanel = ({ alerts }) => {
  if (!alerts || alerts.length === 0) {
    return null;
  }

  const severityIcons = {
    critical: '🚨',
    warning: '⚠️',
    info: 'ℹ️',
  };

  const severityColors = {
    critical: '#ef4444',
    warning: '#f59e0b',
    info: '#3b82f6',
  };

  return (
    <section className="alerts-panel">
      <h2>Active Alerts</h2>
      <div className="alerts-list">
        {alerts.map((alert, index) => (
          <div
            key={index}
            className={`alert alert-${alert.severity}`}
            style={{ borderLeftColor: severityColors[alert.severity] }}
          >
            <div className="alert-header">
              <span className="alert-icon">{severityIcons[alert.severity]}</span>
              <span className="alert-type">{alert.type.replace(/_/g, ' ').toUpperCase()}</span>
              <span className="alert-time">{new Date(alert.timestamp).toLocaleTimeString()}</span>
            </div>
            <div className="alert-message">{alert.message}</div>
          </div>
        ))}
      </div>
    </section>
  );
};
