"""Business logic module for AllôBye - Pure business rules without infrastructure dependencies.

This module contains all core business rules for:
- Pickup scheduling and time windows
- Delegate authorization and permissions
- Emergency notification cascading
- Multi-school coordination
- State management and validation

All functions in this module are:
- Pure (no side effects)
- Framework-agnostic (no FastMCP, Supabase, or external dependencies)
- Testable (clear inputs and outputs)
- Well-documented with type hints
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from enum import Enum
from typing import List, Optional, Dict, Any, Tuple, Set


# ═══════════════════════════════════════════════════════════════
# ENUMS AND CONSTANTS
# ═══════════════════════════════════════════════════════════════


class PickupStatus(Enum):
    """Possible states for a pickup request."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DELAYED = "delayed"


class EmergencyType(Enum):
    """Types of emergencies that can be declared."""
    LATE = "late"
    ILLNESS = "illness"
    CANCEL = "cancel"
    OTHER = "other"


class Permission(Enum):
    """Permission types for delegates."""
    PICKUP = "pickup"
    EMERGENCY_CONTACT = "emergency_contact"
    MEDICAL_DECISIONS = "medical_decisions"


class TimeWindow(Enum):
    """Time window options for pickup queries."""
    CURRENT = "current"  # Next 30 minutes
    TODAY = "today"      # Rest of the day
    CUSTOM = "custom"    # Custom range


# Business rule constants
CURRENT_WINDOW_MINUTES = 30
SCHOOL_START_HOUR = 7
SCHOOL_END_HOUR = 18
MIN_ADVANCE_NOTICE_MINUTES = 15
MAX_FUTURE_DAYS = 7
MAX_CHILDREN_PER_PICKUP = 10
DELEGATE_EXPIRATION_DAYS = 365


# ═══════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class TimeRange:
    """Represents a time range for pickup queries."""
    start: datetime
    end: datetime

    def contains(self, dt: datetime) -> bool:
        """Check if datetime is within this range."""
        return self.start <= dt <= self.end

    def duration_minutes(self) -> int:
        """Get duration in minutes."""
        return int((self.end - self.start).total_seconds() / 60)


