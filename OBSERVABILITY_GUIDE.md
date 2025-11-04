# AllôBye MCP Server - Observability Guide

**Complete guide to monitoring, logging, tracing, and alerting for the AllôBye MCP Server**

---

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Structured Logging](#structured-logging)
4. [Distributed Tracing](#distributed-tracing)
5. [Metrics & Monitoring](#metrics--monitoring)
6. [Health Checks](#health-checks)
7. [Alerting](#alerting)
8. [Dashboards](#dashboards)
9. [Troubleshooting](#troubleshooting)
10. [Best Practices](#best-practices)

---

## Overview

The AllôBye MCP Server implements comprehensive observability to ensure:

- **Visibility**: Track every request end-to-end with correlation IDs
- **Performance**: Monitor latency, throughput, and resource utilization
- **Reliability**: Detect and alert on failures before they impact users
- **Business Insights**: Track key business metrics (pickups, emergencies, delegates)
- **Security**: Monitor for suspicious patterns and attacks

### Key Features

- ✅ Structured JSON logging with correlation IDs
- ✅ Distributed tracing with span tracking
- ✅ Prometheus-compatible metrics export
- ✅ Business and technical metrics
- ✅ Multi-dimensional metric labels
- ✅ Comprehensive health checks
- ✅ Automated alerting with runbooks
- ✅ Real-time monitoring dashboards

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Application Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   MCP Tools  │  │  Auth Module │  │  Database    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Observability Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Logging    │  │   Tracing    │  │   Metrics    │      │
│  │  (JSON logs) │  │ (Correlation │  │ (Prometheus) │      │
│  └──────────────┘  │     IDs)     │  └──────────────┘      │
│                    └──────────────┘                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Health Checks│  │   Alerting   │  │  Dashboards  │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Collection Layer                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │  Log Aggr.   │  │  Prometheus  │  │   Grafana    │      │
│  │ (ELK/Cloud)  │  │   Server     │  │  Dashboard   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
```

---

## Structured Logging

### Overview

All logs are structured as JSON with consistent fields for easy parsing and analysis.

### Log Structure

Every log entry includes:

```json
{
  "timestamp": "2025-11-04T15:30:45.123Z",
  "level": "INFO",
  "service": "allobye-mcp-server",
  "environment": "production",
  "message": "Tool call completed",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "trace_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "span_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "tool": "pickup-schedule-create",
  "duration_ms": 234.5,
  "success": true,
  "user_id": "user_123",
  "school_id": "school_456"
}
```

### Correlation IDs

**Every request gets a unique correlation ID** that tracks it through the entire system.

#### Using Correlation IDs

```python
from logging_config import (
    correlation_context,
    get_correlation_id,
    get_logger
)

logger = get_logger(__name__)

# Automatic correlation ID generation
with correlation_context(user_id="user_123") as correlation_id:
    logger.info("Processing request")
    # All logs here will have the same correlation_id
    process_data()
    logger.info("Request completed")
```

### Logging Scopes

Use logging scopes for operations that need timing:

```python
from logging_config import logging_scope, get_logger

logger = get_logger(__name__)

with logging_scope("database_query", table="pickups") as ctx:
    # Perform database query
    results = fetch_pickups()
    ctx["rows_fetched"] = len(results)
    # Automatically logs duration and context
```

### Log Levels

- **DEBUG**: Detailed debugging information
- **INFO**: General informational messages
- **WARNING**: Warning messages for potential issues
- **ERROR**: Error messages for failures
- **CRITICAL**: Critical failures requiring immediate attention

### Searching Logs

#### Find all requests for a user

```bash
grep '"user_id": "user_123"' logs/*.json
```

#### Find all errors for a specific tool

```bash
jq 'select(.tool == "pickup-schedule-create" and .level == "ERROR")' logs/*.json
```

#### Track a request end-to-end

```bash
jq 'select(.correlation_id == "a1b2c3d4-e5f6-7890")' logs/*.json
```

---

## Distributed Tracing

### Overview

Distributed tracing tracks requests across multiple operations and services using trace IDs and span IDs.

### Trace Structure

```
Request (trace_id: abc123)
├── Span: validate_auth (span_id: def456, parent: none)
│   └── Duration: 45ms
├── Span: database_query (span_id: ghi789, parent: def456)
│   └── Duration: 120ms
└── Span: send_notification (span_id: jkl012, parent: def456)
    └── Duration: 89ms
```

### Using Trace Context

```python
from logging_config import trace_context, get_logger

logger = get_logger(__name__)

# Create a new trace
with trace_context(span_name="process_pickup") as trace_info:
    trace_id = trace_info["trace_id"]
    span_id = trace_info["span_id"]

    # Nested span
    with trace_context(span_name="validate_permissions") as nested_trace:
        # This span has parent_span_id set
        validate_user_permissions()

    # Another nested span
    with trace_context(span_name="create_pickup_record") as nested_trace:
        create_pickup()
```

### Trace Propagation

When making external calls, propagate trace context:

```python
headers = {
    "X-Trace-Id": get_trace_id(),
    "X-Span-Id": get_span_id(),
    "X-Correlation-Id": get_correlation_id(),
}

response = requests.post(external_api, headers=headers)
```

---

## Metrics & Monitoring

### Prometheus Metrics

All metrics are exported in Prometheus format at `/metrics` endpoint.

### Metric Types

#### Counters (Monotonic Increasing)

- `allobye_requests_total`: Total requests
- `allobye_tool_calls_total{tool="..."}`: Tool call count
- `allobye_pickups_created_total`: Pickups created
- `allobye_emergencies_declared_total`: Emergencies declared

#### Gauges (Can Increase or Decrease)

- `allobye_active_connections`: Current active connections
- `allobye_active_sessions`: Current user sessions
- `allobye_cache_size_bytes`: Cache size
- `allobye_uptime_seconds`: Server uptime

#### Histograms (Distribution of Values)

- `allobye_tool_latency_ms{tool="...",quantile="..."}`: Latency percentiles
  - `quantile="avg"`: Average latency
  - `quantile="0.50"`: Median (P50)
  - `quantile="0.95"`: 95th percentile (P95)
  - `quantile="0.99"`: 99th percentile (P99)

### Business Metrics

Track key business events:

```python
from monitoring import get_metrics

metrics = get_metrics()

# Record business events
metrics.record_business_event(
    "pickup_created",
    labels={"school": "school_123", "role": "parent"}
)

metrics.record_business_event(
    "emergency_declared",
    labels={"emergency_type": "late", "school": "school_123"}
)

metrics.record_business_event("parent_login")
metrics.record_business_event("staff_login")
```

### Multi-Dimensional Labels

Use labels for filtering and aggregation:

```python
# Record tool call with labels
metrics.record_tool_call(
    tool_name="pickup-schedule-create",
    latency_ms=234.5,
    success=True,
    labels={
        "school": "school_123",
        "role": "parent",
        "pickup_type": "single"
    }
)
```

### Querying Metrics

#### PromQL Examples

```promql
# Request rate (requests per second)
rate(allobye_requests_total[5m])

# Error rate by tool
rate(allobye_tool_errors_total[5m]) / rate(allobye_tool_calls_total[5m])

# 95th percentile latency for pickup scheduling
allobye_tool_latency_ms{tool="pickup-schedule-create",quantile="0.95"}

# Total pickups created per school (using labels)
sum(allobye_pickups_created_total) by (school)

# Cache hit rate
allobye_cache_hits_total / (allobye_cache_hits_total + allobye_cache_misses_total)
```

---

## Health Checks

### Endpoint

```
GET /health
```

### Response Format

```json
{
  "status": "healthy",
  "timestamp": "2025-11-04T15:30:45.123Z",
  "total_check_duration_ms": 145.8,
  "service": "allobye-mcp-server",
  "version": "1.0.0",
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connectivity OK",
      "latency_ms": 23.4,
      "timestamp": "2025-11-04T15:30:45.100Z",
      "details": {"latency_ms": 23.4}
    },
    "supabase_api": {
      "status": "healthy",
      "message": "Supabase API responding",
      "latency_ms": 67.2,
      "timestamp": "2025-11-04T15:30:45.120Z",
      "details": {"status_code": 200}
    },
    "cache": {
      "status": "healthy",
      "message": "Cache operational",
      "latency_ms": 1.2
    },
    "monitoring": {
      "status": "healthy",
      "message": "Monitoring system operational",
      "latency_ms": 0.5
    },
    "authentication": {
      "status": "healthy",
      "message": "Authentication system configured",
      "latency_ms": 0.3
    }
  },
  "metrics": {
    "uptime_seconds": 3600,
    "total_requests": 1234,
    "active_connections": 5,
    "error_rate": 0.02,
    "avg_latency_ms": 234.5
  }
}
```

### Health Status Levels

- **healthy**: All systems operational
- **degraded**: Some systems slow but functional
- **unhealthy**: Critical failures detected

### Monitoring Health Checks

```bash
# Check health
curl http://localhost:8000/health

# Check specific component (using jq)
curl -s http://localhost:8000/health | jq '.components.database'

# Alert if unhealthy
curl -s http://localhost:8000/health | jq -e '.status == "healthy"' || alert
```

---

## Alerting

### Alert Configuration

Alerts are defined in `alerts.yml`:

```yaml
alerts:
  - name: high_error_rate
    severity: warning
    condition:
      metric: error_rate
      operator: greater_than
      threshold: 0.05
      duration: 300
    response_procedure: |
      1. Check recent error logs
      2. Identify failing tools
      3. Check database connectivity
```

### Alert Severity Levels

- **info**: Informational, no action needed
- **warning**: Potential issue, monitor closely
- **error**: Issue requiring attention
- **critical**: Immediate action required

### Common Alerts

#### High Error Rate

**Trigger**: Error rate > 5% for 5 minutes

**Response**:
1. Check monitoring dashboard
2. Review error logs
3. Check database and API status
4. Investigate recent changes

#### Database Connectivity Failure

**Trigger**: 3 consecutive database failures

**Response**:
1. Check database server status
2. Verify network connectivity
3. Check connection pool
4. Verify credentials
5. Escalate if unresolved

#### Emergency Notification Failure

**Trigger**: Emergency notifications failing

**Response**:
1. **CRITICAL**: Immediate action required
2. Verify emergency tool functionality
3. Check notification system
4. Manual notification may be required
5. Escalate immediately

### Alert Destinations

Alerts can be sent to:

- **Logs**: All alerts logged to monitoring system
- **Prometheus**: Metrics include alert counts
- **Email**: (Future) Email notifications
- **Slack**: (Future) Slack webhook integration
- **PagerDuty**: (Future) On-call escalation

---

## Dashboards

### Monitoring Dashboard

Access the monitoring dashboard:

```
MCP Tool: monitoring-dashboard-fetch
Widget: allobye-monitoring.html
```

### Dashboard Sections

#### 1. Overview

- Uptime
- Total requests
- Active connections
- Error rate
- Average latency

#### 2. Tool Metrics

- Calls per tool
- Success/error rates
- Latency distributions
- Top tools by usage

#### 3. Business Metrics

- Pickups created/completed
- Emergencies declared
- Delegates authorized
- User logins (parents vs staff)

#### 4. Database Performance

- Query count
- Error rate
- Average latency
- Slow queries

#### 5. Recent Activity

- Recent requests (last 50)
- Recent errors (last 20)
- Active alerts

### Custom Dashboards

#### Grafana Dashboard

Example Grafana dashboard configuration:

```json
{
  "dashboard": {
    "title": "AllôBye MCP Server",
    "panels": [
      {
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(allobye_requests_total[5m])"
          }
        ]
      },
      {
        "title": "Error Rate",
        "targets": [
          {
            "expr": "rate(allobye_tool_errors_total[5m]) / rate(allobye_tool_calls_total[5m])"
          }
        ]
      },
      {
        "title": "P95 Latency",
        "targets": [
          {
            "expr": "allobye_tool_latency_ms{quantile=\"0.95\"}"
          }
        ]
      }
    ]
  }
}
```

---

## Troubleshooting

### High Latency

**Symptoms**: Slow response times, users complaining about delays

**Investigation**:

```bash
# Check P95 latency
curl -s http://localhost:8000/metrics | grep 'quantile="0.95"'

# Find slow tools
curl -s http://localhost:8000/metrics | grep latency_ms | sort -k2 -n

# Check slow queries
curl -s http://localhost:8000/metrics | grep slow_queries
```

**Common Causes**:
- Slow database queries (missing indexes)
- External API delays (Supabase)
- High connection count
- Resource exhaustion

### High Error Rate

**Symptoms**: Many failed requests, errors in logs

**Investigation**:

```bash
# Check error rate by tool
curl -s http://localhost:8000/metrics | grep error

# Find recent errors in logs
jq 'select(.level == "ERROR")' logs/*.json | tail -20

# Check specific tool errors
jq 'select(.tool == "pickup-schedule-create" and .level == "ERROR")' logs/*.json
```

**Common Causes**:
- Database connectivity issues
- Authentication failures
- Validation errors
- Permission issues

### Database Issues

**Symptoms**: Connection failures, timeouts, slow queries

**Investigation**:

```bash
# Check database health
curl -s http://localhost:8000/health | jq '.components.database'

# Check consecutive failures
curl -s http://localhost:8000/metrics | grep db_consecutive_failures

# Check slow queries
curl -s http://localhost:8000/metrics | grep db_slow_queries
```

**Common Causes**:
- Connection pool exhausted
- Missing indexes
- Long-running transactions
- Database server issues

---

## Best Practices

### 1. Always Use Correlation IDs

```python
# ✅ Good
with correlation_context(user_id=user_id) as cid:
    process_request()

# ❌ Bad
process_request()  # No correlation tracking
```

### 2. Log Important Events

```python
# ✅ Good
logger.info("Pickup created", pickup_id=pickup_id, child_count=len(children))

# ❌ Bad
print("Pickup created")  # Not structured, no correlation
```

### 3. Record Business Metrics

```python
# ✅ Good
metrics.record_business_event("pickup_created", labels={"school": school_id})

# ❌ Bad
# Only recording technical metrics, missing business context
```

### 4. Use Tracing for Complex Operations

```python
# ✅ Good
with trace_context(span_name="process_emergency") as trace:
    with trace_context(span_name="notify_delegates"):
        notify_delegates()
    with trace_context(span_name="notify_schools"):
        notify_schools()

# ❌ Bad
notify_delegates()
notify_schools()
# No tracing, can't see breakdown
```

### 5. Include Context in Logs

```python
# ✅ Good
logger.error(
    "Pickup creation failed",
    user_id=user_id,
    child_ids=child_ids,
    error=str(e),
    error_type=type(e).__name__
)

# ❌ Bad
logger.error("Pickup creation failed")  # Missing context
```

### 6. Monitor Health Regularly

```bash
# Set up health check monitoring (every 30 seconds)
*/30 * * * * curl -s http://localhost:8000/health | jq -e '.status == "healthy"' || alert
```

### 7. Review Alerts Configuration

Regularly review and update `alerts.yml`:

- Adjust thresholds based on actual traffic
- Add new alerts for new features
- Update runbooks with lessons learned
- Test alert response procedures

### 8. Analyze Trends

Use metrics to identify trends:

```promql
# Week-over-week request growth
rate(allobye_requests_total[1w]) / rate(allobye_requests_total[1w] offset 1w)

# Error rate trend
rate(allobye_tool_errors_total[1d])
```

---

## Integration Examples

### Prometheus Scrape Config

```yaml
scrape_configs:
  - job_name: 'allobye-mcp'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### ELK Stack Log Shipping

```yaml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /var/log/allobye/*.json
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["localhost:9200"]
  index: "allobye-logs-%{+yyyy.MM.dd}"
```

### CloudWatch Integration

```python
import boto3

cloudwatch = boto3.client('cloudwatch')

# Send custom metrics
cloudwatch.put_metric_data(
    Namespace='AlloBye/MCP',
    MetricData=[
        {
            'MetricName': 'PickupsCreated',
            'Value': pickups_created,
            'Unit': 'Count',
            'Dimensions': [
                {'Name': 'School', 'Value': school_id}
            ]
        }
    ]
)
```

---

## Additional Resources

- **Alerts Configuration**: `allobye_server_python/alerts.yml`
- **Health Checks**: `allobye_server_python/health_checks.py`
- **Logging Config**: `allobye_server_python/logging_config.py`
- **Monitoring Module**: `allobye_server_python/monitoring.py`
- **Prometheus Documentation**: https://prometheus.io/docs/
- **Grafana Documentation**: https://grafana.com/docs/

---

**Last Updated**: 2025-11-04
**Version**: 1.0
**Maintainer**: AllôBye Engineering Team
