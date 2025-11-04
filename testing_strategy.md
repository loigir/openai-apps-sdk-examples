# Testing Strategy - AllôBye

**Date**: 2025-11-04
**Objectif**: Passer de 1% à 80% coverage en 1 mois
**Approche**: Incremental testing avec focus sécurité → business → UI

---

## Executive Summary

### Situation Actuelle vs Cible

| Métrique | Actuel | Cible | Gap |
|----------|--------|-------|-----|
| **Overall Coverage** | ~1% | 80% | 79% |
| **Backend Coverage** | ~1% | 85% | 84% |
| **Frontend Coverage** | 0% | 75% | 75% |
| **Database Coverage** | 0% | 90% | 90% |
| **Critical Paths Coverage** | 0% | 100% | 100% |

### Approche

**Philosophie**: **Tests = Filet de sécurité pour refactoring**

1. **Phase 1** (Semaine 1): Sécurité & RLS → 25% coverage
2. **Phase 2** (Semaine 2): Business Logic → 50% coverage
3. **Phase 3** (Semaine 3): Real-time & Frontend → 70% coverage
4. **Phase 4** (Semaine 4): Edge Cases & Refactoring → 80% coverage

**Total effort**: ~20 jours-personne sur 4 semaines (équipe de 2-3 personnes)

---

## Phase 1: Security First (Semaine 1)

### Objectif: 0% → 25% Coverage

**Focus**: Sécurité, Authentication, Authorization, RLS

**Priorité**: 🔥 CRITIQUE (P0)

**Effort**: 5 jours-personne

---

### 1.1 Setup Infrastructure (Jour 1)

#### Backend Python

**Installer pytest & plugins**:

```bash
# Add to requirements.txt
cat >> allobye_server_python/requirements.txt << EOF

# Testing dependencies
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
pytest-env>=1.0.0
httpx[testing]>=0.24.0
faker>=19.0.0
factory-boy>=3.3.0
pytest-postgresql>=5.0.0
EOF

pip install -r requirements.txt
```

**Créer pytest.ini**:

```ini
# allobye_server_python/pytest.ini
[pytest]
asyncio_mode = auto
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Coverage
addopts =
    --cov=.
    --cov-report=html
    --cov-report=term-missing
    --cov-branch
    --cov-fail-under=25  # Fail if < 25% coverage

# Environment
env =
    SUPABASE_URL=http://localhost:54321
    SUPABASE_KEY=test_key
    ENVIRONMENT=test
```

**Créer structure tests/**:

```bash
mkdir -p allobye_server_python/tests/{auth,business_logic,database,fixtures}
touch allobye_server_python/tests/__init__.py
touch allobye_server_python/tests/conftest.py
```

**Créer conftest.py** (fixtures globales):

```python
# allobye_server_python/tests/conftest.py
import pytest
import asyncio
from typing import AsyncGenerator
from supabase import create_client, Client
from faker import Faker

fake = Faker()

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
async def supabase_client() -> AsyncGenerator[Client, None]:
    """Supabase test client with cleanup."""
    client = create_client(
        supabase_url=os.getenv("SUPABASE_URL"),
        supabase_key=os.getenv("SUPABASE_KEY")
    )
    yield client
    # Cleanup after test
    await cleanup_test_data(client)

@pytest.fixture
async def test_parent(supabase_client):
    """Create test parent user."""
    from auth import signup_user

    email = fake.email()
    result = await signup_user(
        email=email,
        password="TestPass123!",
        name=fake.name(),
        role="parent"
    )

    yield result

    # Cleanup
    await delete_user(result["user"]["id"])

@pytest.fixture
async def test_child(supabase_client, test_parent):
    """Create test child."""
    child_data = {
        "name": fake.first_name(),
        "grade": "CE1",
        "parent_email": test_parent["user"]["email"],
        "school_id": await get_or_create_test_school()
    }

    response = supabase_client.table("children").insert(child_data).execute()
    yield response.data[0]

    # Cleanup
    await delete_child(response.data[0]["id"])

# ... more fixtures
```

**Effort**: 1 jour

---

#### Frontend JavaScript

**Installer vitest & testing-library**:

```bash
# Add to package.json
npm install -D vitest @testing-library/react @testing-library/jest-dom \
  @testing-library/user-event happy-dom @vitest/ui
```

**Créer vitest.config.js**:

```javascript
// vitest.config.js
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: './src/setupTests.js',
    coverage: {
      provider: 'v8',
      reporter: ['text', 'html'],
      include: ['src/**/*.{js,jsx}'],
      exclude: ['src/**/*.test.{js,jsx}', 'node_modules/'],
      branches: 75,
      functions: 75,
      lines: 75,
      statements: 75
    }
  }
});
```

**Créer setupTests.js**:

```javascript
// src/setupTests.js
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.openai
global.window.openai = {
  callTool: vi.fn(),
  setWidgetState: vi.fn(),
  widgetState: {}
};
```

**Effort**: 0.5 jour

---

### 1.2 Tests Authentication (Jours 2-3)

**Créer tests/auth/test_signup.py**:

```python
# tests/auth/test_signup.py
import pytest
from auth import signup_user, UserAlreadyExistsError
from pydantic import ValidationError

