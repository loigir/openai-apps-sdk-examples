"""Error handling middleware and utilities for AllôBye MCP Server.

This module provides:
- Error handler decorator for tool functions
- Retry logic with exponential backoff
- Circuit breaker pattern for external services
- Error logging with context
- User-friendly error message formatting
- Structured error responses

Usage:
    @error_handler
    async def my_tool_handler(arguments: Dict[str, Any]) -> types.CallToolResult:
        # Your code here
        pass

    @retry_with_backoff(max_retries=3)
    async def fetch_from_external_api():
        # Your code here
        pass
"""

from __future__ import annotations

import asyncio
import time
import traceback
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Dict, List, Optional, TypeVar, cast
from collections import defaultdict

import mcp.types as types
from pydantic import ValidationError

from exceptions import (
    AllobyeError,
    AuthenticationError,
    AuthorizationError,
    BusinessLogicError,
    CircuitBreakerOpenError,
    DatabaseError,
    ExternalServiceError,
    InvalidInputError,
    ResourceError,
    SessionExpiredError,
    SupabaseConnectionError,
    SupabaseError,
    SupabaseTimeoutError,
    SystemError,
    TimeoutError,
    ValidationError as AllobyeValidationError,
    is_retryable_error,
)

# Get logger (will be set by main module)
_logger = None


def set_logger(logger: Any) -> None:
    """Set logger for error handlers.

    Args:
        logger: Logger instance from monitoring module
    """
    global _logger
    _logger = logger


def get_logger() -> Any:
    """Get logger instance."""
    return _logger


# ═══════════════════════════════════════════════════════════════
# RETRY POLICY WITH EXPONENTIAL BACKOFF
# ═══════════════════════════════════════════════════════════════


class RetryStrategy(str, Enum):
    """Retry strategy types."""

    EXPONENTIAL = "exponential"  # Exponential backoff: 1s, 2s, 4s, 8s...
    LINEAR = "linear"  # Linear backoff: 1s, 2s, 3s, 4s...
    CONSTANT = "constant"  # Constant delay: 1s, 1s, 1s, 1s...
    FIBONACCI = "fibonacci"  # Fibonacci backoff: 1s, 1s, 2s, 3s, 5s...


