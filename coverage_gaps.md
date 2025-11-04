# Coverage Gaps Report - AllôBye

**Date**: 2025-11-04
**Analyseur**: Analyseur de Tests
**Focus**: Zones critiques non couvertes par les tests

---

## Executive Summary

### Gap Analysis Global

| Zone | Total Functions/Components | Tested | Gap | Criticité |
|------|---------------------------|--------|-----|-----------|
| **Authentication & Security** | 19 | 0 | 100% | 🔥 CRITIQUE |
| **Business Logic (MCP Handlers)** | 15 | 0 | 100% | 🔥 CRITIQUE |
| **Database Layer (RLS + Triggers)** | 28 | 0 | 100% | 🔥 CRITIQUE |
| **Real-time & WebSockets** | 8 | 0 | 100% | 🔥 CRITIQUE |
| **Frontend Components** | 12 | 0 | 100% | ⚠️ HAUTE |
| **Monitoring System** | 17 | ~5 | ~70% | ⚠️ MOYENNE |

**Total Gap**: **99 composants critiques - 0 testés = 99% gap**

---

## Gap #1: Authentication & Authorization (100% Gap) 🔥

### Criticité: MAXIMALE
**Impact**: Failles de sécurité, accès non autorisé, vol de données

### Fonctions Non Testées

#### auth.py - 19 Fonctions - 0% Coverage

| Function | Lines | Complexity | Security Risk | Priority |
|----------|-------|------------|---------------|----------|
| `signup_user` | 96 | 14 | 🔥 CRITIQUE | P0 |
| `login_user` | 80 | 12 | 🔥 CRITIQUE | P0 |
| `validate_session` | 30 | 8 | 🔥 CRITIQUE | P0 |
| `get_user_profile` | 71 | 11 | 🔥 CRITIQUE | P0 |
| `verify_parent_owns_child` | 24 | 3 | 🔥 CRITIQUE | P0 |
| `verify_staff_at_school` | 24 | 3 | 🔥 CRITIQUE | P0 |
| `update_user_profile` | 26 | 6 | ⚠️ HAUTE | P1 |
| `reset_password_request` | 18 | 2 | ⚠️ HAUTE | P1 |
| `verify_email_token` | 22 | 5 | ⚠️ HAUTE | P1 |
| `logout_user` | 14 | 2 | ⚠️ MOYENNE | P2 |

---

### Tests Critiques Manquants

#### 1. Signup Flow

**Scénarios NON TESTÉS**:

```python
# ❌ NOT TESTED: Happy path
def test_signup_creates_user_and_profile():
    result = await signup_user(
        email="parent@test.com",
        password="SecurePass123!",
        name="Test Parent",
        role="parent"
    )
    assert result["user"]["email"] == "parent@test.com"
    assert result["session"]["access_token"] is not None

    # Verify profile created in DB
    profile = await get_user_profile(result["user"]["id"])
    assert profile["role"] == "parent"

# ❌ NOT TESTED: Duplicate email
def test_signup_with_existing_email_fails():
    await signup_user(email="dup@test.com", password="pass123")

    with pytest.raises(UserAlreadyExistsError):
        await signup_user(email="dup@test.com", password="pass456")

# ❌ NOT TESTED: Weak password
def test_signup_with_weak_password_fails():
    with pytest.raises(ValidationError):
        await signup_user(email="test@test.com", password="123")

# ❌ NOT TESTED: Invalid email
def test_signup_with_invalid_email_fails():
    with pytest.raises(ValidationError):
        await signup_user(email="not-an-email", password="SecurePass123!")

# ❌ NOT TESTED: SQL injection attempt
def test_signup_sanitizes_sql_injection():
    result = await signup_user(
        email="'; DROP TABLE users; --@test.com",
        password="pass123"
    )
    # Should NOT drop table, should escape properly

# ❌ NOT TESTED: School staff with schools
def test_signup_school_staff_links_schools():
    result = await signup_user(
        email="staff@test.com",
        password="pass123",
        role="school_staff",
        schools=["school_1", "school_2"]
    )

    profile = await get_user_profile(result["user"]["id"])
    assert len(profile["schools"]) == 2
```

---

#### 2. Login Flow

**Scénarios NON TESTÉS**:

```python
# ❌ NOT TESTED: Valid credentials
def test_login_with_valid_credentials():
    await signup_user(email="test@test.com", password="Pass123!")

    result = await login_user(email="test@test.com", password="Pass123!")
    assert result["session"]["access_token"] is not None
    assert result["user"]["email"] == "test@test.com"

# ❌ NOT TESTED: Invalid password
def test_login_with_wrong_password_fails():
    await signup_user(email="test@test.com", password="correct")

    with pytest.raises(InvalidCredentialsError):
        await login_user(email="test@test.com", password="wrong")

# ❌ NOT TESTED: Non-existent user
def test_login_with_nonexistent_email_fails():
    with pytest.raises(UserNotFoundError):
        await login_user(email="ghost@test.com", password="pass123")

# ❌ NOT TESTED: Case sensitivity
def test_login_email_is_case_insensitive():
    await signup_user(email="Test@Example.com", password="pass123")

    result = await login_user(email="test@example.com", password="pass123")
    assert result["user"] is not None

# ❌ NOT TESTED: Brute force protection
@pytest.mark.parametrize("attempt", range(10))
def test_login_rate_limiting(attempt):
    for i in range(10):
        with pytest.raises(InvalidCredentialsError):
            await login_user(email="test@test.com", password=f"wrong{i}")

    # 11th attempt should be rate-limited
    with pytest.raises(RateLimitExceededError):
        await login_user(email="test@test.com", password="wrong")
```

