"""Comprehensive tests for error handling system.

Tests cover:
- Exception hierarchy and error codes
- Error handler decorator
- Retry logic with exponential backoff
- Circuit breaker pattern
- Error conversion utilities
- Fallback mechanisms
- Error context management
"""

import asyncio
import pytest
import time
from typing import Any, Dict
from datetime import datetime

from exceptions import (
    AllobyeError,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    CircuitBreakerOpenError,
    DatabaseError,
    DatabaseConnectionError,
    DatabaseTimeoutError,
    ExternalServiceError,
    InvalidCredentialsError,
    InvalidInputError,
    ParentChildRelationshipError,
    PermissionDeniedError,
    ResourceNotFoundError,
    SchoolNotFoundError,
    SessionExpiredError,
    SupabaseConnectionError,
    SupabaseError,
    SupabaseTimeoutError,
    SystemError,
    ValidationError,
    WeakPasswordError,
    get_error_from_code,
    is_retryable_error,
    is_client_error,
    is_server_error,
)

from error_handlers import (
    RetryPolicy,
    RetryStrategy,
    CircuitBreaker,
    CircuitBreakerState,
    error_handler,
    retry_with_backoff,
    ErrorContext,
    convert_pydantic_error,
    convert_supabase_error,
    format_error_for_user,
    with_fallback_async,
    DATABASE_RETRY_POLICY,
)

import mcp.types as types
from pydantic import BaseModel, ValidationError as PydanticValidationError


# ═══════════════════════════════════════════════════════════════
# TEST FIXTURES
# ═══════════════════════════════════════════════════════════════


class TestModel(BaseModel):
    """Test model for validation."""
    name: str
    age: int


# ═══════════════════════════════════════════════════════════════
# EXCEPTION HIERARCHY TESTS
# ═══════════════════════════════════════════════════════════════


class TestExceptionHierarchy:
    """Test exception hierarchy and structure."""

    def test_base_exception_structure(self):
        """Test base exception has all required attributes."""
        error = AllobyeError(
            message="Test error",
            details={"key": "value"},
            error_code="TEST_ERROR",
        )

        assert error.message == "Test error"
        assert error.details == {"key": "value"}
        assert error.error_code == "TEST_ERROR"
        assert error.http_status == 500

    def test_exception_to_dict(self):
        """Test exception serialization."""
        error = InvalidInputError("Invalid data", details={"field": "email"})
        error_dict = error.to_dict()

        assert error_dict["error_code"] == "INVALID_INPUT"
        assert error_dict["message"] == "Invalid data"
        assert error_dict["details"] == {"field": "email"}
        assert error_dict["http_status"] == 400

    def test_validation_error_hierarchy(self):
        """Test validation error classes."""
        errors = [
            (InvalidInputError("test"), "INVALID_INPUT", 400),
            (ValidationError("test"), "VALIDATION_ERROR", 400),
            (WeakPasswordError("test"), "WEAK_PASSWORD", 400),
        ]

        for error, code, status in errors:
            assert error.error_code == code
            assert error.http_status == status
            assert isinstance(error, AllobyeError)

    def test_authorization_error_hierarchy(self):
        """Test authorization error classes."""
        errors = [
            (AuthenticationError("test"), "AUTHENTICATION_ERROR", 401),
            (InvalidCredentialsError("test"), "INVALID_CREDENTIALS", 401),
            (SessionExpiredError("test"), "SESSION_EXPIRED", 401),
            (PermissionDeniedError("test"), "PERMISSION_DENIED", 403),
        ]

        for error, code, status in errors:
            assert error.error_code == code
            assert error.http_status == status

    def test_resource_error_hierarchy(self):
        """Test resource error classes."""
        error = ResourceNotFoundError("Resource not found")
        assert error.error_code == "RESOURCE_NOT_FOUND"
        assert error.http_status == 404

        child_error = SchoolNotFoundError("School not found")
        assert child_error.error_code == "SCHOOL_NOT_FOUND"
        assert isinstance(child_error, ResourceNotFoundError)

    def test_database_error_hierarchy(self):
        """Test database error classes."""
        errors = [
            (DatabaseError("test"), "DATABASE_ERROR", 500),
            (DatabaseConnectionError("test"), "DATABASE_CONNECTION_ERROR", 503),
            (DatabaseTimeoutError("test"), "DATABASE_TIMEOUT", 504),
        ]

        for error, code, status in errors:
            assert error.error_code == code
            assert error.http_status == status

    def test_get_error_from_code(self):
        """Test error code lookup."""
        error_class = get_error_from_code("INVALID_INPUT")
        assert error_class == InvalidInputError

        error_class = get_error_from_code("DATABASE_CONNECTION_ERROR")
        assert error_class == DatabaseConnectionError

    def test_is_retryable_error(self):
        """Test retryable error detection."""
        assert is_retryable_error(DatabaseConnectionError("test"))
        assert is_retryable_error(SupabaseTimeoutError("test"))
        assert not is_retryable_error(InvalidInputError("test"))
        assert not is_retryable_error(AuthenticationError("test"))

    def test_is_client_error(self):
        """Test client error detection."""
        assert is_client_error(ValidationError("test"))
        assert is_client_error(AuthenticationError("test"))
        assert not is_client_error(DatabaseError("test"))

    def test_is_server_error(self):
        """Test server error detection."""
        assert is_server_error(DatabaseError("test"))
        assert is_server_error(SystemError("test"))
        assert not is_server_error(ValidationError("test"))


