# Complexity Report - AllôBye

**Date**: 2025-11-04
**Auditeur**: Auditeur de Complexité
**Codebase**: AllôBye - Système de coordination de ramassage scolaire

---

## Executive Summary

### Métriques Globales

| Métrique | Valeur | Status |
|----------|--------|--------|
| **Total Lines of Code** | 4,373 | ✓ |
| **Total Files Analyzed** | 7 | ✓ |
| **Total Functions** | 77+ | ✓ |
| **Hotspots Identified** | 15 | ⚠️ |
| **Functions > 50 lines** | 12 | ⚠️ |
| **Functions with Complexity > 10** | 8 | ⚠️ |

### Distribution par Langage

| Language | Files | Lines | Avg Lines/File | Complexity Score |
|----------|-------|-------|----------------|------------------|
| Python | 3 | 2,967 | 989 | High |
| JavaScript/JSX | 3 | 811 | 270 | Medium |
| SQL | 1 | 595 | 595 | Medium-High |

### Verdict Global

**Niveau de Complexité: MEDIUM-HIGH ⚠️**

Le codebase présente des sections de complexité élevée qui nécessitent une attention particulière. Les fichiers Python `main.py` et `auth.py` contiennent plusieurs fonctions dépassant les seuils recommandés pour la maintenabilité.

---

## Analyse Détaillée par Fichier

### 1. Python: main.py

**Chemin**: `/home/user/openai-apps-sdk-examples/allobye_server_python/main.py`

#### Métriques Globales
- **Total Lines**: 1,582
- **Functions/Classes**: 41
- **Avg Function Size**: ~39 lignes
- **Decision Points (if/for/while/except)**: 135
- **Estimated Cyclomatic Complexity**: ~HIGH

#### Analyse par Fonction

##### Fonctions CRITIQUES (Complexity > 10)

| Function | Lines | Start Line | Complexity | Issues |
|----------|-------|------------|------------|--------|
| `_handle_pickup_schedule_create` | 85 | 1023 | 15 | Trop longue, validation multiple, boucles |
| `_handle_delegate_authorize` | 67 | 1111 | 12 | Validation complexe, logique multi-étapes |
| `_handle_emergency_declare` | 68 | 1181 | 11 | Cascade de vérifications |
| `_handle_school_dashboard_fetch` | 76 | 1252 | 13 | Logique widget complexe, multiple checks |
| `_call_tool_request_monitored` | 57 | 1392 | 10 | Try/except imbriqués, metrics tracking |
| `get_school_pickups` | 56 | 612 | 11 | Logique temporelle complexe |

##### Fonctions MOYENNES (Complexity 5-10)

| Function | Lines | Start Line | Complexity | Notes |
|----------|-------|------------|------------|-------|
| `create_pickup_request` | 44 | 426 | 8 | Gestion DB avec fallback mock |
| `broadcast_delegate_authorization` | 37 | 499 | 7 | Logique de synchronisation |
| `broadcast_emergency` | 38 | 565 | 7 | A2A cascade simulation |
| `_handle_auth_signup` | 40 | 844 | 8 | Validation et gestion d'erreurs |
| `_handle_auth_login` | 42 | 887 | 7 | Authentification multi-étapes |
| `_handle_monitoring_dashboard_fetch` | 53 | 1331 | 6 | Agrégation de métriques |

##### Fonctions SIMPLES (Complexity < 5)

- `get_supabase()` - 21 lignes, CC: 3
- `require_auth()` - 13 lignes, CC: 3
- `get_current_user()` - 12 lignes, CC: 2
- `_load_widget_html()` - 23 lignes, CC: 3
- `_tool_meta()` - 20 lignes, CC: 2
- Multiple handlers simples (~10-15 lignes each)

#### Problèmes Identifiés

1. **Fonctions trop longues**: 6 fonctions > 50 lignes
2. **Complexité cyclomatique élevée**: Plusieurs fonctions > 10
3. **Duplication**: Pattern try/except répété dans tous les handlers
4. **Nesting profond**: Jusqu'à 4-5 niveaux dans certains handlers
5. **God function**: `_call_tool_request_monitored` orchestre trop de logique

