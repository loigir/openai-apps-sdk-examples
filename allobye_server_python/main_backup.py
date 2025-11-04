"""AllôBye MCP server implemented with Python FastMCP.

This server provides tools for managing child pickup scheduling, delegate
authorization, and emergency notifications across multiple schools.

Architecture:
- Parent Agent → ChatGPT conversation + React widget (mobile)
- Orchestrator → ChatGPT reasoning + MCP tools (backend)
- Display Agent → React widget (fullscreen, school tablet)
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

import mcp.types as types
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from dotenv import load_dotenv

# Import authentication module
from auth import (
    signup_user,
    login_user,
    logout_user,
    reset_password_request,
    validate_session,
    get_user_profile,
    update_user_profile,
    verify_parent_owns_child,
    verify_staff_at_school,
    UserProfile,
    AuthenticationError,
    InvalidCredentialsError,
    SessionExpiredError,
)

# Load environment variables
load_dotenv()

# Supabase client setup (lazy initialization)
_supabase_client = None


def get_supabase():
    """Get or create Supabase client."""
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client, Client

            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set")

            _supabase_client = create_client(url, key)
        except Exception as e:
            # Fallback to mock mode if Supabase not available
            print(f"Warning: Supabase client initialization failed: {e}")
            _supabase_client = None

    return _supabase_client


# ═══════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════


class PickupScheduleInput(BaseModel):
    """Input schema for scheduling a pickup."""

    child_ids: List[str] = Field(
        ...,
        alias="childIds",
        description="List of child IDs to be picked up",
        min_length=1,
    )
    pickup_person_id: str = Field(
        ...,
        alias="pickupPersonId",
        description="ID of the authorized person picking up the children",
    )
    scheduled_time: str = Field(
        ...,
        alias="scheduledTime",
        description="ISO 8601 datetime for pickup (e.g., 2025-11-04T15:00:00-05:00)",
    )
    notes: Optional[str] = Field(
        None,
        description="Optional notes about the pickup",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class DelegateAuthorizeInput(BaseModel):
    """Input schema for authorizing a delegate."""

    delegate_email: str = Field(
        ...,
        alias="delegateEmail",
        description="Email address of the person to authorize",
    )
    child_ids: List[str] = Field(
        ...,
        alias="childIds",
        description="List of child IDs the delegate can pick up",
        min_length=1,
    )
    permissions: List[str] = Field(
        default=["pickup"],
        description="List of permissions: pickup, emergency_contact, medical_decisions",
    )
    schools: Optional[List[str]] = Field(
        None,
        description="Optional list of school IDs (inferred from children if not provided)",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class EmergencyDeclareInput(BaseModel):
    """Input schema for declaring an emergency."""

    child_id: str = Field(
        ...,
        alias="childId",
        description="ID of the child affected by the emergency",
    )
    emergency_type: str = Field(
        ...,
        alias="emergencyType",
        description="Type of emergency: late, illness, cancel, other",
    )
    context: str = Field(
        ...,
        description="Description of the emergency situation",
    )
    notify_all_delegates: bool = Field(
        True,
        alias="notifyAllDelegates",
        description="Whether to notify all authorized delegates",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class SchoolDashboardInput(BaseModel):
    """Input schema for fetching school dashboard data."""

    school_id: str = Field(
        ...,
        alias="schoolId",
        description="ID of the school to fetch dashboard for",
    )
    date: Optional[str] = Field(
        None,
        description="Date to fetch (ISO format, defaults to today)",
    )
    time_window: str = Field(
        "current",
        alias="timeWindow",
        description="Time window: current (next 30min), today, or custom",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class AuthSignupInput(BaseModel):
    """Input schema for user signup."""

    email: str = Field(
        ...,
        description="Email address for the account",
    )
    password: str = Field(
        ...,
        description="Password (minimum 6 characters)",
        min_length=6,
    )
    name: Optional[str] = Field(
        None,
        description="Full name of the user",
    )
    role: str = Field(
        "parent",
        description="User role: parent or school_staff",
    )
    schools: Optional[List[str]] = Field(
        None,
        description="List of school IDs (required for school_staff)",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class AuthLoginInput(BaseModel):
    """Input schema for user login."""

    email: str = Field(
        ...,
        description="Email address",
    )
    password: str = Field(
        ...,
        description="Password",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class AuthResetPasswordInput(BaseModel):
    """Input schema for password reset request."""

    email: str = Field(
        ...,
        description="Email address to send reset link to",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


class AuthProfileUpdateInput(BaseModel):
    """Input schema for updating user profile."""

    name: Optional[str] = Field(
        None,
        description="New name for the user",
    )
    schools: Optional[List[str]] = Field(
        None,
        description="Updated list of school IDs (for school staff)",
    )

    model_config = ConfigDict(populate_by_name=True, extra="forbid")


# ═══════════════════════════════════════════════════════════════
# WIDGET CONFIGURATION
# ═══════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class AllobyeWidget:
    identifier: str
    title: str
    template_uri: str
    invoking: str
    invoked: str
    html: str


ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
MIME_TYPE = "text/html+skybridge"


@lru_cache(maxsize=None)
def _load_widget_html(component_name: str) -> str:
    """Load widget HTML from assets directory."""
    html_path = ASSETS_DIR / f"{component_name}.html"
    if html_path.exists():
        return html_path.read_text(encoding="utf8")

    fallback_candidates = sorted(ASSETS_DIR.glob(f"{component_name}-*.html"))
    if fallback_candidates:
        return fallback_candidates[-1].read_text(encoding="utf8")

    # Return placeholder if not built yet
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>{component_name}</title>
</head>
<body>
    <div id="{component_name}-root">
        Widget not built yet. Run 'pnpm run build' to generate assets.
    </div>
</body>
</html>"""


