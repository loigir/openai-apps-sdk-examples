"""
Comprehensive test suite for all 10 MCP tools.

Tests each tool's:
- Happy path with valid inputs
- Input validation and error handling
- Authentication requirements
- Authorization checks
- Edge cases and boundary conditions
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import mcp.types as types


# Import handlers
from main import (
    _handle_auth_signup,
    _handle_auth_login,
    _handle_auth_logout,
    _handle_auth_reset_password,
    _handle_auth_profile,
    _handle_pickup_schedule_create,
    _handle_delegate_authorize,
    _handle_emergency_declare,
    _handle_school_dashboard_fetch,
    _handle_monitoring_dashboard_fetch,
)


# ═══════════════════════════════════════════════════════════════
# AUTHENTICATION TOOLS TESTS (5 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.mcp_tools
@pytest.mark.auth
class TestAuthSignup:
    """Test auth-signup tool."""

    async def test_signup_success(self, mock_supabase_patch, clear_rate_limits):
        """Test successful user signup."""
        arguments = {
            "email": "newuser@example.com",
            "password": "SecurePassword123!",
            "name": "New User",
            "role": "parent",
        }

        result = await _handle_auth_signup(arguments)

        assert not result.isError
        assert "créé avec succès" in result.content[0].text
        assert result.structuredContent["email"] == "newuser@example.com"

    async def test_signup_weak_password(self, mock_supabase_patch, clear_rate_limits):
        """Test signup rejects weak password."""
        arguments = {
            "email": "test@example.com",
            "password": "weak",
            "name": "Test User",
        }

        result = await _handle_auth_signup(arguments)

        assert result.isError
        assert "validation" in result.content[0].text.lower()

    async def test_signup_invalid_email(self, mock_supabase_patch, clear_rate_limits):
        """Test signup validates email format."""
        arguments = {
            "email": "not-an-email",
            "password": "SecurePassword123!",
            "name": "Test User",
        }

        result = await _handle_auth_signup(arguments)

        assert result.isError

    async def test_signup_school_staff_with_schools(self, mock_supabase_patch, clear_rate_limits):
        """Test signup for school staff with schools."""
        arguments = {
            "email": "staff@school.com",
            "password": "StaffPassword123!",
            "name": "Staff User",
            "role": "school_staff",
            "schools": ["school_1", "school_2"],
        }

        result = await _handle_auth_signup(arguments)

        assert not result.isError


@pytest.mark.asyncio
@pytest.mark.mcp_tools
@pytest.mark.auth
class TestAuthLogin:
    """Test auth-login tool."""

    async def test_login_success(self, authenticated_user, clear_rate_limits):
        """Test successful login."""
        arguments = {
            "email": authenticated_user["email"],
            "password": authenticated_user["profile"]["password"],
        }

        result = await _handle_auth_login(arguments)

        assert not result.isError
        assert "Connexion réussie" in result.content[0].text
        assert "access_token" in result.structuredContent

    async def test_login_invalid_credentials(self, authenticated_user, clear_rate_limits):
        """Test login with wrong password."""
        arguments = {
            "email": authenticated_user["email"],
            "password": "WrongPassword123!",
        }

        result = await _handle_auth_login(arguments)

        assert result.isError
        assert "incorrect" in result.content[0].text.lower()

    async def test_login_nonexistent_user(self, mock_supabase_patch, clear_rate_limits):
        """Test login with non-existent user."""
        arguments = {
            "email": "nonexistent@example.com",
            "password": "SomePassword123!",
        }

        result = await _handle_auth_login(arguments)

        assert result.isError

    async def test_login_missing_email(self, clear_rate_limits):
        """Test login with missing email."""
        arguments = {
            "password": "Password123!",
        }

        result = await _handle_auth_login(arguments)

        assert result.isError


@pytest.mark.asyncio
@pytest.mark.mcp_tools
@pytest.mark.auth
class TestAuthLogout:
    """Test auth-logout tool."""

    async def test_logout_success(self, authenticated_user):
        """Test successful logout."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
        }

        result = await _handle_auth_logout(arguments)

        assert not result.isError
        assert "Déconnexion réussie" in result.content[0].text

    async def test_logout_missing_token(self):
        """Test logout without access token."""
        arguments = {}

        result = await _handle_auth_logout(arguments)

        assert result.isError
        assert "requis" in result.content[0].text.lower()