---

#### 3. Session Validation

**Scénarios NON TESTÉS**:

```python
# ❌ NOT TESTED: Valid session
def test_validate_session_with_valid_token():
    signup_result = await signup_user(email="test@test.com", password="pass123")
    token = signup_result["session"]["access_token"]

    user = await validate_session(token)
    assert user["email"] == "test@test.com"

# ❌ NOT TESTED: Expired token
def test_validate_session_with_expired_token():
    old_token = "eyJ..."  # Expired JWT

    with pytest.raises(SessionExpiredError):
        await validate_session(old_token)

# ❌ NOT TESTED: Malformed token
def test_validate_session_with_malformed_token():
    with pytest.raises(InvalidTokenError):
        await validate_session("not.a.jwt")

# ❌ NOT TESTED: Tampered token
def test_validate_session_with_tampered_token():
    signup_result = await signup_user(email="user@test.com", password="pass123")
    token = signup_result["session"]["access_token"]

    # Tamper with token (change email claim)
    tampered = token.replace("user@test.com", "admin@test.com")

    with pytest.raises(InvalidTokenError):
        await validate_session(tampered)
```

---

#### 4. Authorization Checks

**Scénarios NON TESTÉS**:

```python
# ❌ NOT TESTED: Parent owns child
def test_verify_parent_owns_child_success():
    parent = await signup_user(email="parent@test.com", ...)
    child = await create_child(parent_email="parent@test.com", ...)

    result = await verify_parent_owns_child(parent["id"], child["id"])
    assert result == True

# ❌ NOT TESTED: Parent does NOT own child
def test_verify_parent_owns_child_fails():
    parent1 = await signup_user(email="parent1@test.com", ...)
    parent2 = await signup_user(email="parent2@test.com", ...)
    child = await create_child(parent_email="parent2@test.com", ...)

    result = await verify_parent_owns_child(parent1["id"], child["id"])
    assert result == False

# ❌ NOT TESTED: Staff at school
def test_verify_staff_at_school_success():
    staff = await signup_user(
        email="staff@test.com",
        role="school_staff",
        schools=["school_1"]
    )

    result = await verify_staff_at_school(staff["id"], "school_1")
    assert result == True

# ❌ NOT TESTED: Staff NOT at school
def test_verify_staff_at_school_fails():
    staff = await signup_user(
        email="staff@test.com",
        role="school_staff",
        schools=["school_1"]
    )

    result = await verify_staff_at_school(staff["id"], "school_2")
    assert result == False
```

---

### Impact de ce Gap

**Risques Non Détectés**:
- ✗ Utilisateur peut signup avec email invalide → Données corrompues
- ✗ Password faible accepté → Comptes compromis
- ✗ Login sans rate limiting → Brute force attacks
- ✗ Session expirée non détectée → Accès non autorisé
- ✗ JWT tamper non détecté → Privilege escalation
- ✗ Parent peut accéder enfants d'autres parents → Data breach
- ✗ Staff peut voir données d'autres écoles → Privacy violation

**Nombre de tests manquants**: **~40 tests critiques**

---

## Gap #2: Business Logic - MCP Handlers (100% Gap) 🔥

### Criticité: MAXIMALE
**Impact**: Bugs fonctionnels, données incohérentes, workflows cassés

### Handlers Non Testés

#### main.py - 15 Handlers Critiques - 0% Coverage

| Handler | Lines | Complexity | Business Impact | Priority |
|---------|-------|------------|-----------------|----------|
| `_handle_pickup_schedule_create` | 85 | 15 | 🔥 CRITIQUE | P0 |
| `_handle_delegate_authorize` | 67 | 12 | 🔥 CRITIQUE | P0 |
| `_handle_emergency_declare` | 68 | 11 | 🔥 CRITIQUE | P0 |
| `_handle_school_dashboard_fetch` | 76 | 13 | ⚠️ HAUTE | P1 |
| `_handle_auth_signup` | 40 | 8 | 🔥 CRITIQUE | P0 |
| `_handle_auth_login` | 42 | 7 | 🔥 CRITIQUE | P0 |
| `get_school_pickups` | 56 | 11 | ⚠️ HAUTE | P1 |
| `create_pickup_request` | 47 | 8 | 🔥 CRITIQUE | P0 |
| `coordinate_cross_school_pickup` | 22 | 7 | ⚠️ HAUTE | P1 |
| `broadcast_delegate_authorization` | 43 | 7 | ⚠️ HAUTE | P1 |
| `broadcast_emergency` | 45 | 7 | 🔥 CRITIQUE | P0 |
| `get_authorized_delegates` | 19 | 5 | ⚠️ HAUTE | P1 |
| `get_schools_for_children` | 25 | 6 | ⚠️ HAUTE | P1 |

---

### Tests Critiques Manquants

#### 1. Pickup Scheduling

**Scénarios NON TESTÉS**:

```python
# ❌ NOT TESTED: Single-school pickup
async def test_create_pickup_single_school():
    parent = await create_test_parent()
    child = await create_test_child(parent_email=parent.email, school_id="school_1")
    delegate = await create_test_delegate(authorized_for=[child.id])

    result = await _handle_pickup_schedule_create({
        "accessToken": parent.token,
        "childIds": [child.id],
        "pickupPersonId": delegate.id,
        "scheduledTime": "15:00"
    })

    assert result.isError == False
    assert "pickup_id" in result.content[0].text

# ❌ NOT TESTED: Multi-school pickup (A2A coordination)
async def test_create_pickup_multi_school():
    parent = await create_test_parent()
    child1 = await create_test_child(school_id="school_1")
    child2 = await create_test_child(school_id="school_2")

    result = await _handle_pickup_schedule_create({
        "childIds": [child1.id, child2.id],
        ...
    })

    assert "schools_affected" in result
    assert len(result["schools_affected"]) == 2

# ❌ NOT TESTED: Parent doesn't own child
async def test_create_pickup_unauthorized_child():
    parent1 = await create_test_parent(email="parent1@test.com")
    parent2 = await create_test_parent(email="parent2@test.com")
    child = await create_test_child(parent_email=parent2.email)

    result = await _handle_pickup_schedule_create({
        "accessToken": parent1.token,
        "childIds": [child.id],
        ...
    })

    assert result.isError == True
    assert "not authorized" in result.content[0].text.lower()

# ❌ NOT TESTED: Delegate not authorized
async def test_create_pickup_unauthorized_delegate():
    child = await create_test_child()
    unauthorized_delegate = await create_test_delegate()  # Not linked to child

    result = await _handle_pickup_schedule_create({
        "pickupPersonId": unauthorized_delegate.id,
        "childIds": [child.id],
        ...
    })

    # SHOULD FAIL but currently NOT VALIDATED!
    # This is a BUG in the code

# ❌ NOT TESTED: Empty child_ids
async def test_create_pickup_no_children():
    result = await _handle_pickup_schedule_create({
        "childIds": [],
        ...
    })

    assert result.isError == True

# ❌ NOT TESTED: Scheduled time in past
async def test_create_pickup_past_time():
    result = await _handle_pickup_schedule_create({
        "scheduledTime": "2020-01-01T10:00:00Z",
        ...
    })

    # Should reject or at least warn

# ❌ NOT TESTED: Concurrent pickup creation
async def test_concurrent_pickup_creation():
    child = await create_test_child()

    # Two parents try to schedule same child simultaneously
    task1 = asyncio.create_task(_handle_pickup_schedule_create({
        "childIds": [child.id],
        "scheduledTime": "15:00"
    }))
    task2 = asyncio.create_task(_handle_pickup_schedule_create({
        "childIds": [child.id],
        "scheduledTime": "15:05"
    }))

    result1, result2 = await asyncio.gather(task1, task2)

    # Both should succeed (or should one fail?)
    # Current behavior: UNDEFINED
```

---

#### 2. Delegate Authorization

**Scénarios NON TESTÉS**:

```python
# ❌ NOT TESTED: Authorize delegate for single child
async def test_authorize_delegate_single_child():
    parent = await create_test_parent()
    child = await create_test_child(parent_email=parent.email)

    result = await _handle_delegate_authorize({
        "accessToken": parent.token,
        "delegateEmail": "grandma@test.com",
        "delegateName": "Grand-mère",
        "childIds": [child.id],
        "permissions": ["pickup", "emergency_contact"]
    })

    assert result.isError == False
    assert "delegate_id" in result

    # Verify delegate created
    delegate = await get_delegate_by_email("grandma@test.com")
    assert delegate is not None
    assert child.id in delegate.authorized_children

# ❌ NOT TESTED: Authorize delegate for multiple children
async def test_authorize_delegate_multiple_children():
    parent = await create_test_parent()
    child1 = await create_test_child(parent_email=parent.email)
    child2 = await create_test_child(parent_email=parent.email)

    result = await _handle_delegate_authorize({
        "childIds": [child1.id, child2.id],
        ...
    })

    delegate = await get_delegate_by_email(...)
    assert len(delegate.authorized_children) == 2

# ❌ NOT TESTED: Update existing delegate
async def test_update_existing_delegate():
    # First authorization
    await _handle_delegate_authorize({
        "delegateEmail": "uncle@test.com",
        "childIds": ["child_1"],
        "permissions": ["pickup"]
    })

    # Update with new child
    await _handle_delegate_authorize({
        "delegateEmail": "uncle@test.com",  # Same email
        "childIds": ["child_1", "child_2"],  # Add child_2
        "permissions": ["pickup", "emergency_contact"]  # Add permission
    })

    delegate = await get_delegate_by_email("uncle@test.com")
    assert len(delegate.authorized_children) == 2
    assert "emergency_contact" in delegate.permissions

# ❌ NOT TESTED: A2A sync to multiple schools
async def test_delegate_authorize_syncs_to_all_schools():
    child1 = await create_test_child(school_id="school_1")
    child2 = await create_test_child(school_id="school_2")

    result = await _handle_delegate_authorize({
        "childIds": [child1.id, child2.id],
        ...
    })

    assert len(result["authorized_schools"]) == 2
    assert "a2a_messages" in result
```

