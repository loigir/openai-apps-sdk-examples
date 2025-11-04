import React from 'react';

/**
 * Tool Usage Bar Chart Component
 * Displays tool call counts and average latency as horizontal bars
 */
export const ToolUsageChart = ({ tools }) => {
  if (!tools || tools.length === 0) {
    return <p className="no-data">No tool usage data available</p>;
  }

  const maxCallCount = Math.max(...tools.map(t => t.call_count));
  const maxLatency = Math.max(...tools.map(t => t.avg_latency_ms));

  return (
    <div className="tool-usage-chart">
      <div className="chart-header">
        <div className="chart-title">Tool Call Count</div>
        <div className="chart-title">Avg Latency (ms)</div>
      </div>

      {tools.map((tool, index) => {
        const callBarWidth = (tool.call_count / maxCallCount) * 100;
        const latencyBarWidth = (tool.avg_latency_ms / maxLatency) * 100;
        const latencyColor = tool.avg_latency_ms > 1000 ? '#ef4444' :
                            tool.avg_latency_ms > 500 ? '#f59e0b' : '#10b981';

        return (
          <div key={index} className="chart-row">
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
};
