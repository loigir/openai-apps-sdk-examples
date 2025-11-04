# Security Recommendations - AllôBye

**Date**: 2025-11-04
**System**: AllôBye School Pickup Coordination System
**Audience**: Development Team, Security Team, CTO

---

## Executive Summary

This document provides **actionable security recommendations** to address the 26 vulnerabilities identified in AllôBye. Recommendations are prioritized by severity and organized into a phased implementation plan.

**Timeline**:
- **Phase 1** (CRITICAL - 1-2 days): Data encryption, XSS fixes, auth architecture
- **Phase 2** (HIGH - 1-2 weeks): Rate limiting, headers, secret management
- **Phase 3** (MEDIUM - 2-4 weeks): CSRF, audit logging, error handling
- **Phase 4** (LOW - 4+ weeks): UX improvements, validation refinements

**Estimated Total Effort**: 3-4 developer weeks

---

## Phase 1: CRITICAL Fixes (1-2 Days)

### 1.1 Encrypt Medical Information (VULN-001)

**Priority**: P0 - CRITICAL
**Effort**: 1 day
**Complexity**: High

#### Implementation Plan:

**Step 1: Enable PostgreSQL Encryption Extension**
```sql
-- Run as superuser
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

**Step 2: Create Encryption Functions**
```sql
-- Encryption key stored in environment variable
CREATE FUNCTION encrypt_field(plaintext TEXT) RETURNS BYTEA AS $$
DECLARE
    encryption_key TEXT := current_setting('app.encryption_key');
BEGIN
    RETURN pgp_sym_encrypt(plaintext, encryption_key);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE FUNCTION decrypt_field(ciphertext BYTEA) RETURNS TEXT AS $$
DECLARE
    encryption_key TEXT := current_setting('app.encryption_key');
BEGIN
    RETURN pgp_sym_decrypt(ciphertext, encryption_key);
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
```

**Step 3: Migrate Schema**
```sql
-- Add new encrypted column
ALTER TABLE children
ADD COLUMN medical_info_encrypted BYTEA;

-- Encrypt existing data
UPDATE children
SET medical_info_encrypted = encrypt_field(medical_info)
WHERE medical_info IS NOT NULL;

-- Drop old column (after verification)
ALTER TABLE children DROP COLUMN medical_info;

-- Rename new column
ALTER TABLE children RENAME COLUMN medical_info_encrypted TO medical_info;
```

**Step 4: Update Application Code**
```python
# auth.py or new encryption.py module
import os
from cryptography.fernet import Fernet

class FieldEncryption:
    def __init__(self):
        self.key = os.getenv("FIELD_ENCRYPTION_KEY").encode()
        self.cipher = Fernet(self.key)

    def encrypt(self, plaintext: str) -> bytes:
        if not plaintext:
            return None
        return self.cipher.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        if not ciphertext:
            return None
        return self.cipher.decrypt(ciphertext).decode()

encryption = FieldEncryption()

# When reading from DB
medical_info = encryption.decrypt(child_record.medical_info)

# When writing to DB
encrypted_medical_info = encryption.encrypt(user_input.medical_info)
```

**Step 5: Key Management**
```bash
# Generate encryption key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Store in AWS Secrets Manager
aws secretsmanager create-secret \
    --name allobye/field-encryption-key \
    --secret-string "$(generated_key)"
```

**Step 6: Update RLS Policies**
```sql
-- RLS policies work on encrypted data automatically
-- No changes needed if using server-side decryption
```

**Testing**:
1. Write encrypted data to test child record
2. Verify decryption returns original value
3. Verify database shows encrypted bytes (not plaintext)
4. Test RLS policies still work correctly

**Rollback Plan**:
- Keep old `medical_info` column for 30 days
- Allow rollback to plaintext if encryption issues found

---

### 1.2 Fix XSS in React Widgets (VULN-002, VULN-003)

**Priority**: P0 - CRITICAL
**Effort**: 4 hours
**Complexity**: Medium

#### Implementation Plan:

**Step 1: Install Sanitization Library**
```bash
cd src/allobye-dashboard
npm install dompurify
npm install --save-dev @types/dompurify
```

**Step 2: Create Sanitization Utility**
```javascript
// src/allobye-dashboard/utils/sanitize.js
import DOMPurify from 'dompurify';

/**
 * Sanitize user-generated content to prevent XSS
 */