SCHOOL_DASHBOARD_WIDGET = AllobyeWidget(
    identifier="school-dashboard",
    title="Tableau de bord école - AllôBye",
    template_uri="ui://widget/allobye-dashboard.html",
    invoking="Chargement du tableau de bord...",
    invoked="Tableau de bord chargé",
    html=_load_widget_html("allobye-dashboard"),
)


# ═══════════════════════════════════════════════════════════════
# AUTHENTICATION HELPERS
# ═══════════════════════════════════════════════════════════════


async def get_current_user(arguments: Dict[str, Any]) -> Optional[UserProfile]:
    """Extract and validate user from request arguments.

    Expects access_token in arguments or returns None for unauthenticated access.

    Args:
        arguments: Tool call arguments

    Returns:
        UserProfile if authenticated, None otherwise
    """
    access_token = arguments.get("access_token") or arguments.get("accessToken")

    if not access_token:
        return None

    try:
        user = await validate_session(access_token)
        return user
    except (SessionExpiredError, AuthenticationError) as e:
        print(f"Authentication error: {e}")
        return None


def require_auth(user: Optional[UserProfile], role: Optional[str] = None) -> bool:
    """Check if user is authenticated and optionally has required role.

    Args:
        user: UserProfile or None
        role: Required role (optional)

    Returns:
        True if authenticated (and has role if specified)
    """
    if not user:
        return False

    if role and user.role != role:
        return False

    return True


# ═══════════════════════════════════════════════════════════════
# DATABASE HELPER FUNCTIONS
# ═══════════════════════════════════════════════════════════════


async def get_schools_for_children(child_ids: List[str]) -> List[Dict[str, Any]]:
    """Get unique schools for a list of children."""
    supabase = get_supabase()
    if not supabase:
        # Mock data for development
        return [
            {"id": "school_1", "name": "École Primaire Exemple"},
        ]

    try:
        # Query children and their schools
        response = supabase.table("children").select("school_id, schools(*)").in_("id", child_ids).execute()

        # Extract unique schools
        schools = {}
        for child in response.data:
            if child.get("schools"):
                school = child["schools"]
                schools[school["id"]] = school

        return list(schools.values())
    except Exception as e:
        print(f"Error fetching schools: {e}")
        return []


