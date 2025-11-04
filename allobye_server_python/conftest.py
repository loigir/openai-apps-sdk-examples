"""
Shared pytest fixtures for AllôBye MCP Server tests.

Provides common fixtures for mocking Supabase, creating test users,
and setting up test data.
"""

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock
from uuid import uuid4

import pytest


# Mock Supabase Response Classes
class MockSupabaseResponse:
    """Mock Supabase response."""

    def __init__(self, data: Any = None, error: Any = None):
        self.data = data
        self.error = error


class MockSupabaseTable:
    """Mock Supabase table."""

    def __init__(self, table_name: str, data_store: Dict):
        self.table_name = table_name
        self.data_store = data_store
        self._query = {}
        self._filters = []

    def select(self, columns: str = "*"):
        self._query["select"] = columns
        return self

    def insert(self, data: Dict):
        if self.table_name not in self.data_store:
            self.data_store[self.table_name] = []
        self.data_store[self.table_name].append(data)
        return self

    def update(self, data: Dict):
        self._query["update"] = data
        return self

    def delete(self):
        self._query["delete"] = True
        return self

    def eq(self, column: str, value: Any):
        self._filters.append(("eq", column, value))
        return self

    def in_(self, column: str, values: List[Any]):
        self._filters.append(("in", column, values))
        return self

    def gte(self, column: str, value: Any):
        self._filters.append(("gte", column, value))
        return self

    def lte(self, column: str, value: Any):
        self._filters.append(("lte", column, value))
        return self

    def order(self, column: str):
        self._query["order"] = column
        return self

    def single(self):
        self._query["single"] = True
        return self

    def upsert(self, data: Dict, on_conflict: str = None):
        if self.table_name not in self.data_store:
            self.data_store[self.table_name] = []
        self.data_store[self.table_name].append(data)
        return self

    def execute(self):
        """Execute the query and return mock response."""
        data = []

        if self.table_name in self.data_store:
            data = self.data_store[self.table_name]

            # Apply filters
            for filter_type, column, value in self._filters:
                if filter_type == "eq":
                    data = [d for d in data if d.get(column) == value]
                elif filter_type == "in":
                    data = [d for d in data if d.get(column) in value]

        if self._query.get("single"):
            data = data[0] if data else None

        return MockSupabaseResponse(data=data)


