# MCP Contract Analysis - AllôBye

**Date**: 2025-11-04
**Analyzer**: Validateur de Types
**Focus**: MCP tool input/output contracts, API guarantees

---

## Executive Summary

AllôBye implements **10 MCP tools** with **excellent input contract enforcement** (100% Pydantic validation) but **weak output contracts** (0% schema validation). The system demonstrates strong API design principles but lacks formal output specifications.

**Contract Quality Assessment**:
- ✅ **Input Contracts**: 100% (All tools have Pydantic schemas)
- ❌ **Output Contracts**: 0% (No output schema validation)
- ⚠️ **Error Contracts**: 50% (Consistent structure, but not validated)
- ✅ **Metadata Contracts**: 80% (Well-documented, but inconsistent)

**Key Strengths**:
- Comprehensive input validation via Pydantic
- Rich metadata annotations (OpenAI-specific)
- Consistent tool naming convention
- Detailed error messages

**Key Weaknesses**:
- No formal output schemas
- Response structure varies per tool
- No API versioning
- Missing contract tests

---

## 1. Tool Inventory and Contract Overview

### 1.1 Authentication Tools (5)

| Tool Name | Input Schema | Output Contract | Error Contract | Status |
|-----------|--------------|-----------------|----------------|--------|
| `auth-signup` | ✅ AuthSignupInput | ⚠️ Informal | ⚠️ Informal | 🟡 Partial |
| `auth-login` | ✅ AuthLoginInput | ⚠️ Informal | ⚠️ Informal | 🟡 Partial |
| `auth-logout` | ✅ Inline Schema | ⚠️ Informal | ⚠️ Informal | 🟡 Partial |
| `auth-reset-password` | ✅ AuthResetPasswordInput | ⚠️ Informal | ⚠️ Informal | 🟡 Partial |
| `auth-profile` | ✅ Inline Schema | ⚠️ Informal | ⚠️ Informal | 🟡 Partial |

### 1.2 Pickup Management Tools (4)

| Tool Name | Input Schema | Output Contract | Error Contract | Status |
|-----------|--------------|-----------------|----------------|--------|
| `pickup-schedule-create` | ✅ PickupScheduleInput | ⚠️ Informal | ⚠️ Informal | 🟡 Partial |
| `delegate-authorize` | ✅ DelegateAuthorizeInput | ⚠️ Informal | ⚠️ Informal | 🟡 Partial |
| `emergency-declare` | ✅ EmergencyDeclareInput | ⚠️ Informal | ⚠️ Informal | 🟡 Partial |
| `school-dashboard-fetch` | ✅ SchoolDashboardInput | ⚠️ Informal | ⚠️ Informal | 🟡 Partial |

### 1.3 Observability Tools (1)

| Tool Name | Input Schema | Output Contract | Error Contract | Status |
|-----------|--------------|-----------------|----------------|--------|
| `monitoring-dashboard-fetch` | ✅ MonitoringDashboardInput | ⚠️ Informal | ⚠️ Informal | 🟡 Partial |

---

## 2. Input Contract Analysis

### 2.1 Input Schema Quality: ✅ EXCELLENT

All 10 tools use **Pydantic models** or **JSON Schema** for input validation.

#### Example: pickup-schedule-create

**Pydantic Model** (main.py:101-126):
```python
class PickupScheduleInput(BaseModel):
    """Input schema for scheduling a pickup."""

    child_ids: List[str] = Field(
        ...,
        alias="childIds",
        description="List of child IDs to be picked up",
        min_length=1,  # ✅ Validation: At least one child required
    )
    pickup_person_id: str = Field(
        ...,
        alias="pickupPersonId",
        description="ID of the authorized person picking up the children",
    )
    scheduled_time: str = Field(
        ...,
        alias="scheduledTime",
        description="ISO 8601 datetime for pickup (e.g., 2025-11-04T15:00:00-05:00)",
    )
    notes: Optional[str] = Field(
        None,
        description="Optional notes about the pickup",
    )

    model_config = ConfigDict(
        populate_by_name=True,  # ✅ Accepts both camelCase and snake_case
        extra="forbid"  # ✅ Rejects unknown fields
    )
```

