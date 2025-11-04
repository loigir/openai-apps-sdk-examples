# Architecture Analysis - AllôBye School Pickup System

**Date**: 2025-11-04
**Analyzer**: Architecture Pattern Analyst
**Codebase**: AllôBye MCP Server + React Widgets

---

## Executive Summary

AllôBye implements a modern event-driven architecture combining the **Model Context Protocol (MCP)** with a **layered architecture** pattern. The system demonstrates strong separation between presentation (React), orchestration (MCP), business logic (Python services), and data persistence (PostgreSQL with RLS).

**Key Strengths**:
- Clean MCP integration with ChatGPT Apps SDK
- Comprehensive observability stack
- Strong security model (JWT + RLS)
- Real-time capabilities via Supabase

**Key Concerns**:
- Monolithic main.py (God Object pattern)
- Frontend-to-database coupling via Realtime
- Mixed responsibilities in service modules

---

## 1. Architectural Patterns Identified

### 1.1 Model Context Protocol (MCP) Pattern

**Implementation**: `/home/user/openai-apps-sdk-examples/allobye_server_python/main.py`

```
┌─────────────────┐
│   ChatGPT UI    │
└────────┬────────┘
         │ MCP Protocol
         ▼
┌─────────────────┐
│  FastMCP Server │ ← main.py (lines 696-700)
│   10 Tools      │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Tool Handlers   │ ← _handle_* functions
│ (Business Logic)│
└─────────────────┘
```

**Tools Exposed**:
- **Authentication** (5 tools): signup, login, logout, reset-password, profile
- **Pickup Management** (4 tools): pickup-schedule-create, delegate-authorize, emergency-declare, school-dashboard-fetch
- **Observability** (1 tool): monitoring-dashboard-fetch

**Pattern Quality**: ✅ Excellent
- Clear tool boundaries
- Consistent naming convention
- Proper input validation (Pydantic models)

**Concerns**:
- All handlers in single file (main.py)
- No handler abstraction layer

---

### 1.2 Layered Architecture Pattern

```
┌──────────────────────────────────────────────────────┐
│              PRESENTATION LAYER                       │
│  - React Widgets (allobye-dashboard, allobye-monitoring) │
│  - Authentication UI (auth-screen.jsx)               │
│  - Component separation: PickupCard, EmergencyAlert  │
└────────────────────┬─────────────────────────────────┘
                     │ MCP Tools + Supabase Realtime
┌────────────────────▼─────────────────────────────────┐
│              APPLICATION LAYER                        │
│  - MCP Server (main.py)                              │
│  - Tool orchestration (_handle_* functions)          │
│  - Widget resource serving                           │
└────────────────────┬─────────────────────────────────┘
                     │ Service calls
┌────────────────────▼─────────────────────────────────┐
│              BUSINESS LOGIC LAYER                     │
│  - Authentication (auth.py)                          │
│  - Monitoring (monitoring.py)                        │
│  - Database helpers (main.py lines 399-689)          │
└────────────────────┬─────────────────────────────────┘
                     │ Supabase SDK
┌────────────────────▼─────────────────────────────────┐
│              DATA ACCESS LAYER                        │
│  - PostgreSQL (Supabase)                             │
│  - Schema with RLS (schema.sql)                      │
│  - Triggers and Functions                            │
└──────────────────────────────────────────────────────┘
```

**Layer Boundaries**:
- ✅ **Good**: Clear separation between React and MCP
- ⚠️ **Concern**: Presentation layer directly accesses data layer (Supabase Realtime)
- ✅ **Good**: Business logic encapsulated in service modules
- ⚠️ **Concern**: Database helpers mixed with orchestration in main.py

---

### 1.3 Pub/Sub (Event-Driven Architecture)

**Real-time Events**: Two complementary systems

#### A) Supabase Realtime (WebSocket)

**Location**: `/home/user/openai-apps-sdk-examples/src/allobye-dashboard/dashboard.jsx` (lines 56-113)

```javascript
supabase
  .channel("pickups-changes")
  .on("postgres_changes", {
    event: "*",
    schema: "public",
    table: "pickups",
    filter: `school_id=eq.${schoolInfo.id}`,
  }, (payload) => {
    // Update UI in real-time
  })
  .subscribe();
```

**Events**:
- INSERT: New pickup scheduled
- UPDATE: Pickup status changed (pending → in_progress → completed)
- DELETE: Pickup cancelled

**Pattern Quality**: ⚠️ Mixed
- ✅ Decoupled real-time updates
- ⚠️ Frontend directly coupled to database schema
- ⚠️ Bypasses application layer

#### B) PostgreSQL NOTIFY/LISTEN