class RetryPolicy:
    """Retry policy with exponential backoff and jitter.

    Implements retry logic with:
    - Configurable retry strategy (exponential, linear, constant, fibonacci)
    - Maximum retry attempts
    - Jitter to prevent thundering herd
    - Per-error-type retry decisions
    - Timeout limits
    """

    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        backoff_multiplier: float = 2.0,
        jitter: bool = True,
        timeout: Optional[float] = None,
        retryable_errors: Optional[tuple] = None,
    ):
        """Initialize retry policy.

        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            strategy: Retry strategy to use
            backoff_multiplier: Multiplier for exponential backoff
            jitter: Add random jitter to prevent thundering herd
            timeout: Maximum total time to retry (seconds)
            retryable_errors: Tuple of error types that should be retried
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.strategy = strategy
        self.backoff_multiplier = backoff_multiplier
        self.jitter = jitter
        self.timeout = timeout
        self.retryable_errors = retryable_errors or (
            DatabaseError,
            ExternalServiceError,
            SupabaseConnectionError,
            SupabaseTimeoutError,
            TimeoutError,
        )

    def get_delay(self, attempt: int) -> float:
        """Calculate delay for retry attempt.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds
        """
        if self.strategy == RetryStrategy.EXPONENTIAL:
            delay = self.initial_delay * (self.backoff_multiplier ** attempt)
        elif self.strategy == RetryStrategy.LINEAR:
            delay = self.initial_delay * (attempt + 1)
        elif self.strategy == RetryStrategy.FIBONACCI:
            # Fibonacci sequence: 1, 1, 2, 3, 5, 8, 13...
            fib = [1, 1]
            for i in range(2, attempt + 2):
                fib.append(fib[i - 1] + fib[i - 2])
            delay = self.initial_delay * fib[attempt]
        else:  # CONSTANT
            delay = self.initial_delay

        # Cap at max delay
        delay = min(delay, self.max_delay)

        # Add jitter if enabled
        if self.jitter:
            import random
            jitter_amount = delay * 0.1  # 10% jitter
            delay += random.uniform(-jitter_amount, jitter_amount)

        return max(0, delay)

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """Check if error should be retried.

        Args:
            error: Exception that occurred
            attempt: Current attempt number (0-indexed)

        Returns:
            True if should retry
        """
        # Check max retries
        if attempt >= self.max_retries:
            return False

        # Check if error type is retryable
        if isinstance(error, self.retryable_errors):
            return True

        # Check using helper function
        return is_retryable_error(error)


# Default retry policies for different scenarios
DEFAULT_RETRY_POLICY = RetryPolicy(max_retries=3, initial_delay=1.0)
DATABASE_RETRY_POLICY = RetryPolicy(max_retries=5, initial_delay=0.5, max_delay=10.0)
EXTERNAL_API_RETRY_POLICY = RetryPolicy(max_retries=3, initial_delay=2.0, max_delay=30.0)


def retry_with_backoff(
    max_retries: int = 3,
    policy: Optional[RetryPolicy] = None,
) -> Callable:
    """Decorator to retry function with exponential backoff.

    Args:
        max_retries: Maximum number of retries
        policy: Custom retry policy (optional)

    Returns:
        Decorated function
    """
    retry_policy = policy or RetryPolicy(max_retries=max_retries)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            last_error = None

            for attempt in range(retry_policy.max_retries + 1):
                try:
                    # Check timeout
                    if retry_policy.timeout:
                        elapsed = time.time() - start_time
                        if elapsed > retry_policy.timeout:
                            raise TimeoutError(
                                f"Retry timeout after {elapsed:.1f}s",
                                details={"max_timeout": retry_policy.timeout},
                            )

                    # Execute function
                    return await func(*args, **kwargs)

                except Exception as e:
                    last_error = e

                    # Check if should retry
                    if not retry_policy.should_retry(e, attempt):
                        raise

                    # Log retry attempt
                    delay = retry_policy.get_delay(attempt)
                    if get_logger():
                        get_logger().warning(
                            f"Retry attempt {attempt + 1}/{retry_policy.max_retries}",
                            function=func.__name__,
                            error=str(e),
                            delay=delay,
                        )

                    # Wait before retry
                    await asyncio.sleep(delay)

            # All retries exhausted
            if last_error:
                raise last_error

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start_time = time.time()
            last_error = None

            for attempt in range(retry_policy.max_retries + 1):
                try:
                    # Check timeout
                    if retry_policy.timeout:
                        elapsed = time.time() - start_time
                        if elapsed > retry_policy.timeout:
                            raise TimeoutError(
                                f"Retry timeout after {elapsed:.1f}s",
                                details={"max_timeout": retry_policy.timeout},
                            )

                    # Execute function
                    return func(*args, **kwargs)

                except Exception as e:
                    last_error = e

                    # Check if should retry
                    if not retry_policy.should_retry(e, attempt):
                        raise

                    # Log retry attempt
                    delay = retry_policy.get_delay(attempt)
                    if get_logger():
                        get_logger().warning(
                            f"Retry attempt {attempt + 1}/{retry_policy.max_retries}",
                            function=func.__name__,
                            error=str(e),
                            delay=delay,
                        )

                    # Wait before retry
                    time.sleep(delay)

            # All retries exhausted
            if last_error:
                raise last_error

        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# ═══════════════════════════════════════════════════════════════
# CIRCUIT BREAKER PATTERN
# ═══════════════════════════════════════════════════════════════


class CircuitBreakerState(str, Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreaker:
    """Circuit breaker for external service calls.

    Implements the circuit breaker pattern to prevent cascading failures:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered, allow limited requests
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: float = 60.0,
        expected_exception: type = ExternalServiceError,
    ):
        """Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Time to wait before attempting recovery (seconds)
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitBreakerState.CLOSED

    def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function through circuit breaker.

        Args:
            func: Function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Function result

        Raises:
            CircuitBreakerOpenError: If circuit is open
        """
        if self.state == CircuitBreakerState.OPEN:
            # Check if timeout has elapsed
            if self.last_failure_time and (time.time() - self.last_failure_time) > self.timeout:
                self.state = CircuitBreakerState.HALF_OPEN
                if get_logger():
                    get_logger().info(
                        "Circuit breaker entering HALF_OPEN state",
                        function=func.__name__,
                    )
            else:
                raise CircuitBreakerOpenError(
                    "Service is temporarily unavailable",
                    details={
                        "service": func.__name__,
                        "retry_after": int(self.timeout - (time.time() - (self.last_failure_time or 0))),
                    },
                )

        try:
            result = func(*args, **kwargs)

            # Success - reset failure count
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.CLOSED
                if get_logger():
                    get_logger().info(
                        "Circuit breaker closed (service recovered)",
                        function=func.__name__,
                    )

            self.failure_count = 0
            return result

        except self.expected_exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()

            if get_logger():
                get_logger().warning(
                    "Circuit breaker failure",
                    function=func.__name__,
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold,
                )

            # Check if should open circuit
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                if get_logger():
                    get_logger().error(
                        "Circuit breaker opened",
                        function=func.__name__,
                        failure_count=self.failure_count,
                    )

            raise