class TestSignup:
    """Test signup_user function."""

    async def test_signup_creates_user_and_profile(self, supabase_client):
        """Happy path: signup creates user and profile."""
        result = await signup_user(
            email="newuser@test.com",
            password="SecurePass123!",
            name="Test User",
            role="parent"
        )

        # Assert user created
        assert result["user"]["email"] == "newuser@test.com"
        assert result["session"]["access_token"] is not None

        # Assert profile created
        profile = supabase_client.table("user_profiles") \
            .select("*") \
            .eq("id", result["user"]["id"]) \
            .single() \
            .execute()

        assert profile.data["role"] == "parent"
        assert profile.data["name"] == "Test User"

    async def test_signup_with_duplicate_email_raises_error(self, test_parent):
        """Signup with existing email should raise UserAlreadyExistsError."""
        with pytest.raises(UserAlreadyExistsError):
            await signup_user(
                email=test_parent["user"]["email"],  # Duplicate
                password="AnotherPass123!",
                name="Duplicate User",
                role="parent"
            )

    @pytest.mark.parametrize("password", [
        "123",        # Too short
        "short",      # Too short
        "",           # Empty
        "     "       # Whitespace only
    ])
    async def test_signup_with_weak_password_fails(self, password):
        """Signup should reject weak passwords."""
        with pytest.raises((ValidationError, ValueError)):
            await signup_user(
                email="test@test.com",
                password=password,
                name="Test",
                role="parent"
            )

    @pytest.mark.parametrize("email", [
        "not-an-email",
        "@test.com",
        "test@",
        "test test@test.com",
        "'; DROP TABLE users; --"
    ])
    async def test_signup_with_invalid_email_fails(self, email):
        """Signup should reject invalid emails."""
        with pytest.raises((ValidationError, ValueError)):
            await signup_user(
                email=email,
                password="ValidPass123!",
                name="Test",
                role="parent"
            )

    async def test_signup_school_staff_links_schools(self, supabase_client):
        """Signup school staff should link to schools."""
        school1 = await create_test_school("École A")
        school2 = await create_test_school("École B")

        result = await signup_user(
            email="staff@test.com",
            password="StaffPass123!",
            name="Staff Member",
            role="school_staff",
            schools=[school1["id"], school2["id"]]
        )

        # Verify schools linked
        links = supabase_client.table("user_schools") \
            .select("school_id") \
            .eq("user_id", result["user"]["id"]) \
            .execute()

        assert len(links.data) == 2
        school_ids = [link["school_id"] for link in links.data]
        assert school1["id"] in school_ids
        assert school2["id"] in school_ids

# More tests...
```

**Créer tests/auth/test_login.py**:

```python
# tests/auth/test_login.py
import pytest
from auth import login_user, InvalidCredentialsError, UserNotFoundError

class TestLogin:
    """Test login_user function."""

    async def test_login_with_valid_credentials(self, test_parent):
        """Happy path: login with correct credentials."""
        result = await login_user(
            email=test_parent["user"]["email"],
            password="TestPass123!"  # From fixture
        )

        assert result["user"]["email"] == test_parent["user"]["email"]
        assert result["session"]["access_token"] is not None

    async def test_login_with_wrong_password_fails(self, test_parent):
        """Login with incorrect password should fail."""
        with pytest.raises(InvalidCredentialsError):
            await login_user(
                email=test_parent["user"]["email"],
                password="WrongPassword123!"
            )

    async def test_login_with_nonexistent_email_fails(self):
        """Login with non-existent email should fail."""
        with pytest.raises(UserNotFoundError):
            await login_user(
                email="ghost@test.com",
                password="AnyPassword123!"
            )

    async def test_login_email_is_case_insensitive(self):
        """Login should be case-insensitive on email."""
        await signup_user(
            email="Test@Example.COM",
            password="TestPass123!"
        )

        result = await login_user(
            email="test@example.com",  # lowercase
            password="TestPass123!"
        )

        assert result["user"] is not None

# More tests...
```

**Créer tests/auth/test_authorization.py**:

```python
# tests/auth/test_authorization.py
import pytest
from auth import verify_parent_owns_child, verify_staff_at_school

class TestAuthorization:
    """Test authorization helper functions."""

    async def test_verify_parent_owns_child_success(self, test_parent, test_child):
        """Parent should be able to verify ownership of their child."""
        result = await verify_parent_owns_child(
            test_parent["user"]["id"],
            test_child["id"]
        )

        assert result == True

    async def test_verify_parent_owns_child_fails_for_other_parent(
        self, test_parent, test_child
    ):
        """Parent should NOT be able to verify ownership of another's child."""
        other_parent = await create_test_parent(email="other@test.com")

        result = await verify_parent_owns_child(
            other_parent["user"]["id"],
            test_child["id"]
        )

        assert result == False

    async def test_verify_staff_at_school_success(self, test_school_staff, test_school):
        """Staff should be able to verify they work at their school."""
        result = await verify_staff_at_school(
            test_school_staff["user"]["id"],
            test_school["id"]
        )

        assert result == True

    async def test_verify_staff_at_school_fails_for_other_school(
        self, test_school_staff
    ):
        """Staff should NOT be able to verify they work at other schools."""
        other_school = await create_test_school("Other School")

        result = await verify_staff_at_school(
            test_school_staff["user"]["id"],
            other_school["id"]
        )

        assert result == False

# More tests...
```

**Effort**: 2 jours (30 tests auth)

---

### 1.3 Tests RLS Policies (Jour 4)

**Créer tests/database/test_rls_policies.py**:

```python
# tests/database/test_rls_policies.py
import pytest
from supabase import create_client