**Location**: `/home/user/openai-apps-sdk-examples/allobye_server_python/schema.sql` (lines 196-231)

```sql
CREATE FUNCTION notify_emergency()
RETURNS TRIGGER AS $$
BEGIN
    PERFORM pg_notify('emergency_alert', json_build_object(...)::text);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Channels**:
- `emergency_alert`: Broadcast emergencies to all subscribers
- School-specific channels (planned)

**Pattern Quality**: ✅ Good
- Database-level events for critical notifications
- Decoupled emergency broadcasting

---

### 1.4 Authentication & Authorization (Middleware Pattern)

**Components**:

#### A) JWT Authentication (Supabase Auth)

**Location**: `/home/user/openai-apps-sdk-examples/allobye_server_python/auth.py`

```python
async def validate_session(access_token: str) -> Optional[UserProfile]:
    """Validate JWT and return user profile"""
    supabase.auth.set_session(access_token, "")
    response = supabase.auth.get_user(access_token)
    # Returns UserProfile or raises SessionExpiredError
```

**Flow**:
```
1. User calls auth-login
   ↓
2. Supabase Auth validates credentials
   ↓
3. JWT access_token returned
   ↓
4. Client stores token (localStorage)
   ↓
5. All tool calls include accessToken
   ↓
6. MCP server validates on every request
```

#### B) Middleware Pattern

**Location**: `/home/user/openai-apps-sdk-examples/allobye_server_python/main.py` (lines 351-392)

```python
async def get_current_user(arguments: Dict[str, Any]) -> Optional[UserProfile]:
    """Extract and validate user from request"""
    access_token = arguments.get("access_token") or arguments.get("accessToken")
    if not access_token:
        return None

    user = await validate_session(access_token)
    return user

def require_auth(user: Optional[UserProfile], role: Optional[str] = None) -> bool:
    """Check authentication and role"""
```

**Usage in Handlers**:
```python
async def _handle_pickup_schedule_create(arguments):
    user = await get_current_user(arguments)  # Middleware
    if not require_auth(user, role="parent"):  # Authorization
        return error_response()

    # Verify ownership
    if not await verify_parent_owns_child(user.id, child_id):
        return error_response()
```

#### C) Row-Level Security (RLS)

**Location**: `/home/user/openai-apps-sdk-examples/allobye_server_python/schema.sql` (lines 267-486)

**Policy Examples**:
```sql
-- Parents can only see their own children
CREATE POLICY "Parents can view their own children"
    ON children FOR SELECT
    USING (parent_email = auth.jwt()->>'email');

-- Delegates can view pickups where they are pickup person
CREATE POLICY "Delegates can view their assigned pickups"
    ON pickups FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM delegates
            WHERE delegates.id = pickups.pickup_person_id
            AND delegates.email = auth.jwt()->>'email'
        )
    );
```

**Pattern Quality**: ✅ Excellent
- Defense in depth (JWT + RLS)
- Consistent middleware pattern
- Role-based access control (parent, school_staff, service_role)

**Concern**: ⚠️ Business authorization logic duplicated in RLS policies

---

### 1.5 Monitoring (Observer Pattern)

**Location**: `/home/user/openai-apps-sdk-examples/allobye_server_python/monitoring.py`

**Components**:

#### A) Structured Logging
```python
class StructuredLogger:
    def info(self, message: str, **extra):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "service": "allobye-mcp-server",
            "message": message,
            **extra
        }
        self.logger.info(json.dumps(log_data))
```

#### B) Metrics Collection
```python
class MetricsCollector:
    def record_tool_call(self, tool_name, latency_ms, success, error):
        metrics = self.tool_metrics[tool_name]
        metrics.call_count += 1
        metrics.total_latency_ms += latency_ms
```

**Metrics Tracked**:
- Tool call count per tool
- Success/error rates
- Latency (min, max, avg, p95)
- Database query performance
- Active connections
- Uptime

#### C) Prometheus Export
```python
def export_prometheus(self) -> str:
    """Export metrics in Prometheus format"""
    # allobye_tool_calls_total{tool="pickup-schedule-create"} 42
    # allobye_tool_latency_ms{tool="pickup-schedule-create"} 150.5
```

#### D) Request Tracing
```python
class RequestTracer:
    def start_trace(self, tool_name: str) -> str:
        trace_id = str(uuid4())
        self.logger.set_context(trace_id=trace_id)
```

#### E) Alerting
```python
class AlertingConfig:
    error_rate_threshold: float = 0.05  # 5%
    latency_threshold_ms: float = 1000.0
    db_failure_threshold: int = 3
