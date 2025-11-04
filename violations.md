# Architectural Violations - AllôBye

**Date**: 2025-11-04
**Project**: AllôBye School Pickup Coordination System
**Analysis Focus**: SOLID principles, architectural patterns, separation of concerns

---

## Violation Severity Legend

- 🔴 **CRITICAL**: Major architectural flaw, significant refactoring required
- 🟠 **HIGH**: Important violation, should be addressed in near term
- 🟡 **MEDIUM**: Quality concern, address when convenient
- 🟢 **LOW**: Minor issue, technical debt

---

## 1. God Object Pattern

### 🔴 CRITICAL: main.py Violates Single Responsibility Principle (SRP)

**File**: `/home/user/openai-apps-sdk-examples/allobye_server_python/main.py`
**Lines**: 1,583 total

**Description**:
The `main.py` module is a God Object that handles too many responsibilities, violating the Single Responsibility Principle. It contains MCP server setup, all tool handlers, database helpers, widget configuration, HTTP endpoints, and orchestration logic.

**Responsibilities Contained**:
1. **MCP Server Configuration** (lines 696-700)
   - FastMCP initialization
   - Server settings

2. **Tool Definitions** (lines 742-836)
   - 10 MCP tool declarations
   - Input schemas
   - Metadata

3. **Tool Handlers** (lines 844-1384)
   - `_handle_auth_signup` (41 lines)
   - `_handle_auth_login` (41 lines)
   - `_handle_auth_logout` (21 lines)
   - `_handle_auth_reset_password` (21 lines)
   - `_handle_auth_profile` (40 lines)
   - `_handle_pickup_schedule_create` (86 lines)
   - `_handle_delegate_authorize` (68 lines)
   - `_handle_emergency_declare` (69 lines)
   - `_handle_school_dashboard_fetch` (77 lines)
   - `_handle_monitoring_dashboard_fetch` (54 lines)

4. **Database Helpers** (lines 399-689)
   - `get_schools_for_children` (25 lines)
   - `create_pickup_request` (47 lines)
   - `coordinate_cross_school_pickup` (18 lines)
   - `broadcast_delegate_authorization` (43 lines)
   - `get_authorized_delegates` (20 lines)
   - `broadcast_emergency` (42 lines)
   - `get_school_pickups` (54 lines)
   - `get_school_info` (19 lines)

5. **Widget Configuration** (lines 287-343)
   - Widget HTML loading
   - Widget metadata
   - Resource caching

6. **Middleware** (lines 351-392)
   - Authentication middleware
   - Authorization helpers

7. **HTTP Endpoints** (lines 1544-1576)
   - `/health` endpoint
   - `/metrics` endpoint
   - CORS configuration

8. **Request Handling** (lines 1392-1449)
   - Tool call routing
   - Metrics collection
   - Error handling

**Impact**:
- ❌ Difficult to test (mixed concerns)
- ❌ Hard to maintain (1,583 lines)
- ❌ Impossible to reuse components independently
- ❌ Poor separation of concerns
- ❌ Tight coupling

**Example**:
```python
# main.py contains ALL of these in one file:

# MCP setup
mcp = FastMCP(name="allobye-server", stateless_http=True)

# Database helper
async def get_schools_for_children(child_ids: List[str]):
    # 25 lines of Supabase queries
    ...

# Tool handler
async def _handle_pickup_schedule_create(arguments: Dict[str, Any]):
    # 86 lines of business logic
    ...

# HTTP endpoint
async def health_endpoint(request):
    # Health check logic
    ...

# Widget config
SCHOOL_DASHBOARD_WIDGET = AllobyeWidget(...)
```

**Recommended Fix**:
Split into separate modules:
```
allobye_server_python/
├── main.py                    # MCP server setup only (< 100 lines)
├── handlers/
│   ├── auth_handlers.py       # Authentication tool handlers
│   ├── pickup_handlers.py     # Pickup management handlers
│   └── monitoring_handlers.py # Monitoring handlers
├── services/
│   ├── auth.py               # Already exists ✅
│   ├── monitoring.py         # Already exists ✅
│   ├── pickup_service.py     # NEW: Pickup business logic
│   └── school_service.py     # NEW: School-related logic
├── repositories/
│   ├── pickup_repository.py  # NEW: Pickup data access
│   ├── school_repository.py  # NEW: School data access
│   └── delegate_repository.py # NEW: Delegate data access
├── middleware/
│   └── auth_middleware.py    # NEW: Extract from main.py
└── widgets/
    └── widget_config.py      # NEW: Widget configuration
```