# Global circuit breakers for different services
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(service_name: str) -> CircuitBreaker:
    """Get or create circuit breaker for service.

    Args:
        service_name: Name of the service

    Returns:
        CircuitBreaker instance
    """
    if service_name not in _circuit_breakers:
        _circuit_breakers[service_name] = CircuitBreaker()
    return _circuit_breakers[service_name]


# ═══════════════════════════════════════════════════════════════
# ERROR HANDLER DECORATOR
# ═══════════════════════════════════════════════════════════════


def format_error_for_user(error: Exception) -> str:
    """Format error message for user display.

    Args:
        error: Exception to format

    Returns:
        User-friendly error message
    """
    if isinstance(error, AllobyeError):
        return error.message

    if isinstance(error, ValidationError):
        # Pydantic validation error
        errors = error.errors()
        if len(errors) == 1:
            field = errors[0].get("loc", ["field"])[-1]
            msg = errors[0].get("msg", "Invalid value")
            return f"Invalid {field}: {msg}"
        else:
            return f"Validation failed for {len(errors)} field(s)"

    # Generic error
    return "An unexpected error occurred. Please try again"


def format_error_details(error: Exception) -> Dict[str, Any]:
    """Format error details for logging.

    Args:
        error: Exception to format

    Returns:
        Dict with error details
    """
    details: Dict[str, Any] = {
        "type": type(error).__name__,
        "message": str(error),
    }

    if isinstance(error, AllobyeError):
        details.update(error.to_dict())

    if isinstance(error, ValidationError):
        details["validation_errors"] = error.errors()

    return details


def error_handler(func: Callable) -> Callable:
    """Decorator to handle errors in tool functions.

    Catches all exceptions and converts them to proper CallToolResult
    with user-friendly error messages and proper logging.

    Args:
        func: Function to wrap

    Returns:
        Wrapped function
    """

    @wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> types.CallToolResult:
        try:
            return await func(*args, **kwargs)

        except AllobyeError as e:
            # Custom application error
            if get_logger():
                get_logger().error(
                    f"Tool error: {func.__name__}",
                    error_code=e.error_code,
                    error=e.message,
                    details=e.details,
                )

            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=e.message,
                    )
                ],
                isError=True,
                _meta={
                    "error_code": e.error_code,
                    "http_status": e.http_status,
                    "details": e.details,
                },
            )

        except ValidationError as e:
            # Pydantic validation error
            error_msg = format_error_for_user(e)
            if get_logger():
                get_logger().warning(
                    f"Validation error: {func.__name__}",
                    error=error_msg,
                    details=e.errors(),
                )

            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=error_msg,
                    )
                ],
                isError=True,
                _meta={
                    "error_code": "VALIDATION_ERROR",
                    "validation_errors": e.errors(),
                },
            )

        except Exception as e:
            # Unexpected error
            error_msg = format_error_for_user(e)
            error_details = format_error_details(e)

            if get_logger():
                get_logger().error(
                    f"Unexpected error: {func.__name__}",
                    error=str(e),
                    error_type=type(e).__name__,
                    traceback=traceback.format_exc(),
                )

            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=error_msg,
                    )
                ],
                isError=True,
                _meta={
                    "error_code": "SYSTEM_ERROR",
                    "error_type": type(e).__name__,
                    "details": error_details,
                },
            )

    return wrapper


# ═══════════════════════════════════════════════════════════════
# ERROR CONTEXT MANAGER
# ═══════════════════════════════════════════════════════════════