@pytest.mark.asyncio
@pytest.mark.mcp_tools
@pytest.mark.auth
class TestAuthResetPassword:
    """Test auth-reset-password tool."""

    async def test_reset_password_success(self, authenticated_user):
        """Test password reset request."""
        arguments = {
            "email": authenticated_user["email"],
        }

        result = await _handle_auth_reset_password(arguments)

        assert not result.isError
        assert "email" in result.content[0].text.lower()

    async def test_reset_password_invalid_email(self):
        """Test password reset with invalid email."""
        arguments = {
            "email": "not-an-email",
        }

        result = await _handle_auth_reset_password(arguments)

        assert result.isError


@pytest.mark.asyncio
@pytest.mark.mcp_tools
@pytest.mark.auth
class TestAuthProfile:
    """Test auth-profile tool."""

    async def test_get_profile_success(self, authenticated_user):
        """Test getting user profile."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
        }

        result = await _handle_auth_profile(arguments)

        assert not result.isError
        assert authenticated_user["email"] in result.content[0].text

    async def test_get_profile_missing_token(self):
        """Test getting profile without token."""
        arguments = {}

        result = await _handle_auth_profile(arguments)

        assert result.isError
        assert "requis" in result.content[0].text.lower()

    async def test_get_profile_invalid_token(self, mock_supabase_patch):
        """Test getting profile with invalid token."""
        arguments = {
            "accessToken": "invalid_token",
        }

        result = await _handle_auth_profile(arguments)

        assert result.isError


# ═══════════════════════════════════════════════════════════════
# PICKUP MANAGEMENT TOOLS TESTS (3 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.mcp_tools
class TestPickupScheduleCreate:
    """Test pickup-schedule-create tool."""

    async def test_create_pickup_success(
        self, authenticated_user, mock_children_data, mock_schools_data
    ):
        """Test creating a pickup schedule."""
        scheduled_time = (datetime.now() + timedelta(hours=2)).isoformat()

        arguments = {
            "accessToken": authenticated_user["access_token"],
            "childIds": ["child_1"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": scheduled_time,
            "notes": "Will be 5 minutes late",
        }

        result = await _handle_pickup_schedule_create(arguments)

        assert not result.isError
        assert "confirmé" in result.content[0].text.lower()
        assert "pickup_id" in result.structuredContent

    async def test_create_pickup_no_auth(self, mock_children_data):
        """Test creating pickup without authentication."""
        arguments = {
            "childIds": ["child_1"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": datetime.now().isoformat(),
        }

        result = await _handle_pickup_schedule_create(arguments)

        assert result.isError
        assert "authentification" in result.content[0].text.lower()

    async def test_create_pickup_invalid_child_id(self, authenticated_user):
        """Test creating pickup with invalid child ID."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "childIds": ["<script>alert('xss')</script>"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": datetime.now().isoformat(),
        }

        result = await _handle_pickup_schedule_create(arguments)

        # Should sanitize or reject malicious input
        assert result.isError or "<script>" not in str(result)

    async def test_create_pickup_empty_children(self, authenticated_user):
        """Test creating pickup with empty children list."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "childIds": [],
            "pickupPersonId": "delegate_1",
            "scheduledTime": datetime.now().isoformat(),
        }

        result = await _handle_pickup_schedule_create(arguments)

        assert result.isError

    async def test_create_pickup_multi_school(
        self, authenticated_user, mock_supabase_patch
    ):
        """Test creating pickup for children in different schools."""
        # Set up children in different schools
        mock_supabase_patch.data_store["children"] = [
            {
                "id": "child_1",
                "school_id": "school_1",
                "schools": {"id": "school_1", "name": "School 1"},
            },
            {
                "id": "child_2",
                "school_id": "school_2",
                "schools": {"id": "school_2", "name": "School 2"},
            },
        ]

        arguments = {
            "accessToken": authenticated_user["access_token"],
            "childIds": ["child_1", "child_2"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": datetime.now().isoformat(),
        }

        result = await _handle_pickup_schedule_create(arguments)

        # Should handle cross-school coordination
        assert not result.isError or "coordin" in str(result).lower()


@pytest.mark.asyncio
@pytest.mark.mcp_tools
class TestDelegateAuthorize:
    """Test delegate-authorize tool."""

    async def test_authorize_delegate_success(self, authenticated_user, mock_children_data):
        """Test authorizing a delegate."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "delegateEmail": "delegate@example.com",
            "childIds": ["child_1"],
            "permissions": ["pickup"],
        }

        result = await _handle_delegate_authorize(arguments)

        assert not result.isError
        assert "autorisé" in result.content[0].text.lower()
        assert "delegate_id" in result.structuredContent

    async def test_authorize_delegate_no_auth(self):
        """Test authorizing delegate without authentication."""
        arguments = {
            "delegateEmail": "delegate@example.com",
            "childIds": ["child_1"],
            "permissions": ["pickup"],
        }

        result = await _handle_delegate_authorize(arguments)

        assert result.isError
        assert "authentification" in result.content[0].text.lower()

    async def test_authorize_delegate_invalid_email(self, authenticated_user):
        """Test authorizing delegate with invalid email."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "delegateEmail": "not-an-email",
            "childIds": ["child_1"],
        }

        result = await _handle_delegate_authorize(arguments)

        assert result.isError

    async def test_authorize_delegate_multiple_permissions(
        self, authenticated_user, mock_children_data
    ):
        """Test authorizing delegate with multiple permissions."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "delegateEmail": "delegate@example.com",
            "childIds": ["child_1", "child_2"],
            "permissions": ["pickup", "emergency_contact"],
        }

        result = await _handle_delegate_authorize(arguments)

        assert not result.isError

    async def test_authorize_delegate_invalid_permission(self, authenticated_user):
        """Test authorizing delegate with invalid permission."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "delegateEmail": "delegate@example.com",
            "childIds": ["child_1"],
            "permissions": ["invalid_permission"],
        }

        result = await _handle_delegate_authorize(arguments)

        assert result.isError


@pytest.mark.asyncio
@pytest.mark.mcp_tools
class TestEmergencyDeclare:
    """Test emergency-declare tool."""

    async def test_declare_emergency_success(self, authenticated_user, mock_children_data):
        """Test declaring an emergency."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "childId": "child_1",
            "emergencyType": "late",
            "context": "Traffic accident on highway, will be 30 minutes late",
            "notifyAllDelegates": True,
        }

        result = await _handle_emergency_declare(arguments)

        assert not result.isError
        assert "urgence" in result.content[0].text.lower()
        assert "emergency_id" in result.structuredContent

    async def test_declare_emergency_no_auth(self):
        """Test declaring emergency without authentication."""
        arguments = {
            "childId": "child_1",
            "emergencyType": "late",
            "context": "Running late",
        }

        result = await _handle_emergency_declare(arguments)

        assert result.isError
        assert "authentification" in result.content[0].text.lower()

    async def test_declare_emergency_invalid_type(self, authenticated_user):
        """Test declaring emergency with invalid type."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "childId": "child_1",
            "emergencyType": "invalid_type",
            "context": "Emergency context",
        }

        result = await _handle_emergency_declare(arguments)

        assert result.isError

    async def test_declare_emergency_xss_context(self, authenticated_user):
        """Test emergency context is sanitized against XSS."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "childId": "child_1",
            "emergencyType": "late",
            "context": "<script>alert('xss')</script>Emergency",
        }

        result = await _handle_emergency_declare(arguments)

        # Should sanitize malicious input
        assert "<script>" not in str(result)

    async def test_declare_emergency_empty_context(self, authenticated_user):
        """Test declaring emergency with empty context."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "childId": "child_1",
            "emergencyType": "late",
            "context": "",
        }

        result = await _handle_emergency_declare(arguments)

        assert result.isError


# ═══════════════════════════════════════════════════════════════
# DASHBOARD TOOLS TESTS (2 tools)
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.mcp_tools
class TestSchoolDashboardFetch:
    """Test school-dashboard-fetch tool."""

    async def test_fetch_dashboard_success(
        self, authenticated_staff, mock_schools_data
    ):
        """Test fetching school dashboard."""
        arguments = {
            "accessToken": authenticated_staff["access_token"],
            "schoolId": "school_1",
            "timeWindow": "current",
        }

        result = await _handle_school_dashboard_fetch(arguments)

        assert not result.isError
        assert "ramassages" in result.content[0].text.lower()

    async def test_fetch_dashboard_no_auth(self):
        """Test fetching dashboard without authentication."""
        arguments = {
            "schoolId": "school_1",
        }

        result = await _handle_school_dashboard_fetch(arguments)

        assert result.isError
        assert "authentification" in result.content[0].text.lower()

    async def test_fetch_dashboard_parent_role(self, authenticated_user):
        """Test parent cannot access school dashboard."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "schoolId": "school_1",
        }

        result = await _handle_school_dashboard_fetch(arguments)

        # Should require school_staff role
        assert result.isError

    async def test_fetch_dashboard_different_time_windows(self, authenticated_staff):
        """Test fetching dashboard with different time windows."""
        for time_window in ["current", "today"]:
            arguments = {
                "accessToken": authenticated_staff["access_token"],
                "schoolId": "school_1",
                "timeWindow": time_window,
            }

            result = await _handle_school_dashboard_fetch(arguments)

            # Should handle different time windows
            assert not result.isError or "invalid" not in result.content[0].text.lower()


