# Logic Separation Analysis - AllôBye

**Date**: 2025-11-04
**Analyseur**: Extracteur de Logique Métier
**Codebase**: AllôBye - Système de coordination de ramassage scolaire

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Définitions](#définitions)
3. [Analyse par couche](#analyse-par-couche)
4. [Matrice de séparation](#matrice-de-séparation)
5. [Violations de séparation](#violations-de-séparation)
6. [Recommandations](#recommandations)

---

## Vue d'ensemble

Cette analyse évalue **dans quelle mesure la logique métier est séparée de l'infrastructure** dans AllôBye. Une bonne séparation permet de:

- **Tester** la logique métier sans infrastructure
- **Changer** d'infrastructure sans modifier les règles métier
- **Comprendre** les règles métier sans connaître les détails techniques
- **Éviter** la duplication de logique entre couches

### Verdict global

| Aspect | Score | Commentaire |
|--------|-------|-------------|
| **Séparation Python/DB** | 🟠 40% | Logique métier significative dans PostgreSQL (RLS, triggers) |
| **Séparation Backend/Frontend** | 🟠 50% | Calculs métier dupliqués côté client |
| **Séparation Auth/Business** | 🔴 30% | Authorization mélangée avec authentication |
| **Séparation MCP/Business** | 🟡 60% | Handlers contiennent logique orchestration + validation |
| **Score global** | 🟠 45% | **Faible séparation** - Refactoring recommandé |

---

## Définitions

### Logique métier (Business Logic)

**Ce que le système DOIT faire** selon les exigences métier:

- **Règles de validation**: "Un parent ne peut planifier que pour SES enfants"
- **Calculs métier**: "Détection de retard si scheduled_time < NOW()"
- **Workflows**: "Multi-école → Coordination A2A automatique"
- **Autorisations métier**: "Délégué autorisé via delegate_children"
- **Transformations**: "Agrégation des écoles à partir des enfants"

### Logique d'infrastructure (Infrastructure Logic)

**Comment le système fonctionne** techniquement:

- **Accès données**: Requêtes SQL, ORM
- **Protocoles**: HTTP, WebSocket, MCP
- **Authentification**: JWT validation, session management
- **Persistance**: Database transactions, caching
- **Communication**: API calls, message queues
- **Monitoring**: Logging, metrics, tracing

### Zone grise (Infrastructure déguisée en métier)

**Logique qui SEMBLE métier mais est VRAIMENT infrastructure**:

- ❌ RLS policies avec logique complexe
- ❌ Triggers database pour workflows métier
- ❌ Frontend calculant des états métier
- ❌ Validations dans contraintes CHECK
- ❌ Logique métier dans middleware auth

---

## Analyse par couche

### Couche 1: Database (PostgreSQL)

#### 📊 Répartition

| Type de logique | Nombre | Exemples |
|-----------------|--------|----------|
| **Infrastructure pure** | 15 | Primary keys, indexes, foreign keys, timestamps |
| **Infrastructure + métier** | 21 | RLS policies avec règles business |
| **Métier pur** | 5 | CHECK constraints (status, emergency_type), triggers cascade |
| **Total** | 41 | |

**Taux de logique métier**: 26 éléments sur 41 = **63%** ⚠️

---

#### Infrastructure pure (légitime) ✅

```sql
-- Foreign keys (infrastructure)
children.school_id → schools.id ON DELETE CASCADE

-- Indexes (performance, infrastructure)
CREATE INDEX idx_pickups_scheduled_time ON pickups(scheduled_time);

-- Auto-timestamps (infrastructure)
updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()

-- UUID generation (infrastructure)
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

**Verdict**: ✅ **Correctement placé**. Ce sont des préoccupations purement techniques.

---

#### Logique métier dans constraints (discutable) ⚠️

```sql
-- RÈGLE MÉTIER: Statuts autorisés
status TEXT CHECK (
    status IN ('pending', 'confirmed', 'in_progress', 'completed', 'cancelled', 'late')
)

-- RÈGLE MÉTIER: Types d'urgence
emergency_type TEXT CHECK (
    emergency_type IN ('late', 'illness', 'cancel', 'injury', 'other')
)

-- RÈGLE MÉTIER: Niveaux de sévérité
severity TEXT CHECK (
    severity IN ('low', 'medium', 'high', 'critical')
)
```

**Analyse**:
- ✅ **Pro**: Garantie d'intégrité au niveau le plus bas
- ✅ **Pro**: Impossible de violer, même en accès direct DB
- ❌ **Con**: Règle métier cachée dans le schéma
- ❌ **Con**: Changement nécessite migration DB
- ❌ **Con**: Pas testable unitairement

**Verdict**: ⚠️ **Acceptable mais pas idéal**. Les énumérations simples peuvent rester en DB, mais devraient être **documentées** et **répliquées** dans le code applicatif pour validation précoce.

**Recommandation**:
```python
# Dupliquer en Python pour validation précoce
class PickupStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    LATE = "late"

# Validation avant DB
if status not in PickupStatus:
    raise ValidationError()
```

---

#### Logique métier dans triggers (problématique) ❌

**Trigger 1: cascade_pickup_status()** (schema.sql:234-256)

```sql
-- RÈGLE MÉTIER: Annulation ramassage → Reset checkouts
IF NEW.status = 'cancelled' AND OLD.status != 'cancelled' THEN
    UPDATE pickup_children SET checked_out = FALSE, ...
END IF;

-- RÈGLE MÉTIER: Complétion ramassage → Auto-checkout enfants
IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
    UPDATE pickup_children SET checked_out = TRUE, ...
END IF;
```

**Problèmes**:
- ❌ **Logique métier invisible** au code applicatif
- ❌ **Impossible à tester unitairement** (nécessite DB complète)
- ❌ **Pas de logging** des actions effectuées
- ❌ **Side effects cachés** (modifications en cascade)
- ❌ **Couplage fort** DB-Business

**Impact**:
- Un développeur lisant `main.py` ne sait PAS que ces cascades existent
- Impossible de tracer quand et pourquoi `checked_out` change
- Impossible de désactiver temporairement la cascade pour tests

**Verdict**: ❌ **Violation majeure de séparation**

**Recommandation**: Déplacer dans service layer Python:
```python
class PickupService:
    async def cancel_pickup(self, pickup_id: str, reason: str):
        """Cancel pickup and reset all checkouts."""
        async with self.db.transaction():
            # Logique métier EXPLICITE
            await self.pickup_repo.update_status(pickup_id, "cancelled")
            await self.pickup_repo.uncheck_all_children(pickup_id)

            # Traçabilité
            logger.info("Pickup cancelled", pickup_id=pickup_id, reason=reason)
            await self.audit_log.record("pickup_cancelled", ...)
```

---

**Trigger 2: notify_emergency()** (schema.sql:196-231)

```sql
CREATE FUNCTION notify_emergency() RETURNS TRIGGER AS $$
BEGIN
    -- Récupération info école (LOGIQUE MÉTIER)
    SELECT c.school_id, s.name INTO school_id, school_name
    FROM children c JOIN schools s ON c.school_id = s.id
    WHERE c.id = NEW.child_id;

    -- Notification temps réel (INFRASTRUCTURE)
    PERFORM pg_notify('emergency_alert', json_build_object(...)::text);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

**Analyse**:
- ✅ **Pro**: Notification temps réel garantie (pas de race condition)
- ✅ **Pro**: Couplage bas (PostgreSQL → abonnés inconnus)
- ❌ **Con**: JOIN et logique métier dans trigger
- ❌ **Con**: Payload structure (business concern) dans DB

**Verdict**: ⚠️ **Acceptable pour notification technique**, mais la construction du payload est métier.

**Recommandation**: Limiter le trigger à `pg_notify('emergency_alert', NEW.id)` et construire le payload côté application.

---

#### Logique métier dans RLS policies (violation majeure) ❌

**21 policies RLS** avec logique métier complexe!

**Exemple 1: Parent can view children's pickups** (schema.sql:351-360)

```sql
CREATE POLICY "Parents can view their children's pickups"
    ON pickups FOR SELECT
    USING (
        EXISTS (
            -- RÈGLE MÉTIER: Parent voit pickup si AU MOINS UN de ses enfants est dedans
            SELECT 1 FROM pickup_children pc
            JOIN children c ON pc.child_id = c.id
            WHERE pc.pickup_id = pickups.id
            AND c.parent_email = auth.jwt()->>'email'
        )
    );
```

**Problèmes**:
- ❌ **Règle métier complexe** (EXISTS + JOIN) dans DB
- ❌ **Impossible à tester** sans DB + Auth complète
- ❌ **Logique cachée** (developer doit lire SQL pour comprendre)
- ❌ **Performance**: JOIN sur CHAQUE requête SELECT
- ❌ **Duplication**: Même logique dans `verify_parent_owns_child()` Python

**Verdict**: ❌ **Violation sévère**. RLS devrait être **ownership simple uniquement**.

**Recommandation**:
```sql
-- RLS: Ownership simple (légitime)
CREATE POLICY "Service role can access all"
    ON pickups FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');

-- Logique métier: Dans application
class PickupRepository:
    async def get_pickups_for_parent(self, parent_id: str):
        """Get all pickups where parent has at least one child."""
        # Logique métier EXPLICITE et testable
        child_ids = await self.get_parent_children(parent_id)
        pickups = await self.db.query("""
            SELECT DISTINCT p.* FROM pickups p
            JOIN pickup_children pc ON p.id = pc.pickup_id
            WHERE pc.child_id IN :child_ids
        """, child_ids=child_ids)
        return pickups
```

---

**Exemple 2: Delegates can view emergencies** (schema.sql:459-469)

```sql
CREATE POLICY "Delegates can view emergencies for authorized children"
    ON emergencies FOR SELECT
    USING (
        EXISTS (
            -- RÈGLE MÉTIER: Délégué voit urgence si autorisé ET actif
            SELECT 1 FROM delegate_children dc
            JOIN delegates d ON dc.delegate_id = d.id
            WHERE dc.child_id = emergencies.child_id
            AND d.email = auth.jwt()->>'email'
            AND dc.is_active = TRUE  -- RÈGLE MÉTIER!
        )
    );
```

**Analyse**:
- ❌ Condition métier `is_active = TRUE` dans RLS
- ❌ Triple JOIN pour vérifier autorisation
- ❌ Logique dupliquée avec `get_authorized_delegates()` Python

**Impact**: Si la règle change (ex: autoriser délégués inactifs en lecture), il faut modifier:
1. La policy SQL
2. La fonction Python
3. Possiblement le frontend

**Verdict**: ❌ **Triplication de logique**

---

#### 📊 Résumé Database

| Élément | Infrastructure | Métier | Hybride | Verdict |
|---------|---------------|--------|---------|---------|
| Constraints (CHECK) | 0 | 3 | 0 | ⚠️ Acceptable |
| Triggers | 5 | 2 | 0 | ❌ Violations |
| RLS Policies | 2 | 0 | 19 | ❌ Violations majeures |
| Foreign keys | 7 | 0 | 0 | ✅ Correct |
| Indexes | 14 | 0 | 0 | ✅ Correct |
| Functions utility | 0 | 2 | 0 | ⚠️ Discutable |

**Score séparation Database**: **35%** - Trop de logique métier dans PostgreSQL

---

### Couche 2: Backend Python

#### 📊 Répartition

| Module | LoC | Infrastructure | Métier | Hybride | Score |
|--------|-----|---------------|--------|---------|-------|
| `main.py` | 1583 | 400 (25%) | 600 (38%) | 583 (37%) | 🟠 38% métier |
| `auth.py` | 633 | 300 (47%) | 150 (24%) | 183 (29%) | 🟠 24% métier |
| `monitoring.py` | 753 | 700 (93%) | 0 (0%) | 53 (7%) | ✅ 0% métier |

**Score moyen**: **20%** de logique métier mélangée à 80% d'infrastructure.

---

#### main.py: God Object mixing everything

**Responsabilités** (violations SRP):
1. **MCP Server setup** (infrastructure) ✅
2. **Tool handlers** (orchestration - hybride) ⚠️
3. **Database helpers** (métier + infrastructure) ❌
4. **Widget configuration** (infrastructure) ✅
5. **Authentication middleware** (infrastructure + authorization) ❌
6. **Monitoring** (infrastructure) ✅

**Analyse fonction par fonction**:

---

**get_schools_for_children()** (main.py:399-423)

```python
async def get_schools_for_children(child_ids: List[str]) -> List[Dict[str, Any]]:
    """Get unique schools for a list of children."""
    # ❌ INFRASTRUCTURE: Supabase query
    response = supabase.table("children").select("school_id, schools(*)").in_("id", child_ids).execute()

    # ✅ MÉTIER: Extraction d'écoles uniques
    schools = {}
    for child in response.data:
        if child.get("schools"):
            school = child["schools"]
            schools[school["id"]] = school

    return list(schools.values())
```

**Problèmes**:
- ❌ Logique métier (déduplication) mélangée avec infrastructure (Supabase query)
- ❌ Couplage fort à Supabase

**Verdict**: ❌ **Violation - Devrait être dans Repository pattern**

**Recommandation**:
```python
# Infrastructure: Repository
class SchoolRepository:
    async def get_by_children(self, child_ids: List[str]) -> List[School]:
        # Query pure (infrastructure)
        response = self.db.query("children").select(...).execute()
        return [School.from_dict(s) for s in response.data]

# Métier: Service
class SchoolService:
    def get_unique_schools(self, children: List[Child]) -> List[School]:
        # Logique métier pure (testable sans DB)
        schools = {child.school_id: child.school for child in children}
        return list(schools.values())
```

---

**create_pickup_request()** (main.py:426-472)

```python
async def create_pickup_request(...):
    """Create a pickup request in the database."""
    pickup_id = str(uuid4())  # ✅ Infrastructure

    # ❌ INFRASTRUCTURE: Direct DB access
    pickup_data = {
        "id": pickup_id,
        "pickup_person_id": pickup_person_id,
        "scheduled_time": scheduled_time,
        "status": "confirmed",  # ✅ MÉTIER: Business rule
        "notes": notes,
    }

    response = supabase.table("pickups").insert(pickup_data).execute()

    # ❌ INFRASTRUCTURE + MÉTIER mélangés
    for child_id in child_ids:
        supabase.table("pickup_children").insert({...}).execute()

    return response.data[0]
```

**Problèmes**:
- ❌ Logique métier (status = "confirmed") mélangée avec DB access
- ❌ Pas de domain model (utilise dict)
- ❌ Direct database access (pas de repository)

**Verdict**: ❌ **Violation majeure**

**Recommandation**:
```python
# Domain model (métier pur)
@dataclass
class Pickup:
    pickup_person_id: str
    child_ids: List[str]
    scheduled_time: datetime
    notes: Optional[str]

    def __post_init__(self):
        self.id = str(uuid4())
        self.status = PickupStatus.CONFIRMED  # Règle métier

# Repository (infrastructure)
class PickupRepository:
    async def create(self, pickup: Pickup) -> Pickup:
        data = pickup.to_dict()
        response = await self.db.insert("pickups", data)
        return Pickup.from_dict(response)

# Service (orchestration métier)
class PickupService:
    async def schedule_pickup(self, ...) -> Pickup:
        # Validation métier
        if not self.authz.can_schedule(parent, child_ids):
            raise UnauthorizedException()

        # Création (règles métier dans domain model)
        pickup = Pickup(...)

        # Persistance (infrastructure déléguée)
        return await self.pickup_repo.create(pickup)
```

---

**coordinate_cross_school_pickup()** (main.py:475-496)

```python
async def coordinate_cross_school_pickup(...):
    """Coordinate pickup across multiple schools (A2A simulation)."""
    # ✅ MÉTIER: Orchestration cross-school
    schools = await get_schools_for_children(child_ids)
    pickup = await create_pickup_request(...)

    # ✅ MÉTIER: Business logic pour A2A
    pickup["schools_affected"] = [s["name"] for s in schools]
    pickup["a2a_messages"] = [
        {"school_id": s["id"], "status": "confirmed"} for s in schools
    ]

    return pickup
```

**Analyse**:
- ✅ Orchestration métier claire
- ⚠️ Simulation A2A (pas de vrai bus)
- ❌ Appelle des fonctions avec violations (get_schools, create_pickup)

**Verdict**: ⚠️ **Correctement pensé mais implémentation couplée**

---

**_handle_pickup_schedule_create()** (main.py:1023-1108)

```python
async def _handle_pickup_schedule_create(arguments: Dict[str, Any]):
    # ✅ INFRASTRUCTURE: MCP protocol
    user = await get_current_user(arguments)

    # ✅ MÉTIER: Authorization
    if not require_auth(user, role="parent"):
        return error_response()

    # ✅ INFRASTRUCTURE: Input validation
    payload = PickupScheduleInput.model_validate(arguments)

    # ✅ MÉTIER: Ownership validation
    for child_id in payload.child_ids:
        if not await verify_parent_owns_child(user.id, child_id):
            return error_response()

    # ✅ MÉTIER: Business decision (multi-school?)
    schools = await get_schools_for_children(payload.child_ids)
    if len(schools) > 1:
        results = await coordinate_cross_school_pickup(...)
    else:
        results = await create_pickup_request(...)

    # ✅ INFRASTRUCTURE: MCP response
    return types.CallToolResult(...)
```

**Analyse**:
- ✅ Orchestration claire (handler rôle = coordination)
- ✅ Séparation auth, validation, logique métier
- ❌ **Manque**: Validation que le délégué est autorisé! (BR-002)
- ⚠️ Appelle des helpers mal structurés

**Verdict**: ⚠️ **Bonne structure mais détails manquants**

---

#### auth.py: Authentication vs Authorization confusion

**Fonctions légitimes** (authentication - infrastructure):
- `signup_user()`: Création compte ✅
- `login_user()`: Connexion ✅
- `logout_user()`: Déconnexion ✅
- `validate_session()`: Validation JWT ✅
- `reset_password_request()`: Reset password ✅

**Fonctions ILLEGITIMES** (authorization - métier):
- `verify_parent_owns_child()`: ❌ **Business logic** (ownership)
- `verify_staff_at_school()`: ❌ **Business logic** (association)

**Problème**: Module nommé `auth.py` contient **authorization** (logique métier) en plus d'**authentication** (infrastructure).

**Verdict**: ❌ **Violation de séparation des préoccupations**

**Recommandation**: Créer module séparé:
```python
# auth.py: Authentication ONLY (infrastructure)
async def signup_user(...)
async def login_user(...)
async def validate_session(...)

# authorization.py: Authorization (business logic)
class AuthorizationService:
    async def can_schedule_pickup(self, user: UserProfile, child_ids: List[str]) -> bool
    async def can_authorize_delegate(self, user: UserProfile, child_ids: List[str]) -> bool
    async def verify_parent_owns_child(self, parent_id: str, child_id: str) -> bool
```

---

#### monitoring.py: Infrastructure pure ✅

**753 lignes d'infrastructure pure**:
- Logging structuré
- Metrics collection
- Request tracing
- Alerting
- Prometheus export
- Health checks

**Aucune logique métier**: ✅ **Parfaitement séparé**

---

#### 📊 Résumé Backend Python

| Aspect | Score | Commentaire |
|--------|-------|-------------|
| **Repository pattern** | ❌ 0% | Aucun - Direct DB access partout |
| **Domain models** | ❌ 0% | Dicts utilisés partout |
| **Service layer** | ❌ 10% | Quelques helpers, pas de structure |
| **Auth vs Authz** | ❌ 30% | Mélangés dans auth.py |
| **Handlers structure** | ✅ 70% | Bonne orchestration |

**Score séparation Backend**: **22%** - Très faible séparation

---

### Couche 3: Frontend React

#### 📊 Répartition

| Composant | LoC | Infrastructure | Métier | Hybride | Score |
|-----------|-----|---------------|--------|---------|-------|
| `dashboard.jsx` | 249 | 120 (48%) | 40 (16%) | 89 (36%) | 🟠 16% métier |
| `pickup-card.jsx` | 77 | 20 (26%) | 30 (39%) | 27 (35%) | 🔴 39% métier |
| `emergency-alert.jsx` | ~50 | 40 (80%) | 0 (0%) | 10 (20%) | ✅ 0% métier |

---

#### dashboard.jsx: Real-time + Business filtering

**Infrastructure** (légitime):
```javascript
// Real-time subscription (infrastructure)
supabase.channel("pickups-changes")
  .on("postgres_changes", { table: "pickups" }, (payload) => {
    setRealtimePickups(...);
  })
  .subscribe();

// Auto-refresh (infrastructure)
setInterval(() => {
  window.openai.callTool("school-dashboard-fetch", ...);
}, refreshInterval * 1000);
```

✅ **Correct**: Ce sont des préoccupations de synchronisation UI.

---

**Métier** (violation):
```javascript
// ❌ RÈGLE MÉTIER: Filtre "next_30min"
if (state.filter === "next_30min") {
  const scheduledTime = new Date(pickup.scheduled_time);
  const thirtyMinutesFromNow = new Date(currentTime.getTime() + 30 * 60 * 1000);
  return scheduledTime <= thirtyMinutesFromNow;
}

// ❌ RÈGLE MÉTIER: Filtre "delays"
if (state.filter === "delays") {
  return pickup.delay && pickup.delay > 0;
}
```

**Problèmes**:
- ❌ Duplication: Backend calcule aussi "current" = 30min (main.py:623)
- ❌ Logique métier dans UI (devrait être dans backend)
- ❌ Difficile à tester (nécessite React + DOM)

**Verdict**: ❌ **Violation - Filtrage devrait être backend**

**Recommandation**:
```javascript
// Frontend: Appel backend avec filtre
const pickups = await callMCPTool("school-dashboard-fetch", {
  schoolId,
  filter: "next_30min"  // Backend applique la règle métier
});

// Backend retourne déjà filtré
setPickups(pickups);  // Pas de filtrage côté client
```

---

#### pickup-card.jsx: Business calculations in UI ❌

```javascript
// ❌ RÈGLE MÉTIER: Couleur selon urgence
const getStatusColor = () => {
  if (pickup.status === "completed") return "green";
  if (pickup.status === "cancelled") return "gray";
  if (pickup.delay && pickup.delay > 0) return "orange";
  if (minutesUntilPickup < 5) return "red";     // ❌ Seuil métier
  if (minutesUntilPickup < 15) return "yellow";  // ❌ Seuil métier
  return "blue";
};

// ❌ RÈGLE MÉTIER: Label temporel
const getTimeLabel = () => {
  if (minutesUntilPickup < 0) return "En retard";
  if (minutesUntilPickup === 0) return "Maintenant";
  if (minutesUntilPickup < 60) return `Dans ${minutesUntilPickup} min`;
  // ...
};
```

**Problèmes**:
- ❌ **Seuils métier hardcodés** (5min, 15min) dans UI
- ❌ Définition "En retard" calculée côté client
- ❌ Impossible de changer les seuils sans rebuild frontend
- ❌ Incohérence: Backend devrait calculer status "late" (BR-008)

**Verdict**: ❌ **Violation majeure - Calculs métier dans presentation**

**Recommandation**:
```javascript
// Frontend: Affichage simple basé sur status backend
const StatusBadge = ({ urgencyLevel }) => {
  const colors = {
    critical: "red",
    urgent: "yellow",
    normal: "blue",
    completed: "green",
    cancelled: "gray"
  };
  return <span className={colors[urgencyLevel]}>{urgencyLevel}</span>;
};

// Backend: Calcul métier
class PickupPresenter:
    def get_urgency_level(self, pickup: Pickup) -> str:
        """Calculate urgency level (business rule)."""
        if pickup.status == PickupStatus.COMPLETED:
            return "completed"
        if pickup.delay_minutes > 0:
            return "delayed"

        minutes_until = (pickup.scheduled_time - datetime.now()).total_seconds() / 60
        if minutes_until < 5:
            return "critical"
        if minutes_until < 15:
            return "urgent"
        return "normal"
```

---

#### 📊 Résumé Frontend

| Aspect | Score | Commentaire |
|--------|-------|-------------|
| **Presentation only** | ❌ 40% | Trop de calculs métier |
| **Backend filtering** | ❌ 30% | Filtres dupliqués client/serveur |
| **Business calculations** | ❌ 20% | Seuils urgence, retards dans UI |
| **Real-time sync** | ✅ 80% | Bien géré (infrastructure) |

**Score séparation Frontend**: **42%** - Trop de logique métier dans UI

---

## Matrice de séparation

### Vue globale par règle métier

| Règle métier | DB (RLS/Trigger) | Backend (Python) | Frontend (JS) | Duplication | Verdict |
|--------------|------------------|------------------|---------------|-------------|---------|
| **BR-001**: Parent ownership | ✅ RLS policy | ✅ verify_parent_owns_child() | ❌ | 🔴 Duplicated | Violation |
| **BR-002**: Delegate authorization | ❌ | ❌ | ❌ | - | Missing |
| **BR-003**: Multi-school coordination | ❌ | ✅ coordinate_cross_school() | ❌ | ✅ Unique | OK |
| **BR-004**: Initial status = confirmed | ❌ | ✅ Hardcoded | ❌ | ✅ Unique | OK |
| **BR-005**: Cancel → Reset checkouts | ✅ Trigger | ❌ | ❌ | ✅ Unique | Violation (DB) |
| **BR-006**: Complete → Auto-checkout | ✅ Trigger | ❌ | ❌ | ✅ Unique | Violation (DB) |
| **BR-007**: ETA calculation | ❌ | ❌ | ❌ | - | Missing |
| **BR-008**: Late detection | ❌ | ❌ | ✅ Frontend | 🔴 Wrong layer | Violation |
| **BR-009**: Status enumeration | ✅ CHECK | ⚠️ Hardcoded | ⚠️ Hardcoded | 🟠 Triplicated | Violation |
| **BR-010**: Unique delegate email | ✅ UNIQUE | ✅ Upsert | ❌ | 🟠 Duplicated | Acceptable |
| **BR-011**: Granular authorization | ✅ Junction table | ✅ delegate_children | ❌ | ✅ Unique | OK |
| **BR-012**: Permission types | ⚠️ ARRAY (no validation) | ❌ | ❌ | - | Missing |
| **BR-013**: A2A sync | ❌ | ✅ broadcast_delegate() | ❌ | ✅ Unique | OK |
| **BR-014**: Active delegates only | ⚠️ RLS partial | ⚠️ Not always filtered | ❌ | 🔴 Inconsistent | Violation |
| **BR-020**: Emergency types | ✅ CHECK | ⚠️ Hardcoded | ❌ | 🟠 Duplicated | Violation |
| **BR-022**: Emergency cascade delegates | ❌ | ✅ broadcast_emergency() | ❌ | ✅ Unique | OK |
| **BR-024**: Real-time notify | ✅ Trigger | ❌ | ✅ Subscription | 🟠 Distributed | OK (pattern) |
| **BR-030**: Role-based access | ✅ RLS | ✅ require_auth() | ❌ | 🟠 Duplicated | Violation |
| **BR-031**: Parent by email | ✅ RLS | ✅ Python | ❌ | 🔴 Duplicated | Violation |
| **BR-050**: Urgency color coding | ❌ | ❌ | ✅ Frontend | 🔴 Wrong layer | Violation |
| **BR-051**: Filter "next 30min" | ❌ | ✅ Backend | ✅ Frontend | 🔴 Duplicated | Violation |
| **BR-053**: Time window calculation | ❌ | ✅ get_school_pickups() | ❌ | ✅ Unique | OK |

---

### Statistiques

| Catégorie | Nombre | Pourcentage |
|-----------|--------|-------------|
| **Unique (bonne couche)** | 8 | 36% |
| **Duplicated** | 9 | 41% |
| **Triplicated** | 2 | 9% |
| **Wrong layer** | 2 | 9% |
| **Missing** | 3 | 14% |
| **Inconsistent** | 1 | 5% |

**Verdict**: **Seulement 36% des règles sont bien placées** ❌

---

## Violations de séparation

### Violation V1: RLS policies avec logique métier complexe

**Sévérité**: 🔴 Critique

**Localisation**: 19 policies sur 21 (schema.sql:267-486)

**Description**: Les policies RLS contiennent des JOINs, EXISTS, et conditions métier complexes au lieu de simple ownership.

**Exemples**:
```sql
-- ❌ COMPLEXE (métier)
USING (
    EXISTS (
        SELECT 1 FROM pickup_children pc
        JOIN children c ON pc.child_id = c.id
        WHERE pc.pickup_id = pickups.id
        AND c.parent_email = auth.jwt()->>'email'
    )
)

-- ✅ SIMPLE (infrastructure)
USING (auth.jwt()->>'role' = 'service_role')
```

**Impact**:
- Logique métier cachée dans DB
- Impossible à tester unitairement
- Duplication avec code Python
- Performance (JOIN sur chaque SELECT)

**Recommandation**: Limiter RLS à:
```sql
-- SEULEMENT role check
USING (auth.jwt()->>'role' = 'service_role')

-- Logique métier dans application
class PickupRepository:
    async def get_for_parent(self, parent_id):
        # Logique métier explicite et testable
```

---

### Violation V2: Triggers pour workflows métier

**Sévérité**: 🔴 Critique

**Localisation**: `cascade_pickup_status()` trigger (schema.sql:234-256)

**Description**: Trigger modifie `pickup_children` selon status du pickup (business workflow).

**Impact**:
- Workflow invisible au code applicatif
- Impossible à logger/tracer
- Pas de tests unitaires
- Side effects cachés

**Recommandation**: Déplacer dans service layer:
```python
class PickupService:
    async def cancel_pickup(self, pickup_id: str):
        async with self.db.transaction():
            await self.pickup_repo.update_status(pickup_id, "cancelled")
            await self.pickup_repo.uncheck_all_children(pickup_id)
            logger.info("Pickup cancelled", pickup_id=pickup_id)
```

---

### Violation V3: Calculs métier dans Frontend

**Sévérité**: 🟠 Haute

**Localisation**:
- `pickup-card.jsx:7-14` (couleurs urgence)
- `pickup-card.jsx:23-30` (labels temps)
- `dashboard.jsx:150-158` (filtres)

**Description**: Seuils métier (5min, 15min) et logique de filtrage hardcodés dans UI.

**Impact**:
- Règles métier dupliquées frontend/backend
- Impossible de changer sans rebuild
- Difficile à tester
- Incohérence possible frontend ≠ backend

**Recommandation**:
```javascript
// Backend calcule et retourne
{
  "pickup_id": "...",
  "urgency_level": "critical",  // ← Backend calcule
  "time_label": "Dans 3 min"    // ← Backend formatte
}

// Frontend affiche seulement
<Badge level={pickup.urgency_level}>{pickup.time_label}</Badge>
```

---

### Violation V4: Authorization dans auth.py

**Sévérité**: 🟠 Haute

**Localisation**: `auth.py:583-632`

**Description**: Fonctions d'authorization (métier) dans module authentication (infrastructure).

**Impact**:
- Confusion préoccupations
- Mauvaise organisation code
- Authorization = business logic, pas infrastructure

**Recommandation**: Séparer:
```python
# auth.py: Authentication (infrastructure)
async def validate_session(token: str) -> UserProfile

# authorization.py: Authorization (business logic)
class AuthorizationService:
    async def can_schedule_pickup(user, child_ids) -> bool
    async def verify_parent_owns_child(parent_id, child_id) -> bool
```

---

### Violation V5: Direct DB access sans Repository

**Sévérité**: 🟠 Haute

**Localisation**: Partout dans `main.py`

**Description**: Appels directs `supabase.table(...).select(...)` sans couche d'abstraction.

**Impact**:
- Couplage fort à Supabase
- Impossible de changer de DB
- Logique métier mélangée avec queries
- Pas de tests unitaires (nécessite DB)

**Recommandation**: Repository pattern:
```python
class PickupRepository:
    async def get_by_id(self, pickup_id: str) -> Optional[Pickup]:
        data = await self.db.query_one("pickups", {"id": pickup_id})
        return Pickup.from_dict(data) if data else None
```

---

### Violation V6: Pas de Domain Models

**Sévérité**: 🟡 Moyenne

**Localisation**: Tout le code utilise `Dict[str, Any]`

**Description**: Pas de dataclasses/models pour Pickup, Child, Delegate, etc.

**Impact**:
- Pas de type safety
- Logique métier éparpillée
- Impossible de mettre business logic dans models
- Pas d'IDE autocomplete

**Recommandation**:
```python
@dataclass
class Pickup:
    id: str
    child_ids: List[str]
    pickup_person_id: str
    scheduled_time: datetime
    status: PickupStatus

    def is_late(self) -> bool:
        """Business logic on model."""
        return self.status == PickupStatus.LATE or self.delay_minutes > 0

    def can_cancel(self) -> bool:
        """Business logic on model."""
        return self.status in [PickupStatus.PENDING, PickupStatus.CONFIRMED]
```

---

### Violation V7: Duplication énumérations

**Sévérité**: 🟡 Moyenne

**Localisation**:
- DB: CHECK constraints (schema.sql:72, 106, 108)
- Python: Hardcoded strings (main.py:456, 592)
- Frontend: Hardcoded strings (pickup-card.jsx:68-72)

**Description**: Mêmes énumérations définies 3 fois.

**Impact**:
- Changement nécessite modification en 3 endroits
- Risque d'incohérence

**Recommandation**:
```python
# Single source of truth
class PickupStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    LATE = "late"

# DB: Générer CHECK depuis enum
# Frontend: Export vers TypeScript
```

---

## Recommandations

### Architecture cible

```
┌──────────────────────────────────────────────────────────────┐
│                         FRONTEND                             │
│  - Presentation ONLY (rendering, events, state)             │
│  - NO business logic, NO calculations                       │
│  - Calls backend for ALL business operations                │
└────────────────────┬─────────────────────────────────────────┘
                     │ MCP Tools + REST API
┌────────────────────▼─────────────────────────────────────────┐
│                    APPLICATION LAYER                         │
│  - MCP Handlers (orchestration)                             │
│  - Input validation (Pydantic)                              │
│  - Response formatting                                       │
│  - NO business logic (delegates to services)                │
└────────────────────┬─────────────────────────────────────────┘
                     │ Service calls
┌────────────────────▼─────────────────────────────────────────┐
│                    BUSINESS LAYER                            │
│  - Services (workflows, orchestration)                      │
│  - Authorization (permissions, ownership)                   │
│  - Domain Models (Pickup, Child, Delegate)                  │
│  - Business calculations (ETA, urgency, late detection)     │
└────────────────────┬─────────────────────────────────────────┘
                     │ Repository calls
┌────────────────────▼─────────────────────────────────────────┐
│                  INFRASTRUCTURE LAYER                        │
│  - Repositories (DB access abstraction)                     │
│  - Authentication (JWT validation)                          │
│  - External services (A2A, notifications)                   │
│  - Monitoring (logging, metrics)                            │
└────────────────────┬─────────────────────────────────────────┘
                     │ DB queries
┌────────────────────▼─────────────────────────────────────────┐
│                      DATABASE                                │
│  - Schema ONLY (tables, foreign keys, indexes)              │
│  - SIMPLE RLS (role-based, NO complex business logic)       │
│  - Constraints (data integrity ONLY)                        │
│  - NO triggers for business workflows                       │
└──────────────────────────────────────────────────────────────┘
```

---

### Refactoring roadmap

#### Phase 1: Extraire logique métier de la DB (Priorité 🔴)

1. **Simplifier RLS policies**
   - Garder seulement role checks
   - Déplacer EXISTS/JOINs dans queries Python

2. **Supprimer trigger cascade_pickup_status**
   - Implémenter dans `PickupService.cancel_pickup()`
   - Implémenter dans `PickupService.complete_pickup()`

3. **Valider énumérations en Python**
   - Créer Enums Python
   - Valider AVANT insertion DB

**Estimation**: 2-3 sprints

---

#### Phase 2: Créer couche Repository (Priorité 🔴)

1. **Définir interface DatabaseClient**
   ```python
   class DatabaseClient(ABC):
       async def query(self, table, filters) -> List[Dict]
       async def insert(self, table, data) -> Dict
       async def update(self, table, id, data) -> Dict
   ```

2. **Créer repositories par domaine**
   ```python
   class PickupRepository(DatabaseClient)
   class ChildRepository(DatabaseClient)
   class DelegateRepository(DatabaseClient)
   class SchoolRepository(DatabaseClient)
   ```

3. **Remplacer direct DB access**
   - `get_schools_for_children()` → `school_repo.get_by_children()`
   - `create_pickup_request()` → `pickup_repo.create()`

**Estimation**: 1-2 sprints

---

#### Phase 3: Créer Domain Models (Priorité 🟠)

1. **Définir dataclasses**
   ```python
   @dataclass
   class Pickup:
       # Fields

       # Business methods
       def is_late(self) -> bool
       def can_cancel(self) -> bool
   ```

2. **Remplacer Dict par Models**
   - Repositories retournent Models
   - Services travaillent avec Models

**Estimation**: 1 sprint

---

#### Phase 4: Créer Service Layer (Priorité 🟠)

1. **Extraire services métier**
   ```python
   class PickupService:
       def __init__(self, pickup_repo, authz_service)

       async def schedule_pickup(...)
       async def cancel_pickup(...)
       async def complete_pickup(...)
       async def calculate_eta(...)
       async def detect_late_pickups(...)
   ```

2. **Séparer Authorization**
   ```python
   class AuthorizationService:
       async def can_schedule_pickup(...)
       async def verify_parent_owns_child(...)
   ```

3. **Simplifier handlers**
   - Handlers = orchestration pure
   - Business logic → Services

**Estimation**: 2 sprints

---

#### Phase 5: Nettoyer Frontend (Priorité 🟡)

1. **Supprimer calculs métier**
   - Backend calcule `urgency_level`
   - Backend calcule `time_label`
   - Backend calcule `is_late`

2. **Déplacer filtres backend**
   - "next_30min" → Backend
   - "delays" → Backend

3. **Frontend = Presentation pure**
   - Juste affichage
   - Pas de logique métier

**Estimation**: 1 sprint

---

### Estimation totale

**Effort**: 7-9 sprints (14-18 semaines)

**Priorités**:
1. 🔴 Phase 1 + 2 (extraire DB + Repository): **Critique** pour testabilité
2. 🟠 Phase 3 + 4 (Models + Services): **Important** pour maintenabilité
3. 🟡 Phase 5 (Frontend): **Nice to have** pour cohérence

---

## Conclusion

### Score global de séparation: 🔴 **38%**

**Problèmes majeurs**:
1. ❌ **63% de logique métier dans PostgreSQL** (RLS, triggers)
2. ❌ **Direct DB access** sans Repository
3. ❌ **Pas de Domain Models** (Dict partout)
4. ❌ **Authorization mélangée** avec Authentication
5. ❌ **Calculs métier dans Frontend** (seuils, filtres)
6. ❌ **Duplication** logique entre Python/SQL/JS

**Points positifs**:
1. ✅ Monitoring **parfaitement séparé**
2. ✅ Handlers ont bonne **structure d'orchestration**
3. ✅ Real-time sync bien **isolé comme infrastructure**

**Recommandation finale**: **Refactoring majeur nécessaire** pour atteindre une séparation acceptable (>70%). Suivre roadmap en 5 phases avec priorité sur extraction logique database et création Repository pattern.
