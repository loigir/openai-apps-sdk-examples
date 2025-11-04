"""SQL Injection Protection Test Suite for AllôBye MCP Server.

This test suite validates SQL injection protection across all database operations.

Test Categories:
1. Input validation tests (UUIDs, emails, strings)
2. SQL injection pattern detection tests
3. Query parameter validation tests
4. Integration tests with Supabase client
5. Security logging tests
"""

import pytest
from datetime import datetime
from typing import Any, Dict, List

# Import security module
from security import (
    validate_uuid,
    validate_email,
    validate_string_length,
    validate_list_of_uuids,
    validate_sql_safe_string,
    detect_sql_injection,
    sanitize_text_input,
    QueryValidator,
    QueryLogger,
    SafeSupabaseQuery,
    SecurityViolation,
    SecurityViolationType,
    validate_iso_datetime,
    validate_enum_value,
)


# ═══════════════════════════════════════════════════════════════
# TEST 1: SQL INJECTION PATTERN DETECTION
# ═══════════════════════════════════════════════════════════════

class TestSQLInjectionDetection:
    """Test SQL injection pattern detection."""

    def test_basic_or_injection(self):
        """Test detection of OR 1=1 injection."""
        malicious_inputs = [
            "admin' OR '1'='1",
            "' OR 1=1--",
            "' OR 'a'='a",
            "admin' OR 1=1#",
            "' OR TRUE--",
        ]

        for input_val in malicious_inputs:
            assert detect_sql_injection(input_val), f"Failed to detect: {input_val}"

    def test_union_select_injection(self):
        """Test detection of UNION SELECT injection."""
        malicious_inputs = [
            "' UNION SELECT * FROM users--",
            "' UNION ALL SELECT password FROM admin--",
            "1' UNION SELECT null,null,null--",
        ]

        for input_val in malicious_inputs:
            assert detect_sql_injection(input_val), f"Failed to detect: {input_val}"

    def test_statement_chaining(self):
        """Test detection of statement chaining attacks."""
        malicious_inputs = [
            "'; DROP TABLE users--",
            "'; DELETE FROM children WHERE 1=1--",
            "'; INSERT INTO admins VALUES ('hacker','pass')--",
            "1'; UPDATE users SET role='admin'--",
        ]

        for input_val in malicious_inputs:
            assert detect_sql_injection(input_val), f"Failed to detect: {input_val}"

    def test_comment_injection(self):
        """Test detection of SQL comments."""
        malicious_inputs = [
            "admin'--",
            "' OR 1=1/*comment*/",
            "admin'/* */OR/* */1=1--",
        ]

        for input_val in malicious_inputs:
            assert detect_sql_injection(input_val), f"Failed to detect: {input_val}"

    def test_time_based_blind_injection(self):
        """Test detection of time-based blind SQL injection."""
        malicious_inputs = [
            "'; WAITFOR DELAY '00:00:05'--",
            "' OR SLEEP(5)--",
            "'; SELECT pg_sleep(5)--",
            "1' AND BENCHMARK(5000000,MD5('test'))--",
        ]

        for input_val in malicious_inputs:
            assert detect_sql_injection(input_val), f"Failed to detect: {input_val}"

    def test_stored_procedure_injection(self):
        """Test detection of stored procedure exploitation."""
        malicious_inputs = [
            "'; EXEC xp_cmdshell 'dir'--",
            "'; EXECUTE sp_executesql N'DROP TABLE users'--",
            "1'; xp_regwrite--",
        ]

        for input_val in malicious_inputs:
            assert detect_sql_injection(input_val), f"Failed to detect: {input_val}"

    def test_safe_inputs(self):
        """Test that safe inputs are not flagged."""
        safe_inputs = [
            "john.doe@example.com",
            "My child's name is Sophie",
            "Picking up at 3:30pm",
            "École Primaire",
            "Grand-maman will pick up",
            "123 Main Street",
        ]

        for input_val in safe_inputs:
            assert not detect_sql_injection(input_val), f"False positive: {input_val}"


# ═══════════════════════════════════════════════════════════════
# TEST 2: UUID VALIDATION
# ═══════════════════════════════════════════════════════════════

