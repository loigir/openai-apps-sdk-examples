# Monitoring System Quick Start Guide

## Installation

No additional dependencies are required! The monitoring system uses only Python standard library components.

## Basic Usage

### 1. Start the Server with Monitoring

```bash
cd allobye_server_python
python main.py
```

The monitoring system is automatically initialized on startup.

### 2. Make Some API Calls

```bash
# Example: Call the monitoring dashboard tool
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "monitoring-dashboard-fetch",
      "arguments": {
        "includeDetails": true
      }
    }
  }'
```

### 3. Check System Health

```bash
curl http://localhost:8000/health | jq .
```

Expected output:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-04T12:34:56.789Z",
  "uptime_seconds": 120.5,
  "service": "allobye-mcp-server",
  "environment": "production",
  "checks": {
    "api": "healthy",
    "database": "healthy"
  },
  "issues": [],
  "metrics": {
    "total_requests": 5,
    "active_connections": 0,
    "error_rate": 0.0,
    "avg_latency_ms": 123.4
  }
}
```

### 4. View Prometheus Metrics

```bash
curl http://localhost:8000/metrics
```

Sample output:
```
# HELP allobye_uptime_seconds Server uptime in seconds
# TYPE allobye_uptime_seconds gauge
allobye_uptime_seconds 120.50

# HELP allobye_requests_total Total number of requests
# TYPE allobye_requests_total counter
allobye_requests_total 5

# HELP allobye_tool_calls_total Total calls for tool monitoring-dashboard-fetch
# TYPE allobye_tool_calls_total counter
allobye_tool_calls_total{tool="monitoring-dashboard-fetch"} 1
```

### 5. Access the Monitoring Dashboard Widget

The monitoring dashboard is accessible as an MCP tool that returns a React widget:

```javascript
// In ChatGPT or MCP client
{
  "tool": "monitoring-dashboard-fetch",
  "arguments": {
    "includeDetails": true
  }
}
```

This displays a fullscreen dashboard with:
- Real-time system health indicator
- Key metrics (requests, latency, error rate)
- Tool usage bar charts
- Recent errors table
- Active alerts
- Database performance metrics

## Monitoring in Action

### Example 1: Tracking Tool Performance

```python
from monitoring import get_metrics

# Get metrics collector
metrics = get_metrics()

# Get tool performance stats
dashboard_data = metrics.get_dashboard_data()

print(f"Total Requests: {dashboard_data['total_requests']}")
print(f"Error Rate: {dashboard_data['overall_error_rate']:.2%}")
print(f"Avg Latency: {dashboard_data['overall_avg_latency_ms']:.0f}ms")

# Get top 5 most-used tools
top_tools = dashboard_data['top_tools']
for tool in top_tools:
    print(f"{tool['name']}: {tool['call_count']} calls, {tool['avg_latency_ms']:.0f}ms avg")
```

### Example 2: Viewing Recent Errors

```python
from monitoring import get_metrics

metrics = get_metrics()
dashboard_data = metrics.get_dashboard_data()

print("Recent Errors:")
for error in dashboard_data['recent_errors'][:5]:
    print(f"[{error['timestamp']}] {error['tool']}: {error['error']}")
```

### Example 3: Checking Alerts

```python
from monitoring import get_metrics

metrics = get_metrics()
alerts = metrics.get_alerts()

if alerts:
    print(f"Active Alerts: {len(alerts)}")
    for alert in alerts:
        print(f"[{alert['severity'].upper()}] {alert['message']}")
else:
    print("No active alerts")
```

### Example 4: Custom Logging

```python
from monitoring import get_logger

logger = get_logger()

# Log various levels
logger.debug("Detailed debug information", request_id="123")
logger.info("User action completed", user_id="user_456", action="create_pickup")
logger.warning("Potential issue detected", latency_ms=1234)
logger.error("Operation failed", error="Database timeout", query="SELECT * FROM pickups")
```

### Example 5: Monitoring Database Operations

```python
from monitoring import get_middleware

