# Critical Test Cases - AllôBye

**Date**: 2025-11-04
**Focus**: Tests prioritaires P0 à écrire IMMÉDIATEMENT
**Objectif**: Couvrir les chemins critiques en 1 semaine

---

## Executive Summary

### Tests Critiques Identifiés

**Total tests P0**: **60 tests critiques**

| Catégorie | Tests P0 | Effort (jours) | Business Impact |
|-----------|----------|----------------|-----------------|
| **Security & RLS** | 24 | 2.5 | 🔥 Data breach prevention |
| **Authentication** | 12 | 1.5 | 🔥 Accès non autorisé |
| **Pickup Scheduling** | 10 | 1.5 | 🔥 Business logic core |
| **Emergency System** | 8 | 1 | 🔥 Real-time safety |
| **Database Triggers** | 6 | 0.5 | 🔥 Data integrity |

**Effort total**: **7 jours** (peut être parallélisé sur 2-3 devs → **3-4 jours calendaires**)

---

## Priorité P0 - Semaine 1 (Critiques)

### 1. Security & RLS Tests (24 tests)

**Criticité**: 🔥🔥🔥 MAXIMALE
**Impact**: Data breach, privacy violations
**Effort**: 2.5 jours

---

#### Test Case #1: RLS - Parent View Own Children

**File**: `tests/database/test_rls_parents.py`

```python
import pytest
from fixtures import create_test_parent, create_test_child, parent_supabase_client

async def test_rls_parent_can_view_own_children(parent_supabase_client, test_parent, test_child):
    """
    CRITICAL: Parent must be able to view ONLY their own children.

    Given: Parent P1 with child C1 (parent_email = P1.email)
    When: P1 queries children table
    Then: P1 can see C1

    Business Impact: Core functionality - parents manage their children
    Security Impact: CRITICAL - must enforce ownership
    """
    response = parent_supabase_client.table("children") \
        .select("*") \
        .eq("id", test_child["id"]) \
        .execute()

    assert len(response.data) == 1
    assert response.data[0]["id"] == test_child["id"]
    assert response.data[0]["parent_email"] == test_parent["user"]["email"]


async def test_rls_parent_cannot_view_other_children(parent_supabase_client):
    """
    CRITICAL: Parent must NOT be able to view other parents' children.

    Given: Parent P1, Parent P2 with child C2
    When: P1 queries children table for C2
    Then: Query returns 0 rows (RLS filters out)

    Business Impact: CRITICAL - prevents data breach
    Security Impact: CRITICAL - privacy violation if fails
    """
    # Create other parent and child
    other_parent = await create_test_parent(email="other@test.com")
    other_child = await create_test_child(parent_email=other_parent["user"]["email"])

    # Try to query as current parent (should be filtered by RLS)
    response = parent_supabase_client.table("children") \
        .select("*") \
        .eq("id", other_child["id"]) \
        .execute()

    # CRITICAL: Must return 0 rows
    assert len(response.data) == 0, "RLS FAILED: Parent can see other parent's children!"
```

**Why Critical**:
- ✗ **WITHOUT THIS TEST**: Parent peut voir enfants d'autres parents → **MAJOR DATA BREACH**
- ✓ **WITH THIS TEST**: RLS policy validée → Privacy garantie

---

#### Test Case #2: RLS - Delegate View Assigned Pickups Only

**File**: `tests/database/test_rls_delegates.py`

