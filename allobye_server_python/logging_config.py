"""Advanced structured logging configuration for AllôBye MCP Server.

This module provides:
- Correlation ID propagation across all operations
- Context managers for logging scopes
- Log aggregation patterns
- Performance timing decorators
- Thread-safe logging context
- Multiple output handlers (console, file, syslog)
"""

from __future__ import annotations

import contextvars
import functools
import logging
import logging.handlers
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Generator, Optional, TypeVar, Union
from uuid import uuid4

# ═══════════════════════════════════════════════════════════════
# CONTEXT VARIABLES FOR CORRELATION
# ═══════════════════════════════════════════════════════════════

# Thread-safe context storage for correlation IDs and metadata
correlation_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "correlation_id", default=None
)
request_context_var: contextvars.ContextVar[Dict[str, Any]] = contextvars.ContextVar(
    "request_context", default_factory=dict
)
trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "trace_id", default=None
)
span_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "span_id", default=None
)
parent_span_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar(
    "parent_span_id", default=None
)

F = TypeVar('F', bound=Callable[..., Any])


# ═══════════════════════════════════════════════════════════════
# CORRELATION ID MANAGEMENT
# ═══════════════════════════════════════════════════════════════


def get_correlation_id() -> str:
    """Get current correlation ID or generate a new one."""
    cid = correlation_id_var.get()
    if not cid:
        cid = str(uuid4())
        correlation_id_var.set(cid)
    return cid


def set_correlation_id(correlation_id: str) -> None:
    """Set correlation ID for current context."""
    correlation_id_var.set(correlation_id)


def get_trace_id() -> Optional[str]:
    """Get current trace ID."""
    return trace_id_var.get()


def set_trace_id(trace_id: str) -> None:
    """Set trace ID for distributed tracing."""
    trace_id_var.set(trace_id)


def get_span_id() -> Optional[str]:
    """Get current span ID."""
    return span_id_var.get()


def set_span_id(span_id: str) -> None:
    """Set span ID for distributed tracing."""
    span_id_var.set(span_id)


def get_parent_span_id() -> Optional[str]:
    """Get parent span ID."""
    return parent_span_id_var.get()


def set_parent_span_id(parent_span_id: Optional[str]) -> None:
    """Set parent span ID for distributed tracing."""
    parent_span_id_var.set(parent_span_id)


def get_request_context() -> Dict[str, Any]:
    """Get current request context."""
    return request_context_var.get() or {}


def update_request_context(**kwargs: Any) -> None:
    """Update request context with additional metadata."""
    ctx = request_context_var.get() or {}
    ctx.update(kwargs)
    request_context_var.set(ctx)


def clear_request_context() -> None:
    """Clear all request context."""
    correlation_id_var.set(None)
    trace_id_var.set(None)
    span_id_var.set(None)
    parent_span_id_var.set(None)
    request_context_var.set({})


# ═══════════════════════════════════════════════════════════════
# CONTEXT MANAGERS
# ═══════════════════════════════════════════════════════════════


@contextmanager
def logging_scope(
    operation: str,
    **metadata: Any
) -> Generator[Dict[str, Any], None, None]:
    """Context manager for logging scope with automatic timing.

    Usage:
        with logging_scope("database_query", table="users", action="select") as ctx:
            # Operation code
            ctx["rows_affected"] = 10
    """
    # Generate correlation ID if not present
    correlation_id = get_correlation_id()

    # Update context
    scope_metadata = {
        "operation": operation,
        "correlation_id": correlation_id,
        **metadata,
    }
    update_request_context(**scope_metadata)

    start_time = time.time()
    scope_context: Dict[str, Any] = {"operation": operation}

    try:
        yield scope_context
    finally:
        duration_ms = (time.time() - start_time) * 1000
        scope_context["duration_ms"] = duration_ms

        # Log completion
        logger = logging.getLogger("allobye.scope")
        logger.info(
            f"Operation completed: {operation}",
            extra={
                **scope_metadata,
                **scope_context,
                "duration_ms": duration_ms,
            }
        )


