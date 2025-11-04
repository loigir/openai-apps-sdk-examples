# Authentication Security Documentation

## Overview

The AllôBye authentication system implements enterprise-grade security features to protect user accounts and prevent unauthorized access. This document describes the security features, configuration, and authentication flow.

## Security Features Implemented

### 1. Password Strength Requirements

**Policy Enforced:**
- Minimum length: 12 characters
- Must contain at least one uppercase letter (A-Z)
- Must contain at least one lowercase letter (a-z)
- Must contain at least one digit (0-9)
- Must contain at least one special character (!@#$%^&*(),.?":{}|<>)
- Cannot be a common password (checked against top 100 most common passwords)
- Cannot contain sequential characters (e.g., "123", "abc")

**Implementation:**
- `validate_password_strength()` function validates all password requirements
- `WeakPasswordError` exception raised when password doesn't meet requirements
- Applied to signup and password reset flows

**Example Validation:**
```python
is_valid, error_msg = validate_password_strength("MyP@ssw0rd123")
if not is_valid:
    raise WeakPasswordError(error_msg)
```

### 2. Rate Limiting

**Protection Against Brute Force Attacks:**

**Login Attempts:**
- Maximum: 5 attempts per 15 minutes per email
- Tracked in-memory (production should use Redis)
- Counter resets after time window expires

**Signup Attempts:**
- Maximum: 3 attempts per 15 minutes per email
- Prevents account enumeration attacks

**Implementation:**
- `check_rate_limit()` function enforces limits
- `RateLimitExceededError` exception raised when limit exceeded
- Automatic cleanup of expired attempts

**Configuration:**
```python
SECURITY_CONFIG.max_login_attempts = 5
SECURITY_CONFIG.max_signup_attempts = 3
SECURITY_CONFIG.rate_limit_window_minutes = 15
```

### 3. Account Lockout

**Failed Login Attempt Tracking:**
- Maximum: 5 failed login attempts
- Lockout duration: 30 minutes
- Automatic unlock after lockout period expires
- Failed attempts cleared on successful login

**Implementation:**
- `record_failed_login()` tracks failed attempts
- `check_account_lockout()` enforces lockout
- `clear_failed_login_attempts()` resets on success
- `AccountLockedError` exception raised when locked

**Storage:**
- `_failed_login_store`: Tracks failed attempts with timestamps
- `_account_lockout_store`: Tracks lockout start time per email

### 4. Secure Session Management

**Session Configuration:**
- Default timeout: 1 hour
- Configurable per environment
- Token expiration validation

**Token Refresh Mechanism:**
- Automatic token rotation on refresh
- Old refresh token invalidated when new one issued
- Prevents token reuse attacks
- Refresh recommended when < 10 minutes until expiry

**Implementation:**
```python
# Check if token should be refreshed
if should_refresh_token(expires_at):
    new_session = await refresh_session(refresh_token)
```

**Functions:**
- `refresh_session()`: Implements token rotation
- `get_session_info()`: Provides expiration details
- `should_refresh_token()`: Recommends when to refresh
- `validate_session()`: Validates current session

### 5. Multi-Factor Authentication (MFA) Preparation

**MFA Hooks Ready for Implementation:**
- `MFAContext` class manages MFA state
- `enable_mfa()` method for MFA setup
- `verify_mfa()` method for code verification
- `check_mfa_required()` checks if MFA needed
- `MFARequiredError` exception for MFA enforcement

**Future Implementation:**
- TOTP (Time-based One-Time Password) support
- SMS verification support
- Email verification support
- Backup codes for account recovery

**Current State:**
All login/signup responses include MFA context:
```python
{
    "mfa_context": {
        "enabled": False,
        "required": False
    }
}
```

## Security Configuration

### Default Configuration

```python
@dataclass
class SecurityConfig:
    # Password policy
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True

    # Rate limiting
    max_login_attempts: int = 5
    rate_limit_window_minutes: int = 15
    max_signup_attempts: int = 3

    # Session management
    session_timeout_hours: int = 1
    token_refresh_threshold_minutes: int = 10

    # Account lockout
    lockout_duration_minutes: int = 30
    max_failed_attempts_before_lockout: int = 5
```

### Customizing Configuration

To adjust security settings, modify the global `SECURITY_CONFIG`:

```python
from allobye_server_python.auth import SECURITY_CONFIG

# Increase session timeout to 2 hours
SECURITY_CONFIG.session_timeout_hours = 2

# More strict password requirements
SECURITY_CONFIG.password_min_length = 16

# Adjust rate limiting
SECURITY_CONFIG.max_login_attempts = 3
SECURITY_CONFIG.rate_limit_window_minutes = 30
```

## Authentication Flow

### 1. User Signup Flow

```
1. User submits signup form
   ↓
2. Check rate limiting (max 3 attempts per 15 min)
   ↓
3. Validate password strength (12+ chars, complexity)
   ↓
4. Check against common passwords
   ↓
5. Create user in Supabase Auth
   ↓
6. Create user profile in database
   ↓
7. Link to schools/children if applicable
   ↓
8. Initialize MFA context
   ↓
9. Return user info, session, and MFA context
```

**Error Handling:**
- `WeakPasswordError`: Password doesn't meet requirements
- `RateLimitExceededError`: Too many signup attempts
- `UserAlreadyExistsError`: Email already registered
- `AuthenticationError`: General signup errors

### 2. User Login Flow

```
1. User submits login credentials
   ↓
2. Check rate limiting (max 5 attempts per 15 min)
   ↓
3. Check account lockout (5 failed attempts = 30 min lockout)
   ↓
4. Authenticate with Supabase
   ↓
5. On SUCCESS:
   - Clear failed login attempts
   - Fetch user profile
   - Initialize MFA context
   - Check if MFA required
   - Return session tokens
   ↓
6. On FAILURE:
   - Record failed login attempt
   - Check if should lock account
   - Throw InvalidCredentialsError
```

**Error Handling:**
- `RateLimitExceededError`: Too many login attempts
- `AccountLockedError`: Account locked due to failed attempts
- `InvalidCredentialsError`: Wrong email/password
- `MFARequiredError`: MFA enabled but not verified
- `EmailNotVerifiedError`: Email not verified (if enforced)

### 3. Session Management Flow

```
1. Client makes authenticated request with access_token
   ↓
2. Validate session (check expiration)
   ↓
3. If token near expiration (< 10 min):
   - Recommend refresh
   - Client calls refresh_session()
   ↓
4. On refresh:
   - Generate new access_token
   - Generate new refresh_token
   - Invalidate old refresh_token
   - Return new session
   ↓
5. If token expired:
   - Throw SessionExpiredError
   - Client must re-authenticate
```

### 4. Password Reset Flow

```
1. User requests password reset
   ↓
2. Send reset email (don't reveal if email exists)
   ↓
3. User clicks link in email
   ↓
4. Verify reset token
   ↓
5. User enters new password
   ↓
6. Validate password strength
   ↓
7. Update password in Supabase
   ↓
8. Clear any account lockouts
   ↓
9. Send confirmation email
```

## Exception Hierarchy

```
AuthenticationError (base)
├── InvalidCredentialsError
├── EmailNotVerifiedError
├── UserAlreadyExistsError
├── SessionExpiredError
├── WeakPasswordError
├── RateLimitExceededError
├── AccountLockedError
└── MFARequiredError
```

## API Usage Examples

### Signup with Strong Password

```python
from allobye_server_python.auth import signup_user, WeakPasswordError

try:
    result = await signup_user(
        email="user@example.com",
        password="MySecureP@ssw0rd123",
        name="John Doe",
        role="parent"
    )

    print(f"User created: {result['user']['id']}")
    print(f"Session expires: {result['session']['expires_at']}")
    print(f"MFA enabled: {result['mfa_context']['enabled']}")

except WeakPasswordError as e:
    print(f"Password error: {e}")
except RateLimitExceededError as e:
    print(f"Rate limit: {e}")
```

### Login with Rate Limiting

```python
from allobye_server_python.auth import login_user, AccountLockedError

try:
    result = await login_user(
        email="user@example.com",
        password="MySecureP@ssw0rd123"
    )

    access_token = result['session']['access_token']
    refresh_token = result['session']['refresh_token']

    # Store tokens securely

except AccountLockedError as e:
    print(f"Account locked: {e}")
except InvalidCredentialsError:
    print("Invalid credentials")
except RateLimitExceededError as e:
    print(f"Too many attempts: {e}")
```

### Session Management with Token Refresh

```python
from allobye_server_python.auth import (
    validate_session,
    refresh_session,
    get_session_info,
    SessionExpiredError
)

# Check session validity
try:
    profile = await validate_session(access_token)
    print(f"Logged in as: {profile.email}")
except SessionExpiredError:
    # Token expired, try refresh
    try:
        new_session = await refresh_session(refresh_token)
        access_token = new_session['session']['access_token']
        refresh_token = new_session['session']['refresh_token']
    except SessionExpiredError:
        # Refresh token also expired, need to re-login
        print("Session expired, please login again")

# Get detailed session info
session_info = await get_session_info(access_token)
if session_info['should_refresh']:
    print(f"Token expires in {session_info['time_until_expiry_minutes']} minutes")
    print("Consider refreshing token soon")
```

## Production Considerations

### 1. Rate Limiting Storage

**Current Implementation:** In-memory storage (development)
**Production Recommendation:** Redis or similar distributed cache

```python
# Example Redis integration
import redis
from datetime import timedelta

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def check_rate_limit_redis(email: str, attempt_type: str = "login"):
    key = f"rate_limit:{attempt_type}:{email}"
    count = redis_client.incr(key)

    if count == 1:
        redis_client.expire(key, timedelta(minutes=15))

    if count > SECURITY_CONFIG.max_login_attempts:
        raise RateLimitExceededError("Too many attempts")
```

### 2. Session Storage

Consider storing session metadata in database for:
- Session revocation
- Multi-device management
- Activity tracking
- Security auditing

### 3. MFA Implementation

For production MFA:
- Use established libraries (pyotp for TOTP)
- Integrate SMS provider (Twilio, AWS SNS)
- Implement backup codes
- Add recovery email flow

### 4. Password Hashing

Supabase Auth handles password hashing using bcrypt with appropriate cost factor.
Never store plain-text passwords.

### 5. Security Headers

Implement security headers in your API:
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`
- `Strict-Transport-Security: max-age=31536000`

### 6. Audit Logging

Log all authentication events:
- Successful logins
- Failed login attempts
- Password changes
- Account lockouts
- Token refreshes
- MFA challenges

### 7. IP-Based Rate Limiting

Consider adding IP-based rate limiting in addition to email-based:
```python
check_rate_limit_by_ip(request.client.ip)
check_rate_limit(email, "login")
```

## Security Best Practices

1. **Never** log sensitive data (passwords, tokens)
2. **Always** use HTTPS in production
3. **Validate** all input on both client and server
4. **Rotate** secrets and keys regularly
5. **Monitor** for suspicious activity patterns
6. **Test** security features regularly
7. **Update** dependencies to patch vulnerabilities
8. **Document** security procedures for team
9. **Review** security configurations quarterly
10. **Implement** security incident response plan

## Compliance

This authentication system helps meet requirements for:
- **GDPR**: User consent, data protection, right to erasure
- **FERPA**: Student data protection (school staff role separation)
- **COPPA**: Parental consent for children under 13
- **SOC 2**: Access controls, audit logging
- **PCI DSS**: Strong authentication (if handling payments)

## Testing Security Features

### Test Password Validation

```python
from allobye_server_python.auth import validate_password_strength

# Test weak passwords
test_passwords = [
    ("short", False),  # Too short
    ("alllowercase123!", False),  # No uppercase
    ("ALLUPPERCASE123!", False),  # No lowercase
    ("NoDigitsHere!", False),  # No digits
    ("NoSpecialChar123", False),  # No special char
    ("Password123!", False),  # Common password
    ("MySecureP@ssw0rd123", True),  # Valid
]

for password, should_pass in test_passwords:
    is_valid, error = validate_password_strength(password)
    assert is_valid == should_pass, f"Failed for: {password}"
```

### Test Rate Limiting

```python
from allobye_server_python.auth import check_rate_limit, RateLimitExceededError

email = "test@example.com"

# Should allow first 5 attempts
for i in range(5):
    check_rate_limit(email, "login")

# 6th attempt should fail
try:
    check_rate_limit(email, "login")
    assert False, "Should have raised RateLimitExceededError"
except RateLimitExceededError:
    pass  # Expected
```

### Test Account Lockout

```python
from allobye_server_python.auth import record_failed_login, check_account_lockout

email = "test@example.com"

# Record 5 failed attempts
for i in range(5):
    record_failed_login(email)

# Should be locked now
try:
    check_account_lockout(email)
    assert False, "Account should be locked"
except AccountLockedError as e:
    assert "30 minutes" in str(e)
```

## Troubleshooting

### Account Locked Error

**Issue:** User sees "Account is locked" message
**Solution:**
1. Wait for lockout duration (30 minutes)
2. Or admin can manually clear: `clear_failed_login_attempts(email)`

### Rate Limit Exceeded

**Issue:** "Too many attempts" message
**Solution:**
1. Wait for rate limit window (15 minutes)
2. Ensure client isn't retrying too quickly

### Session Expired

**Issue:** "Session expired" on API calls
**Solution:**
1. Implement automatic token refresh
2. Check if refresh token also expired
3. Re-authenticate if both tokens expired

### Weak Password Error

**Issue:** Password rejected during signup
**Solution:**
1. Review password requirements in this document
2. Use password strength indicator on frontend
3. Provide clear error messages to user

## Monitoring and Alerts

Set up monitoring for:

1. **High failed login rate**: May indicate brute force attack
2. **Multiple account lockouts**: May indicate distributed attack
3. **Unusual token refresh patterns**: May indicate token theft
4. **Geographic anomalies**: Login from unusual locations
5. **Time-based anomalies**: Login at unusual times

## Future Enhancements

Planned security improvements:

1. **Device fingerprinting**: Track and recognize user devices
2. **Behavioral biometrics**: Analyze typing patterns, mouse movements
3. **Risk-based authentication**: Require MFA for high-risk actions
4. **IP reputation checking**: Block known malicious IPs
5. **CAPTCHA integration**: Prevent automated attacks
6. **Password breach checking**: Check against Have I Been Pwned
7. **WebAuthn/FIDO2**: Hardware key authentication
8. **Social login**: OAuth with Google, Microsoft, Apple

## Support and Security Contact

For security issues or questions:
- Security Email: security@allobye.example.com
- Bug Reports: Create private GitHub issue with "Security" tag
- Urgent Issues: Follow responsible disclosure process

---

**Last Updated:** 2025-11-04
**Version:** 1.0.0
**Author:** Security Agent 4