---

#### 3. Emergency Declaration

**Scénarios NON TESTÉS**:

```python
# ❌ NOT TESTED: Declare emergency for owned child
async def test_declare_emergency_for_owned_child():
    parent = await create_test_parent()
    child = await create_test_child(parent_email=parent.email)

    result = await _handle_emergency_declare({
        "accessToken": parent.token,
        "childId": child.id,
        "emergencyType": "illness",
        "severity": "medium",
        "context": "Fièvre élevée, ne viendra pas aujourd'hui"
    })

    assert result.isError == False
    assert "emergency_id" in result

# ❌ NOT TESTED: Emergency types validation
@pytest.mark.parametrize("emergency_type", [
    "late", "illness", "cancel", "injury", "other"
])
async def test_emergency_types_accepted(emergency_type):
    result = await _handle_emergency_declare({
        "emergencyType": emergency_type,
        ...
    })

    assert result.isError == False

async def test_invalid_emergency_type_rejected():
    result = await _handle_emergency_declare({
        "emergencyType": "invalid_type",
        ...
    })

    assert result.isError == True

# ❌ NOT TESTED: Emergency cascade to delegates
async def test_emergency_notifies_all_delegates():
    child = await create_test_child()
    delegate1 = await authorize_delegate_for_child(child.id)
    delegate2 = await authorize_delegate_for_child(child.id)

    result = await _handle_emergency_declare({
        "childId": child.id,
        ...
    })

    assert result["notified_delegates_count"] == 2

# ❌ NOT TESTED: Emergency cascade to schools
async def test_emergency_notifies_school():
    child = await create_test_child(school_id="school_1")

    result = await _handle_emergency_declare({
        "childId": child.id,
        ...
    })

    assert "school_1" in result["notified_schools"]

# ❌ NOT TESTED: PostgreSQL NOTIFY triggered
async def test_emergency_triggers_pg_notify(pg_notify_listener):
    result = await _handle_emergency_declare({...})

    # Listen for pg_notify on 'emergency_alert' channel
    notification = await pg_notify_listener.wait_for_notification(timeout=1)

    assert notification["channel"] == "emergency_alert"
    assert notification["payload"]["emergency_type"] == "illness"
```

---

### Impact de ce Gap

**Risques Non Détectés**:
- ✗ Pickup créé avec delegate non autorisé → Sécurité enfants compromise
- ✗ Pickup multi-école sans coordination → Enfants perdus
- ✗ Emergency non propagée → Délégués non informés
- ✗ Concurrent pickups → Conflits de données
- ✗ Time window logic incorrecte → Mauvais pickups affichés

**Nombre de tests manquants**: **~50 tests critiques**

---

## Gap #3: Database Layer (100% Gap) 🔥

### Criticité: MAXIMALE
**Impact**: Bypass de sécurité, corruption de données, violations de privacy

### RLS Policies Non Testées: 22/22

#### schema.sql - 22 RLS Policies - 0% Coverage

| Policy | Table | Risk Level | Lines | Priority |
|--------|-------|------------|-------|----------|
| Parents can view their own children | children | 🔥 CRITIQUE | 3 | P0 |
| Parents can view their children's pickups | pickups | 🔥 CRITIQUE | 10 | P0 |
| Parents can view authorized delegates | delegates | 🔥 CRITIQUE | 10 | P0 |
| Parents can view emergencies | emergencies | 🔥 CRITIQUE | 9 | P0 |
| Delegates can view their profile | delegates | ⚠️ HAUTE | 2 | P1 |
| Delegates can view assigned pickups | pickups | 🔥 CRITIQUE | 9 | P0 |
| Delegates can view emergencies | emergencies | 🔥 CRITIQUE | 11 | P0 |
| Staff can view school children | children | 🔥 CRITIQUE | 9 | P0 |
| Staff can view school pickups | pickups | 🔥 CRITIQUE | 11 | P0 |
| Staff can view school emergencies | emergencies | 🔥 CRITIQUE | 10 | P0 |

**+ 12 autres policies (INSERT, UPDATE, DELETE)**

---

### Tests RLS Manquants

