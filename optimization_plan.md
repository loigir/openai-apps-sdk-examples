# Optimization Plan - AllôBye System

**Date**: 2025-11-04
**Évaluateur**: Évaluateur de Performance
**Plan Duration**: 3 mois (12 semaines)
**Codebase**: AllôBye - Système de coordination de ramassage scolaire

---

## Executive Summary

Ce plan d'optimisation priorise les **10 améliorations de performance critiques** identifiées dans le Bottlenecks Report. Les optimisations sont organisées en 4 phases avec des objectifs SMART et des métriques de succès mesurables.

### Objectifs Globaux

**Performance Targets** (fin du plan - 3 mois):

| Métrique | Baseline | Target | Amélioration |
|----------|----------|--------|--------------|
| MCP Tool P95 Latency | 450ms | **< 200ms** | -56% |
| Dashboard Load Time | 1.5s | **< 0.8s** | -47% |
| Bundle Size (gzipped) | 170 KB | **< 120 KB** | -29% |
| Memory Usage (24h) | 333 MB | **< 100 MB** | -70% |
| API Calls/Hour | 133 | **< 80** | -40% |
| Database Query P95 | 60ms | **< 30ms** | -50% |

**ROI Estimation**:
- **Development Time**: 80-100 hours (2.5 weeks FTE)
- **Performance Gain**: 2-5× faster across all metrics
- **Cost Savings**: -40% Supabase API usage = ~$50/month saved
- **User Experience**: Perceived speed improvement from "acceptable" to "fast"

### Phase Overview

| Phase | Duration | Focus | Effort | Impact |
|-------|----------|-------|--------|--------|
| **Phase 1** | Week 1 | Critical fixes (crashes, N+1) | 16h | Very High |
| **Phase 2** | Week 2-4 | Database optimizations | 32h | High |
| **Phase 3** | Week 5-8 | Frontend optimizations | 24h | Medium-High |
| **Phase 4** | Week 9-12 | Infrastructure & monitoring | 20h | Medium |

---

## Phase 1: Critical Fixes (Week 1)

**Timeline**: November 4-10, 2025
**Effort**: 16 hours (2 days)
**Risk**: Low
**Impact**: Very High (prevents production incidents)

### Objectifs

1. ✅ Éliminer le risque de crash serveur (memory leak)
2. ✅ Réduire latence pickup creation de 50%
3. ✅ Améliorer vitesse dashboard de 30%

---

### OPT-01: Fix Monitoring Memory Leak

**Bottleneck**: BOTTLENECK-02
**Priority**: 🔥 CRITICAL
**Effort**: 1 hour
**Impact**: Prevents server OOM crashes

#### Implementation Steps

**1. Update monitoring.py** (30 minutes)

```python
# File: allobye_server_python/monitoring.py
# Lines: 214-220

from collections import deque

class MetricsCollector:
    def __init__(self, config: MonitoringConfig):
        self.tool_metrics: Dict[str, ToolMetrics] = defaultdict(ToolMetrics)

        # BEFORE (unbounded lists):
        # self.recent_errors: List[Dict[str, Any]] = []
        # self.recent_requests: List[Dict[str, Any]] = []
        # self._alerts: List[Dict[str, Any]] = []

        # AFTER (fixed-size circular buffers):
        self.recent_errors = deque(maxlen=100)      # Keep last 100 errors
        self.recent_requests = deque(maxlen=1000)   # Keep last 1000 requests
        self._alerts = deque(maxlen=50)             # Keep last 50 alerts

        self.db_metrics = DatabaseMetrics()
        self._start_time = time.time()
```

**2. Update method signatures** (15 minutes)

No changes needed - `deque` is a drop-in replacement for `list` with:
- `.append()` ✅ Same
- `[-20:]` slicing ✅ Works
- `len()` ✅ Works
- Only difference: auto-evicts oldest when full

**3. Test** (15 minutes)

```python
# Test memory usage
import sys

metrics = MetricsCollector(MonitoringConfig())

# Simulate 10,000 requests
for i in range(10000):
    metrics.record_tool_call("test-tool", 100, True, None)

# Check memory
print(f"recent_requests length: {len(metrics.recent_requests)}")  # Should be 1000 (maxlen)
print(f"Memory size: {sys.getsizeof(metrics.recent_requests)} bytes")  # Should be ~200 KB
```

#### Success Metrics