**Metrics**:
- Current: 1 module, 1,583 lines, 8+ responsibilities
- Target: 10+ modules, < 200 lines each, 1 responsibility per module

---

## 2. Tight Coupling

### 🟠 HIGH: Frontend Directly Coupled to Database Schema

**File**: `/home/user/openai-apps-sdk-examples/src/allobye-dashboard/dashboard.jsx`
**Lines**: 56-113

**Description**:
The React frontend directly subscribes to Supabase Realtime events, bypassing the application layer and creating tight coupling to the database schema.

**Code**:
```javascript
// Frontend knows internal database structure
const channel = supabase
  .channel("pickups-changes")
  .on(
    "postgres_changes",
    {
      event: "*",
      schema: "public",          // ❌ Hardcoded schema
      table: "pickups",          // ❌ Hardcoded table name
      filter: `school_id=eq.${schoolInfo.id}`,  // ❌ Hardcoded column name
    },
    (payload) => {
      // ❌ Frontend processes raw DB payload
      if (payload.eventType === "INSERT" || payload.eventType === "UPDATE") {
        setRealtimePickups((prev) => {
          const updated = prev.filter((p) => p.id !== payload.new.id);
          return [...updated, payload.new].sort(
            (a, b) => new Date(a.scheduled_time) - new Date(b.scheduled_time)
          );
        });
      }
    }
  )
  .subscribe();
```

**Problems**:
1. **Schema Coupling**: Frontend depends on exact database table/column names
2. **Bypasses Business Layer**: Real-time updates skip MCP server validation
3. **No Transformation**: Frontend receives raw database records
4. **Breaking Changes**: Any schema change breaks frontend
5. **Security**: Frontend must have direct Supabase access

**Impact**:
- ❌ Database schema refactoring breaks frontend
- ❌ Cannot enforce business rules on real-time updates
- ❌ Violates layered architecture (Layer 1 → Layer 4 direct)
- ❌ Cannot mock/test real-time subscriptions easily

**Example Scenario**:
```
If we rename: pickups.scheduled_time → pickups.pickup_time

Backend change:
  ✅ Update schema.sql
  ✅ Update main.py queries

Frontend change required:
  ❌ Update dashboard.jsx (line 92: a.scheduled_time)
  ❌ Update pickup-card.jsx (references scheduled_time)
  ❌ Update all components using this field
```

**Recommended Fix**:

**Option 1: Server-Sent Events (SSE) through MCP**
```python
# NEW: In MCP server
@mcp.tool(name="subscribe-school-updates")
async def subscribe_updates(school_id: str):
    """Subscribe to school pickup updates via SSE"""
    async def event_generator():
        async for event in supabase_realtime_channel(school_id):
            # Transform DB event to business event
            yield {
                "type": "pickup_update",
                "data": transform_pickup(event.payload)
            }

    return SSEResponse(event_generator())
```

**Option 2: WebSocket through MCP Server**
```javascript
// Frontend: Subscribe via MCP WebSocket
const mcpWebSocket = new WebSocket('ws://mcp-server/pickups');
mcpWebSocket.onmessage = (event) => {
  const businessEvent = JSON.parse(event.data);
  // Receive transformed business objects, not raw DB records
  setRealtimePickups(businessEvent.pickups);
};
```

**Option 3: Polling with Caching**
```javascript
// Frontend: Poll MCP tool (already implemented, extend it)
useEffect(() => {
  const interval = setInterval(() => {
    callMCPTool("school-dashboard-fetch", { schoolId, timeWindow: "current" });
  }, 5000); // 5s polling instead of 30s
}, [schoolId]);
```

**Recommended**: Option 2 (WebSocket through MCP) for best architecture alignment

---

### 🟠 HIGH: Direct Supabase Client Usage (Multiple Locations)

**Files**:
- `/home/user/openai-apps-sdk-examples/allobye_server_python/main.py` (lines 73-93)
- `/home/user/openai-apps-sdk-examples/allobye_server_python/auth.py` (lines 75-112)

**Description**:
Supabase client is created inline in multiple modules, creating tight coupling and making testing difficult.