**Generated JSON Schema** (auto-generated for MCP):
```json
{
  "type": "object",
  "properties": {
    "childIds": {
      "type": "array",
      "items": { "type": "string" },
      "minItems": 1,
      "description": "List of child IDs to be picked up"
    },
    "pickupPersonId": {
      "type": "string",
      "description": "ID of the authorized person picking up the children"
    },
    "scheduledTime": {
      "type": "string",
      "description": "ISO 8601 datetime for pickup (e.g., 2025-11-04T15:00:00-05:00)"
    },
    "notes": {
      "type": "string",
      "description": "Optional notes about the pickup"
    }
  },
  "required": ["childIds", "pickupPersonId", "scheduledTime"]
}
```

**Contract Guarantees**:
1. ✅ **Field Presence**: Required fields enforced (`required` array)
2. ✅ **Type Safety**: Type coercion via Pydantic (str → str, List → List)
3. ✅ **Field Validation**: `min_length=1` ensures non-empty array
4. ✅ **Unknown Fields Rejected**: `extra="forbid"` prevents typos
5. ✅ **Alias Support**: Frontend can use camelCase, Python uses snake_case
6. ✅ **Descriptions**: Every field documented for ChatGPT

**Quality Score**: 10/10 ✅

---

### 2.2 Input Validation Examples

#### Good: Password Length Validation
```python
class AuthSignupInput(BaseModel):
    password: str = Field(
        ...,
        description="Password (minimum 6 characters)",
        min_length=6,  # ✅ Enforces minimum length
    )
```

**Test**:
```python
# Valid:
AuthSignupInput(email="test@example.com", password="secret123")  # ✅

# Invalid:
AuthSignupInput(email="test@example.com", password="12345")
# ValidationError: String should have at least 6 characters
```

#### Good: Enum-like Validation via Literals (missing!)
**Current**:
```python
class EmergencyDeclareInput(BaseModel):
    emergency_type: str = Field(
        ...,
        description="Type of emergency: late, illness, cancel, other",
    )
    # ⚠️ Accepts ANY string, not just the documented values
```

**Should Be**:
```python
from typing import Literal

class EmergencyDeclareInput(BaseModel):
    emergency_type: Literal["late", "illness", "cancel", "other"] = Field(
        ...,
        description="Type of emergency",
    )
    # ✅ Only accepts documented values
```

---

### 2.3 Input Contract Weaknesses

**Minor Issues**:

1. **UUID Validation Missing**:
   ```python
   child_ids: List[str]  # ⚠️ Should validate UUID format

   # Better:
   from pydantic import UUID4
   child_ids: List[UUID4]  # ✅ Auto-validates UUID format
   ```

2. **Datetime Validation Missing**:
   ```python
   scheduled_time: str  # ⚠️ Could be invalid ISO 8601

   # Better:
   from datetime import datetime
   scheduled_time: datetime  # ✅ Pydantic parses ISO 8601
   ```

3. **Email Validation Missing** (auth tools):
   ```python
   email: str  # ⚠️ Could be invalid email

   # Better:
   from pydantic import EmailStr
   email: EmailStr  # ✅ Validates email format
   ```

**Impact**: Low (SQL database catches most invalid data)

---

## 3. Output Contract Analysis

### 3.1 Output Schema Quality: ❌ CRITICAL GAP

**No Pydantic output models exist.** All responses are manually constructed dictionaries.

#### Example: auth-login Response

**Code** (main.py:900-917):
```python
async def _handle_auth_login(arguments: Dict[str, Any]) -> types.CallToolResult:
    result = await login_user(email=payload.email, password=payload.password)

    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=f"✓ Connexion réussie! Bienvenue {result['profile'].get('name') or result['user']['email']}"
            )
        ],
        structuredContent={  # ❌ No schema validation
            "user_id": result["user"]["id"],
            "email": result["user"]["email"],
            "role": result["profile"]["role"],
            "access_token": result["session"]["access_token"],
        },
        _meta={  # ❌ No schema validation
            "session": result["session"],
            "profile": result["profile"],
        },
    )
```

**Issues**:
1. ❌ No guarantee `result["user"]` exists
2. ❌ No guarantee `result["profile"]["role"]` is valid
3. ❌ No type checking on response structure
4. ❌ `structuredContent` and `_meta` shapes undocumented

**What Should Exist**:
```python
class AuthLoginOutput(BaseModel):
    """Output schema for auth-login tool."""

    user_id: str  # UUID
    email: str
    role: Literal["parent", "school_staff"]
    access_token: str

    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "123e4567-e89b-12d3-a456-426614174000",
                "email": "parent@example.com",
                "role": "parent",
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }

# Usage:
output = AuthLoginOutput(**data).model_dump()  # ✅ Validates before returning
return types.CallToolResult(structuredContent=output)
```

