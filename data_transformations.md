# Data Transformations Analysis - AllôBye System

**Date**: 2025-11-04
**Analyzer**: Traceur de Flux de Données
**Codebase**: AllôBye School Pickup Coordination System

---

## Executive Summary

This document traces all **data transformation pipelines** in the AllôBye system, from raw user input to final UI display. Each transformation stage is analyzed for:

- **Input Format** → **Transformation Logic** → **Output Format**
- **Data Validation** and **Schema Evolution**
- **Serialization/Deserialization** steps
- **Performance bottlenecks** and **optimization opportunities**

**Key Findings**:
- ✅ Strong input validation via Pydantic models (type safety)
- ⚠️ Multiple serialization hops (JSON → Python → DB → JSON → React)
- ✅ Clean separation between business logic and data mapping
- ⚠️ No explicit data versioning (schema changes could break compatibility)
- ⚠️ Inefficient N+1 queries in some pipelines

---

## 1. Auth Flow Transformations

### Pipeline 1.1: Signup Data Transformation

```
[User Input] → [React Form] → [MCP Tool] → [Supabase Auth] → [PostgreSQL] → [Response]
```

#### **Stage 1: User Input → React Form State**

**Source**: `/src/allobye-dashboard/auth-screen.jsx` (lines 16-22)

```javascript
// INPUT: User keyboard events
const [formData, setFormData] = useState({
  email: "",           // Raw string
  password: "",        // Raw string
  name: "",           // Raw string
  role: "parent",     // Enum: 'parent' | 'school_staff'
  confirmPassword: "" // Raw string
});
```

**Transformations**:
- **Sanitization**: None (vulnerability to XSS if displayed without escaping)
- **Validation**: Client-side only (lines 73-82)
  ```javascript
  if (formData.password !== formData.confirmPassword) {
    return "Les mots de passe ne correspondent pas";
  }
  if (formData.password.length < 6) {
    return "Le mot de passe doit contenir au moins 6 caractères";
  }
  ```

**Output**: JavaScript object

---

#### **Stage 2: React Form → MCP Tool Request**

**Source**: `auth-screen.jsx` (line 91-96)

```javascript
// TRANSFORMATION: Remove confirmPassword, add metadata
const result = await window.openai.callTool("auth-signup", {
  email: formData.email,      // No transformation
  password: formData.password, // No transformation (plain text!)
  name: formData.name,
  role: formData.role,
  // confirmPassword not sent (validated client-side only)
});
```

**Data Mapping**:
| React Field | MCP Parameter | Transformation |
|-------------|---------------|----------------|
| `email` | `email` | Identity |
| `password` | `password` | Identity (no hashing!) |
| `name` | `name` | Identity |
| `role` | `role` | Identity |
| `confirmPassword` | (omitted) | Dropped |

**Security Issue**: Password sent in plain text over HTTPS to MCP server.

**Protocol**: JSON-RPC over HTTP POST
```json
{
  "jsonrpc": "2.0",
  "method": "tools/call",
  "params": {
    "name": "auth-signup",
    "arguments": {
      "email": "user@example.com",
      "password": "plaintext123",
      "name": "John Doe",
      "role": "parent"
    }
  }
}
```

---

#### **Stage 3: MCP Tool → Pydantic Validation**

**Source**: `/allobye_server_python/main.py` (lines 213-239, 847)

```python
# INPUT: Dict[str, Any] from MCP request
try:
    payload = AuthSignupInput.model_validate(arguments)
except ValidationError as exc:
    return types.CallToolResult(
        content=[types.TextContent(type="text", text=f"Erreur: {exc.errors()}")],
        isError=True,
    )
```

**Validation Rules** (`AuthSignupInput`):
```python
class AuthSignupInput(BaseModel):
    email: str = Field(..., description="Email address")
    password: str = Field(..., min_length=6, description="Password (min 6)")
    name: Optional[str] = Field(None, description="Full name")
    role: str = Field("parent", description="Role: parent or school_staff")
    schools: Optional[List[str]] = Field(None, description="School IDs")

    model_config = ConfigDict(populate_by_name=True, extra="forbid")
```

**Transformations**:
- **Email validation**: Pydantic checks it's a valid email format
- **Password min length**: Enforced by `min_length=6`
- **Extra fields forbidden**: `extra="forbid"` rejects unknown keys
- **Optional fields**: `name` and `schools` can be None

**Output**: `AuthSignupInput` object (validated Pydantic model)

---

#### **Stage 4: Pydantic Model → Supabase Auth**

**Source**: `/allobye_server_python/auth.py` (lines 156-168)

```python
# TRANSFORMATION: Pydantic object → Supabase Auth dict
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
```

**Data Mapping**:
| Pydantic Field | Supabase Field | Location |
|----------------|----------------|----------|
| `email` | `email` | Top-level |
| `password` | `password` | Top-level (Supabase hashes) |
| `name` | `options.data.name` | User metadata |
| `role` | `options.data.role` | User metadata |

**Supabase Auth Processing**:
1. Hash password with bcrypt (Supabase internal)
2. Generate UUID for user
3. Create JWT access_token and refresh_token
4. Send verification email (if configured)

**Output**: Supabase Auth Response
```python
{
    "user": {
        "id": "uuid-v4",
        "email": "user@example.com",
        "email_confirmed_at": None,
        "created_at": "2025-11-04T12:00:00Z",
        "user_metadata": {"name": "John Doe", "role": "parent"}
    },
    "session": {
        "access_token": "eyJhbG...",  # JWT
        "refresh_token": "...",
        "expires_at": 1730728800
    }
}
```