**Code Examples**:
```python
# main.py
def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client, Client
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        _supabase_client = create_client(url, key)
    return _supabase_client

# auth.py
def get_supabase_client():
    from supabase import create_client, Client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_ANON_KEY")
    return create_client(url, key)

# auth.py (different function!)
def get_supabase_admin():
    from supabase import create_client, Client
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    return create_client(url, key)
```

**Problems**:
1. **Duplication**: 3 different functions creating Supabase clients
2. **Global State**: Global `_supabase_client` in main.py
3. **No Dependency Injection**: Clients hardcoded in functions
4. **Hard to Test**: Cannot mock Supabase without env vars
5. **No Interface**: Tight coupling to Supabase SDK

**Impact**:
- ❌ Cannot swap Supabase for another backend
- ❌ Testing requires real Supabase instance or complex mocking
- ❌ Cannot reuse database logic across different storage backends

**Recommended Fix**:

**Create Database Abstraction Layer**:
```python
# NEW: database/client.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class DatabaseClient(ABC):
    """Abstract database client interface"""

    @abstractmethod
    async def query(self, table: str, filters: Dict) -> List[Dict]:
        pass

    @abstractmethod
    async def insert(self, table: str, data: Dict) -> Dict:
        pass

    @abstractmethod
    async def update(self, table: str, id: str, data: Dict) -> Dict:
        pass

# NEW: database/supabase_client.py
class SupabaseClient(DatabaseClient):
    """Supabase implementation of DatabaseClient"""

    def __init__(self, url: str, key: str):
        from supabase import create_client
        self._client = create_client(url, key)

    async def query(self, table: str, filters: Dict) -> List[Dict]:
        response = self._client.table(table).select("*")
        for key, value in filters.items():
            response = response.eq(key, value)
        return response.execute().data

# NEW: database/factory.py
class DatabaseFactory:
    """Factory for creating database clients"""

    @staticmethod
    def create_client(client_type: str = "supabase", **kwargs) -> DatabaseClient:
        if client_type == "supabase":
            return SupabaseClient(
                url=kwargs.get("url") or os.getenv("SUPABASE_URL"),
                key=kwargs.get("key") or os.getenv("SUPABASE_ANON_KEY")
            )
        elif client_type == "mock":
            return MockDatabaseClient()  # For testing
        raise ValueError(f"Unknown client type: {client_type}")

# Usage in repositories:
class PickupRepository:
    def __init__(self, db_client: DatabaseClient):
        self.db = db_client  # ✅ Dependency injection

    async def get_school_pickups(self, school_id: str):
        return await self.db.query("pickups", {"school_id": school_id})
```

---

### 🟡 MEDIUM: Widget Configuration Tightly Coupled to main.py

**File**: `/home/user/openai-apps-sdk-examples/allobye_server_python/main.py`
**Lines**: 287-343

**Description**:
Widget HTML loading and configuration is embedded in the main orchestration file.

**Code**:
```python
# ❌ Widget logic in main.py
@lru_cache(maxsize=None)
def _load_widget_html(component_name: str) -> str:
    html_path = ASSETS_DIR / f"{component_name}.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf8")
    # ... fallback logic

SCHOOL_DASHBOARD_WIDGET = AllobyeWidget(
    identifier="school-dashboard",
    title="Tableau de bord école - AllôBye",
    template_uri="ui://widget/allobye-dashboard.html",
    invoking="Chargement du tableau de bord...",
    invoked="Tableau de bord chargé",
    html=_load_widget_html("allobye-dashboard"),
)
```

**Recommended Fix**:
```python
# NEW: widgets/widget_manager.py
class WidgetManager:
    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir
        self._cache = {}

    def load_widget(self, name: str) -> AllobyeWidget:
        if name in self._cache:
            return self._cache[name]

        widget = self._load_from_config(name)
        self._cache[name] = widget
        return widget

# main.py (simplified):
from widgets.widget_manager import WidgetManager

widget_manager = WidgetManager(ASSETS_DIR)
SCHOOL_DASHBOARD_WIDGET = widget_manager.load_widget("allobye-dashboard")
```

---

## 3. Leaky Abstractions

### 🟠 HIGH: Business Authorization Logic in RLS Policies

**File**: `/home/user/openai-apps-sdk-examples/allobye_server_python/schema.sql`
**Lines**: 267-486

**Description**:
Row-Level Security (RLS) policies contain complex business logic that should be in the application layer, creating a leaky abstraction.