async def create_pickup_request(
    child_ids: List[str],
    pickup_person_id: str,
    scheduled_time: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a pickup request in the database."""
    supabase = get_supabase()

    pickup_id = str(uuid4())

    if not supabase:
        # Mock response
        return {
            "id": pickup_id,
            "child_ids": child_ids,
            "pickup_person_id": pickup_person_id,
            "scheduled_time": scheduled_time,
            "status": "confirmed",
            "notes": notes,
            "created_at": datetime.now().isoformat(),
        }

    try:
        # Insert pickup record
        pickup_data = {
            "id": pickup_id,
            "pickup_person_id": pickup_person_id,
            "scheduled_time": scheduled_time,
            "status": "confirmed",
            "notes": notes,
        }

        response = supabase.table("pickups").insert(pickup_data).execute()

        # Link children to pickup
        for child_id in child_ids:
            supabase.table("pickup_children").insert({
                "pickup_id": pickup_id,
                "child_id": child_id,
            }).execute()

        return response.data[0] if response.data else pickup_data
    except Exception as e:
        print(f"Error creating pickup: {e}")
        raise


async def coordinate_cross_school_pickup(
    child_ids: List[str],
    pickup_person_id: str,
    scheduled_time: str,
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Coordinate pickup across multiple schools (A2A simulation)."""
    schools = await get_schools_for_children(child_ids)

    # Create pickup request
    pickup = await create_pickup_request(
        child_ids, pickup_person_id, scheduled_time, notes
    )

    # In real implementation, broadcast to A2A bus for each school
    # For now, we'll just return consolidated results
    pickup["schools_affected"] = [s["name"] for s in schools]
    pickup["a2a_messages"] = [
        {"school_id": s["id"], "status": "confirmed"} for s in schools
    ]

    return pickup


async def broadcast_delegate_authorization(
    delegate_email: str,
    child_ids: List[str],
    permissions: List[str],
    schools: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Broadcast delegate authorization to all affected schools."""
    supabase = get_supabase()
    delegate_id = str(uuid4())

    if not supabase:
        return {
            "delegate_id": delegate_id,
            "sync_status": "success",
            "messages": [{"school_id": s["id"], "status": "synced"} for s in schools],
        }

    try:
        # Create or update delegate record
        delegate_data = {
            "id": delegate_id,
            "email": delegate_email,
            "permissions": permissions,
        }

        response = supabase.table("delegates").upsert(delegate_data, on_conflict="email").execute()

        # Link delegate to children
        for child_id in child_ids:
            supabase.table("delegate_children").insert({
                "delegate_id": delegate_id,
                "child_id": child_id,
            }).execute()

        return {
            "delegate_id": delegate_id,
            "sync_status": "success",
            "messages": [{"school_id": s["id"], "status": "synced"} for s in schools],
        }
    except Exception as e:
        print(f"Error authorizing delegate: {e}")
        raise


async def get_authorized_delegates(child_id: str) -> List[Dict[str, Any]]:
    """Get all authorized delegates for a child."""
    supabase = get_supabase()

    if not supabase:
        return [
            {"id": "delegate_1", "email": "grandmaman@example.com", "name": "Grand-maman"}
        ]

    try:
        response = supabase.table("delegate_children").select(
            "delegates(*)"
        ).eq("child_id", child_id).execute()

        return [item["delegates"] for item in response.data if item.get("delegates")]
    except Exception as e:
        print(f"Error fetching delegates: {e}")
        return []


async def broadcast_emergency(
    child_id: str,
    emergency_type: str,
    context: str,
    delegates: List[Dict[str, Any]],
    schools: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Broadcast emergency to delegates and schools (A2A cascade)."""
    emergency_id = str(uuid4())
    supabase = get_supabase()

    if not supabase:
        return {
            "id": emergency_id,
            "a2a_trace": [
                {"type": "delegate_notify", "count": len(delegates)},
                {"type": "school_notify", "count": len(schools)},
            ],
        }

    try:
        # Create emergency record
        emergency_data = {
            "id": emergency_id,
            "child_id": child_id,
            "emergency_type": emergency_type,
            "context": context,
            "created_at": datetime.now().isoformat(),
        }

        supabase.table("emergencies").insert(emergency_data).execute()

        # In real implementation: Send via A2A to all parties
        # For now, log the cascade
        return {
            "id": emergency_id,
            "a2a_trace": [
                {"type": "delegate_notify", "count": len(delegates)},
                {"type": "school_notify", "count": len(schools)},
            ],
        }
    except Exception as e:
        print(f"Error broadcasting emergency: {e}")
        raise


async def get_school_pickups(
    school_id: str,
    date: str,
    time_window: str,
) -> List[Dict[str, Any]]:
    """Get pickup queue for a school dashboard."""
    supabase = get_supabase()

    # Calculate time range
    now = datetime.now()
    if time_window == "current":
        start_time = now
        end_time = now + timedelta(minutes=30)
    elif time_window == "today":
        start_time = now.replace(hour=0, minute=0, second=0)
        end_time = now.replace(hour=23, minute=59, second=59)
    else:
        start_time = now
        end_time = now + timedelta(hours=24)

    if not supabase:
        # Mock data
        return [
            {
                "id": "pickup_1",
                "child": {"name": "Sophie Tremblay"},
                "pickup_person": {"name": "Grand-maman"},
                "scheduled_time": (now + timedelta(minutes=10)).strftime("%H:%M"),
                "status": "pending",
                "eta": "10 min",
                "delay": 0,
            },
            {
                "id": "pickup_2",
                "child": {"name": "Thomas Gagnon"},
                "pickup_person": {"name": "Papa"},
                "scheduled_time": (now + timedelta(minutes=20)).strftime("%H:%M"),
                "status": "pending",
                "eta": "20 min",
                "delay": 5,
            },
        ]

    try:
        response = supabase.table("pickups").select(
            "*, children(*), pickup_person:delegates(*)"
        ).eq("school_id", school_id).gte(
            "scheduled_time", start_time.isoformat()
        ).lte(
            "scheduled_time", end_time.isoformat()
        ).order("scheduled_time").execute()

        return response.data
    except Exception as e:
        print(f"Error fetching pickups: {e}")
        return []


async def get_school_info(school_id: str) -> Dict[str, Any]:
    """Get school information."""
    supabase = get_supabase()

    if not supabase:
        return {
            "id": school_id,
            "name": "École Primaire Exemple",
            "address": "123 Rue Principale, Montréal, QC",
        }

    try:
        response = supabase.table("schools").select("*").eq("id", school_id).single().execute()
        return response.data
    except Exception as e:
        print(f"Error fetching school info: {e}")
        return {"id": school_id, "name": "École Inconnue"}


# ═══════════════════════════════════════════════════════════════
# MCP SERVER SETUP
# ═══════════════════════════════════════════════════════════════


mcp = FastMCP(
    name="allobye-server",
    stateless_http=True,
)


def _tool_meta(widget: Optional[AllobyeWidget] = None) -> Dict[str, Any]:
    """Generate tool metadata."""
    meta = {
        "annotations": {
            "destructiveHint": False,
            "openWorldHint": False,
            "readOnlyHint": True,
        }
    }

    if widget:
        meta.update({
            "openai/outputTemplate": widget.template_uri,
            "openai/toolInvocation/invoking": widget.invoking,
            "openai/toolInvocation/invoked": widget.invoked,
            "openai/widgetAccessible": True,
            "openai/resultCanProduceWidget": True,
        })

    return meta


def _embedded_widget_resource(widget: AllobyeWidget) -> types.EmbeddedResource:
    """Create embedded widget resource."""
    return types.EmbeddedResource(
        type="resource",
        resource=types.TextResourceContents(
            uri=widget.template_uri,
            mimeType=MIME_TYPE,
            text=widget.html,
            title=widget.title,
        ),
    )


# ═══════════════════════════════════════════════════════════════
# MCP TOOL IMPLEMENTATIONS
# ═══════════════════════════════════════════════════════════════


@mcp._mcp_server.list_tools()
async def _list_tools() -> List[types.Tool]:
    """List all available AllôBye tools."""
    return [
        # Authentication tools
        types.Tool(
            name="auth-signup",
            title="Inscription",
            description="Register a new user account (parent or school staff) with email and password.",
            inputSchema=AuthSignupInput.model_json_schema(),
            _meta=_tool_meta(),
        ),
        types.Tool(
            name="auth-login",
            title="Connexion",
            description="Login with email and password. Returns access token for authenticated requests.",
            inputSchema=AuthLoginInput.model_json_schema(),
            _meta=_tool_meta(),
        ),
        types.Tool(
            name="auth-logout",
            title="Déconnexion",
            description="Logout and invalidate current session.",
            inputSchema={
                "type": "object",
                "properties": {
                    "accessToken": {
                        "type": "string",
                        "description": "Access token to invalidate",
                    }
                },
                "required": ["accessToken"],
            },
            _meta=_tool_meta(),
        ),
        types.Tool(
            name="auth-reset-password",
            title="Réinitialiser mot de passe",
            description="Request password reset email.",
            inputSchema=AuthResetPasswordInput.model_json_schema(),
            _meta=_tool_meta(),
        ),
        types.Tool(
            name="auth-profile",
            title="Profil utilisateur",
            description="Get current user profile with associated schools and children.",
            inputSchema={
                "type": "object",
                "properties": {
                    "accessToken": {
                        "type": "string",
                        "description": "Access token",
                    }
                },
                "required": ["accessToken"],
            },
            _meta=_tool_meta(),
        ),
        # Pickup management tools
        types.Tool(
            name="pickup-schedule-create",
            title="Planifier un ramassage",
            description="Schedule a pickup for one or more children. Handles multi-child, multi-school coordination automatically. Requires authentication.",
            inputSchema=PickupScheduleInput.model_json_schema(),
            _meta=_tool_meta(),
        ),
        types.Tool(
            name="delegate-authorize",
            title="Autoriser un délégué",
            description="Authorize a person to pick up children. Automatically syncs across all affected schools. Requires parent authentication.",
            inputSchema=DelegateAuthorizeInput.model_json_schema(),
            _meta=_tool_meta(),
        ),
        types.Tool(
            name="emergency-declare",
            title="Déclarer une urgence",
            description="Declare an emergency affecting pickup. Automatically cascades to all authorized delegates and schools. Requires parent authentication.",
            inputSchema=EmergencyDeclareInput.model_json_schema(),
            _meta=_tool_meta(),
        ),
        types.Tool(
            name="school-dashboard-fetch",
            title="Tableau de bord école",
            description="Fetch current pickup queue for school tablet display. Returns data optimized for fullscreen React widget. Requires school staff authentication.",
            inputSchema=SchoolDashboardInput.model_json_schema(),
            _meta=_tool_meta(SCHOOL_DASHBOARD_WIDGET),
        ),
    ]


# ═══════════════════════════════════════════════════════════════
# AUTHENTICATION TOOL HANDLERS
# ═══════════════════════════════════════════════════════════════


async def _handle_auth_signup(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle user signup."""
    try:
        payload = AuthSignupInput.model_validate(arguments)
    except ValidationError as exc:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur de validation: {exc.errors()}",
                )
            ],
            isError=True,
        )

    try:
        result = await signup_user(
            email=payload.email,
            password=payload.password,
            name=payload.name,
            role=payload.role,
            schools=payload.schools,
        )

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"✓ Compte créé avec succès pour {payload.email}. Veuillez vérifier votre email.",
                )
            ],
            structuredContent={
                "user_id": result["user"]["id"],
                "email": result["user"]["email"],
                "email_verified": result["user"]["email_verified"],
            },
            _meta={
                "session": result["session"],
                "requires_verification": not result["user"]["email_verified"],
            },
        )
    except AuthenticationError as e:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur d'inscription: {str(e)}",
                )
            ],
            isError=True,
        )


async def _handle_auth_login(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle user login."""
    try:
        payload = AuthLoginInput.model_validate(arguments)
    except ValidationError as exc:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur de validation: {exc.errors()}",
                )
            ],
            isError=True,
        )

    try:
        result = await login_user(email=payload.email, password=payload.password)

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"✓ Connexion réussie! Bienvenue {result['profile'].get('name') or result['user']['email']}",
                )
            ],
            structuredContent={
                "user_id": result["user"]["id"],
                "email": result["user"]["email"],
                "role": result["profile"]["role"],
                "access_token": result["session"]["access_token"],
            },
            _meta={
                "session": result["session"],
                "profile": result["profile"],
            },
        )
    except InvalidCredentialsError as e:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text="Email ou mot de passe incorrect.",
                )
            ],
            isError=True,
        )
    except AuthenticationError as e:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur de connexion: {str(e)}",
                )
            ],
            isError=True,
        )


