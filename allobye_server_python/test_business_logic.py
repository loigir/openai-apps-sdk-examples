"""Comprehensive test suite for business logic module.

This test suite validates all pure business rules without external dependencies.
All tests are unit tests that can run in isolation.
"""

import pytest
from datetime import datetime, timedelta
from business_logic import (
    # Time window functions
    calculate_time_window,
    is_within_school_hours,
    calculate_eta_minutes,
    calculate_delay_minutes,
    is_pickup_overdue,
    # Pickup validation functions
    validate_pickup_time,
    validate_child_limit,
    should_coordinate_cross_school,
    # Permission functions
    validate_permissions,
    has_permission,
    is_delegate_expired,
    validate_delegate_authorization,
    can_delegate_pickup_child,
    # Emergency handling functions
    validate_emergency_type,
    calculate_notification_priority,
    determine_notification_recipients,
    should_escalate_emergency,
    # Multi-school coordination functions
    group_children_by_school,
    calculate_coordination_sequence,
    requires_additional_coordination_time,
    # State management functions
    get_next_pickup_state,
    can_cancel_pickup,
    calculate_pickup_metrics,
    # Enums and constants
    PickupStatus,
    EmergencyType,
    Permission,
    TimeWindow,
    CURRENT_WINDOW_MINUTES,
    SCHOOL_START_HOUR,
    SCHOOL_END_HOUR,
    MIN_ADVANCE_NOTICE_MINUTES,
    MAX_FUTURE_DAYS,
    MAX_CHILDREN_PER_PICKUP,
)


# ═══════════════════════════════════════════════════════════════
# TIME WINDOW TESTS
# ═══════════════════════════════════════════════════════════════


class TestTimeWindowFunctions:
    """Test suite for time window calculations."""

    def test_calculate_time_window_current(self):
        """Test current time window calculation (30 minutes)."""
        now = datetime(2025, 11, 4, 14, 30)
        time_range = calculate_time_window(TimeWindow.CURRENT.value, reference_time=now)

        assert time_range.start == now
        assert time_range.end == now + timedelta(minutes=CURRENT_WINDOW_MINUTES)
        assert time_range.duration_minutes() == CURRENT_WINDOW_MINUTES

    def test_calculate_time_window_today(self):
        """Test today time window calculation."""
        now = datetime(2025, 11, 4, 14, 30)
        time_range = calculate_time_window(TimeWindow.TODAY.value, reference_time=now)

        assert time_range.start.hour == 0
        assert time_range.start.minute == 0
        assert time_range.end.hour == 23
        assert time_range.end.minute == 59

    def test_calculate_time_window_custom(self):
        """Test custom time window calculation."""
        start = datetime(2025, 11, 4, 9, 0)
        end = datetime(2025, 11, 4, 17, 0)
        time_range = calculate_time_window(
            TimeWindow.CUSTOM.value,
            custom_start=start,
            custom_end=end
        )

        assert time_range.start == start
        assert time_range.end == end

    def test_calculate_time_window_custom_missing_params(self):
        """Test custom window fails without start/end times."""
        with pytest.raises(ValueError, match="Custom window requires both start and end times"):
            calculate_time_window(TimeWindow.CUSTOM.value)

    def test_time_range_contains(self):
        """Test TimeRange.contains() method."""
        start = datetime(2025, 11, 4, 9, 0)
        end = datetime(2025, 11, 4, 17, 0)
        time_range = calculate_time_window(
            TimeWindow.CUSTOM.value,
            custom_start=start,
            custom_end=end
        )

        # Should contain times within range
        assert time_range.contains(datetime(2025, 11, 4, 12, 0))

        # Should not contain times outside range
        assert not time_range.contains(datetime(2025, 11, 4, 8, 0))
        assert not time_range.contains(datetime(2025, 11, 4, 18, 0))

    def test_is_within_school_hours_valid(self):
        """Test valid school hours."""
        valid_time = datetime(2025, 11, 4, 10, 30)
        assert is_within_school_hours(valid_time) is True

    def test_is_within_school_hours_early(self):
        """Test time before school hours."""
        early_time = datetime(2025, 11, 4, 6, 30)
        assert is_within_school_hours(early_time) is False

    def test_is_within_school_hours_late(self):
        """Test time after school hours."""
        late_time = datetime(2025, 11, 4, 18, 30)
        assert is_within_school_hours(late_time) is False

    def test_calculate_eta_minutes_future(self):
        """Test ETA calculation for future pickup."""
        now = datetime(2025, 11, 4, 14, 0)
        scheduled = datetime(2025, 11, 4, 14, 30)
        eta = calculate_eta_minutes(scheduled, current_time=now)

        assert eta == 30

    def test_calculate_eta_minutes_past(self):
        """Test ETA calculation for overdue pickup."""
        now = datetime(2025, 11, 4, 14, 30)
        scheduled = datetime(2025, 11, 4, 14, 0)
        eta = calculate_eta_minutes(scheduled, current_time=now)

        assert eta == -30

    def test_calculate_delay_minutes_late(self):
        """Test delay calculation when late."""
        scheduled = datetime(2025, 11, 4, 14, 0)
        actual = datetime(2025, 11, 4, 14, 15)
        delay = calculate_delay_minutes(scheduled, actual)

        assert delay == 15

    def test_calculate_delay_minutes_early(self):
        """Test delay calculation when early."""
        scheduled = datetime(2025, 11, 4, 14, 0)
        actual = datetime(2025, 11, 4, 13, 50)
        delay = calculate_delay_minutes(scheduled, actual)

        assert delay == -10

    def test_is_pickup_overdue_yes(self):
        """Test overdue detection for late pickup."""
        # Mock datetime.now() by using scheduled time in the past
        scheduled = datetime.now() - timedelta(minutes=20)
        assert is_pickup_overdue(scheduled, grace_period_minutes=5) is True

    def test_is_pickup_overdue_no(self):
        """Test overdue detection for on-time pickup."""
        scheduled = datetime.now() + timedelta(minutes=10)
        assert is_pickup_overdue(scheduled, grace_period_minutes=5) is False


