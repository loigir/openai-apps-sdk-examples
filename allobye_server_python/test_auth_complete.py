"""
Comprehensive authentication test suite.

Tests all authentication flows including:
- Signup with validation
- Login with rate limiting and lockout
- Session management and token refresh
- Profile management
- Authorization checks
- Security features (password validation, rate limiting, etc.)
"""

import pytest
from datetime import datetime, timedelta

from auth import (
    signup_user,
    login_user,
    logout_user,
    reset_password_request,
    validate_session,
    refresh_session,
    get_user_profile,
    update_user_profile,
    verify_parent_owns_child,
    verify_staff_at_school,
    link_child_to_parent,
    validate_password_strength,
    check_rate_limit,
    check_account_lockout,
    record_failed_login,
    clear_failed_login_attempts,
    should_refresh_token,
    SECURITY_CONFIG,
    WeakPasswordError,
    RateLimitExceededError,
    AccountLockedError,
    InvalidCredentialsError,
    SessionExpiredError,
    UserAlreadyExistsError,
    AuthenticationError,
)


# ═══════════════════════════════════════════════════════════════
# SIGNUP TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.unit
class TestSignup:
    """Test user signup functionality."""

    async def test_signup_parent_success(self, mock_supabase_patch, clear_rate_limits):
        """Test successful parent signup."""
        result = await signup_user(
            email="parent@example.com",
            password="ParentPassword123!",
            name="Parent User",
            role="parent",
        )

        assert result["user"]["email"] == "parent@example.com"
        assert result["session"]["access_token"] is not None
        assert result["mfa_context"]["enabled"] is False

    async def test_signup_staff_success(self, mock_supabase_patch, clear_rate_limits):
        """Test successful school staff signup."""
        result = await signup_user(
            email="staff@school.com",
            password="StaffPassword123!",
            name="Staff User",
            role="school_staff",
            schools=["school_1", "school_2"],
        )

        assert result["user"]["email"] == "staff@school.com"
        assert result["session"]["access_token"] is not None

    async def test_signup_weak_password_short(self, mock_supabase_patch, clear_rate_limits):
        """Test signup rejects short password."""
        with pytest.raises(WeakPasswordError) as exc_info:
            await signup_user(
                email="test@example.com",
                password="Short1!",
                name="Test User",
            )

        assert "12 characters" in str(exc_info.value)

    async def test_signup_weak_password_no_uppercase(self, mock_supabase_patch, clear_rate_limits):
        """Test signup rejects password without uppercase."""
        with pytest.raises(WeakPasswordError) as exc_info:
            await signup_user(
                email="test@example.com",
                password="nouppercase123!",
                name="Test User",
            )

        assert "uppercase" in str(exc_info.value).lower()

    async def test_signup_weak_password_no_digit(self, mock_supabase_patch, clear_rate_limits):
        """Test signup rejects password without digit."""
        with pytest.raises(WeakPasswordError) as exc_info:
            await signup_user(
                email="test@example.com",
                password="NoDigitsHere!",
                name="Test User",
            )

        assert "digit" in str(exc_info.value).lower()

    async def test_signup_weak_password_common(self, mock_supabase_patch, clear_rate_limits):
        """Test signup rejects common password."""
        with pytest.raises(WeakPasswordError) as exc_info:
            await signup_user(
                email="test@example.com",
                password="Password123!",
                name="Test User",
            )

        assert "common" in str(exc_info.value).lower()

    async def test_signup_rate_limiting(self, mock_supabase_patch, clear_rate_limits):
        """Test signup rate limiting."""
        email = "ratelimit@example.com"

        # Exhaust rate limit
        for i in range(SECURITY_CONFIG.max_signup_attempts):
            try:
                await signup_user(
                    email=f"test{i}@example.com",
                    password="ValidPassword123!",
                    name="Test User",
                )
            except:
                pass

        # Next attempt should fail with rate limit
        with pytest.raises(RateLimitExceededError):
            check_rate_limit(email, "signup")