---

#### **Stage 5: Supabase Response → PostgreSQL Insert**

**Source**: `auth.py` (lines 173-190)

```python
# TRANSFORMATION: Flatten Supabase response → DB record
profile_data = {
    "id": response.user.id,          # UUID from Supabase
    "email": email,                  # Original input
    "name": name,                    # Original input
    "role": role,                    # Original input
    "email_verified": False,         # Default
    "created_at": datetime.now().isoformat(),  # Server timestamp
}

supabase.table("user_profiles").insert(profile_data).execute()

# If school staff, create associations
if role == "school_staff" and schools:
    for school_id in schools:
        supabase.table("user_schools").insert({
            "user_id": response.user.id,
            "school_id": school_id,
        }).execute()
```

**Data Mapping**:
| Supabase Field | PostgreSQL Column | Transformation |
|----------------|-------------------|----------------|
| `response.user.id` | `user_profiles.id` | Identity (UUID) |
| `email` (input) | `user_profiles.email` | Identity |
| `name` (input) | `user_profiles.name` | Identity |
| `role` (input) | `user_profiles.role` | Identity |
| (computed) | `user_profiles.email_verified` | Default: False |
| `datetime.now()` | `user_profiles.created_at` | Server timestamp |

**Transaction Safety**: ⚠️ No explicit transaction! If `user_schools` insert fails, orphan `user_profiles` record exists.

---

#### **Stage 6: PostgreSQL → MCP Response**

**Source**: `main.py` (lines 863-879)

```python
# TRANSFORMATION: DB + Supabase → MCP CallToolResult
return types.CallToolResult(
    content=[
        types.TextContent(
            type="text",
            text=f"✓ Compte créé avec succès pour {payload.email}"
        )
    ],
    structuredContent={
        "user_id": result["user"]["id"],
        "email": result["user"]["email"],
        "email_verified": result["user"]["email_verified"],
    },
    _meta={
        "session": result["session"],
        "requires_verification": not result["user"]["email_verified"],
    },
)
```

**Transformation Logic**:
- **Human-readable text**: French success message
- **Structured data**: Machine-readable fields (user_id, email, verified)
- **Metadata**: Session tokens (access_token, refresh_token) in `_meta`

**Output**: MCP CallToolResult (JSON-serializable)

---

#### **Stage 7: MCP Response → React State**

**Source**: `auth-screen.jsx` (lines 99-116)

```javascript
// TRANSFORMATION: MCP result → localStorage + React state
if (result?._meta?.session?.access_token) {
  localStorage.setItem("allobye_token", result._meta.session.access_token);

  // Fetch full profile after signup
  const profileResult = await window.openai.callTool("auth-profile", {
    accessToken: result._meta.session.access_token,
  });

  if (profileResult?.structuredContent) {
    localStorage.setItem("allobye_user", JSON.stringify(profileResult.structuredContent));

    onAuthenticated({
      token: result._meta.session.access_token,
      user: profileResult.structuredContent,
    });
  }
}
```

**Data Mapping**:
| MCP Response | React State | Storage |
|--------------|-------------|---------|
| `_meta.session.access_token` | `authState.token` | localStorage |
| `structuredContent.*` | `authState.user` | localStorage (JSON) |
| (computed) | `authState.isAuthenticated` | React state |

**Serialization**: User profile serialized to JSON string for localStorage.

---

### Pipeline 1.2: Login JWT Validation

```
[JWT] → [Decode] → [Supabase Verify] → [DB Query] → [UserProfile Object]
```

#### **JWT Structure**

**Format**: `header.payload.signature` (base64url encoded)

```json
// Header
{
  "alg": "HS256",
  "typ": "JWT"
}

// Payload (claims)
{
  "sub": "uuid-v4",           // User ID
  "email": "user@example.com",
  "role": "authenticated",
  "aud": "authenticated",
  "exp": 1730728800,          // Expiration timestamp
  "iat": 1730725200,          // Issued at timestamp
  "user_metadata": {
    "name": "John Doe",
    "role": "parent"
  }
}

// Signature (HMAC-SHA256)
HMACSHA256(
  base64UrlEncode(header) + "." + base64UrlEncode(payload),
  SECRET_KEY
)
```

#### **Stage 1: JWT → Supabase Validation**

**Source**: `auth.py` (lines 410-413)

```python
# INPUT: JWT string from client
access_token = arguments.get("access_token")

# TRANSFORMATION: Decode and verify signature
supabase.auth.set_session(access_token, "")
response = supabase.auth.get_user(access_token)
```

**Supabase Processing**:
1. Decode JWT header and payload (base64url decode)
2. Verify signature with SECRET_KEY
3. Check expiration (`exp` claim > now)
4. Check audience (`aud` matches configured value)
5. Return user object from `sub` claim

**Error Cases**:
- Invalid signature → `SessionExpiredError`
- Expired token → `SessionExpiredError`
- Malformed JWT → `AuthenticationError`

---

#### **Stage 2: User Claims → Database Query**

**Source**: `auth.py` (lines 432-494)

```python
# INPUT: User ID from JWT claims
user_id = response.user.id

# TRANSFORMATION: Fetch full profile with associations
profile_response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()

# Fetch associated schools (if school staff)
if profile["role"] == "school_staff":
    schools_response = supabase.table("user_schools").select("school_id").eq("user_id", user_id).execute()
    schools = [s["school_id"] for s in schools_response.data]

# Fetch associated children (if parent)
if profile["role"] == "parent":
    children_response = supabase.table("parent_children").select("child_id").eq("parent_id", user_id).execute()
    children = [c["child_id"] for c in children_response.data]
```

