# AllôBye MCP Server - Monitoring & Observability

**Real-time monitoring, metrics, and observability for AllôBye MCP Server**

---

## Quick Start

### View Monitoring Dashboard

```bash
# Use MCP tool to view monitoring dashboard
mcp tool call monitoring-dashboard-fetch --includeDetails=true
```

### Check System Health

```bash
# HTTP health check
curl http://localhost:8000/health

# Check health status
curl http://localhost:8000/health | jq '.status'
```

### View Prometheus Metrics

```bash
# All metrics
curl http://localhost:8000/metrics

# Filter specific metrics
curl http://localhost:8000/metrics | grep pickup

# Check error rate
curl http://localhost:8000/metrics | grep error_rate
```

---

## Architecture

The monitoring system provides three layers of observability:

1. **Structured Logging**: JSON logs with correlation IDs for request tracking
2. **Metrics Collection**: Prometheus-compatible metrics for performance monitoring
3. **Distributed Tracing**: Span-based tracing for debugging complex flows

### Components

```
┌─────────────────────────────────────────────────┐
│              Application Code                    │
├─────────────────────────────────────────────────┤
│         Monitoring Middleware                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐        │
│  │  Logger  │ │  Metrics │ │  Tracer  │        │
│  └──────────┘ └──────────┘ └──────────┘        │
├─────────────────────────────────────────────────┤
│           Export Endpoints                       │
│  /health (JSON)  |  /metrics (Prometheus)       │
└─────────────────────────────────────────────────┘
```

---

## Metrics

### Technical Metrics

#### System Metrics
- `allobye_uptime_seconds`: Server uptime
- `allobye_requests_total`: Total requests handled
- `allobye_active_connections`: Current active connections
- `allobye_active_sessions`: Current user sessions

#### Tool Performance Metrics
- `allobye_tool_calls_total{tool="..."}`: Total calls per tool
- `allobye_tool_success_total{tool="..."}`: Successful calls per tool
- `allobye_tool_errors_total{tool="..."}`: Failed calls per tool
- `allobye_tool_latency_ms{tool="...", quantile="..."}`: Latency distribution
  - `quantile="avg"`: Average latency
  - `quantile="min"`: Minimum latency
  - `quantile="max"`: Maximum latency
  - `quantile="0.50"`: Median (P50)
  - `quantile="0.95"`: 95th percentile (P95)
  - `quantile="0.99"`: 99th percentile (P99)

#### Database Metrics
- `allobye_db_queries_total`: Total database queries
- `allobye_db_errors_total`: Database query errors
- `allobye_db_slow_queries_total`: Slow queries (> 1 second)
- `allobye_db_latency_ms{quantile="avg"}`: Average query latency

#### Cache Metrics
- `allobye_cache_hits_total`: Cache hits
- `allobye_cache_misses_total`: Cache misses
- `allobye_cache_hit_rate`: Hit rate (0.0 to 1.0)
- `allobye_cache_size_bytes`: Current cache size
- `allobye_cache_items`: Number of cached items

### Business Metrics

#### Pickup Metrics
- `allobye_pickups_created_total`: Total pickups created
- `allobye_pickups_completed_total`: Total pickups completed
- `allobye_pickups_cancelled_total`: Total pickups cancelled
- `allobye_cross_school_pickups_total`: Cross-school pickups

#### Delegate Metrics
- `allobye_delegates_authorized_total`: Delegates authorized
- `allobye_delegate_revocations_total`: Delegate authorizations revoked

#### Emergency Metrics
- `allobye_emergencies_declared_total`: Total emergencies declared
- `allobye_emergency_notifications_total`: Emergency notifications sent

#### Authentication Metrics
- `allobye_parent_logins_total`: Parent user logins
- `allobye_staff_logins_total`: School staff logins

### Multi-Dimensional Metrics

Metrics can be filtered by labels:

```promql
# Pickups per school
sum(allobye_pickups_created_total) by (school)

# Error rate by tool and role
rate(allobye_tool_errors_total[5m]) by (tool, role)

# Emergencies by type
sum(allobye_emergencies_declared_total) by (emergency_type)
```

---

## Logging

### Log Structure

All logs are structured JSON with standard fields:

```json
{
  "timestamp": "2025-11-04T15:30:45.123Z",
  "level": "INFO",
  "service": "allobye-mcp-server",
  "environment": "production",
  "message": "Pickup created successfully",
  "correlation_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "trace_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "span_id": "c3d4e5f6-a7b8-9012-cdef-123456789012",
  "tool": "pickup-schedule-create",
  "duration_ms": 234.5,
  "user_id": "user_123",
  "school_id": "school_456"
}
```

### Correlation IDs

