import React, { memo } from 'react';
import { sanitizeText } from '../utils/sanitize';

// Helper function moved outside component
function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);

  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

/**
 * Recent Errors List Component
 * Displays a chronological list of recent errors
 */
export const ErrorsList = memo(function ErrorsList({ errors }) {
  if (!errors || errors.length === 0) {
    return (
      <div className="no-errors">
        <p>✅ No recent errors</p>
      </div>
    );
  }

  return (
    <div className="errors-list">
      <table className="errors-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Tool</th>
            <th>Error</th>
            <th>Latency</th>
          </tr>
        </thead>
        <tbody>
          {errors.map((error, index) => {
            const timestamp = new Date(error.timestamp);
            const timeAgo = getTimeAgo(timestamp);

            return (
              <tr key={`${error.timestamp}-${error.tool}`}>
                <td className="timestamp" title={timestamp.toLocaleString()}>
                  {timeAgo}
                </td>
                <td className="tool-name">
                  <code>{sanitizeText(error.tool)}</code>
                </td>
                <td className="error-message">{sanitizeText(error.error)}</td>
                <td className="latency">
                  {error.latency_ms.toFixed(0)}ms
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
});