```

**Pattern Quality**: ✅ Excellent
- Comprehensive observability stack
- Prometheus-compatible metrics
- Correlation IDs for tracing
- Health check endpoint (/health)

**Concern**: ⚠️ All monitoring concerns in single module (753 lines)

---

## 2. Separation of Responsibilities Analysis

### 2.1 Frontend vs Backend

**Frontend (React Widgets)**:
```
/src/allobye-dashboard/
├── index.jsx           # App wrapper + session management
├── auth-screen.jsx     # Login/signup UI
├── dashboard.jsx       # Main dashboard with pickup queue
├── pickup-card.jsx     # Individual pickup display
└── emergency-alert.jsx # Emergency banner
```

**Responsibilities**:
- ✅ Pure presentation logic
- ✅ Session management (localStorage)
- ✅ Real-time UI updates (Supabase subscription)
- ⚠️ Direct database access (Realtime bypass MCP)

**Backend (MCP Server)**:
```
/allobye_server_python/
├── main.py       # MCP orchestration + tool handlers
├── auth.py       # Authentication service
└── monitoring.py # Observability service
```

**Responsibilities**:
- ✅ Business logic orchestration
- ✅ Authentication/authorization
- ✅ Database access coordination
- ⚠️ Database helpers mixed with orchestration

### 2.2 Business Logic vs Presentation Logic

**Business Logic** (Backend):
```python
# Pickup scheduling with cross-school coordination
async def coordinate_cross_school_pickup(child_ids, pickup_person_id, ...):
    schools = await get_schools_for_children(child_ids)
    pickup = await create_pickup_request(...)
    pickup["a2a_messages"] = [...]  # A2A simulation
    return pickup
```

**Presentation Logic** (Frontend):
```javascript
// Filter and display pickups
const filteredPickups = pickups.filter((pickup) => {
  if (state.filter === "next_30min") {
    const scheduledTime = new Date(pickup.scheduled_time);
    return scheduledTime <= new Date(currentTime.getTime() + 30 * 60 * 1000);
  }
  return true;
});
```

**Separation Quality**: ✅ Good
- Clear boundary between what belongs in backend vs frontend
- Frontend doesn't contain business rules

### 2.3 Database Schema vs Application Logic

**Schema Responsibilities** (schema.sql):
- ✅ Data integrity (foreign keys, constraints)
- ✅ Indexing for performance
- ✅ Triggers for cascading updates
- ⚠️ Business logic in RLS policies (complex authorization rules)
- ⚠️ Business logic in utility functions

**Application Logic** (main.py, auth.py):
- ✅ Workflow orchestration
- ✅ External service integration (Supabase Auth)
- ⚠️ Authorization duplicated (JWT validation + RLS)

**Example of Schema Business Logic**:
```sql
-- Cascade pickup status changes (business rule in DB)
CREATE FUNCTION cascade_pickup_status() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'cancelled' THEN
        UPDATE pickup_children SET checked_out = FALSE WHERE pickup_id = NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Concern**: Business rules split between application and database

### 2.4 Auth vs Business Logic

**Authentication Module** (auth.py):
```python
# Clear auth responsibilities
async def signup_user(email, password, name, role, schools)
async def login_user(email, password)
async def logout_user(access_token)
async def validate_session(access_token)

# ⚠️ Authorization mixed in
async def verify_parent_owns_child(parent_id, child_id)
async def verify_staff_at_school(user_id, school_id)
```

**Quality**: ⚠️ Mixed
- ✅ Authentication well-separated
- ⚠️ Authorization helpers in auth module (should be in business layer)

---

## 3. Dependency Flow

```
┌─────────────────────────────────────────────┐
│          React Widgets (Frontend)           │
│  - Supabase Realtime (direct DB access)    │
└──────────┬──────────────────┬───────────────┘
           │                  │
           │ MCP Tools        │ WebSocket
           │                  │
┌──────────▼──────────────────▼───────────────┐
│            MCP Server (main.py)             │
│                                             │
│  ┌─────────────┐      ┌──────────────┐    │
│  │ auth.py     │      │ monitoring.py│    │
│  │ (service)   │      │ (service)    │    │
│  └──────┬──────┘      └──────┬───────┘    │
│         │                    │             │
│         └────────┬───────────┘             │
└──────────────────┼─────────────────────────┘
                   │
                   │ Supabase SDK
                   │
┌──────────────────▼─────────────────────────┐
│        PostgreSQL (Supabase)               │
│  - Schema with RLS                         │
│  - Triggers                                │
│  - Realtime (NOTIFY/LISTEN)               │
└────────────────────────────────────────────┘
```

**Dependency Direction**: ✅ Mostly correct (top-down)
**Violations**:
- Frontend → Database (Realtime bypasses application layer)
- Circular: Frontend → MCP → DB, Frontend → DB (Realtime)

