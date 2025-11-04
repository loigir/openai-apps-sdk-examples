# Refactoring Recipes - AllôBye

**Date**: 2025-11-04
**Type**: Step-by-Step Implementation Guides
**Objectif**: Fournir des recettes concrètes pour corriger chaque anti-pattern

---

## Table des Matières

1. [Quick Wins Recipes](#1-quick-wins-recipes)
2. [Critical Wins Recipes](#2-critical-wins-recipes)
3. [Strategic Refactoring Recipes](#3-strategic-refactoring-recipes)
4. [Testing Strategy](#4-testing-strategy)

---

## 1. Quick Wins Recipes

### Recipe #1: Extract Magic Numbers/Strings

**Time**: 2 heures
**Impact**: LOW
**Effort**: LOW
**ROI**: 10.0

#### Step-by-Step

**BEFORE**: Magic numbers scattered everywhere
```javascript
// dashboard.jsx
const timer = setInterval(() => {
  setCurrentTime(new Date());
}, 1000);  // ❌ Magic number

setTimeout(() => {
  setState({ ...state, alert: null });
}, 30000);  // ❌ Magic number
```

**STEP 1**: Create constants file (15 min)
```javascript
// src/constants/timeouts.ts
export const TIMEOUTS = {
  CLOCK_UPDATE_MS: 1000,
  ALERT_DURATION_MS: 30_000,
  REFRESH_INTERVAL_S: 30,
  PICKUP_WINDOW_MINUTES: 30,
} as const;

export const TIME_WINDOWS = {
  CURRENT: 'current',
  TODAY: 'today',
  CUSTOM: 'custom',
} as const;

export const PICKUP_STATUSES = {
  PENDING: 'pending',
  CONFIRMED: 'confirmed',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
  LATE: 'late',
} as const;
```

**STEP 2**: Update all usages (1h 30 min)
```javascript
// dashboard.jsx
import { TIMEOUTS, TIME_WINDOWS } from '../constants/timeouts';

const timer = setInterval(() => {
  setCurrentTime(new Date());
}, TIMEOUTS.CLOCK_UPDATE_MS);  // ✅ Named constant

setTimeout(() => {
  setState({ ...state, alert: null });
}, TIMEOUTS.ALERT_DURATION_MS);  // ✅ Named constant

const thirtyMinutesFromNow = new Date(
  currentTime.getTime() + TIMEOUTS.PICKUP_WINDOW_MINUTES * 60 * 1000
);
```

**STEP 3**: Update Python constants (15 min)
```python
# NEW: allobye_server_python/constants.py
from enum import Enum

class TimeWindow(str, Enum):
    CURRENT = "current"
    TODAY = "today"
    CUSTOM = "custom"

class PickupStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    LATE = "late"

# Use in models
class PickupScheduleInput(BaseModel):
    time_window: TimeWindow = TimeWindow.CURRENT
```

**✓ Checklist**:
- [ ] Create constants file
- [ ] Replace all magic numbers in React
- [ ] Replace all magic strings in React
- [ ] Replace all magic numbers in Python
- [ ] Replace all magic strings in Python
- [ ] Update tests

---

### Recipe #2: Validate Environment Variables

**Time**: 3 heures
**Impact**: LOW
**Effort**: LOW
**ROI**: 6.33

#### Step-by-Step

**BEFORE**: No validation
```python
url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    raise ValueError("Missing env vars")
```

**STEP 1**: Install pydantic-settings (5 min)
```bash
pip install pydantic-settings
```

**STEP 2**: Create config module (1h)
```python
# NEW: allobye_server_python/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import validator, Field
from typing import Literal

class Settings(BaseSettings):
    """Application configuration with validation."""

    # Supabase
    supabase_url: str = Field(..., description="Supabase project URL")
    supabase_anon_key: str = Field(..., description="Supabase anonymous key")
    supabase_service_role_key: str = Field(..., description="Supabase service role key")

    # Server
    environment: Literal["development", "staging", "production"] = "production"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    # Monitoring
    enable_metrics: bool = True
    enable_tracing: bool = True

    # Security
    jwt_secret: str = Field(..., min_length=32)

    @validator("supabase_url")
    def validate_supabase_url(cls, v):
        if not v.startswith("https://"):
            raise ValueError("Supabase URL must start with https://")
        if ".supabase.co" not in v:
            raise ValueError("Invalid Supabase URL format")
        return v

    @validator("jwt_secret")
    def validate_jwt_secret(cls, v):
        if len(v) < 32:
            raise ValueError("JWT secret must be at least 32 characters")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="forbid",  # Reject unknown env vars
    )

# Singleton instance
settings = Settings()
```

**STEP 3**: Update all usages (1h 30 min)
```python
# main.py
from config import settings

def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        from supabase import create_client
        _supabase_client = create_client(
            settings.supabase_url,  # ✅ Validated
            settings.supabase_service_role_key
        )
    return _supabase_client
```

**STEP 4**: Add .env.example (15 min)
```bash
# .env.example
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
ENVIRONMENT=development
LOG_LEVEL=INFO
ENABLE_METRICS=true
ENABLE_TRACING=true
JWT_SECRET=your-32-character-secret-here
```

**✓ Checklist**:
- [ ] Install pydantic-settings
- [ ] Create config.py with Settings class
- [ ] Add validators for critical configs
- [ ] Replace all os.getenv() calls
- [ ] Create .env.example
- [ ] Test startup with invalid configs

---

### Recipe #3: Fix N+1 Queries

**Time**: 4 heures
**Impact**: MEDIUM
**Effort**: LOW
**ROI**: 7.50

#### Step-by-Step

**BEFORE**: Loop with database calls
```python
# main.py lines 1051-1062
for child_id in payload.child_ids:  # ❌ N+1 query
    if not await verify_parent_owns_child(user.id, child_id):
        return error_response()
```

**STEP 1**: Create bulk verification function (1h)
```python
# auth.py
async def verify_parent_owns_children(
    parent_id: str,
    child_ids: List[str]
) -> Dict[str, bool]:
    """Verify parent ownership for multiple children at once.

    Returns:
        Dict mapping child_id to ownership status
    """
    supabase = get_supabase_admin()

    # ✅ Single query with IN clause
    response = supabase.table("parent_children") \
        .select("child_id") \
        .eq("parent_id", parent_id) \
        .in_("child_id", child_ids) \
        .execute()

    owned_child_ids = {row["child_id"] for row in response.data}

    return {
        child_id: child_id in owned_child_ids
        for child_id in child_ids
    }
```

**STEP 2**: Update handler to use bulk query (1h)
```python
# main.py
async def _handle_pickup_schedule_create(arguments):
    user = await get_current_user(arguments)
    payload = PickupScheduleInput.model_validate(arguments)

    # ✅ Single bulk query instead of N queries
    ownership = await verify_parent_owns_children(user.id, payload.child_ids)

    # Check all at once
    unauthorized_children = [
        child_id for child_id, owned in ownership.items()
        if not owned
    ]

    if unauthorized_children:
        return types.CallToolResult(
            content=[types.TextContent(
                type="text",
                text=f"Non autorisé pour les enfants: {', '.join(unauthorized_children)}"
            )],
            isError=True,
        )

    # Continue with business logic...
```

**STEP 3**: Fix school linking N+1 (1h)
```python
# auth.py signup_user
# BEFORE:
if role == "school_staff" and schools:
    for school_id in schools:  # ❌ N queries
        supabase.table("user_schools").insert({...}).execute()

# AFTER:
if role == "school_staff" and schools:
    # ✅ Bulk insert
    school_records = [
        {"user_id": user_id, "school_id": school_id}
        for school_id in schools
    ]
    supabase.table("user_schools").insert(school_records).execute()
```

**STEP 4**: Add database indexes (30 min)
```sql
-- schema.sql
-- Ensure indexes exist for bulk queries
CREATE INDEX IF NOT EXISTS idx_parent_children_parent_id
    ON parent_children(parent_id);
CREATE INDEX IF NOT EXISTS idx_parent_children_child_id
    ON parent_children(child_id);
CREATE INDEX IF NOT EXISTS idx_user_schools_user_id
    ON user_schools(user_id);
```

**STEP 5**: Add tests (30 min)
```python
# test_auth.py
async def test_verify_parent_owns_children_bulk():
    # Setup: Parent owns 2 children, not 1
    parent_id = "parent1"
    owned_ids = ["child1", "child2"]
    not_owned_id = "child3"

    result = await verify_parent_owns_children(
        parent_id,
        owned_ids + [not_owned_id]
    )

    assert result["child1"] == True
    assert result["child2"] == True
    assert result["child3"] == False
```

**✓ Checklist**:
- [ ] Create bulk verification function
- [ ] Update all N+1 loops
- [ ] Add bulk insert for school linking
- [ ] Add database indexes
- [ ] Add tests for bulk operations
- [ ] Verify performance improvement

---

## 2. Critical Wins Recipes

### Recipe #4: Refactor Long Method (signup_user)

**Time**: 8 heures
**Impact**: MEDIUM
**Effort**: MEDIUM
**ROI**: 4.25

#### Step-by-Step

**BEFORE**: 96-line monolithic function

**STEP 1**: Extract mock data (1h)
```python
# NEW: allobye_server_python/tests/fixtures/auth_fixtures.py
from datetime import datetime
from uuid import uuid4

def create_mock_signup_response(email: str, name: str, role: str, schools: list):
    """Create mock signup response for testing."""
    user_id = str(uuid4())
    return {
        "user": {
            "id": user_id,
            "email": email,
            "email_verified": False,
            "created_at": datetime.now().isoformat(),
        },
        "session": {
            "access_token": f"mock_token_{user_id}",
            "refresh_token": f"mock_refresh_{user_id}",
        },
        "profile": {
            "id": user_id,
            "email": email,
            "name": name or email.split("@")[0],
            "role": role,
            "schools": schools or [],
        },
    }
```

**STEP 2**: Create sub-functions (2h)
```python
# auth.py
async def _create_auth_user(email: str, password: str, name: str, role: str):
    """Create user in Supabase Auth."""
    supabase = get_supabase_client()

    response = supabase.auth.sign_up({
        "email": email,
        "password": password,
        "options": {
            "data": {
                "name": name,
                "role": role,
            }
        }
    })

    if not response.user:
        raise AuthenticationError("Failed to create user")

    return response


async def _create_user_profile(user_id: str, email: str, name: str, role: str):
    """Create user profile in database."""
    supabase = get_supabase_admin()

    profile_data = {
        "id": user_id,
        "email": email,
        "name": name or email.split("@")[0],
        "role": role,
        "created_at": datetime.now().isoformat(),
    }

    supabase.table("user_profiles").insert(profile_data).execute()
    return profile_data


async def _link_user_to_schools(user_id: str, schools: List[str]):
    """Link user to multiple schools."""
    if not schools:
        return

    supabase = get_supabase_admin()

    # Bulk insert
    school_records = [
        {"user_id": user_id, "school_id": school_id}
        for school_id in schools
    ]

    supabase.table("user_schools").insert(school_records).execute()


async def _format_signup_response(auth_response, profile_data):
    """Format signup response."""
    return {
        "user": {
            "id": auth_response.user.id,
            "email": auth_response.user.email,
            "email_verified": auth_response.user.email_confirmed_at is not None,
            "created_at": auth_response.user.created_at,
        },
        "session": {
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token,
        },
        "profile": profile_data,
    }
```

**STEP 3**: Refactor main function (2h)
```python
# auth.py
async def signup_user(
    email: str,
    password: str,
    name: Optional[str] = None,
    role: str = "parent",
    schools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Sign up a new user with email and password.

    This is now a high-level orchestration function.
    """
    supabase = get_supabase_client()
    if not supabase:
        # Use mock fixture
        from tests.fixtures.auth_fixtures import create_mock_signup_response
        return create_mock_signup_response(email, name, role, schools)

    try:
        # Step 1: Create auth user
        auth_response = await _create_auth_user(email, password, name, role)

        # Step 2: Create profile
        profile = await _create_user_profile(
            auth_response.user.id,
            email,
            name,
            role
        )

        # Step 3: Link to schools (if school staff)
        if role == "school_staff":
            await _link_user_to_schools(auth_response.user.id, schools)

        # Step 4: Format response
        return await _format_signup_response(auth_response, profile)

    except Exception as e:
        error_msg = str(e).lower()
        if "already registered" in error_msg or "duplicate" in error_msg:
            raise UserAlreadyExistsError(f"User {email} already exists")
        raise AuthenticationError(f"Signup failed: {str(e)}")
```

**STEP 4**: Add unit tests (2h)
```python
# test_auth.py
import pytest
from unittest.mock import Mock, patch

async def test_create_auth_user():
    """Test auth user creation."""
    with patch('auth.get_supabase_client') as mock_supabase:
        mock_supabase.return_value.auth.sign_up.return_value = Mock(
            user=Mock(id="user1", email="test@example.com")
        )

        response = await _create_auth_user(
            "test@example.com",
            "password123",
            "Test User",
            "parent"
        )

        assert response.user.id == "user1"


async def test_signup_user_orchestration():
    """Test full signup orchestration."""
    with patch('auth._create_auth_user') as mock_auth, \
         patch('auth._create_user_profile') as mock_profile, \
         patch('auth._link_user_to_schools') as mock_link:

        mock_auth.return_value = Mock(user=Mock(id="user1"))
        mock_profile.return_value = {"id": "user1", "email": "test@example.com"}

        result = await signup_user(
            "test@example.com",
            "password123",
            "Test User",
            "school_staff",
            ["school1", "school2"]
        )

        # Verify orchestration
        mock_auth.assert_called_once()
        mock_profile.assert_called_once()
        mock_link.assert_called_once_with("user1", ["school1", "school2"])
```

**STEP 5**: Update documentation (1h)
```python
# auth.py
async def signup_user(
    email: str,
    password: str,
    name: Optional[str] = None,
    role: str = "parent",
    schools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Sign up a new user with email and password.

    Orchestrates the complete signup flow:
    1. Create user in Supabase Auth
    2. Create user profile in database
    3. Link user to schools (if school_staff role)
    4. Format and return response

    Args:
        email: User's email address (must be unique)
        password: User's password (min 6 characters)
        name: User's full name (optional, defaults to email prefix)
        role: User role ('parent' or 'school_staff')
        schools: List of school IDs (required for school_staff)

    Returns:
        Dict containing:
        - user: User auth info (id, email, email_verified, created_at)
        - session: Auth session (access_token, refresh_token)
        - profile: User profile (id, email, name, role, schools)

    Raises:
        UserAlreadyExistsError: If user with this email already exists
        AuthenticationError: On other signup errors

    Examples:
        >>> # Parent signup
        >>> result = await signup_user("parent@example.com", "pass123", "Jane Doe")

        >>> # School staff signup
        >>> result = await signup_user(
        ...     "staff@example.com",
        ...     "pass123",
        ...     "John Smith",
        ...     role="school_staff",
        ...     schools=["school1", "school2"]
        ... )
    """
    ...
```

**✓ Checklist**:
- [ ] Extract mock data to fixtures
- [ ] Create _create_auth_user
- [ ] Create _create_user_profile
- [ ] Create _link_user_to_schools
- [ ] Create _format_signup_response
- [ ] Refactor signup_user to orchestration
- [ ] Add unit tests for each sub-function
- [ ] Add integration test for full flow
- [ ] Update docstrings

---

### Recipe #5: Extract Handler Pattern (Decorators)

**Time**: 12 heures
**Impact**: MEDIUM
**Effort**: MEDIUM
**ROI**: 2.67

#### Step-by-Step

**BEFORE**: Pattern repeated 10 times

**STEP 1**: Create decorator module (2h)
```python
# NEW: allobye_server_python/decorators.py
from functools import wraps
from typing import Callable, Optional
import mcp.types as types
from pydantic import BaseModel, ValidationError

from auth import get_current_user, require_auth, UserProfile


def validate_input(model_class: type[BaseModel]):
    """Decorator to validate MCP tool input."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(arguments: dict, *args, **kwargs):
            try:
                # Validate input
                payload = model_class.model_validate(arguments)

                # Call handler with validated payload
                return await func(payload, *args, **kwargs)

            except ValidationError as exc:
                return types.CallToolResult(
                    content=[types.TextContent(
                        type="text",
                        text=f"Erreur de validation: {exc.errors()}"
                    )],
                    isError=True,
                )
        return wrapper
    return decorator


def require_role(role: Optional[str] = None):
    """Decorator to require authentication and role."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(arguments: dict, *args, **kwargs):
            # Extract and validate user
            user = await get_current_user(arguments)

            if not require_auth(user, role=role):
                role_msg = f" en tant que {role}" if role else ""
                return types.CallToolResult(
                    content=[types.TextContent(
                        type="text",
                        text=f"Authentification requise{role_msg}."
                    )],
                    isError=True,
                )

            # Call handler with authenticated user
            return await func(user, *args, **kwargs)

        return wrapper
    return decorator


def success_response(message_template: str):
    """Decorator to format success responses."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Call handler
            result = await func(*args, **kwargs)

            # Format response
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=message_template.format(**result.get("vars", {}))
                )],
                structuredContent=result.get("data"),
                _meta=result.get("meta"),
            )
        return wrapper
    return decorator
```

**STEP 2**: Create base handler class (2h)
```python
# NEW: allobye_server_python/handlers/base.py
from abc import ABC, abstractmethod
from typing import Any, Dict
import mcp.types as types

class BaseHandler(ABC):
    """Base class for MCP tool handlers."""

    @abstractmethod
    async def handle(self, *args, **kwargs) -> Dict[str, Any]:
        """Handle the tool request.

        Returns:
            Dict with keys:
            - vars: Variables for message template
            - data: Structured content
            - meta: Metadata
        """
        pass

    def error_response(self, message: str) -> types.CallToolResult:
        """Create error response."""
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=message)],
            isError=True,
        )
```

**STEP 3**: Refactor one handler as example (2h)
```python
# NEW: allobye_server_python/handlers/pickup_handlers.py
from decorators import validate_input, require_role, success_response
from handlers.base import BaseHandler
from models import PickupScheduleInput

class PickupScheduleHandler(BaseHandler):
    """Handler for pickup schedule creation."""

    @validate_input(PickupScheduleInput)  # ✅ Auto validation
    @require_role("parent")  # ✅ Auto auth check
    @success_response("✓ Ramassage confirmé pour {child_count} enfant(s) à {time}")
    async def handle(
        self,
        user: UserProfile,  # ✅ Injected by decorator
        payload: PickupScheduleInput  # ✅ Validated by decorator
    ) -> Dict[str, Any]:
        """Handle pickup scheduling."""

        # ✅ Just business logic, no boilerplate!

        # Verify ownership
        ownership = await verify_parent_owns_children(
            user.id,
            payload.child_ids
        )

        unauthorized = [
            child_id for child_id, owned in ownership.items()
            if not owned
        ]

        if unauthorized:
            return self.error_response(
                f"Non autorisé pour: {', '.join(unauthorized)}"
            )

        # Get schools
        schools = await get_schools_for_children(payload.child_ids)

        # Create pickup
        if len(schools) > 1:
            results = await coordinate_cross_school_pickup(...)
        else:
            results = await create_pickup_request(...)

        # Format time
        try:
            scheduled_dt = datetime.fromisoformat(payload.scheduled_time)
            time_str = scheduled_dt.strftime("%H:%M")
        except:
            time_str = payload.scheduled_time

        # Return data for decorator to format
        return {
            "vars": {
                "child_count": len(payload.child_ids),
                "time": time_str,
            },
            "data": {
                "pickup_id": results["id"],
                "children": payload.child_ids,
                "status": "confirmed",
                "scheduled_time": payload.scheduled_time,
            },
            "meta": {
                "full_results": results,
                "schools_affected": [s["name"] for s in schools],
                "display_update": True,
            },
        }


# Register handler
pickup_schedule_handler = PickupScheduleHandler()

# Use in main.py
async def _handle_pickup_schedule_create(arguments: dict):
    """MCP tool handler for pickup scheduling."""
    return await pickup_schedule_handler.handle(arguments)
```

**STEP 4**: Refactor remaining 9 handlers (4h)
```python
# handlers/auth_handlers.py
class SignupHandler(BaseHandler):
    @validate_input(SignupInput)
    @success_response("Compte créé avec succès pour {email}")
    async def handle(self, payload: SignupInput):
        result = await signup_user(...)
        return {"vars": {"email": payload.email}, "data": result}


class LoginHandler(BaseHandler):
    @validate_input(LoginInput)
    @success_response("Connexion réussie")
    async def handle(self, payload: LoginInput):
        result = await login_user(payload.email, payload.password)
        return {"data": result}


# ... 7 more handlers
```

**STEP 5**: Add tests (2h)
```python
# test_decorators.py
import pytest
from decorators import validate_input, require_role

class TestInput(BaseModel):
    name: str
    age: int


@validate_input(TestInput)
async def test_handler(payload: TestInput):
    return {"name": payload.name}


async def test_validate_input_decorator():
    """Test input validation decorator."""
    # Valid input
    result = await test_handler({"name": "John", "age": 30})
    assert result["name"] == "John"

    # Invalid input
    result = await test_handler({"name": "John"})  # Missing age
    assert result.isError == True
```

**✓ Checklist**:
- [ ] Create decorators module
- [ ] Create BaseHandler class
- [ ] Refactor 1 handler as example
- [ ] Refactor remaining 9 handlers
- [ ] Add tests for decorators
- [ ] Add tests for each handler
- [ ] Update main.py to use handlers
- [ ] Remove duplicate code

---

### Recipe #6: Extract Custom React Hooks (useRealtimePickups)

**Time**: 12 heures
**Impact**: HIGH
**Effort**: MEDIUM
**ROI**: 3.25

#### Step-by-Step

**BEFORE**: 87-line useEffect

**STEP 1**: Create hooks directory (5 min)
```bash
mkdir -p src/hooks
touch src/hooks/useRealtimePickups.ts
touch src/hooks/useRealtimeEmergencies.ts
touch src/hooks/useSupabaseClient.ts
```

**STEP 2**: Extract Supabase client hook (1h)
```typescript
// src/hooks/useSupabaseClient.ts
import { createClient, SupabaseClient } from '@supabase/supabase-js';
import { useMemo } from 'react';

export function useSupabaseClient(): SupabaseClient | null {
  const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
  const supabaseKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

  const client = useMemo(() => {
    if (!supabaseUrl || !supabaseKey) {
      console.warn('Supabase credentials not configured');
      return null;
    }

    return createClient(supabaseUrl, supabaseKey);
  }, [supabaseUrl, supabaseKey]);

  return client;
}
```

**STEP 3**: Extract pickups realtime hook (3h)
```typescript
// src/hooks/useRealtimePickups.ts
import { useEffect, useState } from 'react';
import { useSupabaseClient } from './useSupabaseClient';

interface Pickup {
  id: string;
  scheduled_time: string;
  status: string;
  // ... other fields
}

interface UseRealtimePickupsOptions {
  schoolId: string | null;
  enabled?: boolean;
}

export function useRealtimePickups({
  schoolId,
  enabled = true,
}: UseRealtimePickupsOptions) {
  const [pickups, setPickups] = useState<Pickup[]>([]);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const supabase = useSupabaseClient();

  useEffect(() => {
    if (!supabase || !schoolId || !enabled) {
      return;
    }

    console.log(`Subscribing to pickups for school: ${schoolId}`);

    const channel = supabase
      .channel(`pickups-${schoolId}`)
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'pickups',
          filter: `school_id=eq.${schoolId}`,
        },
        (payload) => {
          console.log('Pickup change received:', payload);

          if (payload.eventType === 'INSERT' || payload.eventType === 'UPDATE') {
            setPickups((prev) => {
              // Remove old version if exists
              const filtered = prev.filter((p) => p.id !== payload.new.id);

              // Add new version and sort
              return [...filtered, payload.new as Pickup].sort(
                (a, b) => new Date(a.scheduled_time).getTime() - new Date(b.scheduled_time).getTime()
              );
            });
          } else if (payload.eventType === 'DELETE') {
            setPickups((prev) => prev.filter((p) => p.id !== payload.old.id));
          }
        }
      )
      .subscribe((status) => {
        console.log('Pickups subscription status:', status);
        setIsConnected(status === 'SUBSCRIBED');
      });

    return () => {
      console.log(`Unsubscribing from pickups for school: ${schoolId}`);
      channel.unsubscribe();
    };
  }, [supabase, schoolId, enabled]);

  return {
    pickups,
    error,
    isConnected,
  };
}
```

**STEP 4**: Extract emergencies hook (2h)
```typescript
// src/hooks/useRealtimeEmergencies.ts
import { useEffect, useState } from 'react';
import { useSupabaseClient } from './useSupabaseClient';
import { TIMEOUTS } from '../constants/timeouts';

interface Emergency {
  id: string;
  emergency_type: string;
  context: string;
  child_id: string;
  created_at: string;
}

export function useRealtimeEmergencies() {
  const [currentEmergency, setCurrentEmergency] = useState<Emergency | null>(null);
  const supabase = useSupabaseClient();

  useEffect(() => {
    if (!supabase) return;

    const channel = supabase
      .channel('emergencies-all')
      .on(
        'postgres_changes',
        {
          event: 'INSERT',
          schema: 'public',
          table: 'emergencies',
        },
        (payload) => {
          console.log('Emergency received:', payload);
          setCurrentEmergency(payload.new as Emergency);

          // Auto-clear after timeout
          setTimeout(() => {
            setCurrentEmergency(null);
          }, TIMEOUTS.ALERT_DURATION_MS);
        }
      )
      .subscribe();

    return () => {
      channel.unsubscribe();
    };
  }, [supabase]);

  const clearEmergency = () => {
    setCurrentEmergency(null);
  };

  return {
    currentEmergency,
    clearEmergency,
  };
}
```

**STEP 5**: Update Dashboard component (2h)
```typescript
// src/allobye-dashboard/dashboard.jsx
import { useRealtimePickups } from '../hooks/useRealtimePickups';
import { useRealtimeEmergencies } from '../hooks/useRealtimeEmergencies';

export default function Dashboard() {
  const toolOutput = useOpenAiGlobal("toolOutput");
  const metadata = useOpenAiGlobal("toolResponseMetadata");

  const [state, setState] = useWidgetState({
    view: "timeline",
    filter: "all",
  });

  const schoolInfo = metadata?.school_info || {
    name: "École AllôBye",
    id: "school_1",
  };

  // ✅ Clean hook usage!
  const {
    pickups: realtimePickups,
    isConnected
  } = useRealtimePickups({
    schoolId: schoolInfo?.id,
    enabled: true,
  });

  const {
    currentEmergency,
    clearEmergency
  } = useRealtimeEmergencies();

  const pickups = metadata?.pickups || realtimePickups || [];

  // Rest of component...
  return (
    <div className="allobye-dashboard fullscreen">
      {/* ... */}
      {currentEmergency && (
        <EmergencyAlert
          alert={currentEmergency}
          onClose={clearEmergency}
        />
      )}
      {/* ... */}
      <div className="status-indicator">
        <span className={`status-dot ${isConnected ? 'online' : 'offline'}`}></span>
        {isConnected ? 'Connecté' : 'Déconnecté'}
      </div>
    </div>
  );
}
```

**STEP 6**: Add tests (2h)
```typescript
// src/hooks/__tests__/useRealtimePickups.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { useRealtimePickups } from '../useRealtimePickups';

// Mock Supabase
jest.mock('../useSupabaseClient', () => ({
  useSupabaseClient: () => mockSupabaseClient,
}));

test('subscribes to pickups channel', async () => {
  const { result } = renderHook(() =>
    useRealtimePickups({ schoolId: 'school1' })
  );

  await waitFor(() => {
    expect(result.current.isConnected).toBe(true);
  });
});

test('updates pickups on INSERT event', async () => {
  const { result } = renderHook(() =>
    useRealtimePickups({ schoolId: 'school1' })
  );

  // Simulate INSERT event
  mockSupabaseClient.simulateEvent('INSERT', {
    new: { id: 'pickup1', scheduled_time: '2025-11-04T15:00:00' },
  });

  await waitFor(() => {
    expect(result.current.pickups).toHaveLength(1);
    expect(result.current.pickups[0].id).toBe('pickup1');
  });
});
```

**STEP 7**: Add hook documentation (1h)
```typescript
/**
 * Hook to subscribe to real-time pickup updates for a school.
 *
 * Automatically subscribes to Supabase Realtime channel when schoolId is provided
 * and cleans up subscription on unmount.
 *
 * @param options - Configuration options
 * @param options.schoolId - ID of school to subscribe to
 * @param options.enabled - Whether to enable subscription (default: true)
 *
 * @returns Object containing:
 * - pickups: Array of pickup objects, sorted by scheduled_time
 * - error: Any error that occurred during subscription
 * - isConnected: Whether the subscription is active
 *
 * @example
 * ```tsx
 * function Dashboard() {
 *   const { pickups, isConnected } = useRealtimePickups({
 *     schoolId: 'school_123',
 *   });
 *
 *   return (
 *     <div>
 *       <ConnectionStatus connected={isConnected} />
 *       <PickupList pickups={pickups} />
 *     </div>
 *   );
 * }
 * ```
 */
export function useRealtimePickups({ ... }) { ... }
```

**✓ Checklist**:
- [ ] Create hooks directory
- [ ] Extract useSupabaseClient
- [ ] Extract useRealtimePickups
- [ ] Extract useRealtimeEmergencies
- [ ] Update Dashboard to use hooks
- [ ] Add tests for each hook
- [ ] Add JSDoc documentation
- [ ] Remove old useEffect code

---

## 3. Strategic Refactoring Recipes

### Recipe #7: Decompose God Object (main.py)

**Time**: 40 heures
**Impact**: HIGH
**Effort**: HIGH
**ROI**: 1.18

#### Phase 1: Planning (4h)

**STEP 1**: Map current structure
```
main.py (1583 lignes)
├── Imports & Config (1-68)
├── Supabase Client (73-93)
├── Data Models (101-199)
├── Widget Config (287-343)
├── Middleware (351-392)
├── Database Helpers (399-689)
├── MCP Server Setup (696-700)
├── Tool Definitions (742-836)
├── Tool Handlers (844-1384)
├── Request Handling (1392-1449)
└── HTTP Endpoints (1544-1583)
```

**STEP 2**: Design new structure
```
allobye_server_python/
├── main.py                    # MCP server setup ONLY (< 100 lines)
├── config.py                  # Settings & env validation
├── constants.py               # Enums & constants
│
├── models/
│   ├── __init__.py
│   ├── pickup.py             # Pickup data models
│   ├── delegate.py           # Delegate models
│   └── emergency.py          # Emergency models
│
├── database/
│   ├── __init__.py
│   ├── client.py             # DatabaseClient abstraction
│   ├── supabase_client.py    # Supabase implementation
│   └── factory.py            # Database factory
│
├── repositories/
│   ├── __init__.py
│   ├── pickup_repository.py
│   ├── school_repository.py
│   ├── child_repository.py
│   └── delegate_repository.py
│
├── services/
│   ├── __init__.py
│   ├── auth.py              # Already exists
│   ├── monitoring.py        # Already exists
│   ├── pickup_service.py    # NEW: Pickup business logic
│   └── school_service.py    # NEW: School logic
│
├── handlers/
│   ├── __init__.py
│   ├── base.py              # BaseHandler class
│   ├── auth_handlers.py     # 5 auth handlers
│   ├── pickup_handlers.py   # 4 pickup handlers
│   └── monitoring_handlers.py # 1 monitoring handler
│
├── middleware/
│   ├── __init__.py
│   └── auth_middleware.py   # Auth middleware
│
├── widgets/
│   ├── __init__.py
│   └── widget_manager.py    # Widget configuration
│
└── decorators.py            # Handler decorators
```

#### Phase 2: Extract Low-Risk Modules (8h)

**STEP 1**: Extract constants (1h)
```python
# NEW: constants.py
from enum import Enum

class TimeWindow(str, Enum):
    CURRENT = "current"
    TODAY = "today"
    CUSTOM = "custom"

class PickupStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    LATE = "late"

# Move from main.py
```

**STEP 2**: Extract models (2h)
```python
# NEW: models/pickup.py
from pydantic import BaseModel, Field
from typing import List, Optional
from constants import PickupStatus

class PickupScheduleInput(BaseModel):
    child_ids: List[str] = Field(..., alias="childIds")
    pickup_person_id: str = Field(..., alias="pickupPersonId")
    scheduled_time: str = Field(..., alias="scheduledTime")
    notes: Optional[str] = None

# Move from main.py lines 101-126
```

**STEP 3**: Extract widget config (1h)
```python
# NEW: widgets/widget_manager.py
from pathlib import Path
from functools import lru_cache

class WidgetManager:
    def __init__(self, assets_dir: Path):
        self.assets_dir = assets_dir
        self._cache = {}

    @lru_cache(maxsize=None)
    def load_widget_html(self, component_name: str) -> str:
        html_path = self.assets_dir / f"{component_name}.html"
        if html_path.exists():
            return html_path.read_text(encoding="utf8")
        return ""

    def create_school_dashboard_widget(self):
        return AllobyeWidget(
            identifier="school-dashboard",
            title="Tableau de bord école - AllôBye",
            template_uri="ui://widget/allobye-dashboard.html",
            html=self.load_widget_html("allobye-dashboard"),
        )

# Usage in main.py
widget_manager = WidgetManager(ASSETS_DIR)
SCHOOL_DASHBOARD_WIDGET = widget_manager.create_school_dashboard_widget()
```

**STEP 4**: Test extraction (2h)
- Import extracted modules in main.py
- Run all tests
- Fix import errors
- Commit

**STEP 5**: Extract middleware (2h)
```python
# NEW: middleware/auth_middleware.py
from typing import Optional, Dict, Any
from auth import validate_session, UserProfile

async def get_current_user(arguments: Dict[str, Any]) -> Optional[UserProfile]:
    """Extract and validate user from request."""
    access_token = arguments.get("access_token") or arguments.get("accessToken")
    if not access_token:
        return None

    user = await validate_session(access_token)
    return user

def require_auth(user: Optional[UserProfile], role: Optional[str] = None) -> bool:
    """Check authentication and role."""
    if user is None:
        return False
    if role and user.role != role:
        return False
    return True

# Move from main.py lines 351-392
```

#### Phase 3: Create Repository Layer (12h)

**STEP 1**: Create database abstraction (3h)
```python
# NEW: database/client.py
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

class DatabaseClient(ABC):
    """Abstract database client interface."""

    @abstractmethod
    async def query(self, table: str, filters: Dict) -> List[Dict]:
        """Query table with filters."""
        pass

    @abstractmethod
    async def insert(self, table: str, data: Dict) -> Dict:
        """Insert record."""
        pass

    @abstractmethod
    async def update(self, table: str, id: str, data: Dict) -> Dict:
        """Update record."""
        pass

    @abstractmethod
    async def delete(self, table: str, id: str) -> bool:
        """Delete record."""
        pass
```

**STEP 2**: Implement Supabase client (3h)
```python
# NEW: database/supabase_client.py
from database.client import DatabaseClient

class SupabaseClient(DatabaseClient):
    """Supabase implementation of DatabaseClient."""

    def __init__(self, url: str, key: str):
        from supabase import create_client
        self._client = create_client(url, key)

    async def query(self, table: str, filters: Dict) -> List[Dict]:
        response = self._client.table(table).select("*")
        for key, value in filters.items():
            response = response.eq(key, value)
        return response.execute().data

    # ... implement other methods
```

**STEP 3**: Create repositories (6h)
```python
# NEW: repositories/pickup_repository.py
from database.client import DatabaseClient
from typing import List, Optional
from datetime import datetime

class PickupRepository:
    def __init__(self, db_client: DatabaseClient):
        self.db = db_client

    async def get_by_id(self, pickup_id: str) -> Optional[Dict]:
        results = await self.db.query("pickups", {"id": pickup_id})
        return results[0] if results else None

    async def get_school_pickups(
        self,
        school_id: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[Dict]:
        return await self.db.query(
            "pickups",
            {
                "school_id": school_id,
                "scheduled_time__gte": start_time.isoformat(),
                "scheduled_time__lte": end_time.isoformat(),
            }
        )

    async def create(self, pickup_data: Dict) -> Dict:
        return await self.db.insert("pickups", pickup_data)
```

#### Phase 4: Extract Services (8h)

**STEP 1**: Create pickup service (4h)
```python
# NEW: services/pickup_service.py
from repositories.pickup_repository import PickupRepository
from repositories.school_repository import SchoolRepository

class PickupService:
    def __init__(
        self,
        pickup_repo: PickupRepository,
        school_repo: SchoolRepository
    ):
        self.pickup_repo = pickup_repo
        self.school_repo = school_repo

    async def schedule_pickup(
        self,
        child_ids: List[str],
        pickup_person_id: str,
        scheduled_time: str,
        notes: Optional[str] = None
    ) -> Dict:
        """Schedule a pickup for one or more children."""

        # Get schools for children
        schools = await self.school_repo.get_schools_for_children(child_ids)

        # Coordinate pickup (multi-school if needed)
        if len(schools) > 1:
            return await self._coordinate_cross_school_pickup(...)
        else:
            return await self._create_single_school_pickup(...)

    # Move business logic from main.py database helpers
```

**STEP 2**: Create school service (2h)
```python
# NEW: services/school_service.py
from repositories.school_repository import SchoolRepository

class SchoolService:
    def __init__(self, school_repo: SchoolRepository):
        self.school_repo = school_repo

    async def get_dashboard_data(
        self,
        school_id: str,
        time_window: str
    ) -> Dict:
        """Get school dashboard data."""
        # Move logic from get_school_pickups
```

**STEP 3**: Test services (2h)

#### Phase 5: Extract Handlers (8h)

(Already covered in Recipe #5)

**✓ Checklist**:
- [ ] Phase 1: Planning (4h)
- [ ] Phase 2: Extract low-risk modules (8h)
- [ ] Phase 3: Create repository layer (12h)
- [ ] Phase 4: Extract services (8h)
- [ ] Phase 5: Extract handlers (8h covered in Recipe #5)
- [ ] Phase 6: Update main.py to orchestrate (Already small)
- [ ] Phase 7: Comprehensive testing (8h)

---

## 4. Testing Strategy

### Testing Pyramid for AllôBye

```
              /\
             /  \
            / E2E\         (5% - 10 tests)
           /      \
          /--------\
         /          \
        /Integration\     (15% - 30 tests)
       /            \
      /--------------\
     /                \
    /  Unit Tests      \   (80% - 150+ tests)
   /                    \
  /______________________\
```

### Unit Test Examples

```python
# test_pickup_service.py
import pytest
from unittest.mock import Mock
from services.pickup_service import PickupService

@pytest.fixture
def mock_pickup_repo():
    return Mock()

@pytest.fixture
def mock_school_repo():
    return Mock()

@pytest.fixture
def pickup_service(mock_pickup_repo, mock_school_repo):
    return PickupService(mock_pickup_repo, mock_school_repo)

async def test_schedule_pickup_single_school(pickup_service, mock_school_repo):
    """Test scheduling pickup for single school."""
    mock_school_repo.get_schools_for_children.return_value = [
        {"id": "school1", "name": "School A"}
    ]

    result = await pickup_service.schedule_pickup(
        child_ids=["child1", "child2"],
        pickup_person_id="person1",
        scheduled_time="2025-11-04T15:00:00",
        notes="Test pickup"
    )

    assert result["status"] == "confirmed"
    mock_school_repo.get_schools_for_children.assert_called_once()
```

### Integration Test Examples

```python
# test_pickup_flow_integration.py
import pytest
from database.supabase_client import SupabaseClient
from repositories.pickup_repository import PickupRepository
from services.pickup_service import PickupService

@pytest.fixture
async def integration_setup():
    """Setup real database connection for integration tests."""
    db_client = SupabaseClient(
        url=os.getenv("TEST_SUPABASE_URL"),
        key=os.getenv("TEST_SUPABASE_KEY")
    )
    pickup_repo = PickupRepository(db_client)
    school_repo = SchoolRepository(db_client)
    pickup_service = PickupService(pickup_repo, school_repo)

    yield pickup_service

    # Cleanup
    await cleanup_test_data()

async def test_full_pickup_flow(integration_setup):
    """Test complete pickup scheduling flow with real database."""
    service = integration_setup

    result = await service.schedule_pickup(...)

    # Verify in database
    pickup = await service.pickup_repo.get_by_id(result["id"])
    assert pickup["status"] == "confirmed"
```

---

## Conclusion

Ces recettes fournissent des guides étape par étape pour corriger chaque anti-pattern. Chaque recette inclut:
- Estimation de temps
- ROI
- Code BEFORE/AFTER
- Steps détaillés
- Checklist de validation
- Tests

**Prochaines étapes**:
1. Commencer par Quick Wins (Recipe #1-3)
2. Puis Critical Wins (Recipe #4-6)
3. Planifier Strategic (Recipe #7)

**Total Effort Estimé**: 86 heures (2.5 sprints)
**Expected Improvement**: -65% Tech Debt Score

---

**Généré le**: 2025-11-04
**Par**: Refactoring Recipe Agent
**Prochaine mise à jour**: Après chaque sprint
