# State Management Analysis - AllôBye System

**Date**: 2025-11-04
**Analyzer**: Traceur de Flux de Données
**Codebase**: AllôBye School Pickup Coordination System

---

## Executive Summary

AllôBye implements a **multi-layered state management architecture** spanning three distinct domains:

1. **Client-side State** (React): Ephemeral UI state, view preferences, real-time subscriptions
2. **Server-side State** (MCP Server): Stateless HTTP with monitoring/metrics aggregation
3. **Persistent State** (PostgreSQL): Authoritative source of truth with RLS policies

**Key Findings**:
- ✅ Clear separation between transient (React) and persistent (DB) state
- ⚠️ Frontend directly accesses database via Supabase Realtime (bypasses application layer)
- ✅ Stateless MCP server design enables horizontal scaling
- ⚠️ No distributed session management (relies on JWT in localStorage)
- ✅ Comprehensive monitoring state tracked in-memory with proper cleanup

---

## 1. React Frontend State Management

### 1.1 State Categories

#### **A. Local Component State (useState)**

**Location**: `/src/allobye-dashboard/dashboard.jsx`

```javascript
// Ephemeral UI state
const [currentTime, setCurrentTime] = useState(new Date());
const [realtimePickups, setRealtimePickups] = useState([]);
```

**Characteristics**:
- **Scope**: Single component
- **Lifetime**: Component mount → unmount
- **Persistence**: None (lost on refresh)
- **Update Frequency**: High (currentTime updates every second)

**Purpose**:
- `currentTime`: Clock display, pickup ETA calculations
- `realtimePickups`: Buffer for WebSocket updates before merge with MCP data

**State Mutations**:
```javascript
// Timer-driven mutation (every 1s)
useEffect(() => {
  const timer = setInterval(() => {
    setCurrentTime(new Date());
  }, 1000);
  return () => clearInterval(timer);
}, []);

// WebSocket-driven mutation (event-based)
.on("postgres_changes", (payload) => {
  setRealtimePickups((prev) => {
    const updated = prev.filter((p) => p.id !== payload.new.id);
    return [...updated, payload.new].sort(...);
  });
});
```

**Risks**:
- ⚠️ Race condition: `realtimePickups` updates can conflict with MCP tool data
- ⚠️ No debouncing on WebSocket events (rapid updates could cause thrashing)
- ✅ Cleanup properly handled with `return () => clearInterval()`

---

#### **B. Widget Persistent State (useWidgetState)**

**Location**: `/src/use-widget-state.ts`

```typescript
const [state, setState] = useWidgetState({
  view: "timeline",      // UI layout preference
  filter: "all",         // Data filter setting
  alert: null,           // Active emergency alert
});
```

**Characteristics**:
- **Scope**: Widget session (persists across re-renders)
- **Lifetime**: Widget load → widget close
- **Persistence**: `window.openai.widgetState` (ChatGPT session)
- **Sync**: Bidirectional with OpenAI global store

**Implementation Details**:
```typescript
// Reads from OpenAI global store
const widgetStateFromWindow = useOpenAiGlobal("widgetState") as T;

// Writes back to OpenAI store
const setWidgetState = useCallback((state: SetStateAction<T | null>) => {
  _setWidgetState((prevState) => {
    const newState = typeof state === "function" ? state(prevState) : state;
    if (newState != null) {
      window.openai.setWidgetState(newState);  // Persist
    }
    return newState;
  });
}, [window.openai.setWidgetState]);
```

**State Flow**:
```
User Action → setState() → setWidgetState() → window.openai.setWidgetState()
                                            ↓
                              Trigger SET_GLOBALS_EVENT_TYPE
                                            ↓
                     Other components listening via useSyncExternalStore
```

**Benefits**:
- ✅ View preferences persist across widget reloads
- ✅ Emergency alerts survive component re-mounts
- ✅ Type-safe with TypeScript generics

**Concerns**:
- ⚠️ No versioning (state schema changes could break saved states)
- ⚠️ Limited to OpenAI widget environment (not portable)

---

#### **C. Authentication State (localStorage + React)**

**Location**: `/src/allobye-dashboard/index.jsx`