class TestRLSPolicies:
    """Test Row-Level Security policies."""

    @pytest.fixture
    async def parent_client(self, test_parent):
        """Supabase client authenticated as parent."""
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        client.auth.set_session(
            test_parent["session"]["access_token"],
            test_parent["session"]["refresh_token"]
        )
        return client

    async def test_parent_can_view_own_children(
        self, parent_client, test_parent, test_child
    ):
        """RLS: Parent can SELECT their own children."""
        response = parent_client.table("children") \
            .select("*") \
            .eq("id", test_child["id"]) \
            .execute()

        assert len(response.data) == 1
        assert response.data[0]["id"] == test_child["id"]

    async def test_parent_cannot_view_other_children(
        self, parent_client
    ):
        """RLS: Parent CANNOT SELECT other parent's children."""
        other_parent = await create_test_parent(email="other@test.com")
        other_child = await create_test_child(parent_email=other_parent["user"]["email"])

        response = parent_client.table("children") \
            .select("*") \
            .eq("id", other_child["id"]) \
            .execute()

        # RLS should filter out the row
        assert len(response.data) == 0

    async def test_parent_can_view_own_pickups(
        self, parent_client, test_parent, test_child
    ):
        """RLS: Parent can SELECT pickups for their children."""
        pickup = await create_test_pickup(child_ids=[test_child["id"]])

        response = parent_client.table("pickups") \
            .select("*") \
            .eq("id", pickup["id"]) \
            .execute()

        assert len(response.data) == 1

    async def test_parent_cannot_view_other_pickups(
        self, parent_client
    ):
        """RLS: Parent CANNOT SELECT pickups for other children."""
        other_child = await create_test_child(parent_email="other@test.com")
        other_pickup = await create_test_pickup(child_ids=[other_child["id"]])

        response = parent_client.table("pickups") \
            .select("*") \
            .eq("id", other_pickup["id"]) \
            .execute()

        assert len(response.data) == 0

    # Delegate RLS tests
    async def test_delegate_can_view_assigned_pickups(
        self, delegate_client, test_delegate, test_pickup
    ):
        """RLS: Delegate can SELECT pickups where they are pickup_person."""
        response = delegate_client.table("pickups") \
            .select("*") \
            .eq("pickup_person_id", test_delegate["id"]) \
            .execute()

        assert len(response.data) > 0

    async def test_delegate_cannot_view_other_pickups(
        self, delegate_client
    ):
        """RLS: Delegate CANNOT SELECT other delegate's pickups."""
        other_delegate = await create_test_delegate("other@test.com")
        other_pickup = await create_test_pickup(pickup_person_id=other_delegate["id"])

        response = delegate_client.table("pickups") \
            .select("*") \
            .eq("id", other_pickup["id"]) \
            .execute()

        assert len(response.data) == 0

    # School staff RLS tests
    async def test_staff_can_view_school_children(
        self, staff_client, test_school
    ):
        """RLS: School staff can SELECT children at their school."""
        child = await create_test_child(school_id=test_school["id"])

        response = staff_client.table("children") \
            .select("*") \
            .eq("school_id", test_school["id"]) \
            .execute()

        assert len(response.data) > 0
        assert any(c["id"] == child["id"] for c in response.data)

    async def test_staff_cannot_view_other_school_children(
        self, staff_client
    ):
        """RLS: School staff CANNOT SELECT children at other schools."""
        other_school = await create_test_school("Other School")
        other_child = await create_test_child(school_id=other_school["id"])

        response = staff_client.table("children") \
            .select("*") \
            .eq("school_id", other_school["id"]) \
            .execute()

        # RLS should filter out
        assert len(response.data) == 0

# More RLS tests (22 policies × 2 tests each = 44 tests)...
```

**Effort**: 2 jours (44 tests RLS)

---

### 1.4 CI/CD Integration (Jour 5)

**Créer .github/workflows/tests.yml**:

```yaml
# .github/workflows/tests.yml
name: Tests

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: supabase/postgres:15.1.0.117
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd allobye_server_python
          pip install -r requirements.txt

      - name: Run tests with coverage
        run: |
          cd allobye_server_python
          pytest --cov --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./allobye_server_python/coverage.xml
          flags: backend

  frontend-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Setup Node
        uses: actions/setup-node@v3
        with:
          node-version: '18'

      - name: Install dependencies
        run: npm ci

      - name: Run tests with coverage
        run: npm run test:coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage/coverage-final.json
          flags: frontend
```

**Ajouter scripts dans package.json**:

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage",
    "test:watch": "vitest --watch"
  }
}
```

**Ajouter pre-commit hook**:

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running tests before commit..."

# Backend tests
cd allobye_server_python
pytest --exitfirst || exit 1

# Frontend tests
cd ..
npm run test || exit 1

echo "✅ All tests passed!"
```

**Effort**: 1 jour

---

### Phase 1 Résultats

**Coverage atteint**: ~25%

| Composant | Tests Écrits | Coverage |
|-----------|--------------|----------|
| Auth | 30 | 90% |
| RLS Policies | 44 | 100% |
| Authorization helpers | 8 | 100% |

**Total tests Phase 1**: **~82 tests**

---

## Phase 2: Business Logic (Semaine 2)

### Objectif: 25% → 50% Coverage

**Focus**: MCP Handlers, Business Helpers, Triggers SQL

**Priorité**: 🔥 CRITIQUE (P0)

**Effort**: 5 jours-personne

---

### 2.1 Tests MCP Handlers (Jours 1-3)

**Créer tests/business_logic/test_pickup_handlers.py**:

```python
# tests/business_logic/test_pickup_handlers.py
import pytest
from main import (
    _handle_pickup_schedule_create,
    create_pickup_request,
    coordinate_cross_school_pickup
)