---

## 4. Component Boundaries

### Clear Boundaries ✅

1. **MCP Protocol Boundary**
   - Clean interface between ChatGPT and server
   - Tool input validation (Pydantic)
   - Structured responses

2. **Service Modules**
   - auth.py: Self-contained authentication
   - monitoring.py: Self-contained observability

3. **Database Boundary**
   - SQL schema isolated in schema.sql
   - RLS policies for authorization

### Leaky Boundaries ⚠️

1. **Frontend-Database Coupling**
   ```javascript
   // Frontend knows DB schema
   supabase.channel("pickups-changes")
     .on("postgres_changes", { table: "pickups" })
   ```

2. **main.py Monolith**
   - Contains: MCP setup, handlers, DB helpers, widget config
   - No clear internal boundaries

3. **Auth Module Responsibility Leak**
   ```python
   # Authorization (business concern) in auth module
   async def verify_parent_owns_child(...)
   ```

---

## 5. Pattern Implementation Quality

### Excellent ✅

1. **MCP Integration**
   - Clean tool definitions
   - Proper widget embedding
   - Metadata annotations

2. **Observability**
   - Structured logging
   - Prometheus metrics
   - Request tracing
   - Health checks

3. **Security**
   - JWT validation
   - RLS policies
   - Defense in depth

### Good 👍

1. **Layered Architecture**
   - Clear presentation/business/data layers
   - Service encapsulation

2. **Real-time Events**
   - WebSocket for UI updates
   - NOTIFY/LISTEN for emergencies

### Needs Improvement ⚠️

1. **Single Responsibility Principle**
   - main.py violates SRP (1583 lines)
   - monitoring.py mixes concerns (753 lines)

2. **Coupling**
   - Frontend-database tight coupling
   - Mixed authorization logic

---

## 6. Scalability Considerations

### Horizontal Scalability ✅
- Stateless HTTP MCP server
- Supabase managed database
- React widgets (static assets)

### Vertical Concerns ⚠️
- main.py as single point of logic
- All handlers in one process
- No handler-level concurrency

### Real-time Scalability ⚠️
- Supabase Realtime subscriptions per client
- No message queuing for high-volume events
- NOTIFY limited to single PostgreSQL instance

---

## 7. Testability

### Easy to Test ✅
- auth.py: Pure functions with clear inputs/outputs
- monitoring.py: Observable metrics
- Pydantic models for validation

### Hard to Test ⚠️
- main.py: Tightly coupled handlers
- Database helpers mixed with orchestration
- Mock/fallback mode (not ideal for tests)

---

## 8. Key Architectural Metrics

| Metric | Value | Assessment |
|--------|-------|------------|
| **Total LoC** | ~10,650 | Medium complexity |
| **Largest Module** | main.py (1,583 lines) | ⚠️ Too large |
| **Service Modules** | 3 (main, auth, monitoring) | ✅ Good separation |
| **Frontend Components** | 5 per widget | ✅ Well-decomposed |
| **MCP Tools** | 10 | ✅ Reasonable count |
| **Database Tables** | 7 core + 2 junction | ✅ Normalized |
| **RLS Policies** | 21 | ⚠️ Complex authorization |
| **Dependencies** | React → MCP → DB + React → DB | ⚠️ Bypasses |

---

## 9. Summary: Pattern Adherence

| Pattern | Implementation | Quality | Notes |
|---------|---------------|---------|-------|
| **MCP** | FastMCP + 10 tools | ✅ Excellent | Clean protocol usage |
| **Layered Architecture** | 4 layers | 👍 Good | Some boundary violations |
| **Pub/Sub** | Supabase + NOTIFY | 👍 Good | Frontend coupling issue |
| **Auth Middleware** | JWT + RLS | ✅ Excellent | Consistent pattern |
| **Observer (Monitoring)** | Comprehensive | ✅ Excellent | All concerns covered |
| **SRP** | Mixed | ⚠️ Needs work | God objects present |
| **Dependency Injection** | Not used | ⚠️ Missing | Hard-coded dependencies |
| **Repository Pattern** | Not used | ⚠️ Missing | Direct Supabase calls |

---

## Conclusion

AllôBye demonstrates a **well-architected system** with strong observability, security, and real-time capabilities. The MCP integration is exemplary, and the monitoring stack is production-ready.

**Primary concerns** are architectural rather than functional:
- Monolithic main.py needs decomposition
- Frontend-database coupling bypasses business layer
- Missing abstraction layers (Repository, DI)

These are **refactoring opportunities** rather than critical flaws. The system is production-ready with recommended improvements for long-term maintainability.