```javascript
const [authState, setAuthState] = useState({
  isAuthenticated: false,
  token: null,
  user: null,
  loading: true,
});

// Persist to localStorage
localStorage.setItem("allobye_token", token);
localStorage.setItem("allobye_user", JSON.stringify(user));

// Restore on mount
useEffect(() => {
  const token = localStorage.getItem("allobye_token");
  const userStr = localStorage.getItem("allobye_user");
  // ... restore authState
}, []);
```

**Characteristics**:
- **Scope**: Browser session (cross-tab if same origin)
- **Lifetime**: Until logout or localStorage.clear()
- **Persistence**: Browser localStorage (survives refresh)
- **Security**: JWT stored as plain text (vulnerable to XSS)

**State Lifecycle**:
```
1. Signup/Login → Supabase Auth → JWT access_token
                                        ↓
2. Store in localStorage ("allobye_token", "allobye_user")
                                        ↓
3. Every tool call includes accessToken in arguments
                                        ↓
4. MCP server validates via auth.validate_session()
                                        ↓
5. Logout → localStorage.removeItem() + server-side session invalidation
```

**Security Analysis**:
- ⚠️ **XSS Vulnerability**: JWT in localStorage accessible to any script
- ⚠️ **No HttpOnly cookies**: Can't use more secure cookie-based auth
- ✅ **Token expiration**: JWT has built-in expiry (enforced by Supabase)
- ⚠️ **No refresh token rotation**: Refresh tokens stored alongside access tokens
- ⚠️ **CSRF risk**: No CSRF protection (stateless MCP server)

**Recommendations**:
1. Use `sessionStorage` instead of `localStorage` for better security
2. Implement token refresh logic before expiry
3. Add CSP headers to mitigate XSS
4. Consider secure cookie storage if ChatGPT Apps SDK supports it

---

### 1.2 State Synchronization Mechanisms

#### **A. useSyncExternalStore (React 18)**

**Location**: `/src/use-openai-global.ts`

```typescript
export function useOpenAiGlobal<K extends keyof OpenAiGlobals>(
  key: K
): OpenAiGlobals[K] | null {
  return useSyncExternalStore(
    // Subscribe function
    (onChange) => {
      const handleSetGlobal = (event: SetGlobalsEvent) => {
        const value = event.detail.globals[key];
        if (value === undefined) return;
        onChange();  // Notify React of external change
      };
      window.addEventListener(SET_GLOBALS_EVENT_TYPE, handleSetGlobal);
      return () => window.removeEventListener(SET_GLOBALS_EVENT_TYPE, handleSetGlobal);
    },
    // Get snapshot function
    () => window.openai?.[key] ?? null,
    // Get server snapshot (SSR)
    () => window.openai?.[key] ?? null
  );
}
```

**Purpose**: Bridge between OpenAI global store and React component state

**Benefits**:
- ✅ Concurrent-mode safe (React 18)
- ✅ Prevents tearing (state inconsistency during concurrent renders)
- ✅ Automatic re-render on external store changes

**Flow**:
```
OpenAI Global Store Change
        ↓
SET_GLOBALS_EVENT_TYPE dispatched
        ↓
useSyncExternalStore detects change
        ↓
React re-renders subscribed components
        ↓
Components read fresh window.openai[key]
```

---

#### **B. Supabase Realtime Subscriptions**

**Location**: `/src/allobye-dashboard/dashboard.jsx` (lines 56-144)

```javascript
const channel = supabase
  .channel("pickups-changes")
  .on("postgres_changes", {
    event: "*",
    schema: "public",
    table: "pickups",
    filter: `school_id=eq.${schoolInfo.id}`,
  }, (payload) => {
    // Direct state mutation from database event
    setRealtimePickups((prev) => { /* ... */ });
  })
  .subscribe();
```

**Characteristics**:
- **Protocol**: WebSocket (persistent connection)
- **Filter**: Server-side filtering by `school_id`
- **Events**: INSERT, UPDATE, DELETE on `pickups` table
- **Latency**: ~50-200ms from DB commit to UI update