# ═══════════════════════════════════════════════════════════════
# LOGIN TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.unit
class TestLogin:
    """Test user login functionality."""

    async def test_login_success(self, authenticated_user, clear_rate_limits):
        """Test successful login."""
        result = await login_user(
            email=authenticated_user["email"],
            password=authenticated_user["profile"]["password"],
        )

        assert result["user"]["email"] == authenticated_user["email"]
        assert result["session"]["access_token"] is not None
        assert result["profile"]["role"] == "parent"

    async def test_login_wrong_password(self, authenticated_user, clear_rate_limits):
        """Test login with wrong password."""
        with pytest.raises(InvalidCredentialsError):
            await login_user(
                email=authenticated_user["email"],
                password="WrongPassword123!",
            )

    async def test_login_nonexistent_user(self, mock_supabase_patch, clear_rate_limits):
        """Test login with non-existent user."""
        with pytest.raises((InvalidCredentialsError, AuthenticationError)):
            await login_user(
                email="nonexistent@example.com",
                password="SomePassword123!",
            )

    async def test_login_rate_limiting(self, authenticated_user, clear_rate_limits):
        """Test login rate limiting after multiple failures."""
        email = authenticated_user["email"]

        # Exhaust rate limit with wrong password
        for i in range(SECURITY_CONFIG.max_login_attempts):
            try:
                await login_user(email=email, password="WrongPassword123!")
            except:
                pass

        # Next attempt should hit rate limit
        with pytest.raises(RateLimitExceededError):
            check_rate_limit(email, "login")

    async def test_login_account_lockout(self, authenticated_user, clear_rate_limits):
        """Test account lockout after multiple failed attempts."""
        email = authenticated_user["email"]

        # Record multiple failed attempts
        for i in range(SECURITY_CONFIG.max_failed_attempts_before_lockout):
            record_failed_login(email)

        # Account should be locked
        with pytest.raises(AccountLockedError):
            check_account_lockout(email)

    async def test_login_clears_failed_attempts_on_success(
        self, authenticated_user, clear_rate_limits
    ):
        """Test successful login clears failed attempt counter."""
        email = authenticated_user["email"]

        # Record some failed attempts
        record_failed_login(email)
        record_failed_login(email)

        # Successful login should clear them
        await login_user(
            email=email,
            password=authenticated_user["profile"]["password"],
        )

        # Failed attempts should be cleared (no exception)
        check_account_lockout(email)


# ═══════════════════════════════════════════════════════════════
# SESSION MANAGEMENT TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.unit
class TestSessionManagement:
    """Test session management functionality."""

    async def test_validate_session_success(self, authenticated_user):
        """Test validating a valid session."""
        user_profile = await validate_session(authenticated_user["access_token"])

        assert user_profile is not None
        assert user_profile.email == authenticated_user["email"]
        assert user_profile.role == "parent"

    async def test_validate_session_invalid_token(self, mock_supabase_patch):
        """Test validating an invalid token."""
        with pytest.raises((SessionExpiredError, AuthenticationError)):
            await validate_session("invalid_token_12345")

    async def test_logout_success(self, authenticated_user):
        """Test successful logout."""
        result = await logout_user(authenticated_user["access_token"])

        assert result["success"] is True

    async def test_refresh_session_success(self, authenticated_user):
        """Test token refresh."""
        result = await refresh_session(authenticated_user["refresh_token"])

        assert result["session"]["access_token"] is not None
        assert result["session"]["refresh_token"] is not None
        assert result["user"]["id"] is not None

    async def test_refresh_session_invalid_token(self, mock_supabase_patch):
        """Test refresh with invalid token."""
        with pytest.raises((SessionExpiredError, AuthenticationError)):
            await refresh_session("invalid_refresh_token")

    async def test_should_refresh_token_near_expiry(self):
        """Test token refresh recommendation near expiry."""
        # Token expiring in 5 minutes
        expires_at = (datetime.now() + timedelta(minutes=5)).isoformat()

        should_refresh = should_refresh_token(expires_at)

        assert should_refresh is True

    async def test_should_refresh_token_far_expiry(self):
        """Test token refresh not needed when far from expiry."""
        # Token expiring in 1 hour
        expires_at = (datetime.now() + timedelta(hours=1)).isoformat()

        should_refresh = should_refresh_token(expires_at)

        assert should_refresh is False


