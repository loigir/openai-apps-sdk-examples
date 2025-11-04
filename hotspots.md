# Complexity Hotspots - AllôBye

**Date**: 2025-11-04
**Focus**: Top 15 fonctions/composants les plus complexes

---

## Top 15 Hotspots par Complexité

### 🔥 Niveau CRITIQUE (Cognitive Complexity > 15)

#### #1 - Supabase Real-time Subscription Setup
**File**: `src/allobye-dashboard/dashboard.jsx`
**Lines**: 57-144 (87 lignes)
**Cyclomatic Complexity**: 16
**Cognitive Complexity**: 18
**Nesting Depth**: 5

**Code Snippet**:
```javascript
useEffect(() => {
  if (!schoolInfo?.id) return;

  const setupRealtimeSubscription = async () => {
    try {
      const { createClient } = await import("@supabase/supabase-js");
      // ... 87 lignes de logique complexe
      const channel = supabase.channel("pickups-changes")
        .on("postgres_changes", { /* ... */ }, (payload) => {
          // Nested callback logic
        })
        .subscribe();
      // ... plus de subscriptions
    } catch (error) {
      // Error handling
    }
  };
  // ...
}, [schoolInfo?.id]);
```

**Problèmes**:
- ✗ Trop long (87 lignes)
- ✗ Async/await dans useEffect
- ✗ Callbacks imbriqués
- ✗ Multiple subscriptions dans un seul effet
- ✗ Logique de cleanup complexe
- ✗ State updates dans callbacks

**Impact**: **TRÈS ÉLEVÉ**
- Difficulté de test
- Bugs potentiels dans les subscriptions
- Memory leaks possibles
- Maintenance difficile

**Effort de Refactoring**: Medium (2-3 heures)

**Solution Recommandée**:
```javascript
// Créer un hook custom
function useRealtimePickups(schoolId) {
  const [pickups, setPickups] = useState([]);

  useEffect(() => {
    if (!schoolId) return;

    const subscription = subscribeToPickups(schoolId, (newPickup) => {
      setPickups(prev => updatePickupsList(prev, newPickup));
    });

    return () => subscription.unsubscribe();
  }, [schoolId]);

  return pickups;
}

function useRealtimeEmergencies(schoolId) {
  // Similar pattern for emergencies
}
```

---

#### #2 - Pickup Schedule Create Handler
**File**: `allobye_server_python/main.py`
**Lines**: 1023-1108 (85 lignes)
**Cyclomatic Complexity**: 15
**Cognitive Complexity**: 17
**Parameters**: 1 (Dict)

**Code Snippet**:
```python
async def _handle_pickup_schedule_create(arguments: Dict[str, Any]) -> types.CallToolResult:
    # Check authentication
    user = await get_current_user(arguments)
    if not require_auth(user, role="parent"):
        return types.CallToolResult(
            content=[types.TextContent(type="text", text="Authentification requise...")],
            isError=True,
        )

    try:
        payload = PickupScheduleInput.model_validate(arguments)
    except ValidationError as exc:
        return types.CallToolResult(...)

    # Verify parent owns all children
    for child_id in payload.child_ids:
        if not await verify_parent_owns_child(user.id, child_id):
            return types.CallToolResult(...)

    # Get schools for children
    schools = await get_schools_for_children(payload.child_ids)

    # Coordinate pickup (multi-school if needed)
    if len(schools) > 1:
        results = await coordinate_cross_school_pickup(...)
    else:
        results = await create_pickup_request(...)

    # Format time for display
    try:
        scheduled_dt = datetime.fromisoformat(...)
        time_str = scheduled_dt.strftime("%H:%M")
    except:
        time_str = payload.scheduled_time

    return types.CallToolResult(...)
```

**Problèmes**:
- ✗ Trop de responsabilités (auth, validation, business logic, formatting)
- ✗ Multiple early returns
- ✗ Boucle de validation avec async calls
- ✗ Nested try/except
- ✗ Formatage mélangé avec business logic

**Impact**: **ÉLEVÉ**
- Difficile à tester individuellement
- Duplication avec autres handlers
- Changements fragiles

**Effort de Refactoring**: Low (1-2 heures)

