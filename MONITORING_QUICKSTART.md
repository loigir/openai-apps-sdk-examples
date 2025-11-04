# AllôBye Monitoring - Quick Start Guide

**Get started with monitoring in 5 minutes**

---

## 🚀 Quick Examples

### 1. Add Correlation ID to Your Code

```python
from logging_config import correlation_context, get_logger

logger = get_logger(__name__)

async def handle_request(user_id: str):
    # All logs in this block will have the same correlation_id
    with correlation_context(user_id=user_id) as correlation_id:
        logger.info("Starting request processing")

        result = await process_data()

        logger.info("Request completed", result_count=len(result))
        return result
```

**Result**: Every log from this request will have the same correlation_id for easy tracking!

---

### 2. Track Operation Performance

```python
from logging_config import logging_scope

async def fetch_pickups(school_id: str):
    # Automatically times the operation
    with logging_scope("fetch_pickups", school=school_id) as ctx:
        pickups = await db.query("SELECT * FROM pickups WHERE school_id = ?", school_id)

        # Add context
        ctx["pickup_count"] = len(pickups)

        return pickups
    # Automatically logs: "Operation completed: fetch_pickups" with duration_ms
```

---

### 3. Add Distributed Tracing

```python
from logging_config import trace_context

async def process_emergency(child_id: str):
    # Create parent trace
    with trace_context(span_name="process_emergency") as parent_trace:

        # Nested operation 1
        with trace_context(span_name="notify_delegates") as trace1:
            await notify_delegates(child_id)

        # Nested operation 2
        with trace_context(span_name="notify_schools") as trace2:
            await notify_schools(child_id)

        # Nested operation 3
        with trace_context(span_name="send_push_notifications") as trace3:
            await send_push_notifications(child_id)
```

**Result**: See the breakdown of where time is spent in your operations!

---

### 4. Record Business Metrics

```python
from monitoring import get_metrics

metrics = get_metrics()

async def create_pickup(child_ids: list, pickup_person_id: str):
    # Create pickup
    pickup = await db.create_pickup(child_ids, pickup_person_id)

    # Record business event
    metrics.record_business_event(
        "pickup_created",
        labels={
            "school": pickup["school_id"],
            "role": "parent",
            "child_count": str(len(child_ids))
        }
    )

    # Track cross-school pickups
    if len(set(c["school_id"] for c in child_ids)) > 1:
        metrics.record_business_event(
            "cross_school_pickup",
            labels={"school_count": str(len(set(...)))}
        )

    return pickup
```

---

### 5. Check System Health

```bash
# Check overall health
curl http://localhost:8000/health

# Check specific component
curl http://localhost:8000/health | jq '.components.database'

# Check if healthy (exit code 0 if healthy)
curl -s http://localhost:8000/health | jq -e '.status == "healthy"'
```

---

### 6. View Metrics

```bash
# View all metrics
curl http://localhost:8000/metrics

# Check error rate
curl http://localhost:8000/metrics | grep error_rate

# Check P95 latency
curl http://localhost:8000/metrics | grep 'quantile="0.95"'

# Check business metrics
curl http://localhost:8000/metrics | grep pickup
```

---

### 7. Search Logs

```bash
# Find all logs for a specific correlation ID
grep '"correlation_id": "abc-123"' logs/*.json

# Find all errors for a specific tool
jq 'select(.tool == "pickup-schedule-create" and .level == "ERROR")' logs/*.json

# Find slow operations (> 1 second)
jq 'select(.duration_ms > 1000) | {tool, duration_ms, correlation_id}' logs/*.json

# Track a request end-to-end
correlation_id="abc-123"
jq --arg cid "$correlation_id" 'select(.correlation_id == $cid)' logs/*.json | less
```

---

## 📊 Common Prometheus Queries

### Request Rate
```promql
# Requests per second
rate(allobye_requests_total[5m])
```

### Error Rate
```promql
# Overall error rate
rate(allobye_tool_errors_total[5m]) / rate(allobye_tool_calls_total[5m])

# Error rate by tool
rate(allobye_tool_errors_total[5m]) / rate(allobye_tool_calls_total[5m]) by (tool)
```

### Latency
```promql
# Average latency
allobye_tool_latency_ms{quantile="avg"}

# P95 latency
allobye_tool_latency_ms{quantile="0.95"}

# P99 latency
allobye_tool_latency_ms{quantile="0.99"}
```

### Business Metrics
```promql
# Pickups per hour
increase(allobye_pickups_created_total[1h])

# Pickup completion rate
allobye_pickups_completed_total / allobye_pickups_created_total

# Emergencies per day
increase(allobye_emergencies_declared_total[1d])
```

### Cache Performance
```promql
# Cache hit rate
allobye_cache_hit_rate

# Cache miss rate
1 - allobye_cache_hit_rate

# Cache size growth
deriv(allobye_cache_size_bytes[5m])
```

---

## 🔍 Debugging Workflow

### Problem: High latency reported by users

#### Step 1: Check metrics
```bash
curl http://localhost:8000/metrics | grep 'quantile="0.95"' | sort -k2 -n
```

#### Step 2: Identify slow tool
```promql
# In Prometheus
topk(5, allobye_tool_latency_ms{quantile="0.95"})
```

#### Step 3: Find slow requests in logs
```bash
# Find requests > 1s for slow tool
jq 'select(.tool == "pickup-schedule-create" and .duration_ms > 1000)' logs/*.json
```