class MockSupabaseAuth:
    """Mock Supabase auth client."""

    def __init__(self, users_store: Dict):
        self.users_store = users_store
        self.current_session = None

    def sign_up(self, credentials: Dict):
        """Mock signup."""
        email = credentials["email"]
        password = credentials["password"]

        # Check if user exists
        if email in self.users_store:
            raise Exception("User already registered")

        user_id = str(uuid4())
        user_obj = MagicMock()
        user_obj.id = user_id
        user_obj.email = email
        user_obj.email_confirmed_at = None
        user_obj.created_at = datetime.now().isoformat()

        session_obj = MagicMock()
        session_obj.access_token = f"mock_token_{user_id}"
        session_obj.refresh_token = f"mock_refresh_{user_id}"
        session_obj.expires_at = (datetime.now() + timedelta(hours=1)).isoformat()

        self.users_store[email] = {
            "user": {
                "id": user_id,
                "email": email,
                "email_confirmed_at": None,
                "created_at": datetime.now().isoformat(),
            },
            "password": password,
            "session": {
                "access_token": session_obj.access_token,
                "refresh_token": session_obj.refresh_token,
                "expires_at": session_obj.expires_at,
            },
        }

        result = MagicMock()
        result.user = user_obj
        result.session = session_obj
        return result

    def sign_in_with_password(self, credentials: Dict):
        """Mock login."""
        email = credentials["email"]
        password = credentials["password"]

        if email not in self.users_store:
            raise Exception("Invalid login credentials")

        stored = self.users_store[email]
        if stored["password"] != password:
            raise Exception("Invalid login credentials")

        user_data = stored["user"]
        session_data = stored["session"]

        self.current_session = session_data

        user_obj = MagicMock()
        user_obj.id = user_data["id"]
        user_obj.email = user_data["email"]
        user_obj.email_confirmed_at = user_data.get("email_confirmed_at")
        user_obj.created_at = user_data.get("created_at")

        session_obj = MagicMock()
        session_obj.access_token = session_data["access_token"]
        session_obj.refresh_token = session_data["refresh_token"]
        session_obj.expires_at = session_data.get("expires_at")

        result = MagicMock()
        result.user = user_obj
        result.session = session_obj
        return result

    def sign_out(self):
        """Mock logout."""
        self.current_session = None
        return MockSupabaseResponse(data=None)

    def set_session(self, access_token: str, refresh_token: str):
        """Mock set session."""
        pass

    def get_user(self, access_token: str):
        """Mock get user."""
        # Find user by access token
        for email, data in self.users_store.items():
            if data["session"]["access_token"] == access_token:
                user_data = data["user"]
                user_obj = MagicMock()
                user_obj.id = user_data["id"]
                user_obj.email = user_data["email"]
                user_obj.email_confirmed_at = user_data.get("email_confirmed_at")
                user_obj.created_at = user_data.get("created_at")

                result = MagicMock()
                result.user = user_obj
                return result
        raise Exception("Invalid token")

    def get_session(self):
        """Mock get session."""
        return self.current_session

    def refresh_session(self, refresh_token: str):
        """Mock refresh session."""
        # Find user by refresh token
        for email, data in self.users_store.items():
            if data["session"]["refresh_token"] == refresh_token:
                user_id = data["user"]["id"]
                new_session = {
                    "access_token": f"mock_token_refreshed_{user_id}",
                    "refresh_token": f"mock_refresh_refreshed_{user_id}",
                    "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
                }
                data["session"] = new_session

                user_data = data["user"]
                user_obj = MagicMock()
                user_obj.id = user_data["id"]
                user_obj.email = user_data["email"]

                session_obj = MagicMock()
                session_obj.access_token = new_session["access_token"]
                session_obj.refresh_token = new_session["refresh_token"]
                session_obj.expires_at = new_session["expires_at"]

                result = MagicMock()
                result.session = session_obj
                result.user = user_obj
                return result
        raise Exception("Invalid refresh token")

    def reset_password_email(self, email: str):
        """Mock password reset."""
        return MockSupabaseResponse(data=None)

    def verify_otp(self, data: Dict):
        """Mock OTP verification."""
        return MockSupabaseResponse(data=None)


class MockSupabaseClient:
    """Mock Supabase client."""

    def __init__(self):
        self.data_store = {}
        self.users_store = {}
        self.auth = MockSupabaseAuth(self.users_store)

    def table(self, table_name: str):
        """Get mock table."""
        return MockSupabaseTable(table_name, self.data_store)


# Fixtures

@pytest.fixture
def mock_supabase():
    """Create a mock Supabase client."""
    return MockSupabaseClient()


@pytest.fixture
def mock_supabase_patch(monkeypatch, mock_supabase):
    """Patch Supabase client creation to use mock."""
    def mock_get_supabase():
        return mock_supabase

    def mock_get_supabase_admin():
        return mock_supabase

    monkeypatch.setattr("main.get_supabase", mock_get_supabase)
    monkeypatch.setattr("auth.get_supabase_client", mock_get_supabase)
    monkeypatch.setattr("auth.get_supabase_admin", mock_get_supabase_admin)

    return mock_supabase


@pytest.fixture
def test_user_data():
    """Create test user data."""
    user_id = str(uuid4())
    return {
        "id": user_id,
        "email": "test@example.com",
        "password": "TestPassword123!",
        "name": "Test User",
        "role": "parent",
        "schools": [],
        "children": ["child_1", "child_2"],
    }


@pytest.fixture
def test_staff_data():
    """Create test staff data."""
    user_id = str(uuid4())
    return {
        "id": user_id,
        "email": "staff@example.com",
        "password": "StaffPassword123!",
        "name": "Staff User",
        "role": "school_staff",
        "schools": ["school_1"],
        "children": [],
    }