**State Update Logic**:
```javascript
if (payload.eventType === "INSERT" || payload.eventType === "UPDATE") {
  setRealtimePickups((prev) => {
    // Remove old version (if UPDATE)
    const updated = prev.filter((p) => p.id !== payload.new.id);
    // Add new version and sort
    return [...updated, payload.new].sort(
      (a, b) => new Date(a.scheduled_time) - new Date(b.scheduled_time)
    );
  });
} else if (payload.eventType === "DELETE") {
  setRealtimePickups((prev) => prev.filter((p) => p.id !== payload.old.id));
}
```

**Concerns**:
- ⚠️ **Schema Coupling**: Frontend knows DB table structure (`pickups`, `emergencies`)
- ⚠️ **No Optimistic Updates**: UI waits for DB commit → WebSocket event
- ⚠️ **Network Reliability**: No reconnection backoff or offline handling
- ⚠️ **Data Consistency**: `realtimePickups` can diverge from `metadata.pickups`

**Merge Strategy**:
```javascript
// Priority: MCP tool data > Realtime updates
const pickups = metadata?.pickups || realtimePickups || [];
```

This means:
1. If MCP tool has fresh data (`metadata.pickups`), use it
2. Else if Realtime has pushed updates (`realtimePickups`), use those
3. Else empty array

**Issue**: If both exist, MCP data wins even if Realtime is newer!

---

### 1.3 State Update Patterns

#### **Pattern 1: Controlled Intervals (Polling)**

```javascript
useEffect(() => {
  const interval = setInterval(() => {
    window.openai?.callTool("school-dashboard-fetch", {
      schoolId: schoolInfo.id,
      timeWindow: "current",
    });
  }, refreshInterval * 1000);  // Default: 30s
  return () => clearInterval(interval);
}, [schoolInfo, refreshInterval]);
```

**Analysis**:
- **Pro**: Guaranteed data freshness every 30s
- **Con**: Redundant requests if Realtime is working
- **Con**: No exponential backoff on errors
- **Con**: Continues polling even if tab is hidden (`document.hidden`)

**Optimization Recommendation**:
```javascript
// Add visibility check
if (!document.hidden) {
  window.openai?.callTool(...);
}
```

---

#### **Pattern 2: Event-Driven Updates (Push)**

```javascript
.on("postgres_changes", (payload) => {
  setState((prev) => ({ ...prev, newData: payload.new }));
});
```

**Analysis**:
- **Pro**: Instant UI updates (<200ms latency)
- **Pro**: No unnecessary polling
- **Con**: Relies on persistent WebSocket connection
- **Con**: No fallback if WebSocket drops

**Hybrid Approach Recommendation**:
- Use Realtime for instant updates
- Use polling as fallback when WebSocket disconnects
- Implement exponential backoff for reconnection

---

#### **Pattern 3: Computed State (Derived)**

```javascript
const filteredPickups = pickups.filter((pickup) => {
  if (state.filter === "next_30min") {
    const scheduledTime = new Date(pickup.scheduled_time);
    return scheduledTime <= new Date(currentTime.getTime() + 30 * 60 * 1000);
  }
  return true;
});
```

**Analysis**:
- ✅ **Pure function**: No side effects
- ✅ **Recomputed on dependencies**: `pickups`, `state.filter`, `currentTime`
- ✅ **No extra state storage**: Avoids stale derived state
- ⚠️ **Performance**: Recomputes every second (due to `currentTime` dependency)

**Optimization Opportunity**:
```javascript
// Memoize with useMemo to avoid recomputation unless dependencies change
const filteredPickups = useMemo(() => {
  return pickups.filter((pickup) => { /* ... */ });
}, [pickups, state.filter, currentTime.getMinutes()]);  // Only minute precision needed
```

---

## 2. MCP Server State Management

### 2.1 Stateless HTTP Design

**Architecture**: AllôBye MCP server is **stateless** with `stateless_http=True`.

```python
mcp = FastMCP(
    name="allobye-server",
    stateless_http=True,  # No session affinity required
)
```

**Implications**:
- ✅ Horizontal scaling: Any instance can handle any request
- ✅ No session store needed: Auth state in JWT (client-side)
- ✅ Load balancer friendly: No sticky sessions required
- ⚠️ No request deduplication: Duplicate requests process independently
- ⚠️ No circuit breaker state: Each request retries independently

---

### 2.2 Transient State (In-Memory)

