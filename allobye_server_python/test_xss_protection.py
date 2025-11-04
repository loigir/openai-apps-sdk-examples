"""XSS Protection Test Suite for AllôBye Backend.

Tests all input validation and sanitization to ensure XSS attacks are prevented.
"""

import pytest
from pydantic import ValidationError

from validators import (
    sanitize_text,
    validate_email,
    validate_name,
    validate_notes,
    validate_child_id,
    validate_emergency_type,
    validate_permission,
)
from main import (
    PickupScheduleInput,
    DelegateAuthorizeInput,
    EmergencyDeclareInput,
    AuthSignupInput,
    AuthLoginInput,
    AuthResetPasswordInput,
)


class TestSanitizeText:
    """Test text sanitization function."""

    def test_remove_script_tags(self):
        """Test that script tags are removed."""
        malicious = '<script>alert("XSS")</script>Hello'
        assert sanitize_text(malicious) == 'Hello'

    def test_remove_script_with_content(self):
        """Test that script tags and content are removed."""
        malicious = 'Hello<script>var x = document.cookie;</script>World'
        result = sanitize_text(malicious)
        assert 'script' not in result.lower()
        assert 'HelloWorld' in result

    def test_remove_html_tags(self):
        """Test that HTML tags are removed."""
        malicious = '<div>Hello</div><p>World</p>'
        assert sanitize_text(malicious) == 'HelloWorld'

    def test_remove_event_handlers(self):
        """Test that event handlers are removed."""
        malicious = '<img src="x" onerror="alert(1)">'
        result = sanitize_text(malicious)
        assert 'onerror' not in result.lower()
        assert 'alert' not in result.lower()

    def test_remove_javascript_protocol(self):
        """Test that javascript: protocol is removed."""
        malicious = '<a href="javascript:alert(1)">Click</a>'
        result = sanitize_text(malicious)
        assert 'javascript:' not in result.lower()

    def test_remove_data_protocol(self):
        """Test that data: protocol is removed."""
        malicious = '<img src="data:text/html,<script>alert(1)</script>">'
        result = sanitize_text(malicious)
        assert 'data:' not in result.lower()

    def test_normal_text_unchanged(self):
        """Test that normal text passes through."""
        normal = "Hello, world! This is a normal string."
        assert sanitize_text(normal) == normal

    def test_none_returns_none(self):
        """Test that None input returns None."""
        assert sanitize_text(None) is None

    def test_empty_string(self):
        """Test that empty string returns empty string."""
        assert sanitize_text("") == ""


class TestValidateEmail:
    """Test email validation."""

    def test_valid_email(self):
        """Test that valid emails pass."""
        assert validate_email("user@example.com") == "user@example.com"

    def test_email_with_xss(self):
        """Test that XSS in email is rejected."""
        with pytest.raises(ValueError):
            validate_email('<script>alert(1)</script>@example.com')

    def test_email_with_html(self):
        """Test that HTML in email is rejected."""
        with pytest.raises(ValueError):
            validate_email('<a href="x">user@example.com</a>')

    def test_lowercase_email(self):
        """Test that emails are lowercased."""
        assert validate_email("USER@EXAMPLE.COM") == "user@example.com"

    def test_invalid_email_format(self):
        """Test that invalid email format is rejected."""
        with pytest.raises(ValueError):
            validate_email("not-an-email")


class TestValidateName:
    """Test name validation."""

    def test_valid_name(self):
        """Test that valid names pass."""
        assert validate_name("Jean Tremblay") == "Jean Tremblay"

    def test_name_with_accents(self):
        """Test that accented characters are allowed."""
        assert validate_name("François Gagnon") == "François Gagnon"

    def test_name_with_hyphen(self):
        """Test that hyphens are allowed."""
        assert validate_name("Marie-Claude") == "Marie-Claude"

    def test_name_with_apostrophe(self):
        """Test that apostrophes are allowed."""
        assert validate_name("O'Brien") == "O'Brien"

    def test_name_with_xss(self):
        """Test that XSS in name is rejected."""
        with pytest.raises(ValueError):
            validate_name('<script>alert(1)</script>')

    def test_name_with_html(self):
        """Test that HTML in name is rejected."""
        with pytest.raises(ValueError):
            validate_name('<b>Bold Name</b>')

    def test_name_too_long(self):
        """Test that overly long names are rejected."""
        with pytest.raises(ValueError):
            validate_name("A" * 101)

    def test_none_name(self):
        """Test that None name returns None."""
        assert validate_name(None) is None


class TestValidateNotes:
    """Test notes validation."""

    def test_valid_notes(self):
        """Test that valid notes pass."""
        notes = "Please pick up at the back entrance."
        assert validate_notes(notes) == notes

    def test_notes_with_xss(self):
        """Test that XSS in notes is sanitized."""
        malicious = 'Normal text <script>alert(1)</script> more text'
        result = validate_notes(malicious)
        assert 'script' not in result.lower()
        assert 'Normal text' in result

    def test_notes_too_long(self):
        """Test that overly long notes are rejected."""
        with pytest.raises(ValueError):
            validate_notes("A" * 501)

    def test_none_notes(self):
        """Test that None notes returns None."""
        assert validate_notes(None) is None


class TestValidateChildId:
    """Test child ID validation."""

    def test_valid_child_id(self):
        """Test that valid child IDs pass."""
        assert validate_child_id("child_123") == "child_123"

    def test_uuid_child_id(self):
        """Test that UUID format child IDs pass."""
        uuid = "550e8400-e29b-41d4-a716-446655440000"
        assert validate_child_id(uuid) == uuid

    def test_child_id_with_xss(self):
        """Test that XSS in child ID is rejected."""
        with pytest.raises(ValueError):
            validate_child_id('<script>alert(1)</script>')

    def test_child_id_with_spaces(self):
        """Test that child IDs with spaces are rejected."""
        with pytest.raises(ValueError):
            validate_child_id('child 123')