class ErrorContext:
    """Context manager for error handling with automatic logging.

    Usage:
        with ErrorContext("database_operation", user_id="123"):
            # Your code here
            pass
    """

    def __init__(self, operation: str, **context: Any):
        """Initialize error context.

        Args:
            operation: Name of the operation
            **context: Additional context to log
        """
        self.operation = operation
        self.context = context
        self.start_time = time.time()

    def __enter__(self) -> ErrorContext:
        """Enter context."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Any,
    ) -> bool:
        """Exit context and handle errors.

        Args:
            exc_type: Exception type
            exc_val: Exception value
            exc_tb: Exception traceback

        Returns:
            False to re-raise exception
        """
        duration = time.time() - self.start_time

        if exc_val:
            # Error occurred
            if get_logger():
                get_logger().error(
                    f"Error in {self.operation}",
                    error=str(exc_val),
                    error_type=type(exc_val).__name__,
                    duration_ms=duration * 1000,
                    **self.context,
                )
        else:
            # Success
            if get_logger():
                get_logger().debug(
                    f"Completed {self.operation}",
                    duration_ms=duration * 1000,
                    **self.context,
                )

        return False  # Don't suppress exception


# ═══════════════════════════════════════════════════════════════
# FALLBACK VALUES
# ═══════════════════════════════════════════════════════════════


def with_fallback(func: Callable, fallback_value: Any, *args: Any, **kwargs: Any) -> Any:
    """Execute function with fallback value on error.

    Args:
        func: Function to execute
        fallback_value: Value to return on error
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result or fallback value
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        if get_logger():
            get_logger().warning(
                f"Using fallback value for {func.__name__}",
                error=str(e),
                fallback=fallback_value,
            )
        return fallback_value


async def with_fallback_async(
    func: Callable,
    fallback_value: Any,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Execute async function with fallback value on error.

    Args:
        func: Async function to execute
        fallback_value: Value to return on error
        *args: Function arguments
        **kwargs: Function keyword arguments

    Returns:
        Function result or fallback value
    """
    try:
        return await func(*args, **kwargs)
    except Exception as e:
        if get_logger():
            get_logger().warning(
                f"Using fallback value for {func.__name__}",
                error=str(e),
                fallback=fallback_value,
            )
        return fallback_value


# ═══════════════════════════════════════════════════════════════
# EXCEPTION CONVERSION UTILITIES
# ═══════════════════════════════════════════════════════════════


def convert_pydantic_error(error: ValidationError) -> AllobyeValidationError:
    """Convert Pydantic ValidationError to AllobyeValidationError.

    Args:
        error: Pydantic ValidationError

    Returns:
        AllobyeValidationError with formatted message
    """
    errors = error.errors()
    if len(errors) == 1:
        field = errors[0].get("loc", ["field"])[-1]
        msg = errors[0].get("msg", "Invalid value")
        return InvalidInputError(
            f"Invalid {field}: {msg}",
            details={"field": field, "validation_errors": errors},
        )
    else:
        return AllobyeValidationError(
            f"Validation failed for {len(errors)} field(s)",
            details={"validation_errors": errors},
        )


def convert_supabase_error(error: Exception) -> SupabaseError:
    """Convert Supabase error to appropriate custom error.

    Args:
        error: Supabase exception

    Returns:
        Appropriate SupabaseError subclass
    """
    error_msg = str(error).lower()

    if "timeout" in error_msg or "timed out" in error_msg:
        return SupabaseTimeoutError(
            "Database request timed out",
            details={"original_error": str(error)},
        )

    if "connection" in error_msg or "connect" in error_msg:
        return SupabaseConnectionError(
            "Cannot connect to database",
            details={"original_error": str(error)},
        )

    return SupabaseError(
        "Database error occurred",
        details={"original_error": str(error)},
    )


def safe_execute(
    func: Callable,
    error_message: str = "Operation failed",
    fallback: Any = None,
) -> Callable:
    """Decorator to safely execute a function with error handling.

    Args:
        func: Function to wrap
        error_message: Custom error message
        fallback: Fallback value on error

    Returns:
        Wrapped function
    """

    @wraps(func)
    async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if get_logger():
                get_logger().error(
                    error_message,
                    function=func.__name__,
                    error=str(e),
                )
            if fallback is not None:
                return fallback
            raise

    @wraps(func)
    def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if get_logger():
                get_logger().error(
                    error_message,
                    function=func.__name__,
                    error=str(e),
                )
            if fallback is not None:
                return fallback
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper

    return wrapper
