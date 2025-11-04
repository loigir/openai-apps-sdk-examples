# Type Safety Recommendations - AllôBye

**Date**: 2025-11-04
**Analyzer**: Validateur de Types
**Purpose**: Actionable recommendations to achieve 90%+ type coverage

---

## Executive Summary

This document provides **concrete, prioritized recommendations** to improve AllôBye's type safety from the current **67.5% coverage** to the target **90%+ coverage**. All recommendations include code examples, implementation estimates, and risk mitigation strategies.

**Implementation Roadmap**:
- **Phase 1 (Critical)**: 5-7 days → Achieve 85% coverage
- **Phase 2 (High Priority)**: 3-4 days → Achieve 90% coverage
- **Phase 3 (Enhancement)**: 2-3 days → Achieve 95% coverage

**Total Estimated Effort**: 10-14 days for full implementation

---

## Table of Contents

1. [Phase 1: Critical Improvements (P0)](#phase-1-critical-improvements-p0)
2. [Phase 2: High Priority (P1)](#phase-2-high-priority-p1)
3. [Phase 3: Enhancements (P2)](#phase-3-enhancements-p2)
4. [Implementation Guide](#implementation-guide)
5. [Migration Strategies](#migration-strategies)
6. [Testing Strategy](#testing-strategy)
7. [Monitoring & Validation](#monitoring--validation)

---

## Phase 1: Critical Improvements (P0)

**Timeline**: 5-7 days
**Goal**: Fix critical type safety gaps that pose production risks

---

### 1.1 Convert React Components to TypeScript

**Priority**: 🔴 CRITICAL
**Effort**: 2 days
**Risk**: High (frontend type safety completely missing)

#### Current State
```javascript
// src/allobye-dashboard/pickup-card.jsx
export default function PickupCard({ pickup, currentTime }) {
  // No type validation
  const scheduledTime = new Date(pickup.scheduled_time);  // Could fail
  const minutesUntilPickup = Math.floor((scheduledTime - currentTime) / 1000 / 60);
}
```

#### Recommended Implementation

**Step 1: Define Type Interfaces**

Create `/home/user/openai-apps-sdk-examples/src/allobye-dashboard/types.ts`:
```typescript
// === Core Data Types ===

export type UUID = string;  // UUID format string

export type PickupStatus =
  | 'pending'
  | 'confirmed'
  | 'in_progress'
  | 'completed'
  | 'cancelled'
  | 'late';

export type EmergencyType =
  | 'late'
  | 'illness'
  | 'cancel'
  | 'injury'
  | 'other';

export type UserRole =
  | 'parent'
  | 'school_staff';

// === Data Models ===

export interface ChildData {
  id: UUID;
  name: string;
  grade?: string;
  school_id: UUID;
  parent_email: string;
}

export interface DelegateData {
  id: UUID;
  email: string;
  name?: string;
  phone?: string;
  permissions: string[];
}

export interface PickupData {
  id: UUID;
  scheduled_time: string;  // ISO 8601
  actual_time?: string;
  status: PickupStatus;
  notes?: string;
  eta_minutes?: number;
  delay_minutes?: number;
  child?: ChildData;
  pickup_person?: DelegateData;
}

export interface SchoolInfo {
  id: UUID;
  name: string;
  address?: string;
  phone?: string;
  email?: string;
}

export interface EmergencyAlert {
  type: EmergencyType;
  context: string;
  child_id: UUID;
  severity?: 'low' | 'medium' | 'high' | 'critical';
}

// === Component Props ===

export interface PickupCardProps {
  pickup: PickupData;
  currentTime: Date;
}

export interface DashboardProps {
  // Props from useOpenAiGlobal and useWidgetState
}

export interface EmergencyAlertProps {
  alert: EmergencyAlert;
  onClose: () => void;
}

// === Supabase Realtime Payloads ===

export type RealtimeEventType = 'INSERT' | 'UPDATE' | 'DELETE';

export interface RealtimePayload<T> {
  eventType: RealtimeEventType;
  new: T;
  old: T;
  schema: string;
  table: string;
}
```

**Step 2: Rename and Migrate Components**

```bash
# Rename files
cd /home/user/openai-apps-sdk-examples/src/allobye-dashboard
mv pickup-card.jsx pickup-card.tsx
mv dashboard.jsx dashboard.tsx
mv emergency-alert.jsx emergency-alert.tsx
mv auth-screen.jsx auth-screen.tsx
mv index.jsx index.tsx
```

**Step 3: Add Types to Components**

```typescript
// src/allobye-dashboard/pickup-card.tsx
import { PickupCardProps } from "./types";
import "./pickup-card.css";

export default function PickupCard({ pickup, currentTime }: PickupCardProps) {
  const scheduledTime = new Date(pickup.scheduled_time);
  const minutesUntilPickup = Math.floor((scheduledTime.getTime() - currentTime.getTime()) / 1000 / 60);

  const getStatusColor = (): string => {
    if (pickup.status === "completed") return "green";
    if (pickup.status === "cancelled") return "gray";
    if (pickup.delay_minutes && pickup.delay_minutes > 0) return "orange";
    if (minutesUntilPickup < 5) return "red";
    if (minutesUntilPickup < 15) return "yellow";
    return "blue";
  };

  const formatTime = (date: Date): string => {
    return date.toLocaleTimeString("fr-CA", {
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const getTimeLabel = (): string => {
    if (minutesUntilPickup < 0) return "En retard";
    if (minutesUntilPickup === 0) return "Maintenant";
    if (minutesUntilPickup < 60) return `Dans ${minutesUntilPickup} min`;
    const hours = Math.floor(minutesUntilPickup / 60);
    const mins = minutesUntilPickup % 60;
    return `Dans ${hours}h${mins > 0 ? mins.toString().padStart(2, "0") : ""}`;
  };

  return (
    <div className={`pickup-card status-${getStatusColor()}`}>
      <div className="pickup-time-badge">
        <div className="scheduled-time">{formatTime(scheduledTime)}</div>
        <div className="time-until">{getTimeLabel()}</div>
      </div>

      <div className="pickup-details">
        <div className="child-info">
          <div className="child-name">{pickup.child?.name ?? "Enfant inconnu"}</div>
          {pickup.child?.grade && <div className="child-grade">{pickup.child.grade}</div>}
        </div>

        <div className="pickup-person-info">
          <div className="person-icon">👤</div>
          <div className="person-name">{pickup.pickup_person?.name ?? "Personne inconnue"}</div>
        </div>

        {pickup.eta_minutes !== undefined && (
          <div className="eta-info">
            <span className="eta-icon">🚗</span>
            <span className="eta-time">ETA: {pickup.eta_minutes} min</span>
            {pickup.delay_minutes && pickup.delay_minutes > 0 && (
              <span className="delay-badge">+{pickup.delay_minutes} min</span>
            )}
          </div>
        )}

        {pickup.notes && (
          <div className="pickup-notes">
            <span className="notes-icon">📝</span>
            {pickup.notes}
          </div>
        )}
      </div>

      <div className="pickup-status">
        <span className={`status-badge ${pickup.status}`}>
          {pickup.status === "pending" && "En attente"}
          {pickup.status === "in_progress" && "En cours"}
          {pickup.status === "completed" && "Complété"}
          {pickup.status === "cancelled" && "Annulé"}
        </span>
      </div>
    </div>
  );
}
```

**Step 4: Update vite.config.ts**

Ensure TypeScript processing:
```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  esbuild: {
    loader: "tsx",  // ✅ Process .tsx files
    include: /src\/.*\.[tj]sx?$/,
  },
});
```

**Benefits**:
- ✅ Compile-time error detection
- ✅ Autocomplete in IDE
- ✅ Prevents runtime crashes from undefined properties
- ✅ Documents component contracts

---

### 1.2 Add Pydantic Output Models

**Priority**: 🔴 CRITICAL
**Effort**: 2 days
**Risk**: High (no response validation)

#### Current State
```python
# main.py:900-917
return types.CallToolResult(
    structuredContent={  # ❌ No validation
        "user_id": result["user"]["id"],
        "email": result["user"]["email"],
        "role": result["profile"]["role"],
        "access_token": result["session"]["access_token"],
    },
)
```

#### Recommended Implementation

Create `/home/user/openai-apps-sdk-examples/allobye_server_python/schemas.py`:
```python
"""Pydantic schemas for MCP tool inputs and outputs."""

from datetime import datetime
from typing import List, Literal, Optional
from uuid import UUID
from pydantic import BaseModel, Field, EmailStr, ConfigDict

# ═══════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════

PickupStatus = Literal["pending", "confirmed", "in_progress", "completed", "cancelled", "late"]
EmergencyType = Literal["late", "illness", "cancel", "injury", "other"]
UserRole = Literal["parent", "school_staff", "service_role"]
SyncStatus = Literal["success", "partial", "failed"]

# ═══════════════════════════════════════════════════════════════
# OUTPUT SCHEMAS
# ═══════════════════════════════════════════════════════════════

class AuthSignupOutput(BaseModel):
    """Output schema for auth-signup tool."""
    user_id: UUID
    email: EmailStr
    email_verified: bool

    model_config = ConfigDict(from_attributes=True)


class AuthLoginOutput(BaseModel):
    """Output schema for auth-login tool."""
    user_id: UUID
    email: EmailStr
    role: UserRole
    access_token: str

    model_config = ConfigDict(from_attributes=True)


class AuthProfileOutput(BaseModel):
    """Output schema for auth-profile tool."""
    id: UUID
    email: EmailStr
    name: Optional[str] = None
    role: UserRole
    schools: List[UUID]
    children: List[UUID]
    email_verified: bool
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class PickupScheduleOutput(BaseModel):
    """Output schema for pickup-schedule-create tool."""
    pickup_id: UUID
    children: List[UUID]
    status: PickupStatus
    scheduled_time: datetime
    schools_affected: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class DelegateAuthorizeOutput(BaseModel):
    """Output schema for delegate-authorize tool."""
    delegate_id: UUID
    authorized_schools: List[UUID]
    sync_status: SyncStatus

    model_config = ConfigDict(from_attributes=True)


class EmergencyDeclareOutput(BaseModel):
    """Output schema for emergency-declare tool."""
    emergency_id: UUID
    notified_count: int
    delegates_notified: List[UUID] = Field(default_factory=list)
    schools_notified: List[UUID] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class SchoolDashboardOutput(BaseModel):
    """Output schema for school-dashboard-fetch tool."""
    count: int
    next_pickup: Optional[dict] = None  # Could be typed further
    school_name: str

    model_config = ConfigDict(from_attributes=True)


class MonitoringDashboardOutput(BaseModel):
    """Output schema for monitoring-dashboard-fetch tool."""
    uptime_seconds: float
    total_requests: int
    error_rate: float
    avg_latency_ms: float

    model_config = ConfigDict(from_attributes=True)


# ═══════════════════════════════════════════════════════════════
# ERROR SCHEMAS
# ═══════════════════════════════════════════════════════════════

class ErrorCode:
    """Error codes for structured error responses."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    OWNERSHIP_ERROR = "OWNERSHIP_ERROR"
    DATABASE_ERROR = "DATABASE_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class ErrorResponse(BaseModel):
    """Structured error response."""
    code: str
    message: str
    details: Optional[dict] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    model_config = ConfigDict(from_attributes=True)
```

**Update Handlers**:
```python
# main.py
from schemas import AuthLoginOutput, ErrorResponse, ErrorCode

async def _handle_auth_login(arguments: Dict[str, Any]) -> types.CallToolResult:
    try:
        payload = AuthLoginInput.model_validate(arguments)
    except ValidationError as exc:
        error = ErrorResponse(
            code=ErrorCode.VALIDATION_ERROR,
            message="Input validation failed",
            details={"errors": exc.errors()}
        )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=error.message)],
            structuredContent=error.model_dump(mode="json"),
            isError=True,
        )

    try:
        result = await login_user(email=payload.email, password=payload.password)

        # ✅ Validate output before returning
        output = AuthLoginOutput(
            user_id=result["user"]["id"],
            email=result["user"]["email"],
            role=result["profile"]["role"],
            access_token=result["session"]["access_token"],
        )

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"✓ Connexion réussie! Bienvenue {result['profile'].get('name') or result['user']['email']}"
                )
            ],
            structuredContent=output.model_dump(mode="json"),  # ✅ Validated
            _meta={
                "session": result["session"],
                "profile": result["profile"],
            },
        )
    except InvalidCredentialsError:
        error = ErrorResponse(
            code=ErrorCode.INVALID_CREDENTIALS,
            message="Email ou mot de passe incorrect."
        )
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=error.message)],
            structuredContent=error.model_dump(mode="json"),
            isError=True,
        )
```

**Benefits**:
- ✅ Guarantees response structure
- ✅ Catches bugs before returning to client
- ✅ Enables output schema documentation
- ✅ TypeScript type generation possible

---

### 1.3 Replace String UUIDs with UUID Type

**Priority**: 🔴 CRITICAL
**Effort**: 1 day
**Risk**: Medium (requires careful migration)

#### Current State
```python
from uuid import uuid4
pickup_id = str(uuid4())  # ❌ String
child_ids: List[str]  # ❌ List of strings
```

#### Recommended Implementation

**Step 1: Update Pydantic Models**
```python
from uuid import UUID
from pydantic import UUID4  # Alias for UUID validation

class PickupScheduleInput(BaseModel):
    child_ids: List[UUID4] = Field(
        ...,
        alias="childIds",
        description="List of child UUIDs",
        min_length=1,
    )
    pickup_person_id: UUID4 = Field(..., alias="pickupPersonId")
    scheduled_time: datetime  # ✅ Also switch to datetime
    notes: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True, extra="forbid")
```

**Step 2: Update Function Signatures**
```python
async def get_schools_for_children(child_ids: List[UUID]) -> List[Dict[str, Any]]:
    """Get unique schools for a list of children."""
    supabase = get_supabase()

    # Convert UUID to string only at boundary:
    id_strings = [str(cid) for cid in child_ids]

    response = supabase.table("children").select("...").in_("id", id_strings).execute()
    return list(schools.values())


async def create_pickup_request(
    child_ids: List[UUID],
    pickup_person_id: UUID,
    scheduled_time: datetime,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a pickup request."""
    supabase = get_supabase()

    pickup_id = uuid4()  # ✅ Keep as UUID (don't convert to str)

    pickup_data = {
        "id": str(pickup_id),  # ✅ Convert to str only for Supabase
        "pickup_person_id": str(pickup_person_id),
        "scheduled_time": scheduled_time.isoformat(),
        "status": "confirmed",
        "notes": notes,
    }

    response = supabase.table("pickups").insert(pickup_data).execute()
    return response.data[0] if response.data else pickup_data
```

**Step 3: Update auth.py**
```python
@dataclass
class UserProfile:
    """User profile with typed UUIDs."""
    id: UUID  # ✅ UUID type
    email: str
    name: Optional[str] = None
    role: str = "parent"
    schools: List[UUID] = None  # ✅ List[UUID]
    children: List[UUID] = None  # ✅ List[UUID]
    email_verified: bool = False
    created_at: Optional[datetime] = None

    def __post_init__(self):
        if self.schools is None:
            self.schools = []
        if self.children is None:
            self.children = []
```

**Migration Strategy**:
1. Add UUID validation to Pydantic models (accepts both UUID and string)
2. Update internal functions to use UUID type
3. Convert to string only at DB boundary (Supabase calls)
4. Update all type hints progressively

**Benefits**:
- ✅ Prevents invalid UUIDs at runtime
- ✅ Type checker catches errors
- ✅ Self-documenting code

---

### 1.4 Generate Supabase TypeScript Types

**Priority**: 🔴 CRITICAL
**Effort**: 0.5 days
**Risk**: Low (automated generation)

#### Implementation

**Step 1: Generate Types**
```bash
cd /home/user/openai-apps-sdk-examples
npx supabase gen types typescript --project-id <PROJECT_ID> > src/database.types.ts
```

**Step 2: Use Generated Types**
```typescript
// src/allobye-dashboard/dashboard.tsx
import { Database } from "../database.types";

type PickupRow = Database['public']['Tables']['pickups']['Row'];
type EmergencyRow = Database['public']['Tables']['emergencies']['Row'];

// Now Supabase calls are typed:
supabase
  .channel("pickups-changes")
  .on<PickupRow>(  // ✅ Typed payload
    "postgres_changes",
    { event: "*", schema: "public", table: "pickups" },
    (payload) => {
      // payload.new is typed as PickupRow
      console.log(payload.new.scheduled_time);  // ✅ Autocomplete!
    }
  )
  .subscribe();
```

**Benefits**:
- ✅ Database schema changes detected at compile time
- ✅ Autocomplete for all table columns
- ✅ Prevents accessing non-existent fields
- ✅ Stays in sync with DB schema

---

## Phase 2: High Priority (P1)

**Timeline**: 3-4 days
**Goal**: Strengthen type safety across all layers

---

### 2.1 Add SQL Type Constraints

**Priority**: 🟡 HIGH
**Effort**: 1 day
**Risk**: Low (backward compatible)

#### Implementation

Create `/home/user/openai-apps-sdk-examples/allobye_server_python/migrations/001_add_constraints.sql`:
```sql
-- === Email Validation ===
ALTER TABLE children ADD CONSTRAINT valid_parent_email
    CHECK (parent_email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$');

ALTER TABLE delegates ADD CONSTRAINT valid_delegate_email
    CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$');

ALTER TABLE schools ADD CONSTRAINT valid_school_email
    CHECK (email IS NULL OR email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$');

-- === Phone Validation (Quebec format) ===
ALTER TABLE children ADD CONSTRAINT valid_parent_phone
    CHECK (parent_phone IS NULL OR parent_phone ~ '^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$');

ALTER TABLE delegates ADD CONSTRAINT valid_delegate_phone
    CHECK (phone IS NULL OR phone ~ '^\+?1?[-.\s]?\(?[0-9]{3}\)?[-.\s]?[0-9]{3}[-.\s]?[0-9]{4}$');

-- === Permissions Array Validation ===
ALTER TABLE delegates ADD CONSTRAINT valid_permissions
    CHECK (
        permissions <@ ARRAY['pickup', 'emergency_contact', 'medical_decisions']::TEXT[]
    );

-- === Timezone Validation ===
ALTER TABLE schools ADD CONSTRAINT valid_timezone
    CHECK (
        timezone = ANY(
            SELECT name FROM pg_timezone_names WHERE name LIKE 'America/%'
        )
    );

-- === Positive Delays ===
ALTER TABLE pickups ADD CONSTRAINT positive_delay
    CHECK (delay_minutes >= 0);

ALTER TABLE pickups ADD CONSTRAINT positive_eta
    CHECK (eta_minutes IS NULL OR eta_minutes >= 0);

-- === Future Scheduled Times (optional) ===
-- ALTER TABLE pickups ADD CONSTRAINT future_scheduled_time
--     CHECK (scheduled_time > NOW() - INTERVAL '1 hour');  -- Allow 1h grace period

-- === User Role Enum ===
CREATE TYPE user_role AS ENUM ('parent', 'school_staff', 'service_role');
-- Note: Requires migrating existing user_profiles table

-- === Add NOT NULL Constraints ===
ALTER TABLE children ALTER COLUMN name SET NOT NULL;
ALTER TABLE children ALTER COLUMN school_id SET NOT NULL;
ALTER TABLE children ALTER COLUMN parent_email SET NOT NULL;

ALTER TABLE delegates ALTER COLUMN email SET NOT NULL;

ALTER TABLE pickups ALTER COLUMN pickup_person_id SET NOT NULL;
ALTER TABLE pickups ALTER COLUMN scheduled_time SET NOT NULL;
```

**Apply Migration**:
```bash
python allobye_server_python/apply_schema.py --file migrations/001_add_constraints.sql
```

**Benefits**:
- ✅ Database enforces data quality
- ✅ Prevents invalid data at source
- ✅ Catches bugs early

---

### 2.2 Add Runtime Validation with Zod (Frontend)

**Priority**: 🟡 HIGH
**Effort**: 1 day
**Risk**: Low (augments TypeScript)

#### Implementation

**Install Zod**:
```bash
pnpm add zod
```

**Define Zod Schemas** (`src/allobye-dashboard/validation.ts`):
```typescript
import { z } from "zod";

// === Zod Schemas ===

export const PickupDataSchema = z.object({
  id: z.string().uuid(),
  scheduled_time: z.string().datetime(),  // ISO 8601
  actual_time: z.string().datetime().optional(),
  status: z.enum(["pending", "confirmed", "in_progress", "completed", "cancelled", "late"]),
  notes: z.string().optional(),
  eta_minutes: z.number().int().positive().optional(),
  delay_minutes: z.number().int().nonnegative().default(0),
  child: z.object({
    id: z.string().uuid(),
    name: z.string(),
    grade: z.string().optional(),
  }).optional(),
  pickup_person: z.object({
    id: z.string().uuid(),
    name: z.string().optional(),
    email: z.string().email(),
  }).optional(),
});

export const EmergencyAlertSchema = z.object({
  type: z.enum(["late", "illness", "cancel", "injury", "other"]),
  context: z.string(),
  child_id: z.string().uuid(),
  severity: z.enum(["low", "medium", "high", "critical"]).optional(),
});

// === Type Inference ===
export type PickupData = z.infer<typeof PickupDataSchema>;
export type EmergencyAlert = z.infer<typeof EmergencyAlertSchema>;
```

**Use in Components**:
```typescript
// src/allobye-dashboard/dashboard.tsx
import { PickupDataSchema } from "./validation";

.on("postgres_changes", { ... }, (payload) => {
  try {
    // ✅ Validate before using
    const validatedPickup = PickupDataSchema.parse(payload.new);

    setRealtimePickups((prev) => {
      const updated = prev.filter((p) => p.id !== validatedPickup.id);
      return [...updated, validatedPickup];
    });
  } catch (error) {
    console.error("Invalid pickup data from Supabase:", error);
    // Handle error (show notification, log to monitoring, etc.)
  }
})
```

**Benefits**:
- ✅ Runtime validation (TypeScript only does compile-time)
- ✅ Catches schema drift from database
- ✅ Better error messages
- ✅ Can validate external API responses

---

### 2.3 Add Shared Type Definitions

**Priority**: 🟡 HIGH
**Effort**: 1 day
**Risk**: Low (improves consistency)

#### Implementation

Create `/home/user/openai-apps-sdk-examples/shared-types/`:
```
shared-types/
├── python/
│   └── __init__.py
│       └── enums.py  # Python enums
└── typescript/
    └── enums.ts      # TypeScript enums
```

**Python Enums** (`shared-types/python/enums.py`):
```python
from enum import Enum

class PickupStatus(str, Enum):
    """Pickup status values (shared with SQL and TypeScript)."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    LATE = "late"

class EmergencyType(str, Enum):
    """Emergency type values (shared with SQL and TypeScript)."""
    LATE = "late"
    ILLNESS = "illness"
    CANCEL = "cancel"
    INJURY = "injury"
    OTHER = "other"

class UserRole(str, Enum):
    """User role values (shared with SQL and TypeScript)."""
    PARENT = "parent"
    SCHOOL_STAFF = "school_staff"
    SERVICE_ROLE = "service_role"
```

**TypeScript Enums** (`shared-types/typescript/enums.ts`):
```typescript
/**
 * Shared enums between backend and frontend.
 * IMPORTANT: Keep in sync with Python enums and SQL constraints!
 */

export enum PickupStatus {
  PENDING = "pending",
  CONFIRMED = "confirmed",
  IN_PROGRESS = "in_progress",
  COMPLETED = "completed",
  CANCELLED = "cancelled",
  LATE = "late",
}

export enum EmergencyType {
  LATE = "late",
  ILLNESS = "illness",
  CANCEL = "cancel",
  INJURY = "injury",
  OTHER = "other",
}

export enum UserRole {
  PARENT = "parent",
  SCHOOL_STAFF = "school_staff",
  SERVICE_ROLE = "service_role",
}

// Type-safe literal types:
export type PickupStatusValue = `${PickupStatus}`;
export type EmergencyTypeValue = `${EmergencyType}`;
export type UserRoleValue = `${UserRole}`;
```

**Usage in Python**:
```python
from shared_types.python.enums import PickupStatus, UserRole

# Pydantic:
class PickupScheduleOutput(BaseModel):
    status: PickupStatus  # ✅ Enum validated

# Code:
pickup_data = {
    "status": PickupStatus.CONFIRMED,  # ✅ Type-safe
}
```

**Usage in TypeScript**:
```typescript
import { PickupStatus } from "../../shared-types/typescript/enums";

const getStatusColor = (status: PickupStatus): string => {
  switch (status) {
    case PickupStatus.COMPLETED:
      return "green";
    case PickupStatus.CANCELLED:
      return "gray";
    // ... TypeScript ensures all cases covered
  }
};
```

**Generate Script** (optional):
```python
# scripts/generate_shared_types.py
"""
Generate TypeScript enums from Python enums.
Run after modifying Python enums.
"""
import os
from pathlib import Path

def generate_ts_enums():
    # Read Python enums
    # Generate TypeScript file
    # Write to shared-types/typescript/enums.ts
    pass

if __name__ == "__main__":
    generate_ts_enums()
```

**Benefits**:
- ✅ Single source of truth for enums
- ✅ Prevents enum drift
- ✅ Type-safe across all layers

---

## Phase 3: Enhancements (P2)

**Timeline**: 2-3 days
**Goal**: Achieve 95%+ type coverage

---

### 3.1 Add Contract Tests

**Priority**: 🟠 MEDIUM
**Effort**: 2 days

#### Implementation

```python
# tests/test_contracts.py
import pytest
from pydantic import ValidationError
from schemas import (
    PickupScheduleInput,
    PickupScheduleOutput,
    ErrorResponse,
    ErrorCode,
)

class TestPickupScheduleContract:
    """Test input/output contracts for pickup-schedule-create."""

    def test_input_valid(self):
        """Valid input passes validation."""
        data = {
            "childIds": ["123e4567-e89b-12d3-a456-426614174000"],
            "pickupPersonId": "223e4567-e89b-12d3-a456-426614174000",
            "scheduledTime": "2025-11-04T15:30:00-05:00",
        }
        schema = PickupScheduleInput(**data)
        assert len(schema.child_ids) == 1

    def test_input_missing_field(self):
        """Missing required field raises ValidationError."""
        data = {
            "childIds": ["123e4567-e89b-12d3-a456-426614174000"],
            "pickupPersonId": "223e4567-e89b-12d3-a456-426614174000",
        }
        with pytest.raises(ValidationError) as exc_info:
            PickupScheduleInput(**data)
        assert "scheduledTime" in str(exc_info.value)

    def test_input_invalid_uuid(self):
        """Invalid UUID raises ValidationError."""
        data = {
            "childIds": ["not-a-uuid"],
            "pickupPersonId": "223e4567-e89b-12d3-a456-426614174000",
            "scheduledTime": "2025-11-04T15:30:00",
        }
        with pytest.raises(ValidationError):
            PickupScheduleInput(**data)

    def test_output_valid(self):
        """Valid output passes validation."""
        data = {
            "pickup_id": "323e4567-e89b-12d3-a456-426614174000",
            "children": ["123e4567-e89b-12d3-a456-426614174000"],
            "status": "confirmed",
            "scheduled_time": "2025-11-04T15:30:00-05:00",
        }
        output = PickupScheduleOutput(**data)
        assert output.status == "confirmed"

    def test_error_response_structure(self):
        """Error response has correct structure."""
        error = ErrorResponse(
            code=ErrorCode.VALIDATION_ERROR,
            message="Test error",
            details={"field": "test"}
        )
        assert error.code == ErrorCode.VALIDATION_ERROR
        assert "timestamp" in error.model_dump()
```

**Run Tests**:
```bash
pytest tests/test_contracts.py -v
```

---

### 3.2 Add Type Coverage Monitoring

**Priority**: 🟠 MEDIUM
**Effort**: 0.5 days

#### Implementation

**Python (mypy)**:
```bash
# Install mypy
pip install mypy

# Create mypy.ini
cat > mypy.ini << 'EOF'
[mypy]
python_version = 3.11
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True

[mypy-tests.*]
disallow_untyped_defs = False
EOF

# Run mypy
mypy allobye_server_python/ --html-report mypy-report
```

**TypeScript**:
```bash
# Update tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "strictFunctionTypes": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
  }
}

# Check types
pnpm tsc --noEmit
```

**CI/CD Integration** (`.github/workflows/type-check.yml`):
```yaml
name: Type Check

on: [push, pull_request]

jobs:
  python-types:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: "3.11"
      - run: pip install mypy pydantic
      - run: mypy allobye_server_python/ --strict

  typescript-types:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: pnpm/action-setup@v2
      - uses: actions/setup-node@v3
      - run: pnpm install
      - run: pnpm tsc --noEmit
```

---

## Implementation Guide

### Week 1: Critical Phase

**Day 1-2: TypeScript Migration**
- [ ] Create `src/allobye-dashboard/types.ts`
- [ ] Rename all .jsx → .tsx
- [ ] Add types to PickupCard
- [ ] Add types to Dashboard
- [ ] Add types to EmergencyAlert
- [ ] Test compilation

**Day 3-4: Pydantic Output Models**
- [ ] Create `schemas.py` with all output models
- [ ] Update auth-signup handler
- [ ] Update auth-login handler
- [ ] Update pickup-schedule-create handler
- [ ] Update all remaining handlers
- [ ] Test all tools

**Day 5: UUID Migration**
- [ ] Update Pydantic input models
- [ ] Update function signatures
- [ ] Test end-to-end

**Day 6-7: Supabase Types + SQL Constraints**
- [ ] Generate Supabase TypeScript types
- [ ] Apply SQL constraint migration
- [ ] Test database constraints

### Week 2: High Priority Phase

**Day 8: Zod Validation**
- [ ] Install Zod
- [ ] Define schemas
- [ ] Add to Realtime handlers

**Day 9: Shared Types**
- [ ] Create shared-types directory
- [ ] Define Python enums
- [ ] Define TypeScript enums
- [ ] Update all usages

**Day 10-11: Contract Tests**
- [ ] Write input validation tests
- [ ] Write output validation tests
- [ ] Achieve 90% test coverage

---

## Migration Strategies

### Safe UUID Migration

**Strategy**: Gradual migration with backward compatibility

1. **Phase 1**: Accept both UUID and string in Pydantic
   ```python
   from pydantic import field_validator
   from uuid import UUID

   class PickupScheduleInput(BaseModel):
       child_ids: List[Union[UUID, str]]

       @field_validator('child_ids', mode='before')
       def parse_uuids(cls, v):
           return [UUID(x) if isinstance(x, str) else x for x in v]
   ```

2. **Phase 2**: Update all internal code to use UUID

3. **Phase 3**: Remove string support from Pydantic

---

## Testing Strategy

### Test Pyramid

```
         ┌─────────────────┐
         │   E2E Tests     │  (5%)
         │  Full workflow  │
         └─────────────────┘
       ┌───────────────────────┐
       │  Integration Tests    │  (15%)
       │  Tool → DB → Response │
       └───────────────────────┘
     ┌─────────────────────────────┐
     │    Contract Tests           │  (30%)
     │  Input/Output validation    │
     └─────────────────────────────┘
   ┌───────────────────────────────────┐
   │        Unit Tests                 │  (50%)
   │  Individual functions             │
   └───────────────────────────────────┘
```

---

## Monitoring & Validation

### Metrics to Track

```python
# Type Coverage Metrics
{
    "python_type_hints_coverage": "85%",
    "pydantic_model_coverage": "100%",
    "typescript_coverage": "95%",
    "sql_constraint_coverage": "92%",

    "mypy_errors": 0,
    "typescript_errors": 0,

    "contract_test_coverage": "90%",
    "e2e_test_coverage": "75%",
}
```

---

## Conclusion

**Estimated Timeline**: 10-14 days for complete implementation

**Expected Outcome**:
- Type coverage: 67.5% → 95%+
- Production ready: YES
- Runtime type errors: Reduced by 90%+
- Developer experience: Significantly improved

**ROI**:
- Fewer bugs in production
- Faster development (autocomplete, refactoring)
- Better documentation (types are docs)
- Easier onboarding for new developers

**Next Steps**:
1. Prioritize Phase 1 (Critical) - Start immediately
2. Allocate 1 week for Phase 1 completion
3. Schedule Phase 2 for following week
4. Monitor type coverage weekly