```sql
-- ❌ NOT TESTED: Parent can view OWN children
CREATE FUNCTION test_parent_can_view_own_children() RETURNS void AS $$
DECLARE
    parent_user_id UUID;
    child_id UUID;
BEGIN
    -- Setup
    parent_user_id := create_test_user('parent@test.com', 'parent');
    child_id := create_test_child(parent_email => 'parent@test.com');

    -- Set session as parent
    PERFORM set_config('request.jwt.claims', json_build_object(
        'email', 'parent@test.com',
        'role', 'parent'
    )::text, TRUE);

    -- Test: Parent can SELECT their child
    ASSERT EXISTS (SELECT 1 FROM children WHERE id = child_id),
        'Parent should be able to view their own child';
END;
$$ LANGUAGE plpgsql;

-- ❌ NOT TESTED: Parent CANNOT view other parent's children
CREATE FUNCTION test_parent_cannot_view_other_children() RETURNS void AS $$
DECLARE
    parent1_id UUID;
    parent2_id UUID;
    child_of_parent2 UUID;
BEGIN
    parent1_id := create_test_user('parent1@test.com', 'parent');
    parent2_id := create_test_user('parent2@test.com', 'parent');
    child_of_parent2 := create_test_child(parent_email => 'parent2@test.com');

    -- Set session as parent1
    PERFORM set_config('request.jwt.claims', json_build_object(
        'email', 'parent1@test.com',
        'role', 'parent'
    )::text, TRUE);

    -- Test: Parent1 CANNOT see parent2's child
    ASSERT NOT EXISTS (SELECT 1 FROM children WHERE id = child_of_parent2),
        'Parent should NOT be able to view other parent''s children';
END;
$$ LANGUAGE plpgsql;

-- ❌ NOT TESTED: Delegate can view assigned pickups
CREATE FUNCTION test_delegate_can_view_assigned_pickups() RETURNS void AS $$
DECLARE
    delegate_id UUID;
    pickup_id UUID;
BEGIN
    delegate_id := create_test_delegate('delegate@test.com');
    pickup_id := create_test_pickup(pickup_person_id => delegate_id);

    -- Set session as delegate
    PERFORM set_config('request.jwt.claims', json_build_object(
        'email', 'delegate@test.com',
        'role', 'delegate'
    )::text, TRUE);

    -- Test: Delegate can see pickups where they are pickup_person
    ASSERT EXISTS (SELECT 1 FROM pickups WHERE id = pickup_id),
        'Delegate should see pickups assigned to them';
END;
$$ LANGUAGE plpgsql;

-- ❌ NOT TESTED: Delegate CANNOT view other delegate's pickups
CREATE FUNCTION test_delegate_cannot_view_other_pickups() RETURNS void AS $$
DECLARE
    delegate1_id UUID;
    delegate2_id UUID;
    pickup_for_delegate2 UUID;
BEGIN
    delegate1_id := create_test_delegate('delegate1@test.com');
    delegate2_id := create_test_delegate('delegate2@test.com');
    pickup_for_delegate2 := create_test_pickup(pickup_person_id => delegate2_id);

    -- Set session as delegate1
    PERFORM set_config('request.jwt.claims', json_build_object(
        'email', 'delegate1@test.com'
    )::text, TRUE);

    -- Test: Delegate1 CANNOT see delegate2's pickups
    ASSERT NOT EXISTS (SELECT 1 FROM pickups WHERE id = pickup_for_delegate2),
        'Delegate should NOT see other delegate''s pickups';
END;
$$ LANGUAGE plpgsql;

-- ❌ NOT TESTED: School staff can view school children
CREATE FUNCTION test_staff_can_view_school_children() RETURNS void AS $$
DECLARE
    staff_id UUID;
    school_id UUID;
    child_id UUID;
BEGIN
    school_id := create_test_school('École Test');
    staff_id := create_test_user('staff@test.com', 'school_staff', schools => ARRAY[school_id]);
    child_id := create_test_child(school_id => school_id);

    -- Set session as school staff
    PERFORM set_config('request.jwt.claims', json_build_object(
        'email', 'staff@test.com',
        'role', 'school_staff'
    )::text, TRUE);

    -- Test: Staff can see children at their school
    ASSERT EXISTS (SELECT 1 FROM children WHERE id = child_id),
        'School staff should see children at their school';
END;
$$ LANGUAGE plpgsql;

-- ❌ NOT TESTED: School staff CANNOT view other school's children
CREATE FUNCTION test_staff_cannot_view_other_school_children() RETURNS void AS $$
DECLARE
    staff_id UUID;
    school1_id UUID;
    school2_id UUID;
    child_at_school2 UUID;
BEGIN
    school1_id := create_test_school('École A');
    school2_id := create_test_school('École B');
    staff_id := create_test_user('staff@test.com', 'school_staff', schools => ARRAY[school1_id]);
    child_at_school2 := create_test_child(school_id => school2_id);

    -- Set session as staff at school1
    PERFORM set_config('request.jwt.claims', json_build_object(
        'email', 'staff@test.com'
    )::text, TRUE);

    -- Test: Staff CANNOT see children at other schools
    ASSERT NOT EXISTS (SELECT 1 FROM children WHERE id = child_at_school2),
        'School staff should NOT see children at other schools';
END;
$$ LANGUAGE plpgsql;
```

**Nombre de tests RLS manquants**: **~44 tests** (2 par policy: positive + negative)

---

### Triggers Non Testés: 6/6

| Trigger | Function | Risk Level | Priority |
|---------|----------|------------|----------|
| emergency_notification | notify_emergency() | 🔥 CRITIQUE | P0 |
| pickup_status_cascade | cascade_pickup_status() | 🔥 CRITIQUE | P0 |
| update_updated_at (6 tables) | update_updated_at_column() | ⚠️ BASSE | P2 |

---

### Tests Triggers Manquants