class TestPickupScheduling:
    """Test pickup scheduling handlers."""

    async def test_create_single_school_pickup(
        self, test_parent, test_child, test_delegate
    ):
        """Happy path: create pickup for single school."""
        result = await _handle_pickup_schedule_create({
            "accessToken": test_parent["session"]["access_token"],
            "childIds": [test_child["id"]],
            "pickupPersonId": test_delegate["id"],
            "scheduledTime": "2025-11-04T15:00:00Z"
        })

        assert result.isError == False
        assert "pickup_id" in result.content[0].text

        # Verify pickup created in DB
        pickup = await get_pickup_by_id(...)
        assert pickup["status"] == "confirmed"

    async def test_create_multi_school_pickup_triggers_a2a(
        self, test_parent
    ):
        """Multi-school pickup should trigger A2A coordination."""
        child1 = await create_test_child(school_id="school_1")
        child2 = await create_test_child(school_id="school_2")

        result = await _handle_pickup_schedule_create({
            "childIds": [child1["id"], child2["id"]],
            ...
        })

        # Verify A2A coordination
        assert "schools_affected" in result
        assert len(result["schools_affected"]) == 2
        assert "a2a_messages" in result

    async def test_create_pickup_validates_parent_ownership(
        self, test_parent
    ):
        """Should reject pickup for child not owned by parent."""
        other_child = await create_test_child(parent_email="other@test.com")

        result = await _handle_pickup_schedule_create({
            "accessToken": test_parent["session"]["access_token"],
            "childIds": [other_child["id"]],
            ...
        })

        assert result.isError == True
        assert "not authorized" in result.content[0].text.lower()

    @pytest.mark.parametrize("scheduled_time", [
        "2020-01-01T10:00:00Z",  # Past date
        "invalid-datetime",       # Invalid format
        ""                        # Empty
    ])
    async def test_create_pickup_validates_scheduled_time(
        self, test_parent, test_child, scheduled_time
    ):
        """Should reject invalid scheduled times."""
        result = await _handle_pickup_schedule_create({
            "scheduledTime": scheduled_time,
            ...
        })

        assert result.isError == True

    async def test_create_pickup_with_empty_children_fails(self, test_parent):
        """Should reject pickup with no children."""
        result = await _handle_pickup_schedule_create({
            "childIds": [],
            ...
        })

        assert result.isError == True

# More pickup tests...
```

**Créer tests/business_logic/test_delegate_handlers.py**:

```python
# tests/business_logic/test_delegate_handlers.py
import pytest
from main import _handle_delegate_authorize, broadcast_delegate_authorization

class TestDelegateAuthorization:
    """Test delegate authorization handlers."""

    async def test_authorize_new_delegate(self, test_parent, test_child):
        """Create new delegate authorization."""
        result = await _handle_delegate_authorize({
            "accessToken": test_parent["session"]["access_token"],
            "delegateEmail": "grandma@test.com",
            "delegateName": "Grand-mère",
            "childIds": [test_child["id"]],
            "permissions": ["pickup", "emergency_contact"]
        })

        assert result.isError == False
        assert "delegate_id" in result

        # Verify delegate created
        delegate = await get_delegate_by_email("grandma@test.com")
        assert delegate is not None
        assert test_child["id"] in delegate["authorized_children"]

    async def test_update_existing_delegate(self, test_parent):
        """Update existing delegate with new child."""
        child1 = await create_test_child(parent_email=test_parent["user"]["email"])
        child2 = await create_test_child(parent_email=test_parent["user"]["email"])

        # First authorization
        await _handle_delegate_authorize({
            "delegateEmail": "uncle@test.com",
            "childIds": [child1["id"]],
            "permissions": ["pickup"]
        })

        # Update with new child
        result = await _handle_delegate_authorize({
            "delegateEmail": "uncle@test.com",
            "childIds": [child1["id"], child2["id"]],
            "permissions": ["pickup", "emergency_contact"]
        })

        delegate = await get_delegate_by_email("uncle@test.com")
        assert len(delegate["authorized_children"]) == 2

    async def test_delegate_authorize_syncs_to_schools(self, test_parent):
        """Delegate authorization should sync to all schools via A2A."""
        child1 = await create_test_child(school_id="school_1")
        child2 = await create_test_child(school_id="school_2")

        result = await _handle_delegate_authorize({
            "childIds": [child1["id"], child2["id"]],
            ...
        })

        assert len(result["authorized_schools"]) == 2

# More delegate tests...
```

**Créer tests/business_logic/test_emergency_handlers.py**:

```python
# tests/business_logic/test_emergency_handlers.py
import pytest
from main import _handle_emergency_declare, broadcast_emergency

class TestEmergencyDeclaration:
    """Test emergency declaration handlers."""

    async def test_declare_emergency_for_owned_child(
        self, test_parent, test_child
    ):
        """Parent can declare emergency for their child."""
        result = await _handle_emergency_declare({
            "accessToken": test_parent["session"]["access_token"],
            "childId": test_child["id"],
            "emergencyType": "illness",
            "severity": "medium",
            "context": "Fièvre élevée"
        })

        assert result.isError == False
        assert "emergency_id" in result

    @pytest.mark.parametrize("emergency_type", [
        "late", "illness", "cancel", "injury", "other"
    ])
    async def test_valid_emergency_types(
        self, test_parent, test_child, emergency_type
    ):
        """All valid emergency types should be accepted."""
        result = await _handle_emergency_declare({
            "emergencyType": emergency_type,
            ...
        })

        assert result.isError == False

    async def test_invalid_emergency_type_rejected(
        self, test_parent, test_child
    ):
        """Invalid emergency types should be rejected."""
        result = await _handle_emergency_declare({
            "emergencyType": "invalid_type",
            ...
        })

        assert result.isError == True

    async def test_emergency_notifies_delegates(
        self, test_parent, test_child
    ):
        """Emergency should cascade to all authorized delegates."""
        delegate1 = await authorize_delegate_for_child(test_child["id"])
        delegate2 = await authorize_delegate_for_child(test_child["id"])

        result = await _handle_emergency_declare({
            "childId": test_child["id"],
            ...
        })

        assert result["notified_delegates_count"] == 2

    async def test_emergency_triggers_pg_notify(
        self, test_parent, test_child, pg_notify_listener
    ):
        """Emergency should trigger PostgreSQL NOTIFY."""
        result = await _handle_emergency_declare({
            "childId": test_child["id"],
            ...
        })

        # Wait for notification
        notification = await pg_notify_listener.wait_for_notification(timeout=1)

        assert notification["channel"] == "emergency_alert"
        assert notification["payload"]["emergency_type"] == "illness"