**Code Examples**:
```sql
-- ❌ Complex business logic in database
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

-- ❌ Business rule: Delegates can view pickups where they are the pickup person
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

**Problems**:
1. **Duplicated Logic**: Authorization checked in both RLS and application code
2. **Hard to Test**: Database policies require integration tests
3. **Hard to Debug**: Cannot log RLS policy execution
4. **Performance**: Complex JOINs on every query
5. **Maintainability**: Business rules scattered across SQL and Python

**Example of Duplication**:
```python
# Same logic in application layer:
async def verify_parent_owns_child(parent_id: str, child_id: str) -> bool:
    response = supabase.table("parent_children").select("id").eq(
        "parent_id", parent_id
    ).eq("child_id", child_id).execute()
    return len(response.data) > 0

# Tool handler checks this:
if not await verify_parent_owns_child(user.id, child_id):
    return error_response()

# But RLS ALSO checks this in the database!
```

**Impact**:
- ❌ Authorization logic maintained in 2 places
- ❌ Database becomes application-aware
- ❌ Cannot change authorization without schema migration

**Recommended Fix**:

**Keep RLS Simple** (just row ownership):
```sql
-- ✅ Simple RLS: Only check row ownership
CREATE POLICY "Service role can manage all"
    ON pickups FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ✅ Direct ownership only
CREATE POLICY "Parents can view their own records"
    ON children FOR SELECT
    USING (parent_id = auth.uid());
```

**Move Business Logic to Application**:
```python
# ✅ Complex authorization in application layer
class PickupAuthorizationService:
    async def can_view_pickup(self, user: UserProfile, pickup_id: str) -> bool:
        pickup = await self.pickup_repo.get_by_id(pickup_id)

        # Business rules in code (not SQL):
        if user.role == "parent":
            return await self._is_parent_of_any_child(user.id, pickup.child_ids)
        elif user.role == "delegate":
            return user.id == pickup.pickup_person_id
        elif user.role == "school_staff":
            return await self._is_staff_at_school(user.id, pickup.school_id)

        return False
```

---

### 🟡 MEDIUM: Database Triggers Contain Business Logic

**File**: `/home/user/openai-apps-sdk-examples/allobye_server_python/schema.sql`
**Lines**: 234-263

**Description**:
Business rules are implemented in database triggers, making them invisible to the application layer.

**Code**:
```sql
-- ❌ Business rule: "When pickup is cancelled, uncheck all children"
CREATE FUNCTION cascade_pickup_status() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'cancelled' AND OLD.status != 'cancelled' THEN
        UPDATE pickup_children
        SET checked_out = FALSE,
            checked_out_at = NULL,
            checked_out_by = NULL
        WHERE pickup_id = NEW.id;
    END IF;

    -- ❌ Business rule: "When pickup completed, check out all children"
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        UPDATE pickup_children
        SET checked_out = TRUE,
            checked_out_at = COALESCE(checked_out_at, NOW())
        WHERE pickup_id = NEW.id AND checked_out = FALSE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Problems**:
1. **Hidden Logic**: Developers don't know triggers exist
2. **Hard to Test**: Cannot unit test triggers
3. **No Logging**: Cannot trace trigger execution
4. **Side Effects**: Updates happen invisibly
5. **Coupling**: Application assumes trigger behavior

**Recommended Fix**:

**Move to Application Layer**:
```python
# ✅ Business logic visible in code
class PickupService:
    async def cancel_pickup(self, pickup_id: str, reason: str):
        # Explicit business logic
        async with self.db.transaction():
            await self.pickup_repo.update_status(pickup_id, "cancelled")
            await self.pickup_repo.uncheck_all_children(pickup_id)
            await self.audit_log.record("pickup_cancelled", pickup_id, reason)
            logger.info("Pickup cancelled", pickup_id=pickup_id, reason=reason)
```