# ═══════════════════════════════════════════════════════════════
# PICKUP VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════


class TestPickupValidation:
    """Test suite for pickup validation rules."""

    def test_validate_pickup_time_valid(self):
        """Test valid pickup time."""
        now = datetime(2025, 11, 4, 10, 0)
        scheduled = datetime(2025, 11, 4, 15, 0)  # 5 hours in future, during school hours
        result = validate_pickup_time(scheduled, reference_time=now)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_pickup_time_in_past(self):
        """Test pickup time in the past."""
        now = datetime(2025, 11, 4, 15, 0)
        scheduled = datetime(2025, 11, 4, 14, 0)
        result = validate_pickup_time(scheduled, reference_time=now)

        assert result.valid is False
        assert "past" in result.errors[0].lower()

    def test_validate_pickup_time_insufficient_notice(self):
        """Test pickup without minimum advance notice."""
        now = datetime(2025, 11, 4, 15, 0)
        scheduled = datetime(2025, 11, 4, 15, 10)  # Only 10 minutes notice
        result = validate_pickup_time(scheduled, reference_time=now)

        assert result.valid is False
        assert "advance notice" in result.errors[0].lower()

    def test_validate_pickup_time_too_far_future(self):
        """Test pickup too far in the future."""
        now = datetime(2025, 11, 4, 15, 0)
        scheduled = datetime(2025, 11, 12, 15, 0)  # 8 days in future
        result = validate_pickup_time(scheduled, reference_time=now)

        assert result.valid is False
        assert "days in advance" in result.errors[0].lower()

    def test_validate_pickup_time_outside_school_hours(self):
        """Test pickup outside school hours."""
        now = datetime(2025, 11, 4, 10, 0)
        scheduled = datetime(2025, 11, 4, 19, 0)  # 7pm, after school closes
        result = validate_pickup_time(scheduled, reference_time=now)

        assert result.valid is False
        assert "school hours" in result.errors[0].lower() or "between" in result.errors[0].lower()

    def test_validate_pickup_time_weekend_warning(self):
        """Test weekend pickup generates warning."""
        now = datetime(2025, 11, 3, 10, 0)  # Monday
        scheduled = datetime(2025, 11, 8, 10, 0)  # Saturday
        result = validate_pickup_time(scheduled, reference_time=now)

        assert len(result.warnings) > 0
        assert "weekend" in result.warnings[0].lower()

    def test_validate_child_limit_valid(self):
        """Test valid child count."""
        child_ids = ["child_1", "child_2", "child_3"]
        result = validate_child_limit(child_ids)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_child_limit_empty(self):
        """Test empty child list."""
        result = validate_child_limit([])

        assert result.valid is False
        assert "at least one child" in result.errors[0].lower()

    def test_validate_child_limit_too_many(self):
        """Test too many children."""
        child_ids = [f"child_{i}" for i in range(MAX_CHILDREN_PER_PICKUP + 1)]
        result = validate_child_limit(child_ids)

        assert result.valid is False
        assert "cannot schedule pickup for more than" in result.errors[0].lower()

    def test_validate_child_limit_duplicates(self):
        """Test duplicate child IDs."""
        child_ids = ["child_1", "child_2", "child_1"]
        result = validate_child_limit(child_ids)

        assert result.valid is False
        assert "duplicate" in result.errors[0].lower()

    def test_should_coordinate_cross_school_single(self):
        """Test single school doesn't need coordination."""
        school_ids = ["school_1", "school_1", "school_1"]
        assert should_coordinate_cross_school(school_ids) is False

    def test_should_coordinate_cross_school_multiple(self):
        """Test multiple schools need coordination."""
        school_ids = ["school_1", "school_2", "school_1"]
        assert should_coordinate_cross_school(school_ids) is True