#### **A. Monitoring & Metrics State**

**Location**: `/allobye_server_python/monitoring.py`

```python
class MetricsCollector:
    def __init__(self, config: MonitoringConfig):
        self.start_time = time.time()
        self.tool_metrics: Dict[str, ToolMetrics] = defaultdict(ToolMetrics)
        self.db_metrics = DatabaseMetrics()
        self.active_connections = 0
        self.total_requests = 0
        self.recent_errors: List[Dict[str, Any]] = []
        self.recent_requests: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []
```

**Characteristics**:
- **Scope**: Process-level (single MCP server instance)
- **Lifetime**: Server start → server stop
- **Persistence**: None (lost on restart)
- **Aggregation**: Per-tool metrics, database query stats, error logs

**State Updates**:
```python
def record_tool_call(self, tool_name, latency_ms, success, error):
    metrics = self.tool_metrics[tool_name]
    metrics.call_count += 1
    metrics.success_count += 1 if success else 0
    metrics.error_count += 1 if not success else 0
    metrics.total_latency_ms += latency_ms
    metrics.min_latency_ms = min(metrics.min_latency_ms, latency_ms)
    metrics.max_latency_ms = max(metrics.max_latency_ms, latency_ms)
```

**Concurrency**:
- ⚠️ **Not thread-safe**: Uses simple `defaultdict` without locks
- ⚠️ **Race conditions possible**: Concurrent requests increment counters
- ⚠️ **Eventual consistency**: Metrics may lag under high load

**Recommendation**:
```python
import threading

class MetricsCollector:
    def __init__(self):
        self._lock = threading.Lock()
        # ...

    def record_tool_call(self, ...):
        with self._lock:
            # ... atomic updates
```

---

#### **B. Request Tracing State**

```python
class RequestTracer:
    def __init__(self, logger: StructuredLogger):
        self._active_traces: Dict[str, Dict[str, Any]] = {}

    def start_trace(self, tool_name: str) -> str:
        trace_id = str(uuid4())
        self._active_traces[trace_id] = {
            "trace_id": trace_id,
            "tool_name": tool_name,
            "start_time": time.time(),
            "spans": [],
        }
        return trace_id
```

**Characteristics**:
- **Scope**: Request-scoped (trace_id)
- **Lifetime**: Request start → request end
- **Cleanup**: `del self._active_traces[trace_id]` in `end_trace()`

**Memory Leak Risk**:
- ⚠️ If `end_trace()` not called (exception before cleanup), trace lingers
- ⚠️ No TTL or max size limit on `_active_traces`

**Mitigation**:
```python
# Add periodic cleanup
def _cleanup_stale_traces(self):
    now = time.time()
    stale = [tid for tid, trace in self._active_traces.items()
             if now - trace["start_time"] > 300]  # 5 min TTL
    for tid in stale:
        del self._active_traces[tid]
```

---

#### **C. Supabase Client State**

```python
_supabase_client = None

def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(url, key)
    return _supabase_client
```

**Pattern**: Singleton (lazy initialization)

**Characteristics**:
- **Scope**: Process-level global
- **Lifetime**: First call → process end
- **Connection Pool**: Managed by Supabase SDK (httpx under the hood)

**Concerns**:
- ⚠️ **Connection leak**: No explicit cleanup on server shutdown
- ⚠️ **Network errors**: Falls back to `None` but doesn't retry initialization
- ✅ **Thread-safe**: Supabase SDK uses httpx which is thread-safe

---

### 2.3 State Persistence Strategies

#### **Strategy 1: Delegate to PostgreSQL**

All business state (pickups, children, delegates, emergencies) stored in PostgreSQL.

**Benefits**:
- ✅ ACID guarantees
- ✅ RLS policies enforce authorization at data layer
- ✅ Point-in-time recovery
- ✅ Horizontal read scaling (replicas)

**Trade-offs**:
- ⚠️ Latency: Network round-trip per query (50-200ms)
- ⚠️ No in-memory cache (every request queries DB)

---

#### **Strategy 2: Avoid Session State**

Auth state stored in **JWT** (client-side) rather than server-side sessions.