Every request is assigned a unique correlation ID that appears in all related logs:

```python
from logging_config import correlation_context, get_logger

logger = get_logger(__name__)

with correlation_context(user_id="user_123") as correlation_id:
    logger.info("Processing request")
    # All operations here share the same correlation_id
    process_data()
```

### Finding Logs

```bash
# Find all logs for a correlation ID
jq 'select(.correlation_id == "a1b2c3d4-e5f6-7890")' logs/*.json

# Find all errors for a specific tool
jq 'select(.tool == "pickup-schedule-create" and .level == "ERROR")' logs/*.json

# Find slow operations (>1s)
jq 'select(.duration_ms > 1000)' logs/*.json
```

---

## Tracing

### Distributed Tracing

Track requests through multiple operations:

```python
from logging_config import trace_context

# Create a trace
with trace_context(span_name="process_pickup") as trace:
    trace_id = trace["trace_id"]
    span_id = trace["span_id"]

    # Nested operations create child spans
    with trace_context(span_name="validate_auth"):
        validate_user()

    with trace_context(span_name="create_record"):
        create_pickup_record()
```

### Trace Visualization

```
Request: process_pickup (trace_id: abc123)
├─ Span: validate_auth (45ms)
├─ Span: create_record (120ms)
│  ├─ Span: database_insert (80ms)
│  └─ Span: update_cache (40ms)
└─ Span: send_notification (89ms)
Total: 254ms
```

---

## Health Checks

### Health Check Endpoint

```
GET /health
```

### Components Checked

1. **Database Connectivity**: Verifies database connection and query performance
2. **Supabase API**: Checks Supabase API availability
3. **Cache**: Validates cache system health
4. **Monitoring**: Verifies monitoring system is operational
5. **Authentication**: Checks auth system configuration

### Health Status Levels

- `healthy`: All systems operational
- `degraded`: Some systems slow but functional (may impact performance)
- `unhealthy`: Critical failures detected (service may be unavailable)

### Example Response

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
      "latency_ms": 23.4
    },
    "supabase_api": {
      "status": "healthy",
      "message": "Supabase API responding",
      "latency_ms": 67.2
    }
  },
  "metrics": {
    "uptime_seconds": 3600,
    "total_requests": 1234,
    "error_rate": 0.02
  }
}
```

### Automated Health Monitoring

```bash
# Check health every 30 seconds
watch -n 30 "curl -s http://localhost:8000/health | jq '.status'"

# Alert on unhealthy status
curl -s http://localhost:8000/health | jq -e '.status == "healthy"' || send_alert
```

---

## Alerting

### Alert Configuration

Alerts are defined in `alerts.yml` with thresholds and response procedures.

### Alert Categories

1. **Performance Alerts**
   - High error rate (> 5%)
   - High latency (> 1s)
   - Database slow queries

2. **Availability Alerts**
   - Database connection failures
   - API endpoint failures
   - Authentication failures

3. **Business Logic Alerts**
   - Pickup creation failures
   - Emergency notification failures
   - High authentication failure rate

4. **Resource Alerts**
   - High connection count
   - Low cache hit rate
   - Memory/CPU utilization (if monitoring added)

### Alert Response

Each alert includes:
- **Severity**: info, warning, error, critical
- **Threshold**: Metric value that triggers alert
- **Duration**: How long condition must persist
- **Response Procedure**: Step-by-step remediation guide
- **Runbook URL**: Link to detailed documentation

### Example Alert

```yaml
- name: high_error_rate
  severity: warning
  condition:
    metric: error_rate
    operator: greater_than
    threshold: 0.05
    duration: 300
  response_procedure: |
    1. Check monitoring dashboard
    2. Review error logs
    3. Check database connectivity
    4. Investigate recent changes