**SQL Translation** (conceptual):
```sql
-- user_profiles query
SELECT * FROM user_profiles WHERE id = 'uuid-v4';

-- schools query (if school_staff)
SELECT school_id FROM user_schools WHERE user_id = 'uuid-v4';

-- children query (if parent)
SELECT child_id FROM parent_children WHERE parent_id = 'uuid-v4';
```

**N+1 Problem**: ⚠️ Three separate queries instead of one JOIN.

**Optimization**:
```sql
-- Single query with LEFT JOINs
SELECT
    p.*,
    ARRAY_AGG(DISTINCT us.school_id) AS schools,
    ARRAY_AGG(DISTINCT pc.child_id) AS children
FROM user_profiles p
LEFT JOIN user_schools us ON p.id = us.user_id
LEFT JOIN parent_children pc ON p.id = pc.parent_id
WHERE p.id = 'uuid-v4'
GROUP BY p.id;
```

---

#### **Stage 3: Database Rows → UserProfile Dataclass**

**Source**: `auth.py` (lines 484-493)

```python
# TRANSFORMATION: Dict → Dataclass
return {
    "id": profile["id"],
    "email": profile["email"],
    "name": profile.get("name"),
    "role": profile.get("role", "parent"),
    "schools": schools,                    # List[str]
    "children": children,                  # List[str]
    "email_verified": profile.get("email_verified", False),
    "created_at": profile.get("created_at"),
}
```

**Type Conversion**:
| Database Type | Python Type | Default |
|---------------|-------------|---------|
| `UUID` | `str` | N/A (required) |
| `TEXT` | `str` | N/A |
| `TEXT` | `Optional[str]` | `None` |
| `TEXT` | `str` | `"parent"` |
| `UUID[]` | `List[str]` | `[]` |
| `BOOLEAN` | `bool` | `False` |
| `TIMESTAMPTZ` | `str` (ISO 8601) | N/A |

---

## 2. Pickup Flow Transformations

### Pipeline 2.1: Pickup Creation

```
[ChatGPT NL] → [MCP Tool Args] → [DB Insert] → [Realtime Broadcast] → [React UI]
```

#### **Stage 1: Natural Language → Structured Arguments**

**Source**: ChatGPT reasoning (not visible in code)

**Example**:
```
User: "Schedule pickup for Sophie at 3pm today by grandma"
                    ↓
ChatGPT extracts:
  - child_name: "Sophie"
  - scheduled_time: "2025-11-04T15:00:00-05:00"
  - pickup_person: "grandma"
                    ↓
ChatGPT resolves IDs:
  - child_id: "uuid-child-1" (from conversation context)
  - pickup_person_id: "uuid-delegate-1" (from context)
                    ↓
MCP Tool Call:
{
  "childIds": ["uuid-child-1"],
  "pickupPersonId": "uuid-delegate-1",
  "scheduledTime": "2025-11-04T15:00:00-05:00",
  "notes": null
}
```

**Transformation Challenges**:
- **Ambiguity**: "3pm" needs timezone inference (America/Montreal)
- **Entity Resolution**: "Sophie" → child UUID (requires context)
- **Relative Time**: "today" → absolute ISO 8601 timestamp

---

#### **Stage 2: Tool Arguments → Pydantic Validation**

**Source**: `main.py` (lines 101-126, 1039)

```python
class PickupScheduleInput(BaseModel):
    child_ids: List[str] = Field(
        ...,
        alias="childIds",
        description="List of child IDs",
        min_length=1,
    )
    pickup_person_id: str = Field(..., alias="pickupPersonId")
    scheduled_time: str = Field(..., alias="scheduledTime")  # ISO 8601
    notes: Optional[str] = Field(None)

    model_config = ConfigDict(populate_by_name=True, extra="forbid")
```

**Validation**:
- `child_ids`: Non-empty list of strings
- `pickup_person_id`: Required string (UUID format not enforced!)
- `scheduled_time`: Required string (ISO 8601 format not validated!)
- `notes`: Optional string

**Missing Validation**:
- ⚠️ No UUID format check (could accept invalid UUIDs)
- ⚠️ No datetime parsing (could accept "not-a-date")
- ⚠️ No future date check (could schedule in the past)

**Improvement**:
```python
from datetime import datetime
from pydantic import field_validator
from uuid import UUID

class PickupScheduleInput(BaseModel):
    child_ids: List[UUID] = Field(..., min_length=1)  # Auto-validates UUID
    scheduled_time: datetime = Field(...)  # Auto-parses ISO 8601

    @field_validator('scheduled_time')
    def validate_future_date(cls, v):
        if v < datetime.now():
            raise ValueError('Scheduled time must be in the future')
        return v
```

---

#### **Stage 3: Pydantic Model → Authorization Check**

**Source**: `main.py` (lines 1052-1062)

```python
# TRANSFORMATION: Child IDs → Parent ownership verification
for child_id in payload.child_ids:
    if not await verify_parent_owns_child(user.id, child_id):
        return error_response()

# Database query inside verify_parent_owns_child:
# SELECT id FROM parent_children
# WHERE parent_id = 'user-uuid' AND child_id = 'child-uuid'
```

**Data Flow**:
```
payload.child_ids (List[str])
         ↓
For each child_id:
         ↓
Query: parent_children.select("id").eq("parent_id", user.id).eq("child_id", child_id)
         ↓
Result: {data: [{id: "..."}]} or {data: []}
         ↓
Transform: len(data) > 0 → True/False
```

