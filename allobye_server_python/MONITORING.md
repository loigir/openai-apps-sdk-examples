# AllôBye MCP Server - Observability & Monitoring Documentation

## Overview

The AllôBye MCP server includes a comprehensive observability and monitoring system that provides real-time insights into server performance, request patterns, error tracking, and system health.

## Architecture

The monitoring system consists of the following components:

### 1. Monitoring Module (`monitoring.py`)
Core monitoring infrastructure including:
- **Structured Logging**: JSON-formatted logs with contextual fields
- **Metrics Collection**: Performance metrics, tool usage analytics, error tracking
- **Request Tracing**: Correlation IDs for tracking requests across operations
- **Database Monitoring**: Query performance and error tracking
- **Alerting**: Threshold-based alerting for critical issues
- **Prometheus Export**: Metrics in Prometheus format

### 2. MCP Integration (`main.py`)
- Tool call monitoring middleware
- Health check endpoint (`/health`)
- Metrics endpoint (`/metrics`)
- Database query performance tracking

### 3. React Monitoring Widget
Real-time dashboard for visualizing:
- System health status
- Request metrics (total, error rate, latency)
- Tool usage analytics with bar charts
- Recent errors list
- Active alerts
- Database performance metrics

## Features

### Structured Logging

All logs are output in JSON format with the following fields:

```json
{
  "timestamp": "2025-11-04T12:34:56.789Z",
  "level": "INFO",
  "service": "allobye-mcp-server",
  "environment": "production",
  "message": "Tool call started",
  "tool": "pickup-schedule-create",
  "trace_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Log Levels:**
- `DEBUG`: Detailed diagnostic information
- `INFO`: General informational messages
- `WARNING`: Warning messages for potentially harmful situations
- `ERROR`: Error events that might still allow the app to continue
- `CRITICAL`: Very severe error events

### Metrics Collection

The following metrics are automatically collected:

#### Tool Metrics
- **Call Count**: Total number of calls per tool
- **Success/Error Count**: Number of successful and failed calls
- **Latency**: Min, max, average, and total latency per tool
- **Error Rate**: Percentage of failed calls

#### Database Metrics
- **Query Count**: Total number of database queries
- **Query Latency**: Average query execution time
- **Error Rate**: Percentage of failed queries
- **Consecutive Failures**: Number of consecutive database failures

#### System Metrics
- **Uptime**: Server uptime in seconds
- **Total Requests**: Cumulative request count
- **Active Connections**: Current number of active connections
- **Overall Error Rate**: Global error rate across all tools
- **Overall Latency**: Global average latency

### Request Tracing

Every request is assigned a unique trace ID that follows the request through:
- Tool invocation
- Database queries
- Error handling
- Response generation

Trace IDs appear in all logs for that request, enabling end-to-end request tracking.

### Alerting Rules

Alerts are automatically triggered when:

1. **High Error Rate**
   - Threshold: 5%
   - Severity: WARNING
   - Triggered when a tool's error rate exceeds 5%

2. **High Latency**
   - Threshold: 1000ms
   - Severity: WARNING
   - Triggered when a tool call exceeds 1 second

3. **Database Failures**
   - Threshold: 3 consecutive failures
   - Severity: CRITICAL
   - Triggered after 3 consecutive database query failures

## Usage

### Accessing Metrics

#### Health Check Endpoint

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2025-11-04T12:34:56.789Z",
  "uptime_seconds": 3600,
  "service": "allobye-mcp-server",
  "environment": "production",
  "checks": {
    "api": "healthy",
    "database": "healthy"
  },
  "issues": [],
  "metrics": {
    "total_requests": 1234,
    "active_connections": 5,
    "error_rate": 0.02,
    "avg_latency_ms": 245
  }
}
```

#### Prometheus Metrics Endpoint

```bash
curl http://localhost:8000/metrics
```

