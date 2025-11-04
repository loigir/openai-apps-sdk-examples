"""Comprehensive exception hierarchy for AllôBye MCP Server.

This module provides a structured exception system with:
- Clear error codes for programmatic handling
- User-friendly error messages for UI display
- HTTP status codes for proper API responses
- Error context and details for debugging
- Categorization of errors (validation, authorization, resource, external service, etc.)

Exception Categories:
- Validation: Input validation failures
- Authorization: Permission and authentication errors
- Resource: Resource not found or conflict errors
- External Service: Third-party API failures
- Database: Database connection and query errors
- Business Logic: Business rule violations
- System: Internal server errors
"""

from __future__ import annotations

from typing import Any, Dict, Optional
from http import HTTPStatus


class AllobyeError(Exception):
    """Base exception for all AllôBye errors.

    All custom exceptions inherit from this base class to provide
    consistent error handling across the application.

    Attributes:
        error_code: Unique error code for programmatic handling
        message: User-friendly error message
        details: Additional context for debugging
        http_status: HTTP status code for API responses
    """

    error_code: str = "ALLOBYE_ERROR"
    message: str = "An error occurred"
    http_status: int = HTTPStatus.INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        error_code: Optional[str] = None,
        http_status: Optional[int] = None,
    ):
        """Initialize error with optional overrides.

        Args:
            message: Custom error message (overrides class default)
            details: Additional error context
            error_code: Custom error code (overrides class default)
            http_status: Custom HTTP status (overrides class default)
        """
        self.message = message or self.__class__.message
        self.details = details or {}
        self.error_code = error_code or self.__class__.error_code
        self.http_status = http_status or self.__class__.http_status

        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for serialization.

        Returns:
            Dict containing error information
        """
        return {
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details,
            "http_status": self.http_status,
        }


# ═══════════════════════════════════════════════════════════════
# VALIDATION ERRORS
# ═══════════════════════════════════════════════════════════════


class ValidationError(AllobyeError):
    """Base class for validation errors."""

    error_code = "VALIDATION_ERROR"
    message = "Validation failed"
    http_status = HTTPStatus.BAD_REQUEST


class InvalidInputError(ValidationError):
    """Invalid input data provided."""

    error_code = "INVALID_INPUT"
    message = "Invalid input data provided"


class MissingFieldError(ValidationError):
    """Required field is missing."""

    error_code = "MISSING_FIELD"
    message = "Required field is missing"


class InvalidFormatError(ValidationError):
    """Data format is invalid."""

    error_code = "INVALID_FORMAT"
    message = "Invalid data format"


class InvalidEmailError(ValidationError):
    """Email address is invalid."""

    error_code = "INVALID_EMAIL"
    message = "Invalid email address"


class InvalidDateTimeError(ValidationError):
    """DateTime format is invalid."""

    error_code = "INVALID_DATETIME"
    message = "Invalid date/time format"


class XSSViolationError(ValidationError):
    """Potential XSS attack detected in input."""

    error_code = "XSS_VIOLATION"
    message = "Input contains potentially unsafe content"
    http_status = HTTPStatus.BAD_REQUEST


# ═══════════════════════════════════════════════════════════════
# AUTHORIZATION ERRORS
# ═══════════════════════════════════════════════════════════════


class AuthorizationError(AllobyeError):
    """Base class for authorization errors."""

    error_code = "AUTHORIZATION_ERROR"
    message = "Authorization failed"
    http_status = HTTPStatus.FORBIDDEN


class AuthenticationError(AuthorizationError):
    """User is not authenticated."""

    error_code = "AUTHENTICATION_ERROR"
    message = "Authentication required"
    http_status = HTTPStatus.UNAUTHORIZED


class InvalidCredentialsError(AuthenticationError):
    """Invalid credentials provided."""

    error_code = "INVALID_CREDENTIALS"
    message = "Invalid email or password"


class SessionExpiredError(AuthenticationError):
    """User session has expired."""

    error_code = "SESSION_EXPIRED"
    message = "Your session has expired. Please log in again"


class InvalidTokenError(AuthenticationError):
    """Authentication token is invalid."""

    error_code = "INVALID_TOKEN"
    message = "Invalid authentication token"


class PermissionDeniedError(AuthorizationError):
    """User does not have required permissions."""

    error_code = "PERMISSION_DENIED"
    message = "You do not have permission to perform this action"


class RoleRequiredError(AuthorizationError):
    """User does not have required role."""

    error_code = "ROLE_REQUIRED"
    message = "This action requires a specific role"


class EmailNotVerifiedError(AuthenticationError):
    """Email address has not been verified."""

    error_code = "EMAIL_NOT_VERIFIED"
    message = "Please verify your email address before continuing"


class WeakPasswordError(ValidationError):
    """Password does not meet security requirements."""

    error_code = "WEAK_PASSWORD"
    message = "Password does not meet security requirements"


class RateLimitExceededError(AuthorizationError):
    """Rate limit has been exceeded."""

    error_code = "RATE_LIMIT_EXCEEDED"
    message = "Too many requests. Please try again later"
    http_status = HTTPStatus.TOO_MANY_REQUESTS


class AccountLockedError(AuthenticationError):
    """Account is locked due to security reasons."""

    error_code = "ACCOUNT_LOCKED"
    message = "Account is temporarily locked. Please try again later"


class MFARequiredError(AuthenticationError):
    """Multi-factor authentication is required."""

    error_code = "MFA_REQUIRED"
    message = "Multi-factor authentication required"


# ═══════════════════════════════════════════════════════════════
# RESOURCE ERRORS
# ═══════════════════════════════════════════════════════════════


class ResourceError(AllobyeError):
    """Base class for resource errors."""

    error_code = "RESOURCE_ERROR"
    message = "Resource error"
    http_status = HTTPStatus.NOT_FOUND


class ResourceNotFoundError(ResourceError):
    """Requested resource was not found."""

    error_code = "RESOURCE_NOT_FOUND"
    message = "The requested resource was not found"


class ChildNotFoundError(ResourceNotFoundError):
    """Child not found."""

    error_code = "CHILD_NOT_FOUND"
    message = "Child not found"


class SchoolNotFoundError(ResourceNotFoundError):
    """School not found."""

    error_code = "SCHOOL_NOT_FOUND"
    message = "School not found"


class UserNotFoundError(ResourceNotFoundError):
    """User not found."""

    error_code = "USER_NOT_FOUND"
    message = "User not found"


class DelegateNotFoundError(ResourceNotFoundError):
    """Delegate not found."""

    error_code = "DELEGATE_NOT_FOUND"
    message = "Delegate not found"


class PickupNotFoundError(ResourceNotFoundError):
    """Pickup not found."""

    error_code = "PICKUP_NOT_FOUND"
    message = "Pickup not found"


class ResourceConflictError(ResourceError):
    """Resource conflict (e.g., duplicate)."""

    error_code = "RESOURCE_CONFLICT"
    message = "Resource already exists"
    http_status = HTTPStatus.CONFLICT


class UserAlreadyExistsError(ResourceConflictError):
    """User already exists."""

    error_code = "USER_ALREADY_EXISTS"
    message = "A user with this email already exists"


class DuplicatePickupError(ResourceConflictError):
    """Duplicate pickup schedule."""

    error_code = "DUPLICATE_PICKUP"
    message = "A pickup is already scheduled for this time"


# ═══════════════════════════════════════════════════════════════
# EXTERNAL SERVICE ERRORS
# ═══════════════════════════════════════════════════════════════


class ExternalServiceError(AllobyeError):
    """Base class for external service errors."""

    error_code = "EXTERNAL_SERVICE_ERROR"
    message = "External service error"
    http_status = HTTPStatus.BAD_GATEWAY


class SupabaseError(ExternalServiceError):
    """Supabase service error."""

    error_code = "SUPABASE_ERROR"
    message = "Database service error. Please try again"


class SupabaseConnectionError(SupabaseError):
    """Cannot connect to Supabase."""

    error_code = "SUPABASE_CONNECTION_ERROR"
    message = "Cannot connect to database service"
    http_status = HTTPStatus.SERVICE_UNAVAILABLE


class SupabaseTimeoutError(SupabaseError):
    """Supabase request timed out."""

    error_code = "SUPABASE_TIMEOUT"
    message = "Database request timed out. Please try again"
    http_status = HTTPStatus.GATEWAY_TIMEOUT


class MotionPlusError(ExternalServiceError):
    """Motion+ API error."""

    error_code = "MOTION_PLUS_ERROR"
    message = "Motion+ service error. Please try again"


class MotionPlusConnectionError(MotionPlusError):
    """Cannot connect to Motion+ API."""

    error_code = "MOTION_PLUS_CONNECTION_ERROR"
    message = "Cannot connect to Motion+ service"
    http_status = HTTPStatus.SERVICE_UNAVAILABLE


class EmailServiceError(ExternalServiceError):
    """Email service error."""

    error_code = "EMAIL_SERVICE_ERROR"
    message = "Email service error. Please try again"


class SMSServiceError(ExternalServiceError):
    """SMS service error."""

    error_code = "SMS_SERVICE_ERROR"
    message = "SMS service error. Please try again"


# ═══════════════════════════════════════════════════════════════
# DATABASE ERRORS
# ═══════════════════════════════════════════════════════════════


class DatabaseError(AllobyeError):
    """Base class for database errors."""

    error_code = "DATABASE_ERROR"
    message = "Database error"
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR


class DatabaseConnectionError(DatabaseError):
    """Cannot connect to database."""

    error_code = "DATABASE_CONNECTION_ERROR"
    message = "Cannot connect to database"
    http_status = HTTPStatus.SERVICE_UNAVAILABLE


class DatabaseTimeoutError(DatabaseError):
    """Database query timed out."""

    error_code = "DATABASE_TIMEOUT"
    message = "Database query timed out"
    http_status = HTTPStatus.GATEWAY_TIMEOUT


class DatabaseQueryError(DatabaseError):
    """Database query failed."""

    error_code = "DATABASE_QUERY_ERROR"
    message = "Database query failed"


class DatabaseConstraintError(DatabaseError):
    """Database constraint violation."""

    error_code = "DATABASE_CONSTRAINT_ERROR"
    message = "Database constraint violation"
    http_status = HTTPStatus.CONFLICT


# ═══════════════════════════════════════════════════════════════
# BUSINESS LOGIC ERRORS
# ═══════════════════════════════════════════════════════════════


class BusinessLogicError(AllobyeError):
    """Base class for business logic errors."""

    error_code = "BUSINESS_LOGIC_ERROR"
    message = "Business rule violation"
    http_status = HTTPStatus.UNPROCESSABLE_ENTITY


class InvalidPickupTimeError(BusinessLogicError):
    """Pickup time is invalid (e.g., in the past)."""

    error_code = "INVALID_PICKUP_TIME"
    message = "Pickup time must be in the future"


class UnauthorizedPickupError(BusinessLogicError):
    """Person is not authorized to pick up child."""

    error_code = "UNAUTHORIZED_PICKUP"
    message = "This person is not authorized to pick up this child"


class SchoolClosedError(BusinessLogicError):
    """School is closed at requested time."""

    error_code = "SCHOOL_CLOSED"
    message = "School is closed at the requested time"


class InvalidEmergencyTypeError(BusinessLogicError):
    """Emergency type is invalid."""

    error_code = "INVALID_EMERGENCY_TYPE"
    message = "Invalid emergency type"


class ChildAlreadyPickedUpError(BusinessLogicError):
    """Child has already been picked up."""

    error_code = "CHILD_ALREADY_PICKED_UP"
    message = "Child has already been picked up"


class ParentChildRelationshipError(BusinessLogicError):
    """Parent does not have relationship with child."""

    error_code = "PARENT_CHILD_RELATIONSHIP_ERROR"
    message = "You do not have access to this child"


class StaffSchoolRelationshipError(BusinessLogicError):
    """Staff does not have relationship with school."""

    error_code = "STAFF_SCHOOL_RELATIONSHIP_ERROR"
    message = "You do not have access to this school"


# ═══════════════════════════════════════════════════════════════
# SYSTEM ERRORS
# ═══════════════════════════════════════════════════════════════


class SystemError(AllobyeError):
    """Base class for system errors."""

    error_code = "SYSTEM_ERROR"
    message = "An internal error occurred. Please try again"
    http_status = HTTPStatus.INTERNAL_SERVER_ERROR


class ConfigurationError(SystemError):
    """System configuration error."""

    error_code = "CONFIGURATION_ERROR"
    message = "System configuration error"


class EnvironmentVariableError(ConfigurationError):
    """Required environment variable is missing."""

    error_code = "ENVIRONMENT_VARIABLE_ERROR"
    message = "Required environment variable is missing"


class ServiceUnavailableError(SystemError):
    """Service is temporarily unavailable."""

    error_code = "SERVICE_UNAVAILABLE"
    message = "Service is temporarily unavailable. Please try again"
    http_status = HTTPStatus.SERVICE_UNAVAILABLE


class CircuitBreakerOpenError(ServiceUnavailableError):
    """Circuit breaker is open (too many failures)."""

    error_code = "CIRCUIT_BREAKER_OPEN"
    message = "Service is temporarily unavailable due to high error rate"


class TimeoutError(SystemError):
    """Operation timed out."""

    error_code = "TIMEOUT"
    message = "Operation timed out. Please try again"
    http_status = HTTPStatus.REQUEST_TIMEOUT


# ═══════════════════════════════════════════════════════════════
# ERROR HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def get_error_from_code(error_code: str) -> type[AllobyeError]:
    """Get exception class from error code.

    Args:
        error_code: Error code string

    Returns:
        Exception class matching the error code
    """
    # Map error codes to exception classes
    error_map = {
        exc.error_code: exc
        for exc in AllobyeError.__subclasses__()
    }

    # Recursively get all subclasses
    def get_all_subclasses(cls: type) -> list[type]:
        all_subclasses = []
        for subclass in cls.__subclasses__():
            all_subclasses.append(subclass)
            all_subclasses.extend(get_all_subclasses(subclass))
        return all_subclasses

    # Build complete error map
    for exc_class in get_all_subclasses(AllobyeError):
        if hasattr(exc_class, 'error_code'):
            error_map[exc_class.error_code] = exc_class

    return error_map.get(error_code, AllobyeError)


def is_retryable_error(error: Exception) -> bool:
    """Check if an error is retryable (transient).

    Args:
        error: Exception to check

    Returns:
        True if error should be retried
    """
    retryable_types = (
        DatabaseConnectionError,
        DatabaseTimeoutError,
        SupabaseConnectionError,
        SupabaseTimeoutError,
        MotionPlusConnectionError,
        ServiceUnavailableError,
        TimeoutError,
    )

    return isinstance(error, retryable_types)


def is_client_error(error: Exception) -> bool:
    """Check if an error is a client error (4xx).

    Args:
        error: Exception to check

    Returns:
        True if error is client error
    """
    if isinstance(error, AllobyeError):
        return 400 <= error.http_status < 500
    return False


def is_server_error(error: Exception) -> bool:
    """Check if an error is a server error (5xx).

    Args:
        error: Exception to check

    Returns:
        True if error is server error
    """
    if isinstance(error, AllobyeError):
        return 500 <= error.http_status < 600
    return False