```python
async def test_rls_delegate_can_view_assigned_pickups(delegate_supabase_client, test_delegate):
    """
    CRITICAL: Delegate can view pickups where they are pickup_person.

    Given: Delegate D1, Pickup P1 with pickup_person_id = D1.id
    When: D1 queries pickups table
    Then: D1 can see P1

    Business Impact: Delegates need to see their assigned pickups
    Security Impact: CRITICAL - must restrict to assigned only
    """
    pickup = await create_test_pickup(pickup_person_id=test_delegate["id"])

    response = delegate_supabase_client.table("pickups") \
        .select("*") \
        .eq("pickup_person_id", test_delegate["id"]) \
        .execute()

    assert len(response.data) >= 1
    assert any(p["id"] == pickup["id"] for p in response.data)


async def test_rls_delegate_cannot_view_other_pickups(delegate_supabase_client):
    """
    CRITICAL: Delegate must NOT see pickups assigned to others.

    Given: Delegate D1, Delegate D2, Pickup P2 assigned to D2
    When: D1 queries pickups for P2
    Then: Query returns 0 rows

    Business Impact: CRITICAL - prevents unauthorized pickup access
    Security Impact: CRITICAL - delegate could show up for wrong pickup
    """
    other_delegate = await create_test_delegate("other@test.com")
    other_pickup = await create_test_pickup(pickup_person_id=other_delegate["id"])

    response = delegate_supabase_client.table("pickups") \
        .select("*") \
        .eq("id", other_pickup["id"]) \
        .execute()

    assert len(response.data) == 0, "RLS FAILED: Delegate sees other's pickups!"
```

**Why Critical**:
- ✗ **WITHOUT**: Delegate voit tous les pickups → Peut se présenter pour enfant non autorisé
- ✓ **WITH**: Sécurité physique des enfants garantie

---

#### Test Case #3: RLS - School Staff Isolation

**File**: `tests/database/test_rls_school_staff.py`

```python
async def test_rls_staff_can_view_school_children(staff_supabase_client, test_school):
    """
    CRITICAL: School staff can view children at THEIR school only.

    Given: Staff S1 at School SCH1, Child C1 at SCH1
    When: S1 queries children at SCH1
    Then: S1 can see C1

    Business Impact: Staff need to see their school's children
    Security Impact: CRITICAL - must isolate schools
    """
    child = await create_test_child(school_id=test_school["id"])

    response = staff_supabase_client.table("children") \
        .select("*") \
        .eq("school_id", test_school["id"]) \
        .execute()

    assert any(c["id"] == child["id"] for c in response.data)


async def test_rls_staff_cannot_view_other_school_children(staff_supabase_client):
    """
    CRITICAL: School staff must NOT see children at other schools.

    Given: Staff S1 at School SCH1, School SCH2, Child C2 at SCH2
    When: S1 queries children at SCH2
    Then: Query returns 0 rows

    Business Impact: CRITICAL - multi-tenant data isolation
    Security Impact: CRITICAL - privacy violation, compliance issue
    """
    other_school = await create_test_school("Other School")
    other_child = await create_test_child(school_id=other_school["id"])

    response = staff_supabase_client.table("children") \
        .select("*") \
        .eq("school_id", other_school["id"]) \
        .execute()

    assert len(response.data) == 0, "RLS FAILED: Staff sees other school's data!"
```

**Why Critical**:
- ✗ **WITHOUT**: Staff d'une école voit données d'autres écoles → **COMPLIANCE VIOLATION** (GDPR)
- ✓ **WITH**: Multi-tenant isolation garantie

---

#### Test Case #4: RLS - JWT Tampering Protection

**File**: `tests/database/test_rls_jwt_security.py`

```python
async def test_rls_rejects_tampered_jwt():
    """
    CRITICAL: RLS must reject tampered JWT claims.

    Given: User U1 with JWT containing email="user@test.com"
    When: Attacker tampers JWT to change email="admin@test.com"
    Then: RLS rejects the request (signature validation fails)

    Business Impact: CRITICAL - prevents privilege escalation
    Security Impact: CRITICAL - JWT tampering = full system compromise
    """
    # Get valid JWT
    user = await create_test_user("user@test.com")
    valid_token = user["session"]["access_token"]

    # Tamper with JWT (change email claim)
    # In real attack: decode, modify, re-encode WITHOUT signature
    tampered_token = tamper_jwt_email(valid_token, new_email="admin@test.com")

    # Try to use tampered token
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase.auth.set_session(tampered_token, "")

    with pytest.raises(AuthApiError, match="Invalid token"):
        response = supabase.table("children").select("*").execute()


async def test_rls_enforces_jwt_expiration():
    """
    CRITICAL: RLS must reject expired JWT tokens.

    Given: User with expired JWT (issued 2 hours ago, expires after 1 hour)
    When: User queries with expired token
    Then: Request rejected with "Token expired" error

    Business Impact: CRITICAL - session hijacking prevention
    Security Impact: CRITICAL - expired tokens = persistent access
    """
    # Create token that expired 1 hour ago
    expired_token = create_expired_jwt(expired_minutes_ago=60)

    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    supabase.auth.set_session(expired_token, "")

    with pytest.raises(AuthApiError, match="Token expired|Expired"):
        response = supabase.table("pickups").select("*").execute()
```