#### Recommandations

- ✅ Extraire la logique de validation dans des fonctions dédiées
- ✅ Créer des decorators pour DRY (try/except, authentication)
- ✅ Refactoriser les handlers complexes en sous-fonctions
- ✅ Utiliser un pattern Chain of Responsibility pour les validations

---

### 2. Python: auth.py

**Chemin**: `/home/user/openai-apps-sdk-examples/allobye_server_python/auth.py`

#### Métriques Globales
- **Total Lines**: 632
- **Functions/Classes**: 19
- **Avg Function Size**: ~33 lignes
- **Decision Points**: 91
- **Estimated Cyclomatic Complexity**: MEDIUM-HIGH

#### Analyse par Fonction

##### Fonctions CRITIQUES (Complexity > 10)

| Function | Lines | Start Line | Complexity | Issues |
|----------|-------|------------|------------|--------|
| `signup_user` | 96 | 115 | 14 | Très longue, multiples branches d'erreur |
| `login_user` | 80 | 213 | 12 | Authentification complexe, gestion d'erreurs |
| `get_user_profile` | 71 | 432 | 11 | Requêtes DB conditionnelles multiples |

##### Fonctions MOYENNES (Complexity 5-10)

| Function | Lines | Start Line | Complexity | Notes |
|----------|-------|------------|------------|-------|
| `validate_session` | 30 | 386 | 8 | Validation JWT avec fallback |
| `update_user_profile` | 26 | 506 | 6 | UPDATE avec logique conditionnelle |
| `verify_email_token` | 22 | 353 | 5 | Vérification OTP |

##### Fonctions SIMPLES

- `get_supabase_client()` - 14 lignes, CC: 2
- `get_supabase_admin()` - 14 lignes, CC: 2
- `logout_user()` - 14 lignes, CC: 2
- `reset_password_request()` - 18 lignes, CC: 2
- `verify_parent_owns_child()` - 14 lignes, CC: 2
- `verify_staff_at_school()` - 14 lignes, CC: 2

#### Problèmes Identifiés

1. **Fonctions auth trop longues**: signup_user (96 lignes!) et login_user (80 lignes)
2. **Multiple exit points**: Chaque fonction a 3-5 return statements
3. **Exception handling verbose**: Try/except répété partout
4. **Mock data inline**: Logique de fallback mélangée avec business logic

#### Recommandations

- ✅ Extraire la logique mock dans un module séparé
- ✅ Créer une classe AuthService pour encapsuler la logique
- ✅ Utiliser des Result types au lieu de raise/catch
- ✅ Refactoriser signup_user en 3-4 fonctions plus petites

---

### 3. Python: monitoring.py

**Chemin**: `/home/user/openai-apps-sdk-examples/allobye_server_python/monitoring.py`

#### Métriques Globales
- **Total Lines**: 753
- **Functions/Classes**: 17 (+ 5 classes)
- **Avg Function Size**: ~44 lignes
- **Decision Points**: 57
- **Estimated Cyclomatic Complexity**: MEDIUM

#### Analyse par Fonction/Classe

##### Fonctions COMPLEXES

| Function/Method | Lines | Start Line | Complexity | Issues |
|-----------------|-------|------------|------------|--------|
| `monitor_tool_call` (decorator) | 53 | 565 | 12 | Wrapper async complexe, metrics tracking |
| `export_prometheus` | 56 | 388 | 8 | Très longue mais répétitive |
| `record_tool_call` | 41 | 222 | 9 | Logique conditionnelle, alerting |
| `get_dashboard_data` | 33 | 446 | 6 | Agrégation de données multiples |

##### Classes

| Class | Methods | Lines | Complexity | Notes |
|-------|---------|-------|------------|-------|
| `StructuredLogger` | 7 | 58 | Medium | Bien structurée |
| `MetricsCollector` | 14 | 270 | High | Beaucoup de responsabilités |
| `RequestTracer` | 4 | 56 | Low | Simple, efficace |
| `MonitoringMiddleware` | 2 | 95 | Medium | Context managers bien utilisés |

#### Problèmes Identifiés