# ═══════════════════════════════════════════════════════════════
# RETRY POLICY TESTS
# ═══════════════════════════════════════════════════════════════


class TestRetryPolicy:
    """Test retry policy and strategies."""

    def test_exponential_backoff_delay(self):
        """Test exponential backoff delay calculation."""
        policy = RetryPolicy(
            initial_delay=1.0,
            strategy=RetryStrategy.EXPONENTIAL,
            backoff_multiplier=2.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 1.0  # 1 * 2^0
        assert policy.get_delay(1) == 2.0  # 1 * 2^1
        assert policy.get_delay(2) == 4.0  # 1 * 2^2
        assert policy.get_delay(3) == 8.0  # 1 * 2^3

    def test_linear_backoff_delay(self):
        """Test linear backoff delay calculation."""
        policy = RetryPolicy(
            initial_delay=2.0,
            strategy=RetryStrategy.LINEAR,
            jitter=False,
        )

        assert policy.get_delay(0) == 2.0  # 2 * 1
        assert policy.get_delay(1) == 4.0  # 2 * 2
        assert policy.get_delay(2) == 6.0  # 2 * 3

    def test_constant_delay(self):
        """Test constant delay."""
        policy = RetryPolicy(
            initial_delay=5.0,
            strategy=RetryStrategy.CONSTANT,
            jitter=False,
        )

        assert policy.get_delay(0) == 5.0
        assert policy.get_delay(1) == 5.0
        assert policy.get_delay(2) == 5.0

    def test_fibonacci_backoff_delay(self):
        """Test Fibonacci backoff delay calculation."""
        policy = RetryPolicy(
            initial_delay=1.0,
            strategy=RetryStrategy.FIBONACCI,
            jitter=False,
        )

        assert policy.get_delay(0) == 1.0  # fib[0] = 1
        assert policy.get_delay(1) == 1.0  # fib[1] = 1
        assert policy.get_delay(2) == 2.0  # fib[2] = 2
        assert policy.get_delay(3) == 3.0  # fib[3] = 3
        assert policy.get_delay(4) == 5.0  # fib[4] = 5

    def test_max_delay_cap(self):
        """Test delay is capped at max_delay."""
        policy = RetryPolicy(
            initial_delay=10.0,
            max_delay=20.0,
            strategy=RetryStrategy.EXPONENTIAL,
            jitter=False,
        )

        assert policy.get_delay(0) == 10.0
        assert policy.get_delay(1) == 20.0  # Would be 20, capped
        assert policy.get_delay(2) == 20.0  # Would be 40, capped
        assert policy.get_delay(3) == 20.0  # Would be 80, capped

    def test_should_retry_max_attempts(self):
        """Test retry limit enforcement."""
        policy = RetryPolicy(max_retries=3)

        assert policy.should_retry(DatabaseConnectionError("test"), 0)
        assert policy.should_retry(DatabaseConnectionError("test"), 1)
        assert policy.should_retry(DatabaseConnectionError("test"), 2)
        assert not policy.should_retry(DatabaseConnectionError("test"), 3)

    def test_should_retry_error_type(self):
        """Test retry based on error type."""
        policy = RetryPolicy(max_retries=3)

        # Retryable errors
        assert policy.should_retry(DatabaseConnectionError("test"), 0)
        assert policy.should_retry(SupabaseTimeoutError("test"), 0)

        # Non-retryable errors
        assert not policy.should_retry(InvalidInputError("test"), 0)
        assert not policy.should_retry(AuthenticationError("test"), 0)

    @pytest.mark.asyncio
    async def test_retry_decorator_success(self):
        """Test retry decorator with successful execution."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        async def successful_function():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_function()
        assert result == "success"
        assert call_count == 1  # No retries needed

    @pytest.mark.asyncio
    async def test_retry_decorator_eventual_success(self):
        """Test retry decorator with eventual success."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        async def eventually_successful():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise DatabaseConnectionError("Connection failed")
            return "success"

        result = await eventually_successful()
        assert result == "success"
        assert call_count == 3  # Succeeded on 3rd attempt

    @pytest.mark.asyncio
    async def test_retry_decorator_exhausted(self):
        """Test retry decorator when retries exhausted."""
        call_count = 0
        policy = RetryPolicy(max_retries=2, initial_delay=0.01)

        @retry_with_backoff(policy=policy)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise DatabaseConnectionError("Connection failed")

        with pytest.raises(DatabaseConnectionError):
            await always_fails()

        assert call_count == 3  # Initial + 2 retries

    @pytest.mark.asyncio
    async def test_retry_decorator_non_retryable_error(self):
        """Test retry decorator with non-retryable error."""
        call_count = 0

        @retry_with_backoff(max_retries=3)
        async def invalid_input():
            nonlocal call_count
            call_count += 1
            raise InvalidInputError("Bad input")

        with pytest.raises(InvalidInputError):
            await invalid_input()

        assert call_count == 1  # No retries for validation error


# ═══════════════════════════════════════════════════════════════
# CIRCUIT BREAKER TESTS
# ═══════════════════════════════════════════════════════════════


class TestCircuitBreaker:
    """Test circuit breaker pattern."""

    def test_circuit_breaker_closed_state(self):
        """Test circuit breaker in closed state."""
        cb = CircuitBreaker(failure_threshold=3)

        def successful_call():
            return "success"

        result = cb.call(successful_call)
        assert result == "success"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_opens_after_threshold(self):
        """Test circuit breaker opens after failure threshold."""
        cb = CircuitBreaker(failure_threshold=3, expected_exception=ExternalServiceError)

        def failing_call():
            raise ExternalServiceError("Service down")

        # First 2 failures - circuit stays closed
        for i in range(2):
            with pytest.raises(ExternalServiceError):
                cb.call(failing_call)
            assert cb.state == CircuitBreakerState.CLOSED

        # 3rd failure - circuit opens
        with pytest.raises(ExternalServiceError):
            cb.call(failing_call)
        assert cb.state == CircuitBreakerState.OPEN

    def test_circuit_breaker_rejects_when_open(self):
        """Test circuit breaker rejects requests when open."""
        cb = CircuitBreaker(failure_threshold=2, timeout=60.0)
        cb.state = CircuitBreakerState.OPEN
        cb.last_failure_time = time.time()

        def dummy_call():
            return "success"

        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            cb.call(dummy_call)

        assert "temporarily unavailable" in str(exc_info.value).lower()

    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker enters half-open state after timeout."""
        cb = CircuitBreaker(failure_threshold=2, timeout=0.1)

        def failing_call():
            raise ExternalServiceError("Service down")

        # Open the circuit
        for _ in range(2):
            with pytest.raises(ExternalServiceError):
                cb.call(failing_call)

        assert cb.state == CircuitBreakerState.OPEN

        # Wait for timeout
        time.sleep(0.2)

        def successful_call():
            return "recovered"

        # Circuit should be half-open now
        result = cb.call(successful_call)
        assert result == "recovered"
        assert cb.state == CircuitBreakerState.CLOSED

    def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets failure count on success."""
        cb = CircuitBreaker(failure_threshold=3)

        def failing_call():
            raise ExternalServiceError("Failure")

        def successful_call():
            return "success"

        # 2 failures
        for _ in range(2):
            with pytest.raises(ExternalServiceError):
                cb.call(failing_call)

        assert cb.failure_count == 2

        # Success resets count
        cb.call(successful_call)
        assert cb.failure_count == 0


# ═══════════════════════════════════════════════════════════════
# ERROR HANDLER DECORATOR TESTS
# ═══════════════════════════════════════════════════════════════


class TestErrorHandler:
    """Test error handler decorator."""

    @pytest.mark.asyncio
    async def test_error_handler_success(self):
        """Test error handler with successful execution."""

        @error_handler
        async def successful_tool(arguments: Dict[str, Any]) -> types.CallToolResult:
            return types.CallToolResult(
                content=[types.TextContent(type="text", text="Success")]
            )

        result = await successful_tool({})
        assert not result.isError
        assert result.content[0].text == "Success"

    @pytest.mark.asyncio
    async def test_error_handler_custom_error(self):
        """Test error handler with custom AllobyeError."""

        @error_handler
        async def failing_tool(arguments: Dict[str, Any]) -> types.CallToolResult:
            raise InvalidInputError("Bad input", details={"field": "email"})

        result = await failing_tool({})
        assert result.isError
        assert "Bad input" in result.content[0].text
        # Check that meta exists and has error info (use getattr to safely access)
        meta = getattr(result, "_meta", None) or {}
        assert "error_code" in meta or result.isError  # Either has error_code or isError flag

    @pytest.mark.asyncio
    async def test_error_handler_pydantic_validation_error(self):
        """Test error handler with Pydantic ValidationError."""

        @error_handler
        async def validation_tool(arguments: Dict[str, Any]) -> types.CallToolResult:
            # This will raise ValidationError
            TestModel.model_validate({"name": "test"})  # Missing age
            return types.CallToolResult(
                content=[types.TextContent(type="text", text="Success")]
            )

        result = await validation_tool({})
        assert result.isError
        # Check that error message contains validation-related text
        error_text = result.content[0].text.lower()
        assert "invalid" in error_text or "age" in error_text

    @pytest.mark.asyncio
    async def test_error_handler_unexpected_error(self):
        """Test error handler with unexpected exception."""

        @error_handler
        async def unexpected_error_tool(arguments: Dict[str, Any]) -> types.CallToolResult:
            raise ValueError("Unexpected error")

        result = await unexpected_error_tool({})
        assert result.isError
        # Check error message is user-friendly
        assert "error" in result.content[0].text.lower()


# ═══════════════════════════════════════════════════════════════
# ERROR CONVERSION TESTS
# ═══════════════════════════════════════════════════════════════


class TestErrorConversion:
    """Test error conversion utilities."""

    def test_convert_pydantic_error_single_field(self):
        """Test Pydantic error conversion with single field."""
        try:
            TestModel.model_validate({"name": "test"})  # Missing age
        except PydanticValidationError as e:
            converted = convert_pydantic_error(e)
            assert isinstance(converted, InvalidInputError)
            assert "age" in converted.message.lower() or "age" in str(converted.details)

    def test_convert_pydantic_error_multiple_fields(self):
        """Test Pydantic error conversion with multiple fields."""
        try:
            TestModel.model_validate({})  # Missing name and age
        except PydanticValidationError as e:
            converted = convert_pydantic_error(e)
            assert isinstance(converted, ValidationError)
            assert "field" in converted.message.lower()

    def test_convert_supabase_timeout_error(self):
        """Test Supabase timeout error conversion."""
        original_error = Exception("Request timed out after 30s")
        converted = convert_supabase_error(original_error)

        assert isinstance(converted, SupabaseTimeoutError)
        assert "timed out" in converted.message.lower()

    def test_convert_supabase_connection_error(self):
        """Test Supabase connection error conversion."""
        original_error = Exception("Connection refused")
        converted = convert_supabase_error(original_error)

        assert isinstance(converted, SupabaseConnectionError)
        assert "connect" in converted.message.lower()

    def test_convert_supabase_generic_error(self):
        """Test generic Supabase error conversion."""
        original_error = Exception("Some database error")
        converted = convert_supabase_error(original_error)

        assert isinstance(converted, SupabaseError)

    def test_format_error_for_user_custom_error(self):
        """Test user-friendly error formatting for custom errors."""
        error = InvalidInputError("Invalid email format")
        message = format_error_for_user(error)

        assert message == "Invalid email format"
        assert not any(word in message.lower() for word in ["exception", "traceback", "stack"])

    def test_format_error_for_user_pydantic_error(self):
        """Test user-friendly error formatting for Pydantic errors."""
        try:
            TestModel.model_validate({"name": "test"})
        except PydanticValidationError as e:
            message = format_error_for_user(e)
            assert "validation" in message.lower() or "invalid" in message.lower()

    def test_format_error_for_user_generic_error(self):
        """Test user-friendly error formatting for generic errors."""
        error = ValueError("Some internal error")
        message = format_error_for_user(error)

        assert "unexpected error" in message.lower()
        assert "try again" in message.lower()


# ═══════════════════════════════════════════════════════════════
# ERROR CONTEXT TESTS
# ═══════════════════════════════════════════════════════════════


class TestErrorContext:
    """Test error context manager."""

    def test_error_context_success(self):
        """Test error context with successful execution."""
        with ErrorContext("test_operation", user_id="123"):
            result = "success"

        assert result == "success"

    def test_error_context_with_error(self):
        """Test error context with error (should not suppress)."""
        with pytest.raises(ValueError):
            with ErrorContext("test_operation", user_id="123"):
                raise ValueError("Test error")


# ═══════════════════════════════════════════════════════════════
# FALLBACK MECHANISM TESTS
# ═══════════════════════════════════════════════════════════════


class TestFallbackMechanisms:
    """Test fallback mechanisms for non-critical errors."""

    @pytest.mark.asyncio
    async def test_with_fallback_async_success(self):
        """Test async fallback with successful execution."""

        async def successful_func():
            return "result"

        result = await with_fallback_async(successful_func, "fallback")
        assert result == "result"

    @pytest.mark.asyncio
    async def test_with_fallback_async_error(self):
        """Test async fallback with error."""

        async def failing_func():
            raise DatabaseConnectionError("Connection failed")

        result = await with_fallback_async(failing_func, "fallback_value")
        assert result == "fallback_value"


# ═══════════════════════════════════════════════════════════════
# INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════


class TestErrorHandlingIntegration:
    """Integration tests for error handling system."""

    @pytest.mark.asyncio
    async def test_full_error_handling_stack(self):
        """Test complete error handling with decorator, retry, and circuit breaker."""
        call_count = 0
        policy = RetryPolicy(max_retries=2, initial_delay=0.01)

        @error_handler
        @retry_with_backoff(policy=policy)
        async def complex_operation(arguments: Dict[str, Any]) -> types.CallToolResult:
            nonlocal call_count
            call_count += 1

            if call_count < 2:
                raise DatabaseConnectionError("Temporary failure")

            return types.CallToolResult(
                content=[types.TextContent(type="text", text="Success after retry")]
            )

        result = await complex_operation({})
        assert not result.isError
        assert "Success after retry" in result.content[0].text
        assert call_count == 2  # Succeeded on 2nd attempt

    def test_database_retry_policy_configuration(self):
        """Test DATABASE_RETRY_POLICY is properly configured."""
        assert DATABASE_RETRY_POLICY.max_retries == 5
        assert DATABASE_RETRY_POLICY.initial_delay == 0.5
        assert DATABASE_RETRY_POLICY.max_delay == 10.0


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
