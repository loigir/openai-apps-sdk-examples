"""XSS Protection and Input Validation Utilities for AllôBye Backend.

This module provides Pydantic validators and sanitization functions to prevent
XSS attacks and ensure data integrity at the API boundary.
"""

import re
from typing import Optional
from pydantic import field_validator


def sanitize_text(value: Optional[str]) -> Optional[str]:
    """Sanitize text input by removing HTML tags and dangerous characters.

    Args:
        value: Input string that may contain malicious content

    Returns:
        Sanitized string with HTML tags removed, or None if input is None
    """
    if value is None:
        return None

    if not isinstance(value, str):
        return str(value)  # type: ignore[unreachable]

    # Remove script tags and their content FIRST (before general HTML tag removal)
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', value, flags=re.IGNORECASE | re.DOTALL)

    # Remove style tags and their content
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.IGNORECASE | re.DOTALL)

    # Remove ALL HTML tags (including content between tags if dangerous)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)

    # Remove event handlers (onclick, onerror, etc.)
    cleaned = re.sub(r'on\w+\s*=\s*["\'][^"\']*["\']', '', cleaned, flags=re.IGNORECASE)

    # Remove javascript: protocol
    cleaned = re.sub(r'javascript:', '', cleaned, flags=re.IGNORECASE)

    # Remove data: protocol (can be used for XSS)
    cleaned = re.sub(r'data:', '', cleaned, flags=re.IGNORECASE)

    # Normalize whitespace
    cleaned = ' '.join(cleaned.split())

    return cleaned.strip()


def validate_email(value: str) -> str:
    """Validate and sanitize email addresses.

    Args:
        value: Email address string

    Returns:
        Sanitized email address

    Raises:
        ValueError: If email format is invalid
    """
    if not value:
        raise ValueError("Email address is required")

    # Check for HTML before sanitization to reject malicious input
    if '<' in value or '>' in value:
        raise ValueError(f"Invalid email address format (HTML tags not allowed)")

    # Remove any HTML tags
    cleaned = sanitize_text(value)

    if not cleaned:
        raise ValueError("Email address cannot be empty after sanitization")

    # Basic email validation pattern
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

    if not re.match(email_pattern, cleaned):
        raise ValueError(f"Invalid email address format: {cleaned}")

    return cleaned.lower()


def validate_name(value: Optional[str]) -> Optional[str]:
    """Validate and sanitize name fields.

    Args:
        value: Name string

    Returns:
        Sanitized name

    Raises:
        ValueError: If name contains invalid characters
    """
    if value is None:
        return None

    # Check for HTML before sanitization to reject malicious input
    if '<' in value or '>' in value:
        raise ValueError(f"Name contains invalid characters (HTML tags not allowed)")

    cleaned = sanitize_text(value)

    if not cleaned:
        raise ValueError("Name cannot be empty after sanitization")

    # Allow only letters, spaces, hyphens, apostrophes, and accented characters
    if not re.match(r"^[a-zA-ZÀ-ÿ\s'\-]+$", cleaned):
        raise ValueError(f"Name contains invalid characters: {cleaned}")

    if len(cleaned) > 100:
        raise ValueError("Name must be 100 characters or less")

    return cleaned


def validate_notes(value: Optional[str]) -> Optional[str]:
    """Validate and sanitize notes/context fields.

    Args:
        value: Notes text

    Returns:
        Sanitized notes
    """
    if value is None:
        return None

    cleaned = sanitize_text(value)

    if not cleaned:
        return None

    # Limit length to prevent abuse
    if len(cleaned) > 500:
        raise ValueError("Notes must be 500 characters or less")

    return cleaned


def validate_child_id(value: str) -> str:
    """Validate child ID format.

    Args:
        value: Child ID string

    Returns:
        Validated child ID

    Raises:
        ValueError: If ID format is invalid
    """
    if not value:
        raise ValueError("Child ID is required")

    # Remove any HTML/script tags
    cleaned = sanitize_text(value)

    if not cleaned:
        raise ValueError("Child ID cannot be empty after sanitization")

    # Allow only alphanumeric, hyphens, and underscores (UUID-like format)
    if not re.match(r'^[a-zA-Z0-9_-]+$', cleaned):
        raise ValueError(f"Invalid child ID format: {cleaned}")

    if len(cleaned) > 100:
        raise ValueError("Child ID must be 100 characters or less")

    return cleaned


def validate_emergency_type(value: str) -> str:
    """Validate emergency type against allowed values.

    Args:
        value: Emergency type string

    Returns:
        Validated emergency type

    Raises:
        ValueError: If emergency type is not allowed
    """
    allowed_types = {'late', 'illness', 'cancel', 'other'}

    cleaned = sanitize_text(value)

    if not cleaned:
        raise ValueError("Emergency type cannot be empty")

    cleaned_lower = cleaned.lower()

    if cleaned_lower not in allowed_types:
        raise ValueError(f"Invalid emergency type. Must be one of: {', '.join(allowed_types)}")

    return cleaned_lower


def validate_permission(value: str) -> str:
    """Validate permission string against allowed values.

    Args:
        value: Permission string

    Returns:
        Validated permission

    Raises:
        ValueError: If permission is not allowed
    """
    allowed_permissions = {'pickup', 'emergency_contact', 'medical_decisions'}

    cleaned = sanitize_text(value)

    if not cleaned:
        raise ValueError("Permission cannot be empty")

    cleaned_lower = cleaned.lower()

    if cleaned_lower not in allowed_permissions:
        raise ValueError(f"Invalid permission. Must be one of: {', '.join(allowed_permissions)}")

    return cleaned_lower