@pytest.fixture
async def authenticated_user(mock_supabase_patch, test_user_data):
    """Create an authenticated test user."""
    from auth import signup_user

    result = await signup_user(
        email=test_user_data["email"],
        password=test_user_data["password"],
        name=test_user_data["name"],
        role=test_user_data["role"],
    )

    # Add to mock data store
    mock_supabase_patch.data_store["user_profiles"] = [{
        "id": result["user"]["id"],
        "email": test_user_data["email"],
        "name": test_user_data["name"],
        "role": test_user_data["role"],
        "email_verified": False,
    }]

    # Add parent-child relationships
    mock_supabase_patch.data_store["parent_children"] = [
        {"parent_id": result["user"]["id"], "child_id": child_id}
        for child_id in test_user_data["children"]
    ]

    return {
        "user_id": result["user"]["id"],
        "email": test_user_data["email"],
        "access_token": result["session"]["access_token"],
        "refresh_token": result["session"]["refresh_token"],
        "profile": test_user_data,
    }


@pytest.fixture
async def authenticated_staff(mock_supabase_patch, test_staff_data):
    """Create an authenticated staff user."""
    from auth import signup_user

    result = await signup_user(
        email=test_staff_data["email"],
        password=test_staff_data["password"],
        name=test_staff_data["name"],
        role=test_staff_data["role"],
        schools=test_staff_data["schools"],
    )

    # Add to mock data store
    mock_supabase_patch.data_store["user_profiles"] = [{
        "id": result["user"]["id"],
        "email": test_staff_data["email"],
        "name": test_staff_data["name"],
        "role": test_staff_data["role"],
        "email_verified": False,
    }]

    # Add staff-school relationships
    mock_supabase_patch.data_store["user_schools"] = [
        {"user_id": result["user"]["id"], "school_id": school_id}
        for school_id in test_staff_data["schools"]
    ]

    return {
        "user_id": result["user"]["id"],
        "email": test_staff_data["email"],
        "access_token": result["session"]["access_token"],
        "refresh_token": result["session"]["refresh_token"],
        "profile": test_staff_data,
    }


@pytest.fixture
def mock_children_data(mock_supabase_patch):
    """Create mock children data in database."""
    mock_supabase_patch.data_store["children"] = [
        {
            "id": "child_1",
            "name": "Sophie Tremblay",
            "school_id": "school_1",
            "schools": {"id": "school_1", "name": "École Primaire Exemple"},
        },
        {
            "id": "child_2",
            "name": "Thomas Gagnon",
            "school_id": "school_1",
            "schools": {"id": "school_1", "name": "École Primaire Exemple"},
        },
    ]

    return mock_supabase_patch.data_store["children"]


@pytest.fixture
def mock_schools_data(mock_supabase_patch):
    """Create mock schools data in database."""
    mock_supabase_patch.data_store["schools"] = [
        {
            "id": "school_1",
            "name": "École Primaire Exemple",
            "address": "123 Rue Principale, Montréal, QC",
        },
    ]

    return mock_supabase_patch.data_store["schools"]


@pytest.fixture
def mock_delegates_data(mock_supabase_patch):
    """Create mock delegates data in database."""
    mock_supabase_patch.data_store["delegates"] = [
        {
            "id": "delegate_1",
            "email": "grandmaman@example.com",
            "name": "Grand-maman",
            "permissions": ["pickup"],
        },
    ]

    return mock_supabase_patch.data_store["delegates"]


@pytest.fixture
def clear_rate_limits():
    """Clear rate limiting stores before each test."""
    from auth import _rate_limit_store, _failed_login_store, _account_lockout_store

    _rate_limit_store.clear()
    _failed_login_store.clear()
    _account_lockout_store.clear()

    yield

    # Clean up after test
    _rate_limit_store.clear()
    _failed_login_store.clear()
    _account_lockout_store.clear()


@pytest.fixture
def freeze_time():
    """Freeze time for testing time-dependent functions."""
    frozen_time = datetime.now()

    class FrozenTime:
        def __init__(self):
            self.frozen = frozen_time

        def tick(self, **kwargs):
            """Advance time by timedelta."""
            self.frozen += timedelta(**kwargs)
            return self.frozen

        def now(self):
            """Get current frozen time."""
            return self.frozen

    return FrozenTime()