@contextmanager
def correlation_context(
    correlation_id: Optional[str] = None,
    **metadata: Any
) -> Generator[str, None, None]:
    """Context manager for correlation ID scope.

    Usage:
        with correlation_context(user_id="user_123") as cid:
            # All logs in this scope will have the same correlation_id
            logger.info("Processing request")
    """
    # Save previous context
    prev_cid = correlation_id_var.get()
    prev_ctx = request_context_var.get()

    # Set new context
    cid = correlation_id or str(uuid4())
    set_correlation_id(cid)
    update_request_context(**metadata)

    try:
        yield cid
    finally:
        # Restore previous context
        correlation_id_var.set(prev_cid)
        request_context_var.set(prev_ctx)


@contextmanager
def trace_context(
    trace_id: Optional[str] = None,
    span_name: Optional[str] = None,
    parent_span_id: Optional[str] = None,
) -> Generator[Dict[str, str], None, None]:
    """Context manager for distributed tracing.

    Usage:
        with trace_context(span_name="api_call") as trace_info:
            # All operations will be part of this trace
            trace_id = trace_info["trace_id"]
            span_id = trace_info["span_id"]
    """
    # Save previous tracing context
    prev_trace_id = trace_id_var.get()
    prev_span_id = span_id_var.get()
    prev_parent_span_id = parent_span_id_var.get()

    # Generate new IDs if not provided
    tid = trace_id or prev_trace_id or str(uuid4())
    sid = str(uuid4())

    # Set tracing context
    set_trace_id(tid)
    set_span_id(sid)
    set_parent_span_id(parent_span_id or prev_span_id)

    trace_info = {
        "trace_id": tid,
        "span_id": sid,
        "parent_span_id": parent_span_id or prev_span_id or "",
        "span_name": span_name or "unnamed_span",
    }

    start_time = time.time()

    try:
        yield trace_info
    finally:
        duration_ms = (time.time() - start_time) * 1000

        # Log span completion
        logger = logging.getLogger("allobye.trace")
        logger.debug(
            f"Span completed: {span_name}",
            extra={
                **trace_info,
                "duration_ms": duration_ms,
            }
        )

        # Restore previous context
        trace_id_var.set(prev_trace_id)
        span_id_var.set(prev_span_id)
        parent_span_id_var.set(prev_parent_span_id)


# ═══════════════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════════════


def log_execution_time(func: F) -> F:
    """Decorator to log function execution time.

    Usage:
        @log_execution_time
        def process_data():
            pass
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        func_name = f"{func.__module__}.{func.__name__}"

        logger = logging.getLogger("allobye.performance")
        logger.debug(f"Starting: {func_name}")

        try:
            result = wrapper(*args, **kwargs)
            duration_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Completed: {func_name}",
                extra={
                    "function": func_name,
                    "duration_ms": duration_ms,
                    "correlation_id": get_correlation_id(),
                }
            )

            return result
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000

            logger.error(
                f"Failed: {func_name}",
                extra={
                    "function": func_name,
                    "duration_ms": duration_ms,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "correlation_id": get_correlation_id(),
                }
            )
            raise

    return wrapper  # type: ignore


def traced(span_name: Optional[str] = None) -> Callable[[F], F]:
    """Decorator to automatically trace function execution.

    Usage:
        @traced(span_name="database_query")
        def fetch_users():
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            name = span_name or f"{func.__module__}.{func.__name__}"

            with trace_context(span_name=name):
                return func(*args, **kwargs)

        return wrapper  # type: ignore

    return decorator


# ═══════════════════════════════════════════════════════════════
# STRUCTURED LOG FORMATTER
# ═══════════════════════════════════════════════════════════════