**Keep Triggers for Data Integrity Only**:
```sql
-- ✅ Trigger for data integrity (not business logic)
CREATE TRIGGER update_pickups_updated_at
    BEFORE UPDATE ON pickups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

## 4. Mixed Responsibilities

### 🟡 MEDIUM: monitoring.py Mixes Multiple Concerns

**File**: `/home/user/openai-apps-sdk-examples/allobye_server_python/monitoring.py`
**Lines**: 753 total

**Description**:
The monitoring module combines logging, metrics collection, tracing, alerting, and middleware in a single file.

**Responsibilities**:
1. **Structured Logging** (lines 69-137)
   - StructuredLogger class
   - JSON formatting

2. **Metrics Collection** (lines 208-479)
   - MetricsCollector class
   - ToolMetrics dataclass
   - DatabaseMetrics dataclass
   - Prometheus export

3. **Request Tracing** (lines 485-551)
   - RequestTracer class
   - Trace context management

4. **Middleware** (lines 557-650)
   - MonitoringMiddleware class
   - Tool call decoration
   - Database query monitoring

5. **Alerting** (lines 32-48, 331-386)
   - AlertingConfig dataclass
   - Alert rules and thresholds

6. **Health Checks** (lines 716-754)
   - Health status aggregation

**Impact**:
- ⚠️ Hard to import specific components
- ⚠️ Testing requires entire monitoring stack
- ⚠️ Cannot reuse logging without metrics

**Recommended Fix**:
```python
# Split into focused modules:
monitoring/
├── __init__.py
├── logger.py          # StructuredLogger only
├── metrics.py         # MetricsCollector only
├── tracer.py          # RequestTracer only
├── middleware.py      # MonitoringMiddleware only
├── alerting.py        # AlertingConfig and rules
└── health.py          # Health check logic
```

**Benefits**:
- ✅ Each module < 200 lines
- ✅ Clear imports: `from monitoring.logger import StructuredLogger`
- ✅ Easy to test individually
- ✅ Reusable components

---

### 🟡 MEDIUM: auth.py Mixes Authentication and Authorization

**File**: `/home/user/openai-apps-sdk-examples/allobye_server_python/auth.py`
**Lines**: 583-632

**Description**:
The authentication module contains authorization helper functions that should be in a separate authorization service.

**Code**:
```python
# ❌ Authorization in auth.py
async def verify_parent_owns_child(parent_id: str, child_id: str) -> bool:
    """Verify that a parent owns/can access a child."""
    # This is authorization, not authentication

async def verify_staff_at_school(user_id: str, school_id: str) -> bool:
    """Verify that a user is staff at a school."""
    # This is authorization, not authentication
```

**Proper Separation**:
```
Authentication: "Who are you?" (auth.py)
  - signup_user
  - login_user
  - validate_session

Authorization: "What can you do?" (NEW: authorization.py)
  - verify_parent_owns_child
  - verify_staff_at_school
  - check_permission
```

**Recommended Fix**:
```python
# NEW: authorization.py
class AuthorizationService:
    def __init__(self, db_client: DatabaseClient):
        self.db = db_client

    async def verify_parent_owns_child(
        self, parent_id: str, child_id: str
    ) -> bool:
        """Check parent-child ownership"""
        ...

    async def verify_staff_at_school(
        self, user_id: str, school_id: str
    ) -> bool:
        """Check staff-school relationship"""
        ...

    async def can_schedule_pickup(
        self, user: UserProfile, child_ids: List[str]
    ) -> bool:
        """Complex authorization: Can user schedule pickup for these children?"""
        if user.role != "parent":
            return False

        for child_id in child_ids:
            if not await self.verify_parent_owns_child(user.id, child_id):
                return False

        return True
```

---

## 5. Missing Patterns

### 🟠 HIGH: No Repository Pattern

**Current State**: Direct Supabase queries scattered throughout code

**Code Examples**:
```python
# ❌ In main.py (lines 411-423)
supabase.table("children").select("school_id, schools(*)").in_("id", child_ids).execute()

# ❌ In main.py (lines 460-467)
supabase.table("pickups").insert(pickup_data).execute()
supabase.table("pickup_children").insert({"pickup_id": ..., "child_id": ...}).execute()

# ❌ In auth.py (lines 455-456)
supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
```

**Problems**:
- No abstraction over data access
- Hard to test (requires real DB)
- Cannot swap storage backend
- Query logic duplicated

**Recommended Fix**:
```python
# NEW: repositories/pickup_repository.py
class PickupRepository:
    def __init__(self, db_client: DatabaseClient):
        self.db = db_client

    async def get_by_id(self, pickup_id: str) -> Optional[Pickup]:
        data = await self.db.query_one("pickups", {"id": pickup_id})
        return Pickup.from_dict(data) if data else None

    async def get_school_pickups(
        self, school_id: str, start_time: datetime, end_time: datetime
    ) -> List[Pickup]:
        data = await self.db.query(
            "pickups",
            {
                "school_id": school_id,
                "scheduled_time__gte": start_time,
                "scheduled_time__lte": end_time,
            }
        )
        return [Pickup.from_dict(d) for d in data]

    async def create(self, pickup: Pickup) -> Pickup:
        data = await self.db.insert("pickups", pickup.to_dict())
        return Pickup.from_dict(data)