**Why Critical**:
- ✗ **WITHOUT**: Attacker peut modifier JWT → Accès admin
- ✓ **WITH**: JWT integrity validée → System secure

---

**RLS Tests Summary**:

| Test | Priority | Impact | Lines |
|------|----------|--------|-------|
| Parent view own children | P0 | 🔥🔥🔥 | 15 |
| Parent cannot view others | P0 | 🔥🔥🔥 | 18 |
| Delegate view assigned | P0 | 🔥🔥🔥 | 15 |
| Delegate cannot view others | P0 | 🔥🔥🔥 | 16 |
| Staff view school children | P0 | 🔥🔥🔥 | 14 |
| Staff cannot view other schools | P0 | 🔥🔥🔥 | 16 |
| JWT tampering protection | P0 | 🔥🔥🔥 | 20 |
| JWT expiration enforcement | P0 | 🔥🔥🔥 | 18 |
| ... (16 more RLS tests) | P0 | 🔥🔥 | ~200 |

**Total RLS tests**: **24 tests** | **~350 lines** | **2.5 jours**

---

### 2. Authentication Tests (12 tests)

**Criticité**: 🔥🔥🔥 MAXIMALE
**Impact**: Unauthorized access, account takeover
**Effort**: 1.5 jours

---

#### Test Case #5: Signup - Email Already Exists

**File**: `tests/auth/test_signup.py`

```python
async def test_signup_with_duplicate_email_fails():
    """
    CRITICAL: Signup must reject duplicate emails.

    Given: User U1 already exists with email="existing@test.com"
    When: New user tries to signup with same email
    Then: Raise UserAlreadyExistsError

    Business Impact: CRITICAL - prevents account conflicts
    Security Impact: HIGH - account takeover vector
    """
    # First signup
    await signup_user(
        email="existing@test.com",
        password="FirstPass123!",
        name="First User"
    )

    # Second signup with same email
    with pytest.raises(UserAlreadyExistsError):
        await signup_user(
            email="existing@test.com",
            password="SecondPass123!",
            name="Second User"
        )
```

**Why Critical**:
- ✗ **WITHOUT**: Utilisateur peut écraser compte existant
- ✓ **WITH**: Comptes protégés

---

#### Test Case #6: Login - Brute Force Protection

**File**: `tests/auth/test_login_security.py`

```python
@pytest.mark.parametrize("attempt", range(10))
async def test_login_rate_limiting_after_failed_attempts(attempt):
    """
    CRITICAL: Login must implement rate limiting after failed attempts.

    Given: User account exists
    When: 10 consecutive failed login attempts in 1 minute
    Then: 11th attempt returns RateLimitExceededError

    Business Impact: CRITICAL - prevents brute force attacks
    Security Impact: CRITICAL - weak passwords can be cracked
    """
    # Create user
    await signup_user(email="victim@test.com", password="CorrectPass123!")

    # Try 10 wrong passwords
    for i in range(10):
        with pytest.raises(InvalidCredentialsError):
            await login_user(
                email="victim@test.com",
                password=f"WrongPass{i}"
            )

    # 11th attempt should be rate-limited
    with pytest.raises(RateLimitExceededError, match="Too many attempts"):
        await login_user(
            email="victim@test.com",
            password="WrongPass11"
        )


async def test_login_rate_limit_resets_after_cooldown():
    """
    CRITICAL: Rate limit should reset after cooldown period.

    Given: User is rate-limited
    When: Wait for cooldown period (e.g., 15 minutes)
    Then: User can attempt login again

    Business Impact: User not permanently locked out
    Security Impact: Balance between security and usability
    """
    # Trigger rate limit
    for i in range(10):
        with suppress(InvalidCredentialsError):
            await login_user(email="test@test.com", password="wrong")

    # Wait for cooldown (mock time)
    await advance_time(minutes=15)

    # Should be able to login now
    result = await login_user(email="test@test.com", password="correct")
    assert result["session"]["access_token"] is not None
```

