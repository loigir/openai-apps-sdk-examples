import React, { memo, useMemo } from 'react';
import { sanitizeText } from '../utils/sanitize';

// Constants moved outside component
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

/**
 * Alerts Panel Component
 * Displays active system alerts with severity indicators
 */
export const AlertsPanel = memo(function AlertsPanel({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return null;
  }

  return (
    <section className="alerts-panel">
      <h2>Active Alerts</h2>
      <div className="alerts-list">
        {alerts.map((alert) => (
          <div
            key={`${alert.timestamp}-${alert.type}`}
            className={`alert alert-${alert.severity}`}
            style={{ borderLeftColor: severityColors[alert.severity] }}
          >
            <div className="alert-header">
              <span className="alert-icon">{severityIcons[alert.severity]}</span>
              <span className="alert-type">{sanitizeText(alert.type).replace(/_/g, ' ').toUpperCase()}</span>
              <span className="alert-time">{new Date(alert.timestamp).toLocaleTimeString()}</span>
            </div>
            <div className="alert-message">{sanitizeText(alert.message)}</div>
          </div>
        ))}
      </div>
    </section>
  );
});