**Solution Recommandée**:
```python
@require_role("parent")
@validate_input(PickupScheduleInput)
async def _handle_pickup_schedule_create(user: UserProfile, payload: PickupScheduleInput):
    await validate_parent_owns_children(user.id, payload.child_ids)

    schools = await get_schools_for_children(payload.child_ids)
    results = await schedule_pickup(payload, schools)

    return format_pickup_result(results, payload)
```

---

#### #3 - Signup User Function
**File**: `allobye_server_python/auth.py`
**Lines**: 115-211 (96 lignes)
**Cyclomatic Complexity**: 14
**Cognitive Complexity**: 16
**Parameters**: 5

**Code Snippet**:
```python
async def signup_user(
    email: str,
    password: str,
    name: Optional[str] = None,
    role: str = "parent",
    schools: Optional[List[str]] = None,
) -> Dict[str, Any]:
    supabase = get_supabase_client()
    if not supabase:
        # Mock response for development (15 lignes)
        return {...}

    try:
        response = supabase.auth.sign_up({...})

        if not response.user:
            raise AuthenticationError("Failed to create user")

        # Create user profile in database
        profile_data = {...}
        supabase.table("user_profiles").insert(profile_data).execute()

        # If school staff, link to schools
        if role == "school_staff" and schools:
            for school_id in schools:
                supabase.table("user_schools").insert({...}).execute()

        return {...}

    except Exception as e:
        error_msg = str(e).lower()
        if "already registered" in error_msg or "duplicate" in error_msg:
            raise UserAlreadyExistsError(...)
        raise AuthenticationError(...)
```

**Problèmes**:
- ✗ Très longue (96 lignes)
- ✗ Mock data inline (15 lignes)
- ✗ Multiple database operations
- ✗ Loop avec DB calls
- ✗ String-based error detection
- ✗ Complex return object construction

**Impact**: **ÉLEVÉ**
- Difficile à tester (mock + real DB)
- Performance (loop de DB inserts)
- Error handling fragile

**Effort de Refactoring**: Medium (2 heures)

**Solution Recommandée**:
```python
async def signup_user(email: str, password: str, name: str = None,
                      role: str = "parent", schools: List[str] = None) -> UserSignupResult:
    auth_result = await create_auth_user(email, password)
    profile = await create_user_profile(auth_result.user_id, name, role)

    if role == "school_staff" and schools:
        await link_user_to_schools(auth_result.user_id, schools)

    return UserSignupResult(user=auth_result.user, profile=profile)
```

---

### 🔥 Niveau ÉLEVÉ (Cognitive Complexity 11-15)

#### #4 - Login User Function
**File**: `allobye_server_python/auth.py`
**Lines**: 213-293 (80 lignes)
**Cyclomatic Complexity**: 12
**Cognitive Complexity**: 14

**Problèmes**:
- ✗ 80 lignes
- ✗ Mock data inline
- ✗ Multiple exception types
- ✗ Profile fetching mélangé

**Effort**: Low-Medium (1.5 heures)

---

#### #5 - Delegate Authorize Handler
**File**: `allobye_server_python/main.py`
**Lines**: 1111-1178 (67 lignes)
**Cyclomatic Complexity**: 12
**Cognitive Complexity**: 14

**Problèmes**:
- ✗ Pattern similaire à #2
- ✗ Validation en boucle
- ✗ Multiple early returns