1. **MetricsCollector God Class**: 14 méthodes, trop de responsabilités
2. **Duplication**: Méthodes logger très similaires (debug/info/warning/error)
3. **Prometheus export**: Fonction longue et répétitive
4. **Mutable global state**: Variables globales _logger, _metrics, etc.

#### Recommandations

- ✅ Diviser MetricsCollector en ToolMetricsCollector et DBMetricsCollector
- ✅ Utiliser un logger Python standard avec custom formatter
- ✅ Générer export_prometheus via templates
- ✅ Utiliser dependency injection au lieu de globals

---

### 4. React: dashboard.jsx

**Chemin**: `/home/user/openai-apps-sdk-examples/src/allobye-dashboard/dashboard.jsx`

#### Métriques Globales
- **Total Lines**: 248
- **Components**: 1 (Dashboard)
- **Hooks Used**: 3 (useEffect, useState, custom hooks)
- **Decision Points**: 11
- **Estimated Cyclomatic Complexity**: HIGH

#### Analyse du Composant

##### Complexité du Composant Dashboard

| Aspect | Métrique | Status |
|--------|----------|--------|
| **Total Lines** | 248 | ⚠️ Trop long |
| **useEffect Hooks** | 4 | ⚠️ Trop nombreux |
| **State Variables** | 4 | ✓ Acceptable |
| **Nesting Depth** | 5 | ⚠️ Trop profond |
| **Cyclomatic Complexity** | 14 | ⚠️ Élevée |

##### Sections Complexes

| Section | Lines | Start Line | Complexity | Issues |
|---------|-------|------------|------------|--------|
| Supabase realtime setup | 87 | 57 | 16 | TRÈS COMPLEXE: async, subscriptions multiples |
| Filter logic | 15 | 147 | 5 | Logique temporelle |
| Render with conditions | 54 | 193 | 7 | JSX imbriqué |

#### Problèmes Identifiés

1. **useEffect trop complexe**: Real-time subscription (87 lignes!)
2. **Responsabilités multiples**: UI + data fetching + real-time + state management
3. **Nesting profond**: Jusqu'à 5 niveaux dans le JSX
4. **Magic numbers**: 30000, 1000, etc.
5. **Inline functions**: Callbacks définis dans le render

#### Recommandations

- ✅ Extraire la logique Supabase dans un hook custom `useRealtimePickups`
- ✅ Créer un hook `useAutoRefresh` pour la logique de refresh
- ✅ Séparer le filtrage dans une fonction pure `filterPickups`
- ✅ Diviser le composant en sous-composants (Header, PickupQueue, Footer)
- ✅ Déplacer les constantes dans un fichier config

---

### 5. React: auth-screen.jsx

**Chemin**: `/home/user/openai-apps-sdk-examples/src/allobye-dashboard/auth-screen.jsx`

#### Métriques Globales
- **Total Lines**: 355
- **Components**: 1 (AuthScreen)
- **Decision Points**: 15
- **Estimated Cyclomatic Complexity**: MEDIUM-HIGH

#### Analyse du Composant

##### Complexité du Composant AuthScreen

| Aspect | Métrique | Status |
|--------|----------|--------|
| **Total Lines** | 355 | ⚠️ Très long |
| **Functions** | 3 handlers | ✓ Acceptable |
| **State Variables** | 2 | ✓ Bon |
| **Render Modes** | 3 | ⚠️ Conditionnel complexe |
| **Cyclomatic Complexity** | 12 | ⚠️ Élevée |

##### Handlers

| Handler | Lines | Start Line | Complexity | Issues |
|---------|-------|------------|------------|--------|
| `handleSignup` | 65 | 70 | 11 | Trop long, validation + API + navigation |
| `handleLogin` | 39 | 29 | 7 | Gestion d'erreur verbose |
| `handleResetPassword` | 23 | 137 | 4 | Simple |

#### Problèmes Identifiés

1. **Render trop long**: 355 lignes pour un seul composant
2. **Duplication**: 3 formulaires très similaires
3. **handleSignup trop complexe**: 65 lignes avec validation, API calls, navigation
4. **Alert usage**: `alert()` au lieu de UI moderne
5. **Inline validation**: Logique de validation dans le handler

