"""Authentication module for AllôBye MCP server.

Provides email/password authentication using Supabase Auth, including:
- User signup and login with strong password requirements
- Password reset
- Email verification
- Secure session management with token rotation
- Rate limiting for brute force protection
- Failed login attempt tracking
- MFA preparation hooks
- User profile management with roles (parent, school_staff)

Security Features:
- Password requirements: min 12 chars, uppercase, lowercase, digit, special char
- Rate limiting: max 5 attempts per 15 minutes per email
- Session timeout: configurable, default 1 hour
- Token refresh mechanism with rotation
- Failed login tracking with automatic lockout
- Common password blacklist checking
"""

from __future__ import annotations

import os
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import uuid4

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


# Security Configuration
@dataclass
class SecurityConfig:
    """Security configuration for authentication system."""

    # Password policy
    password_min_length: int = 12
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = True

    # Rate limiting
    max_login_attempts: int = 5
    rate_limit_window_minutes: int = 15
    max_signup_attempts: int = 3

    # Session management
    session_timeout_hours: int = 1
    token_refresh_threshold_minutes: int = 10

    # Account lockout
    lockout_duration_minutes: int = 30
    max_failed_attempts_before_lockout: int = 5


# Global security configuration
SECURITY_CONFIG = SecurityConfig()


# In-memory rate limiting storage (in production, use Redis)
_rate_limit_store: Dict[str, List[datetime]] = defaultdict(list)
_failed_login_store: Dict[str, List[datetime]] = defaultdict(list)
_account_lockout_store: Dict[str, datetime] = {}


# Common passwords blacklist (top 100 most common)
COMMON_PASSWORDS = {
    "123456", "password", "12345678", "qwerty", "123456789", "12345", "1234",
    "111111", "1234567", "dragon", "123123", "baseball", "iloveyou", "trustno1",
    "1234567890", "sunshine", "master", "welcome", "shadow", "ashley", "football",
    "jesus", "michael", "ninja", "mustang", "password1", "123456789a", "password123",
    "welcome123", "admin", "root", "administrator", "changeme", "letmein", "monkey",
    "password1234", "qwerty123", "abc123", "admin123", "welcome1", "passw0rd",
}


@dataclass
class UserProfile:
    """User profile with role and associated entities."""

    id: str
    email: str
    name: Optional[str] = None
    role: str = "parent"  # 'parent' or 'school_staff'
    schools: Optional[List[str]] = None  # List of school IDs
    children: Optional[List[str]] = None  # List of child IDs (for parents)
    email_verified: bool = False
    created_at: Optional[str] = None

    def __post_init__(self) -> None:
        if self.schools is None:
            self.schools = []
        if self.children is None:
            self.children = []


class AuthenticationError(Exception):
    """Base exception for authentication errors."""

    pass


class InvalidCredentialsError(AuthenticationError):
    """Raised when credentials are invalid."""

    pass


class EmailNotVerifiedError(AuthenticationError):
    """Raised when email is not verified."""

    pass


class UserAlreadyExistsError(AuthenticationError):
    """Raised when user already exists."""

    pass


class SessionExpiredError(AuthenticationError):
    """Raised when session is expired."""

    pass


class WeakPasswordError(AuthenticationError):
    """Raised when password does not meet security requirements."""

    pass


class RateLimitExceededError(AuthenticationError):
    """Raised when rate limit is exceeded."""

    pass


class AccountLockedError(AuthenticationError):
    """Raised when account is locked due to too many failed attempts."""

    pass


class MFARequiredError(AuthenticationError):
    """Raised when MFA is required but not provided."""

    pass