async def _handle_auth_logout(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle user logout."""
    access_token = arguments.get("accessToken") or arguments.get("access_token")

    if not access_token:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text="Token d'accès requis pour la déconnexion",
                )
            ],
            isError=True,
        )

    try:
        result = await logout_user(access_token=access_token)

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text="✓ Déconnexion réussie",
                )
            ],
            structuredContent=result,
        )
    except AuthenticationError as e:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur de déconnexion: {str(e)}",
                )
            ],
            isError=True,
        )


async def _handle_auth_reset_password(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle password reset request."""
    try:
        payload = AuthResetPasswordInput.model_validate(arguments)
    except ValidationError as exc:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur de validation: {exc.errors()}",
                )
            ],
            isError=True,
        )

    try:
        result = await reset_password_request(email=payload.email)

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=result["message"],
                )
            ],
            structuredContent=result,
        )
    except AuthenticationError as e:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur: {str(e)}",
                )
            ],
            isError=True,
        )


async def _handle_auth_profile(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle get user profile."""
    access_token = arguments.get("accessToken") or arguments.get("access_token")

    if not access_token:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text="Token d'accès requis",
                )
            ],
            isError=True,
        )

    try:
        user = await validate_session(access_token)

        if not user:
            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text="Session invalide ou expirée",
                    )
                ],
                isError=True,
            )

        profile = await get_user_profile(user.id)

        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Profil: {profile['name'] or profile['email']} ({profile['role']})",
                )
            ],
            structuredContent=profile,
        )
    except SessionExpiredError:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text="Session expirée. Veuillez vous reconnecter.",
                )
            ],
            isError=True,
        )
    except AuthenticationError as e:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur: {str(e)}",
                )
            ],
            isError=True,
        )


# ═══════════════════════════════════════════════════════════════
# PICKUP MANAGEMENT TOOL HANDLERS
# ═══════════════════════════════════════════════════════════════


async def _handle_pickup_schedule_create(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle pickup scheduling tool."""
    # Check authentication
    user = await get_current_user(arguments)
    if not require_auth(user, role="parent"):
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text="Authentification requise. Veuillez vous connecter en tant que parent.",
                )
            ],
            isError=True,
        )

    try:
        payload = PickupScheduleInput.model_validate(arguments)
    except ValidationError as exc:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur de validation: {exc.errors()}",
                )
            ],
            isError=True,
        )

    # Verify parent owns all children
    for child_id in payload.child_ids:
        if not await verify_parent_owns_child(user.id, child_id):
            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=f"Vous n'êtes pas autorisé à planifier un ramassage pour l'enfant {child_id}",
                    )
                ],
                isError=True,
            )

    # Get schools for children
    schools = await get_schools_for_children(payload.child_ids)

    # Coordinate pickup (multi-school if needed)
    if len(schools) > 1:
        results = await coordinate_cross_school_pickup(
            payload.child_ids,
            payload.pickup_person_id,
            payload.scheduled_time,
            payload.notes,
        )
    else:
        results = await create_pickup_request(
            payload.child_ids,
            payload.pickup_person_id,
            payload.scheduled_time,
            payload.notes,
        )

    # Format time for display
    try:
        scheduled_dt = datetime.fromisoformat(payload.scheduled_time.replace("Z", "+00:00"))
        time_str = scheduled_dt.strftime("%H:%M")
    except:
        time_str = payload.scheduled_time

    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=f"✓ Ramassage confirmé pour {len(payload.child_ids)} enfant(s) à {time_str}",
            )
        ],
        structuredContent={
            "pickup_id": results["id"],
            "children": payload.child_ids,
            "status": "confirmed",
            "scheduled_time": payload.scheduled_time,
        },
        _meta={
            "full_results": results,
            "schools_affected": [s["name"] for s in schools],
            "display_update": True,
        },
    )


