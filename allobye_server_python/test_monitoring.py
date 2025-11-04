#!/usr/bin/env python3
"""Test script for AllôBye monitoring system.

This script demonstrates and tests the monitoring features:
- Metrics collection
- Structured logging
- Request tracing
- Database monitoring
- Alerting rules
- Prometheus export
"""

import asyncio
import time
from monitoring import (
    initialize_monitoring,
    get_logger,
    get_metrics,
    get_middleware,
    get_health_status,
    MonitoringConfig,
    AlertingConfig,
)


async def test_basic_logging():
    """Test structured logging functionality."""
    print("\n=== Testing Structured Logging ===")

    logger = get_logger()

    logger.debug("Debug message", test_id=1)
    logger.info("Info message", test_id=2)
    logger.warning("Warning message", test_id=3, extra_field="test_value")
    logger.error("Error message", test_id=4, error_code="TEST_ERR")

    print("✓ Logged messages at all levels")


async def test_metrics_collection():
    """Test metrics collection and recording."""
    print("\n=== Testing Metrics Collection ===")

    metrics = get_metrics()

    # Simulate tool calls
    metrics.record_tool_call("test-tool-1", 123.5, True)
    metrics.record_tool_call("test-tool-1", 234.5, True)
    metrics.record_tool_call("test-tool-1", 456.7, False, "Test error")
    metrics.record_tool_call("test-tool-2", 89.3, True)

    # Simulate database queries
    metrics.record_db_query(45.2, True)
    metrics.record_db_query(67.8, True)
    metrics.record_db_query(123.4, False, "Connection timeout")

    # Increment requests
    metrics.increment_requests()
    metrics.increment_requests()
    metrics.increment_requests()

    # Check metrics
    dashboard = metrics.get_dashboard_data()

    print(f"✓ Total Requests: {dashboard['total_requests']}")
    print(f"✓ Overall Error Rate: {dashboard['overall_error_rate']:.2%}")
    print(f"✓ Overall Avg Latency: {dashboard['overall_avg_latency_ms']:.1f}ms")
    print(f"✓ DB Queries: {dashboard['database']['query_count']}")
    print(f"✓ DB Avg Latency: {dashboard['database']['avg_latency_ms']:.1f}ms")

    assert dashboard['total_requests'] == 3
    assert len(dashboard['tool_details']) == 2
    assert dashboard['database']['query_count'] == 3


async def test_alerting():
    """Test alerting rules and thresholds."""
    print("\n=== Testing Alerting Rules ===")

    # Reconfigure with lower thresholds for testing
    config = MonitoringConfig(
        alerting=AlertingConfig(
            error_rate_threshold=0.1,  # 10% for testing
            latency_threshold_ms=100.0,  # 100ms for testing
            db_failure_threshold=2,
            enable_alerts=True,
        )
    )

    initialize_monitoring(config)
    metrics = get_metrics()

    # Trigger high latency alert
    for i in range(5):
        metrics.record_tool_call("slow-tool", 1500.0, True)

    # Trigger error rate alert
    for i in range(15):
        success = i < 5  # 33% error rate
        metrics.record_tool_call("error-prone-tool", 50.0, success, None if success else "Test error")

    # Trigger database failure alert
    metrics.record_db_query(100.0, False, "Connection error")
    metrics.record_db_query(100.0, False, "Connection error")
    metrics.record_db_query(100.0, False, "Connection error")

    alerts = metrics.get_alerts()

    print(f"✓ Generated {len(alerts)} alerts")
    for alert in alerts[-5:]:
        print(f"  [{alert['severity'].upper()}] {alert['type']}: {alert['message']}")

    assert len(alerts) > 0


async def test_request_tracing():
    """Test request tracing with correlation IDs."""
    print("\n=== Testing Request Tracing ===")

    middleware = get_middleware()
    logger = get_logger()

    # Start a trace
    trace_id = middleware.tracer.start_trace("test-tool")
    print(f"✓ Started trace: {trace_id}")

    # Add some spans
    with middleware.tracer.trace_span(trace_id, "database_query", table="users"):
        await asyncio.sleep(0.1)

    with middleware.tracer.trace_span(trace_id, "api_call", endpoint="/api/test"):
        await asyncio.sleep(0.05)

    # End trace
    duration = middleware.tracer.end_trace(trace_id, True)
    print(f"✓ Trace completed in {duration:.1f}ms")