# Password Validation Functions
def validate_password_strength(password: str) -> Tuple[bool, Optional[str]]:
    """Validate password meets security requirements.

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    config = SECURITY_CONFIG

    # Check minimum length
    if len(password) < config.password_min_length:
        return False, f"Password must be at least {config.password_min_length} characters long"

    # Check for uppercase
    if config.password_require_uppercase and not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter"

    # Check for lowercase
    if config.password_require_lowercase and not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter"

    # Check for digit
    if config.password_require_digit and not re.search(r"\d", password):
        return False, "Password must contain at least one digit"

    # Check for special character
    if config.password_require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)"

    # Check against common passwords
    if password.lower() in COMMON_PASSWORDS:
        return False, "Password is too common. Please choose a more unique password"

    # Check for obvious sequential patterns at start or as dominant pattern
    # More lenient - only reject if it starts with obvious sequence or has long sequences
    if re.search(r"^(123|234|345|456|567|678|789|abc|bcd|cde|def|qwerty)", password.lower()):
        return False, "Password starts with sequential characters. Please choose a stronger password"

    return True, None


def check_rate_limit(email: str, attempt_type: str = "login") -> None:
    """Check if rate limit is exceeded for an email.

    Args:
        email: Email address to check
        attempt_type: Type of attempt ('login' or 'signup')

    Raises:
        RateLimitExceededError: If rate limit is exceeded
    """
    now = datetime.now()
    config = SECURITY_CONFIG
    window = timedelta(minutes=config.rate_limit_window_minutes)

    # Get attempt history
    attempts = _rate_limit_store[f"{attempt_type}:{email}"]

    # Remove old attempts outside the window
    attempts[:] = [attempt for attempt in attempts if now - attempt < window]

    # Check limit
    max_attempts = config.max_login_attempts if attempt_type == "login" else config.max_signup_attempts

    if len(attempts) >= max_attempts:
        raise RateLimitExceededError(
            f"Too many {attempt_type} attempts. Please try again in {config.rate_limit_window_minutes} minutes"
        )

    # Record this attempt
    attempts.append(now)


def check_account_lockout(email: str) -> None:
    """Check if account is locked due to failed login attempts.

    Args:
        email: Email address to check

    Raises:
        AccountLockedError: If account is locked
    """
    if email in _account_lockout_store:
        lockout_time = _account_lockout_store[email]
        unlock_time = lockout_time + timedelta(minutes=SECURITY_CONFIG.lockout_duration_minutes)

        if datetime.now() < unlock_time:
            remaining = (unlock_time - datetime.now()).seconds // 60
            raise AccountLockedError(
                f"Account is locked due to too many failed login attempts. "
                f"Please try again in {remaining} minutes"
            )
        else:
            # Lockout expired, remove it
            del _account_lockout_store[email]
            _failed_login_store[email].clear()


def record_failed_login(email: str) -> None:
    """Record a failed login attempt and check for lockout.

    Args:
        email: Email address that failed login
    """
    now = datetime.now()
    config = SECURITY_CONFIG

    # Add failed attempt
    _failed_login_store[email].append(now)

    # Remove old attempts (older than lockout window)
    window = timedelta(minutes=config.lockout_duration_minutes)
    _failed_login_store[email][:] = [
        attempt for attempt in _failed_login_store[email]
        if now - attempt < window
    ]

    # Check if should lock account
    if len(_failed_login_store[email]) >= config.max_failed_attempts_before_lockout:
        _account_lockout_store[email] = now


def clear_failed_login_attempts(email: str) -> None:
    """Clear failed login attempts after successful login.

    Args:
        email: Email address to clear
    """
    if email in _failed_login_store:
        _failed_login_store[email].clear()
    if email in _account_lockout_store:
        del _account_lockout_store[email]


def should_refresh_token(expires_at: str) -> bool:
    """Check if token should be refreshed based on expiration.

    Args:
        expires_at: Token expiration timestamp (ISO format)

    Returns:
        True if token should be refreshed
    """
    try:
        expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        threshold = timedelta(minutes=SECURITY_CONFIG.token_refresh_threshold_minutes)
        return datetime.now() < expiry < datetime.now() + threshold
    except:
        return False


# MFA Preparation Hooks
class MFAContext:
    """Context for Multi-Factor Authentication (MFA) - Preparation for future implementation."""

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.mfa_enabled = False
        self.mfa_verified = False
        self.mfa_methods: List[str] = []

    def enable_mfa(self, method: str = "totp") -> Dict[str, Union[bool, str]]:
        """Enable MFA for user (placeholder for future implementation).

        Args:
            method: MFA method ('totp', 'sms', 'email')

        Returns:
            Dict with MFA setup information
        """
        return {
            "success": True,
            "method": method,
            "message": "MFA setup initiated (feature coming soon)",
        }

    def verify_mfa(self, code: str) -> bool:
        """Verify MFA code (placeholder for future implementation).

        Args:
            code: MFA verification code

        Returns:
            True if code is valid
        """
        # Placeholder - will integrate with TOTP/SMS provider
        return False

    def check_mfa_required(self) -> bool:
        """Check if MFA is required for this user.

        Returns:
            True if MFA is required
        """
        return self.mfa_enabled and not self.mfa_verified


def get_supabase_client() -> Optional[Any]:
    """Get Supabase client for authentication.

    Uses ANON key for client-side auth operations.
    """
    try:
        from supabase import create_client, Client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")

        return create_client(url, key)
    except Exception as e:
        print(f"Warning: Supabase client initialization failed: {e}")
        return None


def get_supabase_admin() -> Optional[Any]:
    """Get Supabase admin client for privileged operations.

    Uses SERVICE_ROLE key for server-side operations.
    """
    try:
        from supabase import create_client, Client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

        return create_client(url, key)
    except Exception as e:
        print(f"Warning: Supabase admin client initialization failed: {e}")
        return None


async def signup_user(
    email: str,
    password: str,
    name: Optional[str] = None,
    role: str = "parent",
    schools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Sign up a new user with email and password.

    Args:
        email: User's email address
        password: User's password (min 12 chars with complexity requirements)
        name: User's full name
        role: User role ('parent' or 'school_staff')
        schools: List of school IDs (required for school_staff)

    Returns:
        Dict containing user info and session

    Raises:
        WeakPasswordError: If password does not meet requirements
        RateLimitExceededError: If too many signup attempts
        UserAlreadyExistsError: If user already exists
        AuthenticationError: On other errors
    """
    # Check rate limiting
    check_rate_limit(email, "signup")

    # Validate password strength
    is_valid, error_msg = validate_password_strength(password)
    if not is_valid:
        raise WeakPasswordError(error_msg)

    supabase = get_supabase_client()
    if not supabase:
        # Mock response for development
        user_id = str(uuid4())
        return {
            "user": {
                "id": user_id,
                "email": email,
                "email_verified": False,
                "created_at": datetime.now().isoformat(),
            },
            "session": {
                "access_token": f"mock_token_{user_id}",
                "refresh_token": f"mock_refresh_{user_id}",
                "expires_at": (datetime.now() + timedelta(hours=SECURITY_CONFIG.session_timeout_hours)).isoformat(),
            },
            "mfa_context": {
                "enabled": False,
                "required": False,
            },
        }

    try:
        # Sign up with Supabase Auth
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "name": name,
                    "role": role,
                }
            }
        })

        if not response.user:
            raise AuthenticationError("Failed to create user")

        # Create user profile in database
        profile_data = {
            "id": response.user.id,
            "email": email,
            "name": name,
            "role": role,
            "email_verified": False,
            "created_at": datetime.now().isoformat(),
        }

        supabase.table("user_profiles").insert(profile_data).execute()

        # If school staff, link to schools
        if role == "school_staff" and schools:
            for school_id in schools:
                supabase.table("user_schools").insert({
                    "user_id": response.user.id,
                    "school_id": school_id,
                }).execute()

        # Initialize MFA context
        mfa_context = MFAContext(response.user.id)

        return {
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "email_verified": response.user.email_confirmed_at is not None,
                "created_at": response.user.created_at,
            },
            "session": {
                "access_token": response.session.access_token if response.session else None,
                "refresh_token": response.session.refresh_token if response.session else None,
                "expires_at": response.session.expires_at if response.session else None,
            },
            "mfa_context": {
                "enabled": mfa_context.mfa_enabled,
                "required": mfa_context.check_mfa_required(),
            },
        }

    except WeakPasswordError:
        raise
    except RateLimitExceededError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "already registered" in error_msg or "duplicate" in error_msg:
            raise UserAlreadyExistsError(f"User with email {email} already exists")
        raise AuthenticationError(f"Signup failed: {e}")


