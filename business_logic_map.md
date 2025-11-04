# Business Logic Map - AllôBye

**Date**: 2025-11-04
**Analyseur**: Extracteur de Logique Métier
**Codebase**: AllôBye - Système de coordination de ramassage scolaire

---

## Table des matières

1. [Vue d'ensemble](#vue-densemble)
2. [Domaines métier](#domaines-métier)
3. [Flux métier principaux](#flux-métier-principaux)
4. [Localisation de la logique](#localisation-de-la-logique)
5. [Règles par domaine](#règles-par-domaine)
6. [Interactions inter-domaines](#interactions-inter-domaines)

---

## Vue d'ensemble

AllôBye implémente un système de coordination de ramassage scolaire avec les caractéristiques métier suivantes:

### Acteurs métier
- **Parents**: Planifient les ramassages, autorisent les délégués, déclarent les urgences
- **Délégués**: Personnes autorisées à récupérer les enfants
- **Personnel scolaire**: Visualise et gère la file de ramassage
- **Enfants**: Sujets des ramassages (objets passifs)
- **Écoles**: Institutions où se déroulent les ramassages

### Capacités métier clés
1. **Coordination multi-enfant**: Un ramassage peut concerner plusieurs enfants
2. **Coordination multi-école**: Synchronisation via A2A (Agent-to-Agent)
3. **Gestion des délégations**: Autorisations granulaires par enfant
4. **Gestion des urgences**: Cascade de notifications
5. **Calcul d'ETA et détection de retards**: Alertes en temps réel

---

## Domaines métier

```
┌─────────────────────────────────────────────────────────────────────┐
│                         DOMAINES MÉTIER                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌───────────────────┐      ┌───────────────────┐                 │
│  │   RAMASSAGES      │◄────►│   AUTORISATIONS   │                 │
│  │   (Pickups)       │      │   (Delegates)     │                 │
│  │                   │      │                   │                 │
│  │ - Planification   │      │ - Permissions     │                 │
│  │ - États           │      │ - Scopes          │                 │
│  │ - ETA/Retards     │      │ - Multi-école     │                 │
│  └─────────┬─────────┘      └─────────┬─────────┘                 │
│            │                          │                           │
│            │                          │                           │
│            ▼                          ▼                           │
│  ┌───────────────────┐      ┌───────────────────┐                 │
│  │   URGENCES        │      │   AUTHENTIFICATION│                 │
│  │   (Emergencies)   │      │   (Auth)          │                 │
│  │                   │      │                   │                 │
│  │ - Types           │      │ - Rôles           │                 │
│  │ - Sévérité        │      │ - JWT             │                 │
│  │ - Cascade         │      │ - RLS             │                 │
│  └─────────┬─────────┘      └───────────────────┘                 │
│            │                                                       │
│            ▼                                                       │
│  ┌───────────────────┐                                            │
│  │   ÉCOLES          │                                            │
│  │   (Schools)       │                                            │
│  │                   │                                            │
│  │ - Enfants         │                                            │
│  │ - Personnel       │                                            │
│  │ - Coordination    │                                            │
│  └───────────────────┘                                            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Flux métier principaux

### Flux 1: Planification de ramassage (Parent → System)

```
┌──────────────────────────────────────────────────────────────────────┐
│ FLUX: Planification de ramassage                                    │
└──────────────────────────────────────────────────────────────────────┘

1. Parent authentifié appelle pickup-schedule-create
   │
   ├─► Validation métier (main.py:1023-1108)
   │   ├─ Auth: User must be "parent"
   │   ├─ Ownership: Parent owns ALL children
   │   └─ Delegate: pickup_person_id exists and authorized
   │
   ├─► Détection multi-école (main.py:1065-1074)
   │   └─ get_schools_for_children() → Liste d'écoles uniques
   │
   ├─► DÉCISION MÉTIER:
   │   │
   │   ├─ SI multiple écoles:
   │   │  └─► coordinate_cross_school_pickup() (main.py:475-496)
   │   │      ├─ Create pickup request
   │   │      ├─ A2A simulation: broadcast to each school
   │   │      └─ Return: schools_affected + a2a_messages
   │   │
   │   └─ SI école unique:
   │      └─► create_pickup_request() (main.py:426-472)
   │          ├─ Insert pickup record (status: "confirmed")
   │          ├─ Link children via pickup_children table
   │          └─ Return: pickup record
   │
   └─► Retour au parent: pickup_id + confirmation
```

**Règles métier appliquées**:
- BR-001: Un parent ne peut planifier que pour SES enfants
- BR-002: Le délégué doit être autorisé pour TOUS les enfants du ramassage
- BR-003: Les ramassages multi-écoles nécessitent coordination A2A
- BR-004: Status initial = "confirmed" (pas "pending")

---

### Flux 2: Autorisation de délégué (Parent → System → Multi-écoles)

```
┌──────────────────────────────────────────────────────────────────────┐
│ FLUX: Autorisation de délégué                                       │
└──────────────────────────────────────────────────────────────────────┘

1. Parent authentifié appelle delegate-authorize
   │
   ├─► Validation métier (main.py:1111-1178)
   │   ├─ Auth: User must be "parent"
   │   └─ Ownership: Parent owns ALL children
   │
   ├─► Inférence des écoles (main.py:1153)
   │   └─ get_schools_for_children(child_ids)
   │       └─ RÈGLE: Schools inférées des enfants si non fournies
   │
   ├─► Broadcast via A2A (main.py:499-541)
   │   └─ broadcast_delegate_authorization()
   │       ├─ UPSERT delegate (by email)
   │       │  └─ RÈGLE: Un délégué = une seule ligne (unique email)
   │       │
   │       ├─ Link delegate → children (junction table)
   │       │  └─ Permissions: ["pickup", "emergency_contact", "medical_decisions"]
   │       │
   │       └─ Simulate A2A sync to all schools
   │           └─ Return: sync_status + messages per school
   │
   └─► Retour: delegate_id + authorized_schools + sync status
```

**Règles métier appliquées**:
- BR-010: Un délégué est identifié par email (unique constraint)
- BR-011: Autorisations granulaires par enfant (pas global)
- BR-012: Permissions multiples: pickup, emergency_contact, medical_decisions
- BR-013: Synchronisation A2A avec toutes les écoles affectées
- BR-014: Upsert sémantique: UPDATE si existe, INSERT sinon

---

### Flux 3: Déclaration d'urgence (Parent → Cascade → Délégués + Écoles)

```
┌──────────────────────────────────────────────────────────────────────┐
│ FLUX: Déclaration d'urgence                                         │
└──────────────────────────────────────────────────────────────────────┘

1. Parent authentifié appelle emergency-declare
   │
   ├─► Validation métier (main.py:1181-1249)
   │   ├─ Auth: User must be "parent"
   │   └─ Ownership: Parent owns child
   │
   ├─► Récupération des acteurs (main.py:1222-1223)
   │   ├─ get_authorized_delegates(child_id)
   │   │  └─ RÈGLE: Seuls les délégués ACTIFS (is_active = TRUE)
   │   │
   │   └─ get_schools_for_children([child_id])
   │      └─ RÈGLE: Écoles dérivées de l'enfant
   │
   ├─► Broadcast d'urgence (main.py:565-609)
   │   └─ broadcast_emergency()
   │       ├─ Create emergency record
   │       │  ├─ Types: late, illness, cancel, injury, other
   │       │  ├─ Severity: low, medium, high, critical
   │       │  └─ Status: resolved = FALSE
   │       │
   │       ├─ TRIGGER (schema.sql:196-231)
   │       │  └─ notify_emergency() via pg_notify
   │       │      ├─ Channel: 'emergency_alert'
   │       │      └─ Payload: emergency_id, child, school, type, severity
   │       │
   │       └─ A2A cascade (simulation)
   │           ├─ Notify ALL delegates (count)
   │           └─ Notify ALL schools (count)
   │
   └─► Retour: emergency_id + notified_count + cascade_trace
```

**Règles métier appliquées**:
- BR-020: Types d'urgence limités: late, illness, cancel, injury, other
- BR-021: 4 niveaux de sévérité: low, medium, high, critical
- BR-022: Cascade automatique à TOUS les délégués autorisés
- BR-023: Notification temps réel via PostgreSQL NOTIFY
- BR-024: Urgences non résolues par défaut (resolved = FALSE)

---

### Flux 4: Affichage du tableau de bord école (School Staff → System)

```
┌──────────────────────────────────────────────────────────────────────┐
│ FLUX: Dashboard école                                               │
└──────────────────────────────────────────────────────────────────────┘

1. Personnel scolaire appelle school-dashboard-fetch
   │
   ├─► Validation métier (main.py:1252-1328)
   │   ├─ Auth: User must be "school_staff"
   │   └─ Authorization: verify_staff_at_school(user_id, school_id)
   │       └─ RÈGLE: Staff doit être lié à cette école
   │
   ├─► Calcul fenêtre temporelle (main.py:612-630)
   │   └─ get_school_pickups(school_id, date, time_window)
   │       │
   │       ├─ time_window = "current":
   │       │  └─ [NOW, NOW + 30 minutes]
   │       │
   │       ├─ time_window = "today":
   │       │  └─ [00:00:00, 23:59:59] today
   │       │
   │       └─ time_window = "custom":
   │          └─ [NOW, NOW + 24 hours]
   │
   ├─► Récupération données (main.py:656-663)
   │   └─ SELECT pickups + children + delegates
   │       ├─ JOIN pickup_children
   │       ├─ JOIN children (filter: school_id)
   │       ├─ JOIN delegates (pickup_person)
   │       └─ ORDER BY scheduled_time ASC
   │
   └─► Frontend: Real-time updates (dashboard.jsx:56-144)
       │
       ├─► Supabase Realtime subscription
       │   ├─ Table: pickups (filter: school_id)
       │   ├─ Events: INSERT, UPDATE, DELETE
       │   └─ RÈGLE: Auto-merge avec données existantes
       │
       ├─► Emergency subscription
       │   ├─ Table: emergencies (all schools)
       │   └─ Auto-display alert for 30 seconds
       │
       └─► Filtrage client (dashboard.jsx:147-161)
           ├─ "all": Tous les ramassages
           ├─ "next_30min": scheduled_time <= NOW + 30min
           └─ "delays": delay > 0
```

**Règles métier appliquées**:
- BR-030: Personnel scolaire voit SEULEMENT son école
- BR-031: Fenêtre "current" = 30 minutes fixes
- BR-032: Tri chronologique par scheduled_time
- BR-033: Real-time via WebSocket (bypass MCP)
- BR-034: Alertes urgences auto-dismiss après 30 secondes

---

## Localisation de la logique

### Logique métier dans Python (main.py)

| Fonction | Ligne | Règle métier |
|----------|-------|--------------|
| `get_schools_for_children()` | 399-423 | Multi-école: extraction d'écoles uniques |
| `create_pickup_request()` | 426-472 | Création ramassage + liaison enfants |
| `coordinate_cross_school_pickup()` | 475-496 | Coordination A2A multi-école |
| `broadcast_delegate_authorization()` | 499-541 | Synchronisation délégué multi-école |
| `get_authorized_delegates()` | 544-562 | Récupération délégués actifs |
| `broadcast_emergency()` | 565-609 | Cascade urgence (délégués + écoles) |
| `get_school_pickups()` | 612-668 | File de ramassage avec fenêtres temporelles |
| `_handle_pickup_schedule_create()` | 1023-1108 | Validation ownership + orchestration |
| `_handle_delegate_authorize()` | 1111-1178 | Validation ownership + broadcast |
| `_handle_emergency_declare()` | 1181-1249 | Validation + cascade urgence |
| `_handle_school_dashboard_fetch()` | 1252-1328 | Validation staff + récupération données |

**Observation**: Logique concentrée dans handlers et helpers. **Pas de séparation service layer**.

---

### Logique métier dans auth.py

| Fonction | Ligne | Règle métier |
|----------|-------|--------------|
| `signup_user()` | 115-210 | Création compte + profil + liens écoles |
| `login_user()` | 213-292 | Auth + fetch profil complet |
| `validate_session()` | 386-429 | Validation JWT + fetch profil |
| `get_user_profile()` | 432-503 | Agrégation: user + schools + children |
| `verify_parent_owns_child()` | 583-606 | **AUTORISATION**: parent-child ownership |
| `verify_staff_at_school()` | 609-632 | **AUTORISATION**: staff-school relationship |

**Observation**: **Mélange authentication + authorization**. Les fonctions `verify_*` sont de la logique métier (authorization), pas de l'authentication.

---

### Logique métier dans PostgreSQL (schema.sql)

#### Contraintes métier (CHECK)

| Table | Colonne | Contrainte | Ligne |
|-------|---------|------------|-------|
| `pickups` | `status` | `IN ('pending', 'confirmed', 'in_progress', 'completed', 'cancelled', 'late')` | 72 |
| `emergencies` | `emergency_type` | `IN ('late', 'illness', 'cancel', 'injury', 'other')` | 106 |
| `emergencies` | `severity` | `IN ('low', 'medium', 'high', 'critical')` | 108 |

**Règles métier**: Énumérations strictes. Toute valeur hors liste est **rejetée par la DB**.

---

#### Triggers métier

| Trigger | Function | Ligne | Règle métier |
|---------|----------|-------|--------------|
| `emergency_notification` | `notify_emergency()` | 228-231 | Notification temps réel via pg_notify |
| `pickup_status_cascade` | `cascade_pickup_status()` | 259-263 | Cascade automatique de status changes |

**Détail cascade_pickup_status()** (schema.sql:234-256):
```sql
IF NEW.status = 'cancelled' AND OLD.status != 'cancelled' THEN
    -- RÈGLE: Annulation ramassage → Annulation checkout enfants
    UPDATE pickup_children
    SET checked_out = FALSE,
        checked_out_at = NULL,
        checked_out_by = NULL
    WHERE pickup_id = NEW.id;
END IF;

IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
    -- RÈGLE: Completion ramassage → Auto-checkout enfants non sortis
    UPDATE pickup_children
    SET checked_out = TRUE,
        checked_out_at = COALESCE(checked_out_at, NOW())
    WHERE pickup_id = NEW.id AND checked_out = FALSE;
END IF;
```

**Règles métier**:
- BR-040: Annulation ramassage → Reset de tous les checkouts
- BR-041: Completion ramassage → Auto-checkout des enfants restants

---

#### RLS Policies (Row-Level Security)

**21 politiques RLS** implémentant la logique d'autorisation:

##### Règles pour Parents

| Politique | Table | Ligne | Règle métier |
|-----------|-------|-------|--------------|
| Parents can view their own children | `children` | 298-300 | Parent voit SES enfants (par email) |
| Parents can view their children's pickups | `pickups` | 351-360 | Parent voit ramassages de SES enfants |
| Parents can view authorized delegates | `delegates` | 329-338 | Parent voit délégués autorisés pour SES enfants |
| Parents can view emergencies for their children | `emergencies` | 448-456 | Parent voit urgences de SES enfants |

**Logique complexe** (exemple):
```sql
-- RLS policy: Parents can view their children's pickups
USING (
    EXISTS (
        SELECT 1 FROM pickup_children pc
        JOIN children c ON pc.child_id = c.id
        WHERE pc.pickup_id = pickups.id
        AND c.parent_email = auth.jwt()->>'email'  -- JWT claim
    )
);
```

**Observation**: **Logique métier dans la DB**. Le parent doit avoir au moins UN enfant dans le ramassage pour le voir.

---

##### Règles pour Délégués

| Politique | Table | Ligne | Règle métier |
|-----------|-------|-------|--------------|
| Delegates can view their own profile | `delegates` | 324-326 | Délégué voit SON profil |
| Delegates can view their assigned pickups | `pickups` | 363-371 | Délégué voit ramassages où il est pickup_person |
| Delegates can view emergencies for authorized children | `emergencies` | 459-469 | Délégué voit urgences des enfants qu'il peut récupérer |

**Règle BR-042**: Un délégué ne voit que les ramassages où **il est la personne de ramassage** (pickup_person_id = delegate.id).

---

##### Règles pour School Staff

| Politique | Table | Ligne | Règle métier |
|-----------|-------|-------|--------------|
| School staff can view children at their school | `children` | 303-311 | Staff voit enfants de SON école |
| School staff can view school pickups | `pickups` | 374-384 | Staff voit ramassages de SON école |
| School staff can view emergencies at their school | `emergencies` | 472-481 | Staff voit urgences de SON école |

**Observation**: Toutes les policies utilisent `schools.email = auth.jwt()->>'email'` pour valider l'appartenance.

---

### Logique métier dans Frontend (dashboard.jsx)

| Logique | Ligne | Règle métier |
|---------|-------|--------------|
| Calcul urgence temporelle | pickup-card.jsx:7-14 | < 5min = rouge, < 15min = jaune, < 60min = bleu |
| Filtre "next_30min" | dashboard.jsx:150-154 | scheduledTime <= NOW + 30min |
| Filtre "delays" | dashboard.jsx:156-158 | delay > 0 |
| Auto-dismiss alert | dashboard.jsx:124-126 | 30 secondes timeout |
| Real-time merge | dashboard.jsx:88-94 | Fusion pickups MCP + Realtime |

**Règle BR-050**: Couleur urgence calculée côté client:
```javascript
if (minutesUntilPickup < 5) return "red";    // Urgent!
if (minutesUntilPickup < 15) return "yellow"; // Bientôt
```

**Observation**: **Logique métier dans UI** (calculs de couleur, filtrage).

---

## Règles par domaine

### Domaine: Ramassages (Pickups)

#### BR-001: Ownership validation
- **Localisation**: main.py:1052-1062
- **Règle**: Un parent ne peut planifier un ramassage que pour les enfants qu'il possède
- **Implémentation**: Appel `verify_parent_owns_child()` pour CHAQUE enfant
- **Sanction**: Error response si un seul enfant n'appartient pas au parent

#### BR-002: Delegate authorization
- **Localisation**: Implicite (non validé actuellement)
- **Règle**: Le pickup_person_id doit être un délégué autorisé pour TOUS les enfants
- **État**: **NON IMPLÉMENTÉ** ⚠️
- **Impact**: Un parent peut assigner un délégué non autorisé

#### BR-003: Multi-school coordination
- **Localisation**: main.py:1068-1081
- **Règle**: Si enfants de >1 école → appel `coordinate_cross_school_pickup()`
- **Implémentation**: Simulation A2A (pas de vrai bus)
- **Retour**: `schools_affected` + `a2a_messages`

#### BR-004: Initial status
- **Localisation**: main.py:456
- **Règle**: Tout nouveau ramassage est créé avec status = "confirmed"
- **Observation**: Pas de status "pending" initial (contrairement au seed data)

#### BR-005: Status transitions
- **Localisation**: schema.sql:234-256 (trigger)
- **Règles**:
  - `cancelled` → Tous les checkouts remis à FALSE
  - `completed` → Tous les enfants non checkout passent à TRUE
- **Implémentation**: Trigger automatique (invisible au code Python)

#### BR-006: ETA calculation
- **Localisation**: Non implémenté
- **État**: Champ `eta_minutes` existe mais **jamais calculé** ⚠️
- **Usage**: Frontend affiche si présent, mais source inconnue

#### BR-007: Late detection
- **Localisation**:
  - DB: Champ `status = 'late'` (manuelle)
  - DB: Champ `delay_minutes` (manuelle)
  - Frontend: pickup-card.jsx:10 (affichage)
- **Observation**: **Pas de détection automatique** ⚠️

---

### Domaine: Autorisations (Delegates)

#### BR-010: Unique delegate
- **Localisation**: schema.sql:57 + main.py:525
- **Règle**: Un délégué = un email unique
- **Implémentation**:
  - DB: `UNIQUE NOT NULL` constraint
  - Python: `upsert(on_conflict="email")`
- **Comportement**: UPDATE si existe, INSERT sinon

#### BR-011: Granular authorization
- **Localisation**: Junction table `delegate_children`
- **Règle**: Autorisations par enfant (pas globale)
- **Exemple**: Délégué A peut récupérer enfant X mais pas enfant Y

#### BR-012: Permission types
- **Localisation**: schema.sql:60 (delegates.permissions)
- **Types**: `pickup`, `emergency_contact`, `medical_decisions`
- **Type**: ARRAY (multiple permissions par délégué)
- **Validation**: **Aucune** ⚠️ (n'importe quelle string acceptée)

#### BR-013: A2A synchronization
- **Localisation**: main.py:499-541
- **Règle**: Autorisation diffusée à TOUTES les écoles des enfants
- **Implémentation**: Simulation (messages par école)
- **État**: Pas de vrai bus A2A

#### BR-014: Expiration support
- **Localisation**: schema.sql:97 (`expires_at`)
- **État**: Champ existe mais **jamais utilisé** ⚠️
- **Impact**: Pas de révocation automatique d'autorisations expirées

---

### Domaine: Urgences (Emergencies)

#### BR-020: Emergency types
- **Localisation**: schema.sql:106
- **Types autorisés**: `late`, `illness`, `cancel`, `injury`, `other`
- **Validation**: CHECK constraint (rejet DB si invalide)

#### BR-021: Severity levels
- **Localisation**: schema.sql:108
- **Niveaux**: `low`, `medium`, `high`, `critical`
- **Défaut**: `medium` (si non spécifié)

#### BR-022: Cascade notification
- **Localisation**: main.py:565-609
- **Règle**: Notification automatique à:
  - TOUS les délégués autorisés pour l'enfant
  - TOUTES les écoles de l'enfant
- **Implémentation**: Simulation A2A (trace retournée)

#### BR-023: Real-time notification
- **Localisation**: schema.sql:196-231 (trigger)
- **Mécanisme**: PostgreSQL `pg_notify`
- **Channel**: `emergency_alert`
- **Payload**: JSON avec emergency_id, child_id, school_id, type, severity, context

#### BR-024: Auto-resolve
- **Localisation**: Aucune
- **État**: **NON IMPLÉMENTÉ** ⚠️
- **Impact**: Urgences restent `resolved = FALSE` indéfiniment

---

### Domaine: Authentification/Autorisation

#### BR-030: Role-based access
- **Localisation**: main.py:375-391 + auth.py
- **Rôles**: `parent`, `school_staff`, `service_role`
- **Validation**: Middleware `require_auth(user, role="parent")`

#### BR-031: Parent ownership
- **Localisation**: auth.py:583-606
- **Règle**: Parent identifié par email dans `children.parent_email`
- **Table**: Junction `parent_children` (parent_id ↔ child_id)
- **Observation**: **Duplication** email vs ID ⚠️

#### BR-032: Staff-school association
- **Localisation**: auth.py:609-632
- **Règle**: Personnel lié via table `user_schools`
- **Validation**: Lookup dans junction table

#### BR-033: RLS enforcement
- **Localisation**: schema.sql:267-486 (21 policies)
- **Principe**: Defense in depth (JWT + RLS)
- **Observation**: **Logique métier complexe dans DB** ⚠️

#### BR-034: JWT claims
- **Localisation**: Toutes les RLS policies
- **Claims utilisés**:
  - `auth.jwt()->>'email'`: Identification utilisateur
  - `auth.jwt()->>'role'`: Rôle (service_role)
- **Observation**: `email` claim mais pas `user_id` ⚠️

---

## Interactions inter-domaines

### Interaction 1: Ramassage multi-enfant → Multi-école

```
Input: child_ids = ["child_A", "child_B"]
  │
  ├─► get_schools_for_children()
  │   └─ child_A → school_1
  │   └─ child_B → school_2
  │
  ├─► DÉCISION: len(schools) > 1
  │   └─ TRUE → coordinate_cross_school_pickup()
  │
  └─► A2A: Broadcast to [school_1, school_2]
```

**Règle métier**: La détection multi-école est **automatique** basée sur les enfants.

---

### Interaction 2: Délégué autorisé → Ramassage permis

```
Delegate D autorisé pour child_X (via delegate_children)
  │
  ├─► Parent planifie ramassage avec pickup_person_id = D
  │
  ├─► PROBLÈME: Pas de validation ⚠️
  │   └─ Code devrait vérifier: D ∈ authorized_delegates(child_X)
  │   └─ État actuel: N'importe quel delegate_id accepté
  │
  └─► RLS Policy (lecture):
      └─ Delegate D peut voir ce ramassage (pickup_person_id = D)
```

**Incohérence**: Validation manquante en écriture mais appliquée en lecture.

---

### Interaction 3: Urgence → Cascade multi-acteurs

```
Parent déclare urgence pour child_X
  │
  ├─► get_authorized_delegates(child_X)
  │   └─ Délégués: [D1, D2, D3] (is_active = TRUE)
  │
  ├─► get_schools_for_children([child_X])
  │   └─ Écoles: [school_1]
  │
  ├─► broadcast_emergency()
  │   ├─ INSERT into emergencies (resolved = FALSE)
  │   │
  │   ├─► TRIGGER notify_emergency()
  │   │   └─ pg_notify('emergency_alert', {...})
  │   │
  │   └─ A2A cascade (simulation)
  │       ├─ Notify delegates: 3
  │       └─ Notify schools: 1
  │
  └─► Frontend: Supabase subscription reçoit event
      └─ Display alert for 30 seconds
```

**Règle métier**: La cascade est **automatique et complète** (tous les acteurs).

---

### Interaction 4: RLS Policy → Application logic

```
User (parent) essaie de lire pickup_X
  │
  ├─► RLS Policy évaluation (database)
  │   └─ EXISTS (
  │       SELECT 1 FROM pickup_children pc
  │       JOIN children c ON pc.child_id = c.id
  │       WHERE pc.pickup_id = pickup_X
  │       AND c.parent_email = user.email
  │     )
  │
  ├─► SI TRUE: Row retournée
  │   └─ Application reçoit les données
  │
  └─► SI FALSE: Row filtrée
      └─ Application reçoit tableau vide (pas d'erreur)
```

**Observation**: **Validation silencieuse**. L'application ne sait pas si:
- Pickup n'existe pas
- Pickup existe mais user non autorisé

---

## Résumé

### Points forts de la logique métier

1. ✅ **Multi-enfant, multi-école**: Coordination automatique
2. ✅ **Cascade urgences**: Notification complète et automatique
3. ✅ **RLS Defense in depth**: Sécurité à plusieurs niveaux
4. ✅ **Real-time**: pg_notify + Supabase subscriptions

### Points faibles identifiés

1. ⚠️ **Pas de validation delegate authorization** lors de la création de ramassage
2. ⚠️ **ETA calculation non implémentée** (champ existe mais vide)
3. ⚠️ **Late detection manuelle** (pas de calcul automatique)
4. ⚠️ **Emergency auto-resolve manquant** (urgences jamais marquées resolved)
5. ⚠️ **Delegate expiration non utilisée** (expires_at ignoré)
6. ⚠️ **Logique métier éparpillée**: Python + SQL + Frontend
7. ⚠️ **Duplication authorization**: Vérifications en Python ET RLS
8. ⚠️ **Permissions non validées**: ARRAY accepte n'importe quelle string

---

**Conclusion**: AllôBye implémente une logique métier **riche et complexe**, mais avec **incohérences et lacunes**. La séparation entre infrastructure et métier est **floue**, surtout au niveau des RLS policies et des triggers.