export function sanitizeHTML(dirty) {
  if (!dirty) return '';

  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'p', 'br'],
    ALLOWED_ATTR: [],
    KEEP_CONTENT: true,
  });
}

/**
 * Sanitize text to plain text only (most secure)
 */
export function sanitizeText(dirty) {
  if (!dirty) return '';

  // Strip ALL HTML tags
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: [],
    KEEP_CONTENT: true,
  });
}
```

**Step 3: Update pickup-card.jsx**
```javascript
import { sanitizeText } from './utils/sanitize';

export default function PickupCard({ pickup, currentTime }) {
  // ... existing code ...

  return (
    <div className={`pickup-card status-${getStatusColor()}`}>
      {/* ... */}

      <div className="pickup-details">
        <div className="child-info">
          {/* SANITIZED: Child name */}
          <div className="child-name">
            {sanitizeText(pickup.child?.name) || "Enfant inconnu"}
          </div>
          {/* SANITIZED: Grade */}
          {pickup.child?.grade && (
            <div className="child-grade">{sanitizeText(pickup.child.grade)}</div>
          )}
        </div>

        <div className="pickup-person-info">
          <div className="person-icon">👤</div>
          {/* SANITIZED: Delegate name */}
          <div className="person-name">
            {sanitizeText(pickup.pickup_person?.name) || "Personne inconnue"}
          </div>
        </div>

        {/* SANITIZED: Notes */}
        {pickup.notes && (
          <div className="pickup-notes">
            <span className="notes-icon">📝</span>
            {sanitizeText(pickup.notes)}
          </div>
        )}
      </div>
    </div>
  );
}
```

**Step 4: Update emergency-alert.jsx**
```javascript
import { sanitizeText } from './utils/sanitize';

export default function EmergencyAlert({ alert, onClose }) {
  return (
    <div className={`emergency-alert type-${alert.type}`}>
      <div className="alert-icon">{getEmergencyIcon(alert.type)}</div>
      <div className="alert-content">
        <div className="alert-title">{getEmergencyTitle(alert.type)}</div>
        {/* SANITIZED: Emergency context */}
        <div className="alert-context">
          {sanitizeText(alert.context)}
        </div>
      </div>
      <button className="alert-close" onClick={onClose}>×</button>
    </div>
  );
}
```

**Step 5: Add Backend Validation**
```python
# main.py - Add sanitization on input
import html

class PickupScheduleInput(BaseModel):
    notes: Optional[str] = Field(None, max_length=500)

    @field_validator('notes')
    def sanitize_notes(cls, v):
        if v:
            # Escape HTML entities
            v = html.escape(v)
            # Limit length
            v = v[:500]
        return v

class EmergencyDeclareInput(BaseModel):
    context: str = Field(..., max_length=1000)

    @field_validator('context')
    def sanitize_context(cls, v):
        # Escape HTML entities
        return html.escape(v[:1000])
```

**Testing**:
```javascript
// Test payloads
const xssPayloads = [
  "<script>alert('XSS')</script>",
  "<img src=x onerror=alert('XSS')>",
  "<iframe src='https://evil.com'>",
  "javascript:alert('XSS')",
  "<svg onload=alert('XSS')>",
];

// Verify all payloads are sanitized
xssPayloads.forEach(payload => {
  const sanitized = sanitizeText(payload);
  assert(!sanitized.includes('<'), "HTML tags should be removed");
  assert(!sanitized.includes('javascript:'), "JS protocol should be removed");
});
```

---

### 1.3 Fix Service Role Key Usage (VULN-004)

**Priority**: P0 - CRITICAL
**Effort**: 3 hours
**Complexity**: Medium

#### Implementation Plan:

**Step 1: Create Separate Supabase Clients**
```python
# main.py - Refactor get_supabase()

def get_supabase_client():
    """Get Supabase client with ANON key (RLS enforced)."""
    global _supabase_anon_client
    if _supabase_anon_client is None:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")  # ✅ Use ANON key

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")

        _supabase_anon_client = create_client(url, key)
    return _supabase_anon_client


def get_supabase_admin():
    """Get Supabase admin client (USE SPARINGLY - bypasses RLS)."""
    global _supabase_admin_client
    if _supabase_admin_client is None:
        from supabase import create_client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise ValueError("SERVICE_ROLE_KEY must be set")

        _supabase_admin_client = create_client(url, key)
        logger.warning("Admin client initialized - bypasses RLS")
    return _supabase_admin_client