```

**Benefits**:
- ✅ Single source of truth for queries
- ✅ Easy to test (mock repository)
- ✅ Can add caching layer
- ✅ Type-safe with domain models

---

### 🟡 MEDIUM: No Dependency Injection

**Current State**: Dependencies hardcoded via global functions

**Code Examples**:
```python
# ❌ Hardcoded dependency
def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = create_client(url, key)
    return _supabase_client

# ❌ Used everywhere
async def create_pickup_request(...):
    supabase = get_supabase()  # Cannot inject mock
```

**Problems**:
- Cannot mock dependencies
- Hard to test
- Cannot configure per-environment
- Tight coupling to implementations

**Recommended Fix**:
```python
# NEW: container.py (Dependency Injection Container)
from dataclasses import dataclass

@dataclass
class ServiceContainer:
    """Container for all application dependencies"""

    # Database
    db_client: DatabaseClient

    # Repositories
    pickup_repository: PickupRepository
    school_repository: SchoolRepository
    user_repository: UserRepository

    # Services
    auth_service: AuthenticationService
    authorization_service: AuthorizationService
    pickup_service: PickupService
    monitoring_service: MonitoringService

    @classmethod
    def create_production(cls) -> "ServiceContainer":
        """Create production dependencies"""
        db_client = DatabaseFactory.create_client("supabase")

        # Repositories
        pickup_repo = PickupRepository(db_client)
        school_repo = SchoolRepository(db_client)
        user_repo = UserRepository(db_client)

        # Services
        auth_service = AuthenticationService(user_repo, db_client)
        authz_service = AuthorizationService(user_repo, pickup_repo)
        pickup_service = PickupService(pickup_repo, school_repo)
        monitoring_service = MonitoringService()

        return cls(
            db_client=db_client,
            pickup_repository=pickup_repo,
            school_repository=school_repo,
            user_repository=user_repo,
            auth_service=auth_service,
            authorization_service=authz_service,
            pickup_service=pickup_service,
            monitoring_service=monitoring_service,
        )

    @classmethod
    def create_test(cls) -> "ServiceContainer":
        """Create test dependencies with mocks"""
        db_client = MockDatabaseClient()
        # ... rest with mocks

# Usage in handlers:
container = ServiceContainer.create_production()

async def _handle_pickup_schedule_create(arguments: Dict):
    # ✅ Injected dependencies
    pickup_service = container.pickup_service
    authz_service = container.authorization_service

    user = await container.auth_service.validate_session(token)
    if not await authz_service.can_schedule_pickup(user, child_ids):
        return error_response()

    pickup = await pickup_service.schedule_pickup(...)
    return success_response(pickup)
```

---

### 🟢 LOW: No Domain Models

**Current State**: Dictionaries used throughout

**Code Examples**:
```python
# ❌ Using raw dicts
pickup_data = {
    "id": pickup_id,
    "pickup_person_id": pickup_person_id,
    "scheduled_time": scheduled_time,
    "status": "confirmed",
    "notes": notes,
}

response = supabase.table("pickups").insert(pickup_data).execute()
```

**Recommended Fix**:
```python
# NEW: domain/pickup.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from enum import Enum

class PickupStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    LATE = "late"

@dataclass
class Pickup:
    """Domain model for pickup request"""

    id: str
    pickup_person_id: str
    child_ids: List[str]
    scheduled_time: datetime
    status: PickupStatus
    notes: Optional[str] = None
    eta_minutes: Optional[int] = None
    delay_minutes: int = 0

    @classmethod
    def from_dict(cls, data: dict) -> "Pickup":
        """Create from database dict"""
        return cls(
            id=data["id"],
            pickup_person_id=data["pickup_person_id"],
            child_ids=data.get("child_ids", []),
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]),
            status=PickupStatus(data["status"]),
            notes=data.get("notes"),
            eta_minutes=data.get("eta_minutes"),
            delay_minutes=data.get("delay_minutes", 0),
        )

    def to_dict(self) -> dict:
        """Convert to database dict"""
        return {
            "id": self.id,
            "pickup_person_id": self.pickup_person_id,
            "scheduled_time": self.scheduled_time.isoformat(),
            "status": self.status.value,
            "notes": self.notes,
            "eta_minutes": self.eta_minutes,
            "delay_minutes": self.delay_minutes,
        }

    def is_late(self) -> bool:
        """Business logic: Check if pickup is late"""
        return self.status == PickupStatus.LATE or self.delay_minutes > 0

    def can_cancel(self) -> bool:
        """Business logic: Can this pickup be cancelled?"""
        return self.status in [PickupStatus.PENDING, PickupStatus.CONFIRMED]