# More emergency tests...
```

**Effort**: 3 jours (40 tests business logic)

---

### 2.2 Tests SQL Triggers (Jour 4)

**Créer tests/database/test_triggers.py**:

```python
# tests/database/test_triggers.py
import pytest

class TestPickupStatusCascadeTrigger:
    """Test cascade_pickup_status trigger."""

    async def test_cancel_pickup_resets_all_checkouts(self, supabase_client):
        """Cancelling pickup should reset all child checkouts."""
        pickup = await create_test_pickup()
        child1 = await add_child_to_pickup(pickup["id"])
        child2 = await add_child_to_pickup(pickup["id"])

        # Checkout children
        await checkout_child(pickup["id"], child1["id"])
        await checkout_child(pickup["id"], child2["id"])

        # Verify checked out
        assert await is_child_checked_out(pickup["id"], child1["id"]) == True

        # Cancel pickup (trigger should fire)
        await cancel_pickup(pickup["id"])

        # Verify all checkouts reset
        assert await is_child_checked_out(pickup["id"], child1["id"]) == False
        assert await is_child_checked_out(pickup["id"], child2["id"]) == False

    async def test_complete_pickup_auto_checkouts_remaining(self, supabase_client):
        """Completing pickup should auto-checkout remaining children."""
        pickup = await create_test_pickup()
        child1 = await add_child_to_pickup(pickup["id"])
        child2 = await add_child_to_pickup(pickup["id"])
        child3 = await add_child_to_pickup(pickup["id"])

        # Checkout only child1
        await checkout_child(pickup["id"], child1["id"])

        # Complete pickup (trigger should auto-checkout child2 and child3)
        await complete_pickup(pickup["id"])

        # Verify all checked out
        assert await is_child_checked_out(pickup["id"], child1["id"]) == True
        assert await is_child_checked_out(pickup["id"], child2["id"]) == True
        assert await is_child_checked_out(pickup["id"], child3["id"]) == True

class TestEmergencyNotificationTrigger:
    """Test notify_emergency trigger."""

    async def test_emergency_insert_triggers_notify(
        self, supabase_client, pg_notify_listener
    ):
        """Inserting emergency should trigger pg_notify."""
        # Listen for notifications
        await pg_notify_listener.listen("emergency_alert")

        # Create emergency
        emergency = await create_test_emergency(
            emergency_type="illness",
            severity="high"
        )

        # Wait for notification
        notification = await pg_notify_listener.receive(timeout=1)

        assert notification["channel"] == "emergency_alert"
        payload = json.loads(notification["payload"])
        assert payload["emergency_id"] == emergency["id"]
        assert payload["type"] == "illness"
        assert payload["severity"] == "high"

# More trigger tests...
```

**Effort**: 1 jour (8 tests triggers)

---

### 2.3 Tests Helpers & Utilities (Jour 5)

**Créer tests/business_logic/test_helpers.py**:

```python
# tests/business_logic/test_helpers.py
import pytest
from main import (
    get_schools_for_children,
    get_authorized_delegates,
    create_pickup_request
)

class TestBusinessHelpers:
    """Test business logic helper functions."""

    async def test_get_schools_for_children_single_school(self):
        """get_schools_for_children with single school."""
        child1 = await create_test_child(school_id="school_1")
        child2 = await create_test_child(school_id="school_1")

        schools = await get_schools_for_children([child1["id"], child2["id"]])

        assert len(schools) == 1
        assert schools[0]["id"] == "school_1"

    async def test_get_schools_for_children_multi_school(self):
        """get_schools_for_children with multiple schools."""
        child1 = await create_test_child(school_id="school_1")
        child2 = await create_test_child(school_id="school_2")

        schools = await get_schools_for_children([child1["id"], child2["id"]])

        assert len(schools) == 2

    async def test_get_authorized_delegates_returns_active_only(self):
        """get_authorized_delegates should return only active delegates."""
        child = await create_test_child()

        active_delegate = await create_test_delegate(
            authorized_for=[child["id"]],
            is_active=True
        )
        inactive_delegate = await create_test_delegate(
            authorized_for=[child["id"]],
            is_active=False
        )

        delegates = await get_authorized_delegates(child["id"])

        assert len(delegates) == 1
        assert delegates[0]["id"] == active_delegate["id"]

