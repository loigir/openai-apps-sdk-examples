# Architectural Recommendations - AllôBye

**Date**: 2025-11-04
**Project**: AllôBye School Pickup Coordination System
**Objective**: Transform from good to excellent architecture

---

## Executive Summary

AllôBye is a **well-architected system** with strong fundamentals in security, observability, and real-time capabilities. The recommendations below focus on improving **maintainability**, **testability**, and **scalability** through strategic refactoring.

**Current State**: Production-ready with technical debt
**Target State**: Industry best practices, fully modular, highly testable

**Estimated Effort**: 4-6 weeks (2-3 sprints)
**Risk**: Low (refactoring, not feature changes)
**Business Impact**: Improved development velocity, reduced bugs

---

## Priority Matrix

| Phase | Priority | Effort | Impact | Timeline |
|-------|----------|--------|--------|----------|
| Phase 1: Decomposition | 🔴 Critical | High | High | Week 1-2 |
| Phase 2: Abstractions | 🟠 High | Medium | High | Week 3-4 |
| Phase 3: Testing | 🟡 Medium | Medium | Medium | Week 5-6 |
| Phase 4: Optimization | 🟢 Low | Low | Low | Future |

---

## Phase 1: Decompose God Objects (Weeks 1-2)

### Goal
Split monolithic files into focused, single-responsibility modules.

### 1.1 Decompose main.py (1,583 lines → 10+ modules)

**Current Structure**:
```
allobye_server_python/
└── main.py (1,583 lines)  # ❌ God Object
```

**Recommended Structure**:
```
allobye_server_python/
├── main.py (< 100 lines)               # Server setup only
├── config.py                            # Configuration
├── container.py                         # Dependency injection
│
├── handlers/                            # MCP tool handlers
│   ├── __init__.py
│   ├── auth_handlers.py                 # Auth tools (5 handlers)
│   ├── pickup_handlers.py               # Pickup tools (3 handlers)
│   └── monitoring_handlers.py           # Monitoring tool (1 handler)
│
├── services/                            # Business logic
│   ├── __init__.py
│   ├── auth.py                          # ✅ Already exists
│   ├── monitoring.py                    # ✅ Already exists
│   ├── pickup_service.py                # NEW: Pickup orchestration
│   ├── school_service.py                # NEW: School logic
│   └── authorization_service.py         # NEW: Moved from auth.py
│
├── repositories/                        # Data access
│   ├── __init__.py
│   ├── base_repository.py               # Abstract base
│   ├── pickup_repository.py             # Pickup data access
│   ├── school_repository.py             # School data access
│   ├── child_repository.py              # Child data access
│   └── delegate_repository.py           # Delegate data access
│
├── domain/                              # Domain models
│   ├── __init__.py
│   ├── pickup.py                        # Pickup entity
│   ├── child.py                         # Child entity
│   ├── school.py                        # School entity
│   └── delegate.py                      # Delegate entity
│
├── database/                            # Database abstraction
│   ├── __init__.py
│   ├── client.py                        # Abstract DatabaseClient
│   ├── supabase_client.py               # Supabase implementation
│   └── factory.py                       # Client factory
│
├── widgets/                             # Widget configuration
│   ├── __init__.py
│   ├── widget_manager.py                # Widget loading
│   └── widget_models.py                 # Widget dataclasses
│
└── middleware/                          # Request middleware
    ├── __init__.py
    ├── auth_middleware.py               # JWT validation
    └── monitoring_middleware.py         # Metrics, logging
```

**Implementation Steps**:

#### Step 1: Create Directory Structure
```bash
cd allobye_server_python
mkdir -p handlers services repositories domain database widgets middleware
touch handlers/__init__.py services/__init__.py repositories/__init__.py
touch domain/__init__.py database/__init__.py widgets/__init__.py middleware/__init__.py
```

#### Step 2: Extract Handlers (Day 1)

**NEW: handlers/auth_handlers.py**
```python
"""Authentication tool handlers."""

from typing import Dict, Any
import mcp.types as types
from pydantic import ValidationError

from services.auth import signup_user, login_user, logout_user, reset_password_request
from domain.auth import AuthSignupInput, AuthLoginInput, AuthResetPasswordInput


async def handle_auth_signup(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle user signup."""
    try:
        payload = AuthSignupInput.model_validate(arguments)
    except ValidationError as exc:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Erreur: {exc.errors()}")],
            isError=True,
        )

    try:
        result = await signup_user(
            email=payload.email,
            password=payload.password,
            name=payload.name,
            role=payload.role,
            schools=payload.schools,
        )

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"✓ Compte créé pour {payload.email}",
                )
            ],
            structuredContent={
                "user_id": result["user"]["id"],
                "email": result["user"]["email"],
            },
        )
    except Exception as e:
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=f"Erreur: {str(e)}")],
            isError=True,
        )


async def handle_auth_login(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle user login."""
    # Similar pattern...


async def handle_auth_logout(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle user logout."""
    # ...
```