**Performance Issue**: ⚠️ N+1 query (one query per child)

**Optimization**:
```python
# Single query with IN clause
owned_children = await get_owned_children(user.id, payload.child_ids)
if set(owned_children) != set(payload.child_ids):
    return error_response("Not authorized for all children")
```

---

#### **Stage 4: Validated Data → School Lookup**

**Source**: `main.py` (lines 1065, 399-423)

```python
# INPUT: List of child UUIDs
schools = await get_schools_for_children(payload.child_ids)

# TRANSFORMATION: Children → Schools (via JOIN)
response = supabase.table("children").select("school_id, schools(*)").in_("id", child_ids).execute()

# Extract unique schools
schools = {}
for child in response.data:
    if child.get("schools"):
        school = child["schools"]
        schools[school["id"]] = school

return list(schools.values())
```

**SQL Translation**:
```sql
SELECT
    c.school_id,
    s.id, s.name, s.address, s.phone, s.email, s.timezone
FROM children c
JOIN schools s ON c.school_id = s.id
WHERE c.id IN ('child-1', 'child-2', ...)
```

**Data Transformation**:
```python
# Database rows (denormalized with duplicates if multiple children at same school)
[
    {
        "id": "child-1",
        "school_id": "school-A",
        "schools": {"id": "school-A", "name": "École Primaire A", ...}
    },
    {
        "id": "child-2",
        "school_id": "school-A",  # Duplicate school
        "schools": {"id": "school-A", "name": "École Primaire A", ...}
    }
]
                    ↓ (Deduplication by school["id"])
# Unique schools
[
    {"id": "school-A", "name": "École Primaire A", ...}
]
```

---

#### **Stage 5: Pickup Data → Database Insert**

**Source**: `main.py` (lines 426-472)

```python
# TRANSFORMATION: Validated input → Database records
pickup_id = str(uuid4())  # Generate new UUID

pickup_data = {
    "id": pickup_id,
    "pickup_person_id": pickup_person_id,
    "scheduled_time": scheduled_time,  # ISO 8601 string
    "status": "confirmed",             # Hardcoded initial state
    "notes": notes,
}

# Insert pickup record
response = supabase.table("pickups").insert(pickup_data).execute()

# Insert pickup-children associations
for child_id in child_ids:
    supabase.table("pickup_children").insert({
        "pickup_id": pickup_id,
        "child_id": child_id,
    }).execute()
```

**PostgreSQL Storage**:
```sql
-- pickups table
INSERT INTO pickups (id, pickup_person_id, scheduled_time, status, notes)
VALUES (
    'uuid-pickup',
    'uuid-delegate',
    '2025-11-04 15:00:00-05:00'::timestamptz,
    'confirmed',
    NULL
);

-- pickup_children junction table (one row per child)
INSERT INTO pickup_children (pickup_id, child_id, checked_out)
VALUES
    ('uuid-pickup', 'uuid-child-1', FALSE),
    ('uuid-pickup', 'uuid-child-2', FALSE);
```

**Data Type Transformations**:
| Python Type | PostgreSQL Type | Conversion |
|-------------|-----------------|------------|
| `str` (UUID) | `UUID` | Supabase SDK parses |
| `str` (ISO 8601) | `TIMESTAMPTZ` | PostgreSQL parses |
| `str` ("confirmed") | `TEXT` | Identity |
| `Optional[str]` | `TEXT` | NULL if None |

**Trigger Activation**:
```sql
-- After INSERT on pickups
TRIGGER update_pickups_updated_at
  → SET updated_at = NOW()
```

---

#### **Stage 6: Database Event → Realtime Broadcast**

**Source**: PostgreSQL Logical Replication

**Data Flow**:
```
INSERT INTO pickups
        ↓
PostgreSQL writes to WAL (Write-Ahead Log)
        ↓
Supabase Realtime reads WAL changes
        ↓
Filter by table: "pickups"
        ↓
Filter by RLS: Check if subscriber can see row
        ↓
Serialize row to JSON
        ↓
Push via WebSocket to subscribers
```

**Realtime Payload**:
```javascript
{
  "schema": "public",
  "table": "pickups",
  "commit_timestamp": "2025-11-04T15:00:01Z",
  "eventType": "INSERT",
  "new": {
    "id": "uuid-pickup",
    "pickup_person_id": "uuid-delegate",
    "scheduled_time": "2025-11-04T15:00:00-05:00",
    "status": "confirmed",
    "notes": null,
    "created_at": "2025-11-04T15:00:00Z",
    "updated_at": "2025-11-04T15:00:00Z"
  },
  "old": null  // No old value for INSERT
}
```

---

#### **Stage 7: WebSocket → React State Update**

**Source**: `dashboard.jsx` (lines 84-94)

```javascript
.on("postgres_changes", (payload) => {
  console.log("Pickup change received:", payload);

  if (payload.eventType === "INSERT" || payload.eventType === "UPDATE") {
    setRealtimePickups((prev) => {
      // Remove duplicate if UPDATE (by pickup.id)
      const updated = prev.filter((p) => p.id !== payload.new.id);

      // Add new version and sort by scheduled_time
      return [...updated, payload.new].sort(
        (a, b) => new Date(a.scheduled_time) - new Date(b.scheduled_time)
      );
    });
  }
});
```