**Why Critical**:
- ✗ **WITHOUT**: Attacker peut brute force passwords → Account takeover
- ✓ **WITH**: Comptes protégés contre brute force

---

#### Test Case #7: Session Validation - Expired Token

**File**: `tests/auth/test_session_validation.py`

```python
async def test_validate_session_rejects_expired_token():
    """
    CRITICAL: Expired sessions must be rejected.

    Given: User session created 2 hours ago (expires after 1 hour)
    When: User makes request with expired token
    Then: Raise SessionExpiredError

    Business Impact: CRITICAL - session hijacking prevention
    Security Impact: CRITICAL - persistent access after logout
    """
    # Create user and get token
    user = await signup_user(email="test@test.com", password="Pass123!")
    token = user["session"]["access_token"]

    # Mock time advancement (2 hours)
    await advance_time(hours=2)

    # Try to use expired token
    with pytest.raises(SessionExpiredError):
        await validate_session(token)


async def test_validate_session_rejects_malformed_token():
    """
    CRITICAL: Malformed tokens must be rejected.

    Given: Invalid JWT tokens (not proper format)
    When: validate_session called
    Then: Raise InvalidTokenError

    Business Impact: HIGH - prevents injection attacks
    Security Impact: CRITICAL - malformed tokens = attack vector
    """
    invalid_tokens = [
        "not.a.jwt",
        "only.two.parts",
        "",
        None,
        "a" * 1000,  # Too long
        "../../etc/passwd",  # Path traversal attempt
    ]

    for invalid_token in invalid_tokens:
        with pytest.raises(InvalidTokenError):
            await validate_session(invalid_token)
```

**Why Critical**:
- ✗ **WITHOUT**: Sessions persistent après expiration → Stolen tokens work forever
- ✓ **WITH**: Sessions properly invalidated

---

**Authentication Tests Summary**:

| Test | Priority | Impact | Lines |
|------|----------|--------|-------|
| Duplicate email rejection | P0 | 🔥🔥🔥 | 18 |
| Brute force protection | P0 | 🔥🔥🔥 | 25 |
| Rate limit cooldown | P0 | 🔥🔥 | 20 |
| Expired token rejection | P0 | 🔥🔥🔥 | 16 |
| Malformed token rejection | P0 | 🔥🔥🔥 | 18 |
| Weak password rejection | P0 | 🔥🔥 | 15 |
| ... (6 more auth tests) | P0 | 🔥🔥 | ~100 |

**Total auth tests**: **12 tests** | **~210 lines** | **1.5 jours**

---

### 3. Pickup Scheduling Tests (10 tests)

**Criticité**: 🔥🔥 HAUTE
**Impact**: Core business logic failure
**Effort**: 1.5 jours

---

#### Test Case #8: Create Pickup - Parent Ownership Validation

**File**: `tests/business_logic/test_pickup_scheduling.py`