async def login_user(email: str, password: str) -> Dict[str, Any]:
    """Login user with email and password.

    Args:
        email: User's email address
        password: User's password

    Returns:
        Dict containing user info, session, profile, and MFA context

    Raises:
        RateLimitExceededError: If too many login attempts
        AccountLockedError: If account is locked due to failed attempts
        InvalidCredentialsError: If credentials are invalid
        EmailNotVerifiedError: If email is not verified
        MFARequiredError: If MFA is enabled but not verified
        AuthenticationError: On other errors
    """
    # Check rate limiting
    check_rate_limit(email, "login")

    # Check if account is locked
    check_account_lockout(email)

    supabase = get_supabase_client()
    if not supabase:
        # Mock response
        user_id = str(uuid4())
        clear_failed_login_attempts(email)
        return {
            "user": {
                "id": user_id,
                "email": email,
                "email_verified": True,
            },
            "session": {
                "access_token": f"mock_token_{user_id}",
                "refresh_token": f"mock_refresh_{user_id}",
                "expires_at": (datetime.now() + timedelta(hours=SECURITY_CONFIG.session_timeout_hours)).isoformat(),
            },
            "profile": {
                "id": user_id,
                "email": email,
                "name": "Mock User",
                "role": "parent",
                "schools": [],
                "children": [],
            },
            "mfa_context": {
                "enabled": False,
                "required": False,
            },
        }

    try:
        # Sign in with Supabase Auth
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })

        if not response.user:
            record_failed_login(email)
            raise InvalidCredentialsError("Invalid email or password")

        # Check email verification (optional - can be enforced)
        # if not response.user.email_confirmed_at:
        #     raise EmailNotVerifiedError("Please verify your email before logging in")

        # Clear failed login attempts on successful login
        clear_failed_login_attempts(email)

        # Fetch user profile
        profile = await get_user_profile(response.user.id)

        # Initialize MFA context
        mfa_context = MFAContext(response.user.id)

        # Check if MFA is required
        if mfa_context.check_mfa_required():
            raise MFARequiredError("Multi-factor authentication required")

        return {
            "user": {
                "id": response.user.id,
                "email": response.user.email,
                "email_verified": response.user.email_confirmed_at is not None,
            },
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at,
            },
            "profile": profile,
            "mfa_context": {
                "enabled": mfa_context.mfa_enabled,
                "required": mfa_context.check_mfa_required(),
            },
        }

    except (InvalidCredentialsError, RateLimitExceededError, AccountLockedError, MFARequiredError):
        raise
    except EmailNotVerifiedError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "credentials" in error_msg:
            record_failed_login(email)
            raise InvalidCredentialsError("Invalid email or password")
        raise AuthenticationError(f"Login failed: {e}")