**NEW: handlers/pickup_handlers.py**
```python
"""Pickup management tool handlers."""

from typing import Dict, Any
import mcp.types as types

from services.pickup_service import PickupService
from services.authorization_service import AuthorizationService
from middleware.auth_middleware import get_current_user
from container import get_container


async def handle_pickup_schedule_create(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle pickup scheduling."""
    container = get_container()
    pickup_service = container.pickup_service
    authz_service = container.authorization_service

    # Authenticate
    user = await get_current_user(arguments)
    if not user or user.role != "parent":
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="Authentification requise")],
            isError=True,
        )

    # Parse input
    payload = PickupScheduleInput.model_validate(arguments)

    # Authorize
    if not await authz_service.can_schedule_pickup(user.id, payload.child_ids):
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="Non autorisé")],
            isError=True,
        )

    # Execute business logic
    pickup = await pickup_service.schedule_pickup(
        child_ids=payload.child_ids,
        pickup_person_id=payload.pickup_person_id,
        scheduled_time=payload.scheduled_time,
        notes=payload.notes,
    )

    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=f"✓ Ramassage confirmé pour {len(payload.child_ids)} enfant(s)",
            )
        ],
        structuredContent=pickup.to_dict(),
    )
```

**Updated: main.py** (simplified)
```python
"""AllôBye MCP server - Main entry point."""

from mcp.server.fastmcp import FastMCP
from container import ServiceContainer
from handlers import auth_handlers, pickup_handlers, monitoring_handlers
from widgets.widget_manager import WidgetManager


# Initialize dependencies
container = ServiceContainer.create_production()
widget_manager = WidgetManager(ASSETS_DIR)

# Create MCP server
mcp = FastMCP(name="allobye-server", stateless_http=True)


# Register tool handlers
TOOL_HANDLERS = {
    # Authentication
    "auth-signup": auth_handlers.handle_auth_signup,
    "auth-login": auth_handlers.handle_auth_login,
    "auth-logout": auth_handlers.handle_auth_logout,
    "auth-reset-password": auth_handlers.handle_auth_reset_password,
    "auth-profile": auth_handlers.handle_auth_profile,

    # Pickup management
    "pickup-schedule-create": pickup_handlers.handle_pickup_schedule_create,
    "delegate-authorize": pickup_handlers.handle_delegate_authorize,
    "emergency-declare": pickup_handlers.handle_emergency_declare,
    "school-dashboard-fetch": pickup_handlers.handle_school_dashboard_fetch,

    # Monitoring
    "monitoring-dashboard-fetch": monitoring_handlers.handle_monitoring_dashboard_fetch,
}


@mcp._mcp_server.list_tools()
async def list_tools() -> List[types.Tool]:
    """List all available tools."""
    # Tool definitions stay here (metadata only)
    return [...]


async def call_tool_handler(req: types.CallToolRequest) -> types.ServerResult:
    """Route tool calls to handlers with monitoring."""
    tool_name = req.params.name
    arguments = req.params.arguments or {}

    handler = TOOL_HANDLERS.get(tool_name)
    if not handler:
        return error_result(f"Unknown tool: {tool_name}")

    # Monitoring wrapper
    start_time = time.time()
    try:
        result = await handler(arguments)
        container.metrics.record_success(tool_name, time.time() - start_time)
        return types.ServerResult(result)
    except Exception as e:
        container.metrics.record_error(tool_name, str(e))
        raise


# Register handler
mcp._mcp_server.request_handlers[types.CallToolRequest] = call_tool_handler

# Create app
app = mcp.streamable_http_app()

# Add health/metrics endpoints
app.router.routes.extend([
    Route("/health", container.health_service.health_endpoint),
    Route("/metrics", container.metrics.metrics_endpoint),
])


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
```

**Benefits**:
- ✅ main.py: 1,583 → ~100 lines (94% reduction)
- ✅ Each handler file: < 200 lines
- ✅ Clear imports: `from handlers.auth_handlers import handle_auth_signup`
- ✅ Easy to test handlers individually

---

### 1.2 Split monitoring.py (753 lines → 6 modules)

**NEW: monitoring/logger.py** (< 150 lines)
```python
"""Structured JSON logging."""

import json
import logging
from datetime import datetime
from typing import Dict, Any


class StructuredLogger:
    """JSON structured logger with contextual fields."""

    def __init__(self, name: str, log_level: str = "INFO"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level))
        self._request_context: Dict[str, Any] = {}

        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        self.logger.handlers = [handler]

    def set_context(self, **context):
        """Set request-level context fields."""
        self._request_context.update(context)

    def clear_context(self):
        """Clear request context."""
        self._request_context = {}

    def info(self, message: str, **extra):
        """Log info message."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": "INFO",
            "message": message,
            **self._request_context,
            **extra,
        }
        self.logger.info(json.dumps(log_data))

    # ... other log methods
```

