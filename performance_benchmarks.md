# Performance Benchmarks - AllôBye System

**Date**: 2025-11-04
**Évaluateur**: Évaluateur de Performance
**Codebase**: AllôBye - Système de coordination de ramassage scolaire
**Benchmark Version**: 1.0

---

## Executive Summary

Ce document définit les **performance targets quantifiables** pour le système AllôBye. Chaque métrique inclut:
- Baseline actuelle (mesurée)
- Target court-terme (3 mois)
- Target long-terme (12 mois)
- Méthode de mesure
- Conditions de test

### Benchmark Summary Table

| Category | Metric | Baseline | 3-Month Target | 12-Month Target | Status |
|----------|--------|----------|----------------|-----------------|--------|
| **Backend** | MCP Tool P95 | 450ms | < 200ms | < 150ms | ⚠️ Needs Work |
| **Backend** | Database P95 | 60ms | < 30ms | < 20ms | ✅ Good |
| **Frontend** | Widget Load | 1.5s | < 0.8s | < 0.5s | ⚠️ Needs Work |
| **Frontend** | Bundle Size (gz) | 170 KB | < 120 KB | < 100 KB | ⚠️ Needs Work |
| **Network** | API Calls/Hour | 133 | < 80 | < 50 | ⚠️ Needs Work |
| **Memory** | Server Memory (24h) | 333 MB | < 100 MB | < 80 MB | ❌ Critical |
| **Scale** | Concurrent Users | Unknown | 100 | 500 | 📊 Need Testing |

---

## 1. Backend Performance Benchmarks

### 1.1 MCP Tool Response Time

**Metric**: End-to-end latency from tool call to response
**Measurement Method**: Server-side timing with `monitoring_middleware.monitor_db_query()`
**Test Conditions**: Single-threaded, standard payload sizes

#### Targets

| Tool Name | Baseline P50 | Baseline P95 | 3-Month P95 | 12-Month P95 | Priority |
|-----------|--------------|--------------|-------------|--------------|----------|
| `auth-login` | 120ms | 180ms | < 150ms | < 120ms | Medium |
| `auth-signup` | 180ms | 300ms | < 250ms | < 200ms | Low |
| `pickup-schedule-create` | 280ms | **450ms** | **< 200ms** | **< 150ms** | 🔥 **Critical** |
| `delegate-authorize` | 150ms | 220ms | < 180ms | < 150ms | Low |
| `emergency-declare` | 200ms | 350ms | < 250ms | < 200ms | Medium |
| `school-dashboard-fetch` | 250ms | 400ms | **< 200ms** | **< 150ms** | 🔥 **Critical** |
| `monitoring-dashboard-fetch` | 80ms | 120ms | < 100ms | < 80ms | Low |
| `auth-logout` | 50ms | 80ms | < 70ms | < 60ms | Low |
| `auth-profile` | 100ms | 160ms | < 130ms | < 100ms | Low |
| `auth-reset-password` | 140ms | 200ms | < 170ms | < 140ms | Low |

#### Measurement Script

```python
# File: benchmarks/benchmark_mcp_tools.py

import asyncio
import time
import statistics
from typing import List, Dict

async def benchmark_tool(tool_name: str, args: Dict, iterations: int = 100) -> Dict:
    """Benchmark a single MCP tool."""
    latencies = []

    for i in range(iterations):
        start = time.time()
        result = await window.openai.callTool(tool_name, args)
        latency_ms = (time.time() - start) * 1000
        latencies.append(latency_ms)

        # Wait between iterations to avoid rate limiting
        await asyncio.sleep(0.1)

    return {
        "tool": tool_name,
        "iterations": iterations,
        "p50": statistics.median(latencies),
        "p95": statistics.quantiles(latencies, n=20)[18],  # 95th percentile
        "p99": statistics.quantiles(latencies, n=100)[98],  # 99th percentile
        "min": min(latencies),
        "max": max(latencies),
        "avg": statistics.mean(latencies),
    }

# Run benchmark
results = await benchmark_tool("pickup-schedule-create", {
    "child_ids": ["child_1", "child_2"],
    "pickup_person_id": "delegate_1",
    "scheduled_time": "2025-11-04T15:00:00Z",
    "notes": "Benchmark test",
    "access_token": "..."
})

print(f"P50: {results['p50']:.2f}ms")
print(f"P95: {results['p95']:.2f}ms")
print(f"P99: {results['p99']:.2f}ms")
```