async def _handle_delegate_authorize(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle delegate authorization tool."""
    # Check authentication
    user = await get_current_user(arguments)
    if not require_auth(user, role="parent"):
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text="Authentification requise. Veuillez vous connecter en tant que parent.",
                )
            ],
            isError=True,
        )

    try:
        payload = DelegateAuthorizeInput.model_validate(arguments)
    except ValidationError as exc:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur de validation: {exc.errors()}",
                )
            ],
            isError=True,
        )

    # Verify parent owns all children
    for child_id in payload.child_ids:
        if not await verify_parent_owns_child(user.id, child_id):
            return types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=f"Vous n'êtes pas autorisé à gérer les délégués pour l'enfant {child_id}",
                    )
                ],
                isError=True,
            )

    # Infer schools from children if not provided
    schools = await get_schools_for_children(payload.child_ids)

    # Broadcast authorization via A2A
    sync_results = await broadcast_delegate_authorization(
        payload.delegate_email,
        payload.child_ids,
        payload.permissions,
        schools,
    )

    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=f"✓ {payload.delegate_email} autorisé(e) pour {len(payload.child_ids)} enfant(s) dans {len(schools)} école(s)",
            )
        ],
        structuredContent={
            "delegate_id": sync_results["delegate_id"],
            "authorized_schools": [s["id"] for s in schools],
        },
        _meta={
            "sync_status": sync_results,
            "a2a_messages": sync_results["messages"],
        },
    )


async def _handle_emergency_declare(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle emergency declaration tool."""
    # Check authentication
    user = await get_current_user(arguments)
    if not require_auth(user, role="parent"):
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text="Authentification requise. Veuillez vous connecter en tant que parent.",
                )
            ],
            isError=True,
        )

    try:
        payload = EmergencyDeclareInput.model_validate(arguments)
    except ValidationError as exc:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur de validation: {exc.errors()}",
                )
            ],
            isError=True,
        )

    # Verify parent owns child
    if not await verify_parent_owns_child(user.id, payload.child_id):
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Vous n'êtes pas autorisé à déclarer une urgence pour cet enfant",
                )
            ],
            isError=True,
        )

    # Get delegates and schools
    delegates = await get_authorized_delegates(payload.child_id)
    schools = await get_schools_for_children([payload.child_id])

    # Broadcast emergency via A2A
    cascade_results = await broadcast_emergency(
        payload.child_id,
        payload.emergency_type,
        payload.context,
        delegates,
        schools,
    )

    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=f"🚨 Urgence déclarée. {len(delegates)} délégué(s) et {len(schools)} école(s) notifié(s).",
            )
        ],
        structuredContent={
            "emergency_id": cascade_results["id"],
            "notified_count": len(delegates) + len(schools),
        },
        _meta={
            "cascade_trace": cascade_results["a2a_trace"],
            "display_alerts": True,
        },
    )