**NEW: monitoring/metrics.py** (< 200 lines)
```python
"""Metrics collection and Prometheus export."""

from dataclasses import dataclass, field
from collections import defaultdict
from typing import Dict


@dataclass
class ToolMetrics:
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        return self.total_latency_ms / self.call_count if self.call_count > 0 else 0.0


class MetricsCollector:
    """Collects and aggregates metrics."""

    def __init__(self):
        self.tool_metrics: Dict[str, ToolMetrics] = defaultdict(ToolMetrics)
        self.start_time = time.time()

    def record_tool_call(self, tool_name: str, latency_ms: float, success: bool):
        metrics = self.tool_metrics[tool_name]
        metrics.call_count += 1
        metrics.total_latency_ms += latency_ms

        if success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []
        for tool_name, metrics in self.tool_metrics.items():
            lines.append(f'allobye_tool_calls_total{{tool="{tool_name}"}} {metrics.call_count}')
            lines.append(f'allobye_tool_latency_ms{{tool="{tool_name}"}} {metrics.avg_latency_ms:.2f}')
        return "\n".join(lines)
```

**Benefits**:
- ✅ monitoring.py: 753 → 6 files × ~125 lines
- ✅ Import only what you need: `from monitoring.logger import StructuredLogger`
- ✅ Each module has one clear purpose

---

## Phase 2: Add Abstraction Layers (Weeks 3-4)

### Goal
Introduce Repository pattern, Domain Models, and Dependency Injection for better testability.

### 2.1 Repository Pattern

**NEW: repositories/base_repository.py**
```python
"""Abstract base repository."""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, List, Optional, Dict, Any

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base repository for data access."""

    @abstractmethod
    async def get_by_id(self, id: str) -> Optional[T]:
        """Get entity by ID."""
        pass

    @abstractmethod
    async def get_all(self, filters: Dict[str, Any] = None) -> List[T]:
        """Get all entities matching filters."""
        pass

    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create new entity."""
        pass

    @abstractmethod
    async def update(self, id: str, entity: T) -> T:
        """Update existing entity."""
        pass

    @abstractmethod
    async def delete(self, id: str) -> bool:
        """Delete entity."""
        pass
```

**NEW: repositories/pickup_repository.py**
```python
"""Pickup repository for data access."""

from typing import List, Optional, Dict, Any
from datetime import datetime

from repositories.base_repository import BaseRepository
from domain.pickup import Pickup, PickupStatus
from database.client import DatabaseClient


class PickupRepository(BaseRepository[Pickup]):
    """Repository for pickup data access."""

    def __init__(self, db_client: DatabaseClient):
        self.db = db_client

    async def get_by_id(self, id: str) -> Optional[Pickup]:
        """Get pickup by ID."""
        data = await self.db.query_one("pickups", {"id": id})
        return Pickup.from_dict(data) if data else None

    async def get_all(self, filters: Dict[str, Any] = None) -> List[Pickup]:
        """Get all pickups matching filters."""
        data = await self.db.query("pickups", filters or {})
        return [Pickup.from_dict(d) for d in data]

    async def get_school_pickups(
        self,
        school_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> List[Pickup]:
        """Get pickups for a school in time window."""
        data = await self.db.query(
            "pickups",
            {
                "school_id": school_id,
                "scheduled_time__gte": start_time.isoformat(),
                "scheduled_time__lte": end_time.isoformat(),
            },
        )
        return [Pickup.from_dict(d) for d in data]

    async def create(self, pickup: Pickup) -> Pickup:
        """Create new pickup."""
        data = await self.db.insert("pickups", pickup.to_dict())
        return Pickup.from_dict(data)

    async def update_status(self, pickup_id: str, new_status: PickupStatus) -> Pickup:
        """Update pickup status."""
        data = await self.db.update(
            "pickups",
            pickup_id,
            {"status": new_status.value}
        )
        return Pickup.from_dict(data)

    async def cancel(self, pickup_id: str, reason: str) -> Pickup:
        """Cancel a pickup."""
        data = await self.db.update(
            "pickups",
            pickup_id,
            {
                "status": PickupStatus.CANCELLED.value,
                "cancellation_reason": reason,
            }
        )
        return Pickup.from_dict(data)
```

**Benefits**:
- ✅ Single source of truth for data access
- ✅ Easy to test (mock repository)
- ✅ Type-safe with domain models
- ✅ Can add caching layer transparently

---

### 2.2 Domain Models