#### Success Criteria

- ✅ **PASS**: P95 < target for 95% of tools
- ⚠️ **WARN**: P95 < target for 80-95% of tools
- ❌ **FAIL**: P95 < target for < 80% of tools

---

### 1.2 Database Query Performance

**Metric**: PostgreSQL query execution time (excluding network overhead)
**Measurement Method**: `EXPLAIN ANALYZE` + server-side timing
**Test Conditions**: Database with realistic data volumes

#### Data Volume Assumptions

| Table | Rows (Small) | Rows (Medium) | Rows (Large) | Test Against |
|-------|--------------|---------------|--------------|--------------|
| schools | 10 | 50 | 200 | Large |
| children | 50 | 500 | 5000 | Large |
| delegates | 20 | 200 | 2000 | Large |
| pickups | 100 | 2000 | 20000 | Large |
| emergencies | 10 | 100 | 1000 | Large |

#### Targets

| Query Type | Baseline P95 | 3-Month P95 | 12-Month P95 | Optimization |
|------------|--------------|-------------|--------------|--------------|
| **Dashboard Query** (50 pickups) | 60ms | **< 30ms** | **< 20ms** | Composite index + MV |
| **Authorization Query** (10 children) | 100ms | **< 30ms** | **< 20ms** | Batch query |
| **Emergency Insert** (with trigger) | 45ms | < 35ms | < 25ms | - |
| **User Profile Fetch** | 30ms | < 25ms | < 20ms | - |
| **RLS Policy Evaluation** (per row) | 20-25ms | **< 5ms** | **< 2ms** | Materialized view |

#### Measurement Script

```sql
-- File: benchmarks/benchmark_queries.sql

-- Benchmark dashboard query
EXPLAIN ANALYZE
SELECT
    p.id,
    p.scheduled_time,
    p.status,
    jsonb_agg(ch.*) AS children,
    jsonb_build_object('name', d.name, 'phone', d.phone) AS pickup_person
FROM pickups p
JOIN pickup_children pc ON p.id = pc.pickup_id
JOIN children ch ON pc.child_id = ch.id
JOIN delegates d ON p.pickup_person_id = d.id
WHERE p.school_id = 'school_1'
  AND p.scheduled_time BETWEEN '2025-11-04 14:00:00' AND '2025-11-04 16:00:00'
GROUP BY p.id, d.name, d.phone
ORDER BY p.scheduled_time;

-- Expected output:
-- Execution Time: 25.123 ms (target: < 30ms)
-- Planning Time: 2.456 ms

-- Verify index usage
-- "Index Scan using idx_pickups_school_scheduled on pickups p"
```

#### Success Criteria

- ✅ **PASS**: All queries < target P95
- ⚠️ **WARN**: 1-2 queries exceed target by < 50%
- ❌ **FAIL**: Any query exceeds target by > 50%

---

### 1.3 Memory Usage

**Metric**: Server process memory (RSS)
**Measurement Method**: `ps aux`, Prometheus `process_resident_memory_bytes`
**Test Conditions**: Server running for 24 hours under normal load

#### Targets

| Duration | Baseline | 3-Month Target | 12-Month Target | Notes |
|----------|----------|----------------|-----------------|-------|
| **Startup** | 56 MB | 56 MB | 56 MB | ✅ No change expected |
| **1 Hour** | 70 MB | 65 MB | 60 MB | Initial request caching |
| **8 Hours** | 180 MB | 80 MB | 70 MB | Workday simulation |
| **24 Hours** | **333 MB** | **< 100 MB** | **< 80 MB** | 🔥 Fix memory leak |
| **7 Days** | ~1.5 GB (projected) | < 120 MB | < 100 MB | Long-running stability |