```python
async def test_create_pickup_validates_parent_owns_all_children():
    """
    CRITICAL: Parent must own ALL children in pickup request.

    Given: Parent P1, Child C1 (owned by P1), Child C2 (owned by P2)
    When: P1 tries to create pickup for [C1, C2]
    Then: Request rejected with "Not authorized" error

    Business Impact: CRITICAL - prevents unauthorized child pickup
    Security Impact: CRITICAL - child safety issue
    """
    parent1 = await create_test_parent(email="parent1@test.com")
    parent2 = await create_test_parent(email="parent2@test.com")

    child1 = await create_test_child(parent_email=parent1["user"]["email"])
    child2 = await create_test_child(parent_email=parent2["user"]["email"])

    # Parent1 tries to schedule pickup for Parent2's child
    result = await _handle_pickup_schedule_create({
        "accessToken": parent1["session"]["access_token"],
        "childIds": [child1["id"], child2["id"]],  # C2 NOT owned!
        "pickupPersonId": "delegate_123",
        "scheduledTime": "2025-11-04T15:00:00Z"
    })

    assert result.isError == True
    assert "not authorized" in result.content[0].text.lower()


async def test_create_pickup_rejects_empty_children_list():
    """
    CRITICAL: Pickup must have at least one child.

    Given: Parent P1
    When: P1 creates pickup with empty childIds
    Then: ValidationError raised

    Business Impact: HIGH - prevents invalid pickups
    Data Impact: Prevents orphan pickup records
    """
    parent = await create_test_parent()

    with pytest.raises(ValidationError, match="at least one child"):
        await _handle_pickup_schedule_create({
            "accessToken": parent["session"]["access_token"],
            "childIds": [],  # EMPTY!
            "pickupPersonId": "delegate_123",
            "scheduledTime": "2025-11-04T15:00:00Z"
        })
```

**Why Critical**:
- ✗ **WITHOUT**: Parent peut planifier pickup pour enfant d'un autre → **CHILD SAFETY ISSUE**
- ✓ **WITH**: Seulement enfants autorisés

---

#### Test Case #9: Multi-School Coordination

**File**: `tests/business_logic/test_multi_school_pickup.py`

```python
async def test_multi_school_pickup_triggers_a2a_coordination():
    """
    CRITICAL: Pickup with children from multiple schools must coordinate.

    Given: Child C1 at School S1, Child C2 at School S2
    When: Parent creates pickup for [C1, C2]
    Then: coordinate_cross_school_pickup() called, A2A messages sent

    Business Impact: CRITICAL - core multi-school feature
    Data Impact: Both schools must be notified
    """
    parent = await create_test_parent()

    child1 = await create_test_child(
        parent_email=parent["user"]["email"],
        school_id="school_1"
    )
    child2 = await create_test_child(
        parent_email=parent["user"]["email"],
        school_id="school_2"
    )

    result = await _handle_pickup_schedule_create({
        "childIds": [child1["id"], child2["id"]],
        ...
    })

    # Verify A2A coordination
    assert "schools_affected" in result
    assert len(result["schools_affected"]) == 2
    assert "school_1" in result["schools_affected"]
    assert "school_2" in result["schools_affected"]

    # Verify A2A messages
    assert "a2a_messages" in result
    assert len(result["a2a_messages"]) == 2


async def test_single_school_pickup_no_a2a():
    """
    CRITICAL: Single-school pickup should NOT trigger A2A.

    Given: Children C1, C2 both at School S1
    When: Parent creates pickup for [C1, C2]
    Then: create_pickup_request() called (NOT coordinate_cross_school)

    Business Impact: Performance - avoid unnecessary A2A overhead
    """
    child1 = await create_test_child(school_id="school_1")
    child2 = await create_test_child(school_id="school_1")

    result = await _handle_pickup_schedule_create({
        "childIds": [child1["id"], child2["id"]],
        ...
    })

    # Should NOT have A2A coordination
    assert "schools_affected" not in result or len(result["schools_affected"]) == 1
```

**Why Critical**:
- ✗ **WITHOUT**: Multi-école non coordonné → Enfants perdus entre écoles
- ✓ **WITH**: Coordination garantie

---

**Pickup Tests Summary**:

| Test | Priority | Impact | Lines |
|------|----------|--------|-------|
| Parent ownership validation | P0 | 🔥🔥🔥 | 22 |
| Empty children rejection | P0 | 🔥🔥 | 15 |
| Multi-school A2A coordination | P0 | 🔥🔥🔥 | 25 |
| Single-school no A2A | P0 | 🔥🔥 | 18 |
| Past scheduled time validation | P0 | 🔥🔥 | 14 |
| ... (5 more pickup tests) | P0 | 🔥🔥 | ~80 |

**Total pickup tests**: **10 tests** | **~190 lines** | **1.5 jours**

---

### 4. Emergency System Tests (8 tests)

**Criticité**: 🔥🔥 HAUTE
**Impact**: Real-time safety notifications
**Effort**: 1 jour

---

#### Test Case #10: Emergency Cascade to Delegates

**File**: `tests/business_logic/test_emergency_cascade.py`

```python
async def test_emergency_notifies_all_authorized_delegates():
    """
    CRITICAL: Emergency must notify ALL authorized delegates.

    Given: Child C1, Delegates D1 and D2 authorized for C1
    When: Parent declares emergency for C1
    Then: Both D1 and D2 receive notification

    Business Impact: CRITICAL - delegate notification = child safety
    Data Impact: All stakeholders must be informed
    """
    child = await create_test_child()

    delegate1 = await create_test_delegate("delegate1@test.com")
    delegate2 = await create_test_delegate("delegate2@test.com")

    await authorize_delegate_for_child(delegate1["id"], child["id"])
    await authorize_delegate_for_child(delegate2["id"], child["id"])

    result = await _handle_emergency_declare({
        "childId": child["id"],
        "emergencyType": "illness",
        "severity": "high",
        "context": "Fièvre 39°C"
    })

    assert result["notified_delegates_count"] == 2
    assert delegate1["id"] in result["notified_delegate_ids"]
    assert delegate2["id"] in result["notified_delegate_ids"]


async def test_emergency_triggers_postgresql_notify():
    """
    CRITICAL: Emergency must trigger PostgreSQL NOTIFY for real-time.

    Given: Child C1
    When: Parent declares emergency
    Then: pg_notify triggered on 'emergency_alert' channel

    Business Impact: CRITICAL - real-time notification system
    Technical Impact: Dashboard auto-updates
    """
    pg_listener = await create_pg_notify_listener("emergency_alert")

    child = await create_test_child()

    result = await _handle_emergency_declare({
        "childId": child["id"],
        "emergencyType": "late",
        "severity": "medium",
        "context": "Traffic, 15 min de retard"
    })

    # Wait for pg_notify
    notification = await pg_listener.receive(timeout=2)

    assert notification["channel"] == "emergency_alert"
    payload = json.loads(notification["payload"])
    assert payload["emergency_id"] == result["emergency_id"]
    assert payload["type"] == "late"
    assert payload["severity"] == "medium"
```

**Why Critical**:
- ✗ **WITHOUT**: Délégués non notifiés → Enfant en danger
- ✓ **WITH**: Communication temps réel garantie

---

**Emergency Tests Summary**:

| Test | Priority | Impact | Lines |
|------|----------|--------|-------|
| Notify all delegates | P0 | 🔥🔥🔥 | 24 |
| PostgreSQL NOTIFY trigger | P0 | 🔥🔥🔥 | 22 |
| Emergency types validation | P0 | 🔥🔥 | 18 |
| School notification | P0 | 🔥🔥 | 20 |
| ... (4 more emergency tests) | P0 | 🔥🔥 | ~70 |

**Total emergency tests**: **8 tests** | **~154 lines** | **1 jour**

---

### 5. Database Triggers Tests (6 tests)

**Criticité**: 🔥🔥 HAUTE
**Impact**: Data integrity, cascade logic
**Effort**: 0.5 jour

---

#### Test Case #11: Cascade Pickup Cancel → Reset Checkouts

**File**: `tests/database/test_cascade_trigger.py`