@dataclass(frozen=True)
class PickupValidationResult:
    """Result of pickup validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]

    @classmethod
    def success(cls) -> PickupValidationResult:
        """Create a successful validation result."""
        return cls(valid=True, errors=[], warnings=[])

    @classmethod
    def failure(cls, errors: List[str], warnings: Optional[List[str]] = None) -> PickupValidationResult:
        """Create a failed validation result."""
        return cls(valid=False, errors=errors, warnings=warnings or [])


@dataclass(frozen=True)
class DelegateValidationResult:
    """Result of delegate authorization validation."""
    valid: bool
    errors: List[str]
    warnings: List[str]
    inferred_schools: List[str]


# ═══════════════════════════════════════════════════════════════
# TIME WINDOW FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def calculate_time_window(
    window_type: str,
    reference_time: Optional[datetime] = None,
    custom_start: Optional[datetime] = None,
    custom_end: Optional[datetime] = None,
) -> TimeRange:
    """Calculate time range based on window type.

    Args:
        window_type: Type of window (current, today, custom)
        reference_time: Reference time (defaults to now)
        custom_start: Start time for custom window
        custom_end: End time for custom window

    Returns:
        TimeRange object with calculated start and end times

    Raises:
        ValueError: If custom window is specified without start/end times
    """
    now = reference_time or datetime.now()

    if window_type == TimeWindow.CURRENT.value:
        return TimeRange(
            start=now,
            end=now + timedelta(minutes=CURRENT_WINDOW_MINUTES)
        )
    elif window_type == TimeWindow.TODAY.value:
        return TimeRange(
            start=now.replace(hour=0, minute=0, second=0, microsecond=0),
            end=now.replace(hour=23, minute=59, second=59, microsecond=999999)
        )
    elif window_type == TimeWindow.CUSTOM.value:
        if not custom_start or not custom_end:
            raise ValueError("Custom window requires both start and end times")
        return TimeRange(start=custom_start, end=custom_end)
    else:
        # Default to next 24 hours
        return TimeRange(start=now, end=now + timedelta(hours=24))


def is_within_school_hours(dt: datetime) -> bool:
    """Check if datetime is within school operating hours.

    Args:
        dt: Datetime to check

    Returns:
        True if within school hours, False otherwise
    """
    return SCHOOL_START_HOUR <= dt.hour < SCHOOL_END_HOUR


def calculate_eta_minutes(scheduled_time: datetime, current_time: Optional[datetime] = None) -> int:
    """Calculate estimated time of arrival in minutes.

    Args:
        scheduled_time: Scheduled pickup time
        current_time: Current time (defaults to now)

    Returns:
        Minutes until pickup (negative if overdue)
    """
    now = current_time or datetime.now()
    delta = scheduled_time - now
    return int(delta.total_seconds() / 60)


def calculate_delay_minutes(scheduled_time: datetime, actual_time: datetime) -> int:
    """Calculate delay in minutes between scheduled and actual time.

    Args:
        scheduled_time: Scheduled pickup time
        actual_time: Actual pickup time

    Returns:
        Delay in minutes (positive if late, negative if early)
    """
    delta = actual_time - scheduled_time
    return int(delta.total_seconds() / 60)


def is_pickup_overdue(scheduled_time: datetime, grace_period_minutes: int = 15) -> bool:
    """Check if a pickup is overdue considering grace period.

    Args:
        scheduled_time: Scheduled pickup time
        grace_period_minutes: Grace period in minutes

    Returns:
        True if pickup is overdue, False otherwise
    """
    now = datetime.now()
    overdue_threshold = scheduled_time + timedelta(minutes=grace_period_minutes)
    return now > overdue_threshold


# ═══════════════════════════════════════════════════════════════
# PICKUP VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def validate_pickup_time(scheduled_time: datetime, reference_time: Optional[datetime] = None) -> PickupValidationResult:
    """Validate pickup scheduling time against business rules.

    Business rules:
    - Must be within school hours (7am-6pm)
    - Must have minimum advance notice (15 minutes)
    - Cannot be more than 7 days in the future
    - Cannot be in the past

    Args:
        scheduled_time: Requested pickup time
        reference_time: Reference time (defaults to now)

    Returns:
        PickupValidationResult with validation status and messages
    """
    now = reference_time or datetime.now()
    errors = []
    warnings = []

    # Check if in the past
    if scheduled_time < now:
        errors.append("Pickup time cannot be in the past")

    # Check minimum advance notice
    min_notice_time = now + timedelta(minutes=MIN_ADVANCE_NOTICE_MINUTES)
    if scheduled_time < min_notice_time:
        errors.append(f"Pickup requires at least {MIN_ADVANCE_NOTICE_MINUTES} minutes advance notice")

    # Check maximum future date
    max_future_time = now + timedelta(days=MAX_FUTURE_DAYS)
    if scheduled_time > max_future_time:
        errors.append(f"Cannot schedule pickups more than {MAX_FUTURE_DAYS} days in advance")

    # Check school hours
    if not is_within_school_hours(scheduled_time):
        errors.append(f"Pickup must be between {SCHOOL_START_HOUR}:00 and {SCHOOL_END_HOUR}:00")

    # Check if weekend
    if scheduled_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
        warnings.append("Pickup scheduled for weekend - please verify school is open")

    if errors:
        return PickupValidationResult.failure(errors, warnings)
    return PickupValidationResult(valid=True, errors=[], warnings=warnings)


def validate_child_limit(child_ids: List[str]) -> PickupValidationResult:
    """Validate number of children in a pickup request.

    Args:
        child_ids: List of child IDs

    Returns:
        PickupValidationResult with validation status
    """
    errors = []

    if not child_ids:
        errors.append("At least one child must be specified")

    if len(child_ids) > MAX_CHILDREN_PER_PICKUP:
        errors.append(f"Cannot schedule pickup for more than {MAX_CHILDREN_PER_PICKUP} children at once")

    # Check for duplicates
    if len(child_ids) != len(set(child_ids)):
        errors.append("Duplicate child IDs found in request")

    if errors:
        return PickupValidationResult.failure(errors)
    return PickupValidationResult.success()


def should_coordinate_cross_school(school_ids: List[str]) -> bool:
    """Determine if cross-school coordination is needed.

    Args:
        school_ids: List of unique school IDs

    Returns:
        True if multiple schools are involved, False otherwise
    """
    return len(set(school_ids)) > 1


# ═══════════════════════════════════════════════════════════════
# PERMISSION AND AUTHORIZATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def validate_permissions(permissions: List[str]) -> PickupValidationResult:
    """Validate permission list against allowed values.

    Args:
        permissions: List of permission strings

    Returns:
        PickupValidationResult with validation status
    """
    errors = []
    valid_permissions = {p.value for p in Permission}

    for perm in permissions:
        if perm not in valid_permissions:
            errors.append(f"Invalid permission: {perm}. Must be one of {valid_permissions}")

    if not permissions:
        errors.append("At least one permission must be specified")

    if errors:
        return PickupValidationResult.failure(errors)
    return PickupValidationResult.success()


def has_permission(delegate_permissions: List[str], required_permission: str) -> bool:
    """Check if delegate has required permission.

    Args:
        delegate_permissions: List of delegate's permissions
        required_permission: Permission to check for

    Returns:
        True if delegate has permission, False otherwise
    """
    return required_permission in delegate_permissions


def is_delegate_expired(created_at: datetime, expiration_days: int = DELEGATE_EXPIRATION_DAYS) -> bool:
    """Check if delegate authorization has expired.

    Args:
        created_at: When delegate was authorized
        expiration_days: Days until expiration

    Returns:
        True if expired, False otherwise
    """
    now = datetime.now()
    expiration_date = created_at + timedelta(days=expiration_days)
    return now > expiration_date


def validate_delegate_authorization(
    delegate_email: str,
    child_ids: List[str],
    permissions: List[str],
    school_ids: Optional[List[str]] = None,
) -> DelegateValidationResult:
    """Validate delegate authorization request.

    Args:
        delegate_email: Email of the delegate
        child_ids: List of child IDs
        permissions: List of permissions to grant
        school_ids: Optional list of school IDs

    Returns:
        DelegateValidationResult with validation status
    """
    errors = []
    warnings = []

    # Validate email format (basic check)
    if not delegate_email or '@' not in delegate_email:
        errors.append("Valid email address required for delegate")

    # Validate child IDs
    child_result = validate_child_limit(child_ids)
    if not child_result.valid:
        errors.extend(child_result.errors)

    # Validate permissions
    perm_result = validate_permissions(permissions)
    if not perm_result.valid:
        errors.extend(perm_result.errors)

    # If schools not provided, they will be inferred from children
    inferred_schools = school_ids or []

    if not inferred_schools:
        warnings.append("School IDs will be inferred from children")

    if errors:
        return DelegateValidationResult(
            valid=False,
            errors=errors,
            warnings=warnings,
            inferred_schools=inferred_schools
        )

    return DelegateValidationResult(
        valid=True,
        errors=[],
        warnings=warnings,
        inferred_schools=inferred_schools
    )


def can_delegate_pickup_child(
    delegate_permissions: List[str],
    authorized_child_ids: List[str],
    requested_child_id: str,
) -> bool:
    """Check if delegate can pickup a specific child.

    Args:
        delegate_permissions: Delegate's permissions
        authorized_child_ids: Children delegate is authorized for
        requested_child_id: Child being requested for pickup

    Returns:
        True if delegate can pickup child, False otherwise
    """
    return (
        has_permission(delegate_permissions, Permission.PICKUP.value)
        and requested_child_id in authorized_child_ids
    )


# ═══════════════════════════════════════════════════════════════
# EMERGENCY HANDLING FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def validate_emergency_type(emergency_type: str) -> bool:
    """Validate emergency type against allowed values.

    Args:
        emergency_type: Emergency type string

    Returns:
        True if valid, False otherwise
    """
    valid_types = {e.value for e in EmergencyType}
    return emergency_type in valid_types


def calculate_notification_priority(emergency_type: str) -> int:
    """Calculate notification priority based on emergency type.

    Args:
        emergency_type: Type of emergency

    Returns:
        Priority level (1=highest, 5=lowest)
    """
    priority_map = {
        EmergencyType.ILLNESS.value: 1,      # Highest priority
        EmergencyType.CANCEL.value: 2,
        EmergencyType.LATE.value: 3,
        EmergencyType.OTHER.value: 4,        # Lowest priority
    }
    return priority_map.get(emergency_type, 5)


def determine_notification_recipients(
    emergency_type: str,
    delegates: List[Dict[str, Any]],
    notify_all: bool = True,
) -> List[Dict[str, Any]]:
    """Determine which delegates should be notified of emergency.

    Args:
        emergency_type: Type of emergency
        delegates: List of authorized delegates
        notify_all: Whether to notify all delegates

    Returns:
        List of delegates to notify
    """
    if not delegates:
        return []

    if notify_all:
        return delegates

    # Filter delegates with emergency contact permission
    emergency_delegates = [
        d for d in delegates
        if Permission.EMERGENCY_CONTACT.value in d.get('permissions', [])
    ]

    # If no emergency contacts, fall back to all delegates for critical emergencies
    if not emergency_delegates and emergency_type in [EmergencyType.ILLNESS.value]:
        return delegates

    return emergency_delegates or delegates


def should_escalate_emergency(
    emergency_type: str,
    time_elapsed_minutes: int,
    acknowledgment_count: int,
) -> bool:
    """Determine if emergency should be escalated.

    Args:
        emergency_type: Type of emergency
        time_elapsed_minutes: Minutes since emergency declared
        acknowledgment_count: Number of delegates who acknowledged

    Returns:
        True if should escalate, False otherwise
    """
    # Escalation thresholds
    escalation_rules = {
        EmergencyType.ILLNESS.value: (5, 1),   # 5 min, need 1 ack
        EmergencyType.CANCEL.value: (10, 1),   # 10 min, need 1 ack
        EmergencyType.LATE.value: (15, 0),     # 15 min, no ack needed
        EmergencyType.OTHER.value: (20, 1),    # 20 min, need 1 ack
    }

    threshold_minutes, min_acks = escalation_rules.get(
        emergency_type,
        (15, 1)  # Default
    )

    return (
        time_elapsed_minutes >= threshold_minutes
        and acknowledgment_count < min_acks
    )


# ═══════════════════════════════════════════════════════════════
# MULTI-SCHOOL COORDINATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def group_children_by_school(
    children_data: List[Dict[str, Any]]
) -> Dict[str, List[str]]:
    """Group child IDs by their school.

    Args:
        children_data: List of child data with school_id

    Returns:
        Dictionary mapping school_id to list of child_ids
    """
    school_groups: Dict[str, List[str]] = {}

    for child in children_data:
        school_id = child.get('school_id')
        child_id = child.get('id')

        if school_id and child_id:
            if school_id not in school_groups:
                school_groups[school_id] = []
            school_groups[school_id].append(child_id)

    return school_groups


def calculate_coordination_sequence(
    schools_data: List[Dict[str, Any]],
    pickup_time: datetime,
) -> List[str]:
    """Calculate optimal sequence for multi-school pickup coordination.

    Args:
        schools_data: List of school data with location info
        pickup_time: Scheduled pickup time

    Returns:
        List of school IDs in optimal coordination sequence
    """
    # Simple implementation: prioritize by distance or alphabetically
    # In production, this could use actual routing/distance calculations
    return sorted([s['id'] for s in schools_data])


def requires_additional_coordination_time(
    school_count: int,
    base_pickup_time: datetime,
) -> Tuple[bool, int]:
    """Determine if multi-school pickup needs additional coordination time.

    Args:
        school_count: Number of schools involved
        base_pickup_time: Base pickup time

    Returns:
        Tuple of (needs_extra_time, additional_minutes)
    """
    if school_count <= 1:
        return (False, 0)

    # Add 10 minutes per additional school for coordination
    additional_minutes = (school_count - 1) * 10

    return (True, additional_minutes)


# ═══════════════════════════════════════════════════════════════
# STATE MANAGEMENT FUNCTIONS
# ═══════════════════════════════════════════════════════════════


def get_next_pickup_state(current_state: str) -> str:
    """Get the next valid state for a pickup.

    Args:
        current_state: Current pickup status

    Returns:
        Next valid state

    Raises:
        ValueError: If current state is terminal
    """
    state_transitions = {
        PickupStatus.PENDING.value: PickupStatus.CONFIRMED.value,
        PickupStatus.CONFIRMED.value: PickupStatus.IN_PROGRESS.value,
        PickupStatus.IN_PROGRESS.value: PickupStatus.COMPLETED.value,
        PickupStatus.DELAYED.value: PickupStatus.IN_PROGRESS.value,
    }

    next_state = state_transitions.get(current_state)

    if not next_state:
        raise ValueError(f"No valid transition from state: {current_state}")

    return next_state


def can_cancel_pickup(current_state: str, scheduled_time: datetime) -> Tuple[bool, str]:
    """Determine if a pickup can be cancelled.

    Args:
        current_state: Current pickup status
        scheduled_time: Scheduled pickup time

    Returns:
        Tuple of (can_cancel, reason)
    """
    # Cannot cancel completed pickups
    if current_state == PickupStatus.COMPLETED.value:
        return (False, "Cannot cancel completed pickup")

    # Cannot cancel if already in progress
    if current_state == PickupStatus.IN_PROGRESS.value:
        return (False, "Cannot cancel pickup already in progress")

    # Check if too close to pickup time
    now = datetime.now()
    time_until_pickup = (scheduled_time - now).total_seconds() / 60

    if time_until_pickup < MIN_ADVANCE_NOTICE_MINUTES:
        return (False, f"Cannot cancel within {MIN_ADVANCE_NOTICE_MINUTES} minutes of pickup")

    return (True, "Pickup can be cancelled")


def calculate_pickup_metrics(pickups: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate aggregate metrics for a list of pickups.

    Args:
        pickups: List of pickup data

    Returns:
        Dictionary with calculated metrics
    """
    total = len(pickups)
    if total == 0:
        return {
            'total': 0,
            'by_status': {},
            'average_delay_minutes': 0,
            'on_time_percentage': 100.0,
        }

    # Count by status
    status_counts: Dict[str, int] = {}
    total_delay = 0
    on_time_count = 0

    for pickup in pickups:
        status = pickup.get('status', PickupStatus.PENDING.value)
        status_counts[status] = status_counts.get(status, 0) + 1

        # Calculate delays
        delay = pickup.get('delay_minutes', 0)
        total_delay += delay

        if delay <= 5:  # 5 minute grace period
            on_time_count += 1

    return {
        'total': total,
        'by_status': status_counts,
        'average_delay_minutes': total_delay / total if total > 0 else 0,
        'on_time_percentage': (on_time_count / total * 100) if total > 0 else 100.0,
    }