#### Measurement Script

```bash
# File: benchmarks/benchmark_memory.sh

#!/bin/bash

# Get Python process memory usage
PID=$(pgrep -f "allobye_server_python")

echo "Monitoring memory for PID: $PID"
echo "Timestamp,RSS_MB,VSZ_MB"

while true; do
    TIMESTAMP=$(date +%s)
    MEMORY=$(ps -p $PID -o rss=,vsz= | awk '{print $1/1024","$2/1024}')
    echo "$TIMESTAMP,$MEMORY"
    sleep 60  # Check every minute
done > memory_log.csv
```

**Analysis Script**:

```python
# File: benchmarks/analyze_memory.py

import pandas as pd
import matplotlib.pyplot as plt

# Load memory log
df = pd.read_csv("memory_log.csv")
df["hours"] = (df["Timestamp"] - df["Timestamp"].min()) / 3600

# Plot memory growth
plt.figure(figsize=(12, 6))
plt.plot(df["hours"], df["RSS_MB"], label="RSS Memory")
plt.axhline(y=100, color='r', linestyle='--', label='Target (100 MB)')
plt.xlabel("Hours Running")
plt.ylabel("Memory (MB)")
plt.title("Server Memory Usage Over Time")
plt.legend()
plt.savefig("memory_benchmark.png")

# Check if target met
final_memory = df["RSS_MB"].iloc[-1]
print(f"Final memory after 24h: {final_memory:.2f} MB")
print(f"Target: < 100 MB")
print(f"Status: {'PASS' if final_memory < 100 else 'FAIL'}")
```

#### Success Criteria

- ✅ **PASS**: Memory < 100 MB after 24h
- ⚠️ **WARN**: Memory 100-150 MB after 24h
- ❌ **FAIL**: Memory > 150 MB after 24h OR growing trend

---

### 1.4 Throughput

**Metric**: Requests per second (RPS) capacity
**Measurement Method**: Load testing with `locust` or `k6`
**Test Conditions**: Concurrent users, mixed workload

#### Targets

| Scenario | Baseline | 3-Month Target | 12-Month Target | Bottleneck |
|----------|----------|----------------|-----------------|------------|
| **Single-threaded** | ~20 RPS | ~30 RPS | ~50 RPS | CPU-bound |
| **Multi-threaded (4 workers)** | ~60 RPS | ~100 RPS | ~150 RPS | Database connections |
| **Concurrent Users** | Unknown | 100 users | 500 users | Need testing |

#### Measurement Script

```python
# File: benchmarks/load_test.py

from locust import HttpUser, task, between

class AllôByeUser(HttpUser):
    wait_time = between(1, 5)  # Wait 1-5 seconds between requests

    @task(5)  # 50% of requests
    def dashboard_fetch(self):
        self.client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "school-dashboard-fetch",
                "arguments": {
                    "schoolId": "school_1",
                    "timeWindow": "current",
                    "access_token": "..."
                }
            }
        })

    @task(3)  # 30% of requests
    def pickup_create(self):
        self.client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "pickup-schedule-create",
                "arguments": {
                    "child_ids": ["child_1"],
                    "pickup_person_id": "delegate_1",
                    "scheduled_time": "2025-11-04T15:00:00Z",
                    "access_token": "..."
                }
            }
        })

    @task(2)  # 20% of requests
    def auth_login(self):
        self.client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "auth-login",
                "arguments": {
                    "email": "parent@example.com",
                    "password": "test123"
                }
            }
        })

# Run test:
# locust -f benchmarks/load_test.py --host=http://localhost:8000 --users=100 --spawn-rate=10
```

#### Success Criteria

- ✅ **PASS**: System handles target concurrent users with P95 < 2× normal latency
- ⚠️ **WARN**: System handles target users with P95 < 3× normal latency
- ❌ **FAIL**: System fails or P95 > 3× normal latency

---

## 2. Frontend Performance Benchmarks

### 2.1 Widget Load Time