class StructuredFormatter(logging.Formatter):
    """JSON formatter with correlation IDs and context."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        import json

        # Base log entry
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add correlation ID
        correlation_id = get_correlation_id()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        # Add trace context
        trace_id = get_trace_id()
        if trace_id:
            log_entry["trace_id"] = trace_id

        span_id = get_span_id()
        if span_id:
            log_entry["span_id"] = span_id

        parent_span_id = get_parent_span_id()
        if parent_span_id:
            log_entry["parent_span_id"] = parent_span_id

        # Add request context
        context = get_request_context()
        if context:
            log_entry["context"] = context

        # Add extra fields from record
        if hasattr(record, "__dict__"):
            for key, value in record.__dict__.items():
                if key not in [
                    "name", "msg", "args", "created", "filename", "funcName",
                    "levelname", "levelno", "lineno", "module", "msecs",
                    "message", "pathname", "process", "processName",
                    "relativeCreated", "thread", "threadName", "exc_info",
                    "exc_text", "stack_info",
                ]:
                    log_entry[key] = value

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry, default=str)


# ═══════════════════════════════════════════════════════════════
# LOGGING CONFIGURATION
# ═══════════════════════════════════════════════════════════════


def setup_logging(
    log_level: str = "INFO",
    log_file: Optional[Path] = None,
    enable_syslog: bool = False,
    syslog_address: str = "/dev/log",
) -> None:
    """Configure structured logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        enable_syslog: Enable syslog handler
        syslog_address: Syslog address (for remote syslog)
    """
    # Get root logger
    root_logger = logging.getLogger("allobye")
    root_logger.setLevel(getattr(logging, log_level.upper()))

    # Remove existing handlers
    root_logger.handlers.clear()

    # Console handler with structured formatter
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, log_level.upper()))
    console_handler.setFormatter(StructuredFormatter())
    root_logger.addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(getattr(logging, log_level.upper()))
        file_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(file_handler)

    # Syslog handler (if enabled)
    if enable_syslog:
        try:
            syslog_handler = logging.handlers.SysLogHandler(address=syslog_address)
            syslog_handler.setLevel(getattr(logging, log_level.upper()))
            syslog_handler.setFormatter(StructuredFormatter())
            root_logger.addHandler(syslog_handler)
        except Exception as e:
            root_logger.warning(f"Failed to setup syslog handler: {e}")

    # Prevent propagation to avoid duplicate logs
    root_logger.propagate = False

    root_logger.info(
        "Logging configured",
        extra={
            "log_level": log_level,
            "log_file": str(log_file) if log_file else None,
            "enable_syslog": enable_syslog,
        }
    )


# ═══════════════════════════════════════════════════════════════
# LOG AGGREGATION PATTERNS
# ═══════════════════════════════════════════════════════════════


class LogAggregator:
    """Aggregates logs for batch processing or sampling."""

    def __init__(self, batch_size: int = 100, flush_interval: float = 60.0):
        """Initialize log aggregator.

        Args:
            batch_size: Number of logs to buffer before flushing
            flush_interval: Time interval (seconds) to force flush
        """
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.buffer: list[Dict[str, Any]] = []
        self.last_flush = time.time()

    def add_log(self, log_entry: Dict[str, Any]) -> None:
        """Add log entry to buffer."""
        self.buffer.append(log_entry)

        # Flush if batch is full or interval exceeded
        if len(self.buffer) >= self.batch_size:
            self.flush()
        elif time.time() - self.last_flush > self.flush_interval:
            self.flush()

    def flush(self) -> list[Dict[str, Any]]:
        """Flush buffered logs and return them."""
        logs = self.buffer.copy()
        self.buffer.clear()
        self.last_flush = time.time()
        return logs


class SamplingLogger:
    """Logger that samples logs to reduce volume."""

    def __init__(self, sample_rate: float = 0.1):
        """Initialize sampling logger.

        Args:
            sample_rate: Fraction of logs to keep (0.0 to 1.0)
        """
        import random
        self.sample_rate = sample_rate
        self.random = random.Random()

    def should_log(self) -> bool:
        """Determine if this log should be kept."""
        return self.random.random() < self.sample_rate


# ═══════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def get_logger(name: str) -> logging.Logger:
    """Get a logger with the allobye prefix.

    Usage:
        logger = get_logger(__name__)
        logger.info("Processing request")
    """
    return logging.getLogger(f"allobye.{name}")