# ═══════════════════════════════════════════════════════════════
# PROFILE MANAGEMENT TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.unit
class TestProfileManagement:
    """Test user profile management."""

    async def test_get_user_profile(self, authenticated_user, mock_supabase_patch):
        """Test getting user profile."""
        # Add profile to mock store
        mock_supabase_patch.data_store["user_profiles"] = [{
            "id": authenticated_user["user_id"],
            "email": authenticated_user["email"],
            "name": authenticated_user["profile"]["name"],
            "role": "parent",
            "email_verified": False,
        }]

        profile = await get_user_profile(authenticated_user["user_id"])

        assert profile["email"] == authenticated_user["email"]
        assert profile["role"] == "parent"

    async def test_update_user_profile_name(
        self, authenticated_user, mock_supabase_patch
    ):
        """Test updating user profile name."""
        # Add profile to mock store
        mock_supabase_patch.data_store["user_profiles"] = [{
            "id": authenticated_user["user_id"],
            "email": authenticated_user["email"],
            "name": "Old Name",
            "role": "parent",
        }]

        updated = await update_user_profile(
            user_id=authenticated_user["user_id"],
            name="New Name",
        )

        assert updated["name"] == "New Name"

    async def test_update_user_profile_schools(
        self, authenticated_staff, mock_supabase_patch
    ):
        """Test updating school staff schools."""
        # Add profile to mock store
        mock_supabase_patch.data_store["user_profiles"] = [{
            "id": authenticated_staff["user_id"],
            "email": authenticated_staff["email"],
            "name": authenticated_staff["profile"]["name"],
            "role": "school_staff",
        }]

        updated = await update_user_profile(
            user_id=authenticated_staff["user_id"],
            schools=["school_1", "school_2", "school_3"],
        )

        assert len(updated["schools"]) == 3


# ═══════════════════════════════════════════════════════════════
# AUTHORIZATION TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.auth
@pytest.mark.unit
class TestAuthorization:
    """Test authorization checks."""

    async def test_verify_parent_owns_child_success(
        self, authenticated_user, mock_supabase_patch
    ):
        """Test parent ownership verification."""
        # Add parent-child relationship
        mock_supabase_patch.data_store["parent_children"] = [{
            "id": "1",
            "parent_id": authenticated_user["user_id"],
            "child_id": "child_1",
        }]

        owns = await verify_parent_owns_child(
            authenticated_user["user_id"],
            "child_1",
        )

        assert owns is True

    async def test_verify_parent_owns_child_failure(
        self, authenticated_user, mock_supabase_patch
    ):
        """Test parent doesn't own child."""
        # Empty relationships
        mock_supabase_patch.data_store["parent_children"] = []

        owns = await verify_parent_owns_child(
            authenticated_user["user_id"],
            "other_child",
        )

        assert owns is False

    async def test_verify_staff_at_school_success(
        self, authenticated_staff, mock_supabase_patch
    ):
        """Test staff-school verification."""
        # Add staff-school relationship
        mock_supabase_patch.data_store["user_schools"] = [{
            "id": "1",
            "user_id": authenticated_staff["user_id"],
            "school_id": "school_1",
        }]

        is_staff = await verify_staff_at_school(
            authenticated_staff["user_id"],
            "school_1",
        )

        assert is_staff is True

    async def test_verify_staff_at_school_failure(
        self, authenticated_staff, mock_supabase_patch
    ):
        """Test staff not at school."""
        # Empty relationships
        mock_supabase_patch.data_store["user_schools"] = []

        is_staff = await verify_staff_at_school(
            authenticated_staff["user_id"],
            "other_school",
        )

        assert is_staff is False

    async def test_link_child_to_parent(self, authenticated_user, mock_supabase_patch):
        """Test linking a child to parent."""
        result = await link_child_to_parent(
            authenticated_user["user_id"],
            "new_child_id",
        )

        assert result["success"] is True