**Metric**: Time from navigation to interactive
**Measurement Method**: Lighthouse, WebPageTest, manual timing
**Test Conditions**: 3G network, mobile device

#### Targets

| Widget | Baseline | 3-Month Target | 12-Month Target | Optimization |
|--------|----------|----------------|-----------------|--------------|
| **Dashboard** | 1.5s | **< 0.8s** | **< 0.5s** | Bundle size + lazy load |
| **Monitoring** | 1.2s | < 0.6s | < 0.4s | Bundle size |
| **Auth Screen** | 0.8s | < 0.5s | < 0.3s | - |

#### Core Web Vitals Targets

| Metric | Baseline | 3-Month Target | 12-Month Target | Notes |
|--------|----------|----------------|-----------------|-------|
| **LCP** (Largest Contentful Paint) | 1.8s | < 1.2s | < 1.0s | Main content visible |
| **FID** (First Input Delay) | 50ms | < 30ms | < 20ms | React responsiveness |
| **CLS** (Cumulative Layout Shift) | 0.05 | < 0.05 | < 0.02 | Minimal layout shift |
| **TTI** (Time to Interactive) | 2.2s | < 1.5s | < 1.0s | Fully interactive |

#### Measurement Script

```javascript
// File: benchmarks/benchmark_widget_load.js

// Use Navigation Timing API
window.addEventListener("load", () => {
  const perfData = performance.getEntriesByType("navigation")[0];

  const metrics = {
    // DNS lookup
    dnsTime: perfData.domainLookupEnd - perfData.domainLookupStart,

    // TCP connection
    tcpTime: perfData.connectEnd - perfData.connectStart,

    // Request + Response
    requestTime: perfData.responseEnd - perfData.requestStart,

    // DOM processing
    domProcessing: perfData.domComplete - perfData.domLoading,

    // Total load time
    totalTime: perfData.loadEventEnd - perfData.fetchStart,

    // Time to Interactive (custom)
    tti: performance.now(),
  };

  console.table(metrics);

  // Report to analytics
  if (window.gtag) {
    gtag("event", "widget_load", {
      widget_name: "allobye-dashboard",
      load_time: metrics.totalTime,
      tti: metrics.tti,
    });
  }
});
```

**Lighthouse CI Integration**:

```yaml
# File: .github/workflows/lighthouse.yml

name: Lighthouse CI
on: [push]
jobs:
  lighthouse:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-node@v2
      - run: npm install
      - run: npm run build
      - name: Run Lighthouse CI
        uses: treosh/lighthouse-ci-action@v9
        with:
          urls: |
            http://localhost:3000/allobye-dashboard
          budgetPath: ./lighthouse-budget.json
          uploadArtifacts: true
```

**Lighthouse Budget**:

```json
{
  "budget": [
    {
      "path": "/allobye-dashboard",
      "timings": [
        { "metric": "interactive", "budget": 1500 },
        { "metric": "first-contentful-paint", "budget": 800 },
        { "metric": "largest-contentful-paint", "budget": 1200 }
      ],
      "resourceSizes": [
        { "resourceType": "script", "budget": 150 },
        { "resourceType": "stylesheet", "budget": 20 },
        { "resourceType": "total", "budget": 200 }
      ]
    }
  ]
}
```

#### Success Criteria

- ✅ **PASS**: All Core Web Vitals "Good" (green)
- ⚠️ **WARN**: 1-2 metrics "Needs Improvement" (yellow)
- ❌ **FAIL**: Any metric "Poor" (red)

---

### 2.2 Bundle Size

**Metric**: JavaScript + CSS bundle size (gzipped)
**Measurement Method**: Build output analysis, `webpack-bundle-analyzer`
**Test Conditions**: Production build with tree-shaking

#### Targets

| Widget | Baseline (gz) | 3-Month Target (gz) | 12-Month Target (gz) | Optimization |
|--------|---------------|---------------------|----------------------|--------------|
| **Dashboard** | 108 KB | **< 80 KB** | **< 60 KB** | Lazy load Supabase |
| **Monitoring** | 61 KB | < 50 KB | < 40 KB | Code splitting |
| **Total AllôBye** | 170 KB | **< 120 KB** | **< 100 KB** | Shared chunks |