Response (Prometheus format):
```
# HELP allobye_uptime_seconds Server uptime in seconds
# TYPE allobye_uptime_seconds gauge
allobye_uptime_seconds 3600.00

# HELP allobye_requests_total Total number of requests
# TYPE allobye_requests_total counter
allobye_requests_total 1234

# HELP allobye_tool_calls_total Total calls for tool pickup-schedule-create
# TYPE allobye_tool_calls_total counter
allobye_tool_calls_total{tool="pickup-schedule-create"} 456

# ... more metrics
```

### Monitoring Dashboard Tool

Access the monitoring dashboard through the MCP tool:

```json
{
  "tool": "monitoring-dashboard-fetch",
  "arguments": {
    "includeDetails": true
  }
}
```

This returns a React widget displaying:
- Real-time system health
- Key performance metrics
- Tool usage bar charts
- Recent errors
- Active alerts
- Database performance

### Programmatic Access

```python
from monitoring import get_metrics, get_logger, get_health_status

# Get metrics collector
metrics = get_metrics()

# Access dashboard data
dashboard_data = metrics.get_dashboard_data()

# Get top tools by usage
top_tools = metrics.get_top_tools(limit=5)

# Get recent alerts
alerts = metrics.get_alerts()

# Get health status
health = get_health_status()

# Use structured logger
logger = get_logger()
logger.info("Custom log message", custom_field="value")
```

## Configuration

### Environment Variables

```bash
# Set environment (default: production)
ENVIRONMENT=production

# Set log level (default: INFO)
# Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL=INFO
```

### Monitoring Configuration

```python
from monitoring import configure_monitoring, AlertingConfig

# Configure monitoring
configure_monitoring(
    service_name="allobye-mcp-server",
    environment="staging",
    log_level="DEBUG",
    enable_tracing=True,
    enable_metrics=True,
    alerting=AlertingConfig(
        error_rate_threshold=0.03,  # 3% instead of default 5%
        latency_threshold_ms=500.0,  # 500ms instead of default 1000ms
        db_failure_threshold=5,      # 5 consecutive failures instead of 3
        enable_alerts=True
    )
)
```

## Common Monitoring Scenarios

### 1. Investigating High Latency

```bash
# Check metrics endpoint
curl http://localhost:8000/metrics | grep latency

# View tool-specific latency
curl http://localhost:8000/metrics | grep "allobye_tool_latency_ms"
```

Check logs:
```bash
# Filter for high latency requests (assuming JSON logs)
grep '"latency_ms"' logs.json | jq 'select(.latency_ms > 1000)'
```

### 2. Tracking Error Rates

```bash
# Check health endpoint
curl http://localhost:8000/health | jq '.metrics.error_rate'

# Get error count per tool
curl http://localhost:8000/metrics | grep "allobye_tool_errors_total"
```

View recent errors in logs:
```bash
grep '"level":"ERROR"' logs.json | tail -20 | jq .
```

### 3. Database Performance Issues

```bash
# Check database metrics
curl http://localhost:8000/health | jq '.checks.database'

# View database query metrics
curl http://localhost:8000/metrics | grep "allobye_db"
```

Filter database errors:
```bash
grep 'monitor_db_query' logs.json | grep '"success":false' | jq .
```

### 4. Tracing a Specific Request

Find logs for a specific trace ID:
```bash
grep '"trace_id":"a1b2c3d4-e5f6-7890-abcd-ef1234567890"' logs.json | jq .
```

### 5. Monitoring System Health Over Time

```bash
# Scrape metrics every 60 seconds
while true; do
  curl -s http://localhost:8000/health | jq '{
    timestamp: .timestamp,
    uptime: .uptime_seconds,
    requests: .metrics.total_requests,
    error_rate: .metrics.error_rate,
    latency: .metrics.avg_latency_ms
  }'
  sleep 60
done
```

## Integration with External Tools

### Prometheus

Add to `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'allobye-mcp'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### Grafana

Create dashboards using Prometheus data source:

**Key Metrics:**
- `allobye_uptime_seconds`
- `allobye_requests_total`
- `rate(allobye_tool_calls_total[5m])`
- `allobye_tool_latency_ms`
- `allobye_db_latency_ms`

**Example PromQL Queries:**
```promql
# Request rate (requests per second)
rate(allobye_requests_total[5m])