- ✅ Memory usage stable after 24h (was growing)
- ✅ `len(recent_requests)` never exceeds 1000
- ✅ No functionality broken (monitoring dashboard still works)

#### Rollback Plan

```bash
git checkout main -- allobye_server_python/monitoring.py
```

---

### OPT-02: Batch Authorization Queries (Fix N+1)

**Bottleneck**: BOTTLENECK-01
**Priority**: 🔥 CRITICAL
**Effort**: 3 hours
**Impact**: -50% latency on pickup creation

#### Implementation Steps

**1. Create new batched authorization function** (60 minutes)

```python
# File: allobye_server_python/auth.py
# Add new function

async def verify_parent_owns_children(
    parent_id: str,
    child_ids: List[str]
) -> Tuple[bool, Optional[str]]:
    """Verify parent owns ALL children in single batched query.

    Args:
        parent_id: Parent's user ID
        child_ids: List of child IDs to verify

    Returns:
        (authorized, error_message) tuple
        - authorized: True if parent owns ALL children
        - error_message: Error description if not authorized
    """
    if not child_ids:
        return False, "No children specified"

    if not parent_id:
        return False, "Parent ID required"

    supabase = get_supabase_admin()

    try:
        # Single query with IN clause
        response = supabase.table("parent_children").select("child_id").eq(
            "parent_id", parent_id
        ).in_("child_id", child_ids).execute()

        owned_child_ids = {row["child_id"] for row in response.data}

        # Check if ALL requested children are owned
        unauthorized = set(child_ids) - owned_child_ids
        if unauthorized:
            return False, f"Not authorized for children: {', '.join(unauthorized)}"

        return True, None

    except Exception as e:
        logger.error("Authorization check failed", error=str(e), parent_id=parent_id)
        return False, f"Authorization check failed: {str(e)}"
```

**2. Update main.py to use batched function** (30 minutes)

```python
# File: allobye_server_python/main.py
# Lines: 1052-1062

async def _handle_pickup_schedule_create(arguments: Dict[str, Any]) -> types.CallToolResult:
    # ... (validation code unchanged) ...

    # BEFORE (N+1 queries):
    # for child_id in payload.child_ids:
    #     if not await verify_parent_owns_child(user.id, child_id):
    #         return error_response()

    # AFTER (single batched query):
    authorized, error_msg = await verify_parent_owns_children(user.id, payload.child_ids)
    if not authorized:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur d'autorisation: {error_msg}",
                )
            ],
            isError=True,
        )

    # ... (rest of function unchanged) ...
```

**3. Add similar batch function for emergency handler** (30 minutes)

```python
# File: allobye_server_python/main.py
# Lines: ~1200 (emergency handler)

async def _handle_emergency_declare(arguments: Dict[str, Any]) -> types.CallToolResult:
    # ... validation ...

    # Single batch check instead of loop
    authorized, error_msg = await verify_parent_owns_children(
        user.id,
        [payload.child_id]  # Single child, but use batch function for consistency
    )
    if not authorized:
        return error_response(error_msg)

    # ... rest of function ...
```

**4. Add tests** (60 minutes)

```python
# File: tests/test_auth_batch.py (new file)

import pytest
from auth import verify_parent_owns_children

@pytest.mark.asyncio
async def test_batch_authorization_all_owned():
    """Test that parent owning all children is authorized."""
    parent_id = "parent-123"
    child_ids = ["child-1", "child-2", "child-3"]

    # Mock: parent owns all 3 children
    authorized, error = await verify_parent_owns_children(parent_id, child_ids)

    assert authorized == True
    assert error is None

@pytest.mark.asyncio
async def test_batch_authorization_some_unauthorized():
    """Test that missing one child fails authorization."""
    parent_id = "parent-123"
    child_ids = ["child-1", "child-2", "child-999"]  # child-999 not owned

    authorized, error = await verify_parent_owns_children(parent_id, child_ids)

    assert authorized == False
    assert "child-999" in error

@pytest.mark.asyncio
async def test_batch_authorization_empty_list():
    """Test edge case: empty child list."""
    parent_id = "parent-123"
    child_ids = []

    authorized, error = await verify_parent_owns_children(parent_id, child_ids)

    assert authorized == False
    assert "No children" in error
```

#### Success Metrics

**Performance**:
- ✅ 1 child: 100ms → 100ms (no change)
- ✅ 5 children: 500ms → **100ms** (-80%)
- ✅ 10 children: 1000ms → **100ms** (-90%)