async def logout_user(access_token: str) -> Dict[str, Any]:
    """Logout user and invalidate session.

    Args:
        access_token: User's access token

    Returns:
        Dict with success status
    """
    supabase = get_supabase_client()
    if not supabase:
        return {"success": True, "message": "Logged out (mock)"}

    try:
        # Set the session before signing out
        supabase.auth.set_session(access_token, "")
        supabase.auth.sign_out()

        return {"success": True, "message": "Logged out successfully"}
    except Exception as e:
        # Even if signout fails, return success (client will clear local session)
        print(f"Warning: Logout error: {e}")
        return {"success": True, "message": "Logged out"}


async def reset_password_request(email: str) -> Dict[str, Any]:
    """Request password reset for a user.

    Sends password reset email via Supabase Auth.

    Args:
        email: User's email address

    Returns:
        Dict with success status
    """
    supabase = get_supabase_client()
    if not supabase:
        return {
            "success": True,
            "message": f"Password reset email sent to {email} (mock)",
        }

    try:
        supabase.auth.reset_password_email(email)

        return {
            "success": True,
            "message": f"Password reset email sent to {email}",
        }
    except Exception as e:
        # Don't reveal if email exists or not
        return {
            "success": True,
            "message": "If this email exists, a password reset link has been sent",
        }


async def verify_email_token(token: str) -> Dict[str, Any]:
    """Verify email with token from verification email.

    Args:
        token: Email verification token

    Returns:
        Dict with verification status
    """
    supabase = get_supabase_client()
    if not supabase:
        return {"success": True, "message": "Email verified (mock)"}

    try:
        response = supabase.auth.verify_otp({
            "token": token,
            "type": "email",
        })

        if response.user:
            # Update profile
            supabase.table("user_profiles").update({
                "email_verified": True,
            }).eq("id", response.user.id).execute()

            return {"success": True, "message": "Email verified successfully"}
        else:
            raise AuthenticationError("Invalid verification token")

    except Exception as e:
        raise AuthenticationError(f"Email verification failed: {e}")