```python
async def get_current_user(arguments: Dict[str, Any]) -> Optional[UserProfile]:
    access_token = arguments.get("access_token")
    if not access_token:
        return None
    user = await validate_session(access_token)  # Decode JWT
    return user
```

**Benefits**:
- ✅ Stateless: No session store needed
- ✅ Scalable: No sticky sessions
- ✅ Portable: JWT valid across instances

**Trade-offs**:
- ⚠️ Revocation: Can't invalidate JWT until expiry
- ⚠️ Size: JWT included in every request (increases bandwidth)
- ⚠️ Security: If leaked, valid until expiration

---

#### **Strategy 3: Monitoring State is Ephemeral**

Metrics aggregated in-memory, not persisted.

**Rationale**:
- Prometheus scrapes `/metrics` endpoint every 15-60s
- Prometheus stores historical data
- MCP server only needs current counters

**Concerns**:
- ⚠️ Metrics lost on restart (breaks continuity)
- ⚠️ No cross-instance aggregation (each instance has separate metrics)

**Alternative**: Push to external metrics backend (StatsD, DataDog, etc.)

---

## 3. PostgreSQL State Management

### 3.1 Authoritative State

PostgreSQL is the **single source of truth** for all business data.

**Tables**:
- `schools`: School entities
- `children`: Child records with parent linkage
- `delegates`: Authorized pickup persons
- `pickups`: Scheduled pickup requests
- `pickup_children`: Many-to-many pickup ↔ child
- `delegate_children`: Many-to-many delegate ↔ child authorization
- `emergencies`: Emergency notifications

**State Transitions**:

```sql
-- Pickup status state machine
status TEXT CHECK (status IN (
  'pending',      -- Initial state after creation
  'confirmed',    -- Confirmed by system
  'in_progress',  -- Pickup person en route
  'completed',    -- Child picked up
  'cancelled',    -- Cancelled by parent
  'late'          -- Past scheduled_time + threshold
))
```

**Enforced by**: CHECK constraint + application logic

**Missing**: No explicit state machine enforcement (can transition from any state to any state)

**Recommendation**: Add trigger to validate state transitions
```sql
CREATE FUNCTION validate_pickup_status_transition() RETURNS TRIGGER AS $$
BEGIN
    -- Enforce valid transitions
    IF OLD.status = 'completed' AND NEW.status != 'completed' THEN
        RAISE EXCEPTION 'Cannot change status of completed pickup';
    END IF;
    -- ... more rules
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

---

### 3.2 State Consistency Mechanisms

#### **A. ACID Transactions**

```python
# Not explicitly shown in code, but Supabase SDK uses transactions
supabase.table("pickups").insert(pickup_data).execute()
for child_id in child_ids:
    supabase.table("pickup_children").insert({...}).execute()
```

**Issue**: No explicit transaction wrapper!

**Risk**: If `pickup_children` insert fails, orphan `pickups` record exists.

**Fix**:
```python
# Use database transaction
supabase.rpc("create_pickup_with_children", {
    "pickup_data": pickup_data,
    "child_ids": child_ids
})

-- In PostgreSQL
CREATE FUNCTION create_pickup_with_children(...) RETURNS JSON AS $$
BEGIN
    INSERT INTO pickups ... RETURNING * INTO pickup_record;
    FOREACH child_id IN ARRAY child_ids LOOP
        INSERT INTO pickup_children ...;
    END LOOP;
    RETURN pickup_record;
END;
$$ LANGUAGE plpgsql;
```

---

#### **B. Triggers for Cascading State Updates**

```sql
-- Cascade pickup status changes
CREATE FUNCTION cascade_pickup_status() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'cancelled' THEN
        UPDATE pickup_children
        SET checked_out = FALSE, checked_out_at = NULL
        WHERE pickup_id = NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER pickup_status_cascade
    AFTER UPDATE ON pickups
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION cascade_pickup_status();
```

**Analysis**:
- ✅ **Atomic**: Trigger runs in same transaction as UPDATE
- ✅ **Consistent**: Child checkout state always matches pickup status
- ⚠️ **Performance**: Triggers add latency to UPDATE queries
- ⚠️ **Complexity**: Business logic spread between app and DB

---

#### **C. Row-Level Security (RLS) as State Filter**

```sql
-- Parents can only see their own children's pickups
CREATE POLICY "Parents can view their children's pickups"
    ON pickups FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pickup_children pc
            JOIN children c ON pc.child_id = c.id
            WHERE pc.pickup_id = pickups.id
            AND c.parent_email = auth.jwt()->>'email'
        )
    );