**NEW: domain/pickup.py**
```python
"""Pickup domain model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from enum import Enum


class PickupStatus(Enum):
    """Pickup status enumeration."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    LATE = "late"


@dataclass
class Pickup:
    """Domain model for pickup request."""

    id: str
    pickup_person_id: str
    child_ids: List[str]
    scheduled_time: datetime
    status: PickupStatus
    school_id: str
    notes: Optional[str] = None
    eta_minutes: Optional[int] = None
    delay_minutes: int = 0
    cancellation_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: dict) -> "Pickup":
        """Create from database dict."""
        return cls(
            id=data["id"],
            pickup_person_id=data["pickup_person_id"],
            child_ids=data.get("child_ids", []),
            scheduled_time=datetime.fromisoformat(data["scheduled_time"]),
            status=PickupStatus(data["status"]),
            school_id=data["school_id"],
            notes=data.get("notes"),
            eta_minutes=data.get("eta_minutes"),
            delay_minutes=data.get("delay_minutes", 0),
            cancellation_reason=data.get("cancellation_reason"),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else None,
        )

    def to_dict(self) -> dict:
        """Convert to database dict."""
        return {
            "id": self.id,
            "pickup_person_id": self.pickup_person_id,
            "scheduled_time": self.scheduled_time.isoformat(),
            "status": self.status.value,
            "school_id": self.school_id,
            "notes": self.notes,
            "eta_minutes": self.eta_minutes,
            "delay_minutes": self.delay_minutes,
            "cancellation_reason": self.cancellation_reason,
        }

    # Business logic methods
    def is_late(self) -> bool:
        """Check if pickup is late."""
        return self.status == PickupStatus.LATE or self.delay_minutes > 0

    def can_cancel(self) -> bool:
        """Check if pickup can be cancelled."""
        return self.status in [PickupStatus.PENDING, PickupStatus.CONFIRMED]

    def can_complete(self) -> bool:
        """Check if pickup can be marked complete."""
        return self.status in [PickupStatus.IN_PROGRESS, PickupStatus.CONFIRMED]

    def mark_in_progress(self) -> "Pickup":
        """Mark pickup as in progress."""
        if self.status != PickupStatus.CONFIRMED:
            raise ValueError("Only confirmed pickups can be marked in progress")
        self.status = PickupStatus.IN_PROGRESS
        return self

    def complete(self) -> "Pickup":
        """Complete the pickup."""
        if not self.can_complete():
            raise ValueError(f"Cannot complete pickup with status: {self.status}")
        self.status = PickupStatus.COMPLETED
        return self
```

**Benefits**:
- ✅ Type safety (IDE autocomplete)
- ✅ Business logic on domain models
- ✅ Validation at domain level
- ✅ Immutable data transformations

---

### 2.3 Dependency Injection

**NEW: container.py**
```python
"""Dependency injection container."""

from dataclasses import dataclass
from typing import Optional

from database.factory import DatabaseFactory
from database.client import DatabaseClient
from repositories.pickup_repository import PickupRepository
from repositories.school_repository import SchoolRepository
from repositories.child_repository import ChildRepository
from repositories.user_repository import UserRepository
from services.auth import AuthenticationService
from services.authorization_service import AuthorizationService
from services.pickup_service import PickupService
from monitoring.logger import StructuredLogger
from monitoring.metrics import MetricsCollector


@dataclass
class ServiceContainer:
    """Container for all application dependencies."""

    # Database
    db_client: DatabaseClient

    # Repositories
    pickup_repository: PickupRepository
    school_repository: SchoolRepository
    child_repository: ChildRepository
    user_repository: UserRepository

    # Services
    auth_service: AuthenticationService
    authorization_service: AuthorizationService
    pickup_service: PickupService

    # Monitoring
    logger: StructuredLogger
    metrics: MetricsCollector

    @classmethod
    def create_production(cls) -> "ServiceContainer":
        """Create production dependencies."""
        # Database client
        db_client = DatabaseFactory.create_client(
            "supabase",
            url=os.getenv("SUPABASE_URL"),
            key=os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
        )

        # Repositories
        pickup_repo = PickupRepository(db_client)
        school_repo = SchoolRepository(db_client)
        child_repo = ChildRepository(db_client)
        user_repo = UserRepository(db_client)

        # Services
        auth_service = AuthenticationService(user_repo, db_client)
        authz_service = AuthorizationService(user_repo, child_repo, pickup_repo)
        pickup_service = PickupService(pickup_repo, school_repo, child_repo)

        # Monitoring
        logger = StructuredLogger("allobye", log_level="INFO")
        metrics = MetricsCollector()

        return cls(
            db_client=db_client,
            pickup_repository=pickup_repo,
            school_repository=school_repo,
            child_repository=child_repo,
            user_repository=user_repo,
            auth_service=auth_service,
            authorization_service=authz_service,
            pickup_service=pickup_service,
            logger=logger,
            metrics=metrics,
        )

    @classmethod
    def create_test(cls, **overrides) -> "ServiceContainer":
        """Create test dependencies with mocks."""
        from database.mock_client import MockDatabaseClient

        # Use mocks by default
        db_client = overrides.get("db_client", MockDatabaseClient())

        # Create repositories with mock DB
        pickup_repo = overrides.get("pickup_repository", PickupRepository(db_client))
        school_repo = overrides.get("school_repository", SchoolRepository(db_client))
        child_repo = overrides.get("child_repository", ChildRepository(db_client))
        user_repo = overrides.get("user_repository", UserRepository(db_client))

        # Create services
        auth_service = overrides.get("auth_service", AuthenticationService(user_repo, db_client))
        authz_service = overrides.get("authorization_service", AuthorizationService(user_repo, child_repo, pickup_repo))
        pickup_service = overrides.get("pickup_service", PickupService(pickup_repo, school_repo, child_repo))

        # Monitoring
        logger = overrides.get("logger", StructuredLogger("allobye-test", log_level="DEBUG"))
        metrics = overrides.get("metrics", MetricsCollector())

        return cls(
            db_client=db_client,
            pickup_repository=pickup_repo,
            school_repository=school_repo,
            child_repository=child_repo,
            user_repository=user_repo,
            auth_service=auth_service,
            authorization_service=authz_service,
            pickup_service=pickup_service,
            logger=logger,
            metrics=metrics,
        )


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container() -> ServiceContainer:
    """Get global container instance."""
    global _container
    if _container is None:
        _container = ServiceContainer.create_production()
    return _container


def set_container(container: ServiceContainer):
    """Set global container (for testing)."""
    global _container
    _container = container
```