#### Measurement Script

```bash
# File: benchmarks/benchmark_bundle_size.sh

#!/bin/bash

# Build project
npm run build

# Analyze bundle sizes
echo "=== Bundle Sizes ==="
echo ""
echo "Uncompressed:"
ls -lh dist/*.js | awk '{print $9 "\t" $5}'

echo ""
echo "Gzipped:"
for file in dist/*.js; do
    gzip -c "$file" | wc -c | awk -v file="$file" '{printf "%s\t%.2f KB\n", file, $1/1024}'
done

# Check against targets
DASHBOARD_GZ=$(gzip -c dist/allobye-dashboard.js | wc -c)
DASHBOARD_KB=$((DASHBOARD_GZ / 1024))

echo ""
if [ $DASHBOARD_KB -lt 80 ]; then
    echo "✅ Dashboard bundle: ${DASHBOARD_KB} KB (target: < 80 KB)"
else
    echo "❌ Dashboard bundle: ${DASHBOARD_KB} KB (target: < 80 KB)"
fi
```

**Bundle Analysis**:

```javascript
// File: vite.config.js

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { visualizer } from "rollup-plugin-visualizer";

export default defineConfig({
  plugins: [
    react(),
    visualizer({
      filename: "dist/bundle-stats.html",
      open: true,
      gzipSize: true,
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // Split vendor chunks
          react: ["react", "react-dom"],
          supabase: ["@supabase/supabase-js"],
        },
      },
    },
  },
});
```

#### Success Criteria

- ✅ **PASS**: All bundles < target
- ⚠️ **WARN**: Bundles < target + 20%
- ❌ **FAIL**: Any bundle > target + 20%

---

### 2.3 React Performance

**Metric**: Component render time, re-render frequency
**Measurement Method**: React DevTools Profiler
**Test Conditions**: Dashboard with 20-50 pickups

#### Targets

| Metric | Baseline | 3-Month Target | 12-Month Target | Optimization |
|--------|----------|----------------|-----------------|--------------|
| **Re-renders per minute** | 60 | **< 5** | **< 2** | useMemo + memo |
| **Dashboard render time** | 15-20ms | < 10ms | < 5ms | Memoization |
| **PickupCard render time** | 2-3ms | < 2ms | < 1ms | React.memo |

#### Measurement Script

```javascript
// File: src/allobye-dashboard/dashboard.jsx

import { Profiler } from "react";

let renderCount = 0;
let totalRenderTime = 0;

function onRenderCallback(id, phase, actualDuration, baseDuration, startTime, commitTime) {
  renderCount++;
  totalRenderTime += actualDuration;

  console.log({
    component: id,
    phase, // "mount" or "update"
    renderTime: actualDuration.toFixed(2) + "ms",
    avgRenderTime: (totalRenderTime / renderCount).toFixed(2) + "ms",
    renderCount,
  });

  // Alert if slow render
  if (actualDuration > 50) {
    console.warn(`⚠️ Slow render detected: ${actualDuration.toFixed(2)}ms`);
  }
}

export default function Dashboard() {
  return (
    <Profiler id="Dashboard" onRender={onRenderCallback}>
      {/* ... dashboard content ... */}
    </Profiler>
  );
}
```

#### Success Criteria

- ✅ **PASS**: < 5 re-renders/minute, avg render < 10ms
- ⚠️ **WARN**: 5-10 re-renders/minute, avg render 10-20ms
- ❌ **FAIL**: > 10 re-renders/minute OR avg render > 20ms

---

## 3. Network Performance Benchmarks

### 3.1 API Call Efficiency

**Metric**: API calls per user session
**Measurement Method**: Request logging + analytics
**Test Conditions**: Typical 1-hour dashboard usage

#### Targets