---

### 3.2 Response Structure Analysis

**Per-Tool Response Shapes**:

#### auth-signup
```json
{
  "structuredContent": {
    "user_id": "uuid",
    "email": "string",
    "email_verified": "boolean"
  },
  "_meta": {
    "session": {
      "access_token": "string",
      "refresh_token": "string",
      "expires_at": "number"
    },
    "requires_verification": "boolean"
  }
}
```

#### auth-login
```json
{
  "structuredContent": {
    "user_id": "uuid",
    "email": "string",
    "role": "string",
    "access_token": "string"
  },
  "_meta": {
    "session": { ... },
    "profile": { ... }
  }
}
```

#### pickup-schedule-create
```json
{
  "structuredContent": {
    "pickup_id": "uuid",
    "children": ["uuid", ...],
    "status": "confirmed",
    "scheduled_time": "ISO 8601"
  },
  "_meta": {
    "full_results": { ... },
    "schools_affected": ["string", ...],
    "display_update": true
  }
}
```

**Observations**:
1. ⚠️ **Inconsistent Structure**: Each tool returns different fields
2. ⚠️ **No Envelope**: Some use `structuredContent`, some use `_meta`
3. ✅ **Content Field**: All have `content` with text description

**Recommendation**: Standardize response envelope
```typescript
interface ToolResponse<T> {
  content: TextContent[];
  structuredContent: T;  // Tool-specific schema
  _meta?: {
    timestamp: string;
    request_id: string;
    [key: string]: any;  // Tool-specific metadata
  };
}
```

---

### 3.3 Missing Output Contracts

**All 10 tools lack formal output schemas.** Here's what should exist:

```python
# === Authentication Tools ===

class AuthSignupOutput(BaseModel):
    user_id: UUID4
    email: EmailStr
    email_verified: bool

class AuthLoginOutput(BaseModel):
    user_id: UUID4
    email: EmailStr
    role: UserRole  # Enum
    access_token: str

class AuthProfileOutput(BaseModel):
    id: UUID4
    email: EmailStr
    name: Optional[str]
    role: UserRole
    schools: List[UUID4]
    children: List[UUID4]
    email_verified: bool

# === Pickup Management Tools ===

class PickupScheduleOutput(BaseModel):
    pickup_id: UUID4
    children: List[UUID4]
    status: PickupStatus  # Enum
    scheduled_time: datetime
    schools_affected: List[str]

class DelegateAuthorizeOutput(BaseModel):
    delegate_id: UUID4
    authorized_schools: List[UUID4]
    sync_status: Literal["success", "partial", "failed"]

class EmergencyDeclareOutput(BaseModel):
    emergency_id: UUID4
    notified_count: int
    delegates_notified: List[UUID4]
    schools_notified: List[UUID4]

# === Dashboard Tools ===

class SchoolDashboardOutput(BaseModel):
    count: int
    next_pickup: Optional[PickupData]
    pickups: List[PickupData]
    school_info: SchoolData

class MonitoringDashboardOutput(BaseModel):
    uptime_seconds: float
    total_requests: int
    error_rate: float
    # ... (full monitoring.py dashboard data)
```

---

## 4. Error Contract Analysis

### 4.1 Error Response Structure

**Current Implementation**:

All errors follow this pattern:
```python
return types.CallToolResult(
    content=[types.TextContent(type="text", text="Error message")],
    isError=True,
)
```

**Examples**:

#### Validation Error (main.py:848-852):
```python
return types.CallToolResult(
    content=[
        types.TextContent(
            type="text",
            text=f"Erreur de validation: {exc.errors()}"  # ⚠️ Unparseable
        )
    ],
    isError=True,
)
```

#### Authentication Error (main.py:918-922):
```python
return types.CallToolResult(
    content=[types.TextContent(type="text", text="Email ou mot de passe incorrect.")],
    isError=True,
)
```

#### Authorization Error (main.py:1028-1036):
```python
return types.CallToolResult(
    content=[
        types.TextContent(
            type="text",
            text="Authentification requise. Veuillez vous connecter en tant que parent.",
        )
    ],
    isError=True,
)
```