# Average latency by tool
avg by (tool) (allobye_tool_latency_ms)

# Error rate
rate(allobye_tool_errors_total[5m]) / rate(allobye_tool_calls_total[5m])

# Database query latency
allobye_db_latency_ms
```

### ELK Stack (Elasticsearch, Logstash, Kibana)

**Logstash Configuration:**

```ruby
input {
  file {
    path => "/var/log/allobye/app.log"
    codec => "json"
  }
}

filter {
  if [service] == "allobye-mcp-server" {
    mutate {
      add_field => { "[@metadata][index]" => "allobye-logs" }
    }
  }
}

output {
  elasticsearch {
    hosts => ["localhost:9200"]
    index => "%{[@metadata][index]}-%{+YYYY.MM.dd}"
  }
}
```

### Datadog

Use the Datadog agent with custom metrics:

```python
from datadog import statsd

# Send metrics to Datadog
statsd.increment('allobye.tool.calls', tags=['tool:pickup-schedule-create'])
statsd.histogram('allobye.tool.latency', 245, tags=['tool:pickup-schedule-create'])
```

## Best Practices

1. **Set Appropriate Log Levels**
   - Use `DEBUG` in development
   - Use `INFO` or `WARNING` in production
   - Use `ERROR` for exceptions and failures

2. **Monitor Key Metrics**
   - Error rate (should be < 1%)
   - Average latency (should be < 500ms)
   - Database query performance
   - System uptime

3. **Set Up Alerts**
   - Configure alerts for critical thresholds
   - Use escalation policies for severe issues
   - Test alerting rules regularly

4. **Review Logs Regularly**
   - Check error logs daily
   - Investigate latency spikes
   - Monitor database query patterns

5. **Use Tracing for Debugging**
   - Always include trace IDs in error reports
   - Use trace IDs to correlate logs across systems
   - Keep trace data for at least 7 days

## Troubleshooting

### High Memory Usage

```python
# Check metrics collector memory usage
import sys
metrics = get_metrics()
print(f"Recent requests: {sys.getsizeof(metrics.recent_requests)}")
print(f"Recent errors: {sys.getsizeof(metrics.recent_errors)}")
print(f"Alerts: {sys.getsizeof(metrics._alerts)}")
```

**Solution:** Reduce retention limits in `MonitoringConfig`:
```python
configure_monitoring(metrics_retention_seconds=1800)  # 30 minutes instead of 1 hour
```

### Missing Metrics

Ensure monitoring is initialized:
```python
from monitoring import initialize_monitoring
initialize_monitoring()
```

### Health Check Returns 503

Check the health status details:
```bash
curl http://localhost:8000/health | jq '.issues'
```

Common causes:
- High error rate (> 5%)
- Database connection failures
- System resource exhaustion

## Performance Impact

The monitoring system is designed to have minimal performance overhead:

- **Latency overhead**: < 1ms per request
- **Memory usage**: ~50-100MB for metrics storage
- **CPU usage**: < 1% additional CPU load

## Security Considerations

1. **Metrics Endpoint**: Exposes performance data but not sensitive information
2. **Health Endpoint**: Provides system status without exposing credentials
3. **Logs**: May contain request arguments - ensure PII is not logged
4. **Access Control**: Consider adding authentication for metrics/health endpoints in production

## Future Enhancements

Potential future additions:
- OpenTelemetry integration for distributed tracing
- Custom metric types (histograms, summaries)
- Advanced anomaly detection
- Integration with PagerDuty/Slack for alerting
- Real-time streaming metrics dashboard
- Long-term metrics storage and analysis

## Support

For issues or questions about the monitoring system:
1. Check this documentation
2. Review the source code in `monitoring.py`
3. Check logs for error messages
4. Consult the health check endpoint

## References

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [OpenTelemetry](https://opentelemetry.io/)
- [Structured Logging Best Practices](https://www.datadoghq.com/blog/python-logging-best-practices/)