**Usage in Tests**:
```python
# test_pickup_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from container import ServiceContainer
from domain.pickup import Pickup, PickupStatus


@pytest.fixture
def container():
    """Create test container with mocks."""
    mock_pickup_repo = Mock()
    mock_pickup_repo.create = AsyncMock(return_value=Pickup(...))

    return ServiceContainer.create_test(
        pickup_repository=mock_pickup_repo,
    )


async def test_schedule_pickup(container):
    """Test pickup scheduling."""
    pickup_service = container.pickup_service

    result = await pickup_service.schedule_pickup(
        child_ids=["child_1"],
        pickup_person_id="delegate_1",
        scheduled_time=datetime.now(),
    )

    assert result.status == PickupStatus.CONFIRMED
    container.pickup_repository.create.assert_called_once()
```

**Benefits**:
- ✅ Easy to test (inject mocks)
- ✅ Single source of dependency configuration
- ✅ Can swap implementations (production vs test)
- ✅ Clear dependency graph

---

## Phase 3: Improve Frontend Architecture (Week 5)

### Goal
Decouple frontend from database schema and enforce layered architecture.

### 3.1 Replace Direct Supabase Realtime with MCP WebSocket

**Problem**: Frontend directly subscribes to database changes
```javascript
// ❌ Current: Direct database coupling
supabase.channel("pickups-changes")
  .on("postgres_changes", { table: "pickups" }, (payload) => { ... })
```

**Solution**: Route real-time updates through MCP server

#### Backend: Add WebSocket Support

**NEW: realtime/websocket_manager.py**
```python
"""WebSocket manager for real-time updates."""

from typing import Dict, Set
from starlette.websockets import WebSocket


class WebSocketManager:
    """Manage WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, school_id: str):
        """Connect a WebSocket for a school."""
        await websocket.accept()

        if school_id not in self.active_connections:
            self.active_connections[school_id] = set()

        self.active_connections[school_id].add(websocket)

    def disconnect(self, websocket: WebSocket, school_id: str):
        """Disconnect a WebSocket."""
        if school_id in self.active_connections:
            self.active_connections[school_id].discard(websocket)

    async def broadcast_to_school(self, school_id: str, message: dict):
        """Broadcast message to all connections for a school."""
        if school_id not in self.active_connections:
            return

        for connection in self.active_connections[school_id].copy():
            try:
                await connection.send_json(message)
            except Exception:
                # Connection closed, remove it
                self.active_connections[school_id].discard(connection)
```

**NEW: realtime/supabase_listener.py**
```python
"""Listen to Supabase Realtime and forward to WebSockets."""

import asyncio
from supabase import create_client

from realtime.websocket_manager import WebSocketManager


class SupabaseRealtimeListener:
    """Listen to Supabase Realtime and broadcast to WebSockets."""

    def __init__(self, websocket_manager: WebSocketManager, supabase_url: str, supabase_key: str):
        self.ws_manager = websocket_manager
        self.supabase = create_client(supabase_url, supabase_key)

    async def start_listening(self):
        """Start listening to Supabase Realtime."""
        channel = self.supabase.channel("pickups-changes")

        def handle_pickup_change(payload):
            """Handle pickup change event."""
            asyncio.create_task(self._process_pickup_change(payload))

        channel.on("postgres_changes", {"table": "pickups"}, handle_pickup_change)
        channel.subscribe()

    async def _process_pickup_change(self, payload):
        """Process pickup change and broadcast to relevant school."""
        event_type = payload.get("eventType")
        new_data = payload.get("new")

        if not new_data:
            return

        school_id = new_data.get("school_id")
        if not school_id:
            return

        # Transform DB event to business event
        business_event = {
            "type": "pickup_update",
            "action": event_type.lower(),
            "data": {
                "id": new_data["id"],
                "status": new_data["status"],
                "scheduled_time": new_data["scheduled_time"],
                # Don't expose all DB fields
            },
        }

        # Broadcast to school's WebSocket connections
        await self.ws_manager.broadcast_to_school(school_id, business_event)
```