class TestValidateEmergencyType:
    """Test emergency type validation."""

    def test_valid_emergency_types(self):
        """Test that valid emergency types pass."""
        assert validate_emergency_type("late") == "late"
        assert validate_emergency_type("illness") == "illness"
        assert validate_emergency_type("cancel") == "cancel"
        assert validate_emergency_type("other") == "other"

    def test_invalid_emergency_type(self):
        """Test that invalid emergency types are rejected."""
        with pytest.raises(ValueError):
            validate_emergency_type("invalid")

    def test_emergency_type_with_xss(self):
        """Test that XSS in emergency type is rejected."""
        with pytest.raises(ValueError):
            validate_emergency_type('<script>alert(1)</script>')


class TestValidatePermission:
    """Test permission validation."""

    def test_valid_permissions(self):
        """Test that valid permissions pass."""
        assert validate_permission("pickup") == "pickup"
        assert validate_permission("emergency_contact") == "emergency_contact"
        assert validate_permission("medical_decisions") == "medical_decisions"

    def test_invalid_permission(self):
        """Test that invalid permissions are rejected."""
        with pytest.raises(ValueError):
            validate_permission("invalid_permission")


class TestPickupScheduleInputModel:
    """Test PickupScheduleInput model validation."""

    def test_valid_pickup_input(self):
        """Test that valid pickup input passes."""
        data = {
            "childIds": ["child_1", "child_2"],
            "pickupPersonId": "person_1",
            "scheduledTime": "2025-11-04T15:00:00-05:00",
            "notes": "Please call when arriving",
        }
        model = PickupScheduleInput(**data)
        assert len(model.child_ids) == 2
        assert model.notes == "Please call when arriving"

    def test_pickup_input_with_xss_notes(self):
        """Test that XSS in notes is sanitized."""
        data = {
            "childIds": ["child_1"],
            "pickupPersonId": "person_1",
            "scheduledTime": "2025-11-04T15:00:00-05:00",
            "notes": '<script>alert(1)</script>Normal note',
        }
        model = PickupScheduleInput(**data)
        assert 'script' not in model.notes.lower()
        assert 'Normal note' in model.notes


class TestDelegateAuthorizeInputModel:
    """Test DelegateAuthorizeInput model validation."""

    def test_valid_delegate_input(self):
        """Test that valid delegate input passes."""
        data = {
            "delegateEmail": "grandma@example.com",
            "childIds": ["child_1"],
            "permissions": ["pickup", "emergency_contact"],
        }
        model = DelegateAuthorizeInput(**data)
        assert model.delegate_email == "grandma@example.com"

    def test_delegate_input_with_invalid_email(self):
        """Test that invalid email is rejected."""
        data = {
            "delegateEmail": "<script>alert(1)</script>",
            "childIds": ["child_1"],
            "permissions": ["pickup"],
        }
        with pytest.raises(ValidationError):
            DelegateAuthorizeInput(**data)


class TestEmergencyDeclareInputModel:
    """Test EmergencyDeclareInput model validation."""

    def test_valid_emergency_input(self):
        """Test that valid emergency input passes."""
        data = {
            "childId": "child_1",
            "emergencyType": "late",
            "context": "Traffic jam on highway",
            "notifyAllDelegates": True,
        }
        model = EmergencyDeclareInput(**data)
        assert model.emergency_type == "late"
        assert model.context == "Traffic jam on highway"

    def test_emergency_input_with_xss_context(self):
        """Test that XSS in context is sanitized."""
        data = {
            "childId": "child_1",
            "emergencyType": "illness",
            "context": '<script>alert(1)</script>Child has fever',
            "notifyAllDelegates": True,
        }
        model = EmergencyDeclareInput(**data)
        assert 'script' not in model.context.lower()
        assert 'Child has fever' in model.context

    def test_emergency_input_with_invalid_type(self):
        """Test that invalid emergency type is rejected."""
        data = {
            "childId": "child_1",
            "emergencyType": "invalid_type",
            "context": "Some context",
        }
        with pytest.raises(ValidationError):
            EmergencyDeclareInput(**data)


class TestAuthSignupInputModel:
    """Test AuthSignupInput model validation."""

    def test_valid_signup_input(self):
        """Test that valid signup input passes."""
        data = {
            "email": "user@example.com",
            "password": "SecurePassword123",
            "name": "Jean Tremblay",
            "role": "parent",
        }
        model = AuthSignupInput(**data)
        assert model.email == "user@example.com"
        assert model.name == "Jean Tremblay"

    def test_signup_input_with_xss_name(self):
        """Test that XSS in name is rejected."""
        data = {
            "email": "user@example.com",
            "password": "SecurePassword123",
            "name": '<script>alert(1)</script>',
            "role": "parent",
        }
        with pytest.raises(ValidationError):
            AuthSignupInput(**data)


class TestAuthLoginInputModel:
    """Test AuthLoginInput model validation."""

    def test_valid_login_input(self):
        """Test that valid login input passes."""
        data = {
            "email": "user@example.com",
            "password": "password123",
        }
        model = AuthLoginInput(**data)
        assert model.email == "user@example.com"

    def test_login_input_with_invalid_email(self):
        """Test that invalid email is rejected."""
        data = {
            "email": "not-an-email",
            "password": "password123",
        }
        with pytest.raises(ValidationError):
            AuthLoginInput(**data)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