| Scenario | Baseline | 3-Month Target | 12-Month Target | Optimization |
|----------|----------|----------------|-----------------|--------------|
| **API calls/hour** | 133 | **< 80** | **< 50** | Deduplication + adaptive refresh |
| **Redundant calls** | ~30% | **< 10%** | **< 5%** | Request cache |
| **Payload size avg** | 12 KB | **< 7 KB** | **< 5 KB** | Field selection |

#### Measurement Script

```javascript
// File: src/utils/apiCallTracker.js

const apiCallLog = [];

// Intercept all MCP calls
const originalCallTool = window.openai.callTool;
window.openai.callTool = async function(toolName, args) {
  const startTime = Date.now();

  // Call original
  const result = await originalCallTool.call(this, toolName, args);

  // Log call
  apiCallLog.push({
    timestamp: startTime,
    toolName,
    latency: Date.now() - startTime,
    payloadSize: JSON.stringify(args).length,
    responseSize: JSON.stringify(result).length,
  });

  return result;
};

// Analyze after 1 hour
setTimeout(() => {
  const totalCalls = apiCallLog.length;
  const avgLatency = apiCallLog.reduce((sum, log) => sum + log.latency, 0) / totalCalls;
  const avgPayload = apiCallLog.reduce((sum, log) => sum + log.responseSize, 0) / totalCalls;

  console.log("=== API Call Analysis (1 hour) ===");
  console.log(`Total calls: ${totalCalls}`);
  console.log(`Avg latency: ${avgLatency.toFixed(2)}ms`);
  console.log(`Avg response size: ${(avgPayload / 1024).toFixed(2)} KB`);

  // Check targets
  if (totalCalls < 80) {
    console.log("✅ API calls target met");
  } else {
    console.log(`❌ API calls exceeded target: ${totalCalls} (target: < 80)`);
  }
}, 3600000);  // 1 hour
```

#### Success Criteria

- ✅ **PASS**: API calls < target, redundancy < 10%
- ⚠️ **WARN**: API calls < target + 20%, redundancy < 20%
- ❌ **FAIL**: API calls > target + 20% OR redundancy > 20%

---

### 3.2 Real-time Latency

**Metric**: Time from database event to UI update
**Measurement Method**: Server timestamp vs client receipt timestamp
**Test Conditions**: Supabase Realtime WebSocket

#### Targets

| Event Type | Baseline P95 | 3-Month P95 | 12-Month P95 | Notes |
|------------|--------------|-------------|--------------|-------|
| **Pickup Update** | 300ms | < 250ms | < 200ms | DB → Client |
| **Emergency Alert** | 400ms | < 300ms | < 200ms | Critical event |
| **WebSocket Reconnect** | Never | **< 10s** | **< 5s** | 🔥 Add reconnection |

#### Measurement Script

```javascript
// File: src/utils/realtimeLatencyTracker.js

const latencies = [];

// Track latency for each Realtime event
supabase
  .channel("pickups-changes")
  .on("postgres_changes", {...}, (payload) => {
    const serverTimestamp = new Date(payload.commit_timestamp).getTime();
    const clientTimestamp = Date.now();
    const latency = clientTimestamp - serverTimestamp;

    latencies.push(latency);

    console.log(`Realtime latency: ${latency}ms`);

    // Alert if high latency
    if (latency > 500) {
      console.warn(`⚠️ High realtime latency: ${latency}ms`);
    }
  })
  .subscribe();

// Calculate P95 after 100 events
setInterval(() => {
  if (latencies.length >= 100) {
    const sorted = latencies.sort((a, b) => a - b);
    const p95 = sorted[Math.floor(sorted.length * 0.95)];

    console.log(`Realtime P95 latency: ${p95}ms (target: < 250ms)`);
    latencies.length = 0;  // Reset
  }
}, 60000);  // Check every minute
```

#### Success Criteria

- ✅ **PASS**: P95 latency < target for all event types
- ⚠️ **WARN**: P95 latency < target + 50%
- ❌ **FAIL**: P95 latency > target + 50%

---

## 4. Scalability Benchmarks

### 4.1 Concurrent Users Capacity