**Transformation**:
```
payload.new (Database row format)
        ↓
Merge with prev (array of pickups)
        ↓
Sort by scheduled_time (ascending)
        ↓
setRealtimePickups([...])
        ↓
React re-renders PickupCard components
```

**Data Enrichment** (happens during render):
```javascript
// Calculate ETA
const scheduledTime = new Date(pickup.scheduled_time);
const now = currentTime;
const diffMinutes = Math.round((scheduledTime - now) / 60000);

// Transform to display format
const eta = diffMinutes > 0 ? `${diffMinutes} min` : "En retard";
const delay = pickup.delay_minutes || 0;
```

---

### Pipeline 2.2: Multi-School Coordination (A2A Simulation)

**Source**: `main.py` (lines 475-496)

```python
async def coordinate_cross_school_pickup(child_ids, pickup_person_id, scheduled_time, notes):
    # Stage 1: Get affected schools
    schools = await get_schools_for_children(child_ids)

    # Stage 2: Create unified pickup
    pickup = await create_pickup_request(child_ids, pickup_person_id, scheduled_time, notes)

    # Stage 3: Simulate A2A broadcast
    pickup["schools_affected"] = [s["name"] for s in schools]
    pickup["a2a_messages"] = [
        {"school_id": s["id"], "status": "confirmed"} for s in schools
    ]

    return pickup
```

**Data Transformation**:
```
Input: child_ids = ["child-A", "child-B"]
                    ↓
Step 1: Get schools
        ↓
children.select("school_id, schools(*)").in_("id", child_ids)
                    ↓
Result: [
  {school_id: "school-X", schools: {id: "X", name: "École X"}},
  {school_id: "school-Y", schools: {id: "Y", name: "École Y"}}
]
                    ↓
Step 2: Deduplicate schools
                    ↓
schools = [
  {id: "school-X", name: "École X"},
  {id: "school-Y", name: "École Y"}
]
                    ↓
Step 3: Create pickup (single DB record)
                    ↓
pickups.insert({pickup_person_id, scheduled_time, status: "confirmed"})
pickup_children.insert([
  {pickup_id, child_id: "child-A"},
  {pickup_id, child_id: "child-B"}
])
                    ↓
Step 4: Augment with A2A metadata
                    ↓
pickup["schools_affected"] = ["École X", "École Y"]
pickup["a2a_messages"] = [
  {school_id: "school-X", status: "confirmed"},
  {school_id: "school-Y", status: "confirmed"}
]
                    ↓
Return enriched pickup object
```

**A2A Message Format** (simulated):
```python
{
    "type": "pickup_request",
    "pickup_id": "uuid-pickup",
    "school_id": "school-X",
    "child_ids": ["child-A"],
    "scheduled_time": "2025-11-04T15:00:00-05:00",
    "pickup_person": {
        "id": "delegate-uuid",
        "name": "Grand-maman",
        "email": "grandma@example.com"
    },
    "status": "confirmed",
    "timestamp": "2025-11-04T14:30:00Z"
}
```

**Note**: This is **simulated** in current implementation. Real A2A would use message bus (RabbitMQ, Kafka, etc.).

---

## 3. Emergency Flow Transformations

### Pipeline 3.1: Emergency Declaration

```
[ChatGPT NL] → [MCP Tool] → [DB Insert] → [TRIGGER] → [pg_notify] → [WebSocket] → [React Alert]
```

#### **Stage 1: Natural Language → Emergency Data**

**Example**:
```
User: "Emergency! Sophie is sick, I need to cancel pickup"
                    ↓
ChatGPT extracts:
  - child: "Sophie" → child_id: "uuid-child"
  - emergency_type: "illness"
  - context: "Sophie is sick, need to cancel pickup"
  - severity: "medium" (inferred)
                    ↓
MCP Tool Call:
{
  "childId": "uuid-child",
  "emergencyType": "illness",
  "context": "Sophie is sick, need to cancel pickup",
  "notifyAllDelegates": true
}
```

---

#### **Stage 2: Tool Args → Database Insert**

**Source**: `main.py` (lines 565-609)

```python
# TRANSFORMATION: Input → Database record
emergency_id = str(uuid4())

emergency_data = {
    "id": emergency_id,
    "child_id": child_id,
    "emergency_type": emergency_type,  # 'late', 'illness', 'cancel', 'injury', 'other'
    "context": context,
    "created_at": datetime.now().isoformat(),
}

supabase.table("emergencies").insert(emergency_data).execute()
```

**PostgreSQL Insert**:
```sql
INSERT INTO emergencies (id, child_id, emergency_type, context, severity, resolved, created_at)
VALUES (
    'uuid-emergency',
    'uuid-child',
    'illness',
    'Sophie is sick, need to cancel pickup',
    'medium',  -- Default from schema
    FALSE,     -- Default
    '2025-11-04 14:30:00+00:00'::timestamptz
);
```

---

#### **Stage 3: Database Trigger → pg_notify**

**Source**: `schema.sql` (lines 196-231)

```sql
CREATE FUNCTION notify_emergency() RETURNS TRIGGER AS $$
DECLARE
    school_id UUID;
    school_name TEXT;
BEGIN
    -- Stage 1: Get school information
    SELECT c.school_id, s.name INTO school_id, school_name
    FROM children c
    JOIN schools s ON c.school_id = s.id
    WHERE c.id = NEW.child_id;

    -- Stage 2: Build JSON payload
    PERFORM pg_notify(
        'emergency_alert',
        json_build_object(
            'emergency_id', NEW.id,
            'child_id', NEW.child_id,
            'school_id', school_id,
            'school_name', school_name,
            'type', NEW.emergency_type,
            'severity', NEW.severity,
            'context', NEW.context,
            'created_at', NEW.created_at
        )::text
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER emergency_notification
    AFTER INSERT ON emergencies
    FOR EACH ROW
    EXECUTE FUNCTION notify_emergency();
```