# ═══════════════════════════════════════════════════════════════
# PERMISSION AND AUTHORIZATION TESTS
# ═══════════════════════════════════════════════════════════════


class TestPermissionValidation:
    """Test suite for permission and authorization rules."""

    def test_validate_permissions_valid(self):
        """Test valid permissions."""
        permissions = [Permission.PICKUP.value, Permission.EMERGENCY_CONTACT.value]
        result = validate_permissions(permissions)

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_permissions_invalid(self):
        """Test invalid permission."""
        permissions = ["pickup", "invalid_permission"]
        result = validate_permissions(permissions)

        assert result.valid is False
        assert "invalid permission" in result.errors[0].lower()

    def test_validate_permissions_empty(self):
        """Test empty permissions list."""
        result = validate_permissions([])

        assert result.valid is False
        assert "at least one permission" in result.errors[0].lower()

    def test_has_permission_yes(self):
        """Test delegate has permission."""
        delegate_perms = [Permission.PICKUP.value, Permission.EMERGENCY_CONTACT.value]
        assert has_permission(delegate_perms, Permission.PICKUP.value) is True

    def test_has_permission_no(self):
        """Test delegate doesn't have permission."""
        delegate_perms = [Permission.PICKUP.value]
        assert has_permission(delegate_perms, Permission.MEDICAL_DECISIONS.value) is False

    def test_is_delegate_expired_yes(self):
        """Test expired delegate."""
        created = datetime.now() - timedelta(days=400)
        assert is_delegate_expired(created, expiration_days=365) is True

    def test_is_delegate_expired_no(self):
        """Test active delegate."""
        created = datetime.now() - timedelta(days=30)
        assert is_delegate_expired(created, expiration_days=365) is False

    def test_validate_delegate_authorization_valid(self):
        """Test valid delegate authorization."""
        result = validate_delegate_authorization(
            delegate_email="grandma@example.com",
            child_ids=["child_1", "child_2"],
            permissions=[Permission.PICKUP.value],
            school_ids=["school_1"],
        )

        assert result.valid is True
        assert len(result.errors) == 0

    def test_validate_delegate_authorization_invalid_email(self):
        """Test invalid email."""
        result = validate_delegate_authorization(
            delegate_email="invalid-email",
            child_ids=["child_1"],
            permissions=[Permission.PICKUP.value],
        )

        assert result.valid is False
        assert "email" in result.errors[0].lower()

    def test_validate_delegate_authorization_no_schools_warning(self):
        """Test warning when schools not provided."""
        result = validate_delegate_authorization(
            delegate_email="grandma@example.com",
            child_ids=["child_1"],
            permissions=[Permission.PICKUP.value],
        )

        assert len(result.warnings) > 0
        assert "inferred" in result.warnings[0].lower()

    def test_can_delegate_pickup_child_yes(self):
        """Test delegate can pickup authorized child."""
        delegate_perms = [Permission.PICKUP.value]
        authorized_children = ["child_1", "child_2"]

        assert can_delegate_pickup_child(delegate_perms, authorized_children, "child_1") is True

    def test_can_delegate_pickup_child_no_permission(self):
        """Test delegate without pickup permission."""
        delegate_perms = [Permission.EMERGENCY_CONTACT.value]
        authorized_children = ["child_1", "child_2"]

        assert can_delegate_pickup_child(delegate_perms, authorized_children, "child_1") is False

    def test_can_delegate_pickup_child_not_authorized(self):
        """Test delegate not authorized for child."""
        delegate_perms = [Permission.PICKUP.value]
        authorized_children = ["child_1", "child_2"]

        assert can_delegate_pickup_child(delegate_perms, authorized_children, "child_3") is False