**Observations**:
1. ✅ **Consistent Flag**: All use `isError=True`
2. ✅ **Human-Readable**: Error messages in French (good for users)
3. ⚠️ **Not Structured**: Errors are plain text, not JSON
4. ❌ **No Error Codes**: Can't programmatically distinguish error types
5. ❌ **Inconsistent Details**: Validation errors include raw Pydantic output

---

### 4.2 Error Contract Issues

**Problem 1: Unparseable Validation Errors**

**Current**:
```
"Erreur de validation: [{'loc': ('childIds',), 'msg': 'Field required', 'type': 'missing'}]"
```

**Should Be**:
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Input validation failed",
    "details": {
      "fields": [
        {
          "field": "childIds",
          "message": "Field required",
          "type": "missing"
        }
      ]
    }
  }
}
```

**Problem 2: No Error Type Enumeration**

**Missing Error Codes**:
```python
class ErrorCode(str, Enum):
    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    AUTHORIZATION_FAILED = "AUTHORIZATION_FAILED"
    INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
    SESSION_EXPIRED = "SESSION_EXPIRED"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    DATABASE_ERROR = "DATABASE_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"
```

**Problem 3: No Structured Error Response**

**Should Define**:
```python
class ErrorResponse(BaseModel):
    code: ErrorCode
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    request_id: Optional[str] = None

# Usage:
return types.CallToolResult(
    structuredContent=ErrorResponse(
        code=ErrorCode.VALIDATION_ERROR,
        message="Input validation failed",
        details={"fields": exc.errors()}
    ).model_dump(),
    isError=True,
)
```

---

### 4.3 Error Contract Quality Score

```
┌──────────────────────────────────────────────────────────┐
│                ERROR CONTRACT SCORECARD                  │
├────────────────────────────┬──────────┬──────────────────┤
│ Criterion                  │ Score    │ Status           │
├────────────────────────────┼──────────┼──────────────────┤
│ Consistent Error Flag      │ 100%     │ ✅ Excellent     │
│ Human-Readable Messages    │ 100%     │ ✅ Excellent     │
│ Structured Error Format    │ 0%       │ ❌ Missing       │
│ Error Code Enumeration     │ 0%       │ ❌ Missing       │
│ Error Details              │ 25%      │ ⚠️ Inconsistent  │
│ Frontend Parseability      │ 20%      │ ❌ Poor          │
├────────────────────────────┼──────────┼──────────────────┤
│ OVERALL                    │ 41%      │ ⚠️ Needs Work    │
└────────────────────────────┴──────────┴──────────────────┘
```

---

## 5. Metadata Contract Analysis

### 5.1 OpenAI-Specific Metadata

**All tools include rich metadata** for ChatGPT integration:

```python
def _tool_meta(widget: Optional[AllobyeWidget] = None) -> Dict[str, Any]:
    meta = {
        "annotations": {
            "destructiveHint": False,
            "openWorldHint": False,
            "readOnlyHint": True,
        }
    }

    if widget:
        meta.update({
            "openai/outputTemplate": widget.template_uri,
            "openai/toolInvocation/invoking": widget.invoking,
            "openai/toolInvocation/invoked": widget.invoked,
            "openai/widgetAccessible": True,
            "openai/resultCanProduceWidget": True,
        })

    return meta
```

**Quality**: ✅ Excellent
- Semantic hints for ChatGPT
- Widget integration metadata
- Consistent across all tools

---

### 5.2 Tool Response Metadata

**Per-Tool Analysis**:

#### auth-login (main.py:913-916):
```python
_meta={
    "session": result["session"],  # ✅ Useful: Access token, refresh token
    "profile": result["profile"],  # ✅ Useful: Full user profile
}
```

#### pickup-schedule-create (main.py:1103-1107):
```python
_meta={
    "full_results": results,  # ⚠️ Redundant with structuredContent?
    "schools_affected": [s["name"] for s in schools],  # ✅ Useful
    "display_update": True,  # ✅ Useful: Signals UI refresh
}
```

#### school-dashboard-fetch (main.py:1317-1327):
```python
_meta={
    "openai.com/widget": widget_resource.model_dump(mode="json"),
    "openai/outputTemplate": SCHOOL_DASHBOARD_WIDGET.template_uri,
    "openai/toolInvocation/invoking": "Chargement du tableau de bord...",
    "openai/toolInvocation/invoked": "Tableau de bord chargé",
    "openai/widgetAccessible": True,
    "openai/resultCanProduceWidget": True,
    "pickups": pickups,  # ✅ Widget data
    "school_info": school_info,  # ✅ Widget data
    "display_mode": "fullscreen",  # ✅ UI hint
    "refresh_interval": 30,  # ✅ Polling interval
}
```

**Observations**:
1. ✅ **Rich Context**: Metadata provides extra info for frontend
2. ⚠️ **Inconsistent Fields**: Each tool has different _meta shape
3. ⚠️ **Duplication**: Some data in both `structuredContent` and `_meta`
4. ❌ **No Schema**: _meta structure not validated

---

### 5.3 Widget Contract

**Widget-Enabled Tools** (2):
- `school-dashboard-fetch`
- `monitoring-dashboard-fetch`

**Widget Metadata Contract**:
```python
@dataclass(frozen=True)
class AllobyeWidget:
    identifier: str  # "school-dashboard"
    title: str  # "Tableau de bord école - AllôBye"
    template_uri: str  # "ui://widget/allobye-dashboard.html"
    invoking: str  # "Chargement du tableau de bord..."
    invoked: str  # "Tableau de bord chargé"
    html: str  # Full HTML content