```

**Benefits**:
- ✅ Type safety
- ✅ IDE autocomplete
- ✅ Business logic on models
- ✅ Validation

---

## 6. Configuration Issues

### 🟢 LOW: Environment Variables Not Validated

**File**: `/home/user/openai-apps-sdk-examples/allobye_server_python/main.py`
**Lines**: 80-84

**Code**:
```python
# ❌ No validation
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")
```

**Recommended Fix**:
```python
# NEW: config.py
from pydantic import BaseSettings, validator

class Settings(BaseSettings):
    """Application configuration with validation"""

    # Supabase
    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    # Server
    environment: str = "production"
    log_level: str = "INFO"

    # Monitoring
    enable_metrics: bool = True
    enable_tracing: bool = True

    @validator("supabase_url")
    def validate_url(cls, v):
        if not v.startswith("https://"):
            raise ValueError("Supabase URL must start with https://")
        return v

    @validator("log_level")
    def validate_log_level(cls, v):
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v

    class Config:
        env_file = ".env"
        case_sensitive = False

# Usage:
settings = Settings()  # Validates and loads from .env
```

---

## Summary

### Violations by Severity

| Severity | Count | Priority |
|----------|-------|----------|
| 🔴 CRITICAL | 1 | Fix immediately (main.py God Object) |
| 🟠 HIGH | 4 | Address in next sprint |
| 🟡 MEDIUM | 4 | Technical debt, plan refactoring |
| 🟢 LOW | 2 | Nice to have |

### Top 5 Issues to Address

1. **🔴 Split main.py** (1,583 lines → 10+ modules)
2. **🟠 Fix Frontend-Database Coupling** (Add WebSocket through MCP)
3. **🟠 Simplify RLS Policies** (Move business logic to app layer)
4. **🟠 Add Repository Pattern** (Abstract data access)
5. **🟡 Separate Monitoring Concerns** (Split monitoring.py into focused modules)

### Metrics

| Metric | Current | Target | Gap |
|--------|---------|--------|-----|
| Files in main.py | 1 | 10+ | -9 |
| Avg lines per module | 750 | 200 | -550 |
| Direct DB access points | ~15 | 0 (via repos) | -15 |
| RLS policies with business logic | 21 | 7 (ownership only) | -14 |
| Abstraction layers | 3 | 5 (+ repo + domain) | -2 |

---

## Testing Impact

### Current Testability: ⚠️ Poor

**Why**:
- God object (main.py) requires full integration test
- Direct Supabase coupling requires real database
- No dependency injection → cannot mock
- Business logic in database → cannot unit test

**Example**:
```python
# ❌ Cannot unit test this:
async def create_pickup_request(...):
    supabase = get_supabase()  # Requires real Supabase
    response = supabase.table("pickups").insert(...).execute()  # Real DB call
```

### Target Testability: ✅ Good

**After Refactoring**:
```python
# ✅ Can unit test:
class TestPickupService:
    def setup(self):
        self.mock_repo = Mock(spec=PickupRepository)
        self.service = PickupService(self.mock_repo)

    async def test_schedule_pickup(self):
        self.mock_repo.create.return_value = Pickup(...)

        result = await self.service.schedule_pickup(...)

        assert result.status == PickupStatus.CONFIRMED
        self.mock_repo.create.assert_called_once()
```

---

## Conclusion

AllôBye has a **solid foundation** with excellent security, observability, and MCP integration. The identified violations are primarily **structural** rather than functional:

**Critical Path**:
1. Decompose main.py (God Object)
2. Add abstraction layers (Repository, Domain Models)
3. Implement Dependency Injection

These changes will improve **testability**, **maintainability**, and **scalability** without changing functionality.

**Estimated Refactoring Effort**: 2-3 sprints (4-6 weeks)