class TestUUIDValidation:
    """Test UUID input validation."""

    def test_valid_uuids(self):
        """Test that valid UUIDs pass validation."""
        valid_uuids = [
            "550e8400-e29b-41d4-a716-446655440000",
            "123e4567-e89b-12d3-a456-426614174000",
            "00000000-0000-0000-0000-000000000000",
        ]

        for uuid in valid_uuids:
            result = validate_uuid(uuid)
            assert result == uuid.lower()

    def test_invalid_uuid_format(self):
        """Test that invalid UUID formats are rejected."""
        invalid_uuids = [
            "not-a-uuid",
            "550e8400-e29b-41d4-a716",  # Too short
            "550e8400-e29b-41d4-a716-44665544000Z",  # Invalid character
            "550e8400e29b41d4a716446655440000",  # Missing hyphens
            "",  # Empty
            "' OR 1=1--",  # SQL injection attempt
        ]

        for uuid in invalid_uuids:
            with pytest.raises(SecurityViolation) as exc:
                validate_uuid(uuid)
            assert exc.value.violation_type == SecurityViolationType.INVALID_UUID

    def test_uuid_list_validation(self):
        """Test validation of UUID lists."""
        # Valid list
        valid_list = [
            "550e8400-e29b-41d4-a716-446655440000",
            "123e4567-e89b-12d3-a456-426614174000",
        ]
        result = validate_list_of_uuids(valid_list)
        assert len(result) == 2

        # Invalid list with SQL injection
        invalid_list = [
            "550e8400-e29b-41d4-a716-446655440000",
            "' OR 1=1--",
        ]
        with pytest.raises(SecurityViolation):
            validate_list_of_uuids(invalid_list)

    def test_uuid_sql_injection_attempts(self):
        """Test that SQL injection attempts in UUID fields are blocked."""
        injection_attempts = [
            "550e8400' OR '1'='1",
            "'; DROP TABLE children--",
            "550e8400-e29b-41d4-a716-446655440000'; DELETE FROM users--",
        ]

        for attempt in injection_attempts:
            with pytest.raises(SecurityViolation):
                validate_uuid(attempt)


# ═══════════════════════════════════════════════════════════════
# TEST 3: EMAIL VALIDATION
# ═══════════════════════════════════════════════════════════════

class TestEmailValidation:
    """Test email input validation."""

    def test_valid_emails(self):
        """Test that valid emails pass validation."""
        valid_emails = [
            "user@example.com",
            "john.doe@example.co.uk",
            "test+tag@domain.com",
            "admin@school-name.edu",
        ]

        for email in valid_emails:
            result = validate_email(email)
            assert result == email.lower()

    def test_invalid_email_format(self):
        """Test that invalid email formats are rejected."""
        invalid_emails = [
            "not-an-email",
            "@example.com",
            "user@",
            "user @example.com",
            "",
        ]

        for email in invalid_emails:
            with pytest.raises(SecurityViolation) as exc:
                validate_email(email)
            assert exc.value.violation_type == SecurityViolationType.INVALID_EMAIL

    def test_email_sql_injection_attempts(self):
        """Test that SQL injection attempts in email fields are blocked."""
        injection_attempts = [
            "admin@example.com' OR '1'='1",
            "'; DROP TABLE users--@example.com",
            "user@example.com'; DELETE FROM children--",
        ]

        for attempt in injection_attempts:
            with pytest.raises(SecurityViolation):
                validate_email(attempt)


# ═══════════════════════════════════════════════════════════════
# TEST 4: STRING VALIDATION
# ═══════════════════════════════════════════════════════════════

class TestStringValidation:
    """Test string input validation."""

    def test_valid_strings(self):
        """Test that valid strings pass validation."""
        valid_strings = [
            ("Normal text", 1, 100),
            ("My child Sophie", 1, 100),
            ("Picking up at 3pm", 1, 100),
        ]

        for text, min_len, max_len in valid_strings:
            result = validate_string_length(text, min_len, max_len)
            assert result == text

    def test_string_length_validation(self):
        """Test string length requirements."""
        # Too short
        with pytest.raises(SecurityViolation):
            validate_string_length("ab", min_length=5)

        # Too long
        with pytest.raises(SecurityViolation):
            validate_string_length("a" * 1001, max_length=1000)

    def test_string_sql_injection_attempts(self):
        """Test that SQL injection in strings is detected."""
        injection_attempts = [
            "'; DROP TABLE children--",
            "test' OR '1'='1",
            "name' UNION SELECT * FROM users--",
        ]

        for attempt in injection_attempts:
            with pytest.raises(SecurityViolation) as exc:
                validate_string_length(attempt, 1, 100)
            assert exc.value.violation_type == SecurityViolationType.SQL_INJECTION_ATTEMPT

    def test_text_sanitization(self):
        """Test text sanitization removes dangerous characters."""
        # Null bytes
        assert sanitize_text_input("test\x00data") == "testdata"

        # Control characters (except newline, tab)
        assert sanitize_text_input("test\x01\x02data") == "testdata"

        # Preserves safe whitespace
        assert sanitize_text_input("test\ndata\tmore") == "test\ndata\tmore"

        # Truncates long input
        long_text = "a" * 2000
        result = sanitize_text_input(long_text, max_length=100)
        assert len(result) == 100