```

**Step 2: Update All Database Calls**
```python
# main.py - Replace all get_supabase() with get_supabase_client()

async def get_schools_for_children(child_ids: List[str]) -> List[Dict[str, Any]]:
    supabase = get_supabase_client()  # ✅ Use ANON key
    # RLS policies will enforce access control
    response = supabase.table("children").select("school_id, schools(*)").in_("id", child_ids).execute()
    return list(schools.values())


async def create_pickup_request(...):
    supabase = get_supabase_client()  # ✅ Use ANON key
    # RLS will verify user owns children
    response = supabase.table("pickups").insert(pickup_data).execute()
    return response.data[0]
```

**Step 3: Set JWT Context for RLS**
```python
# For operations requiring user context, set JWT in client

async def _handle_pickup_schedule_create(arguments):
    user = await get_current_user(arguments)
    access_token = arguments.get("accessToken")

    supabase = get_supabase_client()

    # Set user JWT for RLS context
    supabase.postgrest.auth(access_token)

    # Now RLS policies will use this JWT
    response = supabase.table("pickups").insert({...}).execute()
```

**Step 4: Limit Admin Client Usage**
```python
# Only use admin client for:
# 1. Schema migrations (apply_schema.py)
# 2. Background jobs (cleanup tasks)
# 3. User profile creation (signup)

async def signup_user(...):
    # Need admin to create user_profiles without existing JWT
    supabase_admin = get_supabase_admin()

    # Create profile
    supabase_admin.table("user_profiles").insert(profile_data).execute()

    # Log admin usage
    logger.warning("Admin client used for user signup", user_id=user_id)
```

**Step 5: Update .env Files**
```env
# .env
SUPABASE_ANON_KEY=your_anon_key_here

# .env.admin (SEPARATE FILE - restricted access)
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

**Step 6: Add Monitoring**
```python
# monitoring.py - Track admin client usage

def track_admin_client_usage(operation: str, user_id: str):
    metrics_collector.increment("admin_client_calls", {
        "operation": operation,
        "user_id": user_id
    })
    logger.warning("Admin client used", operation=operation, user_id=user_id)
```

**Testing**:
1. Verify all queries work with ANON key
2. Test that RLS policies block unauthorized access
3. Confirm admin client only used for approved operations
4. Check logs for admin client usage

---

### 1.4 Remove Frontend Database Bypass (VULN-005)

**Priority**: P0 - CRITICAL
**Effort**: 1 day
**Complexity**: High

#### Implementation Plan:

**Step 1: Create MCP Tool for Real-time Updates**
```python
# main.py - Add Server-Sent Events tool

from starlette.responses import StreamingResponse
import asyncio

@mcp.tool("subscribe-pickup-updates")
async def subscribe_pickup_updates(
    school_id: str,
    access_token: str,
) -> StreamingResponse:
    """Subscribe to real-time pickup updates via Server-Sent Events."""

    # Verify authorization
    user = await validate_session(access_token)
    if not await verify_staff_at_school(user.id, school_id):
        raise PermissionError("Not authorized for this school")

    async def event_stream():
        """Generate SSE stream."""
        supabase = get_supabase_client()
        supabase.postgrest.auth(access_token)

        # Poll for updates every 5 seconds
        last_update = datetime.now()

        while True:
            try:
                # Fetch pickups updated since last check
                response = supabase.table("pickups") \
                    .select("*, children(*), delegates(*)") \
                    .eq("school_id", school_id) \
                    .gte("updated_at", last_update.isoformat()) \
                    .execute()

                if response.data:
                    # Send update via SSE
                    for pickup in response.data:
                        yield f"data: {json.dumps(pickup)}\n\n"

                last_update = datetime.now()
                await asyncio.sleep(5)

            except Exception as e:
                logger.error("SSE stream error", error=str(e))
                yield f"event: error\ndata: {str(e)}\n\n"
                break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )
```