#### Step 4: Track specific request end-to-end
```bash
# Get correlation_id from slow request
correlation_id=$(jq -r 'select(.tool == "pickup-schedule-create" and .duration_ms > 1000) | .correlation_id' logs/*.json | head -1)

# Track full request
jq --arg cid "$correlation_id" 'select(.correlation_id == $cid)' logs/*.json
```

#### Step 5: Check database performance
```bash
curl http://localhost:8000/metrics | grep db_slow_queries
curl http://localhost:8000/health | jq '.components.database'
```

---

## 🚨 Alert Response Example

### Alert: High Error Rate

#### 1. Check current status
```bash
# Check metrics
curl http://localhost:8000/metrics | grep error

# Check health
curl http://localhost:8000/health
```

#### 2. View recent errors
```bash
# Last 10 errors
jq 'select(.level == "ERROR")' logs/*.json | tail -10

# Errors by tool
jq -r 'select(.level == "ERROR") | .tool' logs/*.json | sort | uniq -c | sort -rn
```

#### 3. Identify pattern
```bash
# Check for specific error messages
jq 'select(.level == "ERROR") | .error' logs/*.json | sort | uniq -c | sort -rn
```

#### 4. Check dependencies
```bash
# Database health
curl http://localhost:8000/health | jq '.components.database'

# Supabase API health
curl http://localhost:8000/health | jq '.components.supabase_api'
```

#### 5. Correlate with deployments
```bash
# Check when errors started
jq 'select(.level == "ERROR") | .timestamp' logs/*.json | head -1

# Recent git commits
git log --since="2 hours ago" --oneline
```

---

## 📈 Grafana Dashboard

### Quick Grafana Setup

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'allobye-mcp'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

### Key Panels

1. **Request Rate**
   - Query: `rate(allobye_requests_total[5m])`
   - Type: Graph

2. **Error Rate**
   - Query: `rate(allobye_tool_errors_total[5m]) / rate(allobye_tool_calls_total[5m])`
   - Type: Graph
   - Alert: > 5%

3. **P95 Latency**
   - Query: `allobye_tool_latency_ms{quantile="0.95"}`
   - Type: Graph
   - Alert: > 1000ms

4. **Business Metrics**
   - Query: `increase(allobye_pickups_created_total[1h])`
   - Type: Stat

5. **Health Status**
   - Query: Health endpoint
   - Type: Stat

---

## 🧪 Testing Your Monitoring

### Test 1: Correlation IDs Work

```python
# Test script
from logging_config import correlation_context, get_logger

logger = get_logger(__name__)

with correlation_context(user_id="test_user") as cid:
    logger.info("Test log 1")
    logger.info("Test log 2")
    logger.info("Test log 3")
    print(f"Correlation ID: {cid}")
```

Then search logs:
```bash
grep "<correlation_id>" logs/*.json
```

You should see all 3 logs with the same correlation_id!

---

### Test 2: Business Metrics Work

```python
from monitoring import get_metrics

metrics = get_metrics()

# Record test events
metrics.record_business_event("pickup_created")
metrics.record_business_event("pickup_created", labels={"school": "test_school"})
metrics.record_business_event("emergency_declared")

# Check metrics
print(f"Pickups created: {metrics.business_metrics.pickups_created}")
```

Then check Prometheus:
```bash
curl http://localhost:8000/metrics | grep pickups_created
```

---

### Test 3: Health Checks Work

```bash
# Normal health
curl http://localhost:8000/health | jq '.status'
# Should return: "healthy"

# Check all components
curl http://localhost:8000/health | jq '.components | keys'
# Should return: ["authentication", "cache", "database", "monitoring", "supabase_api"]
```

---

## 📚 Next Steps

1. **Read Full Guide**: Check out [OBSERVABILITY_GUIDE.md](./OBSERVABILITY_GUIDE.md)
2. **Configure Alerts**: Review [alerts.yml](./allobye_server_python/alerts.yml)
3. **Set Up Prometheus**: Configure scraping for production
4. **Create Dashboards**: Build Grafana dashboards for your team
5. **Test Incident Response**: Practice alert response procedures

---

## 🆘 Common Issues

### Issue: Logs don't have correlation_id

**Solution**: Make sure you're using `correlation_context`:
```python
with correlation_context(user_id=user_id) as cid:
    logger.info("Your log here")
```

### Issue: Metrics not showing up

**Solution**: Make sure you're recording events:
```python
metrics = get_metrics()
metrics.record_business_event("your_event")
```

### Issue: Health check fails

**Solution**: Check component status:
```bash
curl http://localhost:8000/health | jq '.components'
```

### Issue: Can't find logs

**Solution**: Check log file location:
```bash
ls -la logs/
# Or check logging config
python -c "from logging_config import setup_logging; help(setup_logging)"
```

---

## 💡 Pro Tips

1. **Always use correlation contexts** for request handling
2. **Record business events** whenever important actions occur
3. **Use logging scopes** for automatic timing
4. **Check health endpoint** before deployments
5. **Set up alerts early** to catch issues proactively
6. **Review metrics weekly** to identify trends
7. **Keep runbooks updated** with lessons learned

---

## 📞 Getting Help

- **Documentation**: [OBSERVABILITY_GUIDE.md](./OBSERVABILITY_GUIDE.md)
- **Monitoring Guide**: [MONITORING.md](./MONITORING.md)
- **Implementation Report**: [MONITORING_IMPLEMENTATION_REPORT.md](./MONITORING_IMPLEMENTATION_REPORT.md)
- **Code Examples**: Check docstrings in monitoring modules

---

**Last Updated**: 2025-11-04
**Version**: 1.0