```

**Quality**: ✅ Excellent
- Well-structured dataclass
- Immutable (frozen=True)
- Loaded from files with fallback

**Issue**: ⚠️ HTML content not validated (could be invalid HTML)

---

## 6. Contract Guarantees Analysis

### 6.1 Input Guarantees: ✅ STRONG

**What the Contract Guarantees**:
1. ✅ Required fields are present
2. ✅ Field types match schema
3. ✅ Field values validated (min_length, etc.)
4. ✅ Unknown fields rejected
5. ✅ Automatic type coercion (str → str, int → int)

**Test Case**:
```python
# Valid input:
{
  "childIds": ["uuid-1", "uuid-2"],
  "pickupPersonId": "uuid-3",
  "scheduledTime": "2025-11-04T15:00:00-05:00"
}
# ✅ Passes validation

# Invalid input (missing field):
{
  "childIds": ["uuid-1"],
  "pickupPersonId": "uuid-3"
}
# ❌ ValidationError: Field required: scheduledTime

# Invalid input (wrong type):
{
  "childIds": "uuid-1",  # Should be array
  "pickupPersonId": "uuid-3",
  "scheduledTime": "2025-11-04T15:00:00"
}
# ❌ ValidationError: Input should be a valid list

# Invalid input (unknown field):
{
  "childIds": ["uuid-1"],
  "pickupPersonId": "uuid-3",
  "scheduledTime": "2025-11-04T15:00:00",
  "extraField": "value"
}
# ❌ ValidationError: Extra inputs are not permitted
```

---

### 6.2 Output Guarantees: ❌ NONE

**What the Contract SHOULD Guarantee**:
1. ❌ Response shape matches documented schema
2. ❌ All required fields present
3. ❌ Field types are correct
4. ❌ Enum values are valid

**Current Reality**:
```python
# No validation before returning:
return types.CallToolResult(
    structuredContent={
        "pickup_id": results.get("id"),  # Could be None!
        "children": payload.child_ids,
        "status": "confirmed",  # Could be typo: "confimred"
    }
)
```

**Possible Failures**:
```python
# If results is empty dict:
structuredContent = {
    "pickup_id": None,  # ❌ Should be UUID
    "children": [...],
    "status": "confirmed",
}

# If database returns unexpected status:
structuredContent = {
    "pickup_id": "...",
    "children": [...],
    "status": "unknown_status",  # ❌ Not in enum
}
```

---

### 6.3 Error Guarantees: ⚠️ PARTIAL

**What IS Guaranteed**:
1. ✅ `isError=True` flag is set
2. ✅ Error message is human-readable

**What is NOT Guaranteed**:
1. ❌ Error message is parseable
2. ❌ Error code is provided
3. ❌ Error details are structured

---

## 7. Contract Testing Analysis

### 7.1 Current Testing: ❌ NONE

**No contract tests exist** in the repository.

**What Should Exist**:

```python
# tests/test_contracts.py

import pytest
from pydantic import ValidationError
from main import PickupScheduleInput, _handle_pickup_schedule_create

