import React from 'react';

/**
 * Recent Errors List Component
 * Displays a chronological list of recent errors
 */
export const ErrorsList = ({ errors }) => {
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
              <tr key={index}>
                <td className="timestamp" title={timestamp.toLocaleString()}>
                  {timeAgo}
                </td>
                <td className="tool-name">
                  <code>{error.tool}</code>
                </td>
                <td className="error-message">{error.error}</td>
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
};

function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);

  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
