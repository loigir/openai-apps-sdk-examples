"""Comprehensive observability and monitoring system for AllôBye MCP server.

This module provides:
- Structured JSON logging with log levels
- Performance metrics (latency, throughput, error rates)
- Request tracing with correlation IDs
- Database query monitoring
- Real-time metrics collection
- Prometheus format metrics export
- Alerting rules and thresholds
"""

from __future__ import annotations

import json
import logging
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional
from uuid import uuid4


# ═══════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════

@dataclass
class AlertingConfig:
    """Configuration for alerting thresholds."""
    error_rate_threshold: float = 0.05  # 5%
    latency_threshold_ms: float = 1000.0  # 1 second
    db_failure_threshold: int = 3  # consecutive failures
    enable_alerts: bool = True


@dataclass
class MonitoringConfig:
    """Global monitoring configuration."""
    service_name: str = "allobye-mcp-server"
    environment: str = "production"
    log_level: str = "INFO"
    enable_tracing: bool = True
    enable_metrics: bool = True
    alerting: AlertingConfig = field(default_factory=AlertingConfig)
    metrics_retention_seconds: int = 3600  # 1 hour


# Global config instance
_config = MonitoringConfig()


def configure_monitoring(**kwargs) -> MonitoringConfig:
    """Update global monitoring configuration."""
    global _config
    for key, value in kwargs.items():
        if hasattr(_config, key):
            setattr(_config, key, value)
    return _config


# ═══════════════════════════════════════════════════════════════
# STRUCTURED LOGGING
# ═══════════════════════════════════════════════════════════════

class StructuredLogger:
    """JSON structured logger with contextual fields."""

    def __init__(self, name: str, config: MonitoringConfig):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, config.log_level))
        self.config = config
        self._request_context: Dict[str, Any] = {}

        # Configure JSON formatter
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        self.logger.handlers = [handler]

    def set_context(self, **context):
        """Set request-level context fields."""
        self._request_context.update(context)

    def clear_context(self):
        """Clear request context."""
        self._request_context = {}

    def _format_log(self, level: str, message: str, **extra) -> Dict[str, Any]:
        """Format log entry as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": level,
            "service": self.config.service_name,
            "environment": self.config.environment,
            "message": message,
            **self._request_context,
            **extra,
        }
        return log_entry

    def debug(self, message: str, **extra):
        """Log debug message."""
        log_data = self._format_log("DEBUG", message, **extra)
        self.logger.debug(json.dumps(log_data))

    def info(self, message: str, **extra):
        """Log info message."""
        log_data = self._format_log("INFO", message, **extra)
        self.logger.info(json.dumps(log_data))

    def warning(self, message: str, **extra):
        """Log warning message."""
        log_data = self._format_log("WARNING", message, **extra)
        self.logger.warning(json.dumps(log_data))

    def error(self, message: str, **extra):
        """Log error message."""
        log_data = self._format_log("ERROR", message, **extra)
        self.logger.error(json.dumps(log_data))

    def critical(self, message: str, **extra):
        """Log critical message."""
        log_data = self._format_log("CRITICAL", message, **extra)
        self.logger.critical(json.dumps(log_data))


class JsonFormatter(logging.Formatter):
    """JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Message is already JSON string from StructuredLogger
        return record.getMessage()


# ═══════════════════════════════════════════════════════════════
# METRICS COLLECTION
# ═══════════════════════════════════════════════════════════════