async def _handle_school_dashboard_fetch(arguments: Dict[str, Any]) -> types.CallToolResult:
    """Handle school dashboard fetch tool."""
    # Check authentication
    user = await get_current_user(arguments)
    if not require_auth(user, role="school_staff"):
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text="Authentification requise. Veuillez vous connecter en tant que personnel scolaire.",
                )
            ],
            isError=True,
        )

    try:
        payload = SchoolDashboardInput.model_validate(arguments)
    except ValidationError as exc:
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Erreur de validation: {exc.errors()}",
                )
            ],
            isError=True,
        )

    # Verify staff has access to this school
    if not await verify_staff_at_school(user.id, payload.school_id):
        return types.CallToolResult(
            content=[
                types.TextContent(
                    type="text",
                    text=f"Vous n'êtes pas autorisé à accéder au tableau de bord de cette école",
                )
            ],
            isError=True,
        )

    # Get pickup queue
    pickups = await get_school_pickups(
        payload.school_id,
        payload.date or datetime.now().strftime("%Y-%m-%d"),
        payload.time_window,
    )

    # Get school info
    school_info = await get_school_info(payload.school_id)

    # Create widget resource
    widget_resource = _embedded_widget_resource(SCHOOL_DASHBOARD_WIDGET)

    return types.CallToolResult(
        content=[
            types.TextContent(
                type="text",
                text=f"{len(pickups)} ramassages prévus dans la fenêtre {payload.time_window}",
            )
        ],
        structuredContent={
            "count": len(pickups),
            "next_pickup": pickups[0] if pickups else None,
        },
        _meta={
            "openai.com/widget": widget_resource.model_dump(mode="json"),
            "openai/outputTemplate": SCHOOL_DASHBOARD_WIDGET.template_uri,
            "openai/toolInvocation/invoking": SCHOOL_DASHBOARD_WIDGET.invoking,
            "openai/toolInvocation/invoked": SCHOOL_DASHBOARD_WIDGET.invoked,
            "openai/widgetAccessible": True,
            "openai/resultCanProduceWidget": True,
            "pickups": pickups,
            "school_info": school_info,
            "display_mode": "fullscreen",
            "refresh_interval": 30,
        },
    )