**Step 2: Update Frontend to Use SSE**
```javascript
// dashboard.jsx - Replace Supabase subscription with SSE

useEffect(() => {
  if (!schoolInfo?.id || !accessToken) return;

  // Connect to SSE endpoint
  const eventSource = new EventSource(
    `/api/subscribe-pickup-updates?schoolId=${schoolInfo.id}&accessToken=${accessToken}`
  );

  eventSource.onmessage = (event) => {
    const pickup = JSON.parse(event.data);
    console.log("Pickup update:", pickup);

    setRealtimePickups((prev) => {
      const updated = prev.filter((p) => p.id !== pickup.id);
      return [...updated, pickup].sort(
        (a, b) => new Date(a.scheduled_time) - new Date(b.scheduled_time)
      );
    });
  };

  eventSource.onerror = (error) => {
    console.error("SSE error:", error);
    eventSource.close();
  };

  return () => {
    eventSource.close();
  };
}, [schoolInfo?.id, accessToken]);
```

**Step 3: Remove Supabase Direct Access**
```javascript
// dashboard.jsx - DELETE this code block

// ❌ REMOVE:
const setupRealtimeSubscription = async () => {
  const { createClient } = await import("@supabase/supabase-js");
  const supabase = createClient(supabaseUrl, supabaseKey);

  supabase.channel("pickups-changes")
    .on("postgres_changes", { table: "pickups" })
    .subscribe();
};
```

**Step 4: Remove Supabase from Frontend Dependencies**
```bash
# package.json
npm uninstall @supabase/supabase-js
```

**Step 5: Remove Supabase Env Vars from Frontend**
```bash
# .env (frontend) - DELETE:
# VITE_SUPABASE_URL=...
# VITE_SUPABASE_ANON_KEY=...
```

**Alternative: Use WebSockets**
```python
# main.py - WebSocket implementation (more efficient)

from fastapi import WebSocket

@app.websocket("/ws/pickup-updates/{school_id}")
async def websocket_pickup_updates(websocket: WebSocket, school_id: str):
    await websocket.accept()

    # Authenticate via first message
    auth_message = await websocket.receive_json()
    access_token = auth_message.get("accessToken")

    user = await validate_session(access_token)
    if not await verify_staff_at_school(user.id, school_id):
        await websocket.close(code=1008)  # Policy violation
        return

    # Stream updates
    try:
        while True:
            pickups = await get_school_pickups(school_id, ...)
            await websocket.send_json({"type": "update", "data": pickups})
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        logger.info("WebSocket disconnected", school_id=school_id)
```

**Testing**:
1. Verify real-time updates still work
2. Test authorization (should fail for wrong school)
3. Confirm no direct database access from browser console
4. Load test SSE/WebSocket performance

---

### 1.5 Move Tokens to httpOnly Cookies (VULN-013)

**Priority**: P0 - CRITICAL
**Effort**: 2 hours
**Complexity**: Low

#### Implementation Plan:

**Step 1: Update Backend to Set Cookies**
```python
# main.py - Update login handler

async def _handle_auth_login(arguments: Dict[str, Any]) -> types.CallToolResult:
    result = await login_user(email=payload.email, password=payload.password)

    # Create response with cookie
    response_headers = {
        "Set-Cookie": (
            f"allobye_session={result['session']['access_token']}; "
            "HttpOnly; "  # Not accessible to JavaScript
            "Secure; "    # HTTPS only
            "SameSite=Strict; "  # CSRF protection
            f"Max-Age=3600; "  # 1 hour
            "Path=/"
        )
    }

    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=f"✓ Connexion réussie! Bienvenue {result['profile'].get('name')}"
            )
        ],
        structuredContent={
            "user_id": result["user"]["id"],
            "email": result["user"]["email"],
            "role": result["profile"]["role"],
            # ❌ DON'T include access_token in response
        },
        _meta={"response_headers": response_headers}
    )
```

**Step 2: Update Frontend**
```javascript
// auth-screen.jsx - Remove localStorage

const handleLogin = async (e) => {
  e.preventDefault();

  try {
    const result = await window.openai.callTool("auth-login", {
      email: formData.email,
      password: formData.password,
    });

    // ❌ REMOVE: localStorage.setItem("allobye_token", ...)

    // Cookie is set automatically by browser
    if (onAuthenticated) {
      onAuthenticated({
        user: result._meta?.profile,
        // Token is in httpOnly cookie, not accessible
      });
    }
  } catch (error) {
    // ...
  }
};
```

**Step 3: Update API Calls to Use Cookies**
```javascript
// dashboard.jsx - Cookies sent automatically

const refreshData = async () => {
  // Cookies sent automatically with request
  const result = await window.openai.callTool("school-dashboard-fetch", {
    schoolId: schoolInfo.id,
    // ❌ DON'T send accessToken manually
  });
};
```