**Add to main.py**:
```python
from starlette.websockets import WebSocket
from realtime.websocket_manager import WebSocketManager
from realtime.supabase_listener import SupabaseRealtimeListener

# Initialize WebSocket manager
ws_manager = WebSocketManager()
realtime_listener = SupabaseRealtimeListener(
    ws_manager,
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_ROLE_KEY"),
)


@app.on_event("startup")
async def startup():
    """Start Supabase Realtime listener on server startup."""
    await realtime_listener.start_listening()


@app.websocket("/ws/schools/{school_id}")
async def websocket_endpoint(websocket: WebSocket, school_id: str):
    """WebSocket endpoint for school real-time updates."""
    await ws_manager.connect(websocket, school_id)

    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except Exception:
        pass
    finally:
        ws_manager.disconnect(websocket, school_id)
```

#### Frontend: Replace Supabase with MCP WebSocket

**Updated: dashboard.jsx**
```javascript
// ✅ New: WebSocket through MCP server
useEffect(() => {
  if (!schoolInfo?.id) return;

  const wsUrl = import.meta.env.VITE_MCP_SERVER_WS || 'ws://localhost:8000';
  const ws = new WebSocket(`${wsUrl}/ws/schools/${schoolInfo.id}`);

  ws.onmessage = (event) => {
    const businessEvent = JSON.parse(event.data);

    if (businessEvent.type === 'pickup_update') {
      // Update UI with business event (not raw DB payload)
      setRealtimePickups((prev) => {
        if (businessEvent.action === 'insert' || businessEvent.action === 'update') {
          const updated = prev.filter((p) => p.id !== businessEvent.data.id);
          return [...updated, businessEvent.data].sort(
            (a, b) => new Date(a.scheduled_time) - new Date(b.scheduled_time)
          );
        } else if (businessEvent.action === 'delete') {
          return prev.filter((p) => p.id !== businessEvent.data.id);
        }
        return prev;
      });
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
  };

  ws.onclose = () => {
    console.log('WebSocket disconnected');
    // Implement reconnection logic
  };

  return () => {
    ws.close();
  };
}, [schoolInfo]);
```

**Benefits**:
- ✅ Frontend decoupled from database schema
- ✅ Backend controls what data is exposed
- ✅ Can enforce business rules on real-time events
- ✅ Easier to test (mock WebSocket)

---

## Phase 4: Testing & Quality (Week 6)

### Goal
Achieve 80%+ test coverage with unit and integration tests.

### 4.1 Unit Tests for Services

**NEW: tests/unit/test_pickup_service.py**
```python
"""Unit tests for PickupService."""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock

from container import ServiceContainer
from services.pickup_service import PickupService
from domain.pickup import Pickup, PickupStatus
from domain.child import Child
from domain.school import School


@pytest.fixture
def container():
    """Create test container with mocks."""
    # Mock repositories
    mock_pickup_repo = Mock()
    mock_school_repo = Mock()
    mock_child_repo = Mock()

    # Configure mocks
    mock_pickup_repo.create = AsyncMock()
    mock_school_repo.get_by_id = AsyncMock()
    mock_child_repo.get_by_id = AsyncMock()

    return ServiceContainer.create_test(
        pickup_repository=mock_pickup_repo,
        school_repository=mock_school_repo,
        child_repository=mock_child_repo,
    )


@pytest.mark.asyncio
async def test_schedule_pickup_success(container):
    """Test successful pickup scheduling."""
    # Arrange
    pickup_service = container.pickup_service
    pickup_repo = container.pickup_repository
    child_repo = container.child_repository

    child = Child(id="child_1", name="Sophie", school_id="school_1")
    child_repo.get_by_id.return_value = child

    expected_pickup = Pickup(
        id="pickup_1",
        pickup_person_id="delegate_1",
        child_ids=["child_1"],
        scheduled_time=datetime.now() + timedelta(hours=1),
        status=PickupStatus.CONFIRMED,
        school_id="school_1",
    )
    pickup_repo.create.return_value = expected_pickup

    # Act
    result = await pickup_service.schedule_pickup(
        child_ids=["child_1"],
        pickup_person_id="delegate_1",
        scheduled_time=datetime.now() + timedelta(hours=1),
    )

    # Assert
    assert result.id == "pickup_1"
    assert result.status == PickupStatus.CONFIRMED
    assert len(result.child_ids) == 1
    pickup_repo.create.assert_called_once()


@pytest.mark.asyncio
async def test_schedule_pickup_invalid_time(container):
    """Test scheduling pickup in the past fails."""
    pickup_service = container.pickup_service

    with pytest.raises(ValueError, match="Cannot schedule pickup in the past"):
        await pickup_service.schedule_pickup(
            child_ids=["child_1"],
            pickup_person_id="delegate_1",
            scheduled_time=datetime.now() - timedelta(hours=1),  # Past time
        )
```