# ═══════════════════════════════════════════════════════════════
# MCP REQUEST HANDLERS
# ═══════════════════════════════════════════════════════════════


async def _call_tool_request(req: types.CallToolRequest) -> types.ServerResult:
    """Handle tool calls."""
    tool_name = req.params.name
    arguments = req.params.arguments or {}

    handlers = {
        # Authentication tools
        "auth-signup": _handle_auth_signup,
        "auth-login": _handle_auth_login,
        "auth-logout": _handle_auth_logout,
        "auth-reset-password": _handle_auth_reset_password,
        "auth-profile": _handle_auth_profile,
        # Pickup management tools
        "pickup-schedule-create": _handle_pickup_schedule_create,
        "delegate-authorize": _handle_delegate_authorize,
        "emergency-declare": _handle_emergency_declare,
        "school-dashboard-fetch": _handle_school_dashboard_fetch,
    }

    handler = handlers.get(tool_name)
    if not handler:
        return types.ServerResult(
            types.CallToolResult(
                content=[
                    types.TextContent(
                        type="text",
                        text=f"Outil inconnu: {tool_name}",
                    )
                ],
                isError=True,
            )
        )

    result = await handler(arguments)
    return types.ServerResult(result)


async def _handle_read_resource(req: types.ReadResourceRequest) -> types.ServerResult:
    """Handle resource reads."""
    resource_uri = str(req.params.uri)

    if resource_uri != SCHOOL_DASHBOARD_WIDGET.template_uri:
        return types.ServerResult(
            types.ReadResourceResult(
                contents=[],
                _meta={"error": f"Unknown resource: {req.params.uri}"},
            )
        )

    contents = [
        types.TextResourceContents(
            uri=SCHOOL_DASHBOARD_WIDGET.template_uri,
            mimeType=MIME_TYPE,
            text=SCHOOL_DASHBOARD_WIDGET.html,
            _meta=_tool_meta(SCHOOL_DASHBOARD_WIDGET),
        )
    ]

    return types.ServerResult(types.ReadResourceResult(contents=contents))