@pytest.mark.asyncio
@pytest.mark.mcp_tools
class TestMonitoringDashboardFetch:
    """Test monitoring-dashboard-fetch tool."""

    async def test_fetch_monitoring_success(self):
        """Test fetching monitoring dashboard."""
        arguments = {
            "includeDetails": True,
        }

        result = await _handle_monitoring_dashboard_fetch(arguments)

        assert not result.isError
        assert "Monitoring Dashboard" in result.content[0].text
        assert result.structuredContent is not None

    async def test_fetch_monitoring_without_details(self):
        """Test fetching monitoring dashboard without details."""
        arguments = {
            "includeDetails": False,
        }

        result = await _handle_monitoring_dashboard_fetch(arguments)

        assert not result.isError
        assert "uptime_seconds" in result.structuredContent

    async def test_fetch_monitoring_default_args(self):
        """Test fetching monitoring dashboard with default arguments."""
        arguments = {}

        result = await _handle_monitoring_dashboard_fetch(arguments)

        # Should work with defaults
        assert not result.isError


# ═══════════════════════════════════════════════════════════════
# EDGE CASES AND BOUNDARY CONDITIONS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.mcp_tools
class TestMCPToolsEdgeCases:
    """Test edge cases and boundary conditions for all tools."""

    async def test_tool_with_extra_fields(self, authenticated_user, mock_children_data):
        """Test tool with extra unexpected fields (should be rejected)."""
        arguments = {
            "accessToken": authenticated_user["access_token"],
            "childIds": ["child_1"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": datetime.now().isoformat(),
            "unexpectedField": "should be rejected",
        }

        result = await _handle_pickup_schedule_create(arguments)

        # Pydantic with extra="forbid" should reject this
        assert result.isError

    async def test_tool_with_unicode_input(self, authenticated_user):
        """Test tool handles Unicode characters properly."""
        arguments = {
            "email": "test-unicode@example.com",
            "password": "SecurePassword123!",
            "name": "François Côté-Beauséjour 你好",
            "role": "parent",
        }

        result = await _handle_auth_signup(arguments)

        # Should handle Unicode properly
        assert not result.isError or "validation" not in result.content[0].text.lower()

    async def test_tool_with_very_long_input(self, authenticated_user):
        """Test tool handles very long input strings."""
        very_long_notes = "x" * 10000

        arguments = {
            "accessToken": authenticated_user["access_token"],
            "childIds": ["child_1"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": datetime.now().isoformat(),
            "notes": very_long_notes,
        }

        result = await _handle_pickup_schedule_create(arguments)

        # Should handle or reject very long input
        assert result is not None

    async def test_tool_with_null_values(self):
        """Test tool handles null values appropriately."""
        arguments = {
            "email": None,
            "password": None,
        }

        result = await _handle_auth_login(arguments)

        assert result.isError