# ═══════════════════════════════════════════════════════════════
# TEST 5: QUERY PARAMETER VALIDATION
# ═══════════════════════════════════════════════════════════════

class TestQueryValidator:
    """Test query parameter validation."""

    def test_valid_filter_params(self):
        """Test validation of filter parameters."""
        params = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "school_id": "123e4567-e89b-12d3-a456-426614174000",
            "email": "user@example.com",
            "status": "active",
        }

        validated = QueryValidator.validate_filter_params(params)
        assert "user_id" in validated
        assert "email" in validated

    def test_invalid_param_names(self):
        """Test rejection of invalid parameter names."""
        invalid_params = [
            {"'; DROP TABLE--": "value"},
            {"param name": "value"},  # Space not allowed
            {"param-name": "value"},  # Hyphen not allowed
            {"1param": "value"},  # Must start with letter or underscore
        ]

        for params in invalid_params:
            with pytest.raises(SecurityViolation):
                QueryValidator.validate_filter_params(params)

    def test_sql_injection_in_params(self):
        """Test detection of SQL injection in parameter values."""
        injection_params = {
            "user_id": "'; DROP TABLE users--",
            "name": "admin' OR '1'='1",
        }

        with pytest.raises(SecurityViolation):
            QueryValidator.validate_filter_params(injection_params)

    def test_insert_data_validation(self):
        """Test validation of INSERT data."""
        # Valid data
        valid_data = {
            "name": "John Doe",
            "email": "john@example.com",
            "age": 35,
            "active": True,
        }

        validated = QueryValidator.validate_insert_data(valid_data)
        assert "name" in validated
        assert "email" in validated

        # Invalid field names
        invalid_data = {
            "'; DROP--": "value",
        }

        with pytest.raises(SecurityViolation):
            QueryValidator.validate_insert_data(invalid_data)

    def test_insert_data_field_whitelist(self):
        """Test field whitelisting in INSERT operations."""
        # Valid data with only allowed fields
        valid_data = {
            "name": "John",
            "email": "john@example.com",
        }

        allowed_fields = ["name", "email"]

        validated = QueryValidator.validate_insert_data(valid_data, allowed_fields)
        assert "name" in validated
        assert "email" in validated

        # Invalid data with non-allowed field
        invalid_data = {
            "name": "John",
            "email": "john@example.com",
            "malicious_field": "'; DROP TABLE users--",
        }

        # Should raise error for non-allowed field
        with pytest.raises(SecurityViolation):
            QueryValidator.validate_insert_data(invalid_data, allowed_fields)


# ═══════════════════════════════════════════════════════════════
# TEST 6: DATETIME AND ENUM VALIDATION
# ═══════════════════════════════════════════════════════════════

class TestAdditionalValidation:
    """Test additional validation functions."""

    def test_iso_datetime_validation(self):
        """Test ISO 8601 datetime validation."""
        valid_datetimes = [
            "2025-11-04T15:00:00-05:00",
            "2025-11-04T20:00:00Z",
            "2025-11-04T15:00:00",
        ]

        for dt in valid_datetimes:
            result = validate_iso_datetime(dt)
            assert result == dt

        # Invalid formats
        invalid_datetimes = [
            "not a date",
            "'; DROP TABLE--",
            "invalid-datetime-format",
        ]

        for dt in invalid_datetimes:
            with pytest.raises(SecurityViolation):
                validate_iso_datetime(dt)

    def test_enum_value_validation(self):
        """Test enum value validation."""
        allowed_roles = ["parent", "school_staff", "admin"]

        # Valid values
        assert validate_enum_value("parent", allowed_roles) == "parent"
        assert validate_enum_value("school_staff", allowed_roles) == "school_staff"

        # Invalid values
        with pytest.raises(SecurityViolation):
            validate_enum_value("hacker", allowed_roles)

        with pytest.raises(SecurityViolation):
            validate_enum_value("parent' OR '1'='1", allowed_roles)


# ═══════════════════════════════════════════════════════════════
# TEST 7: INTEGRATION TESTS
# ═══════════════════════════════════════════════════════════════