```

**Characteristics**:
- **Scope**: Row-level (per-user view of data)
- **Enforcement**: Query rewrite at PostgreSQL level
- **Performance**: Adds subquery to every SELECT

**State Partitioning**:
- Each user sees a different "view" of the `pickups` table
- Same physical table, different logical states per user

**Concerns**:
- ⚠️ **Complex Joins**: Subqueries impact query performance
- ⚠️ **Index Coverage**: Need indexes on `parent_email`, `pickup_id`, etc.
- ⚠️ **Debugging**: Hard to test RLS policies (must impersonate users)

---

### 3.3 State Synchronization with Realtime

#### **Realtime Publication**

```sql
-- Enable real-time for pickups table
ALTER PUBLICATION supabase_realtime ADD TABLE pickups;
ALTER PUBLICATION supabase_realtime ADD TABLE emergencies;
```

**Mechanism**: PostgreSQL logical replication

**Flow**:
```
1. Client issues UPDATE pickups SET status='in_progress' WHERE id=X
              ↓
2. PostgreSQL commits transaction, writes to WAL (write-ahead log)
              ↓
3. Supabase Realtime listens to WAL changes
              ↓
4. Realtime filters by table + RLS policies
              ↓
5. Push JSON payload to WebSocket subscribers
              ↓
6. React component receives event, updates state
```

**Latency Breakdown**:
- DB commit: ~5-20ms
- WAL read: ~10-50ms
- WebSocket push: ~20-100ms
- Total: ~50-200ms

**Concerns**:
- ⚠️ **Ordering**: Multiple rapid updates may arrive out of order
- ⚠️ **Missed Events**: If WebSocket disconnects, no event replay
- ⚠️ **Bandwidth**: Every UPDATE triggers WebSocket message (even if not displayed)

---

## 4. State Lifecycle Analysis

### 4.1 Pickup State Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                 PICKUP ENTITY STATE MACHINE                 │
└─────────────────────────────────────────────────────────────┘

[Creation]
    ↓
┌─────────┐
│ pending │ ← Initial state after parent schedules pickup
└────┬────┘
     │ (auto-confirm or manual review)
     ↓
┌───────────┐
│ confirmed │ ← System confirms pickup is valid
└─────┬─────┘
      │
      ├─→ (delegate accepts) ────────────────────┐
      │                                          ↓
      ├─→ (scheduled_time passed + no show) ─→ [late]
      │                                          ↓
      ↓                               (eventually picked up)
┌──────────────┐                                ↓
│ in_progress  │ ← Delegate en route      ┌───────────┐
└──────┬───────┘                          │ completed │
       │                                  └───────────┘
       │ (child checked out)
       ↓
  [completed]

[Cancellation Path]
   Any state ──(parent cancels)──→ [cancelled]
                                      ↓
                            (trigger: cascade_pickup_status)
                                      ↓
                      UPDATE pickup_children SET checked_out=FALSE
```

**State Mutations**:
1. **Creation**: `create_pickup_request()` → status='confirmed'
2. **Delegate Accept**: Manual or implicit → status='in_progress'
3. **Checkout**: School staff checks out child → status='completed'
4. **Timeout**: Scheduled time passed → status='late' (needs cron job - NOT IMPLEMENTED)
5. **Cancellation**: Parent declares emergency → status='cancelled'

**Missing State Transitions**:
- ⚠️ No automatic `late` detection (requires background job)
- ⚠️ No `pending` → `confirmed` logic (immediately confirmed on creation)
- ⚠️ No retry logic for failed pickups

---

### 4.2 Emergency State Lifecycle

```
[Parent declares emergency]
           ↓
      INSERT INTO emergencies
      {emergency_type, context, severity}
           ↓
      TRIGGER: notify_emergency()
           ↓
      pg_notify('emergency_alert', ...)
           ↓
    ┌─────┴─────┐
    ↓           ↓
[Delegates] [Schools]
  (notified)  (alerted)
    ↓           ↓
  [React Dashboard updates UI]
    ↓
  [Auto-dismiss after 30s] (client-side timer)
    ↓
  [Manual resolution by staff]
    ↓
  UPDATE emergencies SET resolved=TRUE
```