**Database Load**:
- ✅ Queries per pickup creation: 5 → **1** (-80%)

#### Rollback Plan

```python
# Keep old function as fallback
async def verify_parent_owns_child_single(parent_id: str, child_id: str) -> bool:
    """Legacy single-child verification (fallback)."""
    authorized, _ = await verify_parent_owns_children(parent_id, [child_id])
    return authorized
```

---

### OPT-03: Add Composite Index on Pickups

**Bottleneck**: BOTTLENECK-05
**Priority**: 🟠 HIGH
**Effort**: 30 minutes
**Impact**: -28% dashboard query latency

#### Implementation Steps

**1. Create migration SQL** (10 minutes)

```sql
-- File: allobye_server_python/migrations/003_add_composite_indexes.sql

-- Composite index for dashboard query
-- Covers: WHERE school_id = ? AND scheduled_time BETWEEN ? AND ?
-- Includes status and pickup_person_id to avoid heap lookups
CREATE INDEX CONCURRENTLY idx_pickups_school_scheduled
ON pickups(school_id, scheduled_time)
INCLUDE (status, pickup_person_id);

-- Partial index for active pickups only (smaller, faster)
CREATE INDEX CONCURRENTLY idx_pickups_active_school_scheduled
ON pickups(school_id, scheduled_time)
WHERE status IN ('pending', 'confirmed', 'in_progress');

-- Verify indexes created
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'pickups'
ORDER BY indexname;

-- Analyze query plan (should use new index)
EXPLAIN ANALYZE
SELECT * FROM pickups
WHERE school_id = 'school_1'
AND scheduled_time BETWEEN '2025-11-04 14:00:00' AND '2025-11-04 16:00:00'
ORDER BY scheduled_time;
```

**2. Run migration** (10 minutes)

```bash
# Apply migration to Supabase
psql $SUPABASE_DATABASE_URL -f allobye_server_python/migrations/003_add_composite_indexes.sql

# Note: CONCURRENTLY ensures no table locking (safe for production)
```

**3. Test query performance** (10 minutes)

```python
# File: tests/test_index_performance.py

import time

async def benchmark_dashboard_query():
    """Measure dashboard query performance."""
    school_id = "school_1"
    start = time.time()

    response = supabase.table("pickups").select(
        "*, children(*), pickup_person:delegates(*)"
    ).eq("school_id", school_id).gte(
        "scheduled_time", "2025-11-04T14:00:00Z"
    ).lte(
        "scheduled_time", "2025-11-04T16:00:00Z"
    ).order("scheduled_time").execute()

    latency = (time.time() - start) * 1000
    print(f"Dashboard query: {latency:.2f}ms")
    assert latency < 30, f"Query too slow: {latency}ms"
```

#### Success Metrics

- ✅ Dashboard query: 35ms → **25ms** (-28%)
- ✅ Query plan uses `idx_pickups_school_scheduled` (verify with EXPLAIN)
- ✅ Index size: < 10 MB (check with `pg_relation_size()`)

---

## Phase 2: Database Optimizations (Week 2-4)

**Timeline**: November 11 - December 1, 2025
**Effort**: 32 hours (4 days)
**Risk**: Medium
**Impact**: High (44× speedup on large datasets)

---

### OPT-04: Optimize RLS Policies with Materialized Views

**Bottleneck**: BOTTLENECK-03
**Priority**: 🔥 CRITICAL (for large schools)
**Effort**: 12 hours
**Impact**: -77% dashboard load time

#### Implementation Steps

**1. Create materialized view** (3 hours)