# ═══════════════════════════════════════════════════════════════
# EMERGENCY HANDLING TESTS
# ═══════════════════════════════════════════════════════════════


class TestEmergencyHandling:
    """Test suite for emergency handling rules."""

    def test_validate_emergency_type_valid(self):
        """Test valid emergency types."""
        assert validate_emergency_type(EmergencyType.LATE.value) is True
        assert validate_emergency_type(EmergencyType.ILLNESS.value) is True
        assert validate_emergency_type(EmergencyType.CANCEL.value) is True
        assert validate_emergency_type(EmergencyType.OTHER.value) is True

    def test_validate_emergency_type_invalid(self):
        """Test invalid emergency type."""
        assert validate_emergency_type("invalid_type") is False

    def test_calculate_notification_priority_illness(self):
        """Test highest priority for illness."""
        priority = calculate_notification_priority(EmergencyType.ILLNESS.value)
        assert priority == 1  # Highest priority

    def test_calculate_notification_priority_late(self):
        """Test medium priority for late."""
        priority = calculate_notification_priority(EmergencyType.LATE.value)
        assert priority == 3

    def test_determine_notification_recipients_all(self):
        """Test notify all delegates."""
        delegates = [
            {"id": "d1", "permissions": [Permission.PICKUP.value]},
            {"id": "d2", "permissions": [Permission.EMERGENCY_CONTACT.value]},
        ]

        recipients = determine_notification_recipients(
            emergency_type=EmergencyType.LATE.value,
            delegates=delegates,
            notify_all=True,
        )

        assert len(recipients) == 2

    def test_determine_notification_recipients_emergency_only(self):
        """Test notify only emergency contact delegates."""
        delegates = [
            {"id": "d1", "permissions": [Permission.PICKUP.value]},
            {"id": "d2", "permissions": [Permission.EMERGENCY_CONTACT.value]},
        ]

        recipients = determine_notification_recipients(
            emergency_type=EmergencyType.LATE.value,
            delegates=delegates,
            notify_all=False,
        )

        assert len(recipients) == 1
        assert recipients[0]["id"] == "d2"

    def test_determine_notification_recipients_illness_fallback(self):
        """Test illness emergency notifies all if no emergency contacts."""
        delegates = [
            {"id": "d1", "permissions": [Permission.PICKUP.value]},
            {"id": "d2", "permissions": [Permission.PICKUP.value]},
        ]

        recipients = determine_notification_recipients(
            emergency_type=EmergencyType.ILLNESS.value,
            delegates=delegates,
            notify_all=False,
        )

        # Should fallback to all delegates for critical emergencies
        assert len(recipients) == 2

    def test_should_escalate_emergency_yes(self):
        """Test emergency should be escalated."""
        # Illness emergency, 10 minutes elapsed, no acknowledgments
        should_escalate = should_escalate_emergency(
            emergency_type=EmergencyType.ILLNESS.value,
            time_elapsed_minutes=10,
            acknowledgment_count=0,
        )

        assert should_escalate is True

    def test_should_escalate_emergency_no_time(self):
        """Test emergency shouldn't escalate yet."""
        # Illness emergency, only 3 minutes elapsed
        should_escalate = should_escalate_emergency(
            emergency_type=EmergencyType.ILLNESS.value,
            time_elapsed_minutes=3,
            acknowledgment_count=0,
        )

        assert should_escalate is False

    def test_should_escalate_emergency_acknowledged(self):
        """Test acknowledged emergency doesn't escalate."""
        # Illness emergency, sufficient time but acknowledged
        should_escalate = should_escalate_emergency(
            emergency_type=EmergencyType.ILLNESS.value,
            time_elapsed_minutes=10,
            acknowledgment_count=1,
        )

        assert should_escalate is False