**Step 4: Update Backend to Read Cookies**
```python
# main.py - Extract token from cookie

async def get_current_user(arguments: Dict[str, Any], request) -> Optional[UserProfile]:
    # Try cookie first
    access_token = request.cookies.get("allobye_session")

    # Fallback to argument (for backwards compatibility during migration)
    if not access_token:
        access_token = arguments.get("access_token") or arguments.get("accessToken")

    if not access_token:
        return None

    return await validate_session(access_token)
```

**Testing**:
1. Verify login sets cookie (check DevTools → Application → Cookies)
2. Confirm cookie has HttpOnly, Secure, SameSite flags
3. Test that `document.cookie` cannot access token
4. Verify logout clears cookie

---

## Phase 2: HIGH Severity Fixes (1-2 Weeks)

### 2.1 Implement Rate Limiting (VULN-007)

**Priority**: P1 - HIGH
**Effort**: 1 day
**Complexity**: Medium

#### Implementation:

**Step 1: Install Rate Limiting Library**
```bash
pip install slowapi
```

**Step 2: Configure Rate Limiter**
```python
# main.py

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Add to app
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
```

**Step 3: Apply Rate Limits to Endpoints**
```python
# Authentication endpoints (strict limits)
@limiter.limit("5/15minutes")
async def _handle_auth_login(arguments):
    # ...

@limiter.limit("3/hour")
async def _handle_auth_signup(arguments):
    # ...

@limiter.limit("3/hour")
async def _handle_auth_reset_password(arguments):
    # ...

# Emergency endpoints (prevent spam)
@limiter.limit("3/hour")
async def _handle_emergency_declare(arguments):
    # ...

# Pickup scheduling (prevent abuse)
@limiter.limit("20/hour")
async def _handle_pickup_schedule_create(arguments):
    # ...

# Dashboard (generous limit)
@limiter.limit("100/minute")
async def _handle_school_dashboard_fetch(arguments):
    # ...
```

**Step 4: Add Per-User Rate Limiting**
```python
# Use user_id instead of IP for authenticated endpoints

def get_user_identifier(request, arguments):
    """Get user_id or IP for rate limiting."""
    access_token = arguments.get("accessToken")
    if access_token:
        try:
            user = validate_session(access_token)  # Sync version
            return f"user:{user.id}"
        except:
            pass
    return f"ip:{get_remote_address(request)}"

limiter = Limiter(key_func=get_user_identifier)
```

**Step 5: Add Rate Limit Headers**
```python
# Return rate limit info in response headers

@app.middleware("http")
async def add_rate_limit_headers(request, call_next):
    response = await call_next(request)

    if hasattr(request.state, "view_rate_limit"):
        limit_info = request.state.view_rate_limit
        response.headers["X-RateLimit-Limit"] = str(limit_info.limit)
        response.headers["X-RateLimit-Remaining"] = str(limit_info.remaining)
        response.headers["X-RateLimit-Reset"] = str(limit_info.reset_time)

    return response
```

**Step 6: Add Redis for Distributed Rate Limiting**
```python
# For production with multiple servers
import redis

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=6379,
    decode_responses=True
)

limiter = Limiter(
    key_func=get_user_identifier,
    storage_uri=f"redis://{os.getenv('REDIS_HOST')}:6379"
)
```

---

### 2.2 Strengthen Password Requirements (VULN-006)

**Priority**: P1 - HIGH
**Effort**: 2 hours
**Complexity**: Low

#### Implementation:

**Step 1: Update Pydantic Validation**
```python
# auth.py

import re

def validate_password_strength(password: str) -> bool:
    """Validate password meets strength requirements."""
    if len(password) < 12:
        return False

    # Must have uppercase
    if not re.search(r'[A-Z]', password):
        return False

    # Must have lowercase
    if not re.search(r'[a-z]', password):
        return False

    # Must have number
    if not re.search(r'\d', password):
        return False

    # Must have special character
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False

    return True


class AuthSignupInput(BaseModel):
    password: str = Field(..., min_length=12)

    @field_validator('password')
    def validate_password(cls, v):
        if not validate_password_strength(v):
            raise ValueError(
                "Password must be at least 12 characters and include "
                "uppercase, lowercase, number, and special character"
            )
        return v
```

**Step 2: Check Against Breached Passwords**
```bash
pip install pwnedpasswords
```