```sql
-- File: allobye_server_python/migrations/004_materialized_pickups.sql

-- Materialized view with pre-joined data
CREATE MATERIALIZED VIEW mv_parent_pickups AS
SELECT
    p.id,
    p.school_id,
    p.scheduled_time,
    p.status,
    p.notes,
    p.pickup_person_id,
    p.created_at,
    p.updated_at,
    c.parent_email,
    -- Aggregate children as JSON
    jsonb_agg(DISTINCT jsonb_build_object(
        'id', ch.id,
        'name', ch.name,
        'grade', ch.grade
    )) AS children,
    -- Aggregate pickup person as JSON
    jsonb_build_object(
        'id', d.id,
        'name', d.name,
        'phone', d.phone
    ) AS pickup_person
FROM pickups p
JOIN pickup_children pc ON p.id = pc.pickup_id
JOIN children ch ON pc.child_id = ch.id
JOIN delegates d ON p.pickup_person_id = d.id
GROUP BY p.id, p.school_id, p.scheduled_time, p.status, p.notes,
         p.pickup_person_id, p.created_at, p.updated_at, ch.parent_email,
         d.id, d.name, d.phone;

-- Create indexes for fast lookup
CREATE INDEX idx_mv_parent_pickups_email
ON mv_parent_pickups(parent_email);

CREATE INDEX idx_mv_parent_pickups_school_scheduled
ON mv_parent_pickups(school_id, scheduled_time);

-- Enable RLS on materialized view
ALTER MATERIALIZED VIEW mv_parent_pickups ENABLE ROW LEVEL SECURITY;

-- Simple RLS policy (no complex subquery!)
CREATE POLICY "Parents see their pickups" ON mv_parent_pickups FOR SELECT
    USING (parent_email = auth.jwt()->>'email');
```

**2. Create refresh mechanism** (2 hours)

```sql
-- Function to refresh materialized view
CREATE OR REPLACE FUNCTION refresh_parent_pickups_mv()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY mv_parent_pickups;
    -- Log refresh
    INSERT INTO system_logs (event, details)
    VALUES ('mv_refresh', jsonb_build_object('view', 'mv_parent_pickups', 'timestamp', NOW()));
END;
$$ LANGUAGE plpgsql;

-- Schedule refresh every 5 minutes (via pg_cron or external scheduler)
-- Note: Supabase may not support pg_cron in free tier, use external cron job
```

**3. Update application code** (4 hours)

```python
# File: allobye_server_python/main.py

async def get_school_pickups_optimized(
    school_id: str,
    date: str,
    time_window: str,
) -> List[Dict[str, Any]]:
    """Get pickup queue using optimized materialized view."""
    supabase = get_supabase()

    # Calculate time range
    now = datetime.now()
    if time_window == "current":
        start_time = now
        end_time = now + timedelta(minutes=30)
    # ... (time window logic unchanged) ...

    try:
        # Query materialized view instead of base table
        # NOTE: Materialized view has data up to 5 minutes old
        response = supabase.table("mv_parent_pickups").select(
            "*"  # All data pre-joined!
        ).eq("school_id", school_id).gte(
            "scheduled_time", start_time.isoformat()
        ).lte(
            "scheduled_time", end_time.isoformat()
        ).order("scheduled_time").execute()

        # Data already has children and pickup_person as JSON
        # No additional queries needed!
        return response.data

    except Exception as e:
        logger.error("Error fetching pickups from MV", error=str(e))
        # Fallback to original query if MV fails
        return await get_school_pickups_original(school_id, date, time_window)
```

**4. External refresh scheduler** (2 hours)

```python
# File: scripts/refresh_materialized_views.py

import os
import schedule
import time
from supabase import create_client

def refresh_views():
    """Refresh all materialized views."""
    supabase = create_client(
        os.getenv("SUPABASE_URL"),
        os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    )

    try:
        # Call refresh function
        supabase.rpc("refresh_parent_pickups_mv").execute()
        print(f"[{datetime.now()}] Materialized view refreshed successfully")
    except Exception as e:
        print(f"[{datetime.now()}] Error refreshing MV: {e}")

# Schedule refresh every 5 minutes
schedule.every(5).minutes.do(refresh_views)

print("Materialized view refresh scheduler started (every 5 min)")
while True:
    schedule.run_pending()
    time.sleep(60)
```

**5. Test & benchmark** (1 hour)

```python
# Compare performance
async def benchmark_mv_vs_original():
    school_id = "school_1"

    # Original query
    start = time.time()
    original = await get_school_pickups_original(school_id, "today", "current")
    original_time = (time.time() - start) * 1000

    # Materialized view query
    start = time.time()
    optimized = await get_school_pickups_optimized(school_id, "today", "current")
    optimized_time = (time.time() - start) * 1000

    print(f"Original: {original_time:.2f}ms")
    print(f"Optimized: {optimized_time:.2f}ms")
    print(f"Speedup: {original_time / optimized_time:.1f}×")

    # Verify data consistency
    assert len(original) == len(optimized), "Row count mismatch"
```

#### Success Metrics

**Performance** (50 pickups):
- ✅ Query time: 1310ms → **30ms** (44× speedup)
- ✅ No RLS subquery overhead
- ✅ Dashboard load: 1.5s → **0.5s** (-67%)