**Effort**: Low (1 heure avec refactoring de #2)

---

#### #6 - School Dashboard Fetch Handler
**File**: `allobye_server_python/main.py`
**Lines**: 1252-1328 (76 lignes)
**Cyclomatic Complexity**: 13
**Cognitive Complexity**: 13

**Problèmes**:
- ✗ Widget creation complexe
- ✗ Data aggregation
- ✗ Metadata construction

**Effort**: Medium (2 heures)

---

#### #7 - Get User Profile
**File**: `allobye_server_python/auth.py`
**Lines**: 432-503 (71 lignes)
**Cyclomatic Complexity**: 11
**Cognitive Complexity**: 13

**Code Snippet**:
```python
async def get_user_profile(user_id: str) -> Dict[str, Any]:
    supabase = get_supabase_admin()
    if not supabase:
        return {...}  # Mock

    try:
        profile_response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()

        if not profile_response.data:
            return {...}

        profile = profile_response.data

        # Fetch associated schools (for school staff)
        schools = []
        if profile.get("role") == "school_staff":
            schools_response = supabase.table("user_schools").select("school_id").eq("user_id", user_id).execute()
            schools = [s["school_id"] for s in schools_response.data]

        # Fetch associated children (for parents)
        children = []
        if profile.get("role") == "parent":
            children_response = supabase.table("parent_children").select("child_id").eq("parent_id", user_id).execute()
            children = [c["child_id"] for c in children_response.data]

        return {...}
    except Exception as e:
        return {...}
```

**Problèmes**:
- ✗ Multiple DB queries conditionnelles
- ✗ Role-based logic
- ✗ Exception swallowing (return au lieu de raise)

**Effort**: Low (1 heure)

**Solution Recommandée**:
```python
async def get_user_profile(user_id: str) -> UserProfile:
    profile = await fetch_profile(user_id)

    associations = await fetch_user_associations(user_id, profile.role)

    return UserProfile(
        **profile,
        schools=associations.schools,
        children=associations.children
    )
```

---

#### #8 - Emergency Declare Handler
**File**: `allobye_server_python/main.py`
**Lines**: 1181-1249 (68 lignes)
**Cyclomatic Complexity**: 11
**Cognitive Complexity**: 13

**Problèmes**: Identiques à #2 et #5

---

#### #9 - HandleSignup (React)
**File**: `src/allobye-dashboard/auth-screen.jsx`
**Lines**: 70-135 (65 lignes)
**Cyclomatic Complexity**: 11
**Cognitive Complexity**: 12

**Code Snippet**:
```javascript
const handleSignup = async (e) => {
  e.preventDefault();

  // Validation
  if (formData.password !== formData.confirmPassword) {
    setState({ ...state, error: "Les mots de passe ne correspondent pas" });
    return;
  }

  if (formData.password.length < 6) {
    setState({ ...state, error: "Le mot de passe doit contenir au moins 6 caractères" });
    return;
  }

  setState({ ...state, loading: true, error: null });

  try {
    if (!window.openai?.callTool) {
      throw new Error("MCP tools not available");
    }

    const result = await window.openai.callTool("auth-signup", {...});

    if (result?._meta?.session?.access_token) {
      localStorage.setItem("allobye_token", result._meta.session.access_token);

      const profileResult = await window.openai.callTool("auth-profile", {...});

      if (profileResult?.structuredContent) {
        localStorage.setItem("allobye_user", JSON.stringify(profileResult.structuredContent));

        if (onAuthenticated) {
          onAuthenticated({...});
        }
      }
    } else {
      setState({...});
      alert("Compte créé avec succès!");
    }
  } catch (error) {
    setState({...});
  }
};
```

**Problèmes**:
- ✗ Validation inline
- ✗ Multiple API calls séquentiels
- ✗ LocalStorage manipulation
- ✗ alert() usage
- ✗ Nested conditionals profondes

**Effort**: Low (1 heure)

**Solution Recommandée**:
```javascript
const { signup, loading, error } = useAuth();
const { showToast } = useToast();

const handleSignup = async (e) => {
  e.preventDefault();

  const validationError = validateSignupForm(formData);
  if (validationError) {
    showToast(validationError, 'error');
    return;
  }

  const result = await signup(formData);
  if (result.success) {
    onAuthenticated(result.session);
  }
};
```

---

#### #10 - Get School Pickups
**File**: `allobye_server_python/main.py`
**Lines**: 612-668 (56 lignes)
**Cyclomatic Complexity**: 11
**Cognitive Complexity**: 12

**Code Snippet**:
```python
async def get_school_pickups(
    school_id: str,
    date: str,
    time_window: str,
) -> List[Dict[str, Any]]:
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
        # Mock data (19 lignes)
        return [...]

    try:
        with monitoring_middleware.monitor_db_query("get_school_pickups"):
            response = supabase.table("pickups").select(...).eq(...).gte(...).lte(...).order("scheduled_time").execute()

        return response.data
    except Exception as e:
        logger.error("Error fetching pickups", ...)
        return []
```

**Problèmes**:
- ✗ Time calculation logic complexe
- ✗ Mock data inline (19 lignes)
- ✗ Magic strings ("current", "today")
- ✗ Empty return sur error (swallowing)

**Effort**: Low (1 heure)

**Solution Recommandée**:
```python
async def get_school_pickups(school_id: str, date: str,
                             time_window: TimeWindow) -> List[Pickup]:
    time_range = calculate_time_range(time_window, date)

    pickups = await pickup_repository.find_by_school_and_time(
        school_id, time_range.start, time_range.end
    )

    return pickups
```

---

### ⚠️ Niveau MOYEN (Cognitive Complexity 8-10)

#### #11 - Cascade Pickup Status (SQL)
**File**: `allobye_server_python/schema.sql`
**Lines**: 234-256 (22 lignes)
**Cyclomatic Complexity**: 10
**Cognitive Complexity**: 11

**Problèmes**:
- Multiple IF statements
- UPDATE cascade logic
- Side effects complexes

---

#### #12 - Notify Emergency Function (SQL)
**File**: `allobye_server_python/schema.sql`
**Lines**: 196-225 (29 lignes)
**Cyclomatic Complexity**: 8
**Cognitive Complexity**: 10

**Problèmes**:
- JOIN avec SELECT INTO
- pg_notify avec JSON construction
- Multiple tables touched

---

#### #13 - Monitor Tool Call Decorator
**File**: `allobye_server_python/monitoring.py`
**Lines**: 565-618 (53 lignes)
**Cyclomatic Complexity**: 12
**Cognitive Complexity**: 10

**Problèmes**:
- Async wrapper complexe
- Try/except/finally avec metrics
- State tracking complexe

---

#### #14 - Record Tool Call
**File**: `allobye_server_python/monitoring.py`
**Lines**: 222-263 (41 lignes)
**Cyclomatic Complexity**: 9
**Cognitive Complexity**: 9

**Problèmes**:
- Conditional metrics updates
- List management
- Alerting logic

---

#### #15 - Call Tool Request Monitored
**File**: `allobye_server_python/main.py`
**Lines**: 1392-1449 (57 lignes)
**Cyclomatic Complexity**: 10
**Cognitive Complexity**: 9

**Problèmes**:
- Large handler dictionary
- Try/except/finally avec metrics
- Manual timing logic

---

## Résumé des Hotspots

### Par Fichier

| File | Hotspots | Total CC | Avg CC | Status |
|------|----------|----------|--------|--------|
| main.py | 6 | 78 | 13.0 | ⚠️ High |
| auth.py | 3 | 42 | 14.0 | ⚠️ High |
| monitoring.py | 2 | 21 | 10.5 | ⚠️ Medium |
| dashboard.jsx | 2 | 29 | 14.5 | ❌ Critical |
| auth-screen.jsx | 1 | 12 | 12.0 | ⚠️ High |
| schema.sql | 2 | 18 | 9.0 | ⚠️ Medium |

### Par Catégorie

| Catégorie | Hotspots | Effort Total | ROI |
|-----------|----------|--------------|-----|
| Authentication | 3 | 4.5h | High |
| Request Handlers | 5 | 6h | Very High |
| Real-time/Async | 2 | 5h | High |
| Database/SQL | 2 | 3h | Medium |
| Monitoring | 2 | 2h | Low |
| UI/Forms | 1 | 1h | Medium |

---

## Plan de Refactoring Prioritaire

### Phase 1 - Quick Wins (1 semaine, 8-10h)
1. Refactoriser handlers auth (signup_user, login_user) → **+3 points**
2. Extraire validation decorators pour handlers MCP → **+4 points**
3. Créer hook useRealtimePickups (dashboard.jsx) → **+5 points**

**Impact**: -12 points de complexité | ROI: Very High

### Phase 2 - Medium Refactoring (2 semaines, 15-20h)
4. Diviser tous les MCP handlers avec decorators pattern
5. Extraire mock data dans module séparé
6. Simplifier RLS policies SQL

**Impact**: -20 points de complexité | ROI: High

### Phase 3 - Architectural Improvements (1 mois)
7. Introduire Repository pattern pour DB
8. Créer custom hooks pour tous les useEffect complexes
9. Implémenter Result types au lieu d'exceptions

**Impact**: -30 points de complexité | ROI: Very High (long terme)

---

## Métriques de Succès

### Avant Refactoring
- **Hotspots critiques (CC > 15)**: 3
- **Total Cognitive Complexity**: 194
- **Avg Function Size**: 39 lignes
- **Functions > 50 lines**: 12

### Après Refactoring (Cible)
- **Hotspots critiques (CC > 15)**: 0
- **Total Cognitive Complexity**: < 120
- **Avg Function Size**: < 25 lignes
- **Functions > 50 lines**: < 3

---

**Dernière mise à jour**: 2025-11-04
**Prochaine revue**: 2025-11-11