middleware = get_middleware()

# Monitor a database query
async def fetch_data():
    with middleware.monitor_db_query("fetch_user_data"):
        # Your database query here
        result = await db.query("SELECT * FROM users WHERE id = ?", user_id)
        return result
```

## Viewing Logs

All logs are output in JSON format to stdout. To view structured logs:

```bash
# View all logs
python main.py 2>&1 | jq .

# Filter by log level
python main.py 2>&1 | jq 'select(.level == "ERROR")'

# Filter by tool
python main.py 2>&1 | jq 'select(.tool == "pickup-schedule-create")'

# View only errors with latency > 1000ms
python main.py 2>&1 | jq 'select(.level == "ERROR" and .latency_ms > 1000)'
```

## Setting Up Continuous Monitoring

### Option 1: Simple Shell Script

Create `monitor.sh`:

```bash
#!/bin/bash

while true; do
  echo "=== $(date) ==="
  curl -s http://localhost:8000/health | jq '{
    status: .status,
    uptime_hours: (.uptime_seconds / 3600 | floor),
    requests: .metrics.total_requests,
    error_rate: (.metrics.error_rate * 100 | floor),
    latency: .metrics.avg_latency_ms
  }'
  echo ""
  sleep 60
done
```

Run it:
```bash
chmod +x monitor.sh
./monitor.sh
```

### Option 2: Prometheus + Grafana

1. Install Prometheus and Grafana (via Docker):

```bash
# Create docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3'
services:
  prometheus:
    image: prom/prometheus:latest
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
EOF

# Create prometheus.yml
cat > prometheus.yml << 'EOF'
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'allobye'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: '/metrics'
EOF

# Start services
docker-compose up -d
```

2. Access Grafana at http://localhost:3000 (admin/admin)
3. Add Prometheus data source (http://prometheus:9090)
4. Create dashboard with queries:
   - Request Rate: `rate(allobye_requests_total[5m])`
   - Error Rate: `rate(allobye_tool_errors_total[5m]) / rate(allobye_tool_calls_total[5m])`
   - Latency: `allobye_tool_latency_ms`

## Testing the Monitoring System

Run the included test script:

```bash
python test_monitoring.py
```

This will:
1. Make several tool calls
2. Simulate some errors
3. Check metrics collection
4. Verify alerting rules
5. Export Prometheus metrics

## Common Tasks

### Reset Metrics

Restart the server:
```bash
# Press Ctrl+C to stop
# Then restart
python main.py
```

### Change Log Level

Set environment variable:
```bash
LOG_LEVEL=DEBUG python main.py
```

### Disable Alerts

```python
from monitoring import configure_monitoring, AlertingConfig

configure_monitoring(
    alerting=AlertingConfig(enable_alerts=False)
)
```

### Export Metrics to File

```bash
curl http://localhost:8000/metrics > metrics_$(date +%Y%m%d_%H%M%S).txt
```

## Troubleshooting

### Metrics Endpoint Returns 404

Make sure you're using the monitored version of main.py:
```bash
grep "monitoring" allobye_server_python/main.py
```

### No Logs Appearing

Check log level:
```bash
LOG_LEVEL=DEBUG python main.py
```

### Dashboard Shows No Data

Ensure you've made some tool calls first:
```bash
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "monitoring-dashboard-fetch",
      "arguments": {"includeDetails": true}
    }
  }'
```

## Next Steps

1. **Read the full documentation**: [MONITORING.md](./MONITORING.md)
2. **Integrate with external tools**: Set up Prometheus, Grafana, or ELK
3. **Customize alerting**: Adjust thresholds in `MonitoringConfig`
4. **Add custom metrics**: Extend the monitoring system for your needs
5. **Set up dashboards**: Create visualizations for your key metrics

## Resources

- [Full Monitoring Documentation](./MONITORING.md)
- [Monitoring Module Source](./monitoring.py)
- [Main Server with Monitoring](./main.py)
- [React Dashboard Widget](../src/allobye-monitoring/)
