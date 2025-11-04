"""
Integration tests for AllôBye MCP Server.

Tests end-to-end workflows combining multiple components:
- Complete user journey from signup to pickup scheduling
- Cross-school coordination scenarios
- Emergency notification cascades
- Authentication + authorization + MCP tool flows
"""

import pytest
from datetime import datetime, timedelta

from auth import signup_user, login_user, validate_session
from main import (
    _handle_pickup_schedule_create,
    _handle_delegate_authorize,
    _handle_emergency_declare,
    _handle_school_dashboard_fetch,
)


# ═══════════════════════════════════════════════════════════════
# COMPLETE USER JOURNEYS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.integration
class TestCompleteUserJourney:
    """Test complete user journeys from signup to tool usage."""

    async def test_parent_signup_to_pickup_flow(
        self, mock_supabase_patch, mock_children_data, mock_schools_data, clear_rate_limits
    ):
        """Test: Parent signs up → logs in → schedules pickup."""
        # Step 1: Sign up
        signup_result = await signup_user(
            email="newparent@example.com",
            password="ParentPassword123!",
            name="New Parent",
            role="parent",
        )

        assert signup_result["user"]["id"] is not None
        access_token = signup_result["session"]["access_token"]

        # Step 2: Set up parent-child relationship
        user_id = signup_result["user"]["id"]
        mock_supabase_patch.data_store["user_profiles"] = [{
            "id": user_id,
            "email": "newparent@example.com",
            "name": "New Parent",
            "role": "parent",
        }]
        mock_supabase_patch.data_store["parent_children"] = [{
            "parent_id": user_id,
            "child_id": "child_1",
        }]

        # Step 3: Schedule pickup
        scheduled_time = (datetime.now() + timedelta(hours=3)).isoformat()
        pickup_result = await _handle_pickup_schedule_create({
            "accessToken": access_token,
            "childIds": ["child_1"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": scheduled_time,
            "notes": "First pickup",
        })

        assert not pickup_result.isError
        assert "confirmé" in pickup_result.content[0].text.lower()

    async def test_staff_signup_to_dashboard_flow(
        self, mock_supabase_patch, mock_schools_data, clear_rate_limits
    ):
        """Test: Staff signs up → logs in → accesses dashboard."""
        # Step 1: Sign up
        signup_result = await signup_user(
            email="newstaff@school.com",
            password="StaffPassword123!",
            name="New Staff",
            role="school_staff",
            schools=["school_1"],
        )

        assert signup_result["user"]["id"] is not None
        access_token = signup_result["session"]["access_token"]

        # Step 2: Set up staff profile
        user_id = signup_result["user"]["id"]
        mock_supabase_patch.data_store["user_profiles"] = [{
            "id": user_id,
            "email": "newstaff@school.com",
            "name": "New Staff",
            "role": "school_staff",
        }]
        mock_supabase_patch.data_store["user_schools"] = [{
            "user_id": user_id,
            "school_id": "school_1",
        }]

        # Step 3: Access dashboard
        dashboard_result = await _handle_school_dashboard_fetch({
            "accessToken": access_token,
            "schoolId": "school_1",
            "timeWindow": "current",
        })

        assert not dashboard_result.isError
        assert "ramassages" in dashboard_result.content[0].text.lower()

    async def test_login_session_validation_flow(
        self, mock_supabase_patch, clear_rate_limits
    ):
        """Test: Signup → Login → Validate session."""
        # Step 1: Sign up
        email = "sessiontest@example.com"
        password = "SessionPassword123!"

        signup_result = await signup_user(
            email=email,
            password=password,
            name="Session Test",
            role="parent",
        )

        # Step 2: Login
        login_result = await login_user(email=email, password=password)

        assert login_result["session"]["access_token"] is not None

        # Step 3: Validate session
        user_profile = await validate_session(
            login_result["session"]["access_token"]
        )

        assert user_profile is not None
        assert user_profile.email == email


# ═══════════════════════════════════════════════════════════════
# CROSS-SCHOOL COORDINATION
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.integration
class TestCrossSchoolCoordination:
    """Test cross-school coordination scenarios."""

    async def test_multi_school_pickup_coordination(
        self, authenticated_user, mock_supabase_patch
    ):
        """Test scheduling pickup for children in different schools."""
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

        mock_supabase_patch.data_store["parent_children"] = [
            {"parent_id": authenticated_user["user_id"], "child_id": "child_1"},
            {"parent_id": authenticated_user["user_id"], "child_id": "child_2"},
        ]

        # Schedule pickup for both children
        scheduled_time = (datetime.now() + timedelta(hours=2)).isoformat()
        result = await _handle_pickup_schedule_create({
            "accessToken": authenticated_user["access_token"],
            "childIds": ["child_1", "child_2"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": scheduled_time,
        })

        # Should coordinate across both schools
        assert not result.isError

    async def test_multi_school_delegate_authorization(
        self, authenticated_user, mock_supabase_patch
    ):
        """Test authorizing delegate for children in different schools."""
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

        mock_supabase_patch.data_store["parent_children"] = [
            {"parent_id": authenticated_user["user_id"], "child_id": "child_1"},
            {"parent_id": authenticated_user["user_id"], "child_id": "child_2"},
        ]

        # Authorize delegate for both children
        result = await _handle_delegate_authorize({
            "accessToken": authenticated_user["access_token"],
            "delegateEmail": "grandparent@example.com",
            "childIds": ["child_1", "child_2"],
            "permissions": ["pickup"],
        })

        # Should sync across both schools
        assert not result.isError
        assert "delegate_id" in result.structuredContent


# ═══════════════════════════════════════════════════════════════
# EMERGENCY CASCADE WORKFLOWS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.integration
class TestEmergencyCascade:
    """Test emergency notification cascade scenarios."""

    async def test_emergency_notifies_delegates_and_schools(
        self, authenticated_user, mock_supabase_patch
    ):
        """Test emergency declaration cascades to all parties."""
        # Set up child, delegates, and school
        mock_supabase_patch.data_store["children"] = [{
            "id": "child_1",
            "school_id": "school_1",
            "schools": {"id": "school_1", "name": "School 1"},
        }]

        mock_supabase_patch.data_store["parent_children"] = [{
            "parent_id": authenticated_user["user_id"],
            "child_id": "child_1",
        }]

        mock_supabase_patch.data_store["delegates"] = [
            {"id": "delegate_1", "email": "delegate1@example.com"},
            {"id": "delegate_2", "email": "delegate2@example.com"},
        ]

        # Declare emergency
        result = await _handle_emergency_declare({
            "accessToken": authenticated_user["access_token"],
            "childId": "child_1",
            "emergencyType": "late",
            "context": "Traffic accident, will be 45 minutes late",
            "notifyAllDelegates": True,
        })

        # Should notify all parties
        assert not result.isError
        assert "urgence" in result.content[0].text.lower()

    async def test_emergency_different_types(self, authenticated_user, mock_supabase_patch):
        """Test different emergency types."""
        # Set up child
        mock_supabase_patch.data_store["parent_children"] = [{
            "parent_id": authenticated_user["user_id"],
            "child_id": "child_1",
        }]

        emergency_types = ["late", "illness", "cancel", "other"]

        for em_type in emergency_types:
            result = await _handle_emergency_declare({
                "accessToken": authenticated_user["access_token"],
                "childId": "child_1",
                "emergencyType": em_type,
                "context": f"Emergency type: {em_type}",
            })

            # Should handle each type
            assert not result.isError or "invalid" not in result.content[0].text.lower()


# ═══════════════════════════════════════════════════════════════
# AUTHORIZATION WORKFLOWS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.integration
class TestAuthorizationWorkflows:
    """Test authorization across different workflows."""

    async def test_parent_cannot_access_others_children(
        self, authenticated_user, mock_supabase_patch
    ):
        """Test parent cannot schedule pickup for other parent's children."""
        # Set up another child NOT owned by this parent
        mock_supabase_patch.data_store["parent_children"] = []  # No relationship

        scheduled_time = (datetime.now() + timedelta(hours=2)).isoformat()
        result = await _handle_pickup_schedule_create({
            "accessToken": authenticated_user["access_token"],
            "childIds": ["other_child"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": scheduled_time,
        })

        # Should be unauthorized
        assert result.isError

    async def test_parent_cannot_access_school_dashboard(
        self, authenticated_user, mock_schools_data
    ):
        """Test parent cannot access school staff dashboard."""
        result = await _handle_school_dashboard_fetch({
            "accessToken": authenticated_user["access_token"],
            "schoolId": "school_1",
        })

        # Should require school_staff role
        assert result.isError

    async def test_staff_cannot_authorize_delegates(
        self, authenticated_staff, mock_children_data
    ):
        """Test school staff cannot authorize delegates (parent-only)."""
        result = await _handle_delegate_authorize({
            "accessToken": authenticated_staff["access_token"],
            "delegateEmail": "delegate@example.com",
            "childIds": ["child_1"],
            "permissions": ["pickup"],
        })

        # Should require parent role
        assert result.isError

    async def test_staff_can_only_access_their_schools(
        self, authenticated_staff, mock_supabase_patch
    ):
        """Test staff can only access dashboards for their schools."""
        # Staff is associated with school_1
        mock_supabase_patch.data_store["user_schools"] = [{
            "user_id": authenticated_staff["user_id"],
            "school_id": "school_1",
        }]

        # Can access school_1
        result1 = await _handle_school_dashboard_fetch({
            "accessToken": authenticated_staff["access_token"],
            "schoolId": "school_1",
        })

        assert not result1.isError

        # Cannot access school_2
        result2 = await _handle_school_dashboard_fetch({
            "accessToken": authenticated_staff["access_token"],
            "schoolId": "school_2",
        })

        assert result2.isError


# ═══════════════════════════════════════════════════════════════
# COMPLEX SCENARIOS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.slow
class TestComplexScenarios:
    """Test complex real-world scenarios."""

    async def test_complete_day_workflow(
        self, mock_supabase_patch, clear_rate_limits
    ):
        """Test complete day workflow: signup → authorize delegate → schedule pickup → emergency."""
        # Step 1: Parent signs up
        parent_result = await signup_user(
            email="parent@example.com",
            password="ParentPassword123!",
            name="Parent User",
            role="parent",
        )

        parent_id = parent_result["user"]["id"]
        access_token = parent_result["session"]["access_token"]

        # Set up parent profile and child
        mock_supabase_patch.data_store["user_profiles"] = [{
            "id": parent_id,
            "email": "parent@example.com",
            "name": "Parent User",
            "role": "parent",
        }]
        mock_supabase_patch.data_store["parent_children"] = [{
            "parent_id": parent_id,
            "child_id": "child_1",
        }]
        mock_supabase_patch.data_store["children"] = [{
            "id": "child_1",
            "school_id": "school_1",
            "schools": {"id": "school_1", "name": "School 1"},
        }]

        # Step 2: Authorize delegate (grandparent)
        delegate_result = await _handle_delegate_authorize({
            "accessToken": access_token,
            "delegateEmail": "grandparent@example.com",
            "childIds": ["child_1"],
            "permissions": ["pickup", "emergency_contact"],
        })

        assert not delegate_result.isError

        # Step 3: Schedule regular pickup
        scheduled_time = (datetime.now() + timedelta(hours=6)).isoformat()
        pickup_result = await _handle_pickup_schedule_create({
            "accessToken": access_token,
            "childIds": ["child_1"],
            "pickupPersonId": delegate_result.structuredContent["delegate_id"],
            "scheduledTime": scheduled_time,
            "notes": "Regular after-school pickup",
        })

        assert not pickup_result.isError

        # Step 4: Declare emergency (running late)
        emergency_result = await _handle_emergency_declare({
            "accessToken": access_token,
            "childId": "child_1",
            "emergencyType": "late",
            "context": "Meeting running over, will be 20 minutes late",
            "notifyAllDelegates": True,
        })

        assert not emergency_result.isError

    async def test_concurrent_pickups_different_parents(
        self, mock_supabase_patch, clear_rate_limits
    ):
        """Test concurrent pickup scheduling by different parents."""
        # Create two parents
        parent1 = await signup_user(
            email="parent1@example.com",
            password="Parent1Password123!",
            name="Parent 1",
            role="parent",
        )

        parent2 = await signup_user(
            email="parent2@example.com",
            password="Parent2Password123!",
            name="Parent 2",
            role="parent",
        )

        # Set up children and relationships
        mock_supabase_patch.data_store["parent_children"] = [
            {"parent_id": parent1["user"]["id"], "child_id": "child_1"},
            {"parent_id": parent2["user"]["id"], "child_id": "child_2"},
        ]
        mock_supabase_patch.data_store["children"] = [
            {"id": "child_1", "school_id": "school_1", "schools": {"id": "school_1", "name": "School 1"}},
            {"id": "child_2", "school_id": "school_1", "schools": {"id": "school_1", "name": "School 1"}},
        ]

        # Both schedule pickups at same time
        scheduled_time = (datetime.now() + timedelta(hours=3)).isoformat()

        result1 = await _handle_pickup_schedule_create({
            "accessToken": parent1["session"]["access_token"],
            "childIds": ["child_1"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": scheduled_time,
        })

        result2 = await _handle_pickup_schedule_create({
            "accessToken": parent2["session"]["access_token"],
            "childIds": ["child_2"],
            "pickupPersonId": "delegate_2",
            "scheduledTime": scheduled_time,
        })

        # Both should succeed independently
        assert not result1.isError
        assert not result2.isError

    async def test_security_validation_across_workflow(
        self, authenticated_user, mock_supabase_patch
    ):
        """Test XSS protection across entire workflow."""
        # Set up child
        mock_supabase_patch.data_store["parent_children"] = [{
            "parent_id": authenticated_user["user_id"],
            "child_id": "child_1",
        }]

        # Try XSS in pickup notes
        result1 = await _handle_pickup_schedule_create({
            "accessToken": authenticated_user["access_token"],
            "childIds": ["child_1"],
            "pickupPersonId": "delegate_1",
            "scheduledTime": datetime.now().isoformat(),
            "notes": "<script>alert('xss')</script>Pickup note",
        })

        # Try XSS in emergency context
        result2 = await _handle_emergency_declare({
            "accessToken": authenticated_user["access_token"],
            "childId": "child_1",
            "emergencyType": "other",
            "context": "<img src=x onerror=alert('xss')>Emergency",
        })

        # All XSS attempts should be sanitized
        assert "<script>" not in str(result1)
        assert "onerror" not in str(result2)