```python
async def test_cancel_pickup_resets_all_child_checkouts():
    """
    CRITICAL: Cancelling pickup must reset all child checkouts.

    Given: Pickup P1 with children [C1, C2, C3], C1 and C2 checked out
    When: Update P1 status to 'cancelled'
    Then: Trigger sets all pickup_children.checked_out = FALSE

    Business Impact: CRITICAL - data consistency
    Data Impact: Prevents orphan checkout records
    """
    pickup = await create_test_pickup()

    child1 = await add_child_to_pickup(pickup["id"])
    child2 = await add_child_to_pickup(pickup["id"])
    child3 = await add_child_to_pickup(pickup["id"])

    # Checkout C1 and C2
    await checkout_child(pickup["id"], child1["id"])
    await checkout_child(pickup["id"], child2["id"])

    # Verify checked out
    assert await get_checkout_status(pickup["id"], child1["id"]) == True
    assert await get_checkout_status(pickup["id"], child2["id"]) == True

    # Cancel pickup (should trigger cascade)
    await update_pickup_status(pickup["id"], "cancelled")

    # Verify ALL checkouts reset
    assert await get_checkout_status(pickup["id"], child1["id"]) == False
    assert await get_checkout_status(pickup["id"], child2["id"]) == False
    assert await get_checkout_status(pickup["id"], child3["id"]) == False


async def test_complete_pickup_auto_checkouts_remaining_children():
    """
    CRITICAL: Completing pickup must auto-checkout un-checked children.

    Given: Pickup P1 with [C1, C2, C3], only C1 checked out
    When: Update P1 status to 'completed'
    Then: Trigger sets C2 and C3 checked_out = TRUE

    Business Impact: HIGH - workflow automation
    Data Impact: Completes incomplete data
    """
    pickup = await create_test_pickup()

    child1 = await add_child_to_pickup(pickup["id"])
    child2 = await add_child_to_pickup(pickup["id"])
    child3 = await add_child_to_pickup(pickup["id"])

    # Checkout only C1
    await checkout_child(pickup["id"], child1["id"])

    # Complete pickup
    await update_pickup_status(pickup["id"], "completed")

    # Verify ALL now checked out
    assert await get_checkout_status(pickup["id"], child1["id"]) == True
    assert await get_checkout_status(pickup["id"], child2["id"]) == True  # AUTO!
    assert await get_checkout_status(pickup["id"], child3["id"]) == True  # AUTO!
```

**Why Critical**:
- ✗ **WITHOUT**: Checkouts incohérents après cancel/complete → Data corruption
- ✓ **WITH**: Data integrity garantie

---

**Trigger Tests Summary**:

| Test | Priority | Impact | Lines |
|------|----------|--------|-------|
| Cancel resets checkouts | P0 | 🔥🔥🔥 | 26 |
| Complete auto-checkouts | P0 | 🔥🔥 | 24 |
| Emergency pg_notify | P0 | 🔥🔥🔥 | 20 |
| ... (3 more trigger tests) | P0 | 🔥🔥 | ~60 |

**Total trigger tests**: **6 tests** | **~130 lines** | **0.5 jour**

---

## Résumé des Tests Critiques P0

### Par Catégorie

| Catégorie | Tests P0 | Lines | Effort | Risk Mitigated |
|-----------|----------|-------|--------|----------------|
| **Security & RLS** | 24 | ~350 | 2.5j | Data breach, Privacy |
| **Authentication** | 12 | ~210 | 1.5j | Account takeover |
| **Pickup Logic** | 10 | ~190 | 1.5j | Business logic bugs |
| **Emergency System** | 8 | ~154 | 1j | Safety notifications |
| **DB Triggers** | 6 | ~130 | 0.5j | Data integrity |
| **TOTAL** | **60** | **~1,034** | **7j** | **System integrity** |

---

### Ordre d'Implémentation Recommandé

**Semaine 1 - Jour par jour**:

#### Jour 1: Security Foundation
- [ ] Setup pytest infrastructure (fixtures, conftest)
- [ ] RLS tests #1-#8 (Parent & Delegate isolation)
- **Deliverable**: 8 RLS tests passing

#### Jour 2: Multi-Tenant Security
- [ ] RLS tests #9-#16 (School staff isolation)
- [ ] JWT security tests #17-#24
- **Deliverable**: 16 RLS tests passing (total: 24)

#### Jour 3: Authentication
- [ ] Auth tests #1-#6 (Signup, Login)
- [ ] Session validation tests #7-#12
- **Deliverable**: 12 auth tests passing

#### Jour 4: Business Logic
- [ ] Pickup scheduling tests #1-#5
- [ ] Multi-school coordination tests #6-#10
- **Deliverable**: 10 pickup tests passing

#### Jour 5: Real-time & Triggers
- [ ] Emergency cascade tests #1-#8
- [ ] Database trigger tests #1-#6
- **Deliverable**: 14 tests passing

#### Jour 6-7: Buffer & Documentation
- [ ] Fix any failing tests
- [ ] Add test documentation
- [ ] Setup CI/CD
- [ ] Code review

---

## Quick Start Guide

### Setup (30 minutes)

```bash
# 1. Install dependencies
cd allobye_server_python
pip install -r requirements.txt

# 2. Create test structure
mkdir -p tests/{auth,database,business_logic,fixtures}
touch tests/conftest.py

# 3. Configure pytest
cat > pytest.ini << EOF
[pytest]
asyncio_mode = auto
testpaths = tests
addopts = --cov=. --cov-report=html --cov-fail-under=25
EOF

# 4. Run first test
pytest tests/ -v
```

### Template Test File

```python
# tests/auth/test_critical_auth.py
import pytest
from auth import signup_user, UserAlreadyExistsError

class TestCriticalAuth:
    """Critical P0 authentication tests."""

    async def test_signup_rejects_duplicate_email(self):
        """P0: Prevent duplicate email signup."""
        await signup_user(email="test@test.com", password="Pass123!")

        with pytest.raises(UserAlreadyExistsError):
            await signup_user(email="test@test.com", password="Other123!")

    # Add more P0 tests...
```

---

## Success Criteria

### Week 1 Goals

**Tests written**: 60 critical tests
**Coverage achieved**: ~25%
**Critical paths covered**: 100%

### Acceptance Criteria

- [ ] All 24 RLS tests passing
- [ ] All 12 auth tests passing
- [ ] All 10 pickup tests passing
- [ ] All 8 emergency tests passing
- [ ] All 6 trigger tests passing
- [ ] CI/CD pipeline green
- [ ] No P0 security gaps remaining

---

## Annexe: Test Templates

### Template: RLS Test

```python
async def test_rls_<role>_<action>_<resource>(client, fixtures):
    """
    CRITICAL: <Role> <can/cannot> <action> <resource>.

    Given: <Setup>
    When: <Action>
    Then: <Expected result>

    Business Impact: <Why it matters>
    Security Impact: <Security implications>
    """
    # ARRANGE
    resource = await create_test_resource()

    # ACT
    response = client.table("<table>").select("*").execute()

    # ASSERT
    assert len(response.data) == <expected_count>
```

### Template: Business Logic Test

```python
async def test_<function>_<scenario>_<result>():
    """
    CRITICAL: <Description of what's being tested>.

    Given: <Initial state>
    When: <Action performed>
    Then: <Expected outcome>

    Business Impact: <Impact on business>
    Data Impact: <Impact on data>
    """
    # ARRANGE
    setup = await create_test_setup()

    # ACT
    result = await function_under_test(...)

    # ASSERT
    assert result.isError == False
    assert result["expected_field"] == expected_value
```

---

**Document créé le**: 2025-11-04
**Priorité**: 🔥 P0 - À commencer IMMÉDIATEMENT
**Effort total**: 7 jours (parallélisable → 3-4 jours calendaires)
**ROI**: Protection contre data breach, account takeover, business logic bugs