**Data Freshness**:
- ✅ Data staleness: < 5 minutes (acceptable for dashboard)
- ✅ Real-time updates via WebSocket still work (bypass MV)

**Storage**:
- ✅ MV size: ~5-10 MB (10-20% of base tables)

#### Rollback Plan

```sql
-- Disable MV usage in code, revert to original queries
-- Keep MV for later use (no harm in existence)
```

---

### OPT-05: Reduce JSON Payload Sizes

**Bottleneck**: BOTTLENECK-06
**Priority**: 🟠 HIGH
**Effort**: 4 hours
**Impact**: -60% payload size, -58% transfer time

#### Implementation Steps

**1. Update dashboard query to select specific fields** (2 hours)

```python
# File: allobye_server_python/main.py

async def get_school_pickups_lean(
    school_id: str,
    date: str,
    time_window: str,
) -> List[Dict[str, Any]]:
    """Get pickup queue with minimal payload."""
    supabase = get_supabase()

    # ... (time window logic unchanged) ...

    # BEFORE (returns ALL columns):
    # response = supabase.table("pickups").select(
    #     "*, children(*), pickup_person:delegates(*)"
    # )...

    # AFTER (select only required fields):
    response = supabase.table("pickups").select(
        """
        id,
        scheduled_time,
        status,
        notes,
        children:pickup_children(
            child:children(
                id,
                name,
                grade
            )
        ),
        pickup_person:delegates(
            id,
            name,
            phone
        )
        """
    ).eq("school_id", school_id).gte(
        "scheduled_time", start_time.isoformat()
    ).lte(
        "scheduled_time", end_time.isoformat()
    ).order("scheduled_time").execute()

    return response.data
```

**2. Update monitoring dashboard query** (1 hour)

```python
# File: allobye_server_python/main.py

async def _handle_monitoring_dashboard_fetch(...):
    # ... existing code ...

    # Minimize metrics payload
    dashboard_data = {
        "uptime": int(metrics_collector.get_uptime()),
        "total_requests": metrics_collector.total_requests,
        "error_rate": metrics_collector.get_overall_error_rate(),
        "avg_latency": metrics_collector.get_overall_avg_latency(),

        # Top 5 tools only (instead of all 10)
        "top_tools": metrics_collector.get_top_tools(limit=5),

        # Last 10 errors only (instead of 20)
        "recent_errors": list(metrics_collector.recent_errors)[-10:],

        # Last 20 requests only (instead of 50)
        "recent_requests": list(metrics_collector.recent_requests)[-20:],

        # Alerts (full list, usually < 10)
        "alerts": list(metrics_collector._alerts),

        # Database metrics (aggregate only, no details)
        "db": {
            "total_queries": metrics_collector.db_metrics.total_queries,
            "avg_latency": metrics_collector.db_metrics.get_avg_latency(),
        },
    }
    # ... return ...
```

**3. Test payload sizes** (1 hour)

```python
# Test payload reduction
import json

def measure_payload_size(data):
    """Measure JSON payload size."""
    json_str = json.dumps(data)
    size_bytes = len(json_str.encode('utf-8'))
    return size_bytes

# Before
pickups_full = await get_school_pickups_original(school_id, "today", "current")
size_before = measure_payload_size(pickups_full)

# After
pickups_lean = await get_school_pickups_lean(school_id, "today", "current")
size_after = measure_payload_size(pickups_lean)

print(f"Payload size before: {size_before / 1024:.2f} KB")
print(f"Payload size after: {size_after / 1024:.2f} KB")
print(f"Reduction: {(1 - size_after / size_before) * 100:.1f}%")

# Verify data completeness
assert all(k in pickups_lean[0] for k in ["id", "scheduled_time", "children"])
```

#### Success Metrics

**Payload Sizes** (20 pickups):
- ✅ Dashboard: 50 KB → **20 KB** (-60%)
- ✅ Monitoring: 30 KB → **12 KB** (-60%)

**Transfer Times** (3G network):
- ✅ Dashboard: 480ms → **200ms** (-58%)
- ✅ Monitoring: 300ms → **120ms** (-60%)

**Monthly Bandwidth** (20 schools):
- ✅ Data transfer: 3.2 GB → **1.3 GB** (-59%)

---

### OPT-06: Add Missing Indexes for Authorization

**Bottleneck**: Related to BOTTLENECK-01
**Priority**: 🟠 HIGH
**Effort**: 1 hour
**Impact**: -20% authorization query time