# ═══════════════════════════════════════════════════════════════
# MULTI-SCHOOL COORDINATION TESTS
# ═══════════════════════════════════════════════════════════════


class TestMultiSchoolCoordination:
    """Test suite for multi-school coordination logic."""

    def test_group_children_by_school(self):
        """Test grouping children by school."""
        children = [
            {"id": "child_1", "school_id": "school_1"},
            {"id": "child_2", "school_id": "school_2"},
            {"id": "child_3", "school_id": "school_1"},
        ]

        groups = group_children_by_school(children)

        assert len(groups) == 2
        assert "school_1" in groups
        assert "school_2" in groups
        assert len(groups["school_1"]) == 2
        assert len(groups["school_2"]) == 1

    def test_calculate_coordination_sequence(self):
        """Test coordination sequence calculation."""
        schools = [
            {"id": "school_3"},
            {"id": "school_1"},
            {"id": "school_2"},
        ]

        sequence = calculate_coordination_sequence(
            schools,
            pickup_time=datetime.now(),
        )

        # Should be sorted
        assert sequence == ["school_1", "school_2", "school_3"]

    def test_requires_additional_coordination_time_single_school(self):
        """Test single school doesn't need extra time."""
        needs_time, minutes = requires_additional_coordination_time(
            school_count=1,
            base_pickup_time=datetime.now(),
        )

        assert needs_time is False
        assert minutes == 0

    def test_requires_additional_coordination_time_multiple_schools(self):
        """Test multiple schools need extra time."""
        needs_time, minutes = requires_additional_coordination_time(
            school_count=3,
            base_pickup_time=datetime.now(),
        )

        assert needs_time is True
        assert minutes == 20  # (3-1) * 10 minutes


# ═══════════════════════════════════════════════════════════════
# STATE MANAGEMENT TESTS
# ═══════════════════════════════════════════════════════════════


class TestStateManagement:
    """Test suite for state management functions."""

    def test_get_next_pickup_state_pending_to_confirmed(self):
        """Test transition from pending to confirmed."""
        next_state = get_next_pickup_state(PickupStatus.PENDING.value)
        assert next_state == PickupStatus.CONFIRMED.value

    def test_get_next_pickup_state_confirmed_to_in_progress(self):
        """Test transition from confirmed to in progress."""
        next_state = get_next_pickup_state(PickupStatus.CONFIRMED.value)
        assert next_state == PickupStatus.IN_PROGRESS.value

    def test_get_next_pickup_state_in_progress_to_completed(self):
        """Test transition from in progress to completed."""
        next_state = get_next_pickup_state(PickupStatus.IN_PROGRESS.value)
        assert next_state == PickupStatus.COMPLETED.value

    def test_get_next_pickup_state_invalid(self):
        """Test invalid state transition."""
        with pytest.raises(ValueError, match="No valid transition"):
            get_next_pickup_state(PickupStatus.COMPLETED.value)

    def test_can_cancel_pickup_yes(self):
        """Test pickup can be cancelled."""
        scheduled = datetime.now() + timedelta(hours=2)
        can_cancel, reason = can_cancel_pickup(PickupStatus.PENDING.value, scheduled)

        assert can_cancel is True
        assert "can be cancelled" in reason.lower()

    def test_can_cancel_pickup_completed(self):
        """Test cannot cancel completed pickup."""
        scheduled = datetime.now() + timedelta(hours=2)
        can_cancel, reason = can_cancel_pickup(PickupStatus.COMPLETED.value, scheduled)

        assert can_cancel is False
        assert "completed" in reason.lower()

    def test_can_cancel_pickup_in_progress(self):
        """Test cannot cancel in-progress pickup."""
        scheduled = datetime.now() + timedelta(hours=2)
        can_cancel, reason = can_cancel_pickup(PickupStatus.IN_PROGRESS.value, scheduled)

        assert can_cancel is False
        assert "in progress" in reason.lower()

    def test_can_cancel_pickup_too_late(self):
        """Test cannot cancel too close to pickup time."""
        scheduled = datetime.now() + timedelta(minutes=10)
        can_cancel, reason = can_cancel_pickup(PickupStatus.PENDING.value, scheduled)

        assert can_cancel is False
        assert "within" in reason.lower()

    def test_calculate_pickup_metrics_empty(self):
        """Test metrics for empty pickup list."""
        metrics = calculate_pickup_metrics([])

        assert metrics['total'] == 0
        assert metrics['on_time_percentage'] == 100.0

    def test_calculate_pickup_metrics_mixed(self):
        """Test metrics for mixed pickups."""
        pickups = [
            {"status": PickupStatus.COMPLETED.value, "delay_minutes": 0},
            {"status": PickupStatus.COMPLETED.value, "delay_minutes": 10},
            {"status": PickupStatus.PENDING.value, "delay_minutes": 0},
            {"status": PickupStatus.COMPLETED.value, "delay_minutes": 3},
        ]

        metrics = calculate_pickup_metrics(pickups)

        assert metrics['total'] == 4
        assert metrics['by_status'][PickupStatus.COMPLETED.value] == 3
        assert metrics['by_status'][PickupStatus.PENDING.value] == 1
        assert metrics['average_delay_minutes'] == 3.25  # (0+10+0+3)/4
        assert metrics['on_time_percentage'] == 75.0  # 3 out of 4 within 5 min grace