**Metric**: Number of simultaneous users system can support
**Measurement Method**: Load testing with gradual user ramp-up
**Test Conditions**: Mixed workload, realistic usage patterns

#### Targets

| Resource | Bottleneck | 3-Month Capacity | 12-Month Capacity | Notes |
|----------|------------|------------------|-------------------|-------|
| **Database Connections** | 60 (Supabase free tier) | 50 users | 200 users | Upgrade to Pro tier |
| **WebSocket Connections** | 200 (Supabase free tier) | 100 users | 500 users | Connection pooling |
| **Server Memory** | 512 MB container | 100 users | 500 users | After memory leak fix |
| **Server CPU** | 100% (single core) | 80 users | 300 users | Multi-core scaling |

#### Measurement Script

```python
# File: benchmarks/load_test_scaling.py

from locust import HttpUser, task, between, events

# Track failure rate
failures = 0
successes = 0

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, **kwargs):
    global failures, successes
    if exception:
        failures += 1
    else:
        successes += 1

class AllôByeUser(HttpUser):
    wait_time = between(5, 15)

    @task
    def dashboard_fetch(self):
        # ... (same as throughput test) ...
        pass

# Run with increasing users:
# locust -f benchmarks/load_test_scaling.py --host=http://localhost:8000 \
#        --users=100 --spawn-rate=5 --run-time=10m

# Then analyze:
# - At what user count does error rate exceed 1%?
# - At what user count does P95 latency exceed 2× baseline?
```

#### Success Criteria

- ✅ **PASS**: System handles target users with < 1% error rate, P95 < 2× baseline
- ⚠️ **WARN**: System handles target users with 1-5% error rate, P95 < 3× baseline
- ❌ **FAIL**: Error rate > 5% OR P95 > 3× baseline

---

### 4.2 Database Scalability

**Metric**: Query performance with increasing data volume
**Measurement Method**: Benchmark queries with 10×, 100×, 1000× data
**Test Conditions**: Seed database with scaled-up test data

#### Targets

| Data Volume | Dashboard Query P95 | Authorization Query P95 | Notes |
|-------------|---------------------|-------------------------|-------|
| **Small** (100 pickups) | 25ms | 20ms | Current production |
| **Medium** (2,000 pickups) | < 35ms | < 25ms | 20 schools, 1 year |
| **Large** (20,000 pickups) | < 50ms | < 30ms | 200 schools, 1 year |
| **XLarge** (200,000 pickups) | < 100ms | < 40ms | Future scale |

#### Measurement Script

```sql
-- File: benchmarks/seed_large_dataset.sql

-- Generate 20,000 pickups for testing
INSERT INTO pickups (id, school_id, pickup_person_id, scheduled_time, status)
SELECT
    gen_random_uuid(),
    'school_' || (random() * 20)::int,
    'delegate_' || (random() * 100)::int,
    '2025-01-01'::date + (random() * 365)::int * interval '1 day',
    CASE (random() * 3)::int
        WHEN 0 THEN 'pending'
        WHEN 1 THEN 'confirmed'
        WHEN 2 THEN 'completed'
        ELSE 'cancelled'
    END
FROM generate_series(1, 20000);

-- Benchmark query with large dataset
EXPLAIN ANALYZE
SELECT * FROM pickups
WHERE school_id = 'school_1'
  AND scheduled_time BETWEEN '2025-11-04' AND '2025-11-05'
ORDER BY scheduled_time;

-- Expected: < 50ms even with 20,000 total pickups (returns ~10-20 rows)
```

#### Success Criteria

- ✅ **PASS**: All queries meet targets at all data volumes
- ⚠️ **WARN**: Queries within 50% of targets
- ❌ **FAIL**: Any query exceeds target by > 50%

---

## 5. Monitoring & Alerting

### 5.1 Performance Monitoring Setup

**Tools**: Prometheus + Grafana OR Datadog/NewRelic

#### Key Metrics to Track