#### Implementation Steps

```sql
-- File: allobye_server_python/migrations/005_authorization_indexes.sql

-- Index for parent_children lookup (used in batched authorization)
CREATE INDEX CONCURRENTLY idx_parent_children_parent_id
ON parent_children(parent_id);

-- Index for children by parent email (used in RLS policies)
CREATE INDEX CONCURRENTLY idx_children_parent_email
ON children(parent_email);

-- Index for delegate_children lookup
CREATE INDEX CONCURRENTLY idx_delegate_children_delegate_id
ON delegate_children(delegate_id);

-- Verify
SELECT schemaname, tablename, indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('parent_children', 'children', 'delegate_children')
ORDER BY tablename, indexname;
```

#### Success Metrics

- ✅ Batched authorization: 100ms → **80ms** (-20%)
- ✅ RLS policy evaluation: 20ms → **15ms** (-25%)

---

## Phase 3: Frontend Optimizations (Week 5-8)

**Timeline**: December 2-29, 2025
**Effort**: 24 hours (3 days)
**Risk**: Low
**Impact**: Medium-High

---

### OPT-07: Fix React Re-render Performance

**Bottleneck**: BOTTLENECK-04
**Priority**: 🟠 HIGH
**Effort**: 4 hours
**Impact**: -98% unnecessary re-renders

#### Implementation Steps

**1. Memoize filteredPickups with minute granularity** (2 hours)

```javascript
// File: src/allobye-dashboard/dashboard.jsx

import { useEffect, useState, useMemo } from "react";

export default function Dashboard() {
  // ... existing code ...

  // Update time only when minute changes (instead of every second)
  const [currentMinute, setCurrentMinute] = useState(
    new Date().getMinutes()
  );

  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date();
      const newMinute = now.getMinutes();

      // Only update if minute actually changed
      if (newMinute !== currentMinute) {
        setCurrentMinute(newMinute);
        setCurrentTime(now);  // Update full time for display
      }
    }, 1000);

    return () => clearInterval(timer);
  }, [currentMinute]);

  // Memoize filtered data - only recalculate when dependencies change
  const filteredPickups = useMemo(() => {
    return pickups.filter((pickup) => {
      if (state.filter === "all") return true;

      if (state.filter === "next_30min") {
        const scheduledTime = new Date(pickup.scheduled_time);
        const thirtyMinutesFromNow = new Date(currentTime.getTime() + 30 * 60 * 1000);
        return scheduledTime <= thirtyMinutesFromNow;
      }

      if (state.filter === "delays") {
        return pickup.delay && pickup.delay > 0;
      }

      return true;
    });
  }, [pickups, state.filter, currentMinute]);  // Only when minute changes!

  // ... rest of component ...
}
```

**2. Memoize PickupCard component** (1 hour)

```javascript
// File: src/allobye-dashboard/pickup-card.jsx

import React from "react";

function PickupCard({ pickup, currentTime }) {
  // ... existing rendering logic ...
}

// Memoize component to prevent re-renders when props haven't changed
export default React.memo(PickupCard, (prevProps, nextProps) => {
  // Only re-render if pickup or relevant time changed
  return (
    prevProps.pickup.id === nextProps.pickup.id &&
    prevProps.pickup.status === nextProps.pickup.status &&
    prevProps.currentTime.getMinutes() === nextProps.currentTime.getMinutes()
  );
});
```

**3. Test performance** (1 hour)

```javascript
// Add React DevTools Profiler
import { Profiler } from "react";

function Dashboard() {
  const onRenderCallback = (id, phase, actualDuration) => {
    console.log(`${id} (${phase}) took ${actualDuration}ms`);
  };

  return (
    <Profiler id="Dashboard" onRender={onRenderCallback}>
      {/* ... existing dashboard JSX ... */}
    </Profiler>
  );
}
```

#### Success Metrics

**Re-render Frequency**:
- ✅ Before: 60 renders/minute
- ✅ After: **1 render/minute** (-98%)

**CPU Usage**:
- ✅ Before: 8-12% CPU (continuous)
- ✅ After: **< 1% CPU** (idle between minutes)

**Battery Impact**:
- ✅ 8-hour battery → **Full 8-hour usage** (no extra drain)

---

### OPT-08: Implement WebSocket Reconnection

**Bottleneck**: BOTTLENECK-07
**Priority**: 🟠 HIGH
**Effort**: 8 hours
**Impact**: 99% uptime (vs 90%)