**Data Transformation**:
```
INSERT INTO emergencies (NEW row)
        ↓
TRIGGER: notify_emergency() executes
        ↓
Step 1: JOIN children + schools to get school info
        ↓
SELECT c.school_id, s.name
FROM children c JOIN schools s ON c.school_id = s.id
WHERE c.id = NEW.child_id
        ↓
Result: {school_id: "school-X", school_name: "École X"}
        ↓
Step 2: Build JSON notification payload
        ↓
json_build_object(
    'emergency_id', 'uuid-emergency',
    'child_id', 'uuid-child',
    'school_id', 'uuid-school',
    'school_name', 'École X',
    'type', 'illness',
    'severity', 'medium',
    'context', 'Sophie is sick...',
    'created_at', '2025-11-04T14:30:00Z'
)
        ↓
Step 3: Serialize to TEXT
        ↓
'{"emergency_id":"uuid-emergency","child_id":"uuid-child",...}'
        ↓
Step 4: pg_notify('emergency_alert', payload)
        ↓
PostgreSQL broadcasts to all LISTEN subscribers
```

---

#### **Stage 4: pg_notify → Supabase Realtime → WebSocket**

**Data Flow**:
```
pg_notify('emergency_alert', json_payload)
        ↓
PostgreSQL NOTIFY mechanism (in-memory broadcast)
        ↓
Supabase Realtime server (LISTEN 'emergency_alert')
        ↓
Filter by RLS (check if subscriber can see this emergency)
        ↓
Push to WebSocket subscribers on "emergencies-changes" channel
        ↓
WebSocket message:
{
  "schema": "public",
  "table": "emergencies",
  "eventType": "INSERT",
  "new": {
    "id": "uuid-emergency",
    "child_id": "uuid-child",
    "emergency_type": "illness",
    "context": "Sophie is sick...",
    "severity": "medium",
    ...
  }
}
```

---

#### **Stage 5: WebSocket → React Alert State**

**Source**: `dashboard.jsx` (lines 103-129)

```javascript
.on("postgres_changes", {
  event: "INSERT",
  schema: "public",
  table: "emergencies",
}, (payload) => {
  console.log("Emergency received:", payload);

  // TRANSFORMATION: DB row → Alert state
  setState({
    ...state,
    alert: {
      type: payload.new.emergency_type,
      context: payload.new.context,
      child_id: payload.new.child_id,
    },
  });

  // Auto-clear after 30 seconds
  setTimeout(() => {
    setState({ ...state, alert: null });
  }, 30000);
});
```

**Data Mapping**:
| WebSocket Payload | React Alert State |
|-------------------|-------------------|
| `payload.new.emergency_type` | `alert.type` |
| `payload.new.context` | `alert.context` |
| `payload.new.child_id` | `alert.child_id` |

**UI Rendering**:
```javascript
{state.alert && (
  <EmergencyAlert
    alert={state.alert}
    onClose={() => setState({ ...state, alert: null })}
  />
)}
```

**EmergencyAlert Component** transforms data for display:
```javascript
// emergency-alert.jsx
const alertIcons = {
  late: "⏰",
  illness: "🤒",
  cancel: "❌",
  injury: "🚑",
  other: "⚠️",
};

const icon = alertIcons[alert.type] || "⚠️";
const message = alert.context;
```

---

## 4. Monitoring Flow Transformations

### Pipeline 4.1: Metrics Collection

```
[Tool Call] → [Monitoring Middleware] → [MetricsCollector] → [Prometheus Export]
```

#### **Stage 1: Tool Execution → Metrics Recording**

**Source**: `main.py` (lines 1392-1449)

```python
async def _call_tool_request_monitored(req: types.CallToolRequest):
    tool_name = req.params.name
    start_time = time.time()
    success = False
    error_msg = None

    try:
        # Execute tool handler
        result = await handler(arguments)
        success = True
        return types.ServerResult(result)
    except Exception as e:
        error_msg = str(e)
        raise
    finally:
        # TRANSFORMATION: Execution data → Metrics
        latency_ms = (time.time() - start_time) * 1000
        metrics_collector.record_tool_call(tool_name, latency_ms, success, error_msg)
```

**Data Captured**:
- `tool_name`: String (e.g., "pickup-schedule-create")
- `latency_ms`: Float (execution time in milliseconds)
- `success`: Boolean
- `error_msg`: Optional[String]

---

#### **Stage 2: Raw Metrics → Aggregated Metrics**

**Source**: `monitoring.py` (lines 222-263)

```python
def record_tool_call(self, tool_name, latency_ms, success, error):
    # TRANSFORMATION: Event → Counters
    metrics = self.tool_metrics[tool_name]  # defaultdict(ToolMetrics)

    metrics.call_count += 1
    metrics.success_count += 1 if success else 0
    metrics.error_count += 1 if not success else 0
    metrics.total_latency_ms += latency_ms
    metrics.min_latency_ms = min(metrics.min_latency_ms, latency_ms)
    metrics.max_latency_ms = max(metrics.max_latency_ms, latency_ms)

    # TRANSFORMATION: Event → Recent history
    self.recent_requests.append({
        "timestamp": datetime.utcnow().isoformat(),
        "tool": tool_name,
        "latency_ms": latency_ms,
        "success": success,
        "error": error,
    })

    # Keep only last 100 requests
    if len(self.recent_requests) > 100:
        self.recent_requests = self.recent_requests[-100:]
```