@dataclass
class Metric:
    """Single metric data point."""
    name: str
    value: float
    timestamp: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class ToolMetrics:
    """Metrics for a single tool."""
    call_count: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average latency."""
        if self.call_count == 0:
            return 0.0
        return self.total_latency_ms / self.call_count

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.call_count == 0:
            return 0.0
        return self.error_count / self.call_count

    @property
    def success_rate(self) -> float:
        """Calculate success rate."""
        if self.call_count == 0:
            return 0.0
        return self.success_count / self.call_count


@dataclass
class DatabaseMetrics:
    """Metrics for database operations."""
    query_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    consecutive_failures: int = 0
    last_error_time: Optional[float] = None

    @property
    def avg_latency_ms(self) -> float:
        """Calculate average query latency."""
        if self.query_count == 0:
            return 0.0
        return self.total_latency_ms / self.query_count

    @property
    def error_rate(self) -> float:
        """Calculate error rate."""
        if self.query_count == 0:
            return 0.0
        return self.error_count / self.query_count


class MetricsCollector:
    """Collects and aggregates metrics."""

    def __init__(self, config: MonitoringConfig):
        self.config = config
        self.start_time = time.time()
        self.tool_metrics: Dict[str, ToolMetrics] = defaultdict(ToolMetrics)
        self.db_metrics = DatabaseMetrics()
        self.active_connections = 0
        self.total_requests = 0
        self.recent_errors: List[Dict[str, Any]] = []
        self.recent_requests: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []

    def record_tool_call(self, tool_name: str, latency_ms: float, success: bool, error: Optional[str] = None):
        """Record a tool call."""
        metrics = self.tool_metrics[tool_name]
        metrics.call_count += 1

        if success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1

        metrics.total_latency_ms += latency_ms
        metrics.min_latency_ms = min(metrics.min_latency_ms, latency_ms)
        metrics.max_latency_ms = max(metrics.max_latency_ms, latency_ms)

        # Record in recent requests
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

        # Record error
        if not success and error:
            self.recent_errors.append({
                "timestamp": datetime.utcnow().isoformat(),
                "tool": tool_name,
                "error": error,
                "latency_ms": latency_ms,
            })

            # Keep only last 50 errors
            if len(self.recent_errors) > 50:
                self.recent_errors = self.recent_errors[-50:]

        # Check alerting rules
        self._check_tool_alerts(tool_name, metrics, latency_ms)

    def record_db_query(self, latency_ms: float, success: bool, error: Optional[str] = None):
        """Record a database query."""
        self.db_metrics.query_count += 1
        self.db_metrics.total_latency_ms += latency_ms

        if success:
            self.db_metrics.consecutive_failures = 0
        else:
            self.db_metrics.error_count += 1
            self.db_metrics.consecutive_failures += 1
            self.db_metrics.last_error_time = time.time()

            # Check database alerting rules
            self._check_db_alerts(error)

    def increment_connections(self):
        """Increment active connections."""
        self.active_connections += 1

    def decrement_connections(self):
        """Decrement active connections."""
        self.active_connections = max(0, self.active_connections - 1)

    def increment_requests(self):
        """Increment total requests."""
        self.total_requests += 1

    def get_uptime_seconds(self) -> float:
        """Get server uptime in seconds."""
        return time.time() - self.start_time

    def get_overall_error_rate(self) -> float:
        """Calculate overall error rate across all tools."""
        total_calls = sum(m.call_count for m in self.tool_metrics.values())
        total_errors = sum(m.error_count for m in self.tool_metrics.values())

        if total_calls == 0:
            return 0.0
        return total_errors / total_calls

    def get_overall_avg_latency_ms(self) -> float:
        """Calculate overall average latency across all tools."""
        total_calls = sum(m.call_count for m in self.tool_metrics.values())
        total_latency = sum(m.total_latency_ms for m in self.tool_metrics.values())

        if total_calls == 0:
            return 0.0
        return total_latency / total_calls

    def get_top_tools(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top N tools by call count."""
        tools = [
            {
                "name": name,
                "call_count": metrics.call_count,
                "avg_latency_ms": metrics.avg_latency_ms,
                "error_rate": metrics.error_rate,
            }
            for name, metrics in self.tool_metrics.items()
        ]
        return sorted(tools, key=lambda x: x["call_count"], reverse=True)[:limit]

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return self._alerts[-50:]  # Last 50 alerts

    def _check_tool_alerts(self, tool_name: str, metrics: ToolMetrics, latency_ms: float):
        """Check and trigger tool-related alerts."""
        if not self.config.alerting.enable_alerts:
            return

        # Error rate alert
        if metrics.call_count >= 10 and metrics.error_rate > self.config.alerting.error_rate_threshold:
            self._add_alert(
                "error_rate_high",
                f"Tool {tool_name} error rate {metrics.error_rate:.2%} exceeds threshold "
                f"{self.config.alerting.error_rate_threshold:.2%}",
                severity="warning",
                tool=tool_name,
                error_rate=metrics.error_rate,
            )

        # Latency alert
        if latency_ms > self.config.alerting.latency_threshold_ms:
            self._add_alert(
                "latency_high",
                f"Tool {tool_name} latency {latency_ms:.0f}ms exceeds threshold "
                f"{self.config.alerting.latency_threshold_ms:.0f}ms",
                severity="warning",
                tool=tool_name,
                latency_ms=latency_ms,
            )

    def _check_db_alerts(self, error: Optional[str]):
        """Check and trigger database-related alerts."""
        if not self.config.alerting.enable_alerts:
            return

        # Consecutive failures alert
        if self.db_metrics.consecutive_failures >= self.config.alerting.db_failure_threshold:
            self._add_alert(
                "database_failure",
                f"Database has {self.db_metrics.consecutive_failures} consecutive failures",
                severity="critical",
                consecutive_failures=self.db_metrics.consecutive_failures,
                error=error,
            )

    def _add_alert(self, alert_type: str, message: str, severity: str, **extra):
        """Add an alert to the queue."""
        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": alert_type,
            "severity": severity,
            "message": message,
            **extra,
        }
        self._alerts.append(alert)

        # Keep only last 100 alerts
        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]

    def export_prometheus(self) -> str:
        """Export metrics in Prometheus format."""
        lines = []

        # Service uptime
        lines.append("# HELP allobye_uptime_seconds Server uptime in seconds")
        lines.append("# TYPE allobye_uptime_seconds gauge")
        lines.append(f"allobye_uptime_seconds {self.get_uptime_seconds():.2f}")

        # Total requests
        lines.append("# HELP allobye_requests_total Total number of requests")
        lines.append("# TYPE allobye_requests_total counter")
        lines.append(f"allobye_requests_total {self.total_requests}")

        # Active connections
        lines.append("# HELP allobye_active_connections Current number of active connections")
        lines.append("# TYPE allobye_active_connections gauge")
        lines.append(f"allobye_active_connections {self.active_connections}")

        # Tool metrics
        for tool_name, metrics in self.tool_metrics.items():
            safe_name = tool_name.replace("-", "_")

            # Call count
            lines.append(f"# HELP allobye_tool_calls_total Total calls for tool {tool_name}")
            lines.append(f"# TYPE allobye_tool_calls_total counter")
            lines.append(f'allobye_tool_calls_total{{tool="{tool_name}"}} {metrics.call_count}')

            # Success count
            lines.append(f"# HELP allobye_tool_success_total Successful calls for tool {tool_name}")
            lines.append(f"# TYPE allobye_tool_success_total counter")
            lines.append(f'allobye_tool_success_total{{tool="{tool_name}"}} {metrics.success_count}')

            # Error count
            lines.append(f"# HELP allobye_tool_errors_total Failed calls for tool {tool_name}")
            lines.append(f"# TYPE allobye_tool_errors_total counter")
            lines.append(f'allobye_tool_errors_total{{tool="{tool_name}"}} {metrics.error_count}')

            # Average latency
            lines.append(f"# HELP allobye_tool_latency_ms Average latency for tool {tool_name}")
            lines.append(f"# TYPE allobye_tool_latency_ms gauge")
            lines.append(f'allobye_tool_latency_ms{{tool="{tool_name}"}} {metrics.avg_latency_ms:.2f}')

        # Database metrics
        lines.append("# HELP allobye_db_queries_total Total database queries")
        lines.append("# TYPE allobye_db_queries_total counter")
        lines.append(f"allobye_db_queries_total {self.db_metrics.query_count}")

        lines.append("# HELP allobye_db_errors_total Total database errors")
        lines.append("# TYPE allobye_db_errors_total counter")
        lines.append(f"allobye_db_errors_total {self.db_metrics.error_count}")

        lines.append("# HELP allobye_db_latency_ms Average database query latency")
        lines.append("# TYPE allobye_db_latency_ms gauge")
        lines.append(f"allobye_db_latency_ms {self.db_metrics.avg_latency_ms:.2f}")

        return "\n".join(lines) + "\n"

    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get data for monitoring dashboard."""
        return {
            "uptime_seconds": self.get_uptime_seconds(),
            "total_requests": self.total_requests,
            "active_connections": self.active_connections,
            "overall_error_rate": self.get_overall_error_rate(),
            "overall_avg_latency_ms": self.get_overall_avg_latency_ms(),
            "top_tools": self.get_top_tools(limit=10),
            "recent_errors": self.recent_errors[-20:],
            "recent_requests": self.recent_requests[-50:],
            "alerts": self.get_alerts(),
            "database": {
                "query_count": self.db_metrics.query_count,
                "error_count": self.db_metrics.error_count,
                "avg_latency_ms": self.db_metrics.avg_latency_ms,
                "error_rate": self.db_metrics.error_rate,
                "consecutive_failures": self.db_metrics.consecutive_failures,
            },
            "tool_details": {
                name: {
                    "call_count": metrics.call_count,
                    "success_count": metrics.success_count,
                    "error_count": metrics.error_count,
                    "avg_latency_ms": metrics.avg_latency_ms,
                    "min_latency_ms": metrics.min_latency_ms if metrics.min_latency_ms != float('inf') else 0,
                    "max_latency_ms": metrics.max_latency_ms,
                    "error_rate": metrics.error_rate,
                    "success_rate": metrics.success_rate,
                }
                for name, metrics in self.tool_metrics.items()
            },
        }


# ═══════════════════════════════════════════════════════════════
# REQUEST TRACING
# ═══════════════════════════════════════════════════════════════

class RequestTracer:
    """Traces requests with correlation IDs."""

    def __init__(self, logger: StructuredLogger):
        self.logger = logger
        self._active_traces: Dict[str, Dict[str, Any]] = {}

    def start_trace(self, tool_name: str) -> str:
        """Start a new trace."""
        trace_id = str(uuid4())
        self._active_traces[trace_id] = {
            "trace_id": trace_id,
            "tool_name": tool_name,
            "start_time": time.time(),
            "spans": [],
        }

        self.logger.set_context(trace_id=trace_id, tool=tool_name)
        self.logger.debug("Request trace started", tool=tool_name)

        return trace_id

    def add_span(self, trace_id: str, span_name: str, **metadata):
        """Add a span to the trace."""
        if trace_id not in self._active_traces:
            return

        span = {
            "name": span_name,
            "timestamp": time.time(),
            "metadata": metadata,
        }
        self._active_traces[trace_id]["spans"].append(span)

    def end_trace(self, trace_id: str, success: bool, error: Optional[str] = None):
        """End a trace."""
        if trace_id not in self._active_traces:
            return

        trace = self._active_traces[trace_id]
        duration_ms = (time.time() - trace["start_time"]) * 1000

        self.logger.debug(
            "Request trace completed",
            tool=trace["tool_name"],
            duration_ms=duration_ms,
            success=success,
            error=error,
            span_count=len(trace["spans"]),
        )

        # Clean up
        del self._active_traces[trace_id]
        self.logger.clear_context()

        return duration_ms

    @contextmanager
    def trace_span(self, trace_id: str, span_name: str, **metadata):
        """Context manager for tracing a span."""
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.add_span(trace_id, span_name, duration_ms=duration_ms, **metadata)


# ═══════════════════════════════════════════════════════════════
# MONITORING MIDDLEWARE
# ═══════════════════════════════════════════════════════════════

class MonitoringMiddleware:
    """Middleware for request/response monitoring."""

    def __init__(self, logger: StructuredLogger, metrics: MetricsCollector, tracer: RequestTracer):
        self.logger = logger
        self.metrics = metrics
        self.tracer = tracer

    def monitor_tool_call(self, func: Callable) -> Callable:
        """Decorator to monitor tool calls."""

        @wraps(func)
        async def wrapper(tool_name: str, arguments: Dict[str, Any], *args, **kwargs):
            # Start trace
            trace_id = self.tracer.start_trace(tool_name)
            self.metrics.increment_requests()
            self.metrics.increment_connections()

            start_time = time.time()
            error = None
            success = False

            try:
                self.logger.info(
                    f"Tool call started: {tool_name}",
                    tool=tool_name,
                    arguments=arguments,
                )

                # Execute tool
                result = await func(tool_name, arguments, *args, **kwargs)
                success = True

                return result

            except Exception as e:
                error = str(e)
                self.logger.error(
                    f"Tool call failed: {tool_name}",
                    tool=tool_name,
                    error=error,
                    error_type=type(e).__name__,
                )
                raise

            finally:
                # Record metrics
                latency_ms = (time.time() - start_time) * 1000
                self.metrics.record_tool_call(tool_name, latency_ms, success, error)
                self.metrics.decrement_connections()

                # End trace
                self.tracer.end_trace(trace_id, success, error)

                self.logger.info(
                    f"Tool call completed: {tool_name}",
                    tool=tool_name,
                    latency_ms=latency_ms,
                    success=success,
                )

        return wrapper

    @contextmanager
    def monitor_db_query(self, query_type: str):
        """Context manager for monitoring database queries."""
        start_time = time.time()
        error = None
        success = False

        try:
            self.logger.debug(f"Database query started: {query_type}")
            yield
            success = True

        except Exception as e:
            error = str(e)
            self.logger.error(
                f"Database query failed: {query_type}",
                query_type=query_type,
                error=error,
            )
            raise

        finally:
            latency_ms = (time.time() - start_time) * 1000
            self.metrics.record_db_query(latency_ms, success, error)

            self.logger.debug(
                f"Database query completed: {query_type}",
                latency_ms=latency_ms,
                success=success,
            )


# ═══════════════════════════════════════════════════════════════
# GLOBAL MONITORING INSTANCE
# ═══════════════════════════════════════════════════════════════

# Global monitoring instances
_logger: Optional[StructuredLogger] = None
_metrics: Optional[MetricsCollector] = None
_tracer: Optional[RequestTracer] = None
_middleware: Optional[MonitoringMiddleware] = None


def initialize_monitoring(config: Optional[MonitoringConfig] = None) -> MonitoringMiddleware:
    """Initialize global monitoring system."""
    global _logger, _metrics, _tracer, _middleware, _config

    if config:
        _config = config

    _logger = StructuredLogger("allobye", _config)
    _metrics = MetricsCollector(_config)
    _tracer = RequestTracer(_logger)
    _middleware = MonitoringMiddleware(_logger, _metrics, _tracer)

    _logger.info("Monitoring system initialized", config=asdict(_config))

    return _middleware


def get_logger() -> StructuredLogger:
    """Get global logger instance."""
    global _logger
    if _logger is None:
        initialize_monitoring()
    return _logger


def get_metrics() -> MetricsCollector:
    """Get global metrics collector instance."""
    global _metrics
    if _metrics is None:
        initialize_monitoring()
    return _metrics


def get_tracer() -> RequestTracer:
    """Get global tracer instance."""
    global _tracer
    if _tracer is None:
        initialize_monitoring()
    return _tracer


def get_middleware() -> MonitoringMiddleware:
    """Get global middleware instance."""
    global _middleware
    if _middleware is None:
        initialize_monitoring()
    return _middleware


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK
# ═══════════════════════════════════════════════════════════════

def get_health_status() -> Dict[str, Any]:
    """Get service health status."""
    metrics = get_metrics()
    config = _config

    # Determine overall health
    health = "healthy"
    issues = []

    # Check error rate
    error_rate = metrics.get_overall_error_rate()
    if error_rate > config.alerting.error_rate_threshold:
        health = "degraded"
        issues.append(f"High error rate: {error_rate:.2%}")

    # Check database
    if metrics.db_metrics.consecutive_failures >= config.alerting.db_failure_threshold:
        health = "unhealthy"
        issues.append(f"Database failures: {metrics.db_metrics.consecutive_failures}")

    return {
        "status": health,
        "timestamp": datetime.utcnow().isoformat(),
        "uptime_seconds": metrics.get_uptime_seconds(),
        "service": config.service_name,
        "environment": config.environment,
        "checks": {
            "api": "healthy" if error_rate < config.alerting.error_rate_threshold else "degraded",
            "database": "healthy" if metrics.db_metrics.consecutive_failures == 0 else "unhealthy",
        },
        "issues": issues,
        "metrics": {
            "total_requests": metrics.total_requests,
            "active_connections": metrics.active_connections,
            "error_rate": error_rate,
            "avg_latency_ms": metrics.get_overall_avg_latency_ms(),
        },
    }
