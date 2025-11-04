"""Security module for AllôBye MCP server.

Provides SQL injection protection, input validation, and query sanitization.

Key Features:
- Input validation and sanitization
- SQL injection pattern detection
- Query parameter validation
- Security audit logging
- Rate limiting helpers
"""

from __future__ import annotations

import re
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID
from enum import Enum

# Security logger
security_logger = logging.getLogger("allobye.security")


class SecurityViolationType(Enum):
    """Types of security violations."""
    SQL_INJECTION_ATTEMPT = "sql_injection_attempt"
    INVALID_UUID = "invalid_uuid"
    INVALID_EMAIL = "invalid_email"
    SUSPICIOUS_INPUT = "suspicious_input"
    XSS_ATTEMPT = "xss_attempt"
    PATH_TRAVERSAL = "path_traversal"


class SecurityViolation(Exception):
    """Raised when a security violation is detected."""

    def __init__(self, violation_type: SecurityViolationType, message: str, input_value: Any = None):
        self.violation_type = violation_type
        self.input_value = input_value
        super().__init__(message)


# ═══════════════════════════════════════════════════════════════
# SQL INJECTION PROTECTION
# ═══════════════════════════════════════════════════════════════

# Common SQL injection patterns
SQL_INJECTION_PATTERNS = [
    r"(\bOR\b|\bAND\b)\s+[\d'\"]+\s*=\s*[\d'\"]+",  # OR 1=1, AND '1'='1'
    r"'\s*OR\s+'[^']+'='[^']+",  # OR 'a'='a pattern
    r";\s*(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE|TRUNCATE)\b",  # Statement chaining
    r"UNION\s+(ALL\s+)?SELECT",  # UNION SELECT
    r"--\s*$",  # SQL comments at end
    r"/\*.*\*/",  # Block comments
    r"(EXEC|EXECUTE)\s*\(",  # Execute commands
    r"xp_\w+",  # Extended stored procedures
    r"sp_\w+",  # System stored procedures
    r"0x[0-9a-fA-F]+",  # Hex values (potential injection)
    r"CHAR\s*\(\s*\d+\s*\)",  # CHAR encoding
    r"WAITFOR\s+DELAY",  # Time-based blind SQL injection
    r"BENCHMARK\s*\(",  # MySQL benchmark for timing attacks
    r"SLEEP\s*\(",  # MySQL sleep for timing attacks
    r"pg_sleep\s*\(",  # PostgreSQL sleep for timing attacks
]

SQL_INJECTION_REGEX = [re.compile(pattern, re.IGNORECASE) for pattern in SQL_INJECTION_PATTERNS]


def detect_sql_injection(value: str) -> bool:
    """Detect potential SQL injection attempts in string input.

    Args:
        value: String value to check

    Returns:
        True if potential SQL injection detected, False otherwise
    """
    if not isinstance(value, str):
        return False

    # Check against known patterns
    for pattern in SQL_INJECTION_REGEX:
        if pattern.search(value):
            return True

    return False