```sql
-- ❌ NOT TESTED: Cancel pickup resets checkouts
CREATE FUNCTION test_cancel_pickup_resets_checkouts() RETURNS void AS $$
DECLARE
    pickup_id UUID;
    child1_id UUID;
    child2_id UUID;
BEGIN
    pickup_id := create_test_pickup();
    child1_id := add_child_to_pickup(pickup_id);
    child2_id := add_child_to_pickup(pickup_id);

    -- Checkout children
    UPDATE pickup_children SET checked_out = TRUE, checked_out_at = NOW()
    WHERE pickup_id = pickup_id AND child_id = child1_id;

    ASSERT (SELECT checked_out FROM pickup_children
            WHERE pickup_id = pickup_id AND child_id = child1_id) = TRUE,
        'Child should be checked out';

    -- Cancel pickup (should trigger cascade)
    UPDATE pickups SET status = 'cancelled' WHERE id = pickup_id;

    -- Test: All checkouts reset
    ASSERT (SELECT COUNT(*) FROM pickup_children
            WHERE pickup_id = pickup_id AND checked_out = TRUE) = 0,
        'All children should be unchecked after pickup cancellation';
END;
$$ LANGUAGE plpgsql;

-- ❌ NOT TESTED: Complete pickup auto-checks remaining children
CREATE FUNCTION test_complete_pickup_auto_checkout() RETURNS void AS $$
DECLARE
    pickup_id UUID;
    child1_id UUID;
    child2_id UUID;
    child3_id UUID;
BEGIN
    pickup_id := create_test_pickup();
    child1_id := add_child_to_pickup(pickup_id);
    child2_id := add_child_to_pickup(pickup_id);
    child3_id := add_child_to_pickup(pickup_id);

    -- Checkout only child1
    UPDATE pickup_children SET checked_out = TRUE
    WHERE pickup_id = pickup_id AND child_id = child1_id;

    -- Complete pickup (should auto-checkout child2 and child3)
    UPDATE pickups SET status = 'completed' WHERE id = pickup_id;

    -- Test: All children now checked out
    ASSERT (SELECT COUNT(*) FROM pickup_children
            WHERE pickup_id = pickup_id AND checked_out = TRUE) = 3,
        'All children should be auto-checked when pickup completes';
END;
$$ LANGUAGE plpgsql;

-- ❌ NOT TESTED: Emergency triggers pg_notify
CREATE FUNCTION test_emergency_triggers_notify() RETURNS void AS $$
DECLARE
    emergency_id UUID;
    notification_received BOOLEAN := FALSE;
BEGIN
    -- Listen for notifications
    LISTEN emergency_alert;

    -- Create emergency (should trigger notify_emergency())
    INSERT INTO emergencies (child_id, emergency_type, severity, context)
    VALUES (
        (SELECT id FROM children LIMIT 1),
        'illness',
        'medium',
        'Test emergency'
    )
    RETURNING id INTO emergency_id;

    -- Wait for notification (in real test, use pg_notify listener)
    -- SELECT pg_notify_received('emergency_alert') INTO notification_received;

    ASSERT notification_received = TRUE,
        'pg_notify should be triggered on emergency creation';
END;
$$ LANGUAGE plpgsql;
```

**Nombre de tests triggers manquants**: **~8 tests**

---

### Impact de ce Gap

**Risques Non Détectés**:
- ✗ RLS bypass → Parent voit enfants d'autres parents → **MAJOR DATA BREACH**
- ✗ RLS bypass → Staff voit données autres écoles → **PRIVACY VIOLATION**
- ✗ Trigger cascade_pickup_status non testé → Checkouts incohérents
- ✗ Trigger notify_emergency non testé → Urgences non propagées
- ✗ JWT claims manipulation → **PRIVILEGE ESCALATION**

**Nombre total de tests DB manquants**: **~52 tests critiques**

---

## Gap #4: Real-time & WebSockets (100% Gap) 🔥

### Criticité: HAUTE
**Impact**: Real-time features cassées, stale data, UX dégradée

### Composants Non Testés

| Component | Functionality | Risk | Priority |
|-----------|---------------|------|----------|
| Supabase Realtime subscription setup | WebSocket connection | ⚠️ HAUTE | P1 |
| Postgres changes listener | INSERT/UPDATE/DELETE events | 🔥 CRITIQUE | P0 |
| Emergency alert subscription | Real-time emergencies | 🔥 CRITIQUE | P0 |
| Pickup merge logic (MCP + Realtime) | Data consistency | 🔥 CRITIQUE | P0 |
| WebSocket reconnection | Offline resilience | ⚠️ HAUTE | P1 |
| Subscription cleanup | Memory leaks | ⚠️ MOYENNE | P2 |

---

### Tests Manquants