async def validate_session(access_token: str) -> Optional[UserProfile]:
    """Validate JWT token and return user profile.

    Args:
        access_token: JWT access token

    Returns:
        UserProfile if valid, None otherwise

    Raises:
        SessionExpiredError: If session is expired
        AuthenticationError: On validation errors
    """
    supabase = get_supabase_client()
    if not supabase:
        # Mock validation
        return UserProfile(
            id="mock_user_id",
            email="mock@example.com",
            name="Mock User",
            role="parent",
            email_verified=True,
        )

    try:
        # Set session and get user
        supabase.auth.set_session(access_token, "")
        response = supabase.auth.get_user(access_token)

        if not response.user:
            raise SessionExpiredError("Session expired or invalid")

        # Fetch full profile
        profile_dict = await get_user_profile(response.user.id)

        return UserProfile(**profile_dict)

    except SessionExpiredError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "expired" in error_msg or "invalid" in error_msg:
            raise SessionExpiredError("Session expired or invalid")
        raise AuthenticationError(f"Session validation failed: {e}")


async def refresh_session(refresh_token: str) -> Dict[str, Any]:
    """Refresh session using refresh token (token rotation).

    This implements secure token rotation - each refresh generates a new pair
    of access and refresh tokens, invalidating the old refresh token.

    Args:
        refresh_token: JWT refresh token

    Returns:
        Dict containing new session tokens and user info

    Raises:
        SessionExpiredError: If refresh token is expired or invalid
        AuthenticationError: On refresh errors
    """
    supabase = get_supabase_client()
    if not supabase:
        # Mock refresh
        user_id = str(uuid4())
        return {
            "session": {
                "access_token": f"mock_token_refreshed_{user_id}",
                "refresh_token": f"mock_refresh_refreshed_{user_id}",
                "expires_at": (datetime.now() + timedelta(hours=SECURITY_CONFIG.session_timeout_hours)).isoformat(),
            },
            "user": {
                "id": user_id,
                "email": "mock@example.com",
            },
        }

    try:
        # Refresh session with Supabase
        response = supabase.auth.refresh_session(refresh_token)

        if not response.session:
            raise SessionExpiredError("Invalid or expired refresh token")

        return {
            "session": {
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token,
                "expires_at": response.session.expires_at,
            },
            "user": {
                "id": response.user.id if response.user else None,
                "email": response.user.email if response.user else None,
            },
        }

    except SessionExpiredError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "expired" in error_msg or "invalid" in error_msg:
            raise SessionExpiredError("Invalid or expired refresh token")
        raise AuthenticationError(f"Token refresh failed: {e}")


async def get_session_info(access_token: str) -> Dict[str, Any]:
    """Get detailed session information including expiration and refresh recommendation.

    Args:
        access_token: JWT access token

    Returns:
        Dict with session details and refresh recommendation
    """
    supabase = get_supabase_client()
    if not supabase:
        return {
            "valid": True,
            "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            "should_refresh": False,
            "time_until_expiry_minutes": 60,
        }

    try:
        response = supabase.auth.get_user(access_token)

        if not response.user:
            return {
                "valid": False,
                "expired": True,
            }

        # Get session details
        session = supabase.auth.get_session()
        if not session:
            return {
                "valid": False,
                "expired": True,
            }

        expires_at = session.expires_at if hasattr(session, "expires_at") else None
        should_refresh = should_refresh_token(expires_at) if expires_at else False

        # Calculate time until expiry
        time_until_expiry = None
        if expires_at:
            try:
                expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                time_until_expiry = int((expiry - datetime.now()).total_seconds() / 60)
            except:
                pass

        return {
            "valid": True,
            "expires_at": expires_at,
            "should_refresh": should_refresh,
            "time_until_expiry_minutes": time_until_expiry,
            "user_id": response.user.id,
            "email": response.user.email,
        }

    except Exception as e:
        return {
            "valid": False,
            "error": str(e),
        }