@mcp._mcp_server.list_resources()
async def _list_resources() -> List[types.Resource]:
    """List available resources."""
    return [
        types.Resource(
            name=SCHOOL_DASHBOARD_WIDGET.title,
            title=SCHOOL_DASHBOARD_WIDGET.title,
            uri=SCHOOL_DASHBOARD_WIDGET.template_uri,
            description="School dashboard widget markup",
            mimeType=MIME_TYPE,
            _meta=_tool_meta(SCHOOL_DASHBOARD_WIDGET),
        )
    ]


@mcp._mcp_server.list_resource_templates()
async def _list_resource_templates() -> List[types.ResourceTemplate]:
    """List resource templates."""
    return [
        types.ResourceTemplate(
            name=SCHOOL_DASHBOARD_WIDGET.title,
            title=SCHOOL_DASHBOARD_WIDGET.title,
            uriTemplate=SCHOOL_DASHBOARD_WIDGET.template_uri,
            description="School dashboard widget markup",
            mimeType=MIME_TYPE,
            _meta=_tool_meta(SCHOOL_DASHBOARD_WIDGET),
        )
    ]


# Register handlers
mcp._mcp_server.request_handlers[types.CallToolRequest] = _call_tool_request
mcp._mcp_server.request_handlers[types.ReadResourceRequest] = _handle_read_resource

# Create ASGI app
app = mcp.streamable_http_app()

# Add CORS middleware
try:
    from starlette.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=False,
    )
except Exception:
    pass


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
