# Error Handling Guide - AllôBye MCP Server

## Overview

The AllôBye MCP Server implements a comprehensive, production-ready error handling system that ensures:

- **Consistent error responses** across all endpoints
- **User-friendly error messages** that are actionable
- **Automatic retry logic** for transient failures
- **Circuit breaker pattern** to prevent cascading failures
- **Comprehensive logging** with context for debugging
- **Type-safe error handling** with clear error codes

## Table of Contents

1. [Exception Hierarchy](#exception-hierarchy)
2. [Error Handler Decorator](#error-handler-decorator)
3. [Retry Logic](#retry-logic)
4. [Circuit Breaker](#circuit-breaker)
5. [Error Response Format](#error-response-format)
6. [Best Practices](#best-practices)
7. [Examples](#examples)

---

## Exception Hierarchy

All errors in the system inherit from `AllobyeError`, which provides:

- `error_code`: Unique code for programmatic handling
- `message`: User-friendly error message
- `details`: Additional context for debugging
- `http_status`: HTTP status code for API responses

### Error Categories

#### 1. Validation Errors (400 Bad Request)

```python
ValidationError              # Base validation error
  ├─ InvalidInputError      # Invalid input data
  ├─ MissingFieldError      # Required field missing
  ├─ InvalidFormatError     # Invalid data format
  ├─ InvalidEmailError      # Invalid email address
  ├─ InvalidDateTimeError   # Invalid date/time format
  ├─ XSSViolationError      # Potential XSS attack
  └─ WeakPasswordError      # Password doesn't meet requirements
```

**Example:**
```python
from exceptions import InvalidInputError

raise InvalidInputError(
    "Email address is invalid",
    details={"field": "email", "value": "bad-email"}
)
```

#### 2. Authorization Errors (401/403)

```python
AuthorizationError                   # Base authorization error
  ├─ AuthenticationError (401)       # Authentication required
  │   ├─ InvalidCredentialsError     # Wrong email/password
  │   ├─ SessionExpiredError         # Session expired
  │   ├─ InvalidTokenError           # Invalid auth token
  │   ├─ EmailNotVerifiedError       # Email not verified
  │   ├─ AccountLockedError          # Account locked
  │   └─ MFARequiredError            # MFA required
  └─ PermissionDeniedError (403)     # Insufficient permissions
      ├─ RoleRequiredError           # Required role not met
      └─ RateLimitExceededError (429) # Too many requests
```

**Example:**
```python
from exceptions import PermissionDeniedError

raise PermissionDeniedError(
    "You do not have permission to access this school",
    details={"school_id": "123", "required_role": "school_staff"}
)
```

#### 3. Resource Errors (404/409)

```python
ResourceError                    # Base resource error
  ├─ ResourceNotFoundError (404) # Resource not found
  │   ├─ ChildNotFoundError
  │   ├─ SchoolNotFoundError
  │   ├─ UserNotFoundError
  │   ├─ DelegateNotFoundError
  │   └─ PickupNotFoundError
  └─ ResourceConflictError (409)  # Resource conflict
      ├─ UserAlreadyExistsError
      └─ DuplicatePickupError
```

**Example:**
```python
from exceptions import ChildNotFoundError

raise ChildNotFoundError(
    "Child not found",
    details={"child_id": "child_123"}
)
```

#### 4. External Service Errors (502/503/504)

```python
ExternalServiceError (502)        # Base external service error
  ├─ SupabaseError               # Supabase errors
  │   ├─ SupabaseConnectionError (503)
  │   └─ SupabaseTimeoutError (504)
  ├─ MotionPlusError             # Motion+ API errors
  │   └─ MotionPlusConnectionError (503)
  ├─ EmailServiceError           # Email service errors
  └─ SMSServiceError             # SMS service errors
```

**Example:**
```python
from exceptions import SupabaseTimeoutError

raise SupabaseTimeoutError(
    "Database query timed out",
    details={"query": "get_schools", "timeout_ms": 30000}
)
```

#### 5. Database Errors (500/503/504)

```python
DatabaseError (500)              # Base database error
  ├─ DatabaseConnectionError (503)
  ├─ DatabaseTimeoutError (504)
  ├─ DatabaseQueryError
  └─ DatabaseConstraintError (409)
```

#### 6. Business Logic Errors (422)

```python
BusinessLogicError               # Base business rule violation
  ├─ InvalidPickupTimeError     # Pickup time is invalid
  ├─ UnauthorizedPickupError    # Unauthorized pickup attempt
  ├─ SchoolClosedError          # School is closed
  ├─ InvalidEmergencyTypeError  # Invalid emergency type
  ├─ ChildAlreadyPickedUpError  # Child already picked up
  ├─ ParentChildRelationshipError
  └─ StaffSchoolRelationshipError
```

**Example:**
```python
from exceptions import InvalidPickupTimeError

raise InvalidPickupTimeError(
    "Pickup time must be in the future",
    details={"scheduled_time": "2024-01-01T10:00:00", "current_time": "2024-01-01T15:00:00"}
)
```

#### 7. System Errors (500/503)

```python
SystemError (500)                # Base system error
  ├─ ConfigurationError         # System configuration error
  │   └─ EnvironmentVariableError
  ├─ ServiceUnavailableError (503)
  ├─ CircuitBreakerOpenError (503)
  └─ TimeoutError (408)
```

---

## Error Handler Decorator

The `@error_handler` decorator provides automatic error handling for all tool functions:

### Features

- **Automatic error conversion**: Converts all exceptions to proper `CallToolResult`
- **User-friendly messages**: Formats errors for end users
- **Comprehensive logging**: Logs all errors with context
- **Error metadata**: Includes error codes and details in response

### Usage

```python
from error_handlers import error_handler
import mcp.types as types

@error_handler
async def my_tool_handler(arguments: Dict[str, Any]) -> types.CallToolResult:
    # Your code here - decorator handles all errors automatically

    # Validation
    payload = MyInputModel.model_validate(arguments)

    # Business logic
    result = await perform_operation(payload)

    # Return success
    return types.CallToolResult(
        content=[types.TextContent(type="text", text="Success!")]
    )
```

### What the Decorator Does

1. **Catches all exceptions** (custom, Pydantic, unexpected)
2. **Converts to CallToolResult** with proper error flag
3. **Formats user-friendly messages**
4. **Logs errors** with full context
5. **Returns structured error metadata**

### Error Response Structure

```python
types.CallToolResult(
    content=[types.TextContent(type="text", text="User-friendly message")],
    isError=True,
    _meta={
        "error_code": "INVALID_INPUT",
        "http_status": 400,
        "details": {"field": "email"},
    }
)
```

---

## Retry Logic

### Retry Policies

The system includes pre-configured retry policies:

```python
from error_handlers import (
    retry_with_backoff,
    DATABASE_RETRY_POLICY,      # 5 retries, 0.5s initial, 10s max
    EXTERNAL_API_RETRY_POLICY,  # 3 retries, 2s initial, 30s max
    DEFAULT_RETRY_POLICY,       # 3 retries, 1s initial, 60s max
)
```

### Retry Strategies

1. **Exponential Backoff** (default): 1s, 2s, 4s, 8s...
2. **Linear Backoff**: 1s, 2s, 3s, 4s...
3. **Constant Delay**: 1s, 1s, 1s, 1s...
4. **Fibonacci Backoff**: 1s, 1s, 2s, 3s, 5s...

### Usage

```python
@retry_with_backoff(policy=DATABASE_RETRY_POLICY)
async def fetch_data_from_database():
    supabase = get_supabase()
    return supabase.table("children").select("*").execute()
```

### Custom Retry Policy

```python
from error_handlers import RetryPolicy, RetryStrategy

custom_policy = RetryPolicy(
    max_retries=5,
    initial_delay=0.5,
    max_delay=10.0,
    strategy=RetryStrategy.EXPONENTIAL,
    backoff_multiplier=2.0,
    jitter=True,  # Add random jitter to prevent thundering herd
    timeout=30.0,  # Maximum total time to retry (seconds)
)

@retry_with_backoff(policy=custom_policy)
async def my_function():
    # Your code here
    pass
```

### Retryable Errors

By default, these error types are automatically retried:

- `DatabaseConnectionError`
- `DatabaseTimeoutError`
- `SupabaseConnectionError`
- `SupabaseTimeoutError`
- `ExternalServiceError` and subclasses
- `TimeoutError`

Non-retryable errors (fail immediately):

- All validation errors (400)
- All authorization errors (401/403)
- Business logic errors (422)

---

## Circuit Breaker

The circuit breaker pattern prevents cascading failures when external services are down.

### States

1. **CLOSED** (Normal): All requests pass through
2. **OPEN** (Failing): Requests fail fast without calling service
3. **HALF_OPEN** (Testing): Limited requests to test if service recovered

### Configuration

```python
from error_handlers import CircuitBreaker, ExternalServiceError

# Create circuit breaker for a service
supabase_circuit = CircuitBreaker(
    failure_threshold=5,        # Open after 5 failures
    timeout=60.0,               # Try recovery after 60 seconds
    expected_exception=ExternalServiceError,
)

# Use circuit breaker
try:
    result = supabase_circuit.call(fetch_from_supabase, child_id)
except CircuitBreakerOpenError as e:
    # Service is down, use fallback
    result = get_cached_data(child_id)
```

### Global Circuit Breakers

```python
from error_handlers import get_circuit_breaker

# Get or create circuit breaker for a service
supabase_cb = get_circuit_breaker("supabase")
motion_plus_cb = get_circuit_breaker("motion_plus")

# Use in your code
result = supabase_cb.call(lambda: supabase.table("children").select("*").execute())
```

---

## Error Response Format

### MCP Tool Error Response

```json
{
  "content": [
    {
      "type": "text",
      "text": "Invalid email address"
    }
  ],
  "isError": true,
  "_meta": {
    "error_code": "INVALID_EMAIL",
    "http_status": 400,
    "details": {
      "field": "email",
      "value": "bad-email@"
    }
  }
}
```

### HTTP Error Response

```json
{
  "error_code": "AUTHENTICATION_ERROR",
  "message": "Your session has expired. Please log in again",
  "details": {
    "session_id": "sess_123",
    "expired_at": "2024-01-01T12:00:00Z"
  },
  "http_status": 401
}
```

---

## Best Practices

### 1. Always Use Custom Exceptions

❌ **Don't:**
```python
if not user:
    raise ValueError("User not found")
```

✅ **Do:**
```python
from exceptions import UserNotFoundError

if not user:
    raise UserNotFoundError(
        "User not found",
        details={"user_id": user_id}
    )
```

### 2. Provide Context in Error Details

❌ **Don't:**
```python
raise DatabaseError("Query failed")
```

✅ **Do:**
```python
raise DatabaseError(
    "Failed to fetch schools for children",
    details={
        "child_ids": child_ids,
        "table": "schools",
        "operation": "select",
    }
)
```

### 3. Use Error Handler Decorator on All Tools

❌ **Don't:**
```python
async def my_tool(arguments):
    try:
        # ... code ...
    except Exception as e:
        return CallToolResult(
            content=[TextContent(type="text", text=str(e))],
            isError=True
        )
```

✅ **Do:**
```python
@error_handler
async def my_tool(arguments):
    # Decorator handles all errors automatically
    payload = MyInput.model_validate(arguments)
    result = await perform_operation(payload)
    return CallToolResult(...)
```

### 4. Add Retry Logic to External Calls

❌ **Don't:**
```python
async def fetch_schools():
    return supabase.table("schools").select("*").execute()
```

✅ **Do:**
```python
@retry_with_backoff(policy=DATABASE_RETRY_POLICY)
async def fetch_schools():
    with ErrorContext("fetch_schools"):
        return supabase.table("schools").select("*").execute()
```

### 5. Convert Third-Party Exceptions

❌ **Don't:**
```python
try:
    result = supabase.table("children").select("*").execute()
except Exception as e:
    logger.error(f"Error: {e}")
    raise
```

✅ **Do:**
```python
from error_handlers import convert_supabase_error

try:
    result = supabase.table("children").select("*").execute()
except Exception as e:
    supabase_error = convert_supabase_error(e)
    logger.error("Database error", error=str(e))
    raise supabase_error
```

### 6. Use Error Context for Operations

```python
from error_handlers import ErrorContext

async def complex_operation(child_id: str):
    with ErrorContext("create_pickup", child_id=child_id, user_id=user.id):
        # All errors within this block will be logged with context
        schools = await get_schools_for_children([child_id])
        pickup = await create_pickup_request(...)
        return pickup
```

### 7. Implement Fallbacks for Non-Critical Operations

```python
from error_handlers import with_fallback_async

# Get user's preferred language, fallback to English
language = await with_fallback_async(
    get_user_language,
    fallback_value="en",
    user_id=user.id
)

# Get school logo URL, fallback to default logo
logo_url = await with_fallback_async(
    get_school_logo,
    fallback_value="https://example.com/default-logo.png",
    school_id=school_id
)
```

---

## Examples

### Example 1: Tool Handler with Complete Error Handling

```python
from error_handlers import error_handler, retry_with_backoff, DATABASE_RETRY_POLICY, ErrorContext
from exceptions import ParentChildRelationshipError
import mcp.types as types

@error_handler
async def handle_pickup_schedule(arguments: Dict[str, Any]) -> types.CallToolResult:
    # Validate input (ValidationError auto-handled by decorator)
    payload = PickupScheduleInput.model_validate(arguments)

    # Authenticate user (AuthenticationError auto-handled)
    user = await get_current_user(arguments)
    if not user or user.role != "parent":
        raise AuthenticationError("Parent authentication required")

    # Verify authorization (AuthorizationError auto-handled)
    for child_id in payload.child_ids:
        if not await verify_parent_owns_child(user.id, child_id):
            raise ParentChildRelationshipError(
                f"You do not have access to child {child_id}",
                details={"child_id": child_id, "parent_id": user.id}
            )

    # Fetch data with retry logic
    schools = await get_schools_for_children(payload.child_ids)

    # Create pickup with error context
    with ErrorContext("create_pickup", user_id=user.id, child_ids=payload.child_ids):
        pickup = await create_pickup_request(
            payload.child_ids,
            payload.pickup_person_id,
            payload.scheduled_time,
            payload.notes,
        )

    # Return success
    return types.CallToolResult(
        content=[types.TextContent(
            type="text",
            text=f"✓ Pickup scheduled for {len(payload.child_ids)} children"
        )],
        structuredContent={"pickup_id": pickup["id"]},
    )
```

### Example 2: Database Operation with Retry and Error Conversion

```python
from error_handlers import retry_with_backoff, DATABASE_RETRY_POLICY, ErrorContext, convert_supabase_error
from exceptions import SchoolNotFoundError

@retry_with_backoff(policy=DATABASE_RETRY_POLICY)
async def get_school_info(school_id: str) -> Dict[str, Any]:
    """Get school information with automatic retry on transient failures."""
    supabase = get_supabase()

    if not supabase:
        # Development mode - return mock data
        return {"id": school_id, "name": "Mock School"}

    try:
        with ErrorContext("get_school_info", school_id=school_id):
            response = supabase.table("schools").select("*").eq("id", school_id).single().execute()

            if not response.data:
                raise SchoolNotFoundError(
                    f"School {school_id} not found",
                    details={"school_id": school_id}
                )

            return response.data

    except SchoolNotFoundError:
        # Don't convert resource errors
        raise
    except Exception as e:
        # Convert to custom exception
        supabase_error = convert_supabase_error(e)
        logger.error("Failed to fetch school", school_id=school_id, error=str(e))
        raise supabase_error
```

### Example 3: External API Call with Circuit Breaker

```python
from error_handlers import get_circuit_breaker, EXTERNAL_API_RETRY_POLICY, retry_with_backoff
from exceptions import MotionPlusConnectionError

motion_plus_circuit = get_circuit_breaker("motion_plus")

@retry_with_backoff(policy=EXTERNAL_API_RETRY_POLICY)
async def notify_motion_plus(pickup_id: str, school_id: str):
    """Notify Motion+ API with circuit breaker protection."""

    def call_motion_plus():
        response = requests.post(
            f"{MOTION_PLUS_API_URL}/pickups",
            json={"pickup_id": pickup_id, "school_id": school_id},
            headers={"Authorization": f"Bearer {MOTION_PLUS_API_KEY}"},
            timeout=10,
        )

        if response.status_code != 200:
            raise MotionPlusConnectionError(
                f"Motion+ API returned {response.status_code}",
                details={"status_code": response.status_code, "body": response.text}
            )

        return response.json()

    try:
        # Use circuit breaker
        return motion_plus_circuit.call(call_motion_plus)

    except CircuitBreakerOpenError:
        # Circuit is open - service is down
        logger.warning("Motion+ circuit breaker open, queuing notification")
        await queue_notification_for_later(pickup_id, school_id)
        return {"status": "queued"}
```

---

## Error Codes Reference

| Error Code | HTTP Status | Description |
|-----------|-------------|-------------|
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `INVALID_INPUT` | 400 | Invalid input data |
| `INVALID_EMAIL` | 400 | Invalid email format |
| `WEAK_PASSWORD` | 400 | Password doesn't meet requirements |
| `AUTHENTICATION_ERROR` | 401 | Authentication required |
| `INVALID_CREDENTIALS` | 401 | Wrong email/password |
| `SESSION_EXPIRED` | 401 | Session has expired |
| `PERMISSION_DENIED` | 403 | Insufficient permissions |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `RESOURCE_NOT_FOUND` | 404 | Resource not found |
| `CHILD_NOT_FOUND` | 404 | Child not found |
| `SCHOOL_NOT_FOUND` | 404 | School not found |
| `USER_ALREADY_EXISTS` | 409 | User already exists |
| `BUSINESS_LOGIC_ERROR` | 422 | Business rule violation |
| `INVALID_PICKUP_TIME` | 422 | Pickup time is invalid |
| `DATABASE_ERROR` | 500 | Database error |
| `SUPABASE_ERROR` | 502 | Supabase service error |
| `DATABASE_CONNECTION_ERROR` | 503 | Cannot connect to database |
| `CIRCUIT_BREAKER_OPEN` | 503 | Service temporarily unavailable |
| `DATABASE_TIMEOUT` | 504 | Database query timed out |

---

## Testing Error Handling

See `test_error_handling.py` for comprehensive test examples covering:

- Exception hierarchy
- Error handler decorator
- Retry policies
- Circuit breaker
- Error conversion
- Integration tests

Run tests:
```bash
pytest allobye_server_python/test_error_handling.py -v
```

---

## Summary

The AllôBye error handling system provides:

✅ **Consistent error responses** with clear error codes
✅ **User-friendly messages** that guide users to resolution
✅ **Automatic retry logic** for transient failures
✅ **Circuit breaker** to prevent cascading failures
✅ **Comprehensive logging** with context for debugging
✅ **Type-safe** error handling with Python type hints
✅ **Production-ready** with fallback mechanisms

For more details, see:
- `exceptions.py` - Exception hierarchy
- `error_handlers.py` - Error handling utilities
- `test_error_handling.py` - Comprehensive tests