```

---

## Dashboards

### Monitoring Dashboard Widget

Access via MCP tool:

```
Tool: monitoring-dashboard-fetch
Endpoint: /health
Widget: allobye-monitoring.html
```

### Dashboard Sections

1. **Overview**
   - Uptime, total requests, error rate
   - Active connections and sessions
   - Average latency

2. **Tool Metrics**
   - Top tools by usage
   - Success/error rates per tool
   - Latency distributions

3. **Business Metrics**
   - Pickups created/completed
   - Emergencies and notifications
   - User logins by role

4. **Database Performance**
   - Query count and error rate
   - Slow queries
   - Connection pool status

5. **Recent Activity**
   - Last 50 requests
   - Last 20 errors
   - Active alerts

### Custom Grafana Dashboards

Connect Prometheus to Grafana for advanced visualization:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'allobye-mcp'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

---

## Performance Tuning

### Identifying Bottlenecks

#### 1. Check P95 Latency

```bash
# Find tools with high P95 latency
curl -s http://localhost:8000/metrics | grep 'quantile="0.95"' | sort -k2 -n
```

#### 2. Identify Slow Queries

```bash
# Check slow query count
curl -s http://localhost:8000/metrics | grep slow_queries
```

#### 3. Monitor Error Rates

```promql
# Error rate by tool (Prometheus query)
rate(allobye_tool_errors_total[5m]) / rate(allobye_tool_calls_total[5m])
```

### Optimization Strategies

1. **Database Optimization**
   - Add indexes for frequent queries
   - Optimize N+1 queries
   - Use connection pooling

2. **Caching**
   - Cache frequently accessed data
   - Set appropriate TTLs
   - Monitor hit rates

3. **Async Processing**
   - Use background jobs for heavy operations
   - Implement queue-based processing
   - Optimize notification delivery

---

## Common Queries

### Prometheus Queries

```promql
# Request rate (req/s)
rate(allobye_requests_total[5m])

# Error rate percentage
(rate(allobye_tool_errors_total[5m]) / rate(allobye_tool_calls_total[5m])) * 100

# Average latency
allobye_tool_latency_ms{quantile="avg"}

# Pickups per hour
increase(allobye_pickups_created_total[1h])

# Cache effectiveness
allobye_cache_hit_rate

# Database health
allobye_db_errors_total / allobye_db_queries_total
```

### Log Queries (jq)

```bash
# Count errors by tool
jq -r 'select(.level=="ERROR") | .tool' logs/*.json | sort | uniq -c

# Average latency by tool
jq -r 'select(.duration_ms) | "\(.tool) \(.duration_ms)"' logs/*.json | \
  awk '{sum[$1]+=$2; count[$1]++} END {for (tool in sum) print tool, sum[tool]/count[tool]}'

# Find slowest requests
jq -r 'select(.duration_ms > 1000) | "\(.duration_ms)ms \(.tool) \(.correlation_id)"' logs/*.json | sort -n
```

---

## Integration

### Prometheus

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'allobye'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### ELK Stack

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    paths: ['/var/log/allobye/*.json']
    json.keys_under_root: true

output.elasticsearch:
  hosts: ['localhost:9200']
  index: 'allobye-%{+yyyy.MM.dd}'
```

### Datadog

```python
from datadog import statsd

# Send custom metrics
statsd.increment('allobye.pickup.created')
statsd.histogram('allobye.latency', latency_ms)
statsd.gauge('allobye.active_sessions', session_count)
```

---

## Troubleshooting

### High Latency

1. Check P95 latency: `curl -s /metrics | grep quantile="0.95"`
2. Identify slow tools in dashboard
3. Check database slow queries
4. Review database indexes
5. Check Supabase API status

### High Error Rate

1. View recent errors: `jq 'select(.level=="ERROR")' logs/*.json | tail -20`
2. Check specific tool: `curl -s /metrics | grep tool_errors`
3. Verify database connectivity: `curl -s /health | jq '.components.database'`
4. Check authentication system
5. Review recent deployments

### Database Issues

1. Check health: `curl -s /health | jq '.components.database'`
2. Check consecutive failures: `curl -s /metrics | grep db_consecutive_failures`
3. Check slow queries: `curl -s /metrics | grep db_slow_queries`
4. Review connection pool settings
5. Verify Supabase status

---

## Best Practices

### 1. Monitor Proactively

- Set up automated health checks
- Configure alerts for critical metrics
- Review dashboards regularly
- Analyze trends over time

### 2. Use Correlation IDs

- Always wrap operations in correlation context
- Include correlation IDs in external API calls
- Use correlation IDs for troubleshooting

### 3. Log Appropriately

- Use structured logging (JSON)
- Include relevant context
- Log at appropriate levels
- Avoid logging sensitive data

### 4. Track Business Metrics

- Record key business events
- Use labels for segmentation
- Monitor business KPIs
- Correlate with technical metrics

### 5. Test Monitoring

- Verify metrics are being collected
- Test alert thresholds
- Practice incident response
- Update runbooks regularly

---

## Resources

- **Full Observability Guide**: [OBSERVABILITY_GUIDE.md](./OBSERVABILITY_GUIDE.md)
- **Alert Configuration**: [alerts.yml](./allobye_server_python/alerts.yml)
- **Health Checks Module**: [health_checks.py](./allobye_server_python/health_checks.py)
- **Logging Configuration**: [logging_config.py](./allobye_server_python/logging_config.py)
- **Monitoring Module**: [monitoring.py](./allobye_server_python/monitoring.py)

---

**Last Updated**: 2025-11-04
**Version**: 1.0
**Maintainer**: AllôBye Engineering Team