**Concerns**:
- ⚠️ No acknowledgment tracking (don't know if delegates saw alert)
- ⚠️ No escalation (if not acknowledged within X minutes)
- ⚠️ Client-side auto-dismiss (what if staff misses it?)

---

### 4.3 Authentication State Lifecycle

```
[Signup]
   ↓
Supabase Auth creates user
   ↓
INSERT INTO user_profiles
   ↓
Return JWT (access_token)
   ↓
Client stores in localStorage
   ↓
[Every tool call includes access_token]
   ↓
validate_session(access_token)
   ↓
Supabase Auth decodes JWT
   ↓
Extract user claims (email, role)
   ↓
Fetch user_profile from DB
   ↓
Return UserProfile object
   ↓
[Logout or JWT expiry]
   ↓
Client removes from localStorage
   ↓
Server invalidates session (best effort)
```

**Session Expiry**:
- Access token: 1 hour (default Supabase)
- Refresh token: 30 days (stored in localStorage)
- No automatic refresh (user must re-login)

**Recommendation**: Implement token refresh before expiry
```javascript
useEffect(() => {
  const refreshInterval = setInterval(async () => {
    const expiresAt = getTokenExpiry();
    if (Date.now() > expiresAt - 5 * 60 * 1000) {  // 5 min before expiry
      await refreshAccessToken();
    }
  }, 60000);  // Check every minute
}, []);
```

---

## 5. Cache Strategy Analysis

### 5.1 No Explicit Caching

AllôBye **does not implement application-level caching**.

**Implications**:
- Every `get_school_pickups()` call queries PostgreSQL
- Every `get_user_profile()` call joins `user_profiles` + `user_schools` + `parent_children`
- No memoization of expensive computations

**Performance Impact**:
- Average query latency: 50-200ms
- Under load: DB becomes bottleneck

---

### 5.2 Implicit Browser Caching

**localStorage**:
- `allobye_token`: JWT access token
- `allobye_user`: User profile JSON

**Characteristics**:
- **Eviction**: Manual (on logout)
- **Staleness**: Can be out of sync with DB
- **Validation**: Periodic token validation via `auth-profile` tool

---

### 5.3 PostgreSQL Query Cache

PostgreSQL has built-in query result caching, but **only for identical queries**.

**Ineffective for AllôBye** because:
- Queries include `school_id=eq.${schoolInfo.id}` (unique per school)
- RLS policies inject user email (unique per user)

**Optimization Opportunity**:
- Add Redis for school dashboard data
- Cache key: `school:{school_id}:pickups:{time_window}`
- TTL: 30 seconds (matches refresh interval)
- Invalidate on INSERT/UPDATE to `pickups` table

---

## 6. State Consistency Issues

### 6.1 Race Conditions

#### **Issue 1: Concurrent Pickup Creation**

```python
# Two parents schedule pickup for same child at same time
pickup_1 = create_pickup_request([child_id], delegate_1, "15:00")
pickup_2 = create_pickup_request([child_id], delegate_2, "15:10")
```

**Problem**: No unique constraint preventing double-booking

**Fix**:
```sql
-- Add unique constraint: one active pickup per child at a time
CREATE UNIQUE INDEX idx_active_pickup_per_child
    ON pickup_children (child_id)
    WHERE EXISTS (
        SELECT 1 FROM pickups
        WHERE pickups.id = pickup_children.pickup_id
        AND pickups.status IN ('pending', 'confirmed', 'in_progress')
    );
```

---

#### **Issue 2: Realtime vs. MCP Data Merge**

```javascript
const pickups = metadata?.pickups || realtimePickups || [];
```

**Problem**: If both exist, MCP data (potentially stale) overrides fresh Realtime data.

**Timeline**:
```
T0: MCP fetches pickups (status='pending')
T1: User updates pickup to 'in_progress'
T2: Realtime pushes update → setRealtimePickups([{status='in_progress'}])
T3: MCP response arrives → metadata.pickups = [{status='pending'}]
T4: UI displays stale 'pending' status!
```

**Fix**:
```javascript
// Merge with conflict resolution (newer wins)
const pickups = useMemo(() => {
  const mcpPickups = metadata?.pickups || [];
  const realtimeMap = new Map(realtimePickups.map(p => [p.id, p]));

  return mcpPickups.map(pickup => {
    const realtimeVersion = realtimeMap.get(pickup.id);
    if (realtimeVersion && new Date(realtimeVersion.updated_at) > new Date(pickup.updated_at)) {
      return realtimeVersion;  // Realtime is newer
    }
    return pickup;
  });
}, [metadata, realtimePickups]);
```

---

### 6.2 Data Staleness

#### **Scenario 1: Cached User Profile**

```javascript
localStorage.setItem("allobye_user", JSON.stringify(user));
```

**Problem**: If user's role changes (e.g., parent → school_staff), cached profile is stale.

**Mitigation**: Periodic re-validation (implemented)
```javascript
validateToken(token).catch(() => handleLogout());
```

---

#### **Scenario 2: 30-Second Refresh Lag**

School dashboard polls every 30s. Changes take up to 30s to appear via MCP tool.

**Mitigation**: Realtime subscription provides instant updates (but see Issue 2 above).

---

### 6.3 State Leaks

#### **Issue: Monitoring Metrics Never Reset**

```python
self.tool_metrics: Dict[str, ToolMetrics] = defaultdict(ToolMetrics)
self.recent_errors: List[Dict[str, Any]] = []
```

**Problem**: Counters only increment, never reset. Long-running server accumulates stale data.

**Fix**: Add metric windows
```python
# Keep only last hour of data
self.metric_windows = deque(maxlen=3600)  # 1 sample per second
```

---

## 7. Recommendations

### 7.1 High Priority

1. **Fix Realtime/MCP Data Merge**: Implement timestamp-based conflict resolution
2. **Add Transaction Wrappers**: Ensure pickup creation is atomic
3. **Implement Token Refresh**: Auto-refresh JWT before expiry
4. **Add Unique Constraints**: Prevent double-booking of children

### 7.2 Medium Priority

5. **Add Redis Cache**: Cache school dashboard queries (30s TTL)
6. **Implement Circuit Breaker**: Prevent cascading failures to Supabase
7. **Add Monitoring Metrics TTL**: Prevent unbounded memory growth
8. **Use sessionStorage**: More secure than localStorage for tokens

### 7.3 Low Priority

9. **Add State Machine Validation**: Enforce valid pickup status transitions
10. **Implement Optimistic Updates**: Update UI before server confirmation
11. **Add Reconnection Logic**: Handle WebSocket disconnects gracefully
12. **Memoize Filtered Pickups**: Use `useMemo` to avoid recomputation

---

## 8. State Flow Complexity Matrix

| State Type | Scope | Lifetime | Persistence | Sync Mechanism | Consistency |
|------------|-------|----------|-------------|----------------|-------------|
| **React Local** | Component | Mount→Unmount | None | N/A | ✅ Strong |
| **Widget State** | Session | Widget Load→Close | OpenAI Store | useSyncExternalStore | ✅ Strong |
| **Auth State** | Browser | Until Logout | localStorage | Manual Load/Save | ⚠️ Eventual |
| **Realtime Pickups** | Component | Mount→Unmount | None | WebSocket Push | ⚠️ Eventual |
| **MCP Metrics** | Process | Server Start→Stop | None | N/A | ⚠️ Weak (no locks) |
| **PostgreSQL** | Global | Forever | Disk (ACID) | Transactions + RLS | ✅ Strong |

---

## Conclusion

AllôBye's state management is **pragmatic and mostly sound**, with clear separation between ephemeral UI state (React), stateless orchestration (MCP), and authoritative persistence (PostgreSQL). However, the **direct frontend-to-database coupling via Supabase Realtime** introduces consistency challenges that require careful handling of merge conflicts and stale data scenarios.

The lack of application-level caching is a **scalability concern** but acceptable for the current scale. The **monitoring metrics accumulation** and **race conditions in pickup creation** are the most pressing issues to address.