```python
import pwnedpasswords

@field_validator('password')
def check_breached_password(cls, v):
    # Check against Have I Been Pwned database
    pwned_count = pwnedpasswords.check(v)

    if pwned_count > 0:
        raise ValueError(
            f"This password has appeared in {pwned_count} data breaches. "
            "Please choose a different password."
        )

    return v
```

**Step 3: Update Frontend Validation**
```javascript
// auth-screen.jsx

const validatePassword = (password) => {
  const errors = [];

  if (password.length < 12) {
    errors.push("Au moins 12 caractères");
  }

  if (!/[A-Z]/.test(password)) {
    errors.push("Au moins une lettre majuscule");
  }

  if (!/[a-z]/.test(password)) {
    errors.push("Au moins une lettre minuscule");
  }

  if (!/\d/.test(password)) {
    errors.push("Au moins un chiffre");
  }

  if (!/[!@#$%^&*(),.?":{}|<>]/.test(password)) {
    errors.push("Au moins un caractère spécial");
  }

  return errors;
};

const handlePasswordChange = (e) => {
  const password = e.target.value;
  const errors = validatePassword(password);

  setPasswordErrors(errors);
  setFormData({ ...formData, password });
};
```

---

### 2.3 Add Security Headers (VULN-010, VULN-011)

**Priority**: P1 - HIGH
**Effort**: 2 hours
**Complexity**: Low

#### Implementation:

```python
# main.py - Add security headers middleware

@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)

    # Content Security Policy
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://chat.openai.com; "
        "style-src 'self' 'unsafe-inline'; "  # React needs inline styles
        "img-src 'self' data: https:; "
        "connect-src 'self' https://*.supabase.co; "
        "font-src 'self' data:; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self';"
    )

    # Strict Transport Security
    response.headers['Strict-Transport-Security'] = (
        "max-age=31536000; includeSubDomains; preload"
    )

    # Prevent MIME sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'

    # XSS Protection (legacy browsers)
    response.headers['X-XSS-Protection'] = '1; mode=block'

    # Clickjacking protection
    response.headers['X-Frame-Options'] = 'DENY'

    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'

    # Permissions policy
    response.headers['Permissions-Policy'] = (
        "geolocation=(), microphone=(), camera=()"
    )

    return response
```

---

### 2.4 Implement Proper Secret Management (VULN-009)

**Priority**: P1 - HIGH
**Effort**: 3 hours
**Complexity**: Medium

#### Implementation:

**Option 1: AWS Secrets Manager**
```python
# secrets.py

import boto3
from functools import lru_cache
import json

class SecretManager:
    def __init__(self):
        self.client = boto3.client('secretsmanager', region_name='us-east-1')

    @lru_cache(maxsize=32)
    def get_secret(self, secret_name: str) -> dict:
        """Fetch secret from AWS Secrets Manager (cached)."""
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return json.loads(response['SecretString'])
        except Exception as e:
            logger.error(f"Failed to fetch secret {secret_name}", error=str(e))
            raise

secret_manager = SecretManager()

# Usage in main.py
def get_supabase_client():
    secrets = secret_manager.get_secret('allobye/production')

    url = secrets['SUPABASE_URL']
    key = secrets['SUPABASE_ANON_KEY']

    return create_client(url, key)
```

**Option 2: HashiCorp Vault**
```python
import hvac

class VaultSecretManager:
    def __init__(self):
        self.client = hvac.Client(url=os.getenv('VAULT_ADDR'))
        self.client.auth.approle.login(
            role_id=os.getenv('VAULT_ROLE_ID'),
            secret_id=os.getenv('VAULT_SECRET_ID')
        )

    def get_secret(self, path: str) -> dict:
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response['data']['data']
```

**Migration Steps**:
1. Create secrets in AWS Secrets Manager
2. Update application to read from secret manager
3. Remove secrets from `.env` files
4. Add `.env` to `.gitignore` (if not already)
5. Scan git history for leaked secrets:
   ```bash
   git log --all --full-history -- .env
   ```
6. If secrets found in git, rotate ALL keys immediately

---

### 2.5 Fix CORS Configuration (VULN-008)

**Priority**: P1 - HIGH
**Effort**: 30 minutes
**Complexity**: Low

#### Implementation:

```python
# main.py

# Get allowed origins from environment
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "").split(",")

if not ALLOWED_ORIGINS or ALLOWED_ORIGINS == [""]:
    logger.warning("No ALLOWED_ORIGINS configured, defaulting to localhost")
    ALLOWED_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # ✅ Specific origins only
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],  # Only needed methods
    allow_headers=["Content-Type", "Authorization", "Cookie"],
    expose_headers=["Set-Cookie"],
)
```

**.env Configuration**:
```env
# Development
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173

# Production
ALLOWED_ORIGINS=https://allobye.ca,https://dashboard.allobye.ca,https://chat.openai.com
```

---

## Phase 3: MEDIUM Severity Fixes (2-4 Weeks)

### 3.1 Implement Audit Logging (VULN-018)

**Effort**: 2 days
**Complexity**: Medium

#### Implementation:

```sql
-- schema.sql

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID,
    user_email TEXT,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID,
    old_value JSONB,
    new_value JSONB,
    ip_address INET,
    user_agent TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT
);

CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_user_id ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);

-- Audit trigger for delegate authorizations
CREATE OR REPLACE FUNCTION audit_delegate_children()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO audit_log (action, entity_type, entity_id, new_value)
        VALUES ('delegate_authorized', 'delegate_children', NEW.delegate_id, to_jsonb(NEW));
    ELSIF TG_OP = 'DELETE' THEN
        INSERT INTO audit_log (action, entity_type, entity_id, old_value)
        VALUES ('delegate_revoked', 'delegate_children', OLD.delegate_id, to_jsonb(OLD));
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_delegate_children_changes
    AFTER INSERT OR DELETE ON delegate_children
    FOR EACH ROW
    EXECUTE FUNCTION audit_delegate_children();
```

**Application-Level Logging**:
```python
# main.py

async def log_audit_event(
    action: str,
    entity_type: str,
    entity_id: str,
    user: Optional[UserProfile] = None,
    old_value: Optional[dict] = None,
    new_value: Optional[dict] = None,
    success: bool = True,
    error: Optional[str] = None,
):
    """Log audit event to database."""
    supabase = get_supabase_admin()  # Admin for audit logging

    audit_entry = {
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "user_id": user.id if user else None,
        "user_email": user.email if user else None,
        "old_value": old_value,
        "new_value": new_value,
        "success": success,
        "error_message": error,
    }

    supabase.table("audit_log").insert(audit_entry).execute()


# Use in handlers
async def _handle_delegate_authorize(arguments):
    user = await get_current_user(arguments)

    # ... authorization logic ...

    await log_audit_event(
        action="delegate_authorize",
        entity_type="delegate",
        entity_id=delegate_id,
        user=user,
        new_value={
            "delegate_email": payload.delegate_email,
            "child_ids": payload.child_ids,
            "permissions": payload.permissions,
        }
    )
```

**Audit Query Tool**:
```python
@mcp.tool("audit-log-query")
async def query_audit_log(
    start_date: str,
    end_date: str,
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    access_token: str,
):
    """Query audit log (admin only)."""

    user = await validate_session(access_token)
    if user.role != "admin":
        raise PermissionError("Admin access required")

    supabase = get_supabase_admin()

    query = supabase.table("audit_log").select("*") \
        .gte("timestamp", start_date) \
        .lte("timestamp", end_date)

    if user_id:
        query = query.eq("user_id", user_id)

    if action:
        query = query.eq("action", action)

    results = query.order("timestamp", desc=True).execute()
    return results.data
```

---

### 3.2 Add CSRF Protection (VULN-016)

**Effort**: 4 hours
**Complexity**: Low

```bash
pip install starlette-csrf
```

```python
from starlette_csrf import CSRFMiddleware

app.add_middleware(
    CSRFMiddleware,
    secret=os.getenv("CSRF_SECRET"),
    cookie_name="allobye_csrf",
    cookie_secure=True,
    cookie_httponly=True,
)
```

---

### 3.3 Improve Error Handling (VULN-015, VULN-017)

**Effort**: 1 day

```python
# Custom error responses

class AllOByeError(Exception):
    """Base exception for AllôBye errors."""
    def __init__(self, user_message: str, log_details: dict = None):
        self.user_message = user_message
        self.log_details = log_details or {}
        super().__init__(user_message)


class UnauthorizedError(AllOByeError):
    pass


class ValidationError(AllOByeError):
    pass


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    # Log full details
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        request_path=request.url.path,
        user_agent=request.headers.get("user-agent")
    )

    # Return generic message to user
    if isinstance(exc, AllOByeError):
        message = exc.user_message
    else:
        message = "Une erreur interne est survenue. Veuillez réessayer."

    return JSONResponse(
        status_code=500,
        content={"error": message}
    )
```