```javascript
// ❌ NOT TESTED: Realtime pickup INSERT event
describe('Realtime Pickup Updates', () => {
  it('should add new pickup when INSERT event received', async () => {
    const { result } = renderHook(() => useDashboard());

    // Simulate Supabase INSERT event
    act(() => {
      window.__supabase_realtime_trigger({
        eventType: 'INSERT',
        new: {
          id: 'pickup_123',
          scheduled_time: '2025-11-04T15:00:00Z',
          status: 'pending'
        }
      });
    });

    await waitFor(() => {
      expect(result.current.pickups).toContainEqual(
        expect.objectContaining({ id: 'pickup_123' })
      );
    });
  });

  // ❌ NOT TESTED: Realtime pickup UPDATE event
  it('should update existing pickup when UPDATE event received', async () => {
    const { result } = renderHook(() => useDashboard());

    // Simulate UPDATE event
    act(() => {
      window.__supabase_realtime_trigger({
        eventType: 'UPDATE',
        new: {
          id: 'existing_pickup',
          status: 'completed'  // Changed from 'in_progress'
        }
      });
    });

    await waitFor(() => {
      const pickup = result.current.pickups.find(p => p.id === 'existing_pickup');
      expect(pickup.status).toBe('completed');
    });
  });

  // ❌ NOT TESTED: Realtime pickup DELETE event
  it('should remove pickup when DELETE event received', async () => {
    const { result } = renderHook(() => useDashboard());

    act(() => {
      window.__supabase_realtime_trigger({
        eventType: 'DELETE',
        old: { id: 'deleted_pickup' }
      });
    });

    await waitFor(() => {
      expect(result.current.pickups).not.toContainEqual(
        expect.objectContaining({ id: 'deleted_pickup' })
      );
    });
  });

  // ❌ NOT TESTED: Merge conflict (MCP says pending, Realtime says completed)
  it('should prioritize realtime data over MCP data', async () => {
    const { result } = renderHook(() => useDashboard());

    // MCP returns pickup with status="pending"
    result.current.fetchPickups();  // Sets pickup to "pending"

    // Realtime says "completed"
    act(() => {
      window.__supabase_realtime_trigger({
        eventType: 'UPDATE',
        new: { id: 'pickup_123', status: 'completed' }
      });
    });

    // Realtime should win
    const pickup = result.current.pickups.find(p => p.id === 'pickup_123');
    expect(pickup.status).toBe('completed');
  });

  // ❌ NOT TESTED: WebSocket reconnection after disconnect
  it('should reconnect WebSocket after network failure', async () => {
    const { result } = renderHook(() => useDashboard());

    // Simulate network disconnection
    act(() => {
      window.__supabase_realtime_disconnect();
    });

    await waitFor(() => {
      expect(result.current.realtimeStatus).toBe('disconnected');
    });

    // Simulate network reconnection
    act(() => {
      window.__supabase_realtime_reconnect();
    });

    await waitFor(() => {
      expect(result.current.realtimeStatus).toBe('connected');
    });
  });
});

// ❌ NOT TESTED: Emergency alert real-time
describe('Emergency Alerts', () => {
  it('should display emergency alert when received via realtime', async () => {
    render(<Dashboard />);

    // Simulate emergency alert
    act(() => {
      window.__supabase_realtime_trigger({
        table: 'emergencies',
        eventType: 'INSERT',
        new: {
          id: 'emergency_123',
          type: 'illness',
          context: 'Sophie est malade'
        }
      });
    });

    expect(await screen.findByText(/Sophie est malade/)).toBeInTheDocument();
  });

  it('should auto-dismiss alert after 30 seconds', async () => {
    jest.useFakeTimers();
    render(<Dashboard />);

    act(() => {
      window.__supabase_realtime_trigger({
        table: 'emergencies',
        eventType: 'INSERT',
        new: { id: 'emergency_123', type: 'late' }
      });
    });

    expect(screen.getByRole('alert')).toBeInTheDocument();

    // Fast-forward 30 seconds
    act(() => {
      jest.advanceTimersByTime(30000);
    });

    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});
```

**Nombre de tests real-time manquants**: **~15 tests**

---

## Gap #5: Frontend Components (100% Gap) ⚠️

### Criticité: HAUTE
**Impact**: Bugs UI, mauvaise UX, régression visuelle

### Composants Non Testés: 12/12