class TestSecurityIntegration:
    """Integration tests for complete workflow protection."""

    def test_user_signup_validation(self):
        """Test complete user signup input validation."""
        # Simulate signup data
        signup_data = {
            "email": "newuser@example.com",
            "password": "SecureP@ss123",
            "name": "New User",
            "role": "parent",
        }

        # Validate each field
        email = validate_email(signup_data["email"])
        password = validate_string_length(signup_data["password"], 6, 128)
        name = sanitize_text_input(validate_string_length(signup_data["name"], 1, 255))
        role = validate_enum_value(signup_data["role"], ["parent", "school_staff"])

        assert email == "newuser@example.com"
        assert password == "SecureP@ss123"
        assert name == "New User"
        assert role == "parent"

    def test_user_signup_sql_injection_prevention(self):
        """Test that SQL injection in signup is prevented."""
        malicious_signup = {
            "email": "hacker@example.com'; DROP TABLE users--",
            "password": "pass123",
            "name": "'; DELETE FROM children--",
            "role": "admin' OR '1'='1",
        }

        # Each field should raise SecurityViolation
        with pytest.raises(SecurityViolation):
            validate_email(malicious_signup["email"])

        with pytest.raises(SecurityViolation):
            validate_string_length(malicious_signup["name"], 1, 255)

        with pytest.raises(SecurityViolation):
            validate_enum_value(malicious_signup["role"], ["parent", "school_staff"])

    def test_pickup_schedule_validation(self):
        """Test pickup schedule input validation."""
        schedule_data = {
            "child_ids": [
                "550e8400-e29b-41d4-a716-446655440000",
                "123e4567-e89b-12d3-a456-426614174000",
            ],
            "pickup_person_id": "223e4567-e89b-12d3-a456-426614174000",
            "scheduled_time": "2025-11-04T15:00:00-05:00",
            "notes": "Pick up after school",
        }

        # Validate all fields
        child_ids = validate_list_of_uuids(schedule_data["child_ids"])
        pickup_person_id = validate_uuid(schedule_data["pickup_person_id"])
        scheduled_time = validate_iso_datetime(schedule_data["scheduled_time"])
        notes = sanitize_text_input(schedule_data["notes"])

        assert len(child_ids) == 2
        assert pickup_person_id
        assert scheduled_time
        assert notes == "Pick up after school"

    def test_pickup_schedule_sql_injection_prevention(self):
        """Test that SQL injection in pickup schedule is prevented."""
        malicious_schedule = {
            "child_ids": [
                "550e8400-e29b-41d4-a716-446655440000",
                "'; DROP TABLE pickups--",
            ],
            "pickup_person_id": "' OR '1'='1--",
            "scheduled_time": "'; DELETE FROM children--",
            "notes": "'; UNION SELECT * FROM users--",
        }

        # Each field should raise SecurityViolation
        with pytest.raises(SecurityViolation):
            validate_list_of_uuids(malicious_schedule["child_ids"])

        with pytest.raises(SecurityViolation):
            validate_uuid(malicious_schedule["pickup_person_id"])

        with pytest.raises(SecurityViolation):
            validate_iso_datetime(malicious_schedule["scheduled_time"])

        # Notes field should raise due to SQL injection pattern in validate_string_length
        with pytest.raises(SecurityViolation):
            validate_string_length(malicious_schedule["notes"], 0, 1000)


# ═══════════════════════════════════════════════════════════════
# TEST 8: QUERY LOGGING
# ═══════════════════════════════════════════════════════════════

class TestQueryLogging:
    """Test security audit logging."""

    def test_query_logging(self, caplog):
        """Test that queries are logged for security audit."""
        logger = QueryLogger()

        # Log a successful query
        logger.log_query(
            operation="SELECT",
            table="users",
            params={"user_id": "550e8400-e29b-41d4-a716-446655440000"},
            user_id="550e8400-e29b-41d4-a716-446655440000",
            success=True,
        )

        # Log a failed query
        logger.log_query(
            operation="INSERT",
            table="users",
            params={"email": "test@example.com"},
            user_id=None,
            success=False,
            error="Duplicate key violation",
        )

    def test_sensitive_data_masking(self):
        """Test that sensitive data is masked in logs."""
        logger = QueryLogger()

        # Sensitive data should be masked
        sensitive_data = {
            "email": "user@example.com",
            "password": "SecretPassword123",
            "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        }

        masked = logger._mask_sensitive_data(sensitive_data)
        assert masked["email"] == "user@example.com"  # Not sensitive
        assert masked["password"] == "***MASKED***"
        assert masked["access_token"] == "***MASKED***"


# ═══════════════════════════════════════════════════════════════
# TEST RUNNER
# ═══════════════════════════════════════════════════════════════

if __name__ == "__main__":
    """Run all SQL injection tests."""
    import sys

    print("═" * 70)
    print("AllôBye MCP Server - SQL Injection Protection Test Suite")
    print("═" * 70)
    print()

    # Run tests
    exit_code = pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--color=yes",
        "-W", "ignore::DeprecationWarning",
    ])

    print()
    print("═" * 70)
    if exit_code == 0:
        print("✓ All SQL injection tests PASSED")
    else:
        print("✗ Some SQL injection tests FAILED")
    print("═" * 70)

    sys.exit(exit_code)
