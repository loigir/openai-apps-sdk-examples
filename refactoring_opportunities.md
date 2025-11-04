# AllôBye - Opportunités de Refactoring

**Date**: 2025-11-04
**Focus**: Qualité du code, maintenabilité, DRY principle
**Impact estimé**: Réduction de ~2000 lignes de code dupliqué

---

## Table des Matières
1. [Vue d'Ensemble](#vue-densemble)
2. [Refactorings Python](#refactorings-python)
3. [Refactorings React](#refactorings-react)
4. [Refactorings SQL](#refactorings-sql)
5. [Architecture Suggestions](#architecture-suggestions)
6. [Plan d'Implémentation](#plan-dimplémentation)

---

## Vue d'Ensemble

### Métriques Actuelles
- **Duplication Code Python**: 83% (2400/2900 lignes)
- **Duplication Code React**: 25% (300/1200 lignes)
- **Duplication Code SQL**: 8% (50/620 lignes)

### Objectifs du Refactoring
- Réduire duplication Python à **< 15%**
- Réduire duplication React à **< 10%**
- Améliorer testabilité et maintenabilité
- Centraliser configuration et utilitaires
- Respecter les principes SOLID et DRY

---

## Refactorings Python

### 🔴 R1. Supprimer main_backup.py (CRITIQUE)

**Impact**: Élimine 1472 lignes dupliquées (50% du code Python)
**Effort**: Faible (1-2 heures)
**Risque**: Faible

**Action**:
```bash
# Option 1: Supprimer complètement si inutilisé
rm allobye_server_python/main_backup.py

# Option 2: Convertir en tests d'intégration
mv allobye_server_python/main_backup.py tests/integration/test_main_without_monitoring.py
```

**Justification**:
- 98% de duplication avec main.py
- Seule différence: imports du système de monitoring
- Viole principe DRY de manière flagrante

---

### 🔴 R2. Créer Module Supabase Client Centralisé (CRITIQUE)

**Impact**: Élimine 57 lignes dupliquées
**Effort**: Moyen (2-3 heures)
**Risque**: Moyen (nécessite tests)

**Fichier**: `allobye_server_python/supabase_client.py`

**Code proposé**:
```python
"""Centralized Supabase client management for AllôBye."""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


class SupabaseClientError(Exception):
    """Exception raised for Supabase client errors."""
    pass


@lru_cache(maxsize=1)
def get_supabase_client():
    """Get Supabase client for authentication (ANON key).

    Uses ANON key for client-side auth operations.
    Returns None if initialization fails (mock mode).
    """
    try:
        from supabase import create_client, Client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")

        if not url or not key:
            raise SupabaseClientError(
                "SUPABASE_URL and SUPABASE_ANON_KEY must be set"
            )

        return create_client(url, key)
    except Exception as e:
        print(f"Warning: Supabase client initialization failed: {e}")
        return None


@lru_cache(maxsize=1)
def get_supabase_admin():
    """Get Supabase admin client for privileged operations.

    Uses SERVICE_ROLE key for server-side operations.
    Returns None if initialization fails (mock mode).
    """
    try:
        from supabase import create_client, Client

        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

        if not url or not key:
            raise SupabaseClientError(
                "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set"
            )

        return create_client(url, key)
    except Exception as e:
        print(f"Warning: Supabase admin client initialization failed: {e}")
        return None


def is_mock_mode() -> bool:
    """Check if running in mock mode (Supabase unavailable)."""
    return get_supabase_client() is None
```

**Migration**:
```python
# Dans auth.py et main.py, remplacer par:
from supabase_client import get_supabase_client, get_supabase_admin, is_mock_mode
```

---

### 🟠 R3. Créer Module Mock Data Factory (HAUTE)

**Impact**: Élimine ~200 lignes dupliquées
**Effort**: Moyen (3-4 heures)
**Risque**: Faible

**Fichier**: `allobye_server_python/mocks.py`

**Code proposé**:
```python
"""Mock data factory for AllôBye development and testing."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4


class MockDataFactory:
    """Factory for generating consistent mock data."""

    @staticmethod
    def user(
        email: str,
        name: Optional[str] = None,
        role: str = "parent",
        email_verified: bool = False
    ) -> Dict[str, Any]:
        """Generate mock user data."""
        user_id = str(uuid4())
        return {
            "user": {
                "id": user_id,
                "email": email,
                "email_verified": email_verified,
                "created_at": datetime.now().isoformat(),
            },
            "session": {
                "access_token": f"mock_token_{user_id}",
                "refresh_token": f"mock_refresh_{user_id}",
                "expires_at": (datetime.now() + timedelta(hours=1)).isoformat(),
            },
            "profile": {
                "id": user_id,
                "email": email,
                "name": name or "Mock User",
                "role": role,
                "schools": [],
                "children": [],
                "email_verified": email_verified,
            }
        }

    @staticmethod
    def school(school_id: Optional[str] = None, name: str = "École Primaire Exemple") -> Dict[str, Any]:
        """Generate mock school data."""
        return {
            "id": school_id or "school_1",
            "name": name,
            "address": "123 Rue Principale, Montréal, QC",
        }

    @staticmethod
    def pickup(
        child_ids: List[str],
        pickup_person_id: str,
        scheduled_time: str,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate mock pickup data."""
        return {
            "id": str(uuid4()),
            "child_ids": child_ids,
            "pickup_person_id": pickup_person_id,
            "scheduled_time": scheduled_time,
            "status": "confirmed",
            "notes": notes,
            "created_at": datetime.now().isoformat(),
        }

    @staticmethod
    def delegate(email: str, name: Optional[str] = None) -> Dict[str, Any]:
        """Generate mock delegate data."""
        return {
            "id": str(uuid4()),
            "email": email,
            "name": name or "Grand-maman",
            "permissions": ["pickup"],
        }

    @staticmethod
    def emergency(
        child_id: str,
        emergency_type: str,
        delegates_count: int = 0,
        schools_count: int = 0
    ) -> Dict[str, Any]:
        """Generate mock emergency data."""
        return {
            "id": str(uuid4()),
            "a2a_trace": [
                {"type": "delegate_notify", "count": delegates_count},
                {"type": "school_notify", "count": schools_count},
            ],
        }

    @staticmethod
    def school_pickups() -> List[Dict[str, Any]]:
        """Generate mock school pickups queue."""
        now = datetime.now()
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


# Convenience functions for backward compatibility
def mock_user_signup(email: str, **kwargs) -> Dict[str, Any]:
    return MockDataFactory.user(email, **kwargs)

def mock_user_login(email: str) -> Dict[str, Any]:
    return MockDataFactory.user(email, email_verified=True)

def mock_school(school_id: Optional[str] = None) -> List[Dict[str, Any]]:
    return [MockDataFactory.school(school_id)]
```

**Migration**:
```python
# Remplacer tous les blocs "if not supabase: return {...}" par:
from mocks import MockDataFactory

if not supabase:
    return MockDataFactory.user(email, name=name, role=role)
```

---

### 🟠 R4. Créer Module Database Helpers (HAUTE)

**Impact**: Élimine 284 lignes dupliquées
**Effort**: Élevé (4-6 heures)
**Risque**: Moyen

**Fichier**: `allobye_server_python/database.py`

**Code proposé**:
```python
"""Database helper functions for AllôBye."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from supabase_client import get_supabase_admin, is_mock_mode
from mocks import MockDataFactory


async def get_schools_for_children(child_ids: List[str]) -> List[Dict[str, Any]]:
    """Get unique schools for a list of children."""
    if is_mock_mode():
        return MockDataFactory.mock_school()

    supabase = get_supabase_admin()

    try:
        response = supabase.table("children").select(
            "school_id, schools(*)"
        ).in_("id", child_ids).execute()

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
    pickup_id = str(uuid4())

    if is_mock_mode():
        return MockDataFactory.pickup(
            child_ids, pickup_person_id, scheduled_time, notes
        )

    supabase = get_supabase_admin()

    try:
        pickup_data = {
            "id": pickup_id,
            "pickup_person_id": pickup_person_id,
            "scheduled_time": scheduled_time,
            "status": "confirmed",
            "notes": notes,
        }

        response = supabase.table("pickups").insert(pickup_data).execute()

        for child_id in child_ids:
            supabase.table("pickup_children").insert({
                "pickup_id": pickup_id,
                "child_id": child_id,
            }).execute()

        return response.data[0] if response.data else pickup_data
    except Exception as e:
        print(f"Error creating pickup: {e}")
        raise


# ... autres fonctions database helpers
```

**Migration**:
```python
# Dans main.py, importer:
from database import (
    get_schools_for_children,
    create_pickup_request,
    coordinate_cross_school_pickup,
    broadcast_delegate_authorization,
    get_authorized_delegates,
    broadcast_emergency,
    get_school_pickups,
    get_school_info,
)
```

---

### 🟡 R5. Créer Module Error Handling Standardisé (MOYENNE)

**Impact**: Améliore consistance
**Effort**: Moyen (2-3 heures)
**Risque**: Faible

**Fichier**: `allobye_server_python/errors.py`

**Code proposé**:
```python
"""Standardized error handling for AllôBye."""

from __future__ import annotations

import functools
import traceback
from typing import Any, Callable, Optional, TypeVar

from monitoring import get_logger

logger = get_logger()

T = TypeVar('T')


def handle_database_errors(
    default_return: Any = None,
    log_error: bool = True,
    raise_on_error: bool = False
):
    """Decorator for standardized database error handling.

    Args:
        default_return: Value to return on error (if not raising)
        log_error: Whether to log the error
        raise_on_error: Whether to raise the error after logging
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_error:
                    logger.error(
                        f"Database error in {func.__name__}",
                        error=str(e),
                        traceback=traceback.format_exc(),
                        args=args,
                        kwargs=kwargs
                    )

                if raise_on_error:
                    raise

                return default_return

        return wrapper

    return decorator


def handle_auth_errors(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for standardized authentication error handling."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> T:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            error_msg = str(e).lower()

            # Map common errors to user-friendly messages
            if "already registered" in error_msg or "duplicate" in error_msg:
                from auth import UserAlreadyExistsError
                raise UserAlreadyExistsError("User already exists")
            elif "invalid" in error_msg or "credentials" in error_msg:
                from auth import InvalidCredentialsError
                raise InvalidCredentialsError("Invalid credentials")
            elif "expired" in error_msg:
                from auth import SessionExpiredError
                raise SessionExpiredError("Session expired")
            else:
                from auth import AuthenticationError
                raise AuthenticationError(f"Authentication failed: {e}")

    return wrapper
```

**Usage**:
```python
@handle_database_errors(default_return=[], log_error=True)
async def get_schools_for_children(child_ids: List[str]) -> List[Dict[str, Any]]:
    # ... function implementation
```

---

## Refactorings React

### 🟠 R6. Créer Custom Hook useMCPTool (HAUTE)

**Impact**: Élimine ~50 lignes dupliquées
**Effort**: Faible (1-2 heures)
**Risque**: Faible

**Fichier**: `src/hooks/useMCPTool.js`

**Code proposé**:
```javascript
import { useState, useCallback } from 'react';

/**
 * Custom hook for calling MCP tools with error handling and loading state
 *
 * @returns {Object} { callTool, loading, error }
 */
export function useMCPTool() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const callTool = useCallback(async (toolName, args) => {
    setLoading(true);
    setError(null);

    try {
      if (!window.openai?.callTool) {
        throw new Error('MCP tools not available');
      }

      const result = await window.openai.callTool(toolName, args);
      setLoading(false);
      return result;
    } catch (err) {
      console.error(`MCP tool error [${toolName}]:`, err);
      setError(err.message || 'Unknown error');
      setLoading(false);
      throw err;
    }
  }, []);

  return { callTool, loading, error };
}

/**
 * Custom hook for authenticated MCP tool calls
 * Automatically includes access token from localStorage
 */
export function useMCPToolAuth() {
  const { callTool: baseCallTool, loading, error } = useMCPTool();

  const callTool = useCallback(async (toolName, args) => {
    const token = localStorage.getItem('allobye_token');

    if (!token) {
      throw new Error('No authentication token found');
    }

    return baseCallTool(toolName, {
      ...args,
      accessToken: token,
    });
  }, [baseCallTool]);

  return { callTool, loading, error };
}
```

**Migration**:
```jsx
// Avant:
const handleLogin = async (e) => {
  setState({ ...state, loading: true, error: null });
  try {
    if (!window.openai?.callTool) {
      throw new Error("MCP tools not available");
    }
    const result = await window.openai.callTool("auth-login", {...});
    // ... handle result
  } catch (error) {
    setState({ ...state, loading: false, error: error.message });
  }
};

// Après:
const { callTool, loading, error } = useMCPTool();

const handleLogin = async (e) => {
  try {
    const result = await callTool("auth-login", {
      email: formData.email,
      password: formData.password,
    });
    // ... handle result
  } catch (error) {
    // Error already handled by hook
  }
};
```

---

### 🟠 R7. Créer Service Session Storage (HAUTE)

**Impact**: Élimine ~30 lignes dupliquées
**Effort**: Faible (1 heure)
**Risque**: Faible

**Fichier**: `src/services/sessionStorage.js`

**Code proposé**:
```javascript
/**
 * Centralized session storage management for AllôBye
 */

const TOKEN_KEY = 'allobye_token';
const USER_KEY = 'allobye_user';

/**
 * Session storage service
 */
export const sessionStorage = {
  /**
   * Store user session
   */
  setSession(token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },

  /**
   * Get access token
   */
  getToken() {
    return localStorage.getItem(TOKEN_KEY);
  },

  /**
   * Get user data
   */
  getUser() {
    const userStr = localStorage.getItem(USER_KEY);
    if (!userStr) return null;

    try {
      return JSON.parse(userStr);
    } catch (error) {
      console.error('Error parsing user data:', error);
      return null;
    }
  },

  /**
   * Get complete session
   */
  getSession() {
    return {
      token: this.getToken(),
      user: this.getUser(),
    };
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated() {
    return !!this.getToken();
  },

  /**
   * Clear session
   */
  clearSession() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  },

  /**
   * Update user data
   */
  updateUser(user) {
    localStorage.setItem(USER_KEY, JSON.stringify(user));
  },
};

export default sessionStorage;
```

**Migration**:
```jsx
// Avant:
localStorage.setItem("allobye_token", token);
localStorage.setItem("allobye_user", JSON.stringify(user));

// Après:
import sessionStorage from '../services/sessionStorage';
sessionStorage.setSession(token, user);
```

---

### 🟡 R8. Créer Utilitaires Date/Time (MOYENNE)

**Impact**: Élimine ~30 lignes dupliquées
**Effort**: Faible (1-2 heures)
**Risque**: Faible

**Fichier**: `src/utils/dateFormatters.js`

**Code proposé**:
```javascript
/**
 * Date and time formatting utilities for AllôBye
 */

const LOCALE_FR_CA = 'fr-CA';

/**
 * Format time in HH:MM format
 */
export function formatTime(date) {
  return date.toLocaleTimeString(LOCALE_FR_CA, {
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format full datetime
 */
export function formatDateTime(date) {
  return date.toLocaleString(LOCALE_FR_CA, {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/**
 * Format date only
 */
export function formatDate(date) {
  return date.toLocaleDateString(LOCALE_FR_CA, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

/**
 * Get relative time label (e.g., "Dans 10 min", "En retard")
 */
export function getTimeLabel(minutesUntil) {
  if (minutesUntil < 0) return 'En retard';
  if (minutesUntil === 0) return 'Maintenant';
  if (minutesUntil < 60) return `Dans ${minutesUntil} min`;

  const hours = Math.floor(minutesUntil / 60);
  const mins = minutesUntil % 60;
  return `Dans ${hours}h${mins > 0 ? mins.toString().padStart(2, '0') : ''}`;
}

/**
 * Calculate minutes between two dates
 */
export function getMinutesUntil(targetDate, fromDate = new Date()) {
  return Math.floor((targetDate - fromDate) / 1000 / 60);
}

/**
 * Get time ago label (e.g., "5m ago", "2h ago")
 */
export function getTimeAgo(date) {
  const seconds = Math.floor((new Date() - date) / 1000);

  if (seconds < 60) return `${seconds}s ago`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}
```

---

### 🟡 R9. Créer Constants et Mappings (MOYENNE)

**Impact**: Élimine ~50 lignes dupliquées
**Effort**: Faible (1 heure)
**Risque**: Faible

**Fichier**: `src/constants/index.js`

**Code proposé**:
```javascript
/**
 * Application constants and mappings for AllôBye
 */

// Emergency Types
export const EMERGENCY_TYPES = {
  LATE: 'late',
  ILLNESS: 'illness',
  CANCEL: 'cancel',
  INJURY: 'injury',
  OTHER: 'other',
};

export const EMERGENCY_CONFIG = {
  [EMERGENCY_TYPES.LATE]: {
    icon: '⏰',
    title: 'Retard signalé',
    color: '#f59e0b',
  },
  [EMERGENCY_TYPES.ILLNESS]: {
    icon: '🤒',
    title: 'Maladie signalée',
    color: '#ef4444',
  },
  [EMERGENCY_TYPES.CANCEL]: {
    icon: '❌',
    title: 'Ramassage annulé',
    color: '#6b7280',
  },
  [EMERGENCY_TYPES.INJURY]: {
    icon: '🚑',
    title: 'Blessure signalée',
    color: '#dc2626',
  },
  [EMERGENCY_TYPES.OTHER]: {
    icon: '🚨',
    title: 'Urgence déclarée',
    color: '#ef4444',
  },
};

// Pickup Status
export const PICKUP_STATUS = {
  PENDING: 'pending',
  IN_PROGRESS: 'in_progress',
  COMPLETED: 'completed',
  CANCELLED: 'cancelled',
};

export const STATUS_CONFIG = {
  [PICKUP_STATUS.PENDING]: {
    label: 'En attente',
    color: '#3b82f6',
  },
  [PICKUP_STATUS.IN_PROGRESS]: {
    label: 'En cours',
    color: '#f59e0b',
  },
  [PICKUP_STATUS.COMPLETED]: {
    label: 'Complété',
    color: '#10b981',
  },
  [PICKUP_STATUS.CANCELLED]: {
    label: 'Annulé',
    color: '#6b7280',
  },
};

// System Health Status
export const HEALTH_STATUS = {
  HEALTHY: 'healthy',
  DEGRADED: 'degraded',
  UNHEALTHY: 'unhealthy',
};

export const HEALTH_CONFIG = {
  [HEALTH_STATUS.HEALTHY]: {
    label: 'Healthy',
    color: '#10b981',
  },
  [HEALTH_STATUS.DEGRADED]: {
    label: 'Degraded',
    color: '#f59e0b',
  },
  [HEALTH_STATUS.UNHEALTHY]: {
    label: 'Unhealthy',
    color: '#ef4444',
  },
};

// Alert Severity
export const ALERT_SEVERITY = {
  CRITICAL: 'critical',
  WARNING: 'warning',
  INFO: 'info',
};

export const SEVERITY_CONFIG = {
  [ALERT_SEVERITY.CRITICAL]: {
    icon: '🚨',
    color: '#ef4444',
  },
  [ALERT_SEVERITY.WARNING]: {
    icon: '⚠️',
    color: '#f59e0b',
  },
  [ALERT_SEVERITY.INFO]: {
    icon: 'ℹ️',
    color: '#3b82f6',
  },
};

// Helper functions
export function getEmergencyIcon(type) {
  return EMERGENCY_CONFIG[type]?.icon || EMERGENCY_CONFIG[EMERGENCY_TYPES.OTHER].icon;
}

export function getEmergencyTitle(type) {
  return EMERGENCY_CONFIG[type]?.title || EMERGENCY_CONFIG[EMERGENCY_TYPES.OTHER].title;
}

export function getStatusColor(status) {
  return STATUS_CONFIG[status]?.color || STATUS_CONFIG[PICKUP_STATUS.PENDING].color;
}

export function getHealthColor(status) {
  return HEALTH_CONFIG[status]?.color || HEALTH_CONFIG[HEALTH_STATUS.DEGRADED].color;
}
```

---

### 🟡 R10. Créer Custom Hook useAutoRefresh (MOYENNE)

**Impact**: Élimine ~20 lignes dupliquées
**Effort**: Faible (1 heure)
**Risque**: Faible

**Fichier**: `src/hooks/useAutoRefresh.js`

**Code proposé**:
```javascript
import { useEffect, useRef } from 'react';

/**
 * Custom hook for auto-refreshing data at regular intervals
 *
 * @param {Function} callback - Function to call on each refresh
 * @param {number} intervalSeconds - Refresh interval in seconds
 * @param {boolean} enabled - Whether auto-refresh is enabled
 * @param {Array} dependencies - Dependencies to restart the interval
 */
export function useAutoRefresh(callback, intervalSeconds = 30, enabled = true, dependencies = []) {
  const savedCallback = useRef();

  // Remember the latest callback
  useEffect(() => {
    savedCallback.current = callback;
  }, [callback]);

  // Set up the interval
  useEffect(() => {
    if (!enabled) return;

    const tick = () => {
      if (savedCallback.current) {
        savedCallback.current();
      }
    };

    const interval = setInterval(tick, intervalSeconds * 1000);

    // Call immediately on mount
    tick();

    return () => clearInterval(interval);
  }, [intervalSeconds, enabled, ...dependencies]);
}

export default useAutoRefresh;
```

**Migration**:
```jsx
// Avant:
useEffect(() => {
  const interval = setInterval(() => {
    // refresh logic
  }, refreshInterval * 1000);
  return () => clearInterval(interval);
}, [refreshInterval]);

// Après:
import { useAutoRefresh } from '../hooks/useAutoRefresh';

useAutoRefresh(
  () => {
    // refresh logic
  },
  refreshInterval,
  autoRefreshEnabled,
  [schoolInfo]
);
```

---

### 🟡 R11. Refactoriser AuthForm en Composant Réutilisable (MOYENNE)

**Impact**: Élimine ~100 lignes dupliquées
**Effort**: Moyen (2-3 heures)
**Risque**: Faible

**Fichier**: `src/components/AuthForm.jsx`

**Code proposé**:
```jsx
import { useState } from 'react';

/**
 * Reusable authentication form component
 *
 * @param {Object} props
 * @param {string} props.mode - Form mode: 'login', 'signup', 'reset'
 * @param {Function} props.onSubmit - Submit handler
 * @param {boolean} props.loading - Loading state
 * @param {string} props.error - Error message
 * @param {Function} props.onModeChange - Mode change handler
 */
export default function AuthForm({ mode, onSubmit, loading, error, onModeChange }) {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    name: '',
    role: 'parent',
    confirmPassword: '',
  });

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit(formData);
  };

  const formConfig = {
    login: {
      title: 'Connexion',
      submitText: loading ? 'Connexion...' : 'Se connecter',
      fields: ['email', 'password'],
      links: [
        { text: 'Mot de passe oublié?', mode: 'reset' },
        { text: 'Créer un compte', mode: 'signup' },
      ],
    },
    signup: {
      title: 'Inscription',
      submitText: loading ? 'Création...' : 'Créer mon compte',
      fields: ['name', 'email', 'role', 'password', 'confirmPassword'],
      links: [
        { text: 'Déjà un compte? Se connecter', mode: 'login' },
      ],
    },
    reset: {
      title: 'Réinitialiser le mot de passe',
      submitText: loading ? 'Envoi...' : 'Envoyer le lien',
      description: 'Entrez votre email et nous vous enverrons un lien pour réinitialiser votre mot de passe.',
      fields: ['email'],
      links: [
        { text: 'Retour à la connexion', mode: 'login' },
      ],
    },
  };

  const config = formConfig[mode];

  return (
    <form onSubmit={handleSubmit} className="auth-form">
      <h2>{config.title}</h2>
      {config.description && <p className="form-description">{config.description}</p>}

      {/* Render form fields based on config */}
      {config.fields.includes('name') && (
        <FormField
          label="Nom complet"
          type="text"
          name="name"
          value={formData.name}
          onChange={handleChange}
          placeholder="Jean Tremblay"
        />
      )}

      {config.fields.includes('email') && (
        <FormField
          label="Email"
          type="email"
          name="email"
          value={formData.email}
          onChange={handleChange}
          required
          placeholder="votre@email.com"
        />
      )}

      {config.fields.includes('role') && (
        <FormField
          label="Rôle"
          type="select"
          name="role"
          value={formData.role}
          onChange={handleChange}
          options={[
            { value: 'parent', label: 'Parent' },
            { value: 'school_staff', label: 'Personnel scolaire' },
          ]}
        />
      )}

      {config.fields.includes('password') && (
        <FormField
          label="Mot de passe"
          type="password"
          name="password"
          value={formData.password}
          onChange={handleChange}
          required
          placeholder="••••••••"
          minLength={6}
          hint={mode === 'signup' ? 'Minimum 6 caractères' : null}
        />
      )}

      {config.fields.includes('confirmPassword') && (
        <FormField
          label="Confirmer le mot de passe"
          type="password"
          name="confirmPassword"
          value={formData.confirmPassword}
          onChange={handleChange}
          required
          placeholder="••••••••"
        />
      )}

      <button type="submit" className="btn-primary" disabled={loading}>
        {config.submitText}
      </button>

      <div className="auth-links">
        {config.links.map((link, index) => (
          <button
            key={index}
            type="button"
            className="link-button"
            onClick={() => onModeChange(link.mode)}
          >
            {link.text}
          </button>
        ))}
      </div>
    </form>
  );
}

// Helper component for form fields
function FormField({ label, type, name, value, onChange, options, hint, ...props }) {
  return (
    <div className="form-group">
      <label htmlFor={name}>{label}</label>
      {type === 'select' ? (
        <select id={name} name={name} value={value} onChange={onChange} {...props}>
          {options.map(opt => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
      ) : (
        <input
          id={name}
          type={type}
          name={name}
          value={value}
          onChange={onChange}
          {...props}
        />
      )}
      {hint && <small>{hint}</small>}
    </div>
  );
}
```

---

## Refactorings SQL

### 🟢 R12. Clarifier Rôle de schema_production.sql (BASSE)

**Impact**: Améliore clarté
**Effort**: Faible (30 minutes)
**Risque**: Faible

**Actions**:
1. **Si schema_production.sql est obsolète**: SUPPRIMER
2. **Si c'est une version partielle**: COMPLÉTER ou DOCUMENTER
3. **Si c'est un fichier de migrations**: RENOMMER en `migrations/001_initial.sql`

**Recommandation**:
```bash
# Option recommandée: Supprimer et utiliser uniquement schema.sql
rm allobye_server_python/schema_production.sql

# Ou documenter clairement:
echo "# schema_production.sql - Production-only schema additions" > schema_production.md
```

---

### 🟢 R13. Créer Fonction Générique pour RLS Policies (BASSE)

**Impact**: Réduit verbosité SQL
**Effort**: Moyen (1-2 heures)
**Risque**: Faible

**Code proposé** (ajout à `schema.sql`):
```sql
-- Function to create service role policy for a table
CREATE OR REPLACE FUNCTION create_service_role_policy(table_name TEXT)
RETURNS VOID AS $$
BEGIN
    EXECUTE format(
        'CREATE POLICY "Service role can manage %I"
         ON %I FOR ALL
         USING (auth.jwt()->>''role'' = ''service_role'')
         WITH CHECK (auth.jwt()->>''role'' = ''service_role'')',
        table_name, table_name
    );
END;
$$ LANGUAGE plpgsql;

-- Apply to all tables
SELECT create_service_role_policy('schools');
SELECT create_service_role_policy('children');
SELECT create_service_role_policy('delegates');
SELECT create_service_role_policy('pickups');
SELECT create_service_role_policy('pickup_children');
SELECT create_service_role_policy('delegate_children');
SELECT create_service_role_policy('emergencies');
```

---

## Architecture Suggestions

### A1. Structure de Projet Proposée

```
allobye_server_python/
├── __init__.py
├── main.py                 # Entry point (simplifié)
├── config.py               # Configuration centralisée
├── supabase_client.py      # Clients Supabase
├── mocks.py                # Mock data factory
├── errors.py               # Error handling
├── auth/                   # Module authentication
│   ├── __init__.py
│   ├── handlers.py         # Auth handlers
│   └── models.py           # Auth models
├── database/               # Module database
│   ├── __init__.py
│   ├── helpers.py          # Database helpers
│   └── queries.py          # SQL queries
├── tools/                  # MCP Tools
│   ├── __init__.py
│   ├── auth_tools.py
│   ├── pickup_tools.py
│   └── monitoring_tools.py
├── widgets/                # Widget configuration
│   ├── __init__.py
│   └── loader.py
└── monitoring/             # Monitoring (already modular)
    └── ...

src/
├── hooks/                  # Custom React hooks
│   ├── useMCPTool.js
│   ├── useAutoRefresh.js
│   └── useSession.js
├── services/               # Services layer
│   ├── sessionStorage.js
│   └── api.js
├── utils/                  # Utilities
│   ├── dateFormatters.js
│   └── timeFormatters.js
├── constants/              # Constants
│   └── index.js
├── components/             # Shared components
│   ├── AuthForm.jsx
│   └── BaseDashboard.jsx
├── allobye-dashboard/      # Dashboard app
│   └── ...
└── allobye-monitoring/     # Monitoring app
    └── ...
```

---

### A2. Stratégie de Tests

**Créer suite de tests pour nouveaux modules**:

```python
# tests/unit/test_supabase_client.py
import pytest
from supabase_client import get_supabase_client, is_mock_mode

def test_get_supabase_client_mock_mode(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    assert is_mock_mode() is True

# tests/unit/test_mocks.py
from mocks import MockDataFactory

def test_mock_user():
    user = MockDataFactory.user("test@example.com")
    assert user["user"]["email"] == "test@example.com"
    assert "session" in user
```

---

## Plan d'Implémentation

### Phase 1: Nettoyage Critique (Semaine 1)
**Objectif**: Éliminer 98% duplication Python

1. ✅ **R1**: Supprimer main_backup.py (2h)
2. ✅ **R2**: Créer supabase_client.py (3h)
3. ✅ **R3**: Créer mocks.py (4h)
4. ✅ **R4**: Créer database.py (6h)

**Impact**: -2400 lignes dupliquées

---

### Phase 2: Amélioration React (Semaine 2)
**Objectif**: Réduire duplication React à 10%

5. ✅ **R6**: Custom hook useMCPTool (2h)
6. ✅ **R7**: Service sessionStorage (1h)
7. ✅ **R8**: Utilitaires date/time (2h)
8. ✅ **R9**: Constants et mappings (1h)
9. ✅ **R10**: Custom hook useAutoRefresh (1h)

**Impact**: -150 lignes dupliquées

---

### Phase 3: Refactoring Avancé (Semaine 3)
**Objectif**: Améliorer architecture globale

10. ✅ **R5**: Error handling standardisé (3h)
11. ✅ **R11**: Refactoriser AuthForm (3h)
12. ✅ **R12**: Clarifier schema SQL (1h)
13. ✅ **A1**: Réorganiser structure projet (4h)
14. ✅ **A2**: Ajouter tests unitaires (8h)

**Impact**: Meilleure maintenabilité

---

### Phase 4: Validation et Documentation (Semaine 4)
**Objectif**: Valider changements et documenter

15. Tests d'intégration complets
16. Documentation API mise à jour
17. Guide de migration pour l'équipe
18. Review de code par pairs

---

## Métriques de Succès

### Avant Refactoring
- **Duplication Python**: 83%
- **Duplication React**: 25%
- **Fichiers de test**: 1
- **Couverture tests**: ~5%

### Après Refactoring (Objectifs)
- **Duplication Python**: < 15%
- **Duplication React**: < 10%
- **Fichiers de test**: 20+
- **Couverture tests**: > 70%

---

## Conclusion

Ce plan de refactoring permettra de:
1. **Réduire drastiquement** la duplication de code (-2000 lignes)
2. **Améliorer la maintenabilité** avec une architecture modulaire
3. **Faciliter les tests** avec des composants découplés
4. **Accélérer le développement** futur avec des utilitaires réutilisables

**Estimation totale**: 40-50 heures de travail sur 4 semaines

**ROI estimé**: Réduction de 50% du temps de développement futur et de 70% des bugs liés à la duplication