#### Implementation Steps

**1. Add reconnection logic** (4 hours)

```javascript
// File: src/allobye-dashboard/dashboard.jsx

const [isRealtimeConnected, setIsRealtimeConnected] = useState(false);
const reconnectAttempts = useRef(0);
const MAX_RECONNECT_ATTEMPTS = 10;
const MAX_BACKOFF_DELAY = 60000; // 60 seconds

const setupRealtimeSubscription = useCallback(async () => {
  try {
    const { createClient } = await import("@supabase/supabase-js");
    const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
    const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

    if (!supabaseUrl || !supabaseKey) {
      console.warn("Supabase credentials not configured");
      return;
    }

    const supabase = createClient(supabaseUrl, supabaseKey);

    const channel = supabase
      .channel("pickups-changes")
      .on("postgres_changes", {...}, handlePickupChange)
      .subscribe((status, error) => {
        console.log(`Realtime status: ${status}`, error);

        if (status === "SUBSCRIBED") {
          setIsRealtimeConnected(true);
          reconnectAttempts.current = 0;  // Reset on successful connection
        }

        if (status === "CLOSED" || status === "CHANNEL_ERROR") {
          setIsRealtimeConnected(false);

          // Stop retrying after max attempts
          if (reconnectAttempts.current >= MAX_RECONNECT_ATTEMPTS) {
            console.error("Max reconnection attempts reached. Stopping.");
            return;
          }

          // Exponential backoff: 1s, 2s, 4s, 8s, ... max 60s
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttempts.current),
            MAX_BACKOFF_DELAY
          );

          reconnectAttempts.current++;

          console.log(
            `Reconnecting in ${delay / 1000}s (attempt ${reconnectAttempts.current}/${MAX_RECONNECT_ATTEMPTS})...`
          );

          setTimeout(() => {
            setupRealtimeSubscription();  // Retry
          }, delay);
        }
      });

    return () => channel.unsubscribe();
  } catch (error) {
    console.error("Realtime setup error:", error);
    setIsRealtimeConnected(false);
  }
}, [schoolInfo?.id]);
```

**2. Add connection status UI** (2 hours)

```javascript
// File: src/allobye-dashboard/dashboard.jsx

return (
  <div className="allobye-dashboard fullscreen">
    {/* Connection status indicator */}
    {!isRealtimeConnected && (
      <div className="connection-alert warning">
        <span className="icon">⚠️</span>
        <span className="message">
          Connexion temps réel perdue. Reconnexion en cours...
        </span>
        <span className="attempts">
          Tentative {reconnectAttempts.current}/{MAX_RECONNECT_ATTEMPTS}
        </span>
      </div>
    )}

    {/* ... rest of dashboard ... */}

    <footer className="dashboard-footer">
      {/* ... other controls ... */}

      <div className="status-indicator">
        <span className={`status-dot ${isRealtimeConnected ? "online" : "offline"}`}></span>
        {isRealtimeConnected ? "Connecté" : "Déconnecté"}
      </div>
    </footer>
  </div>
);
```

**3. Fallback to polling when disconnected** (2 hours)

```javascript
// Increase polling frequency when WebSocket down
useEffect(() => {
  if (!isRealtimeConnected && schoolInfo?.id) {
    console.log("WebSocket disconnected - switching to fast polling (5s)");

    const interval = setInterval(() => {
      window.openai.callTool("school-dashboard-fetch", {
        schoolId: schoolInfo.id,
        timeWindow: "current",
      }).catch((err) => console.error("Polling error:", err));
    }, 5000);  // Poll every 5 seconds instead of 30

    return () => clearInterval(interval);
  }
}, [isRealtimeConnected, schoolInfo]);
```

#### Success Metrics

**Reliability**:
- ✅ Connection uptime: 90% → **99%**
- ✅ Reconnection time: Never → **< 10 seconds**
- ✅ Data loss: Frequent → **Zero** (polling fallback)

**User Experience**:
- ✅ Silent failures → **Visible status indicator**
- ✅ No awareness → **User informed of connection state**

---

### OPT-09: Lazy Load Supabase SDK

**Bottleneck**: BOTTLENECK-08
**Priority**: 🟡 MEDIUM
**Effort**: 2 hours
**Impact**: -35 KB initial bundle

#### Implementation Steps

