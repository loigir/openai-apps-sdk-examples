"""Enhanced monitoring module with business metrics, cache tracking, and advanced Prometheus export.

This is an enhanced version of monitoring.py with:
- Business metrics (pickups, emergencies, delegates)
- Cache metrics tracking
- Histogram-based latency tracking
- Multi-dimensional labeled metrics
- Enhanced Prometheus export with quantiles
- Integration with health checks

To integrate: Replace monitoring.py with this file or merge the enhancements.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

# Import the base classes from monitoring.py
from monitoring import (
    MonitoringConfig,
    StructuredLogger,
    RequestTracer,
    MonitoringMiddleware,
    JsonFormatter,
    AlertingConfig,
    Metric,
    ToolMetrics as BaseToolMetrics,
    DatabaseMetrics as BaseDatabaseMetrics,
    _config,
    _logger,
    _metrics,
    _tracer,
    _middleware,
)


# ═══════════════════════════════════════════════════════════════
# ENHANCED METRICS DATACLASSES
# ═══════════════════════════════════════════════════════════════


@dataclass
class EnhancedToolMetrics(BaseToolMetrics):
    """Enhanced tool metrics with histogram support."""
    latency_histogram: List[float] = field(default_factory=list)

    def get_percentile(self, percentile: float) -> float:
        """Calculate latency percentile."""
        if not self.latency_histogram:
            return 0.0
        sorted_latencies = sorted(self.latency_histogram)
        index = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]


@dataclass
class EnhancedDatabaseMetrics(BaseDatabaseMetrics):
    """Enhanced database metrics with histogram and slow query tracking."""
    query_histogram: List[float] = field(default_factory=list)
    slow_query_count: int = 0

    def get_percentile(self, percentile: float) -> float:
        """Calculate query latency percentile."""
        if not self.query_histogram:
            return 0.0
        sorted_latencies = sorted(self.query_histogram)
        index = int(len(sorted_latencies) * percentile / 100)
        return sorted_latencies[min(index, len(sorted_latencies) - 1)]


@dataclass
class BusinessMetrics:
    """Business-level metrics for AllôBye operations."""
    # Pickup metrics
    pickups_created: int = 0
    pickups_completed: int = 0
    pickups_cancelled: int = 0
    cross_school_pickups: int = 0

    # Delegate metrics
    delegates_authorized: int = 0
    delegate_authorizations_revoked: int = 0

    # Emergency metrics
    emergencies_declared: int = 0
    emergency_notifications_sent: int = 0

    # User metrics
    active_sessions: int = 0
    parent_logins: int = 0
    staff_logins: int = 0

    # School metrics
    schools_active: int = 0
    children_registered: int = 0

    def get_pickup_completion_rate(self) -> float:
        """Calculate pickup completion rate."""
        total = self.pickups_created
        if total == 0:
            return 0.0
        return self.pickups_completed / total


@dataclass
class CacheMetrics:
    """Metrics for caching operations."""
    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size_bytes: int = 0
    item_count: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total


# ═══════════════════════════════════════════════════════════════
# ENHANCED METRICS COLLECTOR
# ═══════════════════════════════════════════════════════════════


class EnhancedMetricsCollector:
    """Enhanced metrics collector with business and cache metrics."""

    def __init__(self, config: MonitoringConfig):
        """Initialize enhanced metrics collector."""
        from collections import defaultdict
        import time

        self.config = config
        self.start_time = time.time()

        # Use enhanced metrics
        self.tool_metrics: Dict[str, EnhancedToolMetrics] = defaultdict(EnhancedToolMetrics)
        self.db_metrics = EnhancedDatabaseMetrics()
        self.business_metrics = BusinessMetrics()
        self.cache_metrics = CacheMetrics()

        self.active_connections = 0
        self.total_requests = 0
        self.recent_errors: List[Dict[str, Any]] = []
        self.recent_requests: List[Dict[str, Any]] = []
        self._alerts: List[Dict[str, Any]] = []

        # Label-based metrics for multi-dimensional analysis
        self._label_metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: defaultdict(int))

    def record_tool_call(
        self,
        tool_name: str,
        latency_ms: float,
        success: bool,
        error: str | None = None,
        labels: Dict[str, str] | None = None,
    ) -> None:
        """Record a tool call with labels for multi-dimensional analysis."""
        from datetime import datetime

        metrics = self.tool_metrics[tool_name]
        metrics.call_count += 1

        if success:
            metrics.success_count += 1
        else:
            metrics.error_count += 1

        metrics.total_latency_ms += latency_ms
        metrics.min_latency_ms = min(metrics.min_latency_ms, latency_ms)
        metrics.max_latency_ms = max(metrics.max_latency_ms, latency_ms)

        # Add to histogram (keep last 1000)
        metrics.latency_histogram.append(latency_ms)
        if len(metrics.latency_histogram) > 1000:
            metrics.latency_histogram = metrics.latency_histogram[-1000:]

        # Record labeled metrics
        if labels:
            for label_key, label_value in labels.items():
                metric_key = f"{tool_name}.{label_key}.{label_value}"
                self._label_metrics[metric_key]["count"] += 1
                if success:
                    self._label_metrics[metric_key]["success"] += 1
                else:
                    self._label_metrics[metric_key]["error"] += 1

        # Record in recent requests
        self.recent_requests.append({
            "timestamp": datetime.utcnow().isoformat(),
            "tool": tool_name,
            "latency_ms": latency_ms,
            "success": success,
            "error": error,
            "labels": labels or {},
        })

        # Keep only last 100
        if len(self.recent_requests) > 100:
            self.recent_requests = self.recent_requests[-100:]

        # Record error
        if not success and error:
            self.recent_errors.append({
                "timestamp": datetime.utcnow().isoformat(),
                "tool": tool_name,
                "error": error,
                "latency_ms": latency_ms,
                "labels": labels or {},
            })

            if len(self.recent_errors) > 50:
                self.recent_errors = self.recent_errors[-50:]

        # Check alerting rules
        self._check_tool_alerts(tool_name, metrics, latency_ms)

    def record_db_query(self, latency_ms: float, success: bool, error: str | None = None) -> None:
        """Record a database query with histogram tracking."""
        import time

        self.db_metrics.query_count += 1
        self.db_metrics.total_latency_ms += latency_ms

        # Add to histogram
        self.db_metrics.query_histogram.append(latency_ms)
        if len(self.db_metrics.query_histogram) > 1000:
            self.db_metrics.query_histogram = self.db_metrics.query_histogram[-1000:]

        # Track slow queries
        if latency_ms > 1000:  # > 1 second
            self.db_metrics.slow_query_count += 1

        if success:
            self.db_metrics.consecutive_failures = 0
        else:
            self.db_metrics.error_count += 1
            self.db_metrics.consecutive_failures += 1
            self.db_metrics.last_error_time = time.time()
            self._check_db_alerts(error)

    def record_business_event(
        self,
        event_type: str,
        labels: Dict[str, str] | None = None,
    ) -> None:
        """Record business-level events."""
        # Update business metrics
        if event_type == "pickup_created":
            self.business_metrics.pickups_created += 1
        elif event_type == "pickup_completed":
            self.business_metrics.pickups_completed += 1
        elif event_type == "pickup_cancelled":
            self.business_metrics.pickups_cancelled += 1
        elif event_type == "cross_school_pickup":
            self.business_metrics.cross_school_pickups += 1
        elif event_type == "delegate_authorized":
            self.business_metrics.delegates_authorized += 1
        elif event_type == "delegate_revoked":
            self.business_metrics.delegate_authorizations_revoked += 1
        elif event_type == "emergency_declared":
            self.business_metrics.emergencies_declared += 1
        elif event_type == "emergency_notification":
            self.business_metrics.emergency_notifications_sent += 1
        elif event_type == "parent_login":
            self.business_metrics.parent_logins += 1
        elif event_type == "staff_login":
            self.business_metrics.staff_logins += 1

        # Record with labels
        if labels:
            metric_key = f"business.{event_type}"
            for label_key, label_value in labels.items():
                self._label_metrics[f"{metric_key}.{label_key}.{label_value}"]["count"] += 1

    def record_cache_operation(self, operation: str, size_bytes: int = 0) -> None:
        """Record cache operations."""
        if operation == "hit":
            self.cache_metrics.hits += 1
        elif operation == "miss":
            self.cache_metrics.misses += 1
        elif operation == "eviction":
            self.cache_metrics.evictions += 1
            self.cache_metrics.size_bytes -= size_bytes
            self.cache_metrics.item_count -= 1
        elif operation == "set":
            self.cache_metrics.size_bytes += size_bytes
            self.cache_metrics.item_count += 1

    def increment_connections(self) -> None:
        """Increment active connections."""
        self.active_connections += 1

    def decrement_connections(self) -> None:
        """Decrement active connections."""
        self.active_connections = max(0, self.active_connections - 1)

    def increment_requests(self) -> None:
        """Increment total requests."""
        self.total_requests += 1

    def get_uptime_seconds(self) -> float:
        """Get server uptime."""
        import time
        return time.time() - self.start_time

    def get_overall_error_rate(self) -> float:
        """Calculate overall error rate."""
        total_calls = sum(m.call_count for m in self.tool_metrics.values())
        total_errors = sum(m.error_count for m in self.tool_metrics.values())

        if total_calls == 0:
            return 0.0
        return total_errors / total_calls

    def get_overall_avg_latency_ms(self) -> float:
        """Calculate overall average latency."""
        total_calls = sum(m.call_count for m in self.tool_metrics.values())
        total_latency = sum(m.total_latency_ms for m in self.tool_metrics.values())

        if total_calls == 0:
            return 0.0
        return total_latency / total_calls

    def get_top_tools(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get top N tools by call count."""
        from typing import cast

        tools = [
            {
                "name": name,
                "call_count": metrics.call_count,
                "avg_latency_ms": metrics.avg_latency_ms,
                "error_rate": metrics.error_rate,
            }
            for name, metrics in self.tool_metrics.items()
        ]
        return sorted(tools, key=lambda x: cast(int, x["call_count"]), reverse=True)[:limit]

    def get_alerts(self) -> List[Dict[str, Any]]:
        """Get recent alerts."""
        return self._alerts[-50:]

    def _check_tool_alerts(self, tool_name: str, metrics: EnhancedToolMetrics, latency_ms: float) -> None:
        """Check and trigger tool-related alerts."""
        from datetime import datetime

        if not self.config.alerting.enable_alerts:
            return

        # Error rate alert
        if metrics.call_count >= 10 and metrics.error_rate > self.config.alerting.error_rate_threshold:
            self._add_alert(
                "error_rate_high",
                f"Tool {tool_name} error rate {metrics.error_rate:.2%} exceeds threshold",
                severity="warning",
                tool=tool_name,
                error_rate=metrics.error_rate,
            )

        # Latency alert
        if latency_ms > self.config.alerting.latency_threshold_ms:
            self._add_alert(
                "latency_high",
                f"Tool {tool_name} latency {latency_ms:.0f}ms exceeds threshold",
                severity="warning",
                tool=tool_name,
                latency_ms=latency_ms,
            )

    def _check_db_alerts(self, error: str | None) -> None:
        """Check and trigger database-related alerts."""
        from datetime import datetime

        if not self.config.alerting.enable_alerts:
            return

        if self.db_metrics.consecutive_failures >= self.config.alerting.db_failure_threshold:
            self._add_alert(
                "database_failure",
                f"Database has {self.db_metrics.consecutive_failures} consecutive failures",
                severity="critical",
                consecutive_failures=self.db_metrics.consecutive_failures,
                error=error,
            )

    def _add_alert(self, alert_type: str, message: str, severity: str, **extra: Any) -> None:
        """Add an alert."""
        from datetime import datetime

        alert = {
            "timestamp": datetime.utcnow().isoformat(),
            "type": alert_type,
            "severity": severity,
            "message": message,
            **extra,
        }
        self._alerts.append(alert)

        if len(self._alerts) > 100:
            self._alerts = self._alerts[-100:]

    def export_prometheus(self) -> str:
        """Export enhanced Prometheus metrics with histograms and labels."""
        lines = []

        # Service metrics
        lines.append("# HELP allobye_uptime_seconds Server uptime in seconds")
        lines.append("# TYPE allobye_uptime_seconds gauge")
        lines.append(f"allobye_uptime_seconds {self.get_uptime_seconds():.2f}")

        lines.append("# HELP allobye_requests_total Total number of requests")
        lines.append("# TYPE allobye_requests_total counter")
        lines.append(f"allobye_requests_total {self.total_requests}")

        lines.append("# HELP allobye_active_connections Current number of active connections")
        lines.append("# TYPE allobye_active_connections gauge")
        lines.append(f"allobye_active_connections {self.active_connections}")

        lines.append("# HELP allobye_active_sessions Current number of active user sessions")
        lines.append("# TYPE allobye_active_sessions gauge")
        lines.append(f"allobye_active_sessions {self.business_metrics.active_sessions}")

        # Tool metrics with quantiles
        for tool_name, metrics in self.tool_metrics.items():
            lines.append(f"# HELP allobye_tool_calls_total Total calls for tool {tool_name}")
            lines.append(f"# TYPE allobye_tool_calls_total counter")
            lines.append(f'allobye_tool_calls_total{{tool="{tool_name}"}} {metrics.call_count}')

            lines.append(f"# HELP allobye_tool_success_total Successful calls for tool {tool_name}")
            lines.append(f"# TYPE allobye_tool_success_total counter")
            lines.append(f'allobye_tool_success_total{{tool="{tool_name}"}} {metrics.success_count}')

            lines.append(f"# HELP allobye_tool_errors_total Failed calls for tool {tool_name}")
            lines.append(f"# TYPE allobye_tool_errors_total counter")
            lines.append(f'allobye_tool_errors_total{{tool="{tool_name}"}} {metrics.error_count}')

            # Latency histogram
            lines.append(f"# HELP allobye_tool_latency_ms Latency metrics for tool {tool_name}")
            lines.append(f"# TYPE allobye_tool_latency_ms gauge")
            min_lat = metrics.min_latency_ms if metrics.min_latency_ms != float('inf') else 0
            lines.append(f'allobye_tool_latency_ms{{tool="{tool_name}",quantile="avg"}} {metrics.avg_latency_ms:.2f}')
            lines.append(f'allobye_tool_latency_ms{{tool="{tool_name}",quantile="min"}} {min_lat:.2f}')
            lines.append(f'allobye_tool_latency_ms{{tool="{tool_name}",quantile="max"}} {metrics.max_latency_ms:.2f}')
            lines.append(f'allobye_tool_latency_ms{{tool="{tool_name}",quantile="0.50"}} {metrics.get_percentile(50):.2f}')
            lines.append(f'allobye_tool_latency_ms{{tool="{tool_name}",quantile="0.95"}} {metrics.get_percentile(95):.2f}')
            lines.append(f'allobye_tool_latency_ms{{tool="{tool_name}",quantile="0.99"}} {metrics.get_percentile(99):.2f}')

        # Database metrics
        lines.append("# HELP allobye_db_queries_total Total database queries")
        lines.append("# TYPE allobye_db_queries_total counter")
        lines.append(f"allobye_db_queries_total {self.db_metrics.query_count}")

        lines.append("# HELP allobye_db_errors_total Total database errors")
        lines.append("# TYPE allobye_db_errors_total counter")
        lines.append(f"allobye_db_errors_total {self.db_metrics.error_count}")

        lines.append("# HELP allobye_db_slow_queries_total Total slow database queries")
        lines.append("# TYPE allobye_db_slow_queries_total counter")
        lines.append(f"allobye_db_slow_queries_total {self.db_metrics.slow_query_count}")

        lines.append("# HELP allobye_db_latency_ms Database query latency")
        lines.append("# TYPE allobye_db_latency_ms gauge")
        lines.append(f'allobye_db_latency_ms{{quantile="avg"}} {self.db_metrics.avg_latency_ms:.2f}')

        # Business metrics
        lines.append("# HELP allobye_pickups_created_total Total pickups created")
        lines.append("# TYPE allobye_pickups_created_total counter")
        lines.append(f"allobye_pickups_created_total {self.business_metrics.pickups_created}")

        lines.append("# HELP allobye_pickups_completed_total Total pickups completed")
        lines.append("# TYPE allobye_pickups_completed_total counter")
        lines.append(f"allobye_pickups_completed_total {self.business_metrics.pickups_completed}")

        lines.append("# HELP allobye_pickups_cancelled_total Total pickups cancelled")
        lines.append("# TYPE allobye_pickups_cancelled_total counter")
        lines.append(f"allobye_pickups_cancelled_total {self.business_metrics.pickups_cancelled}")

        lines.append("# HELP allobye_cross_school_pickups_total Total cross-school pickups")
        lines.append("# TYPE allobye_cross_school_pickups_total counter")
        lines.append(f"allobye_cross_school_pickups_total {self.business_metrics.cross_school_pickups}")

        lines.append("# HELP allobye_delegates_authorized_total Total delegates authorized")
        lines.append("# TYPE allobye_delegates_authorized_total counter")
        lines.append(f"allobye_delegates_authorized_total {self.business_metrics.delegates_authorized}")

        lines.append("# HELP allobye_emergencies_declared_total Total emergencies declared")
        lines.append("# TYPE allobye_emergencies_declared_total counter")
        lines.append(f"allobye_emergencies_declared_total {self.business_metrics.emergencies_declared}")

        lines.append("# HELP allobye_emergency_notifications_total Total emergency notifications")
        lines.append("# TYPE allobye_emergency_notifications_total counter")
        lines.append(f"allobye_emergency_notifications_total {self.business_metrics.emergency_notifications_sent}")

        lines.append("# HELP allobye_parent_logins_total Total parent logins")
        lines.append("# TYPE allobye_parent_logins_total counter")
        lines.append(f"allobye_parent_logins_total {self.business_metrics.parent_logins}")

        lines.append("# HELP allobye_staff_logins_total Total staff logins")
        lines.append("# TYPE allobye_staff_logins_total counter")
        lines.append(f"allobye_staff_logins_total {self.business_metrics.staff_logins}")

        # Cache metrics
        lines.append("# HELP allobye_cache_hits_total Total cache hits")
        lines.append("# TYPE allobye_cache_hits_total counter")
        lines.append(f"allobye_cache_hits_total {self.cache_metrics.hits}")

        lines.append("# HELP allobye_cache_misses_total Total cache misses")
        lines.append("# TYPE allobye_cache_misses_total counter")
        lines.append(f"allobye_cache_misses_total {self.cache_metrics.misses}")

        lines.append("# HELP allobye_cache_hit_rate Cache hit rate")
        lines.append("# TYPE allobye_cache_hit_rate gauge")
        lines.append(f"allobye_cache_hit_rate {self.cache_metrics.hit_rate:.4f}")

        lines.append("# HELP allobye_cache_size_bytes Current cache size")
        lines.append("# TYPE allobye_cache_size_bytes gauge")
        lines.append(f"allobye_cache_size_bytes {self.cache_metrics.size_bytes}")

        lines.append("# HELP allobye_cache_items Current number of cached items")
        lines.append("# TYPE allobye_cache_items gauge")
        lines.append(f"allobye_cache_items {self.cache_metrics.item_count}")

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
                "slow_query_count": self.db_metrics.slow_query_count,
            },
            "business_metrics": {
                "pickups_created": self.business_metrics.pickups_created,
                "pickups_completed": self.business_metrics.pickups_completed,
                "pickups_cancelled": self.business_metrics.pickups_cancelled,
                "cross_school_pickups": self.business_metrics.cross_school_pickups,
                "delegates_authorized": self.business_metrics.delegates_authorized,
                "emergencies_declared": self.business_metrics.emergencies_declared,
                "parent_logins": self.business_metrics.parent_logins,
                "staff_logins": self.business_metrics.staff_logins,
            },
            "cache_metrics": {
                "hits": self.cache_metrics.hits,
                "misses": self.cache_metrics.misses,
                "hit_rate": self.cache_metrics.hit_rate,
                "size_bytes": self.cache_metrics.size_bytes,
                "item_count": self.cache_metrics.item_count,
            },
            "tool_details": {
                name: {
                    "call_count": metrics.call_count,
                    "success_count": metrics.success_count,
                    "error_count": metrics.error_count,
                    "avg_latency_ms": metrics.avg_latency_ms,
                    "min_latency_ms": metrics.min_latency_ms if metrics.min_latency_ms != float('inf') else 0,
                    "max_latency_ms": metrics.max_latency_ms,
                    "p50_latency_ms": metrics.get_percentile(50),
                    "p95_latency_ms": metrics.get_percentile(95),
                    "p99_latency_ms": metrics.get_percentile(99),
                    "error_rate": metrics.error_rate,
                    "success_rate": metrics.success_rate,
                }
                for name, metrics in self.tool_metrics.items()
            },
        }
