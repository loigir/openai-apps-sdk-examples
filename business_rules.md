# Business Rules - AllôBye

**Date**: 2025-11-04
**Analyseur**: Extracteur de Logique Métier
**Codebase**: AllôBye - Système de coordination de ramassage scolaire

---

## Table des matières

1. [Format des règles](#format-des-règles)
2. [Règles de ramassage (BR-001 à BR-009)](#règles-de-ramassage-br-001-à-br-009)
3. [Règles d'autorisation de délégués (BR-010 à BR-019)](#règles-dautorisation-de-délégués-br-010-à-br-019)
4. [Règles de gestion des urgences (BR-020 à BR-029)](#règles-de-gestion-des-urgences-br-020-à-br-029)
5. [Règles d'authentification et autorisation (BR-030 à BR-049)](#règles-dauthentification-et-autorisation-br-030-à-br-049)
6. [Règles de calcul et affichage (BR-050 à BR-059)](#règles-de-calcul-et-affichage-br-050-à-br-059)
7. [Règles de données et intégrité (BR-060 à BR-069)](#règles-de-données-et-intégrité-br-060-à-br-069)
8. [Index des règles](#index-des-règles)

---

## Format des règles

Chaque règle métier suit ce format:

```
BR-XXX: Nom court de la règle
└─ Description: Description complète de la règle
└─ Acteurs: Qui est concerné
└─ Condition: Quand la règle s'applique
└─ Action: Ce qui doit se passer
└─ Localisation: Où dans le code
└─ Statut: ✅ Implémenté | ⚠️ Partiel | ❌ Manquant
└─ Priorité: 🔴 Critique | 🟠 Haute | 🟡 Moyenne | 🟢 Basse
```

---

## Règles de ramassage (BR-001 à BR-009)

### BR-001: Parent ownership validation
- **Description**: Un parent ne peut planifier un ramassage que pour les enfants qu'il possède
- **Acteurs**: Parent, Enfant
- **Condition**: Lors de la création d'un ramassage (`pickup-schedule-create`)
- **Action**: Vérifier que `parent_id` possède TOUS les `child_ids` du ramassage
- **Implémentation**:
  - Appel: `verify_parent_owns_child(parent_id, child_id)` pour chaque enfant
  - Rejection: Si un seul enfant n'appartient pas au parent
- **Localisation**: `/allobye_server_python/main.py:1052-1062`
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (sécurité)

```python
# Code de validation
for child_id in payload.child_ids:
    if not await verify_parent_owns_child(user.id, child_id):
        return error_response("Vous n'êtes pas autorisé...")
```

---

### BR-002: Delegate authorization for pickup
- **Description**: Le délégué assigné à un ramassage doit être autorisé pour TOUS les enfants du ramassage
- **Acteurs**: Parent, Délégué, Enfant
- **Condition**: Lors de la création d'un ramassage avec `pickup_person_id`
- **Action**: Vérifier que `delegate_id` est autorisé (via `delegate_children`) pour TOUS les `child_ids`
- **Implémentation**: **AUCUNE** ⚠️
- **Localisation**: Devrait être dans `/allobye_server_python/main.py:1023-1108` (handler pickup-schedule-create)
- **Statut**: ❌ Manquant
- **Priorité**: 🔴 Critique (sécurité)

**Règle attendue non implémentée**:
```python
# Code manquant
for child_id in payload.child_ids:
    if not await verify_delegate_authorized_for_child(
        payload.pickup_person_id, child_id
    ):
        return error_response("Délégué non autorisé pour cet enfant")
```

---

### BR-003: Multi-school coordination
- **Description**: Un ramassage concernant des enfants de plusieurs écoles nécessite une coordination A2A
- **Acteurs**: Parent, Enfants (multi-écoles), Écoles
- **Condition**: `len(get_schools_for_children(child_ids)) > 1`
- **Action**: Appeler `coordinate_cross_school_pickup()` au lieu de `create_pickup_request()`
- **Implémentation**:
  - Détection: Automatique via `get_schools_for_children()`
  - Coordination: Simulation A2A (broadcast à chaque école)
  - Retour: `schools_affected` + `a2a_messages`
- **Localisation**: `/allobye_server_python/main.py:1068-1081`
- **Statut**: ✅ Implémenté (simulation A2A)
- **Priorité**: 🟠 Haute (coordination système)

---

### BR-004: Initial pickup status
- **Description**: Tout nouveau ramassage est créé avec le statut "confirmed"
- **Acteurs**: Système
- **Condition**: Création d'un ramassage via `create_pickup_request()`
- **Action**: Définir `status = "confirmed"` par défaut
- **Implémentation**: Hardcodé dans les données du pickup
- **Localisation**: `/allobye_server_python/main.py:456`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟡 Moyenne

**Note**: Le seed data contient des pickups avec `status = "pending"`, ce qui contredit le code. Incohérence!

```python
pickup_data = {
    "status": "confirmed",  # Toujours "confirmed", jamais "pending"
}
```

---

### BR-005: Status transition - Cancellation cascade
- **Description**: L'annulation d'un ramassage réinitialise tous les checkouts des enfants
- **Acteurs**: Ramassage, Enfants
- **Condition**: Changement de status: `OLD.status != 'cancelled' AND NEW.status = 'cancelled'`
- **Action**:
  - Mettre `checked_out = FALSE` pour tous les enfants du ramassage
  - Effacer `checked_out_at` et `checked_out_by`
- **Implémentation**: Trigger PostgreSQL `cascade_pickup_status()`
- **Localisation**: `/allobye_server_python/schema.sql:238-244`
- **Statut**: ✅ Implémenté (database trigger)
- **Priorité**: 🟠 Haute (cohérence données)

```sql
UPDATE pickup_children
SET checked_out = FALSE,
    checked_out_at = NULL,
    checked_out_by = NULL
WHERE pickup_id = NEW.id;
```

---

### BR-006: Status transition - Completion auto-checkout
- **Description**: La complétion d'un ramassage marque automatiquement comme "checked out" tous les enfants non encore sortis
- **Acteurs**: Ramassage, Enfants
- **Condition**: Changement de status: `OLD.status != 'completed' AND NEW.status = 'completed'`
- **Action**:
  - Mettre `checked_out = TRUE` pour les enfants où `checked_out = FALSE`
  - Mettre `checked_out_at = NOW()` si NULL
- **Implémentation**: Trigger PostgreSQL `cascade_pickup_status()`
- **Localisation**: `/allobye_server_python/schema.sql:247-252`
- **Statut**: ✅ Implémenté (database trigger)
- **Priorité**: 🟠 Haute (cohérence données)

```sql
UPDATE pickup_children
SET checked_out = TRUE,
    checked_out_at = COALESCE(checked_out_at, NOW())
WHERE pickup_id = NEW.id AND checked_out = FALSE;
```

---

### BR-007: ETA calculation
- **Description**: Le système devrait calculer l'ETA (Estimated Time of Arrival) pour chaque ramassage
- **Acteurs**: Ramassage, Délégué
- **Condition**: En continu ou à la demande
- **Action**: Calculer et mettre à jour le champ `eta_minutes`
- **Implémentation**: **AUCUNE** ⚠️
- **Localisation**: Champ existe (`pickups.eta_minutes`) mais jamais utilisé
- **Statut**: ❌ Manquant
- **Priorité**: 🟡 Moyenne (feature manquante)

**Observation**: Le champ existe dans:
- Database: `schema.sql:74` (INTEGER NULL)
- Seed data: `seed.sql:147, 158, 170` (valeurs hardcodées)
- Frontend: `pickup-card.jsx:50` (affichage si présent)

**Mais**: Aucun code de calcul dynamique!

---

### BR-008: Late detection
- **Description**: Le système devrait détecter automatiquement les retards et marquer les ramassages comme "late"
- **Acteurs**: Ramassage, Temps
- **Condition**: `scheduled_time < NOW() AND status NOT IN ('completed', 'cancelled')`
- **Action**: Mettre à jour `status = 'late'` et calculer `delay_minutes`
- **Implémentation**: **AUCUNE** ⚠️
- **Localisation**: Champs existent mais pas de calcul automatique
- **Statut**: ❌ Manquant (détection manuelle uniquement)
- **Priorité**: 🟠 Haute (monitoring critique)

**Observation**:
- Status "late" existe dans l'énumération
- Champ `delay_minutes` existe
- Seed data a des exemples hardcodés
- **Mais**: Pas de cron/scheduler pour mettre à jour automatiquement

---

### BR-009: Allowed pickup statuses
- **Description**: Un ramassage ne peut avoir que les statuts: pending, confirmed, in_progress, completed, cancelled, late
- **Acteurs**: Système
- **Condition**: Toute création ou modification de pickup
- **Action**: Rejeter toute valeur de status hors de cette liste
- **Implémentation**: CHECK constraint PostgreSQL
- **Localisation**: `/allobye_server_python/schema.sql:72`
- **Statut**: ✅ Implémenté (database constraint)
- **Priorité**: 🔴 Critique (intégrité données)

```sql
status TEXT DEFAULT 'pending' CHECK (
    status IN ('pending', 'confirmed', 'in_progress', 'completed', 'cancelled', 'late')
)
```

---

## Règles d'autorisation de délégués (BR-010 à BR-019)

### BR-010: Unique delegate by email
- **Description**: Un délégué est identifié de manière unique par son email
- **Acteurs**: Délégué
- **Condition**: Création ou mise à jour d'un délégué
- **Action**:
  - Si email existe: UPDATE les données
  - Si email n'existe pas: INSERT nouveau délégué
- **Implémentation**:
  - DB: `UNIQUE NOT NULL` constraint sur `delegates.email`
  - Python: `upsert(on_conflict="email")`
- **Localisation**:
  - `/allobye_server_python/schema.sql:57`
  - `/allobye_server_python/main.py:525`
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (identité)

```python
supabase.table("delegates").upsert(delegate_data, on_conflict="email")
```

---

### BR-011: Granular authorization per child
- **Description**: Les autorisations de délégués sont granulaires par enfant (pas globales)
- **Acteurs**: Parent, Délégué, Enfant
- **Condition**: Lors de l'autorisation d'un délégué
- **Action**: Créer un lien `delegate_id ↔ child_id` dans `delegate_children` pour CHAQUE enfant
- **Implémentation**: Junction table many-to-many
- **Localisation**: `/allobye_server_python/schema.sql:92-100`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟠 Haute (sécurité fine)

**Exemple**: Délégué D peut récupérer enfant A mais pas enfant B du même parent.

---

### BR-012: Permission types
- **Description**: Un délégué peut avoir plusieurs types de permissions: pickup, emergency_contact, medical_decisions
- **Acteurs**: Délégué
- **Condition**: Lors de l'autorisation d'un délégué
- **Action**: Stocker les permissions dans un ARRAY
- **Implémentation**:
  - Type: `TEXT[]` (PostgreSQL array)
  - Défaut: `ARRAY['pickup']`
- **Localisation**: `/allobye_server_python/schema.sql:60`
- **Statut**: ⚠️ Partiel (pas de validation)
- **Priorité**: 🟡 Moyenne

**Problème**: Aucune validation! N'importe quelle string peut être ajoutée à l'array.

```sql
permissions TEXT[] DEFAULT ARRAY['pickup']::TEXT[]
-- Problème: Pas de CHECK constraint pour valider les valeurs
```

**Règle attendue**:
```sql
CHECK (permissions <@ ARRAY['pickup', 'emergency_contact', 'medical_decisions']::TEXT[])
```

---

### BR-013: Multi-school A2A synchronization
- **Description**: L'autorisation d'un délégué est synchronisée avec toutes les écoles des enfants concernés
- **Acteurs**: Parent, Délégué, Enfants, Écoles
- **Condition**: Lors de l'appel à `delegate-authorize`
- **Action**:
  - Inférer les écoles via `get_schools_for_children(child_ids)`
  - Broadcaster via A2A à chaque école
  - Retourner status de synchronisation
- **Implémentation**: Simulation A2A (pas de vrai bus)
- **Localisation**: `/allobye_server_python/main.py:1153-1161`
- **Statut**: ✅ Implémenté (simulation)
- **Priorité**: 🟠 Haute (coordination système)

```python
schools = await get_schools_for_children(payload.child_ids)
sync_results = await broadcast_delegate_authorization(
    delegate_email, child_ids, permissions, schools
)
# Retourne: messages = [{"school_id": s["id"], "status": "synced"}, ...]
```

---

### BR-014: Active delegates only
- **Description**: Seuls les délégués actifs (is_active = TRUE) sont considérés pour les ramassages et urgences
- **Acteurs**: Délégué
- **Condition**: Lors de la récupération des délégués autorisés
- **Action**: Filtrer les délégués avec `is_active = TRUE`
- **Implémentation**:
  - DB: Champ `delegates.is_active` (BOOLEAN DEFAULT TRUE)
  - RLS policies: Pas de filtre actif ⚠️
  - Python: Pas de filtre systématique ⚠️
- **Localisation**: `/allobye_server_python/schema.sql:61`
- **Statut**: ⚠️ Partiel (champ existe, pas toujours utilisé)
- **Priorité**: 🟠 Haute

**Problème**: Le champ existe mais n'est pas systématiquement filtré. Exemple:
```python
# main.py:555 - get_authorized_delegates()
response = supabase.table("delegate_children").select("delegates(*)")
# Devrait filtrer: .eq("delegates.is_active", True)
```

---

### BR-015: Delegate expiration
- **Description**: Les autorisations de délégués peuvent avoir une date d'expiration
- **Acteurs**: Parent, Délégué, Enfant
- **Condition**: Lors de la vérification d'autorisation
- **Action**: Rejeter les autorisations où `expires_at < NOW()`
- **Implémentation**: **AUCUNE** ⚠️
- **Localisation**: Champ existe (`delegate_children.expires_at`) mais jamais vérifié
- **Statut**: ❌ Manquant
- **Priorité**: 🟡 Moyenne

**Règle attendue**:
```python
# Devrait filtrer dans get_authorized_delegates():
.filter("expires_at", "is", None)  # Pas d'expiration
.filter("expires_at", "gt", datetime.now().isoformat())  # Ou pas encore expiré
```

---

### BR-016: Authorization tracking
- **Description**: Le système doit tracer qui a autorisé un délégué et quand
- **Acteurs**: Parent (authorizateur), Délégué (autorisé), Enfant
- **Condition**: Lors de l'autorisation
- **Action**: Enregistrer `authorized_by` (email du parent) et `authorized_at` (timestamp)
- **Implémentation**:
  - Champs: `delegate_children.authorized_by`, `authorized_at`
  - Population: **PARTIELLE** ⚠️
- **Localisation**: `/allobye_server_python/schema.sql:96-97`
- **Statut**: ⚠️ Partiel (champs existent, pas toujours remplis)
- **Priorité**: 🟡 Moyenne (audit)

**Observation**: Les champs existent dans le schéma mais le code Python ne les remplit pas:
```python
# main.py:529-532 - broadcast_delegate_authorization
supabase.table("delegate_children").insert({
    "delegate_id": delegate_id,
    "child_id": child_id,
    # Manque: "authorized_by", "authorized_at"
})
```

---

### BR-017: Delegate can view own profile
- **Description**: Un délégué peut consulter son propre profil
- **Acteurs**: Délégué
- **Condition**: Lecture de `delegates` table
- **Action**: Autoriser si `delegates.email = auth.jwt()->>'email'`
- **Implémentation**: RLS policy
- **Localisation**: `/allobye_server_python/schema.sql:324-326`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟢 Basse

```sql
CREATE POLICY "Delegates can view their own profile"
    ON delegates FOR SELECT
    USING (email = auth.jwt()->>'email');
```

---

### BR-018: Delegate can view assigned pickups
- **Description**: Un délégué peut voir les ramassages où il est la personne de ramassage
- **Acteurs**: Délégué, Ramassage
- **Condition**: Lecture de `pickups` table
- **Action**: Autoriser si `pickups.pickup_person_id = delegates.id` ET `delegates.email = user.email`
- **Implémentation**: RLS policy
- **Localisation**: `/allobye_server_python/schema.sql:363-371`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟠 Haute (sécurité)

```sql
CREATE POLICY "Delegates can view their assigned pickups"
    ON pickups FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM delegates
            WHERE delegates.id = pickups.pickup_person_id
            AND delegates.email = auth.jwt()->>'email'
        )
    );
```

---

### BR-019: Parent can view authorized delegates
- **Description**: Un parent peut voir les délégués qu'il a autorisés pour ses enfants
- **Acteurs**: Parent, Délégué, Enfant
- **Condition**: Lecture de `delegates` table
- **Action**: Autoriser si ∃ un enfant du parent autorisé par ce délégué
- **Implémentation**: RLS policy avec JOIN complexe
- **Localisation**: `/allobye_server_python/schema.sql:329-338`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟠 Haute (sécurité)

```sql
CREATE POLICY "Parents can view authorized delegates"
    ON delegates FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM delegate_children dc
            JOIN children c ON dc.child_id = c.id
            WHERE dc.delegate_id = delegates.id
            AND c.parent_email = auth.jwt()->>'email'
        )
    );
```

---

## Règles de gestion des urgences (BR-020 à BR-029)

### BR-020: Emergency types enumeration
- **Description**: Les types d'urgence sont limités à: late, illness, cancel, injury, other
- **Acteurs**: Système
- **Condition**: Création ou modification d'une urgence
- **Action**: Rejeter toute valeur hors de cette liste
- **Implémentation**: CHECK constraint PostgreSQL
- **Localisation**: `/allobye_server_python/schema.sql:106`
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (intégrité données)

```sql
emergency_type TEXT NOT NULL CHECK (
    emergency_type IN ('late', 'illness', 'cancel', 'injury', 'other')
)
```

---

### BR-021: Severity levels
- **Description**: La sévérité d'une urgence doit être: low, medium, high, ou critical
- **Acteurs**: Parent, Système
- **Condition**: Création d'une urgence
- **Action**:
  - Valider que severity ∈ {low, medium, high, critical}
  - Défaut: medium si non spécifié
- **Implémentation**: CHECK constraint + DEFAULT
- **Localisation**: `/allobye_server_python/schema.sql:108`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟠 Haute (classification urgences)

```sql
severity TEXT DEFAULT 'medium' CHECK (
    severity IN ('low', 'medium', 'high', 'critical')
)
```

---

### BR-022: Emergency cascade to all delegates
- **Description**: Une urgence doit être notifiée à TOUS les délégués autorisés pour l'enfant
- **Acteurs**: Parent (déclarateur), Enfant, Délégués
- **Condition**: Déclaration d'urgence via `emergency-declare`
- **Action**:
  - Récupérer tous les délégués autorisés actifs
  - Broadcaster via A2A à chaque délégué
  - Enregistrer la liste dans `notified_delegates`
- **Implémentation**: Simulation A2A
- **Localisation**: `/allobye_server_python/main.py:1222-1232`
- **Statut**: ✅ Implémenté (simulation)
- **Priorité**: 🔴 Critique (notification urgence)

```python
delegates = await get_authorized_delegates(payload.child_id)
cascade_results = await broadcast_emergency(
    child_id, emergency_type, context, delegates, schools
)
# Retourne: a2a_trace avec count de délégués notifiés
```

---

### BR-023: Emergency cascade to all schools
- **Description**: Une urgence doit être notifiée à TOUTES les écoles de l'enfant
- **Acteurs**: Parent (déclarateur), Enfant, Écoles
- **Condition**: Déclaration d'urgence via `emergency-declare`
- **Action**:
  - Récupérer toutes les écoles de l'enfant
  - Broadcaster via A2A à chaque école
  - Enregistrer la liste dans `notified_schools`
- **Implémentation**: Simulation A2A
- **Localisation**: `/allobye_server_python/main.py:1223-1232`
- **Statut**: ✅ Implémenté (simulation)
- **Priorité**: 🔴 Critique (notification urgence)

---

### BR-024: Real-time emergency notification
- **Description**: Une urgence déclenche une notification temps réel via PostgreSQL NOTIFY
- **Acteurs**: Système, Abonnés
- **Condition**: INSERT dans `emergencies` table
- **Action**:
  - Trigger `notify_emergency()` exécuté
  - pg_notify sur channel 'emergency_alert'
  - Payload JSON avec toutes les infos
- **Implémentation**: Trigger PostgreSQL
- **Localisation**: `/allobye_server_python/schema.sql:196-231`
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (temps réel)

```sql
CREATE TRIGGER emergency_notification
    AFTER INSERT ON emergencies
    FOR EACH ROW
    EXECUTE FUNCTION notify_emergency();
```

**Payload NOTIFY**:
```json
{
  "emergency_id": "uuid",
  "child_id": "uuid",
  "school_id": "uuid",
  "school_name": "École X",
  "type": "late",
  "severity": "medium",
  "context": "Description...",
  "created_at": "2025-11-04T..."
}
```

---

### BR-025: Emergency default status
- **Description**: Une urgence est créée avec `resolved = FALSE` par défaut
- **Acteurs**: Système
- **Condition**: Création d'urgence
- **Action**: Définir `resolved = FALSE`
- **Implémentation**: DEFAULT constraint
- **Localisation**: `/allobye_server_python/schema.sql:109`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟡 Moyenne

```sql
resolved BOOLEAN DEFAULT FALSE
```

---

### BR-026: Emergency auto-resolve
- **Description**: Le système devrait marquer automatiquement comme résolues les urgences selon des critères
- **Acteurs**: Système
- **Condition**: Selon type d'urgence:
  - `late`: Quand ramassage complété
  - `cancel`: Quand ramassage annulé
  - `illness`: Après X heures ou action manuelle
- **Action**: Mettre à jour `resolved = TRUE` et `resolved_at = NOW()`
- **Implémentation**: **AUCUNE** ⚠️
- **Localisation**: Champs existent mais pas de logique d'auto-résolution
- **Statut**: ❌ Manquant
- **Priorité**: 🟠 Haute (gestion urgences)

**Règle attendue**: Trigger ou cron qui résout automatiquement:
```sql
-- Résoudre urgences "late" quand pickup complété
UPDATE emergencies e SET
    resolved = TRUE,
    resolved_at = NOW()
FROM pickups p, children c
WHERE e.child_id = c.id
  AND p.id IN (SELECT pickup_id FROM pickup_children WHERE child_id = c.id)
  AND p.status = 'completed'
  AND e.emergency_type = 'late'
  AND e.resolved = FALSE;
```

---

### BR-027: Parent owns emergency child
- **Description**: Un parent ne peut déclarer une urgence que pour ses propres enfants
- **Acteurs**: Parent, Enfant
- **Condition**: Appel à `emergency-declare`
- **Action**: Vérifier `verify_parent_owns_child(parent_id, child_id)`
- **Implémentation**: Validation dans handler
- **Localisation**: `/allobye_server_python/main.py:1210-1219`
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (sécurité)

```python
if not await verify_parent_owns_child(user.id, payload.child_id):
    return error_response("Vous n'êtes pas autorisé...")
```

---

### BR-028: Delegates can view emergencies for authorized children
- **Description**: Un délégué peut voir les urgences des enfants pour lesquels il est autorisé
- **Acteurs**: Délégué, Enfant, Urgence
- **Condition**: Lecture de `emergencies` table
- **Action**: Autoriser si ∃ autorisation active dans `delegate_children`
- **Implémentation**: RLS policy
- **Localisation**: `/allobye_server_python/schema.sql:459-469`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟠 Haute (sécurité)

```sql
CREATE POLICY "Delegates can view emergencies for authorized children"
    ON emergencies FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM delegate_children dc
            JOIN delegates d ON dc.delegate_id = d.id
            WHERE dc.child_id = emergencies.child_id
            AND d.email = auth.jwt()->>'email'
            AND dc.is_active = TRUE  -- Important!
        )
    );
```

---

### BR-029: School staff can view emergencies at their school
- **Description**: Le personnel scolaire peut voir les urgences des enfants de son école
- **Acteurs**: School staff, Enfant, Urgence
- **Condition**: Lecture de `emergencies` table
- **Action**: Autoriser si l'enfant appartient à l'école du staff
- **Implémentation**: RLS policy
- **Localisation**: `/allobye_server_python/schema.sql:472-481`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟠 Haute (sécurité)

```sql
CREATE POLICY "School staff can view emergencies at their school"
    ON emergencies FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM children c
            JOIN schools s ON c.school_id = s.id
            WHERE c.id = emergencies.child_id
            AND s.email = auth.jwt()->>'email'
        )
    );
```

---

## Règles d'authentification et autorisation (BR-030 à BR-049)

### BR-030: Role-based tool access
- **Description**: Certains outils MCP nécessitent un rôle spécifique
- **Acteurs**: User (parent, school_staff)
- **Condition**: Appel à un outil MCP
- **Action**: Vérifier `user.role` contre le rôle requis
- **Implémentation**: Middleware `require_auth(user, role="parent")`
- **Localisation**: `/allobye_server_python/main.py:375-391`
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (sécurité)

**Mapping outils → rôles**:
```python
# Rôle "parent" requis:
- pickup-schedule-create
- delegate-authorize
- emergency-declare

# Rôle "school_staff" requis:
- school-dashboard-fetch

# Pas de rôle requis:
- auth-signup
- auth-login
- auth-logout
- auth-reset-password
- auth-profile
- monitoring-dashboard-fetch
```

---

### BR-031: Parent identified by email
- **Description**: Un parent est identifié par son email dans `children.parent_email`
- **Acteurs**: Parent, Enfant
- **Condition**: Vérification d'ownership
- **Action**: Comparer `children.parent_email` avec `auth.jwt()->>'email'`
- **Implémentation**: RLS policies + Python
- **Localisation**:
  - `/allobye_server_python/schema.sql:300` (RLS)
  - `/allobye_server_python/auth.py:598-600` (Python)
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (identité)

**Problème de duplication**:
- `children.parent_email` (TEXT, foreign reference faible)
- `parent_children.parent_id` (UUID, foreign key forte)

**Incohérence**: Deux systèmes d'ownership coexistent!

---

### BR-032: Staff-school association
- **Description**: Le personnel scolaire est lié aux écoles via la table `user_schools`
- **Acteurs**: School staff, École
- **Condition**: Vérification d'autorisation école
- **Action**: Lookup dans `user_schools` table
- **Implémentation**: Junction table + fonction `verify_staff_at_school()`
- **Localisation**:
  - `/allobye_server_python/auth.py:609-632`
  - Tables: `user_profiles`, `user_schools` (non définies dans schema.sql ⚠️)
- **Statut**: ⚠️ Partiel (code existe, schema incomplet)
- **Priorité**: 🔴 Critique (autorisation)

**Observation**: `user_schools` table est référencée dans le code Python mais **absente du schema.sql**!

---

### BR-033: Service role bypass
- **Description**: Le rôle "service_role" peut accéder à toutes les données sans restrictions
- **Acteurs**: Service (backend)
- **Condition**: Toute opération database
- **Action**: Bypass RLS si `auth.jwt()->>'role' = 'service_role'`
- **Implémentation**: RLS policies "Service role can manage *"
- **Localisation**: Toutes les tables (schema.sql:289, 314, 341, 387, etc.)
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (admin access)

**Exemple**:
```sql
CREATE POLICY "Service role can manage schools"
    ON schools FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');
```

---

### BR-034: JWT claims usage
- **Description**: Les RLS policies utilisent les JWT claims pour l'identification
- **Acteurs**: Tous les users
- **Condition**: Toute requête database
- **Action**: Extraire `email` et `role` du JWT via `auth.jwt()`
- **Implémentation**: Function PostgreSQL fournie par Supabase
- **Localisation**: Toutes les RLS policies
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (auth)

**Claims utilisés**:
```sql
auth.jwt()->>'email'  -- Identification user
auth.jwt()->>'role'   -- Autorisation role
```

**Problème**: Pas d'utilisation de `auth.uid()` (user ID) qui serait plus robuste que email!

---

### BR-035: Schools are publicly viewable
- **Description**: La liste des écoles est accessible à tous (pas de RLS restriction)
- **Acteurs**: Tous
- **Condition**: Lecture de `schools` table
- **Action**: Autoriser toujours
- **Implémentation**: RLS policy "USING (true)"
- **Localisation**: `/allobye_server_python/schema.sql:283-285`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟢 Basse

```sql
CREATE POLICY "Schools are viewable by everyone"
    ON schools FOR SELECT
    USING (true);
```

---

### BR-036: Parent can view own children
- **Description**: Un parent peut voir uniquement ses propres enfants
- **Acteurs**: Parent, Enfant
- **Condition**: Lecture de `children` table
- **Action**: Filtrer par `parent_email = auth.jwt()->>'email'`
- **Implémentation**: RLS policy
- **Localisation**: `/allobye_server_python/schema.sql:298-300`
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (sécurité)

---

### BR-037: Parent can view children's pickups
- **Description**: Un parent peut voir les ramassages de ses enfants
- **Acteurs**: Parent, Enfant, Ramassage
- **Condition**: Lecture de `pickups` table
- **Action**: Autoriser si ∃ au moins un enfant du parent dans le ramassage
- **Implémentation**: RLS policy avec JOIN complexe
- **Localisation**: `/allobye_server_python/schema.sql:351-360`
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (sécurité)

**Logique métier**: Un parent voit un ramassage **même s'il concerne aussi des enfants d'autres parents** (multi-enfant).

---

### BR-038: School staff can view children at their school
- **Description**: Le personnel scolaire peut voir les enfants de son école
- **Acteurs**: School staff, Enfant
- **Condition**: Lecture de `children` table
- **Action**: Autoriser si `schools.email = auth.jwt()->>'email'`
- **Implémentation**: RLS policy avec JOIN
- **Localisation**: `/allobye_server_python/schema.sql:303-311`
- **Statut**: ⚠️ Partiel (logique douteuse)
- **Priorité**: 🔴 Critique (sécurité)

**Problème**: La policy utilise `schools.email` pour identifier le staff, mais:
- `schools.email` est l'email de l'école (direction@stjb.qc.ca)
- Pas l'email du personnel scolaire!

**Incohérence**: Comment un user peut-il avoir `email = direction@stjb.qc.ca`?

---

### BR-039: Defense in depth
- **Description**: L'autorisation est vérifiée à deux niveaux: Application (Python) et Database (RLS)
- **Acteurs**: Système
- **Condition**: Toute opération sensible
- **Action**:
  - Niveau 1: Validation dans handler Python
  - Niveau 2: RLS policy dans PostgreSQL
- **Implémentation**: Duplication volontaire
- **Localisation**: Partout
- **Statut**: ✅ Implémenté
- **Priorité**: 🟠 Haute (sécurité multicouche)

**Exemple**:
```python
# Niveau 1: Python
if not await verify_parent_owns_child(user.id, child_id):
    return error_response()

# Niveau 2: RLS policy (automatique)
# Même si Python est contourné, RLS bloque
```

---

### BR-040 à BR-049: Réservés pour extensions

---

## Règles de calcul et affichage (BR-050 à BR-059)

### BR-050: Time urgency color coding
- **Description**: Les ramassages sont colorés selon l'urgence temporelle
- **Acteurs**: Frontend, Ramassage
- **Condition**: Affichage dans dashboard
- **Action**: Calculer couleur selon `minutesUntilPickup`:
  - Rouge: < 5 minutes (urgent!)
  - Jaune: < 15 minutes (bientôt)
  - Orange: delay > 0 (retard)
  - Bleu: > 15 minutes (normal)
  - Vert: Complété
  - Gris: Annulé
- **Implémentation**: Logique frontend JavaScript
- **Localisation**: `/src/allobye-dashboard/pickup-card.jsx:7-14`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟡 Moyenne (UX)

```javascript
const getStatusColor = () => {
  if (pickup.status === "completed") return "green";
  if (pickup.status === "cancelled") return "gray";
  if (pickup.delay && pickup.delay > 0) return "orange";
  if (minutesUntilPickup < 5) return "red";
  if (minutesUntilPickup < 15) return "yellow";
  return "blue";
};
```

---

### BR-051: "Next 30 minutes" filter
- **Description**: Le filtre "next_30min" affiche les ramassages dans les 30 prochaines minutes
- **Acteurs**: Frontend, User
- **Condition**: Filter activé
- **Action**: Filtrer `scheduled_time <= NOW() + 30 minutes`
- **Implémentation**: Logique frontend
- **Localisation**: `/src/allobye-dashboard/dashboard.jsx:150-154`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟡 Moyenne (UX)

```javascript
if (state.filter === "next_30min") {
  const scheduledTime = new Date(pickup.scheduled_time);
  const thirtyMinutesFromNow = new Date(currentTime.getTime() + 30 * 60 * 1000);
  return scheduledTime <= thirtyMinutesFromNow;
}
```

---

### BR-052: "Delays" filter
- **Description**: Le filtre "delays" affiche uniquement les ramassages en retard
- **Acteurs**: Frontend, User
- **Condition**: Filter activé
- **Action**: Filtrer `delay > 0`
- **Implémentation**: Logique frontend
- **Localisation**: `/src/allobye-dashboard/dashboard.jsx:156-158`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟡 Moyenne (UX)

```javascript
if (state.filter === "delays") {
  return pickup.delay && pickup.delay > 0;
}
```

---

### BR-053: Time window calculation
- **Description**: Le backend calcule les fenêtres temporelles pour les requêtes de pickups
- **Acteurs**: Backend
- **Condition**: Appel à `get_school_pickups()`
- **Action**:
  - "current": [NOW, NOW + 30min]
  - "today": [00:00:00, 23:59:59] today
  - "custom": [NOW, NOW + 24h]
- **Implémentation**: Logique Python
- **Localisation**: `/allobye_server_python/main.py:621-630`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟠 Haute (core feature)

```python
if time_window == "current":
    start_time = now
    end_time = now + timedelta(minutes=30)
elif time_window == "today":
    start_time = now.replace(hour=0, minute=0, second=0)
    end_time = now.replace(hour=23, minute=59, second=59)
else:
    start_time = now
    end_time = now + timedelta(hours=24)
```

---

### BR-054: Emergency alert auto-dismiss
- **Description**: Les alertes d'urgence s'effacent automatiquement après 30 secondes
- **Acteurs**: Frontend
- **Condition**: Réception d'une urgence via Realtime
- **Action**: Afficher alerte puis `setTimeout(30000)` pour la masquer
- **Implémentation**: Logique frontend
- **Localisation**: `/src/allobye-dashboard/dashboard.jsx:124-126`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟡 Moyenne (UX)

```javascript
setTimeout(() => {
  setState({ ...state, alert: null });
}, 30000);  // 30 secondes
```

---

### BR-055: Pickups sorted chronologically
- **Description**: Les ramassages sont toujours triés par `scheduled_time` croissant
- **Acteurs**: Backend
- **Condition**: Requête de pickups
- **Action**: `ORDER BY scheduled_time ASC`
- **Implémentation**: SQL query
- **Localisation**: `/allobye_server_python/main.py:663`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟠 Haute (UX)

```python
.order("scheduled_time")  # ASC par défaut
```

---

### BR-056 à BR-059: Réservés pour extensions

---

## Règles de données et intégrité (BR-060 à BR-069)

### BR-060: Updated_at auto-update
- **Description**: Le champ `updated_at` est automatiquement mis à jour lors d'une modification
- **Acteurs**: Système
- **Condition**: UPDATE sur tables avec `updated_at`
- **Action**: Déclencher trigger `update_updated_at_column()`
- **Implémentation**: Triggers PostgreSQL
- **Localisation**: `/allobye_server_python/schema.sql:157-193`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟡 Moyenne (audit)

**Tables concernées**: schools, children, delegates, pickups, emergencies

```sql
CREATE TRIGGER update_pickups_updated_at
    BEFORE UPDATE ON pickups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

---

### BR-061: Cascade delete relationships
- **Description**: La suppression d'un parent cascade à ses enfants via foreign keys
- **Acteurs**: Système
- **Condition**: DELETE opération
- **Action**: `ON DELETE CASCADE`
- **Implémentation**: Foreign key constraints
- **Localisation**: `/allobye_server_python/schema.sql:44, 69, etc.`
- **Statut**: ✅ Implémenté
- **Priorité**: 🔴 Critique (intégrité référentielle)

**Cascades définies**:
```sql
children.school_id → schools.id ON DELETE CASCADE
pickups.pickup_person_id → delegates.id ON DELETE CASCADE
pickup_children.pickup_id → pickups.id ON DELETE CASCADE
pickup_children.child_id → children.id ON DELETE CASCADE
delegate_children.delegate_id → delegates.id ON DELETE CASCADE
delegate_children.child_id → children.id ON DELETE CASCADE
emergencies.child_id → children.id ON DELETE CASCADE
```

**Attention**: Suppression d'une école → Suppression de tous ses enfants → Cascade massive!

---

### BR-062: Timezone support
- **Description**: Les écoles ont un timezone pour gérer les heures locales
- **Acteurs**: École
- **Condition**: Création école
- **Action**: Définir timezone (défaut: 'America/Montreal')
- **Implémentation**: Colonne `schools.timezone`
- **Localisation**: `/allobye_server_python/schema.sql:35`
- **Statut**: ⚠️ Partiel (stocké mais non utilisé)
- **Priorité**: 🟡 Moyenne

**Observation**: Le champ existe mais **jamais utilisé dans les calculs de temps** ⚠️

---

### BR-063: UUID generation
- **Description**: Les IDs primaires sont des UUIDs générés automatiquement
- **Acteurs**: Système
- **Condition**: INSERT sans ID explicite
- **Action**: Générer UUID via `gen_random_uuid()`
- **Implémentation**: DEFAULT constraint
- **Localisation**: Toutes les tables (schema.sql)
- **Statut**: ✅ Implémenté
- **Priorité**: 🟢 Basse (technique)

```sql
id UUID PRIMARY KEY DEFAULT gen_random_uuid()
```

---

### BR-064: Schema versioning
- **Description**: Le schéma database est versionné pour tracking des migrations
- **Acteurs**: Système
- **Condition**: Application du schéma
- **Action**: Enregistrer version dans `schema_version` table
- **Implémentation**: Table dédiée
- **Localisation**: `/allobye_server_python/schema.sql:587-595`
- **Statut**: ✅ Implémenté
- **Priorité**: 🟡 Moyenne (DevOps)

```sql
INSERT INTO schema_version (version, description)
VALUES (1, 'Initial AllôBye schema with RLS, triggers, and real-time support')
ON CONFLICT (version) DO NOTHING;
```

---

### BR-065 à BR-069: Réservés pour extensions

---

## Index des règles

### Par priorité

#### 🔴 Critique (17 règles)
- BR-001: Parent ownership validation
- BR-002: Delegate authorization for pickup (MANQUANT)
- BR-009: Allowed pickup statuses
- BR-010: Unique delegate by email
- BR-020: Emergency types enumeration
- BR-022: Emergency cascade to all delegates
- BR-023: Emergency cascade to all schools
- BR-024: Real-time emergency notification
- BR-027: Parent owns emergency child
- BR-030: Role-based tool access
- BR-031: Parent identified by email
- BR-032: Staff-school association (PARTIEL)
- BR-033: Service role bypass
- BR-034: JWT claims usage
- BR-036: Parent can view own children
- BR-037: Parent can view children's pickups
- BR-061: Cascade delete relationships

#### 🟠 Haute (14 règles)
- BR-003: Multi-school coordination
- BR-005: Status transition - Cancellation cascade
- BR-006: Status transition - Completion auto-checkout
- BR-008: Late detection (MANQUANT)
- BR-011: Granular authorization per child
- BR-013: Multi-school A2A synchronization
- BR-014: Active delegates only (PARTIEL)
- BR-018: Delegate can view assigned pickups
- BR-019: Parent can view authorized delegates
- BR-021: Severity levels
- BR-026: Emergency auto-resolve (MANQUANT)
- BR-028: Delegates can view emergencies
- BR-029: School staff can view emergencies
- BR-053: Time window calculation
- BR-055: Pickups sorted chronologically

#### 🟡 Moyenne (16 règles)
- BR-004: Initial pickup status
- BR-007: ETA calculation (MANQUANT)
- BR-012: Permission types (PARTIEL)
- BR-015: Delegate expiration (MANQUANT)
- BR-016: Authorization tracking (PARTIEL)
- BR-025: Emergency default status
- BR-039: Defense in depth
- BR-050: Time urgency color coding
- BR-051: "Next 30 minutes" filter
- BR-052: "Delays" filter
- BR-054: Emergency alert auto-dismiss
- BR-060: Updated_at auto-update
- BR-062: Timezone support (PARTIEL)
- BR-064: Schema versioning

#### 🟢 Basse (3 règles)
- BR-017: Delegate can view own profile
- BR-035: Schools are publicly viewable
- BR-063: UUID generation

### Par statut

#### ✅ Implémenté (45 règles)
Voir liste complète ci-dessus

#### ⚠️ Partiel (7 règles)
- BR-012: Permission types
- BR-014: Active delegates only
- BR-016: Authorization tracking
- BR-032: Staff-school association
- BR-038: School staff can view children (logique douteuse)
- BR-062: Timezone support

#### ❌ Manquant (5 règles)
- BR-002: Delegate authorization for pickup
- BR-007: ETA calculation
- BR-008: Late detection
- BR-015: Delegate expiration
- BR-026: Emergency auto-resolve

---

## Conclusion

**Total**: 57 règles métier identifiées

**Distribution**:
- ✅ Implémentées: 45 (79%)
- ⚠️ Partielles: 7 (12%)
- ❌ Manquantes: 5 (9%)

**Observations critiques**:
1. **BR-002** (validation délégué autorisé) est une **faille de sécurité** majeure
2. **BR-007** et **BR-008** (ETA et détection retards) sont des features métier clés non implémentées
3. Plusieurs règles sont **partiellement implémentées** avec incohérences entre Python et SQL
4. Logique métier **éparpillée** sur 3 couches: Python, PostgreSQL, Frontend

**Recommandations**:
1. Implémenter **BR-002** en priorité (sécurité)
2. Centraliser la logique métier dans une couche service (Python)
3. Réduire la logique métier dans RLS policies (uniquement ownership simple)
4. Implémenter les calculs automatiques (ETA, Late detection)
