"""Comprehensive health check system for AllôBye MCP Server.

This module provides:
- Database connectivity checks
- Supabase API health checks
- Cache health checks
- Overall system health aggregation
- Dependency health monitoring
"""

from __future__ import annotations

import asyncio
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

# ═══════════════════════════════════════════════════════════════
# HEALTH STATUS ENUM
# ═══════════════════════════════════════════════════════════════


class HealthStatus(str, Enum):
    """Health status levels."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


# ═══════════════════════════════════════════════════════════════
# HEALTH CHECK RESULT
# ═══════════════════════════════════════════════════════════════


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    component: str
    status: HealthStatus
    message: str
    latency_ms: float
    timestamp: str
    details: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════
# INDIVIDUAL HEALTH CHECKS
# ═══════════════════════════════════════════════════════════════


async def check_database_connectivity() -> HealthCheckResult:
    """Check database connectivity and basic query performance.

    Returns:
        HealthCheckResult with database health status
    """
    start_time = time.time()
    component = "database"

    try:
        # Import here to avoid circular dependencies
        from main import get_supabase

        supabase = get_supabase()

        if not supabase:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message="Supabase client not initialized",
                latency_ms=0,
                timestamp=datetime.utcnow().isoformat() + "Z",
                error="Client initialization failed",
            )

        # Perform a simple query to test connectivity
        # Using a lightweight query that should always work
        response = supabase.table("schools").select("id").limit(1).execute()

        latency_ms = (time.time() - start_time) * 1000

        if latency_ms > 1000:
            # Slow but working
            return HealthCheckResult(
                component=component,
                status=HealthStatus.DEGRADED,
                message=f"Database responding slowly ({latency_ms:.0f}ms)",
                latency_ms=latency_ms,
                timestamp=datetime.utcnow().isoformat() + "Z",
                details={"latency_threshold_ms": 1000},
            )

        return HealthCheckResult(
            component=component,
            status=HealthStatus.HEALTHY,
            message="Database connectivity OK",
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            details={"latency_ms": latency_ms},
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return HealthCheckResult(
            component=component,
            status=HealthStatus.UNHEALTHY,
            message="Database connectivity failed",
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            error=str(e),
            details={"error_type": type(e).__name__},
        )


async def check_supabase_api_health() -> HealthCheckResult:
    """Check Supabase API health and authentication.

    Returns:
        HealthCheckResult with Supabase API health status
    """
    start_time = time.time()
    component = "supabase_api"

    try:
        import httpx

        supabase_url = os.getenv("SUPABASE_URL")
        if not supabase_url:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message="SUPABASE_URL not configured",
                latency_ms=0,
                timestamp=datetime.utcnow().isoformat() + "Z",
                error="Missing configuration",
            )

        # Check Supabase health endpoint
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{supabase_url}/rest/v1/",
                headers={"apikey": os.getenv("SUPABASE_ANON_KEY", "")},
                timeout=5.0,
            )

            latency_ms = (time.time() - start_time) * 1000

            if response.status_code == 200:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.HEALTHY,
                    message="Supabase API responding",
                    latency_ms=latency_ms,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    details={
                        "status_code": response.status_code,
                        "latency_ms": latency_ms,
                    },
                )
            else:
                return HealthCheckResult(
                    component=component,
                    status=HealthStatus.DEGRADED,
                    message=f"Supabase API returned {response.status_code}",
                    latency_ms=latency_ms,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    details={"status_code": response.status_code},
                )

    except asyncio.TimeoutError:
        latency_ms = (time.time() - start_time) * 1000
        return HealthCheckResult(
            component=component,
            status=HealthStatus.UNHEALTHY,
            message="Supabase API timeout",
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            error="Request timeout after 5s",
        )
    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return HealthCheckResult(
            component=component,
            status=HealthStatus.UNHEALTHY,
            message="Supabase API check failed",
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            error=str(e),
            details={"error_type": type(e).__name__},
        )


async def check_cache_health() -> HealthCheckResult:
    """Check cache health (if caching is implemented).

    Returns:
        HealthCheckResult with cache health status
    """
    start_time = time.time()
    component = "cache"

    try:
        # For now, we don't have a cache implementation
        # This is a placeholder for future cache health checks

        # If we had Redis/Memcached, we would:
        # 1. Try to connect
        # 2. Perform a SET/GET operation
        # 3. Check memory usage
        # 4. Check connection pool

        # Mock cache check for now
        latency_ms = (time.time() - start_time) * 1000

        return HealthCheckResult(
            component=component,
            status=HealthStatus.HEALTHY,
            message="Cache not implemented (in-memory only)",
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            details={
                "cache_type": "in-memory",
                "implementation": "none",
            },
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return HealthCheckResult(
            component=component,
            status=HealthStatus.UNKNOWN,
            message="Cache health check failed",
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            error=str(e),
        )


async def check_monitoring_system() -> HealthCheckResult:
    """Check monitoring system health.

    Returns:
        HealthCheckResult with monitoring system health
    """
    start_time = time.time()
    component = "monitoring"

    try:
        from monitoring import get_metrics

        metrics = get_metrics()

        latency_ms = (time.time() - start_time) * 1000

        # Check if metrics are being collected
        if metrics.total_requests == 0 and metrics.get_uptime_seconds() > 60:
            # No requests after 1 minute is suspicious
            return HealthCheckResult(
                component=component,
                status=HealthStatus.DEGRADED,
                message="No requests recorded",
                latency_ms=latency_ms,
                timestamp=datetime.utcnow().isoformat() + "Z",
                details={
                    "total_requests": metrics.total_requests,
                    "uptime_seconds": metrics.get_uptime_seconds(),
                },
            )

        # Check error rate
        error_rate = metrics.get_overall_error_rate()
        if error_rate > 0.20:  # 20% error rate
            return HealthCheckResult(
                component=component,
                status=HealthStatus.DEGRADED,
                message=f"High error rate: {error_rate:.1%}",
                latency_ms=latency_ms,
                timestamp=datetime.utcnow().isoformat() + "Z",
                details={
                    "error_rate": error_rate,
                    "total_requests": metrics.total_requests,
                },
            )

        return HealthCheckResult(
            component=component,
            status=HealthStatus.HEALTHY,
            message="Monitoring system operational",
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            details={
                "total_requests": metrics.total_requests,
                "error_rate": error_rate,
                "uptime_seconds": metrics.get_uptime_seconds(),
            },
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return HealthCheckResult(
            component=component,
            status=HealthStatus.UNHEALTHY,
            message="Monitoring system check failed",
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            error=str(e),
        )


async def check_authentication_system() -> HealthCheckResult:
    """Check authentication system health.

    Returns:
        HealthCheckResult with auth system health
    """
    start_time = time.time()
    component = "authentication"

    try:
        # Check if Supabase auth is configured
        supabase_url = os.getenv("SUPABASE_URL")
        service_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not supabase_url or not service_key:
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message="Authentication not properly configured",
                latency_ms=0,
                timestamp=datetime.utcnow().isoformat() + "Z",
                error="Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY",
            )

        # Check if service key is valid format (should be JWT)
        if not service_key.startswith("eyJ"):
            return HealthCheckResult(
                component=component,
                status=HealthStatus.UNHEALTHY,
                message="Invalid service key format",
                latency_ms=0,
                timestamp=datetime.utcnow().isoformat() + "Z",
                error="Service key should be JWT token",
            )

        latency_ms = (time.time() - start_time) * 1000

        return HealthCheckResult(
            component=component,
            status=HealthStatus.HEALTHY,
            message="Authentication system configured",
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            details={"auth_provider": "supabase"},
        )

    except Exception as e:
        latency_ms = (time.time() - start_time) * 1000
        return HealthCheckResult(
            component=component,
            status=HealthStatus.UNHEALTHY,
            message="Authentication system check failed",
            latency_ms=latency_ms,
            timestamp=datetime.utcnow().isoformat() + "Z",
            error=str(e),
        )


# ═══════════════════════════════════════════════════════════════
# OVERALL HEALTH CHECK
# ═══════════════════════════════════════════════════════════════


async def perform_health_checks() -> Dict[str, Any]:
    """Perform all health checks and aggregate results.

    Returns:
        Dictionary with overall health status and component details
    """
    start_time = time.time()

    # Run all health checks concurrently
    check_results = await asyncio.gather(
        check_database_connectivity(),
        check_supabase_api_health(),
        check_cache_health(),
        check_monitoring_system(),
        check_authentication_system(),
        return_exceptions=True,
    )

    # Process results
    components = {}
    issues = []
    overall_status = HealthStatus.HEALTHY

    for result in check_results:
        if isinstance(result, Exception):
            # Health check itself failed
            overall_status = HealthStatus.UNHEALTHY
            issues.append(f"Health check failed: {str(result)}")
            continue

        if isinstance(result, HealthCheckResult):
            components[result.component] = {
                "status": result.status.value,
                "message": result.message,
                "latency_ms": result.latency_ms,
                "timestamp": result.timestamp,
                "details": result.details,
            }

            if result.error:
                components[result.component]["error"] = result.error

            # Aggregate status
            if result.status == HealthStatus.UNHEALTHY:
                overall_status = HealthStatus.UNHEALTHY
                issues.append(f"{result.component}: {result.message}")
            elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                overall_status = HealthStatus.DEGRADED
                issues.append(f"{result.component}: {result.message}")

    # Calculate total check duration
    total_latency_ms = (time.time() - start_time) * 1000

    # Get metrics for additional context
    try:
        from monitoring import get_metrics

        metrics = get_metrics()
        metrics_summary = {
            "uptime_seconds": metrics.get_uptime_seconds(),
            "total_requests": metrics.total_requests,
            "active_connections": metrics.active_connections,
            "error_rate": metrics.get_overall_error_rate(),
            "avg_latency_ms": metrics.get_overall_avg_latency_ms(),
        }
    except Exception:
        metrics_summary = {}

    return {
        "status": overall_status.value,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total_check_duration_ms": total_latency_ms,
        "service": "allobye-mcp-server",
        "version": "1.0.0",
        "components": components,
        "issues": issues if issues else None,
        "metrics": metrics_summary,
    }


async def get_health_status_enhanced() -> Dict[str, Any]:
    """Enhanced health status with comprehensive checks.

    This function is the main entry point for health checks.

    Returns:
        Complete health status dictionary
    """
    return await perform_health_checks()