#### Recommandations

- ✅ Diviser en 3 composants: LoginForm, SignupForm, ResetPasswordForm
- ✅ Créer un hook `useAuth` pour la logique d'authentification
- ✅ Utiliser un library de validation (yup, zod)
- ✅ Créer un composant Toast/Notification au lieu d'alert()
- ✅ Extraire la validation dans des fonctions pures

---

### 6. React: monitoring/dashboard.jsx

**Chemin**: `/home/user/openai-apps-sdk-examples/src/allobye-monitoring/dashboard.jsx`

#### Métriques Globales
- **Total Lines**: 208
- **Components**: 1 (MonitoringDashboard)
- **Decision Points**: 9
- **Estimated Cyclomatic Complexity**: LOW-MEDIUM

#### Analyse du Composant

##### Complexité

| Aspect | Métrique | Status |
|--------|----------|--------|
| **Total Lines** | 208 | ✓ Acceptable |
| **useEffect Hooks** | 2 | ✓ Bon |
| **State Variables** | 4 | ✓ Bon |
| **Cyclomatic Complexity** | 7 | ✓ Acceptable |

#### Évaluation

**Verdict: BIEN STRUCTURÉ ✓**

Ce composant est un bon exemple de code React maintenable:
- Taille raisonnable (< 250 lignes)
- Responsabilités claires
- Hooks bien utilisés
- Logique séparée dans des sous-composants

#### Recommandations Mineures

- ✓ Extraire getMockData() dans un fichier séparé
- ✓ Utiliser un state management library (Redux, Zustand) pour les données de monitoring
- ✓ Ajouter error boundaries

---

### 7. SQL: schema.sql

**Chemin**: `/home/user/openai-apps-sdk-examples/allobye_server_python/schema.sql`

#### Métriques Globales
- **Total Lines**: 595
- **Tables**: 7
- **Functions**: 5
- **Triggers**: 6
- **RLS Policies**: 22
- **Decision Points (IF/CASE)**: 43
- **Estimated Cyclomatic Complexity**: MEDIUM-HIGH

#### Analyse par Section

##### Tables

| Table | Columns | Indexes | RLS Policies | Complexity |
|-------|---------|---------|--------------|------------|
| schools | 8 | 1 | 2 | Low |
| children | 9 | 2 | 3 | Medium |
| delegates | 7 | 2 | 3 | Medium |
| pickups | 11 | 4 | 4 | High |
| pickup_children | 5 | 2 | 2 | Medium |
| delegate_children | 6 | 2 | 3 | Medium |
| emergencies | 10 | 4 | 4 | High |

##### Fonctions SQL

| Function | Lines | Start Line | Complexity | Issues |
|----------|-------|------------|------------|--------|
| `notify_emergency` | 29 | 196 | 8 | JOIN, pg_notify, json_build_object |
| `cascade_pickup_status` | 22 | 234 | 10 | Multiple IF, UPDATE cascade |
| `get_upcoming_pickups` | 32 | 506 | 9 | JOIN multiple, filtrage temporel |
| `get_active_emergencies` | 16 | 541 | 4 | Simple |
| `update_updated_at_column` | 5 | 157 | 1 | Triviale |

##### RLS Policies (217 lignes!)

**Total Policies**: 22
**Complexity**: HIGH

Les policies RLS sont très nombreuses et complexes, avec des EXISTS subqueries multiples.

#### Problèmes Identifiés

1. **RLS Policies trop nombreuses**: 22 policies (217 lignes)
2. **cascade_pickup_status**: Logique complexe avec multiples UPDATE
3. **notify_emergency**: JSON building et pg_notify complexe
4. **Duplication**: Patterns RLS répétés pour chaque table
5. **Performance**: EXISTS subqueries dans chaque policy

#### Recommandations

- ✅ Créer des fonctions helpers pour les RLS policies répétées
- ✅ Simplifier cascade_pickup_status en décomposant en 2 triggers
- ✅ Indexer les colonnes utilisées dans les policies (parent_email, etc.)
- ✅ Documenter chaque policy avec des commentaires
- ✅ Considérer un audit table pour tracer les changements