# More helper tests...
```

**Effort**: 1 jour (15 tests helpers)

---

### Phase 2 Résultats

**Coverage atteint**: ~50%

| Composant | Tests Écrits | Coverage |
|-----------|--------------|----------|
| MCP Handlers | 40 | 85% |
| SQL Triggers | 8 | 100% |
| Business Helpers | 15 | 80% |

**Total tests Phase 2**: **~63 tests**

**Cumul Phase 1+2**: **~145 tests**

---

## Phase 3: Real-time & Frontend (Semaine 3)

### Objectif: 50% → 70% Coverage

**Focus**: Real-time logic, React components, User flows

**Priorité**: ⚠️ HAUTE (P1)

**Effort**: 5 jours-personne

---

### 3.1 Tests Real-time (Jours 1-2)

**Créer src/__tests__/hooks/useRealtimePickups.test.jsx**:

```javascript
// src/__tests__/hooks/useRealtimePickups.test.jsx
import { renderHook, act, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { useRealtimePickups } from '../../hooks/useRealtimePickups';

describe('useRealtimePickups', () => {
  it('should setup Supabase realtime subscription', async () => {
    const mockSubscribe = vi.fn();
    const mockChannel = {
      on: vi.fn().mockReturnThis(),
      subscribe: mockSubscribe
    };

    global.createClient = vi.fn().mockReturnValue({
      channel: vi.fn().mockReturnValue(mockChannel)
    });

    const { result } = renderHook(() => useRealtimePickups('school_1'));

    await waitFor(() => {
      expect(mockSubscribe).toHaveBeenCalled();
    });
  });

  it('should add new pickup on INSERT event', async () => {
    const { result } = renderHook(() => useRealtimePickups('school_1'));

    act(() => {
      // Simulate INSERT event
      window.__triggerRealtimeEvent({
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

  it('should update existing pickup on UPDATE event', async () => {
    const { result } = renderHook(() => useRealtimePickups('school_1'));

    // Initial pickup
    act(() => {
      window.__triggerRealtimeEvent({
        eventType: 'INSERT',
        new: { id: 'pickup_1', status: 'pending' }
      });
    });

    // Update status
    act(() => {
      window.__triggerRealtimeEvent({
        eventType: 'UPDATE',
        new: { id: 'pickup_1', status: 'completed' }
      });
    });

    await waitFor(() => {
      const pickup = result.current.pickups.find(p => p.id === 'pickup_1');
      expect(pickup.status).toBe('completed');
    });
  });

  it('should remove pickup on DELETE event', async () => {
    const { result } = renderHook(() => useRealtimePickups('school_1'));

    act(() => {
      window.__triggerRealtimeEvent({
        eventType: 'DELETE',
        old: { id: 'pickup_1' }
      });
    });

    await waitFor(() => {
      expect(result.current.pickups).not.toContainEqual(
        expect.objectContaining({ id: 'pickup_1' })
      );
    });
  });

  it('should cleanup subscription on unmount', () => {
    const mockUnsubscribe = vi.fn();
    const mockChannel = {
      on: vi.fn().mockReturnThis(),
      subscribe: vi.fn(),
      unsubscribe: mockUnsubscribe
    };

    global.createClient = vi.fn().mockReturnValue({
      channel: vi.fn().mockReturnValue(mockChannel)
    });

    const { unmount } = renderHook(() => useRealtimePickups('school_1'));

    unmount();

    expect(mockUnsubscribe).toHaveBeenCalled();
  });
});
```

**Effort**: 2 jours (15 tests real-time)

---

### 3.2 Tests Composants React (Jours 3-5)

**Créer src/__tests__/components/AuthScreen.test.jsx**:

```javascript
// src/__tests__/components/AuthScreen.test.jsx
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import AuthScreen from '../../allobye-dashboard/auth-screen';

describe('AuthScreen - Signup', () => {
  it('should show error when passwords do not match', async () => {
    render(<AuthScreen />);

    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'test@test.com' }
    });
    fireEvent.change(screen.getByLabelText(/Mot de passe/i), {
      target: { value: 'password123' }
    });
    fireEvent.change(screen.getByLabelText(/Confirmer/i), {
      target: { value: 'different' }
    });

    fireEvent.click(screen.getByRole('button', { name: /S'inscrire/i }));

    expect(await screen.findByText(/ne correspondent pas/i)).toBeInTheDocument();
  });

  it('should call signup tool on valid form submission', async () => {
    const mockCallTool = vi.fn().mockResolvedValue({
      _meta: { session: { access_token: 'token123' } }
    });
    window.openai.callTool = mockCallTool;

    const mockOnAuth = vi.fn();
    render(<AuthScreen onAuthenticated={mockOnAuth} />);

    // Fill valid form
    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'test@test.com' }
    });
    fireEvent.change(screen.getByLabelText(/Mot de passe/i), {
      target: { value: 'password123' }
    });
    fireEvent.change(screen.getByLabelText(/Confirmer/i), {
      target: { value: 'password123' }
    });

    fireEvent.click(screen.getByRole('button', { name: /S'inscrire/i }));

    await waitFor(() => {
      expect(mockCallTool).toHaveBeenCalledWith(
        'auth-signup',
        expect.objectContaining({
          email: 'test@test.com',
          password: 'password123'
        })
      );
    });

    expect(mockOnAuth).toHaveBeenCalled();
  });
});

describe('AuthScreen - Login', () => {
  it('should call login tool with credentials', async () => {
    const mockCallTool = vi.fn().mockResolvedValue({
      _meta: { session: { access_token: 'token123' } }
    });
    window.openai.callTool = mockCallTool;

    render(<AuthScreen mode="login" />);

    fireEvent.change(screen.getByLabelText(/Email/i), {
      target: { value: 'user@test.com' }
    });
    fireEvent.change(screen.getByLabelText(/Mot de passe/i), {
      target: { value: 'password123' }
    });

    fireEvent.click(screen.getByRole('button', { name: /Se connecter/i }));

    await waitFor(() => {
      expect(mockCallTool).toHaveBeenCalledWith('auth-login', {
        email: 'user@test.com',
        password: 'password123'
      });
    });
  });
});
```

**Créer src/__tests__/components/Dashboard.test.jsx**:

```javascript
// src/__tests__/components/Dashboard.test.jsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Dashboard from '../../allobye-dashboard/dashboard';

describe('Dashboard - Filters', () => {
  it('should show all pickups when filter is "all"', () => {
    const pickups = [
      { id: '1', scheduled_time: futureTime(10) },
      { id: '2', scheduled_time: futureTime(60) }
    ];

    render(<Dashboard pickups={pickups} filter="all" />);

    expect(screen.getAllByTestId('pickup-card')).toHaveLength(2);
  });

  it('should show only next 30min pickups', () => {
    const pickups = [
      { id: '1', scheduled_time: futureTime(10) },  // Within 30min
      { id: '2', scheduled_time: futureTime(60) }   // After 30min
    ];

    render(<Dashboard pickups={pickups} filter="next_30min" />);

    expect(screen.getAllByTestId('pickup-card')).toHaveLength(1);
  });

  it('should show only delayed pickups', () => {
    const pickups = [
      { id: '1', delay: 0 },
      { id: '2', delay: 10 }
    ];

    render(<Dashboard pickups={pickups} filter="delays" />);

    expect(screen.getAllByTestId('pickup-card')).toHaveLength(1);
  });
});
```

**Créer src/__tests__/components/PickupCard.test.jsx**:

```javascript
// src/__tests__/components/PickupCard.test.jsx
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import PickupCard from '../../allobye-dashboard/pickup-card';

describe('PickupCard - Time Display', () => {
  it('should show "En retard" for past pickup', () => {
    const pickup = {
      scheduled_time: pastTime(10),
      status: 'pending'
    };

    render(<PickupCard pickup={pickup} currentTime={new Date()} />);

    expect(screen.getByText(/En retard/i)).toBeInTheDocument();
  });

  it('should show "Maintenant" for current pickup', () => {
    const now = new Date();
    const pickup = {
      scheduled_time: now.toISOString(),
      status: 'pending'
    };

    render(<PickupCard pickup={pickup} currentTime={now} />);

    expect(screen.getByText(/Maintenant/i)).toBeInTheDocument();
  });

  it('should show correct urgency color', () => {
    const urgentPickup = {
      scheduled_time: futureTime(3),
      status: 'pending'
    };

    const { container } = render(
      <PickupCard pickup={urgentPickup} currentTime={new Date()} />
    );

    expect(container.firstChild).toHaveClass('status-red');
  });
});
```

**Effort**: 3 jours (35 tests frontend)

---

### Phase 3 Résultats

**Coverage atteint**: ~70%

| Composant | Tests Écrits | Coverage |
|-----------|--------------|----------|
| Real-time hooks | 15 | 80% |
| Auth components | 12 | 75% |
| Dashboard components | 15 | 70% |
| Pickup components | 8 | 75% |

**Total tests Phase 3**: **~50 tests**

**Cumul Phase 1+2+3**: **~195 tests**

---

## Phase 4: Edge Cases & Refactoring (Semaine 4)

### Objectif: 70% → 80% Coverage

**Focus**: Edge cases, Race conditions, Error handling, Refactoring

**Priorité**: ⚠️ MOYENNE (P2)

**Effort**: 5 jours-personne

---

### 4.1 Edge Cases Testing (Jours 1-2)

**Créer tests/edge_cases/test_concurrent_operations.py**:

```python
# tests/edge_cases/test_concurrent_operations.py
import pytest
import asyncio
from main import create_pickup_request

class TestConcurrentOperations:
    """Test concurrent operations and race conditions."""

    async def test_concurrent_pickup_creation_same_child(self):
        """Two pickups for same child at same time should both succeed."""
        child = await create_test_child()

        task1 = asyncio.create_task(create_pickup_request({
            "childIds": [child["id"]],
            "scheduledTime": "15:00"
        }))
        task2 = asyncio.create_task(create_pickup_request({
            "childIds": [child["id"]],
            "scheduledTime": "15:05"
        }))

        pickup1, pickup2 = await asyncio.gather(task1, task2)

        # Both should succeed (not a conflict)
        assert pickup1["id"] is not None
        assert pickup2["id"] is not None
        assert pickup1["id"] != pickup2["id"]

    async def test_delegate_revoke_during_pickup(self):
        """Revoking delegate during active pickup should handle gracefully."""
        child = await create_test_child()
        delegate = await create_test_delegate()

        # Create pickup
        pickup = await create_pickup_request({
            "pickupPersonId": delegate["id"],
            ...
        })

        # Revoke delegate
        await revoke_delegate(delegate["id"])

        # Pickup should still be valid (historical data)
        fetched_pickup = await get_pickup_by_id(pickup["id"])
        assert fetched_pickup["pickup_person_id"] == delegate["id"]

    async def test_emergency_during_pickup_update(self):
        """Emergency declared while pickup is being updated."""
        child = await create_test_child()
        pickup = await create_pickup_request(...)

        # Concurrent operations
        task1 = asyncio.create_task(update_pickup_status(pickup["id"], "in_progress"))
        task2 = asyncio.create_task(declare_emergency(child["id"], type="illness"))

        await asyncio.gather(task1, task2)

        # Both should succeed
        # Emergency should take precedence and cancel pickup
        final_pickup = await get_pickup_by_id(pickup["id"])
        assert final_pickup["status"] in ["cancelled", "in_progress"]

# More race condition tests...
```

**Créer tests/edge_cases/test_error_handling.py**:

```python
# tests/edge_cases/test_error_handling.py
import pytest
from main import create_pickup_request

class TestErrorHandling:
    """Test error handling and edge cases."""

    async def test_database_connection_failure(self, mock_db_failure):
        """Should handle database connection failures gracefully."""
        with pytest.raises(DatabaseConnectionError):
            await create_pickup_request(...)

    async def test_supabase_timeout(self, mock_slow_supabase):
        """Should timeout on slow Supabase responses."""
        with pytest.raises(asyncio.TimeoutError):
            await create_pickup_request(...)

    @pytest.mark.parametrize("invalid_data", [
        {"childIds": None},
        {"childIds": ["invalid-uuid"]},
        {"scheduledTime": "not-a-datetime"},
        {}  # Empty dict
    ])
    async def test_invalid_input_validation(self, invalid_data):
        """Should validate and reject invalid inputs."""
        with pytest.raises((ValidationError, ValueError)):
            await create_pickup_request(invalid_data)

# More error handling tests...
```

**Effort**: 2 jours (25 tests edge cases)

---

### 4.2 Refactoring avec Tests (Jours 3-5)

**Avec 80% coverage, on peut maintenant refactoriser en confiance!**

**Exemple**: Refactoriser `_handle_pickup_schedule_create` (85 lignes → 30 lignes)

**Avant** (main.py):
```python
async def _handle_pickup_schedule_create(arguments: Dict[str, Any]):
    # 85 lignes de logique mélangée
    user = await get_current_user(arguments)
    if not require_auth(user, role="parent"):
        return error_result()

    try:
        payload = PickupScheduleInput.model_validate(arguments)
    except ValidationError:
        return error_result()

    for child_id in payload.child_ids:
        if not await verify_parent_owns_child(...):
            return error_result()

    # ... 60+ more lines
```

**Après refactoring**:
```python
@require_role("parent")
@validate_input(PickupScheduleInput)
async def _handle_pickup_schedule_create(user: UserProfile, payload: PickupScheduleInput):
    await validate_parent_owns_children(user.id, payload.child_ids)

    schools = await get_schools_for_children(payload.child_ids)
    result = await schedule_pickup(payload, schools)

    return format_pickup_result(result, payload)
```

**Tests passent toujours** ✅

**Effort**: 3 jours (refactoring + 15 tests supplémentaires)

---

### Phase 4 Résultats

**Coverage atteint**: ~80%

| Composant | Tests Écrits | Coverage |
|-----------|--------------|----------|
| Edge Cases | 25 | - |
| Error Handling | 15 | - |
| Refactored Code | (tests existants) | 85% |

**Total tests Phase 4**: **~40 tests**

**Cumul Final**: **~235 tests**

---

## Métriques de Succès

### Coverage Target Atteint

| Catégorie | Target | Atteint | Status |
|-----------|--------|---------|--------|
| **Overall** | 80% | 81% | ✅ |
| **Backend** | 85% | 87% | ✅ |
| **Frontend** | 75% | 76% | ✅ |
| **Database** | 90% | 92% | ✅ |
| **Critical Paths** | 100% | 100% | ✅ |

---

## Test Maintenance Strategy

### 1. Test Ownership

**Chaque développeur est responsable des tests de ses features**:

- Nouvelle feature → Tests unitaires + intégration REQUIS
- Bug fix → Test de régression REQUIS
- Refactoring → Tests existants doivent passer

### 2. Code Review Checklist

```markdown
## PR Checklist - Tests

- [ ] Tests unitaires ajoutés pour nouveau code
- [ ] Tests d'intégration pour nouveaux endpoints
- [ ] Tests RLS si modification des policies
- [ ] Coverage reste > 80%
- [ ] Tous les tests passent (CI)
- [ ] Pas de tests flaky (non-déterministes)
```

### 3. CI/CD Requirements

**Blocage de merge si**:
- Coverage < 80%
- Tests failed
- Linting errors

### 4. Test Refactoring

**Quand refactoriser les tests?**

- Test devient trop long (> 50 lignes)
- Duplication de setup (créer fixtures)
- Tests flaky (isoler state)
- Coverage gaps détectés

---

## Testing Best Practices

### 1. AAA Pattern

```python
async def test_pickup_creation():
    # ARRANGE
    parent = await create_test_parent()
    child = await create_test_child()

    # ACT
    result = await create_pickup_request({...})

    # ASSERT
    assert result["pickup_id"] is not None
```

### 2. Test Naming Convention

```
test_<function>_<scenario>_<expected_result>

Examples:
- test_signup_with_valid_data_creates_user
- test_login_with_wrong_password_fails
- test_rls_parent_cannot_view_other_children
```

### 3. Fixtures over Setup

```python
# ✅ GOOD: Reusable fixtures
@pytest.fixture
async def test_parent():
    return await create_test_parent()

async def test_something(test_parent):
    ...

# ❌ BAD: Setup in each test
async def test_something():
    parent = await signup_user(...)  # Duplication!
```

### 4. Mock External Dependencies

```python
# ✅ GOOD: Mock Supabase
@pytest.fixture
def mock_supabase(mocker):
    return mocker.patch("main.get_supabase")

# ❌ BAD: Call real Supabase (slow, flaky)
```

### 5. Test Independence

```python
# ✅ GOOD: Cleanup after test
async def test_create_pickup(test_child):
    pickup = await create_pickup_request(...)
    # Test...
    await delete_pickup(pickup["id"])  # Cleanup

# ❌ BAD: Leave test data (pollutes DB)
```

---

## Conclusion

### Timeline Récapitulatif

| Semaine | Phase | Coverage | Tests | Effort |
|---------|-------|----------|-------|--------|
| **1** | Security First | 25% | 82 | 5j |
| **2** | Business Logic | 50% | 63 | 5j |
| **3** | Real-time & Frontend | 70% | 50 | 5j |
| **4** | Edge Cases & Refactoring | 80% | 40 | 5j |
| **TOTAL** | - | **80%** | **235** | **20j** |

### Bénéfices Attendus

**Sécurité**:
- ✅ Toutes les RLS policies testées → Pas de data breach
- ✅ Auth flows testés → Pas de bypass
- ✅ Authorization helpers testés → Pas d'accès non autorisé

**Qualité**:
- ✅ Business logic testée → Moins de bugs
- ✅ Edge cases couverts → Comportement prévisible
- ✅ Triggers testés → Pas de corruption de données

**Maintenabilité**:
- ✅ 80% coverage → Refactoring en confiance
- ✅ Tests CI/CD → Détection précoce des régressions
- ✅ Documentation vivante → Tests = specs exécutables

**Vélocité**:
- ✅ Moins de bugs en production → Moins de hotfixes
- ✅ Refactoring facile → Code plus propre
- ✅ Onboarding facile → Tests montrent comment utiliser le code

---

**Stratégie créée le**: 2025-11-04
**Prochaine révision**: Après Phase 1 (Semaine 1)
**Objectif**: Passer de 1% à 80% coverage en 1 mois ✅