### 4.2 Integration Tests

**NEW: tests/integration/test_pickup_flow.py**
```python
"""Integration tests for pickup flow."""

import pytest
from datetime import datetime, timedelta

from container import ServiceContainer


@pytest.fixture
async def integration_container():
    """Create container with real database (test instance)."""
    return ServiceContainer.create_production()  # Uses test DB


@pytest.mark.asyncio
@pytest.mark.integration
async def test_full_pickup_flow(integration_container):
    """Test complete pickup flow from scheduling to completion."""
    # Services
    pickup_service = integration_container.pickup_service
    authz_service = integration_container.authorization_service

    # 1. Schedule pickup
    pickup = await pickup_service.schedule_pickup(
        child_ids=["test_child_1"],
        pickup_person_id="test_delegate_1",
        scheduled_time=datetime.now() + timedelta(hours=1),
    )

    assert pickup.status == PickupStatus.CONFIRMED

    # 2. Mark in progress
    pickup = await pickup_service.start_pickup(pickup.id)
    assert pickup.status == PickupStatus.IN_PROGRESS

    # 3. Complete pickup
    pickup = await pickup_service.complete_pickup(pickup.id)
    assert pickup.status == PickupStatus.COMPLETED

    # 4. Verify children checked out
    children = await pickup_service.get_pickup_children(pickup.id)
    assert all(child.checked_out for child in children)
```

### 4.3 End-to-End Tests

**NEW: tests/e2e/test_mcp_tools.py**
```python
"""End-to-end tests for MCP tools."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
@pytest.mark.e2e
async def test_auth_login_flow():
    """Test complete authentication flow via MCP."""
    async with AsyncClient(base_url="http://localhost:8000") as client:
        # 1. Signup
        signup_response = await client.post(
            "/mcp/tools/auth-signup",
            json={
                "email": "test@example.com",
                "password": "password123",
                "role": "parent",
            },
        )
        assert signup_response.status_code == 200

        # 2. Login
        login_response = await client.post(
            "/mcp/tools/auth-login",
            json={
                "email": "test@example.com",
                "password": "password123",
            },
        )
        assert login_response.status_code == 200
        data = login_response.json()
        assert "access_token" in data["structuredContent"]

        access_token = data["structuredContent"]["access_token"]

        # 3. Get profile
        profile_response = await client.post(
            "/mcp/tools/auth-profile",
            json={"accessToken": access_token},
        )
        assert profile_response.status_code == 200
        profile = profile_response.json()["structuredContent"]
        assert profile["email"] == "test@example.com"
```

---

## Phase 5: Database Optimization (Future)

### 5.1 Simplify RLS Policies

**Current**: Complex business logic in RLS
```sql
-- ❌ Complex logic in database
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

**Recommended**: Simple ownership checks only
```sql
-- ✅ Simple ownership in RLS
CREATE POLICY "Service role full access"
    ON pickups FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- ✅ Direct ownership only
CREATE POLICY "Parents can view own records"
    ON children FOR SELECT
    USING (parent_id = auth.uid());
```

**Move authorization to application**:
```python
# ✅ Complex authorization in code
class AuthorizationService:
    async def can_view_pickup(self, user: UserProfile, pickup_id: str) -> bool:
        pickup = await self.pickup_repo.get_by_id(pickup_id)

        if user.role == "parent":
            return await self._is_parent_of_any_child(user.id, pickup.child_ids)
        elif user.role == "delegate":
            return user.id == pickup.pickup_person_id
        elif user.role == "school_staff":
            return await self._is_staff_at_school(user.id, pickup.school_id)

        return False
```

**Benefits**:
- ✅ RLS enforces row ownership only (simple, fast)
- ✅ Business logic in application (testable, visible)
- ✅ Can log authorization decisions
- ✅ Easier to debug

---

### 5.2 Move Business Logic Out of Triggers

**Current**: Business rules in triggers
```sql
-- ❌ Business logic in trigger
CREATE FUNCTION cascade_pickup_status() RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'cancelled' THEN
        UPDATE pickup_children SET checked_out = FALSE WHERE pickup_id = NEW.id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Recommended**: Explicit in application