**ToolMetrics Dataclass**:
```python
@dataclass
class ToolMetrics:
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        # COMPUTED METRIC
        return self.total_latency_ms / self.call_count if self.call_count > 0 else 0.0

    @property
    def error_rate(self) -> float:
        # COMPUTED METRIC
        return self.error_count / self.call_count if self.call_count > 0 else 0.0
```

---

#### **Stage 3: Aggregated Metrics → Dashboard Data**

**Source**: `monitoring.py` (lines 446-478)

```python
def get_dashboard_data(self) -> Dict[str, Any]:
    return {
        # System metrics
        "uptime_seconds": self.get_uptime_seconds(),
        "total_requests": self.total_requests,
        "active_connections": self.active_connections,

        # Computed overall metrics
        "overall_error_rate": self.get_overall_error_rate(),
        "overall_avg_latency_ms": self.get_overall_avg_latency_ms(),

        # Top tools by call count
        "top_tools": self.get_top_tools(limit=10),

        # Recent history
        "recent_errors": self.recent_errors[-20:],
        "recent_requests": self.recent_requests[-50:],
        "alerts": self.get_alerts(),

        # Database metrics
        "database": {
            "query_count": self.db_metrics.query_count,
            "error_count": self.db_metrics.error_count,
            "avg_latency_ms": self.db_metrics.avg_latency_ms,
            "error_rate": self.db_metrics.error_rate,
            "consecutive_failures": self.db_metrics.consecutive_failures,
        },

        # Per-tool details
        "tool_details": {
            name: {
                "call_count": metrics.call_count,
                "success_count": metrics.success_count,
                "error_count": metrics.error_count,
                "avg_latency_ms": metrics.avg_latency_ms,
                "min_latency_ms": metrics.min_latency_ms,
                "max_latency_ms": metrics.max_latency_ms,
                "error_rate": metrics.error_rate,
                "success_rate": metrics.success_rate,
            }
            for name, metrics in self.tool_metrics.items()
        },
    }
```

---

#### **Stage 4: Dashboard Data → Prometheus Format**

**Source**: `monitoring.py` (lines 388-444)

```python
def export_prometheus(self) -> str:
    lines = []

    # TRANSFORMATION: Python metrics → Prometheus text format

    # Uptime gauge
    lines.append("# HELP allobye_uptime_seconds Server uptime")
    lines.append("# TYPE allobye_uptime_seconds gauge")
    lines.append(f"allobye_uptime_seconds {self.get_uptime_seconds():.2f}")

    # Per-tool metrics
    for tool_name, metrics in self.tool_metrics.items():
        # Call count counter
        lines.append(f'# TYPE allobye_tool_calls_total counter')
        lines.append(f'allobye_tool_calls_total{{tool="{tool_name}"}} {metrics.call_count}')

        # Success count counter
        lines.append(f'allobye_tool_success_total{{tool="{tool_name}"}} {metrics.success_count}')

        # Error count counter
        lines.append(f'allobye_tool_errors_total{{tool="{tool_name}"}} {metrics.error_count}')

        # Average latency gauge
        lines.append(f'allobye_tool_latency_ms{{tool="{tool_name}"}} {metrics.avg_latency_ms:.2f}')

    return "\n".join(lines) + "\n"
```

**Example Output**:
```
# HELP allobye_uptime_seconds Server uptime
# TYPE allobye_uptime_seconds gauge
allobye_uptime_seconds 3600.00

# TYPE allobye_tool_calls_total counter
allobye_tool_calls_total{tool="pickup-schedule-create"} 42
allobye_tool_success_total{tool="pickup-schedule-create"} 40
allobye_tool_errors_total{tool="pickup-schedule-create"} 2
allobye_tool_latency_ms{tool="pickup-schedule-create"} 245.50
```

---

## 5. Data Serialization Analysis

### 5.1 JSON Serialization Hops

**Complete Path from User Input to UI Display**:

```
1. [Browser] User types in form
         ↓ (JavaScript in-memory object)
2. [React] formData state object
         ↓ (JSON.stringify → HTTP POST)
3. [Network] JSON string in HTTP request body
         ↓ (JSON.parse → MCP protocol)
4. [MCP Server] Python dict
         ↓ (Pydantic validation)
5. [MCP Server] Pydantic model (typed object)
         ↓ (model.dict())
6. [MCP Server] Python dict
         ↓ (Supabase SDK JSON encode)
7. [Network] JSON string to PostgreSQL
         ↓ (PostgreSQL JSON parsing)
8. [PostgreSQL] Internal row format (binary)
         ↓ (PostgreSQL JSON encode)
9. [Network] JSON string from PostgreSQL
         ↓ (Supabase SDK JSON decode)
10. [MCP Server] Python dict
         ↓ (types.CallToolResult → JSON)
11. [Network] JSON string in HTTP response
         ↓ (JSON.parse in ChatGPT SDK)
12. [ChatGPT] JavaScript object
         ↓ (window.openai.setGlobals)
13. [React] useState/useOpenAiGlobal
         ↓ (JSX rendering)
14. [Browser] DOM elements
```

**Total Serialization Hops**: 6 (encode) + 5 (decode) = **11 transformations**

**Performance Impact**:
- Each serialization/deserialization adds ~0.1-1ms latency
- Cumulative overhead: ~1-10ms per request
- JSON parsing is CPU-intensive (especially for large arrays)