```yaml
# File: prometheus/allobye_rules.yml

groups:
  - name: allobye_performance
    interval: 30s
    rules:
      # Alert if P95 latency exceeds target
      - alert: HighMCPLatency
        expr: histogram_quantile(0.95, rate(allobye_tool_latency_ms_bucket[5m])) > 200
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "MCP tool P95 latency above target"
          description: "P95 latency is {{ $value }}ms (target: < 200ms)"

      # Alert if error rate exceeds 5%
      - alert: HighErrorRate
        expr: rate(allobye_tool_errors_total[5m]) / rate(allobye_tool_calls_total[5m]) > 0.05
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Error rate above 5%"

      # Alert if memory usage growing
      - alert: MemoryLeak
        expr: process_resident_memory_bytes > 150000000  # 150 MB
        for: 1h
        labels:
          severity: warning
        annotations:
          summary: "Server memory usage above threshold"

      # Alert if database queries slow
      - alert: SlowDatabaseQueries
        expr: histogram_quantile(0.95, rate(allobye_db_query_latency_ms_bucket[5m])) > 50
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Database P95 latency above 50ms"
```

---

### 5.2 Automated Performance Testing

**CI/CD Integration**: Run benchmarks on every PR

```yaml
# File: .github/workflows/performance-tests.yml

name: Performance Tests
on: [pull_request]

jobs:
  backend-benchmarks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: "3.11"
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run MCP tool benchmarks
        run: python benchmarks/benchmark_mcp_tools.py
      - name: Check against targets
        run: |
          if [ $(cat benchmark_results.json | jq '.pickup_create_p95') -gt 200 ]; then
            echo "❌ pickup-schedule-create P95 exceeds 200ms target"
            exit 1
          fi

  frontend-benchmarks:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Node
        uses: actions/setup-node@v2
      - name: Install dependencies
        run: npm install
      - name: Build bundles
        run: npm run build
      - name: Check bundle sizes
        run: |
          DASHBOARD_SIZE=$(gzip -c dist/allobye-dashboard.js | wc -c)
          if [ $DASHBOARD_SIZE -gt 81920 ]; then  # 80 KB
            echo "❌ Dashboard bundle exceeds 80 KB target"
            exit 1
          fi
      - name: Run Lighthouse CI
        uses: treosh/lighthouse-ci-action@v9
        with:
          urls: http://localhost:3000/allobye-dashboard
          budgetPath: ./lighthouse-budget.json
```

---

## 6. Benchmark Reporting

### 6.1 Weekly Performance Report

**Automated Report Generation**:

```python
# File: benchmarks/generate_report.py

import json
from datetime import datetime

def generate_weekly_report():
    """Generate weekly performance report."""
    report = {
        "week": datetime.now().strftime("%Y-W%W"),
        "metrics": {
            "backend": {
                "mcp_tool_p95": load_metric("mcp_tool_p95"),
                "db_query_p95": load_metric("db_query_p95"),
                "memory_24h": load_metric("memory_24h"),
            },
            "frontend": {
                "bundle_size_gz": load_metric("bundle_size_gz"),
                "widget_load_time": load_metric("widget_load_time"),
                "re_renders_per_min": load_metric("re_renders_per_min"),
            },
            "network": {
                "api_calls_per_hour": load_metric("api_calls_per_hour"),
                "realtime_latency_p95": load_metric("realtime_latency_p95"),
            },
        },
        "targets_met": calculate_targets_met(),
        "improvements_needed": identify_improvements(),
    }

    # Save report
    with open(f"reports/perf_report_{report['week']}.json", "w") as f:
        json.dump(report, f, indent=2)

    # Send to Slack/Email
    send_notification(report)
```

---

## Summary

**Current Performance Grade**: **B+ (Good)**

**Target Performance Grade (3 months)**: **A- (Excellent)**

**Target Performance Grade (12 months)**: **A+ (Outstanding)**

---

**Benchmark Owner**: Évaluateur de Performance
**Review Frequency**: Weekly (automated), Monthly (manual analysis)
**Next Benchmark Review**: 2025-11-18 (après Phase 1 optimizations)