---

## Métriques de Complexité par Catégorie

### Distribution de Complexité Cyclomatique

| Complexity Range | Count | Percentage | Status |
|------------------|-------|------------|--------|
| CC 1-5 (Simple) | 45 | 58% | ✓ Excellent |
| CC 6-10 (Moderate) | 20 | 26% | ⚠️ Acceptable |
| CC 11-15 (Complex) | 10 | 13% | ⚠️ À surveiller |
| CC 16+ (Very Complex) | 2 | 3% | ❌ Critique |

### Distribution de Taille de Fonction

| Size Range | Count | Percentage | Status |
|------------|-------|------------|--------|
| 1-20 lignes | 32 | 42% | ✓ Excellent |
| 21-50 lignes | 33 | 43% | ✓ Acceptable |
| 51-100 lignes | 10 | 13% | ⚠️ À refactorer |
| 100+ lignes | 2 | 2% | ❌ Critique |

---

## Debt Technique Score

### Calcul du Score

**Formule**: `Tech Debt Score = (Functions > 50 lines × 3) + (CC > 10 × 5) + (Nesting > 4 × 2)`

| Critère | Count | Weight | Score |
|---------|-------|--------|-------|
| Fonctions > 50 lignes | 12 | × 3 | 36 |
| CC > 10 | 8 | × 5 | 40 |
| Nesting > 4 | 5 | × 2 | 10 |
| **TOTAL** | - | - | **86** |

### Interprétation

| Score Range | Rating | AllôBye Score |
|-------------|--------|---------------|
| 0-30 | Excellent ✓ | - |
| 31-60 | Bon ✓ | - |
| 61-100 | Moyen ⚠️ | **86 ⚠️** |
| 101-150 | Mauvais ❌ | - |
| 150+ | Critique ❌ | - |

**Verdict**: Le codebase a un niveau de dette technique **MOYEN** qui nécessite une attention.

---

## Cognitive Load Analysis

### Fonctions avec Cognitive Load Élevé

| Function | File | Cognitive Complexity | Raison |
|----------|------|----------------------|--------|
| Supabase realtime setup | dashboard.jsx | 18 | Async, callbacks imbriqués, subscriptions multiples |
| `_handle_pickup_schedule_create` | main.py | 17 | Validation multiple, boucles, conditions imbriquées |
| `signup_user` | auth.py | 16 | Branches d'erreur multiples, DB operations |
| `cascade_pickup_status` | schema.sql | 15 | Logique conditionnelle SQL complexe |
| `_handle_delegate_authorize` | main.py | 14 | Vérifications en cascade |

---

## Conclusion et Recommandations Prioritaires

### Top 5 Priorités de Refactoring

1. **🔥 URGENT**: Refactoriser `dashboard.jsx` useEffect real-time (87 lignes)
   - Impact: High | Effort: Medium | ROI: High

2. **🔥 URGENT**: Diviser `signup_user` et `login_user` (auth.py)
   - Impact: High | Effort: Low | ROI: Very High

3. **⚠️ HIGH**: Extraire validation logic dans decorators (main.py)
   - Impact: Medium | Effort: Medium | ROI: High

4. **⚠️ HIGH**: Simplifier RLS policies avec helper functions (schema.sql)
   - Impact: Medium | Effort: High | ROI: Medium

5. **⚠️ MEDIUM**: Diviser MetricsCollector class (monitoring.py)
   - Impact: Medium | Effort: Medium | ROI: Medium

### Métriques Cibles Post-Refactoring

| Métrique | Actuel | Cible | Amélioration |
|----------|--------|-------|--------------|
| Avg Function Size | 39 lignes | < 30 lignes | -23% |
| Functions > 50 lines | 12 | < 5 | -58% |
| Avg CC | 7.2 | < 5 | -31% |
| Tech Debt Score | 86 | < 50 | -42% |

---

**Rapport généré le**: 2025-11-04
**Outil**: Auditeur de Complexité - Custom Analysis
**Next Review**: 2025-11-11 (1 semaine)
