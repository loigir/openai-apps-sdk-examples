"""Authentication module for AllôBye MCP server.

Provides email/password authentication using Supabase Auth, including:
- User signup and login
- Password reset
- Email verification
- Session management
- User profile management with roles (parent, school_staff)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@dataclass
class UserProfile:
    """User profile with role and associated entities."""

    id: str
    email: str
    name: Optional[str] = None
    role: str = "parent"  # 'parent' or 'school_staff'
    schools: List[str] = None  # List of school IDs
    children: List[str] = None  # List of child IDs (for parents)
    email_verified: bool = False
    created_at: Optional[str] = None

    def __post_init__(self):
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


def get_supabase_client():
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


def get_supabase_admin():
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
        password: User's password (min 6 characters)
        name: User's full name
        role: User role ('parent' or 'school_staff')
        schools: List of school IDs (required for school_staff)

    Returns:
        Dict containing user info and session

    Raises:
        UserAlreadyExistsError: If user already exists
        AuthenticationError: On other errors
    """
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
                "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
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
        }

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
        Dict containing user info, session, and profile

    Raises:
        InvalidCredentialsError: If credentials are invalid
        EmailNotVerifiedError: If email is not verified
        AuthenticationError: On other errors
    """
    supabase = get_supabase_client()
    if not supabase:
        # Mock response
        user_id = str(uuid4())
        return {
            "user": {
                "id": user_id,
                "email": email,
                "email_verified": True,
            },
            "session": {
                "access_token": f"mock_token_{user_id}",
                "refresh_token": f"mock_refresh_{user_id}",
                "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            },
            "profile": {
                "id": user_id,
                "email": email,
                "name": "Mock User",
                "role": "parent",
                "schools": [],
                "children": [],
            },
        }

    try:
        # Sign in with Supabase Auth
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password,
        })

        if not response.user:
            raise InvalidCredentialsError("Invalid email or password")

        # Check email verification (optional - can be enforced)
        # if not response.user.email_confirmed_at:
        #     raise EmailNotVerifiedError("Please verify your email before logging in")

        # Fetch user profile
        profile = await get_user_profile(response.user.id)

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
        }

    except InvalidCredentialsError:
        raise
    except EmailNotVerifiedError:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "invalid" in error_msg or "credentials" in error_msg:
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