---

### 5.2 Data Size Growth

**Example**: Pickup with 2 children

**Stage 1 (User Input)**: 150 bytes
```json
{
  "childIds": ["550e8400-e29b-41d4-a716-446655440000", "550e8400-e29b-41d4-a716-446655440001"],
  "pickupPersonId": "650e8400-e29b-41d4-a716-446655440000",
  "scheduledTime": "2025-11-04T15:00:00-05:00",
  "notes": null
}
```

**Stage 2 (After School Lookup)**: 450 bytes
```json
{
  "id": "750e8400-e29b-41d4-a716-446655440000",
  "child_ids": ["550e8400-...", "550e8400-..."],
  "pickup_person_id": "650e8400-...",
  "scheduled_time": "2025-11-04T15:00:00-05:00",
  "status": "confirmed",
  "notes": null,
  "schools_affected": ["École Primaire Exemple"],
  "a2a_messages": [
    {"school_id": "school-1", "status": "confirmed"}
  ],
  "created_at": "2025-11-04T14:30:00Z",
  "updated_at": "2025-11-04T14:30:00Z"
}
```

**Stage 3 (Dashboard with Full Data)**: 850 bytes
```json
{
  "id": "750e8400-...",
  "children": [
    {
      "id": "550e8400-...",
      "name": "Sophie Tremblay",
      "grade": "3e année",
      "parent_name": "Jean Tremblay"
    },
    {
      "id": "550e8400-...",
      "name": "Thomas Gagnon",
      "grade": "4e année",
      "parent_name": "Marie Gagnon"
    }
  ],
  "pickup_person": {
    "id": "650e8400-...",
    "name": "Grand-maman Tremblay",
    "email": "grandma@example.com",
    "phone": "+1-514-555-0123"
  },
  "scheduled_time": "2025-11-04T15:00:00-05:00",
  "status": "confirmed",
  "notes": null,
  "eta": "25 min",
  "delay": 0,
  "created_at": "2025-11-04T14:30:00Z",
  "updated_at": "2025-11-04T14:30:00Z"
}
```

**Data Growth**: 150 bytes → 850 bytes (**5.7x expansion**)

**Why**:
- Initial request: Minimal (just IDs)
- Intermediate: Metadata added (status, timestamps)
- Final: Full denormalized data (child names, pickup person details)

---

## 6. Performance Bottlenecks

### 6.1 N+1 Query Problems

**Issue 1**: `verify_parent_owns_child()` called in loop

```python
for child_id in payload.child_ids:
    if not await verify_parent_owns_child(user.id, child_id):
        return error_response()
```

**Queries Executed**:
- 1 child: 1 query
- 2 children: 2 queries
- 10 children: 10 queries

**Fix**: Batch query
```python
owned_child_ids = await get_owned_child_ids(user.id)
if not all(cid in owned_child_ids for cid in payload.child_ids):
    return error_response()
```

---

**Issue 2**: User profile fetching

```python
# Query 1: Get profile
profile = supabase.table("user_profiles").select("*").eq("id", user_id).execute()

# Query 2: Get schools (if school_staff)
schools = supabase.table("user_schools").select("school_id").eq("user_id", user_id).execute()

# Query 3: Get children (if parent)
children = supabase.table("parent_children").select("child_id").eq("parent_id", user_id).execute()
```

**Fix**: Single JOIN query (see earlier recommendation)

---

### 6.2 Large Array Serialization

**Issue**: School dashboard returns all pickups for the day

```python
pickups = await get_school_pickups(school_id, date, "today")
# Could return 100+ pickup records
```

**Each pickup includes**:
- Pickup metadata: ~200 bytes
- 2-5 children per pickup: ~400 bytes
- Pickup person details: ~150 bytes
- Total per pickup: ~750 bytes

**100 pickups** = **75 KB JSON payload**

**Optimization**:
1. Paginate results (limit to 20 per page)
2. Only return next 30 minutes by default
3. Compress HTTP response (gzip)
4. Use binary format (Protocol Buffers) instead of JSON

---

## 7. Recommendations

### 7.1 High Priority

1. **Batch Authorization Queries**: Eliminate N+1 in `verify_parent_owns_child()`
2. **Add UUID Validation**: Use `UUID` type in Pydantic models
3. **Add DateTime Parsing**: Use `datetime` type instead of `str` for timestamps
4. **Fix Realtime Merge Logic**: Timestamp-based conflict resolution

### 7.2 Medium Priority

5. **Optimize User Profile Fetching**: Single JOIN query instead of 3 separate queries
6. **Add Request Compression**: Enable gzip for large JSON payloads
7. **Paginate Dashboard Data**: Limit pickup results to reduce payload size
8. **Add Schema Versioning**: Include version field in JSON responses

### 7.3 Low Priority

9. **Memoize School Lookups**: Cache school data (rarely changes)
10. **Use GraphQL**: More efficient than REST for nested data fetching
11. **Implement Protobuf**: Binary serialization for performance-critical paths
12. **Add Data Sanitization**: Escape HTML/JavaScript in user-provided strings

---

## Conclusion

AllôBye's data transformation pipelines are **well-structured** with strong type safety (Pydantic) and clear boundaries. However, **multiple serialization hops** and **N+1 query patterns** introduce performance overhead. The **lack of explicit datetime/UUID validation** in Pydantic models is a correctness concern. Addressing the **N+1 queries** and **batching authorization checks** would yield the most significant performance improvements.