def validate_sql_safe_string(value: str, field_name: str = "input") -> str:
    """Validate that a string is safe from SQL injection.

    Args:
        value: String to validate
        field_name: Name of field for error messages

    Returns:
        The original value if safe

    Raises:
        SecurityViolation: If SQL injection pattern detected
    """
    if detect_sql_injection(value):
        security_logger.warning(
            f"SQL injection attempt detected in {field_name}",
            extra={
                "violation_type": SecurityViolationType.SQL_INJECTION_ATTEMPT.value,
                "field": field_name,
                "value_preview": value[:50] if len(value) > 50 else value,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        raise SecurityViolation(
            SecurityViolationType.SQL_INJECTION_ATTEMPT,
            f"Invalid input in {field_name}: Potentially malicious pattern detected",
            value
        )

    return value


# ═══════════════════════════════════════════════════════════════
# INPUT VALIDATION
# ═══════════════════════════════════════════════════════════════

UUID_REGEX = re.compile(r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$', re.IGNORECASE)
EMAIL_REGEX = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')


def validate_uuid(value: str, field_name: str = "id") -> str:
    """Validate UUID format and protect against injection.

    Args:
        value: UUID string to validate
        field_name: Name of field for error messages

    Returns:
        The validated UUID string

    Raises:
        SecurityViolation: If invalid UUID format
    """
    if not isinstance(value, str):
        raise SecurityViolation(
            SecurityViolationType.INVALID_UUID,
            f"Invalid {field_name}: Must be a string",
            value
        )

    # Check UUID format
    if not UUID_REGEX.match(value):
        security_logger.warning(
            f"Invalid UUID format in {field_name}",
            extra={
                "violation_type": SecurityViolationType.INVALID_UUID.value,
                "field": field_name,
                "value": value,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        raise SecurityViolation(
            SecurityViolationType.INVALID_UUID,
            f"Invalid {field_name}: Must be a valid UUID",
            value
        )

    return value.lower()


def validate_email(email: str, field_name: str = "email") -> str:
    """Validate email format and protect against injection.

    Args:
        email: Email address to validate
        field_name: Name of field for error messages

    Returns:
        The validated email (lowercase)

    Raises:
        SecurityViolation: If invalid email format
    """
    if not isinstance(email, str):
        raise SecurityViolation(
            SecurityViolationType.INVALID_EMAIL,
            f"Invalid {field_name}: Must be a string",
            email
        )

    # Basic SQL injection check
    validate_sql_safe_string(email, field_name)

    # Check email format
    if not EMAIL_REGEX.match(email):
        security_logger.warning(
            f"Invalid email format in {field_name}",
            extra={
                "violation_type": SecurityViolationType.INVALID_EMAIL.value,
                "field": field_name,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )
        raise SecurityViolation(
            SecurityViolationType.INVALID_EMAIL,
            f"Invalid {field_name}: Must be a valid email address",
            email
        )

    return email.lower()


def validate_string_length(value: str, min_length: int = 0, max_length: int = 1000, field_name: str = "input") -> str:
    """Validate string length and content safety.

    Args:
        value: String to validate
        min_length: Minimum allowed length
        max_length: Maximum allowed length
        field_name: Name of field for error messages

    Returns:
        The validated string

    Raises:
        SecurityViolation: If length requirements not met or suspicious content
    """
    if not isinstance(value, str):
        raise SecurityViolation(
            SecurityViolationType.SUSPICIOUS_INPUT,
            f"Invalid {field_name}: Must be a string",
            value
        )

    if len(value) < min_length:
        raise SecurityViolation(
            SecurityViolationType.SUSPICIOUS_INPUT,
            f"Invalid {field_name}: Must be at least {min_length} characters",
            value
        )

    if len(value) > max_length:
        raise SecurityViolation(
            SecurityViolationType.SUSPICIOUS_INPUT,
            f"Invalid {field_name}: Must be at most {max_length} characters",
            value
        )

    # Check for SQL injection
    validate_sql_safe_string(value, field_name)

    return value


def validate_list_of_uuids(values: List[str], field_name: str = "ids") -> List[str]:
    """Validate a list of UUIDs.

    Args:
        values: List of UUID strings
        field_name: Name of field for error messages

    Returns:
        List of validated UUIDs

    Raises:
        SecurityViolation: If any UUID is invalid
    """
    if not isinstance(values, list):
        raise SecurityViolation(
            SecurityViolationType.SUSPICIOUS_INPUT,
            f"Invalid {field_name}: Must be a list",
            values
        )

    if not values:
        raise SecurityViolation(
            SecurityViolationType.SUSPICIOUS_INPUT,
            f"Invalid {field_name}: List cannot be empty",
            values
        )

    validated = []
    for i, value in enumerate(values):
        try:
            validated.append(validate_uuid(value, f"{field_name}[{i}]"))
        except SecurityViolation:
            raise

    return validated


def sanitize_text_input(value: str, max_length: int = 1000) -> str:
    """Sanitize text input by removing potentially dangerous characters.

    Args:
        value: Text to sanitize
        max_length: Maximum allowed length

    Returns:
        Sanitized text
    """
    if not isinstance(value, str):
        return str(value)

    # Truncate to max length
    value = value[:max_length]

    # Remove null bytes
    value = value.replace('\x00', '')

    # Remove control characters except newline, tab, carriage return
    value = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', value)

    return value.strip()


# ═══════════════════════════════════════════════════════════════
# QUERY PARAMETER VALIDATION
# ═══════════════════════════════════════════════════════════════

class QueryValidator:
    """Validates and sanitizes database query parameters."""

    @staticmethod
    def validate_filter_params(params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate parameters used in database filters.

        Args:
            params: Dictionary of query parameters

        Returns:
            Validated parameters

        Raises:
            SecurityViolation: If invalid parameters detected
        """
        validated = {}

        for key, value in params.items():
            # Validate key name (prevent injection in column names)
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise SecurityViolation(
                    SecurityViolationType.SUSPICIOUS_INPUT,
                    f"Invalid parameter name: {key}",
                    key
                )

            # Validate value based on type
            if isinstance(value, str):
                if key.endswith('_id') or key == 'id':
                    validated[key] = validate_uuid(value, key)
                elif key.endswith('_email') or key == 'email':
                    validated[key] = validate_email(value, key)
                else:
                    validated[key] = validate_sql_safe_string(value, key)
            elif isinstance(value, (int, float, bool)):
                validated[key] = value
            elif isinstance(value, list):
                if key.endswith('_ids'):
                    validated[key] = validate_list_of_uuids(value, key)
                else:
                    validated[key] = [validate_sql_safe_string(str(v), f"{key}[{i}]") for i, v in enumerate(value)]
            else:
                raise SecurityViolation(
                    SecurityViolationType.SUSPICIOUS_INPUT,
                    f"Unsupported parameter type for {key}",
                    value
                )

        return validated

    @staticmethod
    def validate_insert_data(data: Dict[str, Any], allowed_fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """Validate data for INSERT operations.

        Args:
            data: Data to insert
            allowed_fields: Optional list of allowed field names

        Returns:
            Validated data

        Raises:
            SecurityViolation: If invalid data detected
        """
        validated = {}

        for key, value in data.items():
            # Check if field is allowed
            if allowed_fields is not None and key not in allowed_fields:
                raise SecurityViolation(
                    SecurityViolationType.SUSPICIOUS_INPUT,
                    f"Field not allowed: {key}",
                    key
                )

            # Validate field name
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', key):
                raise SecurityViolation(
                    SecurityViolationType.SUSPICIOUS_INPUT,
                    f"Invalid field name: {key}",
                    key
                )

            # Validate value
            if isinstance(value, str):
                validated[key] = sanitize_text_input(value)
            elif isinstance(value, (int, float, bool, type(None))):
                validated[key] = value
            elif isinstance(value, list):
                validated[key] = [sanitize_text_input(str(v)) if isinstance(v, str) else v for v in value]
            elif isinstance(value, dict):
                validated[key] = value  # Nested objects (e.g., JSONB)
            else:
                validated[key] = str(value)

        return validated


# ═══════════════════════════════════════════════════════════════
# QUERY LOGGING FOR SECURITY AUDIT
# ═══════════════════════════════════════════════════════════════

class QueryLogger:
    """Logs database queries for security auditing."""

    @staticmethod
    def log_query(
        operation: str,
        table: str,
        params: Optional[Dict[str, Any]] = None,
        user_id: Optional[str] = None,
        success: bool = True,
        error: Optional[str] = None
    ):
        """Log a database query for security audit.

        Args:
            operation: Operation type (SELECT, INSERT, UPDATE, DELETE)
            table: Table name
            params: Query parameters (sensitive data should be masked)
            user_id: ID of user performing operation
            success: Whether operation succeeded
            error: Error message if operation failed
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "operation": operation,
            "table": table,
            "user_id": user_id,
            "success": success,
            "params": QueryLogger._mask_sensitive_data(params) if params else None,
        }

        if error:
            log_entry["error"] = error

        if success:
            security_logger.info(f"Query executed: {operation} on {table}", extra=log_entry)
        else:
            security_logger.error(f"Query failed: {operation} on {table}", extra=log_entry)

    @staticmethod
    def _mask_sensitive_data(data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive data in log entries.

        Args:
            data: Data dictionary

        Returns:
            Data with sensitive fields masked
        """
        masked = data.copy()
        sensitive_fields = ['password', 'access_token', 'refresh_token', 'secret', 'api_key']

        for field in sensitive_fields:
            if field in masked:
                masked[field] = "***MASKED***"

        return masked


# ═══════════════════════════════════════════════════════════════
# SAFE QUERY BUILDERS
# ═══════════════════════════════════════════════════════════════

class SafeSupabaseQuery:
    """Wrapper for Supabase queries with automatic validation and logging."""

    def __init__(self, supabase_client, user_id: Optional[str] = None):
        self.client = supabase_client
        self.user_id = user_id
        self.query_logger = QueryLogger()

    def safe_select(self, table: str, columns: str = "*", filters: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a SELECT query with validation.

        Args:
            table: Table name
            columns: Columns to select
            filters: Filter parameters

        Returns:
            Query result
        """
        # Validate table name
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            raise SecurityViolation(
                SecurityViolationType.SUSPICIOUS_INPUT,
                f"Invalid table name: {table}",
                table
            )

        # Validate and sanitize filters
        if filters:
            filters = QueryValidator.validate_filter_params(filters)

        try:
            query = self.client.table(table).select(columns)

            # Apply filters
            if filters:
                for key, value in filters.items():
                    if isinstance(value, list):
                        query = query.in_(key, value)
                    else:
                        query = query.eq(key, value)

            result = query.execute()

            self.query_logger.log_query(
                operation="SELECT",
                table=table,
                params=filters,
                user_id=self.user_id,
                success=True
            )

            return result

        except Exception as e:
            self.query_logger.log_query(
                operation="SELECT",
                table=table,
                params=filters,
                user_id=self.user_id,
                success=False,
                error=str(e)
            )
            raise

    def safe_insert(self, table: str, data: Dict[str, Any], allowed_fields: Optional[List[str]] = None) -> Any:
        """Execute an INSERT query with validation.

        Args:
            table: Table name
            data: Data to insert
            allowed_fields: Optional whitelist of allowed fields

        Returns:
            Query result
        """
        # Validate table name
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            raise SecurityViolation(
                SecurityViolationType.SUSPICIOUS_INPUT,
                f"Invalid table name: {table}",
                table
            )

        # Validate and sanitize data
        validated_data = QueryValidator.validate_insert_data(data, allowed_fields)

        try:
            result = self.client.table(table).insert(validated_data).execute()

            self.query_logger.log_query(
                operation="INSERT",
                table=table,
                params={"fields": list(validated_data.keys())},
                user_id=self.user_id,
                success=True
            )

            return result

        except Exception as e:
            self.query_logger.log_query(
                operation="INSERT",
                table=table,
                params={"fields": list(validated_data.keys())},
                user_id=self.user_id,
                success=False,
                error=str(e)
            )
            raise

    def safe_update(self, table: str, data: Dict[str, Any], filters: Dict[str, Any]) -> Any:
        """Execute an UPDATE query with validation.

        Args:
            table: Table name
            data: Data to update
            filters: Filter parameters

        Returns:
            Query result
        """
        # Validate table name
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table):
            raise SecurityViolation(
                SecurityViolationType.SUSPICIOUS_INPUT,
                f"Invalid table name: {table}",
                table
            )

        # Validate data and filters
        validated_data = QueryValidator.validate_insert_data(data)
        validated_filters = QueryValidator.validate_filter_params(filters)

        try:
            query = self.client.table(table).update(validated_data)

            # Apply filters
            for key, value in validated_filters.items():
                query = query.eq(key, value)

            result = query.execute()

            self.query_logger.log_query(
                operation="UPDATE",
                table=table,
                params={"fields": list(validated_data.keys()), "filters": validated_filters},
                user_id=self.user_id,
                success=True
            )

            return result

        except Exception as e:
            self.query_logger.log_query(
                operation="UPDATE",
                table=table,
                params={"fields": list(validated_data.keys()), "filters": validated_filters},
                user_id=self.user_id,
                success=False,
                error=str(e)
            )
            raise


# ═══════════════════════════════════════════════════════════════
# SECURITY UTILITIES
# ═══════════════════════════════════════════════════════════════

def validate_iso_datetime(value: str, field_name: str = "datetime") -> str:
    """Validate ISO 8601 datetime format.

    Args:
        value: Datetime string to validate
        field_name: Name of field for error messages

    Returns:
        Validated datetime string

    Raises:
        SecurityViolation: If invalid format
    """
    try:
        # Try parsing as ISO format
        from datetime import datetime as dt
        dt.fromisoformat(value.replace('Z', '+00:00'))
        return value
    except (ValueError, AttributeError):
        raise SecurityViolation(
            SecurityViolationType.SUSPICIOUS_INPUT,
            f"Invalid {field_name}: Must be ISO 8601 format",
            value
        )


def validate_enum_value(value: str, allowed_values: List[str], field_name: str = "value") -> str:
    """Validate that a value is in an allowed set.

    Args:
        value: Value to validate
        allowed_values: List of allowed values
        field_name: Name of field for error messages

    Returns:
        Validated value

    Raises:
        SecurityViolation: If value not in allowed set
    """
    if value not in allowed_values:
        raise SecurityViolation(
            SecurityViolationType.SUSPICIOUS_INPUT,
            f"Invalid {field_name}: Must be one of {', '.join(allowed_values)}",
            value
        )

    return value