# ═══════════════════════════════════════════════════════════════
# PASSWORD VALIDATION TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.auth
@pytest.mark.unit
class TestPasswordValidation:
    """Test password strength validation."""

    def test_password_too_short(self):
        """Test password shorter than minimum length."""
        valid, error = validate_password_strength("Short1!")

        assert valid is False
        assert "12 characters" in error

    def test_password_no_uppercase(self):
        """Test password without uppercase letter."""
        valid, error = validate_password_strength("nouppercase123!")

        assert valid is False
        assert "uppercase" in error.lower()

    def test_password_no_lowercase(self):
        """Test password without lowercase letter."""
        valid, error = validate_password_strength("NOLOWERCASE123!")

        assert valid is False
        assert "lowercase" in error.lower()

    def test_password_no_digit(self):
        """Test password without digit."""
        valid, error = validate_password_strength("NoDigitsHere!")

        assert valid is False
        assert "digit" in error.lower()

    def test_password_no_special_char(self):
        """Test password without special character."""
        valid, error = validate_password_strength("NoSpecialChar123")

        assert valid is False
        assert "special" in error.lower()

    def test_password_too_common(self):
        """Test common password rejection."""
        valid, error = validate_password_strength("Password123!")

        assert valid is False
        assert "common" in error.lower()

    def test_password_sequential_start(self):
        """Test password starting with sequential characters."""
        valid, error = validate_password_strength("123SecurePassword!")

        assert valid is False
        assert "sequential" in error.lower()

    def test_password_valid_strong(self):
        """Test valid strong password."""
        valid, error = validate_password_strength("MySecureP@ssw0rd123")

        assert valid is True
        assert error is None

    def test_password_valid_complex(self):
        """Test valid complex password."""
        valid, error = validate_password_strength("C0mpl3x!P@ssw0rd")

        assert valid is True
        assert error is None


# ═══════════════════════════════════════════════════════════════
# RATE LIMITING TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.auth
@pytest.mark.unit
class TestRateLimiting:
    """Test rate limiting functionality."""

    def test_rate_limit_allows_max_attempts(self, clear_rate_limits):
        """Test rate limit allows maximum attempts."""
        email = "test@example.com"

        # Should allow max attempts
        for i in range(SECURITY_CONFIG.max_login_attempts):
            check_rate_limit(email, "login")

        # Should succeed (no exception)
        assert True

    def test_rate_limit_blocks_excess_attempts(self, clear_rate_limits):
        """Test rate limit blocks attempts beyond maximum."""
        email = "test@example.com"

        # Exhaust limit
        for i in range(SECURITY_CONFIG.max_login_attempts):
            check_rate_limit(email, "login")

        # Next attempt should fail
        with pytest.raises(RateLimitExceededError):
            check_rate_limit(email, "login")

    def test_rate_limit_per_email(self, clear_rate_limits):
        """Test rate limit is per email address."""
        email1 = "test1@example.com"
        email2 = "test2@example.com"

        # Exhaust limit for email1
        for i in range(SECURITY_CONFIG.max_login_attempts):
            check_rate_limit(email1, "login")

        # email2 should still work
        check_rate_limit(email2, "login")

        # But email1 should be blocked
        with pytest.raises(RateLimitExceededError):
            check_rate_limit(email1, "login")


# ═══════════════════════════════════════════════════════════════
# ACCOUNT LOCKOUT TESTS
# ═══════════════════════════════════════════════════════════════


@pytest.mark.auth
@pytest.mark.unit
class TestAccountLockout:
    """Test account lockout functionality."""

    def test_account_lockout_after_failed_attempts(self, clear_rate_limits):
        """Test account locks after max failed attempts."""
        email = "lockout@example.com"

        # Record failed attempts
        for i in range(SECURITY_CONFIG.max_failed_attempts_before_lockout):
            record_failed_login(email)

        # Should be locked
        with pytest.raises(AccountLockedError):
            check_account_lockout(email)

    def test_account_lockout_clear(self, clear_rate_limits):
        """Test clearing account lockout."""
        email = "lockout@example.com"

        # Lock account
        for i in range(SECURITY_CONFIG.max_failed_attempts_before_lockout):
            record_failed_login(email)

        # Clear lockout
        clear_failed_login_attempts(email)

        # Should not be locked
        check_account_lockout(email)  # No exception

    def test_account_lockout_prevents_login(self, clear_rate_limits):
        """Test locked account prevents login check."""
        email = "locked@example.com"

        # Lock account
        for i in range(SECURITY_CONFIG.max_failed_attempts_before_lockout):
            record_failed_login(email)

        # Should raise lockout error
        with pytest.raises(AccountLockedError) as exc_info:
            check_account_lockout(email)

        assert "locked" in str(exc_info.value).lower()