```javascript
// File: src/allobye-dashboard/dashboard.jsx

// BEFORE: Imported at top level (always loaded)
// import { createClient } from "@supabase/supabase-js";

// AFTER: Dynamic import when needed
useEffect(() => {
  const setupRealtimeSubscription = async () => {
    // Lazy load Supabase SDK only when setting up Realtime
    const { createClient } = await import("@supabase/supabase-js");

    const supabase = createClient(supabaseUrl, supabaseKey);
    // ... rest of setup ...
  };

  setupRealtimeSubscription();
}, []);
```

#### Success Metrics

- ✅ Initial bundle: 373 KB → **338 KB** (-35 KB, -9%)
- ✅ Gzipped bundle: 108 KB → **88 KB** (-20 KB, -18%)
- ✅ Initial load: 1.5s → **1.35s** (-10%)

---

### OPT-10: Add Request Deduplication

**Bottleneck**: BOTTLENECK-09
**Priority**: 🟡 MEDIUM
**Effort**: 3 hours
**Impact**: -30% redundant API calls

#### Implementation Steps

```javascript
// File: src/utils/requestCache.js (new file)

const requestCache = new Map();
const CACHE_TTL = 5000; // 5 seconds

export async function callToolWithCache(toolName, args) {
  const cacheKey = JSON.stringify({ toolName, args });
  const cached = requestCache.get(cacheKey);

  // Return cached result if fresh
  if (cached && Date.now() - cached.timestamp < CACHE_TTL) {
    console.log(`Cache hit: ${toolName}`);
    return cached.result;
  }

  console.log(`Cache miss: ${toolName} - making API call`);

  // Make actual request
  const result = await window.openai.callTool(toolName, args);

  // Cache result
  requestCache.set(cacheKey, {
    result,
    timestamp: Date.now(),
  });

  // Auto-cleanup after TTL
  setTimeout(() => {
    requestCache.delete(cacheKey);
  }, CACHE_TTL);

  return result;
}
```

#### Success Metrics

- ✅ Redundant API calls: 30-40% → **0%**
- ✅ API quota usage: 133 calls/hour → **~90 calls/hour** (-32%)

---

## Phase 4: Infrastructure & Monitoring (Week 9-12)

**Timeline**: January 2025
**Effort**: 20 hours
**Risk**: Low
**Impact**: Medium (operational improvements)

### OPT-11: Add Performance Monitoring

**Effort**: 8 hours
**Tools**: Prometheus + Grafana OR Datadog/NewRelic

### OPT-12: Database Connection Pooling Config

**Effort**: 4 hours
**Impact**: Better handling of concurrent requests

### OPT-13: Implement Adaptive Refresh Rate

**Effort**: 6 hours
**Impact**: -40% API calls during quiet periods

### OPT-14: Add Performance Tests (CI/CD)

**Effort**: 2 hours
**Impact**: Prevent performance regressions

---

## Success Metrics & Monitoring

### Key Performance Indicators (KPIs)

**Week 1** (after Phase 1):
- ✅ Server uptime: 100% (no OOM crashes)
- ✅ Pickup creation P95: < 200ms
- ✅ Dashboard load P95: < 500ms

**Week 4** (after Phase 2):
- ✅ Dashboard load P95: < 350ms
- ✅ Payload sizes: -60%
- ✅ Database queries: -40%

**Week 8** (after Phase 3):
- ✅ Bundle size: < 120 KB gzipped
- ✅ Frontend CPU: < 2%
- ✅ Real-time uptime: 99%

**Week 12** (after Phase 4):
- ✅ All targets met
- ✅ Monitoring in place
- ✅ Performance tests automated

---

## Risk Mitigation

### Rollback Strategy

Each optimization has:
1. ✅ Feature flags for gradual rollout
2. ✅ Fallback to previous implementation
3. ✅ Database migration reversibility (where applicable)

### Testing Strategy

1. **Unit Tests**: All new functions
2. **Integration Tests**: Database queries, API endpoints
3. **Performance Tests**: Benchmarks before/after
4. **Load Tests**: Simulate 50-100 concurrent users

---

## Resource Requirements

**Team**: 1 Full-Stack Developer
**Timeline**: 12 weeks (part-time, ~7h/week)
**Infrastructure**: No additional costs (uses existing Supabase tier)

---

**Plan Owner**: Évaluateur de Performance
**Approvals Required**: Tech Lead, Product Manager
**Next Review**: 2025-11-18 (après Phase 1)