```python
# ✅ Explicit business logic
class PickupService:
    async def cancel_pickup(self, pickup_id: str, reason: str):
        """Cancel a pickup with explicit business logic."""
        async with self.db.transaction():
            # Update pickup status
            pickup = await self.pickup_repo.update_status(pickup_id, PickupStatus.CANCELLED)

            # Uncheck all children (explicit, not hidden in trigger)
            await self.pickup_repo.uncheck_all_children(pickup_id)

            # Audit log
            await self.audit_log.record("pickup_cancelled", pickup_id, reason)

            # Send notifications
            await self.notification_service.notify_pickup_cancelled(pickup)

            self.logger.info("Pickup cancelled", pickup_id=pickup_id, reason=reason)

        return pickup
```

**Benefits**:
- ✅ Business logic visible in code
- ✅ Can unit test
- ✅ Can log each step
- ✅ Easier to debug

---

## Implementation Timeline

### Week 1: Decompose main.py
- Day 1-2: Extract handlers to `handlers/` directory
- Day 3-4: Create service modules (pickup_service.py, authorization_service.py)
- Day 5: Update main.py to use new structure

### Week 2: Split monitoring.py
- Day 1: Extract logger to `monitoring/logger.py`
- Day 2: Extract metrics to `monitoring/metrics.py`
- Day 3: Extract tracer, middleware, alerting
- Day 4-5: Update imports across codebase

### Week 3: Add Repository Pattern
- Day 1-2: Create base repository and database abstraction
- Day 3-4: Implement pickup, school, child repositories
- Day 5: Replace direct Supabase calls with repositories

### Week 4: Add Domain Models & DI
- Day 1-2: Create domain models (Pickup, Child, School, etc.)
- Day 3-4: Implement dependency injection container
- Day 5: Update services to use DI

### Week 5: Frontend Refactoring
- Day 1-2: Add WebSocket manager and Supabase listener
- Day 3-4: Update dashboard to use MCP WebSocket
- Day 5: Remove direct Supabase dependency from frontend

### Week 6: Testing
- Day 1-2: Write unit tests for services
- Day 3: Write integration tests
- Day 4-5: Write E2E tests for MCP tools

---

## Success Metrics

| Metric | Before | After | Target |
|--------|--------|-------|--------|
| **Code Organization** |
| Largest file (lines) | 1,583 | < 200 | ✅ |
| Average module size | 750 | < 200 | ✅ |
| **Architecture** |
| Abstraction layers | 3 | 5 | ✅ |
| Frontend-DB coupling | Direct | Via MCP | ✅ |
| Dependency injection | None | Full | ✅ |
| **Testing** |
| Unit test coverage | 0% | 80%+ | ✅ |
| Integration tests | 0 | 20+ | ✅ |
| E2E tests | 0 | 10+ | ✅ |
| **Maintainability** |
| Can swap DB backend | No | Yes | ✅ |
| Can test without real DB | No | Yes | ✅ |
| Clear module boundaries | No | Yes | ✅ |

---

## Risk Mitigation

### Refactoring Risks

1. **Breaking Changes**
   - **Risk**: Refactoring breaks existing functionality
   - **Mitigation**: Write tests before refactoring, incremental changes

2. **Performance Regression**
   - **Risk**: Abstraction layers add latency
   - **Mitigation**: Benchmark before/after, optimize hot paths

3. **Team Adoption**
   - **Risk**: Team unfamiliar with new patterns
   - **Mitigation**: Documentation, pair programming, gradual rollout

### Migration Strategy

**Phase-by-Phase Rollout**:
1. ✅ Create new structure alongside old code
2. ✅ Write tests for new structure
3. ✅ Migrate one module at a time
4. ✅ Keep old code until all tests pass
5. ✅ Remove old code only after validation

**Rollback Plan**:
- Keep old main.py as main_backup.py until fully validated
- Feature flags for new vs old code paths
- Database schema changes reversible

---

## Long-Term Benefits

### Development Velocity
- ✅ Faster onboarding (clear module boundaries)
- ✅ Fewer bugs (testable code)
- ✅ Easier to add features (dependency injection)

### Scalability
- ✅ Can split services into microservices
- ✅ Can add caching layer transparently
- ✅ Can swap database backends

### Maintenance
- ✅ Easier to debug (explicit flow)
- ✅ Easier to refactor (small modules)
- ✅ Easier to upgrade dependencies (isolated)

---

## Conclusion

These recommendations transform AllôBye from a **good** to an **excellent** architecture while preserving all existing functionality. The refactoring is low-risk and delivers immediate benefits in testability, maintainability, and developer productivity.

**Recommended Start**: Phase 1 (Decompose main.py) - immediate impact, low risk.

**Questions?** Refer to architecture_analysis.md and violations.md for detailed context.