| Component | Lines | Complexity | Test Priority |
|-----------|-------|------------|---------------|
| dashboard.jsx | 248 | HIGH | P1 |
| auth-screen.jsx | 355 | HIGH | P0 |
| pickup-card.jsx | 76 | MEDIUM | P2 |
| emergency-alert.jsx | 42 | LOW | P2 |
| monitoring/dashboard.jsx | 208 | MEDIUM | P2 |
| monitoring/* (other) | 273 | LOW | P3 |

---

### Tests Manquants

```javascript
// ❌ NOT TESTED: Auth screen - signup flow
describe('AuthScreen - Signup', () => {
  it('should show error when passwords do not match', async () => {
    render(<AuthScreen />);

    fireEvent.change(screen.getByLabelText(/Email/), {
      target: { value: 'test@test.com' }
    });
    fireEvent.change(screen.getByLabelText(/Mot de passe/), {
      target: { value: 'password123' }
    });
    fireEvent.change(screen.getByLabelText(/Confirmer/), {
      target: { value: 'different' }  // MISMATCH
    });

    fireEvent.click(screen.getByRole('button', { name: /S'inscrire/ }));

    expect(await screen.findByText(/ne correspondent pas/)).toBeInTheDocument();
  });

  it('should show error when password is too short', async () => {
    render(<AuthScreen />);

    fireEvent.change(screen.getByLabelText(/Mot de passe/), {
      target: { value: '123' }  // Too short
    });

    fireEvent.click(screen.getByRole('button', { name: /S'inscrire/ }));

    expect(await screen.findByText(/au moins 6 caractères/)).toBeInTheDocument();
  });

  it('should call signup tool and navigate on success', async () => {
    const mockCallTool = jest.fn().mockResolvedValue({
      _meta: { session: { access_token: 'token123' } }
    });
    window.openai = { callTool: mockCallTool };

    const mockOnAuthenticated = jest.fn();
    render(<AuthScreen onAuthenticated={mockOnAuthenticated} />);

    // Fill form
    fireEvent.change(screen.getByLabelText(/Email/), {
      target: { value: 'test@test.com' }
    });
    fireEvent.change(screen.getByLabelText(/Mot de passe/), {
      target: { value: 'password123' }
    });
    fireEvent.change(screen.getByLabelText(/Confirmer/), {
      target: { value: 'password123' }
    });

    fireEvent.click(screen.getByRole('button', { name: /S'inscrire/ }));

    await waitFor(() => {
      expect(mockCallTool).toHaveBeenCalledWith('auth-signup', expect.objectContaining({
        email: 'test@test.com',
        password: 'password123'
      }));
    });

    expect(mockOnAuthenticated).toHaveBeenCalled();
  });
});

// ❌ NOT TESTED: Dashboard - filter logic
describe('Dashboard - Filters', () => {
  it('should show all pickups when filter is "all"', () => {
    const pickups = [
      { id: '1', scheduled_time: futureTime(10) },
      { id: '2', scheduled_time: futureTime(60) },
      { id: '3', scheduled_time: futureTime(120) }
    ];

    const { result } = renderHook(() => useDashboard({ pickups, filter: 'all' }));

    expect(result.current.filteredPickups).toHaveLength(3);
  });

  it('should show only next 30min pickups when filter is "next_30min"', () => {
    const pickups = [
      { id: '1', scheduled_time: futureTime(10) },   // Within 30min
      { id: '2', scheduled_time: futureTime(60) },   // After 30min
      { id: '3', scheduled_time: futureTime(120) }   // After 30min
    ];

    const { result } = renderHook(() => useDashboard({ pickups, filter: 'next_30min' }));

    expect(result.current.filteredPickups).toHaveLength(1);
    expect(result.current.filteredPickups[0].id).toBe('1');
  });

  it('should show only delayed pickups when filter is "delays"', () => {
    const pickups = [
      { id: '1', delay: 0 },
      { id: '2', delay: 10 },  // Delayed
      { id: '3', delay: 5 }    // Delayed
    ];

    const { result } = renderHook(() => useDashboard({ pickups, filter: 'delays' }));

    expect(result.current.filteredPickups).toHaveLength(2);
  });
});

// ❌ NOT TESTED: PickupCard - time calculations
describe('PickupCard - Time Display', () => {
  it('should show "En retard" when pickup time is past', () => {
    const pickup = {
      scheduled_time: pastTime(10)  // 10 minutes ago
    };

    render(<PickupCard pickup={pickup} currentTime={new Date()} />);

    expect(screen.getByText(/En retard/)).toBeInTheDocument();
  });

  it('should show "Maintenant" when pickup time is now', () => {
    const now = new Date();
    const pickup = {
      scheduled_time: now.toISOString()
    };

    render(<PickupCard pickup={pickup} currentTime={now} />);

    expect(screen.getByText(/Maintenant/)).toBeInTheDocument();
  });

  it('should show "Dans X min" when pickup is soon', () => {
    const pickup = {
      scheduled_time: futureTime(15)  // In 15 minutes
    };

    render(<PickupCard pickup={pickup} currentTime={new Date()} />);

    expect(screen.getByText(/Dans 15 min/)).toBeInTheDocument();
  });

  it('should show correct color based on urgency', () => {
    const urgentPickup = {
      scheduled_time: futureTime(3),  // < 5 min
      status: 'pending'
    };

    const { container } = render(<PickupCard pickup={urgentPickup} currentTime={new Date()} />);

    expect(container.firstChild).toHaveClass('status-red');
  });
});
```

**Nombre de tests frontend manquants**: **~35 tests**

---

## Résumé des Gaps Critiques

### Par Priorité

| Priority | Component | Tests Manquants | Effort (jours) | Risk |
|----------|-----------|----------------|----------------|------|
| **P0** | Auth + RLS | ~60 | 5 | 🔥 CRITIQUE |
| **P0** | Business Logic Handlers | ~30 | 3 | 🔥 CRITIQUE |
| **P0** | Database Triggers | ~8 | 1 | 🔥 CRITIQUE |
| **P1** | Real-time Features | ~15 | 2 | ⚠️ HAUTE |
| **P1** | Frontend Critical | ~20 | 2 | ⚠️ HAUTE |
| **P2** | Frontend Secondary | ~15 | 1.5 | ⚠️ MOYENNE |
| **P3** | Monitoring | ~10 | 1 | ⚠️ BASSE |

**Total tests à écrire**: **~158 tests critiques**
**Effort total**: **~15.5 jours-personne**

---

### Par Catégorie de Risque

| Catégorie | Gap | Impact Business | Priority |
|-----------|-----|-----------------|----------|
| **Sécurité** | 100% | Data breach, accès non autorisé | P0 |
| **Données** | 100% | Corruption, incohérence | P0 |
| **Fonctionnalités** | 100% | Bugs, workflows cassés | P0 |
| **UX** | 100% | Interface cassée, stale data | P1 |
| **Observabilité** | 70% | Bugs non détectés | P2 |

---

**Rapport généré le**: 2025-11-04
**Action requise**: Commencer Phase 1 (tests sécurité) immédiatement
