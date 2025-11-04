import React, { memo, useMemo } from 'react';

// Helper function moved outside component
const getLatencyColor = (latency) => {
  if (latency > 1000) return '#ef4444';
  if (latency > 500) return '#f59e0b';
  return '#10b981';
};

/**
 * Tool Usage Bar Chart Component
 * Displays tool call counts and average latency as horizontal bars
 */
export const ToolUsageChart = memo(function ToolUsageChart({ tools }) {
  if (!tools || tools.length === 0) {
    return <p className="no-data">No tool usage data available</p>;
  }

  const maxCallCount = useMemo(() => Math.max(...tools.map(t => t.call_count)), [tools]);
  const maxLatency = useMemo(() => Math.max(...tools.map(t => t.avg_latency_ms)), [tools]);

  return (
    <div className="tool-usage-chart">
      <div className="chart-header">
        <div className="chart-title">Tool Call Count</div>
        <div className="chart-title">Avg Latency (ms)</div>
      </div>

      {tools.map((tool) => {
        const callBarWidth = (tool.call_count / maxCallCount) * 100;
        const latencyBarWidth = (tool.avg_latency_ms / maxLatency) * 100;
        const latencyColor = getLatencyColor(tool.avg_latency_ms);

        return (
          <div key={tool.name} className="chart-row">
            <div className="tool-name">{tool.name}</div>

            <div className="bar-container">
              <div
                className="bar call-count-bar"
                style={{ width: `${callBarWidth}%` }}
              >
                <span className="bar-label">{tool.call_count}</span>
              </div>
            </div>

            <div className="bar-container">
              <div
                className="bar latency-bar"
                style={{
                  width: `${latencyBarWidth}%`,
                  backgroundColor: latencyColor
                }}
              >
                <span className="bar-label">{tool.avg_latency_ms.toFixed(0)}ms</span>
              </div>
            </div>

            <div className="tool-stats">
              <span className={`error-rate ${tool.error_rate > 0.05 ? 'high' : ''}`}>
                {(tool.error_rate * 100).toFixed(1)}% errors
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
});