# ═══════════════════════════════════════════════════════════════
# INTEGRATION TESTS (combining multiple functions)
# ═══════════════════════════════════════════════════════════════


class TestIntegrationScenarios:
    """Integration tests combining multiple business logic functions."""

    def test_complete_pickup_validation_flow(self):
        """Test complete pickup validation workflow."""
        # Setup
        now = datetime(2025, 11, 4, 10, 0)  # Monday 10am
        scheduled = datetime(2025, 11, 4, 15, 30)  # Same day 3:30pm
        child_ids = ["child_1", "child_2"]

        # Validate time
        time_result = validate_pickup_time(scheduled, reference_time=now)
        assert time_result.valid is True

        # Validate children
        child_result = validate_child_limit(child_ids)
        assert child_result.valid is True

        # Check school hours
        assert is_within_school_hours(scheduled) is True

        # Calculate ETA
        eta = calculate_eta_minutes(scheduled, current_time=now)
        assert eta == 330  # 5.5 hours = 330 minutes

    def test_cross_school_pickup_workflow(self):
        """Test multi-school pickup coordination workflow."""
        children = [
            {"id": "child_1", "school_id": "school_1"},
            {"id": "child_2", "school_id": "school_2"},
            {"id": "child_3", "school_id": "school_1"},
        ]

        # Group by school
        groups = group_children_by_school(children)
        assert len(groups) == 2

        # Check if coordination needed
        school_ids = list(groups.keys())
        assert should_coordinate_cross_school(school_ids) is True

        # Calculate additional time
        needs_time, extra_minutes = requires_additional_coordination_time(
            len(school_ids),
            datetime.now(),
        )
        assert needs_time is True
        assert extra_minutes > 0

    def test_emergency_notification_workflow(self):
        """Test emergency notification workflow."""
        delegates = [
            {"id": "d1", "permissions": [Permission.PICKUP.value]},
            {"id": "d2", "permissions": [Permission.EMERGENCY_CONTACT.value]},
            {"id": "d3", "permissions": [Permission.PICKUP.value, Permission.EMERGENCY_CONTACT.value]},
        ]

        # Validate emergency type
        emergency_type = EmergencyType.ILLNESS.value
        assert validate_emergency_type(emergency_type) is True

        # Calculate priority
        priority = calculate_notification_priority(emergency_type)
        assert priority == 1  # Highest

        # Determine recipients
        recipients = determine_notification_recipients(
            emergency_type,
            delegates,
            notify_all=False,
        )
        # Should notify emergency contacts (d2, d3) or all for illness
        assert len(recipients) >= 2

        # Check if should escalate
        should_escalate = should_escalate_emergency(
            emergency_type,
            time_elapsed_minutes=10,
            acknowledgment_count=0,
        )
        assert should_escalate is True


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