async def test_database_monitoring():
    """Test database query monitoring."""
    print("\n=== Testing Database Monitoring ===")

    middleware = get_middleware()

    # Monitor a database operation
    try:
        with middleware.monitor_db_query("test_query"):
            # Simulate database operation
            await asyncio.sleep(0.05)
        print("✓ Monitored successful database query")
    except Exception as e:
        print(f"✗ Database query failed: {e}")

    # Monitor a failing database operation
    try:
        with middleware.monitor_db_query("failing_query"):
            raise Exception("Simulated database error")
    except Exception:
        print("✓ Monitored failing database query")

    metrics = get_metrics()
    db_metrics = metrics.get_dashboard_data()['database']
    print(f"✓ Total DB queries: {db_metrics['query_count']}")


async def test_prometheus_export():
    """Test Prometheus metrics export."""
    print("\n=== Testing Prometheus Export ===")

    metrics = get_metrics()

    # Generate some metrics
    for i in range(10):
        metrics.record_tool_call("prometheus-test", 100 + i * 10, i % 3 != 0)

    # Export to Prometheus format
    prometheus_text = metrics.export_prometheus()

    print("✓ Exported Prometheus metrics:")
    lines = prometheus_text.strip().split('\n')
    for line in lines[:10]:
        if not line.startswith('#'):
            print(f"  {line}")

    assert 'allobye_uptime_seconds' in prometheus_text
    assert 'allobye_requests_total' in prometheus_text
    assert 'allobye_tool_calls_total' in prometheus_text


async def test_health_check():
    """Test health check functionality."""
    print("\n=== Testing Health Check ===")

    health = get_health_status()

    print(f"✓ Status: {health['status']}")
    print(f"✓ Uptime: {health['uptime_seconds']:.1f}s")
    print(f"✓ Service: {health['service']}")
    print(f"✓ Environment: {health['environment']}")
    print(f"✓ API Check: {health['checks']['api']}")
    print(f"✓ Database Check: {health['checks']['database']}")

    if health['issues']:
        print(f"⚠ Issues detected:")
        for issue in health['issues']:
            print(f"  - {issue}")
    else:
        print("✓ No issues detected")


async def test_dashboard_data():
    """Test dashboard data retrieval."""
    print("\n=== Testing Dashboard Data ===")

    metrics = get_metrics()
    dashboard = metrics.get_dashboard_data()

    print(f"✓ Uptime: {dashboard['uptime_seconds']:.1f}s")
    print(f"✓ Total Requests: {dashboard['total_requests']}")
    print(f"✓ Active Connections: {dashboard['active_connections']}")
    print(f"✓ Error Rate: {dashboard['overall_error_rate']:.2%}")
    print(f"✓ Avg Latency: {dashboard['overall_avg_latency_ms']:.1f}ms")

    print(f"\n✓ Top Tools:")
    for tool in dashboard['top_tools'][:5]:
        print(f"  - {tool['name']}: {tool['call_count']} calls, {tool['avg_latency_ms']:.0f}ms avg")

    print(f"\n✓ Recent Errors: {len(dashboard['recent_errors'])}")
    for error in dashboard['recent_errors'][:3]:
        print(f"  - [{error['tool']}] {error['error']}")

    print(f"\n✓ Active Alerts: {len(dashboard['alerts'])}")


async def run_all_tests():
    """Run all monitoring tests."""
    print("╔" + "═" * 60 + "╗")
    print("║" + " " * 15 + "AllôBye Monitoring System Tests" + " " * 14 + "║")
    print("╚" + "═" * 60 + "╝")

    start_time = time.time()

    try:
        await test_basic_logging()
        await test_metrics_collection()
        await test_alerting()
        await test_request_tracing()
        await test_database_monitoring()
        await test_prometheus_export()
        await test_health_check()
        await test_dashboard_data()

        elapsed = time.time() - start_time

        print("\n" + "=" * 62)
        print(f"✓ All tests passed in {elapsed:.2f}s")
        print("=" * 62)

        # Print summary
        print("\n📊 Monitoring System Summary:")
        health = get_health_status()
        print(f"  Status: {health['status']}")
        print(f"  Total Requests: {health['metrics']['total_requests']}")
        print(f"  Error Rate: {health['metrics']['error_rate']:.2%}")
        print(f"  Avg Latency: {health['metrics']['avg_latency_ms']:.1f}ms")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # Initialize monitoring
    config = MonitoringConfig(
        service_name="allobye-test",
        environment="test",
        log_level="INFO",
    )
    initialize_monitoring(config)

    # Run tests
    success = asyncio.run(run_all_tests())

    exit(0 if success else 1)