---

## Phase 4: LOW Severity Fixes (4+ Weeks)

### 4.1 Add Input Validation (VULN-022, VULN-023)

```python
from pydantic import EmailStr, validator

class AuthSignupInput(BaseModel):
    email: EmailStr = Field(...)  # ✅ Built-in email validation

    @field_validator('scheduled_time')
    def validate_iso8601(cls, v):
        try:
            datetime.fromisoformat(v.replace('Z', '+00:00'))
        except ValueError:
            raise ValueError("Invalid ISO 8601 datetime format")
        return v
```

---

### 4.2 Implement Data Retention Policy (VULN-020)

```sql
-- Scheduled cleanup job

CREATE OR REPLACE FUNCTION cleanup_old_data()
RETURNS void AS $$
BEGIN
    -- Delete completed pickups older than 90 days
    DELETE FROM pickups
    WHERE status IN ('completed', 'cancelled')
    AND scheduled_time < NOW() - INTERVAL '90 days';

    -- Delete resolved emergencies older than 30 days
    DELETE FROM emergencies
    WHERE resolved = TRUE
    AND resolved_at < NOW() - INTERVAL '30 days';

    -- Archive audit logs older than 1 year
    INSERT INTO audit_log_archive
    SELECT * FROM audit_log
    WHERE timestamp < NOW() - INTERVAL '1 year';

    DELETE FROM audit_log
    WHERE timestamp < NOW() - INTERVAL '1 year';
END;
$$ LANGUAGE plpgsql;

-- Schedule with pg_cron
SELECT cron.schedule(
    'cleanup-old-data',
    '0 2 * * *',  -- 2 AM daily
    'SELECT cleanup_old_data()'
);
```

---

## Testing Strategy

### Security Testing Checklist:

1. **Penetration Testing**
   - Run OWASP ZAP scan
   - Manual XSS testing with payloads
   - SQL injection attempts
   - Authentication bypass attempts

2. **Code Review**
   - Review all database queries
   - Check all user input handling
   - Verify RLS policies
   - Audit admin client usage

3. **Automated Scans**
   ```bash
   # Python security scan
   bandit -r allobye_server_python/ -ll

   # Dependency vulnerabilities
   safety check

   # Secret scanning
   truffleHog --regex --entropy=True .
   ```

4. **Load Testing**
   ```bash
   # Test rate limiting
   locust -f tests/load_test.py --headless -u 100 -r 10
   ```

---

## Deployment Checklist

Before deploying to production:

- [ ] All CRITICAL vulnerabilities fixed
- [ ] All HIGH vulnerabilities fixed
- [ ] Security headers configured
- [ ] HTTPS enforced
- [ ] Secrets moved to secret manager
- [ ] Rate limiting enabled
- [ ] CORS properly configured
- [ ] Audit logging enabled
- [ ] Monitoring alerts configured
- [ ] Incident response plan documented
- [ ] Security team review completed
- [ ] Penetration test passed

---

## Maintenance

### Ongoing Security Tasks:

**Weekly**:
- Review audit logs for anomalies
- Check rate limit hit rates
- Monitor error logs

**Monthly**:
- Update dependencies
- Review access control policies
- Test backup/restore procedures

**Quarterly**:
- Security audit
- Penetration testing
- Review and update RLS policies

**Annually**:
- Full security assessment
- Disaster recovery drill
- Compliance audit (Loi 25)

---

## Conclusion

Implementing these recommendations will significantly improve AllôBye's security posture, bringing it from **HIGH RISK** to **LOW RISK** for production deployment with real child data.

**Priority Execution**:
1. **Week 1**: CRITICAL fixes (data encryption, XSS, auth architecture)
2. **Week 2-3**: HIGH fixes (rate limiting, headers, secrets)
3. **Week 4-6**: MEDIUM fixes (CSRF, audit logging, error handling)
4. **Week 7+**: LOW fixes (validation, retention policy)

**Estimated Total Effort**: 3-4 developer weeks for phases 1-3.

For questions or clarification, contact the security team.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Next Review**: After Phase 1 completion