class TestPickupScheduleContract:
    """Test input/output contracts for pickup-schedule-create."""

    def test_valid_input(self):
        """Valid input should pass validation."""
        data = {
            "childIds": ["uuid-1", "uuid-2"],
            "pickupPersonId": "uuid-3",
            "scheduledTime": "2025-11-04T15:00:00-05:00"
        }
        schema = PickupScheduleInput(**data)
        assert schema.child_ids == ["uuid-1", "uuid-2"]

    def test_missing_required_field(self):
        """Missing required field should raise ValidationError."""
        data = {
            "childIds": ["uuid-1"],
            "pickupPersonId": "uuid-3"
            # Missing scheduledTime
        }
        with pytest.raises(ValidationError) as exc_info:
            PickupScheduleInput(**data)
        assert "scheduledTime" in str(exc_info.value)

    def test_empty_child_ids(self):
        """Empty child_ids should fail min_length validation."""
        data = {
            "childIds": [],  # Empty list
            "pickupPersonId": "uuid-3",
            "scheduledTime": "2025-11-04T15:00:00"
        }
        with pytest.raises(ValidationError) as exc_info:
            PickupScheduleInput(**data)
        assert "min_length" in str(exc_info.value)

    def test_extra_fields_rejected(self):
        """Unknown fields should be rejected."""
        data = {
            "childIds": ["uuid-1"],
            "pickupPersonId": "uuid-3",
            "scheduledTime": "2025-11-04T15:00:00",
            "extraField": "value"
        }
        with pytest.raises(ValidationError) as exc_info:
            PickupScheduleInput(**data)
        assert "Extra inputs are not permitted" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_output_structure(self):
        """Output should match expected schema."""
        # Mock dependencies, call handler
        result = await _handle_pickup_schedule_create({...})

        # Validate output
        assert "structuredContent" in result
        assert "pickup_id" in result.structuredContent
        assert "children" in result.structuredContent
        assert "status" in result.structuredContent

        # Validate against schema (once it exists)
        # PickupScheduleOutput(**result.structuredContent)
```

---

### 7.2 Contract Testing Gaps

**Missing Test Coverage**:
1. ❌ Input schema validation tests (0%)
2. ❌ Output schema validation tests (0%)
3. ❌ Error response format tests (0%)
4. ❌ Integration tests (tool call → response)
5. ❌ Contract compatibility tests (breaking changes)

---

## 8. API Versioning Analysis

### 8.1 Current Versioning: ❌ NONE

**No API versioning exists.**

**Risk**:
- Tool schema changes break existing clients
- No backward compatibility guarantee
- No deprecation path

**Example Breaking Change**:
```python
# Version 1 (current):
class PickupScheduleInput(BaseModel):
    child_ids: List[str]

# Version 2 (hypothetical):
class PickupScheduleInput(BaseModel):
    child_ids: List[UUID4]  # ❌ BREAKING: Type changed

# Existing clients break silently!
```

---

### 8.2 Recommended Versioning Strategy

**Option 1: Tool Name Versioning**
```python
# v1 tools:
"pickup-schedule-create"
"delegate-authorize"

# v2 tools (breaking changes):
"pickup-schedule-create-v2"
"delegate-authorize-v2"

# Keep both versions running simultaneously
```

**Option 2: Schema Versioning**
```python
class PickupScheduleInputV1(BaseModel):
    child_ids: List[str]

class PickupScheduleInputV2(BaseModel):
    child_ids: List[UUID4]

# Handler checks version:
def _handle_pickup_schedule_create(arguments):
    version = arguments.get("_version", 1)
    if version == 1:
        schema = PickupScheduleInputV1
    else:
        schema = PickupScheduleInputV2
```

**Option 3: Semantic Versioning (Recommended)**
```python
API_VERSION = "1.0.0"

# Breaking changes → 2.0.0
# New features → 1.1.0
# Bug fixes → 1.0.1
```

---

## 9. Contract Documentation

### 9.1 Current Documentation

**Good**:
- ✅ Pydantic Field descriptions
- ✅ Tool titles in French
- ✅ Tool descriptions explain purpose

**Example**:
```python
types.Tool(
    name="pickup-schedule-create",
    title="Planifier un ramassage",
    description="Schedule a pickup for one or more children. Handles multi-child, multi-school coordination automatically. Requires parent authentication.",
    inputSchema=PickupScheduleInput.model_json_schema(),
)
```

**Missing**:
- ❌ Output schema documentation
- ❌ Error code documentation
- ❌ Example requests/responses
- ❌ OpenAPI/Swagger spec

---

### 9.2 Recommended Documentation

**Should Add**:

```python
# === Comprehensive Tool Documentation ===