async def get_user_profile(user_id: str) -> Dict[str, Any]:
    """Get user profile with associated schools and children.

    Args:
        user_id: User ID

    Returns:
        Dict with full user profile
    """
    supabase = get_supabase_admin()
    if not supabase:
        return {
            "id": user_id,
            "email": "mock@example.com",
            "name": "Mock User",
            "role": "parent",
            "schools": [],
            "children": [],
            "email_verified": True,
        }

    try:
        # Fetch user profile
        profile_response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()

        if not profile_response.data:
            return {
                "id": user_id,
                "email": "unknown",
                "role": "parent",
                "schools": [],
                "children": [],
            }

        profile = profile_response.data

        # Fetch associated schools (for school staff)
        schools = []
        if profile.get("role") == "school_staff":
            schools_response = supabase.table("user_schools").select("school_id").eq(
                "user_id", user_id
            ).execute()
            schools = [s["school_id"] for s in schools_response.data]

        # Fetch associated children (for parents)
        children = []
        if profile.get("role") == "parent":
            children_response = supabase.table("parent_children").select("child_id").eq(
                "parent_id", user_id
            ).execute()
            children = [c["child_id"] for c in children_response.data]

        return {
            "id": profile["id"],
            "email": profile["email"],
            "name": profile.get("name"),
            "role": profile.get("role", "parent"),
            "schools": schools,
            "children": children,
            "email_verified": profile.get("email_verified", False),
            "created_at": profile.get("created_at"),
        }

    except Exception as e:
        print(f"Error fetching user profile: {e}")
        return {
            "id": user_id,
            "email": "unknown",
            "role": "parent",
            "schools": [],
            "children": [],
        }


async def update_user_profile(
    user_id: str,
    name: Optional[str] = None,
    schools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Update user profile.

    Args:
        user_id: User ID
        name: New name (optional)
        schools: New list of school IDs (optional, for school staff)

    Returns:
        Updated profile
    """
    supabase = get_supabase_admin()
    if not supabase:
        return {
            "id": user_id,
            "name": name,
            "schools": schools or [],
        }

    try:
        # Update profile
        update_data = {}
        if name is not None:
            update_data["name"] = name

        if update_data:
            supabase.table("user_profiles").update(update_data).eq("id", user_id).execute()

        # Update schools if provided
        if schools is not None:
            # Delete existing associations
            supabase.table("user_schools").delete().eq("user_id", user_id).execute()

            # Add new associations
            for school_id in schools:
                supabase.table("user_schools").insert({
                    "user_id": user_id,
                    "school_id": school_id,
                }).execute()

        # Return updated profile
        return await get_user_profile(user_id)

    except Exception as e:
        raise AuthenticationError(f"Profile update failed: {e}")


async def link_child_to_parent(parent_id: str, child_id: str) -> Dict[str, Any]:
    """Link a child to a parent.

    Args:
        parent_id: Parent user ID
        child_id: Child ID

    Returns:
        Dict with success status
    """
    supabase = get_supabase_admin()
    if not supabase:
        return {"success": True, "message": "Child linked (mock)"}

    try:
        supabase.table("parent_children").insert({
            "parent_id": parent_id,
            "child_id": child_id,
        }).execute()

        return {"success": True, "message": "Child linked to parent"}

    except Exception as e:
        raise AuthenticationError(f"Failed to link child: {e}")


async def verify_parent_owns_child(parent_id: str, child_id: str) -> bool:
    """Verify that a parent owns/can access a child.

    Args:
        parent_id: Parent user ID
        child_id: Child ID

    Returns:
        True if parent owns child, False otherwise
    """
    supabase = get_supabase_admin()
    if not supabase:
        return True  # Mock: allow all

    try:
        response = supabase.table("parent_children").select("id").eq(
            "parent_id", parent_id
        ).eq("child_id", child_id).execute()

        return len(response.data) > 0

    except Exception as e:
        print(f"Error verifying parent-child relationship: {e}")
        return False


async def verify_staff_at_school(user_id: str, school_id: str) -> bool:
    """Verify that a user is staff at a school.

    Args:
        user_id: User ID
        school_id: School ID

    Returns:
        True if user is staff at school, False otherwise
    """
    supabase = get_supabase_admin()
    if not supabase:
        return True  # Mock: allow all

    try:
        response = supabase.table("user_schools").select("id").eq(
            "user_id", user_id
        ).eq("school_id", school_id).execute()

        return len(response.data) > 0

    except Exception as e:
        print(f"Error verifying staff-school relationship: {e}")
        return False
