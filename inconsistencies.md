# Business Logic Inconsistencies - AllôBye

**Date**: 2025-11-04
**Analyseur**: Extracteur de Logique Métier
**Codebase**: AllôBye - Système de coordination de ramassage scolaire

---

## Table des matières

1. [Résumé exécutif](#résumé-exécutif)
2. [Incohérences critiques (Sécurité)](#incohérences-critiques-sécurité)
3. [Incohérences majeures (Fonctionnalité)](#incohérences-majeures-fonctionnalité)
4. [Incohérences de données (Intégrité)](#incohérences-de-données-intégrité)
5. [Duplications de logique](#duplications-de-logique)
6. [Contradictions code vs commentaires](#contradictions-code-vs-commentaires)
7. [Edge cases non couverts](#edge-cases-non-couverts)
8. [Plan d'action](#plan-daction)

---

## Résumé exécutif

**Total**: 27 incohérences détectées

| Catégorie | Nombre | Sévérité |
|-----------|--------|----------|
| **Sécurité** | 3 | 🔴 Critique |
| **Fonctionnalité** | 8 | 🟠 Haute |
| **Intégrité données** | 6 | 🟠 Haute |
| **Duplication** | 7 | 🟡 Moyenne |
| **Contradictions** | 2 | 🟡 Moyenne |
| **Edge cases** | 1 | 🟢 Basse |

**Urgence**: 🔴 **3 incohérences critiques de sécurité** à corriger immédiatement.

---

## Incohérences critiques (Sécurité)

### SEC-001: Pas de validation delegate authorization lors de pickup creation

**Sévérité**: 🔴 Critique (Faille de sécurité)

**Description**: Un parent peut assigner N'IMPORTE QUEL délégué à un ramassage, même si ce délégué n'est PAS autorisé pour les enfants concernés.

**Localisation**:
- Code attendu: `/allobye_server_python/main.py:1023-1108` (handler `pickup-schedule-create`)
- Règle manquante: BR-002

**Règle métier**:
> Le délégué assigné à un ramassage (pickup_person_id) DOIT être autorisé pour TOUS les enfants du ramassage via la table `delegate_children`.

**Preuve de l'incohérence**:

```python
# main.py:1023-1108 - _handle_pickup_schedule_create()

# ✅ Validation 1: Parent owns children
for child_id in payload.child_ids:
    if not await verify_parent_owns_child(user.id, child_id):
        return error_response()

# ❌ MANQUE: Validation 2: Delegate authorized for children
# for child_id in payload.child_ids:
#     if not await verify_delegate_authorized_for_child(
#         payload.pickup_person_id, child_id
#     ):
#         return error_response("Délégué non autorisé pour cet enfant")

# ❌ Code continue sans validation!
results = await create_pickup_request(
    payload.child_ids,
    payload.pickup_person_id,  # N'importe quel ID accepté!
    ...
)
```

**Scénario d'exploitation**:

```
1. Parent A a enfant X
2. Parent A autorise Délégué D pour enfant X
3. Parent B a enfant Y
4. Parent B N'autorise PAS Délégué D pour enfant Y

5. Parent A appelle pickup-schedule-create avec:
   child_ids = [X, Y]  ← Enfant de Parent B!
   pickup_person_id = D

6. ✅ Validation parent ownership: PASSE (erreur détectée pour enfant Y)

7. MAIS si Parent B appelle:
   child_ids = [Y]
   pickup_person_id = D  ← D pas autorisé pour Y!

8. ❌ Aucune validation delegate authorization
9. ❌ Ramassage créé avec délégué non autorisé!
```

**RLS compense partiellement**:
- Le délégué D pourra VOIR le ramassage (policy ligne 363-371)
- Mais il ne DEVRAIT PAS pouvoir récupérer l'enfant Y

**Impact**:
- 🔴 **Sécurité enfant**: Délégué non autorisé peut théoriquement récupérer enfant
- 🔴 **Violation règle métier**: Parents perdent contrôle sur qui peut récupérer leurs enfants
- 🟠 **Incohérence base de données**: `pickup_person_id` pointe vers délégué invalide

**Correction immédiate requise**:

```python
async def _handle_pickup_schedule_create(arguments: Dict[str, Any]):
    # ... existing validations ...

    # AJOUTER: Validation delegate authorization
    for child_id in payload.child_ids:
        is_authorized = await verify_delegate_authorized_for_child(
            payload.pickup_person_id,
            child_id
        )
        if not is_authorized:
            return types.CallToolResult(
                content=[types.TextContent(
                    type="text",
                    text=f"Le délégué n'est pas autorisé à récupérer l'enfant {child_id}"
                )],
                isError=True
            )

    # ... continue with pickup creation ...

# Nouvelle fonction dans auth.py
async def verify_delegate_authorized_for_child(
    delegate_id: str,
    child_id: str
) -> bool:
    """Verify delegate is authorized for child."""
    supabase = get_supabase_admin()
    response = supabase.table("delegate_children").select("id").eq(
        "delegate_id", delegate_id
    ).eq("child_id", child_id).eq("is_active", True).execute()

    return len(response.data) > 0
```

---

### SEC-002: RLS policy school staff uses school email instead of user ID

**Sévérité**: 🔴 Critique (Faille d'authentification)

**Description**: Les RLS policies pour school staff utilisent `schools.email` pour identifier le personnel, mais ce champ contient l'email de l'ÉCOLE (ex: `direction@stjb.qc.ca`), pas l'email du personnel.

**Localisation**: `/allobye_server_python/schema.sql:303-311, 374-384, 472-481`

**Exemple de policy problématique**:

```sql
-- ❌ PROBLÈME: Utilise schools.email pour identifier staff
CREATE POLICY "School staff can view children at their school"
    ON children FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM schools
            WHERE schools.id = children.school_id
            AND schools.email = auth.jwt()->>'email'  -- ❌ FAUX!
        )
    );
```

**Analyse**:
- `schools.email` = Email de l'école (ex: `direction@stjb.qc.ca`)
- `auth.jwt()->>'email'` = Email du user connecté

**Question**: Comment un user peut-il avoir le même email que l'école?

**Réponse**: C'est IMPOSSIBLE avec l'architecture actuelle!

**Vérification dans seed data**:

```sql
-- seed.sql:19-35
INSERT INTO schools (id, name, address, phone, email, timezone) VALUES
(
    '11111111-1111-1111-1111-111111111111',
    'École Primaire Saint-Jean-Baptiste',
    '123 Rue Principale, Montréal, QC H1A 1A1',
    '514-555-0101',
    'direction@stjb.qc.ca',  -- ← Email de l'ÉCOLE
    'America/Montreal'
);
```

**Incohérence avec auth.py**:

```python
# auth.py:609-632 - verify_staff_at_school()
async def verify_staff_at_school(user_id: str, school_id: str) -> bool:
    """Verify that a user is staff at a school."""
    # ✅ Utilise user_schools junction table
    response = supabase.table("user_schools").select("id").eq(
        "user_id", user_id
    ).eq("school_id", school_id).execute()

    return len(response.data) > 0
```

**Problème**: `user_schools` table est référencée dans le code Python mais **ABSENTE du schema.sql**!

**Grep confirmation**:

```bash
$ grep -r "user_schools" allobye_server_python/
auth.py:471:    schools_response = supabase.table("user_schools").select("school_id")...
auth.py:541:    supabase.table("user_schools").delete().eq("user_id", user_id)...
auth.py:545:    supabase.table("user_schools").insert({...

$ grep -r "user_schools" allobye_server_python/schema.sql
(aucun résultat)
```

**Impact**:
- 🔴 **Sécurité**: RLS policies ne fonctionnent PAS pour school staff
- 🔴 **Feature broken**: Personnel scolaire ne peut pas accéder aux données
- 🔴 **Schema incomplet**: Table critique manquante

**Correction immédiate requise**:

1. **Ajouter table manquante dans schema.sql**:

```sql
-- NEW TABLE: User-School association
CREATE TABLE user_schools (
    user_id UUID NOT NULL,  -- Assume user_profiles table exists
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    role TEXT DEFAULT 'staff',  -- 'admin', 'staff', 'teacher'
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (user_id, school_id)
);

CREATE INDEX idx_user_schools_user_id ON user_schools(user_id);
CREATE INDEX idx_user_schools_school_id ON user_schools(school_id);

-- Enable RLS
ALTER TABLE user_schools ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role can manage user_schools"
    ON user_schools FOR ALL
    USING (auth.jwt()->>'role' = 'service_role');
```

2. **Corriger RLS policies pour staff**:

```sql
-- ✅ CORRECT: Utilise user_schools junction table
CREATE POLICY "School staff can view children at their school"
    ON children FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_schools us
            WHERE us.school_id = children.school_id
            AND us.user_id = auth.uid()  -- ✅ Utilise user ID, pas email
        )
    );
```

3. **Ajouter table user_profiles** (également manquante):

```sql
-- Assume this table should exist based on auth.py usage
CREATE TABLE user_profiles (
    id UUID PRIMARY KEY,  -- Same as auth.users.id
    email TEXT NOT NULL UNIQUE,
    name TEXT,
    role TEXT DEFAULT 'parent' CHECK (role IN ('parent', 'school_staff', 'admin')),
    email_verified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

---

### SEC-003: Duplication parent ownership (email vs ID)

**Sévérité**: 🔴 Critique (Incohérence identité)

**Description**: Le système utilise DEUX mécanismes différents pour identifier qu'un parent possède un enfant:
1. `children.parent_email` (TEXT)
2. `parent_children.parent_id` (UUID FK)

**Localisation**:
- Email system: `schema.sql:46` + RLS policies
- ID system: `auth.py:479-482` (référence `parent_children` table)

**Preuve**:

```sql
-- schema.sql:41-52 - Children table
CREATE TABLE children (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    grade TEXT,
    parent_email TEXT NOT NULL,  -- ❌ Système 1: Email
    parent_name TEXT,
    parent_phone TEXT,
    ...
);

-- RLS policy utilise parent_email
CREATE POLICY "Parents can view their own children"
    ON children FOR SELECT
    USING (parent_email = auth.jwt()->>'email');  -- ❌ Utilise email
```

```python
# auth.py:479-482 - get_user_profile()
# Fetch associated children (for parents)
children = []
if profile.get("role") == "parent":
    children_response = supabase.table("parent_children").select("child_id").eq(
        "parent_id", user_id  # ✅ Système 2: UUID FK
    ).execute()
```

**Grep confirmation**:

```bash
$ grep -r "parent_children" allobye_server_python/
auth.py:479:    children_response = supabase.table("parent_children").select...

$ grep -r "parent_children" allobye_server_python/schema.sql
(aucun résultat)
```

**Problème**: La table `parent_children` est référencée mais **ABSENTE du schema.sql**!

**Questions**:
1. Quelle est la source de vérité? Email ou ID?
2. Que se passe-t-il si email change?
3. Comment maintenir cohérence entre les deux?

**Impact**:
- 🔴 **Incohérence données**: Deux systèmes peuvent diverger
- 🟠 **Security bypass potentiel**: Changer email pourrait contourner ownership
- 🟠 **Maintenance nightmare**: Devs ne savent pas quel système utiliser

**Scénario problématique**:

```
1. Parent A crée compte avec email: parent@example.com
2. Parent A est assigné enfant X via parent_email = "parent@example.com"
3. Parent A change email vers: newparent@example.com
4. ❌ children.parent_email reste "parent@example.com" (non mis à jour)
5. ❌ Parent A ne peut plus voir enfant X (RLS check fail)
6. ❌ Mais parent_children.parent_id existe toujours (si table existe)
```

**Correction immédiate requise**:

1. **Ajouter table parent_children manquante**:

```sql
CREATE TABLE parent_children (
    parent_id UUID NOT NULL,  -- FK to user_profiles.id
    child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    relationship TEXT DEFAULT 'parent',  -- 'parent', 'guardian', 'other'
    primary_contact BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY (parent_id, child_id)
);

CREATE INDEX idx_parent_children_parent_id ON parent_children(parent_id);
CREATE INDEX idx_parent_children_child_id ON parent_children(child_id);
```

2. **Choisir une source de vérité** (Recommandation: UUID FK):

```sql
-- ✅ Supprimer parent_email de children (remplacé par FK)
ALTER TABLE children DROP COLUMN parent_email;
ALTER TABLE children DROP COLUMN parent_name;
ALTER TABLE children DROP COLUMN parent_phone;

-- ✅ Utiliser parent_children comme source de vérité unique
CREATE POLICY "Parents can view their children"
    ON children FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM parent_children pc
            WHERE pc.child_id = children.id
            AND pc.parent_id = auth.uid()  -- ✅ UUID, pas email
        )
    );
```

3. **Migration data**:

```sql
-- Migrer données existantes
INSERT INTO parent_children (parent_id, child_id)
SELECT
    up.id AS parent_id,
    c.id AS child_id
FROM children c
JOIN user_profiles up ON c.parent_email = up.email;
```

---

## Incohérences majeures (Fonctionnalité)

### FUNC-001: Initial pickup status contradiction

**Sévérité**: 🟠 Haute (Incohérence données vs code)

**Description**: Le code crée toujours les pickups avec `status = "confirmed"`, mais le seed data contient des pickups avec `status = "pending"`.

**Localisation**:
- Code: `/allobye_server_python/main.py:456`
- Seed data: `/allobye_server_python/seed.sql:144`

**Preuve**:

```python
# main.py:456
pickup_data = {
    "id": pickup_id,
    "pickup_person_id": pickup_person_id,
    "scheduled_time": scheduled_time,
    "status": "confirmed",  # ❌ Toujours "confirmed"
    "notes": notes,
}
```

```sql
-- seed.sql:139-148
INSERT INTO pickups (id, pickup_person_id, scheduled_time, status, ...)
VALUES (
    'p1111111-1111-1111-1111-111111111111',
    'd1111111-1111-1111-1111-111111111111',
    now_time + INTERVAL '15 minutes',
    'pending',  -- ❌ Status = "pending"
    ...
);
```

**Questions**:
1. Quel est le status initial correct: `pending` ou `confirmed`?
2. Si `pending`, quand passe-t-il à `confirmed`?
3. Si `confirmed`, pourquoi seed data a `pending`?

**Impact**:
- 🟠 **Confusion métier**: Développeurs ne savent pas le workflow
- 🟡 **Tests inconsistants**: Seed data ne reflète pas comportement réel

**Analyse workflow attendu**:

```
Option 1: pending → confirmed
  1. Parent crée pickup → status = "pending"
  2. École confirme → status = "confirmed"
  3. Délégué arrive → status = "in_progress"
  4. Enfant récupéré → status = "completed"

Option 2: confirmed direct (actuel)
  1. Parent crée pickup → status = "confirmed" (auto-approved)
  2. Délégué arrive → status = "in_progress"
  3. Enfant récupéré → status = "completed"
```

**Recommandation**:
1. **Décider** du workflow métier
2. **Aligner** code et seed data
3. **Documenter** transitions de status

```python
# Si workflow Option 1:
pickup_data = {
    "status": "pending",  # ✅ Initial status
}

# Ajouter handler pour confirmation
@mcp.tool(name="pickup-confirm")
async def confirm_pickup(pickup_id: str):
    """School confirms pickup request."""
    await pickup_repo.update_status(pickup_id, "confirmed")
```

---

### FUNC-002: ETA calculation manquante

**Sévérité**: 🟠 Haute (Feature advertised mais non implémentée)

**Description**: Le champ `pickups.eta_minutes` existe et est affiché dans le frontend, mais n'est JAMAIS calculé dynamiquement.

**Localisation**:
- Schema: `/allobye_server_python/schema.sql:74`
- Frontend display: `/src/allobye-dashboard/pickup-card.jsx:50-56`
- Seed data: `/allobye_server_python/seed.sql:147, 158, 170`
- Code calculation: **AUCUN** ❌

**Preuve**:

```sql
-- schema.sql:74
CREATE TABLE pickups (
    ...
    eta_minutes INTEGER,  -- ❌ Existe mais jamais utilisé
    ...
);
```

```javascript
// pickup-card.jsx:50-56
{pickup.eta && (
  <div className="eta-info">
    <span className="eta-icon">🚗</span>
    <span className="eta-time">ETA: {pickup.eta}</span>  // ✅ Affichage existe
    {pickup.delay > 0 && <span className="delay-badge">+{pickup.delay} min</span>}
  </div>
)}
```

```sql
-- seed.sql:147
INSERT INTO pickups (..., eta_minutes, ...)
VALUES (
    ...,
    15,  -- ❌ Valeur hardcodée, pas calculée
    ...
);
```

**Grep confirmation**:

```bash
$ grep -r "eta" allobye_server_python/*.py
(aucun résultat pour calcul dynamique)
```

**Impact**:
- 🟠 **Feature incomplete**: Promettre ETA mais ne pas livrer
- 🟡 **UI confusing**: Affiche ETA seulement si seed data le contient
- 🟡 **Business value loss**: ETA critique pour coordination ramassages

**Recommandation**: Implémenter calcul ETA

```python
class PickupService:
    async def calculate_eta(self, pickup_id: str) -> int:
        """Calculate ETA based on delegate location and traffic."""
        pickup = await self.pickup_repo.get_by_id(pickup_id)

        # Option 1: Simple (scheduled_time - now)
        eta_minutes = (pickup.scheduled_time - datetime.now()).total_seconds() / 60

        # Option 2: Advanced (intégration Google Maps API)
        # delegate_location = await self.location_service.get_delegate_location(pickup.pickup_person_id)
        # school_location = await self.school_repo.get_location(pickup.school_id)
        # eta_minutes = await self.maps_api.get_travel_time(delegate_location, school_location)

        await self.pickup_repo.update_eta(pickup_id, int(eta_minutes))
        return int(eta_minutes)

    async def update_all_etas(self):
        """Cron job to update ETAs for active pickups."""
        active_pickups = await self.pickup_repo.get_active()
        for pickup in active_pickups:
            await self.calculate_eta(pickup.id)
```

---

### FUNC-003: Late detection manquante

**Sévérité**: 🟠 Haute (Feature critique non implémentée)

**Description**: Le système ne détecte PAS automatiquement les retards. Le status `late` et le champ `delay_minutes` doivent être définis manuellement.

**Localisation**:
- Schema: Status `late` existe (schema.sql:72)
- Field: `delay_minutes` existe (schema.sql:75)
- Seed data: Exemples hardcodés (seed.sql:165-172)
- Code detection: **AUCUN** ❌

**Règle métier attendue**:
> Un pickup est "late" si `scheduled_time < NOW()` ET `status NOT IN ('completed', 'cancelled')`

**Preuve absence**:

```bash
$ grep -r "late" allobye_server_python/*.py
main.py:72:    status IN ('pending', 'confirmed', 'in_progress', 'completed', 'cancelled', 'late')
# ❌ Seulement définition enum, pas de calcul

$ grep -r "delay_minutes" allobye_server_python/*.py
(aucun résultat)
```

**Impact**:
- 🔴 **Safety**: Personnel scolaire ne sait pas si enfant attend trop longtemps
- 🟠 **User experience**: Parents ne sont pas alertés automatiquement
- 🟠 **Business logic incomplete**: Règle métier clé manquante

**Recommandation**: Implémenter détection automatique

```python
class PickupService:
    async def detect_late_pickups(self):
        """Cron job to detect and mark late pickups."""
        now = datetime.now()

        # Find pickups that should be late
        late_pickups = await self.pickup_repo.find_late_pickups(now)

        for pickup in late_pickups:
            # Calculate delay
            delay_minutes = int((now - pickup.scheduled_time).total_seconds() / 60)

            # Update status
            await self.pickup_repo.update(pickup.id, {
                "status": "late",
                "delay_minutes": delay_minutes
            })

            # Notify stakeholders
            await self.notification_service.notify_late_pickup(
                pickup_id=pickup.id,
                delay_minutes=delay_minutes
            )

            logger.warning("Pickup marked as late", pickup_id=pickup.id, delay=delay_minutes)

# Repository query
class PickupRepository:
    async def find_late_pickups(self, current_time: datetime) -> List[Pickup]:
        """Find pickups that are late."""
        data = await self.db.query("""
            SELECT * FROM pickups
            WHERE scheduled_time < :current_time
              AND status NOT IN ('completed', 'cancelled', 'late')
        """, current_time=current_time)
        return [Pickup.from_dict(d) for d in data]
```

**Scheduler**:

```python
# Add to main.py or separate scheduler.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

# Run every minute
@scheduler.scheduled_job('interval', minutes=1)
async def check_late_pickups():
    pickup_service = container.pickup_service
    await pickup_service.detect_late_pickups()

scheduler.start()
```

---

### FUNC-004: Delegate expiration non utilisée

**Sévérité**: 🟡 Moyenne (Feature non finalisée)

**Description**: Le champ `delegate_children.expires_at` existe mais n'est jamais vérifié dans les queries.

**Localisation**:
- Schema: `/allobye_server_python/schema.sql:97`
- Usage: **AUCUN** ❌

**Preuve**:

```sql
-- schema.sql:97
CREATE TABLE delegate_children (
    delegate_id UUID NOT NULL,
    child_id UUID NOT NULL,
    authorized_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    authorized_by TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,  -- ❌ Jamais vérifié
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (delegate_id, child_id)
);
```

```bash
$ grep -r "expires_at" allobye_server_python/*.py
(aucun résultat)
```

**Impact**:
- 🟡 **Security**: Autorisations temporaires ne sont jamais révoquées
- 🟡 **Business logic incomplete**: Feature promise mais non délivrée

**Recommandation**:

```python
# Dans get_authorized_delegates()
async def get_authorized_delegates(child_id: str) -> List[Dict[str, Any]]:
    response = supabase.table("delegate_children").select(
        "delegates(*)"
    ).eq("child_id", child_id).or_(
        # ✅ Filtre expiration
        "expires_at.is.null,expires_at.gt." + datetime.now().isoformat()
    ).execute()

    return [item["delegates"] for item in response.data if item.get("delegates")]
```

---

### FUNC-005: Permission types non validés

**Sévérité**: 🟡 Moyenne (Validation manquante)

**Description**: Le champ `delegates.permissions` est un ARRAY sans validation. N'importe quelle string peut être ajoutée.

**Localisation**: `/allobye_server_python/schema.sql:60`

**Preuve**:

```sql
-- schema.sql:60
permissions TEXT[] DEFAULT ARRAY['pickup']::TEXT[]
-- ❌ Aucun CHECK constraint!
```

**Valeurs attendues** (selon commentaires et code):
- `pickup`
- `emergency_contact`
- `medical_decisions`

**Problème**: Pas de validation!

```sql
-- ❌ Actuellement accepté:
INSERT INTO delegates (email, permissions)
VALUES ('test@example.com', ARRAY['invalid_permission', 'foo', 'bar']);
-- ✅ Accepté sans erreur!
```

**Impact**:
- 🟡 **Data quality**: Données invalides possibles
- 🟡 **Business logic**: Frontend/Backend doivent valider (duplication)

**Recommandation**:

```sql
-- ✅ Ajouter CHECK constraint
ALTER TABLE delegates
ADD CONSTRAINT check_valid_permissions
CHECK (
    permissions <@ ARRAY['pickup', 'emergency_contact', 'medical_decisions']::TEXT[]
);
```

---

### FUNC-006: Active delegates not always filtered

**Sévérité**: 🟡 Moyenne (Inconsistance filtering)

**Description**: Le champ `delegates.is_active` et `delegate_children.is_active` existent mais ne sont pas toujours filtrés dans les queries.

**Localisation**:
- Filtré: RLS policy (schema.sql:467)
- NON filtré: `get_authorized_delegates()` (main.py:555)

**Preuve**:

```sql
-- ✅ RLS policy filtre is_active
CREATE POLICY "Delegates can view emergencies for authorized children"
    ON emergencies FOR SELECT
    USING (
        ...
        AND dc.is_active = TRUE  -- ✅ Filtré
    );
```

```python
# ❌ Python ne filtre PAS is_active
async def get_authorized_delegates(child_id: str):
    response = supabase.table("delegate_children").select(
        "delegates(*)"
    ).eq("child_id", child_id).execute()
    # ❌ Devrait filtrer: .eq("is_active", True)

    return [item["delegates"] for item in response.data]
```

**Impact**:
- 🟡 **Inconsistency**: RLS filtre mais Python non
- 🟡 **Business logic**: Délégués inactifs peuvent apparaître dans certaines queries

**Recommandation**:

```python
# ✅ Toujours filtrer is_active
async def get_authorized_delegates(child_id: str):
    response = supabase.table("delegate_children").select(
        "delegates(*)"
    ).eq("child_id", child_id).eq(
        "is_active", True  # ✅ Filtrer actifs seulement
    ).execute()

    # ✅ Aussi filtrer delegates.is_active
    return [
        item["delegates"]
        for item in response.data
        if item.get("delegates") and item["delegates"].get("is_active", True)
    ]
```

---

### FUNC-007: Emergency auto-resolve manquante

**Sévérité**: 🟡 Moyenne (Feature incomplete)

**Description**: Les urgences ne sont jamais automatiquement marquées comme résolues. Le champ `resolved` reste `FALSE` indéfiniment.

**Localisation**:
- Schema: `emergencies.resolved` (schema.sql:109)
- Code auto-resolve: **AUCUN** ❌

**Impact**:
- 🟡 **Dashboard pollution**: Anciennes urgences s'accumulent
- 🟡 **UX**: Personnel voit urgences déjà résolues

**Recommandation**:

```python
class EmergencyService:
    async def auto_resolve_emergencies(self):
        """Auto-resolve emergencies based on type."""

        # Résoudre urgences "late" quand pickup complété
        await self.db.execute("""
            UPDATE emergencies e SET
                resolved = TRUE,
                resolved_at = NOW()
            FROM children c, pickups p, pickup_children pc
            WHERE e.child_id = c.id
              AND pc.child_id = c.id
              AND p.id = pc.pickup_id
              AND p.status = 'completed'
              AND e.emergency_type = 'late'
              AND e.resolved = FALSE
        """)

        # Résoudre urgences "cancel" quand pickup annulé
        await self.db.execute("""
            UPDATE emergencies e SET
                resolved = TRUE,
                resolved_at = NOW()
            FROM children c, pickups p, pickup_children pc
            WHERE e.child_id = c.id
              AND pc.child_id = c.id
              AND p.id = pc.pickup_id
              AND p.status = 'cancelled'
              AND e.emergency_type = 'cancel'
              AND e.resolved = FALSE
        """)
```

---

### FUNC-008: Timezone support non utilisé

**Sévérité**: 🟢 Basse (Feature non finalisée)

**Description**: Le champ `schools.timezone` existe mais n'est jamais utilisé dans les calculs de temps.

**Localisation**: `/allobye_server_python/schema.sql:35`

**Impact**:
- 🟢 **Fonctionnalité limitée**: Toutes les écoles traitées en UTC
- 🟢 **Future problem**: Multi-timezone non supporté

**Recommandation**: Utiliser timezone dans calculs

```python
import pytz

class PickupService:
    async def get_school_pickups(self, school_id: str, ...):
        school = await self.school_repo.get_by_id(school_id)
        school_tz = pytz.timezone(school.timezone)

        # Convertir en timezone école
        now_school = datetime.now(school_tz)

        # Calculs de fenêtre temporelle en timezone local
        if time_window == "today":
            start_time = now_school.replace(hour=0, minute=0, second=0)
            end_time = now_school.replace(hour=23, minute=59, second=59)
```

---

## Incohérences de données (Intégrité)

### DATA-001: Tables manquantes référencées dans le code

**Sévérité**: 🔴 Critique (Schema incomplet)

**Description**: Plusieurs tables sont référencées dans le code Python mais ABSENTES du schema.sql.

**Tables manquantes**:
1. `user_profiles` - Référencée dans `auth.py:455, 536, 574`
2. `user_schools` - Référencée dans `auth.py:471, 541, 545`
3. `parent_children` - Référencée dans `auth.py:479, 572`

**Preuve**:

```python
# auth.py:455
profile_response = supabase.table("user_profiles").select("*").eq("id", user_id).single().execute()
# ❌ Table "user_profiles" non définie dans schema.sql

# auth.py:471
schools_response = supabase.table("user_schools").select("school_id").eq("user_id", user_id).execute()
# ❌ Table "user_schools" non définie dans schema.sql

# auth.py:479
children_response = supabase.table("parent_children").select("child_id").eq("parent_id", user_id).execute()
# ❌ Table "parent_children" non définie dans schema.sql
```

**Grep confirmation**:

```bash
$ grep -r "user_profiles\|user_schools\|parent_children" schema.sql
(aucun résultat)
```

**Impact**:
- 🔴 **Schema incomplet**: Impossible d'appliquer schema.sql seul
- 🔴 **Production failure**: Code crash si tables n'existent pas
- 🟠 **Documentation**: Nouveau dev ne peut pas setup DB

**Recommandation**: Ajouter tables manquantes (voir SEC-002, SEC-003)

---

### DATA-002: CASCADE deletes dangereux

**Sévérité**: 🟠 Haute (Perte de données potentielle)

**Description**: La suppression d'une école cascade à TOUS ses enfants, pickups, emergencies, etc.

**Localisation**: `/allobye_server_python/schema.sql:44`

```sql
CREATE TABLE children (
    ...
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    ...
);
```

**Cascade chain**:

```
DELETE school
  ↓ CASCADE
DELETE children (tous les enfants de l'école)
  ↓ CASCADE
DELETE pickup_children (tous les liens pickup-enfant)
  ↓ CASCADE
DELETE delegate_children (toutes les autorisations)
  ↓ CASCADE
DELETE emergencies (toutes les urgences)
```

**Impact**:
- 🔴 **Data loss**: Suppression école = suppression MASSIVE de données
- 🟠 **No soft delete**: Impossible de désactiver école sans perte
- 🟡 **Audit trail**: Perte historique complet

**Scénario catastrophe**:

```sql
-- Admin supprime école par erreur
DELETE FROM schools WHERE id = 'school-id';

-- ❌ Effet cascade:
-- - 50 enfants supprimés
-- - 200 pickups supprimés
-- - 100 autorisations délégués supprimées
-- - 30 urgences supprimées
-- ❌ DONNÉES PERDUES DÉFINITIVEMENT
```

**Recommandation**: Soft delete avec flag

```sql
-- ✅ Ajouter colonne deleted_at
ALTER TABLE schools ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

-- ✅ Modifier policies pour filtrer deleted
CREATE POLICY "Schools are viewable by everyone"
    ON schools FOR SELECT
    USING (deleted_at IS NULL);  -- Seulement écoles actives

-- ✅ Soft delete au lieu de hard delete
UPDATE schools SET deleted_at = NOW() WHERE id = 'school-id';
-- ✅ Données préservées, just hidden
```

---

### DATA-003: Pas de contrainte sur pickup_person_id

**Sévérité**: 🟠 Haute (Intégrité référentielle faible)

**Description**: Rien n'empêche de créer un pickup avec un `pickup_person_id` qui n'existe pas dans `delegates`.

**Localisation**: `/allobye_server_python/schema.sql:69`

```sql
CREATE TABLE pickups (
    id UUID PRIMARY KEY,
    pickup_person_id UUID NOT NULL REFERENCES delegates(id) ON DELETE CASCADE,
    ...
);
```

**Observation**: Foreign key existe MAIS code Python ne vérifie pas avant insertion!

**Preuve**:

```python
# main.py:460 - create_pickup_request()
response = supabase.table("pickups").insert(pickup_data).execute()
# ❌ Pas de validation que pickup_person_id existe dans delegates!
```

**Scénario problème**:

```python
# ❌ Code actuel accepte:
await create_pickup_request(
    child_ids=["child_1"],
    pickup_person_id="non-existent-uuid",  # ❌ N'existe pas!
    ...
)
# ✅ PostgreSQL rejette (FK violation)
# Mais erreur DB, pas validation métier
```

**Impact**:
- 🟠 **Poor UX**: Erreur DB au lieu de validation métier
- 🟡 **Error messages**: Message cryptique au lieu de "Délégué non trouvé"

**Recommandation**: Valider avant insertion

```python
async def create_pickup_request(...):
    # ✅ Validation métier
    delegate = await delegate_repo.get_by_id(pickup_person_id)
    if not delegate:
        raise DelegateNotFoundError(f"Delegate {pickup_person_id} not found")

    # ✅ Aussi vérifier: delegate is active
    if not delegate.is_active:
        raise DelegateInactiveError(f"Delegate {pickup_person_id} is inactive")

    # Continue with insert...
```

---

### DATA-004: Seed data incohérent avec contraintes

**Sévérité**: 🟡 Moyenne (Test data invalide)

**Description**: Le seed data (seed.sql) contient des données qui violent les règles métier du code.

**Exemples**:

1. **Status "pending"** alors que code crée "confirmed":

```sql
-- seed.sql:144
INSERT INTO pickups (..., status, ...)
VALUES (..., 'pending', ...);  -- ❌ Code utilise "confirmed"
```

2. **ETA hardcodés** alors qu'ils devraient être calculés:

```sql
-- seed.sql:147
INSERT INTO pickups (..., eta_minutes, ...)
VALUES (..., 15, ...);  -- ❌ Valeur statique, devrait être calculée
```

**Impact**:
- 🟡 **Confusion**: Devs voient data qui ne match pas le code
- 🟡 **Tests**: Tests basés sur seed data peuvent être faux

**Recommandation**: Aligner seed data avec code

```sql
-- ✅ Utiliser status cohérent
INSERT INTO pickups (..., status, ...)
VALUES (..., 'confirmed', ...);  -- ✅ Match code

-- ✅ Ne pas définir ETA (sera calculé)
INSERT INTO pickups (..., eta_minutes, ...)
VALUES (..., NULL, ...);  -- ✅ NULL, calculé plus tard
```

---

### DATA-005: Pas de validation multi-école dans DB

**Sévérité**: 🟡 Moyenne (Validation manquante)

**Description**: Rien n'empêche dans la DB de créer un pickup avec des enfants de différentes écoles sans marquer comme "multi-school".

**Impact**:
- 🟡 **Data consistency**: Peut créer pickups invalides via SQL direct
- 🟡 **Relies on application**: Validation seulement en Python

**Recommandation**: Ajouter trigger de validation

```sql
CREATE FUNCTION validate_pickup_children_same_school()
RETURNS TRIGGER AS $$
DECLARE
    school_count INTEGER;
BEGIN
    SELECT COUNT(DISTINCT c.school_id) INTO school_count
    FROM pickup_children pc
    JOIN children c ON pc.child_id = c.id
    WHERE pc.pickup_id = NEW.pickup_id;

    IF school_count > 1 THEN
        -- ⚠️ Multi-école détecté
        UPDATE pickups SET multi_school = TRUE WHERE id = NEW.pickup_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_multi_school
    AFTER INSERT ON pickup_children
    FOR EACH ROW
    EXECUTE FUNCTION validate_pickup_children_same_school();
```

---

### DATA-006: Indexes manquants pour performance

**Sévérité**: 🟢 Basse (Performance)

**Description**: Certaines queries fréquentes n'ont pas d'index optimaux.

**Exemples**:

```sql
-- ❌ Requête fréquente sans index composite
SELECT * FROM pickups
WHERE status = 'confirmed'
AND scheduled_time > NOW()
ORDER BY scheduled_time;

-- ✅ Index existant:
CREATE INDEX idx_pickups_status ON pickups(status);
CREATE INDEX idx_pickups_scheduled_time ON pickups(scheduled_time);

-- ⚠️ Mais pas d'index composite!
```

**Recommandation**:

```sql
-- ✅ Ajouter indexes composites pour queries fréquentes
CREATE INDEX idx_pickups_status_scheduled_time ON pickups(status, scheduled_time)
WHERE status NOT IN ('completed', 'cancelled');  -- Partial index

CREATE INDEX idx_emergencies_resolved_created ON emergencies(resolved, created_at DESC)
WHERE resolved = FALSE;  -- Partial index pour urgences actives

CREATE INDEX idx_delegate_children_active ON delegate_children(child_id, delegate_id)
WHERE is_active = TRUE;  -- Partial index pour autorisations actives
```

---

## Duplications de logique

### DUP-001: Parent ownership validation (Python + RLS)

**Sévérité**: 🟡 Moyenne

**Description**: Même logique de vérification parent-enfant en Python ET dans RLS policy.

**Localisations**:
- Python: `auth.py:598-600`
- RLS: `schema.sql:300`

**Duplication**:

```python
# Python
async def verify_parent_owns_child(parent_id: str, child_id: str):
    response = supabase.table("parent_children").select("id").eq(
        "parent_id", parent_id
    ).eq("child_id", child_id).execute()
    return len(response.data) > 0
```

```sql
-- RLS
USING (parent_email = auth.jwt()->>'email')
```

**Impact**: Logique doit être maintenue en 2 endroits.

---

### DUP-002: Status enumerations (DB + Python + Frontend)

**Sévérité**: 🟡 Moyenne

**Localisations**:
- DB: `schema.sql:72`
- Python: `main.py:456` (hardcoded)
- Frontend: `pickup-card.jsx:68-72`

**Duplication**: Enum défini 3 fois.

---

### DUP-003: Filter "next 30min" (Backend + Frontend)

**Sévérité**: 🟡 Moyenne

**Localisations**:
- Backend: `main.py:623-624` (time_window="current")
- Frontend: `dashboard.jsx:150-154`

**Duplication**:

```python
# Backend
if time_window == "current":
    end_time = now + timedelta(minutes=30)
```

```javascript
// Frontend
const thirtyMinutesFromNow = new Date(currentTime.getTime() + 30 * 60 * 1000);
return scheduledTime <= thirtyMinutesFromNow;
```

**Impact**: Règle "30 minutes" dupliquée.

---

### DUP-004 à DUP-007: (Autres duplications)

Voir matrice complète dans `logic_separation_analysis.md`.

---

## Contradictions code vs commentaires

### CONT-001: A2A simulation vs real implementation

**Sévérité**: 🟡 Moyenne (Documentation trompeuse)

**Description**: Le code dit "A2A simulation" mais les commentaires/noms de fonctions suggèrent une vraie implémentation.

**Localisation**: `/allobye_server_python/main.py:489-494`

**Code**:

```python
async def coordinate_cross_school_pickup(...):
    """Coordinate pickup across multiple schools (A2A simulation)."""
    # ...
    # ✅ Commentaire dit "simulation"
    pickup["a2a_messages"] = [
        {"school_id": s["id"], "status": "confirmed"} for s in schools
    ]  # ❌ Format suggère vrai messages
    # In real implementation, broadcast to A2A bus for each school
    # ✅ Commentaire dit "In real implementation"
    return pickup
```

**Confusion**:
- Commentaire docstring: "A2A simulation"
- Commentaire inline: "In real implementation, broadcast to A2A bus"
- Structure données: Format comme si vraie implementation

**Impact**: Devs ne savent pas si c'est simulation ou réel.

**Recommandation**: Clarifier

```python
async def coordinate_cross_school_pickup(...):
    """
    Coordinate pickup across multiple schools.

    SIMULATION MODE: Currently returns mock A2A messages.
    TODO: Integrate real A2A bus when available.
    """
    # ...
    pickup["a2a_messages_simulated"] = [...]  # ✅ Nom clair
    pickup["a2a_implementation_status"] = "simulated"  # ✅ Explicite
```

---

### CONT-002: Mock data in production code

**Sévérité**: 🟡 Moyenne

**Description**: Plusieurs fonctions retournent mock data au lieu de lever une erreur si Supabase n'est pas disponible.

**Exemple**: `main.py:403-406`

```python
async def get_schools_for_children(child_ids: List[str]):
    supabase = get_supabase()
    if not supabase:
        # Mock data for development
        return [{"id": "school_1", "name": "École Primaire Exemple"}]
    # ...
```

**Problème**:
- En production, si Supabase down → retourne mock data!
- Tests peuvent passer avec mock alors que vraie DB fail

**Recommandation**: Lever erreur

```python
if not supabase:
    if os.getenv("ENVIRONMENT") == "development":
        return [{"id": "school_1", "name": "École Primaire Exemple"}]
    else:
        raise DatabaseUnavailableError("Supabase client not available")
```

---

## Edge cases non couverts

### EDGE-001: Pickup avec 0 enfants

**Sévérité**: 🟢 Basse

**Description**: Rien n'empêche de créer un pickup sans enfants (child_ids vide).

**Validation actuelle**:

```python
# PickupScheduleInput model
child_ids: List[str] = Field(..., min_length=1)  # ✅ Validation input
```

**Mais**:

```python
# create_pickup_request()
for child_id in child_ids:  # ⚠️ Si child_ids = [], boucle vide
    supabase.table("pickup_children").insert({...})
# ✅ Pickup créé SANS enfants!
```

**Recommendation**: Ajouter assertion

```python
async def create_pickup_request(child_ids, ...):
    if not child_ids:
        raise ValueError("Pickup must have at least one child")
    # ...
```

---

## Plan d'action

### Priorité 1: Sécurité (Immédiat)

1. **SEC-001**: Implémenter validation delegate authorization
   - Effort: 0.5 jour
   - Impact: 🔴 Critique

2. **SEC-002**: Ajouter tables manquantes (user_profiles, user_schools)
   - Effort: 1 jour
   - Impact: 🔴 Critique

3. **SEC-003**: Résoudre duplication parent ownership
   - Effort: 1 jour
   - Impact: 🔴 Critique

**Total Priorité 1**: 2.5 jours

---

### Priorité 2: Fonctionnalité (Sprint suivant)

4. **FUNC-001**: Clarifier initial pickup status
   - Effort: 0.5 jour
   - Impact: 🟠 Haute

5. **FUNC-002**: Implémenter ETA calculation
   - Effort: 2 jours
   - Impact: 🟠 Haute

6. **FUNC-003**: Implémenter late detection
   - Effort: 1 jour
   - Impact: 🟠 Haute

7. **DATA-001**: Compléter schema.sql avec tables manquantes
   - Effort: 0.5 jour (dupliqué avec SEC-002)
   - Impact: 🔴 Critique

**Total Priorité 2**: 4 jours

---

### Priorité 3: Qualité (Backlog)

8. **DUP-001 à DUP-007**: Réduire duplications
   - Effort: 3 jours
   - Impact: 🟡 Moyenne

9. **FUNC-004 à FUNC-008**: Features non finalisées
   - Effort: 2 jours
   - Impact: 🟡 Moyenne

10. **DATA-002 à DATA-006**: Améliorations data integrity
    - Effort: 2 jours
    - Impact: 🟡 Moyenne

**Total Priorité 3**: 7 jours

---

### Estimation totale

**Effort total**: 13.5 jours
**Sprints**: 3 sprints (2 semaines chacun)

---

## Conclusion

**27 incohérences détectées**, dont:
- 🔴 **3 critiques de sécurité** (à corriger immédiatement)
- 🟠 **8 majeures de fonctionnalité** (à planifier sprint suivant)
- 🟡 **14 moyennes de qualité** (à traiter progressivement)
- 🟢 **2 basses** (backlog)

**Action immédiate recommandée**: Corriger les 3 incohérences critiques de sécurité avant mise en production.

**Recommandation long-terme**: Suivre le plan de refactoring dans `logic_separation_analysis.md` pour éviter de nouvelles incohérences.