class PickupScheduleCreateContract:
    """
    Tool: pickup-schedule-create
    Version: 1.0.0

    Description:
        Schedule a pickup for one or more children across one or more schools.
        Automatically coordinates multi-school pickups via A2A message bus.

    Authentication:
        - Required: Yes
        - Role: parent

    Input Schema:
        See PickupScheduleInput

    Output Schema:
        See PickupScheduleOutput

    Errors:
        - VALIDATION_ERROR: Input validation failed
        - AUTHENTICATION_FAILED: User not authenticated
        - AUTHORIZATION_FAILED: User not authorized (not a parent)
        - OWNERSHIP_ERROR: Parent doesn't own specified children
        - DATABASE_ERROR: Database operation failed

    Example Request:
        {
            "childIds": ["123e4567-e89b-12d3-a456-426614174000"],
            "pickupPersonId": "223e4567-e89b-12d3-a456-426614174000",
            "scheduledTime": "2025-11-04T15:30:00-05:00",
            "notes": "Ramassage chez grand-maman"
        }

    Example Response:
        {
            "structuredContent": {
                "pickup_id": "323e4567-e89b-12d3-a456-426614174000",
                "children": ["123e4567-e89b-12d3-a456-426614174000"],
                "status": "confirmed",
                "scheduled_time": "2025-11-04T15:30:00-05:00"
            },
            "_meta": {
                "schools_affected": ["École Primaire Exemple"],
                "display_update": true
            }
        }

    Side Effects:
        - Creates pickup record in database
        - Sends A2A messages to affected schools
        - Triggers Supabase Realtime event
    """
```

---

## 10. Contract Quality Scorecard

```
╔════════════════════════════════════════════════════════════════╗
║                   MCP CONTRACT QUALITY SCORE                   ║
╠════════════════════════════════════════════════════════════════╣
║                                                                ║
║  Input Contracts:  100% ✅ (Excellent - Pydantic validated)    ║
║  Output Contracts:   0% ❌ (Critical - No validation)          ║
║  Error Contracts:   50% ⚠️ (Partial - Inconsistent format)     ║
║  Metadata:          80% ✅ (Good - Rich but unvalidated)       ║
║  Documentation:     60% ⚠️ (Fair - Missing output docs)        ║
║  Testing:            0% ❌ (None - No contract tests)          ║
║  Versioning:         0% ❌ (None - Breaking changes risky)     ║
║                                                                ║
║  ──────────────────────────────────────────────────────────  ║
║  OVERALL SCORE:     41% ⚠️ NEEDS SIGNIFICANT IMPROVEMENT       ║
║                                                                ║
╚════════════════════════════════════════════════════════════════╝
```

---

## 11. Critical Recommendations

### Immediate Actions (P0):

1. **Define Output Pydantic Models** for all 10 tools
   - Validate responses before returning
   - Document expected structure

2. **Standardize Error Response Format**
   - Add error codes (enum)
   - Structure error details
   - Make errors parseable

3. **Add Contract Tests**
   - Input validation tests
   - Output validation tests
   - Error format tests

4. **Document Output Schemas**
   - Add example responses
   - Document error cases

### Short-Term (P1):

5. Implement API versioning (semantic versioning)
6. Generate OpenAPI spec from Pydantic models
7. Add contract compatibility tests
8. Add output validation middleware

### Long-Term (P2):

9. Generate TypeScript types from Pydantic schemas
10. Implement GraphQL schema (optional alternative)
11. Add contract monitoring (detect breaking changes)
12. Build contract testing framework

---

## Conclusion

AllôBye's MCP contracts demonstrate **excellent input validation** (100% Pydantic coverage) but **critical gaps in output contracts** (0% validation). The system is well-designed for **preventing bad input** but offers **no guarantees about response structure**.

**Strengths**:
- ✅ Comprehensive Pydantic input models
- ✅ Rich OpenAI-specific metadata
- ✅ Clear tool descriptions
- ✅ Consistent error flags

**Weaknesses**:
- ❌ No output schema validation
- ❌ Inconsistent response structures
- ❌ No contract tests
- ❌ No API versioning
- ⚠️ Unstructured error responses

**Production Readiness**: ⚠️ **NOT READY**
- Block deployment until output contracts defined
- Estimated work: 3-4 days to add output models and tests

**Recommendation**: Implement output Pydantic models immediately. This is a **prerequisite for production** to ensure API stability and prevent silent breaking changes.
