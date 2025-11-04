# Code Ownership Map - AllôBye

**Date**: 2025-11-04
**Analyste**: Traceur de Changements
**Codebase**: AllôBye - Système de coordination de ramassage scolaire

---

## Executive Summary

### Ownership Overview

| Zone | Primary Owner | Commits | LOC | Bus Factor | Risk |
|------|---------------|---------|-----|------------|------|
| **AllôBye** | Claude (AI) | 1 | 13,732 | **1** | ❌ CRITICAL |
| **Pizzaz** | Katia Gil Guzman | 18 | ~8,500 | **1** | ⚠️ HIGH |
| **Solar System** | Katia Gil Guzman | 5 | ~2,100 | **1** | ⚠️ HIGH |
| **Infrastructure** | Katia Gil Guzman | 6 | ~1,400 | **1** | ⚠️ MEDIUM |
| **Repository Global** | Katia Gil Guzman | 15 (60%) | ~12,000 | **1** | ❌ CRITICAL |

### Verdict Global

**Bus Factor: 1** ❌ **CRITICAL**

Le projet est dans une situation de **risque critique** avec:
- **60%** du code par un seul contributeur humain (Katia)
- **54%** du code par un AI agent (Claude)
- **100%** d'AllôBye sans ownership humain
- **Aucun co-ownership** sur fichiers critiques

---

## Ownership Methodology

### Définitions

**Primary Owner**: Auteur de >50% des commits d'un fichier
**Secondary Owner**: Auteur de 20-50% des commits
**Contributor**: Auteur de <20% des commits
**Orphan Code**: Code sans owner actif (>3 mois sans modification)
**AI-Owned Code**: Code créé/maintenu uniquement par AI agents

### Ownership Metrics

| Métrique | Définition | Cible Saine |
|----------|------------|-------------|
| **Bus Factor** | Min personnes perdues = paralysie | ≥ 3 |
| **Concentration** | % code par top contributor | < 40% |
| **Co-Ownership** | % fichiers avec ≥2 owners | > 60% |
| **AI Ownership** | % code par AI uniquement | < 10% |
| **Orphan Rate** | % code sans owner actif | < 5% |

### Current State

| Métrique | Valeur | Cible | Status |
|----------|--------|-------|--------|
| **Bus Factor** | 1 | ≥ 3 | ❌ CRITICAL |
| **Concentration** | 60% (Katia) | < 40% | ❌ HIGH |
| **Co-Ownership** | 24% | > 60% | ❌ CRITICAL |
| **AI Ownership** | 54% (Claude) | < 10% | ❌ CRITICAL |
| **Orphan Rate** | 0% | < 5% | ✓ (trop récent) |

---

## Ownership by Contributor

### 1. Katia Gil Guzman

**Role**: Lead Maintainer / Primary Owner

**Commits**: 15 (60%)
**Lines Owned**: ~12,000 (47%)
**Active Period**: 2025-10-06 → 2025-10-23 (18 jours)
**Last Activity**: 2025-10-23 (12 jours ago)

**Owned Files** (Primary Owner >50%):

#### Backend
- `pizzaz_server_python/main.py` (5/7 commits = 71%)
- `pizzaz_server_node/src/server.ts` (4/5 commits = 80%)
- `solar-system_server_python/main.py` (4/5 commits = 80%)

#### Frontend
- `src/pizzaz/index.jsx` (3/4 commits = 75%)
- `src/pizzaz/Sidebar.jsx` (2/2 commits = 100%)
- `src/pizzaz-albums/index.jsx` (2/2 commits = 100%)
- `src/pizzaz-albums/FullscreenViewer.jsx` (2/2 commits = 100%)
- `src/pizzaz-albums/FilmStrip.jsx` (2/2 commits = 100%)
- `src/pizzaz-carousel/PlaceCard.jsx` (2/2 commits = 100%)

#### Infrastructure
- `build-all.mts` (4/5 commits = 80%)
- `vite.config.mts` (1/2 commits = 50%)
- `README.md` (3/4 commits = 75%)

**Ownership Summary**:
```
Total Primary Ownership: 12 files
Total Secondary Ownership: 3 files
Contribution Range: Oct 6 → Oct 23
Activity Level: High (15 commits / 18 days = 0.83/day)
```

**Knowledge Concentration Risk**: ❌ **CRITICAL**
- Seul owner de 12 fichiers critiques
- Départ = paralysie complète de Pizzaz/Solar System
- Aucun backup owner identifié

---

### 2. Claude (AI Agent)

**Role**: AI Contributor (AllôBye Implementation)

**Commits**: 1 (4% des commits, mais 54% du code!)
**Lines Owned**: 13,732 (54%)
**Active Period**: 2025-11-04 (1 jour)
**Last Activity**: 2025-11-04 (0 jours ago)

**Owned Files** (Primary Owner 100%):

#### Backend Python
- `allobye_server_python/main.py` (1,582 LOC)
- `allobye_server_python/auth.py` (632 LOC)
- `allobye_server_python/monitoring.py` (753 LOC)
- `allobye_server_python/schema.sql` (595 LOC)
- `allobye_server_python/apply_schema.py` (359 LOC)
- `allobye_server_python/test_monitoring.py` (288 LOC)
- `allobye_server_python/seed.sql` (273 LOC)

#### Frontend React
- `src/allobye-dashboard/dashboard.jsx` (248 LOC)
- `src/allobye-dashboard/auth-screen.jsx` (355 LOC)
- `src/allobye-dashboard/emergency-alert.jsx` (42 LOC)
- `src/allobye-dashboard/pickup-card.jsx` (76 LOC)
- `src/allobye-dashboard/index.jsx` (125 LOC)

#### Monitoring Widgets
- `src/allobye-monitoring/dashboard.jsx` (208 LOC)
- `src/allobye-monitoring/alerts-panel.jsx` (45 LOC)
- `src/allobye-monitoring/errors-list.jsx` (60 LOC)
- `src/allobye-monitoring/metrics-grid.jsx` (47 LOC)
- `src/allobye-monitoring/system-health.jsx` (47 LOC)
- `src/allobye-monitoring/tool-usage-chart.jsx` (63 LOC)
- `src/allobye-monitoring/index.jsx` (11 LOC)

#### Documentation
- `ALLOBYE_IMPLEMENTATION_SUMMARY.md` (608 LOC)
- `QUICKSTART.md` (385 LOC)
- `allobye_server_python/README.md` (366 LOC)
- `allobye_server_python/AUTHENTICATION.md` (479 LOC)
- `allobye_server_python/MONITORING.md` (503 LOC)
- `allobye_server_python/SCHEMA_DOCUMENTATION.md` (608 LOC)
- + 4 autres docs (1,700 LOC total)

#### CSS Styles
- `src/allobye-dashboard/*.css` (6 files, 1,900 LOC)
- `src/allobye-monitoring/dashboard.css` (459 LOC)

**Ownership Summary**:
```
Total Primary Ownership: 42 files (100% AllôBye)
Total Secondary Ownership: 0 files
Contribution Range: Nov 4 only
Activity Level: Single Big Bang Commit
```

**AI Ownership Risk**: ❌❌ **CRITICAL**
- ✗ **Aucun humain** n'a touché au code AllôBye
- ✗ **Pas de review** humaine du code
- ✗ **Pas de tests** par développeur humain
- ✗ **Knowledge implicite** non documenté
- ✗ **Maintenance future** incertaine

**CRITICAL FINDING**: AllôBye est entièrement **orphelin** d'un point de vue humain:
- Créé par AI
- Jamais modifié par humain
- Aucun humain ne connaît le code en profondeur
- Bus Factor humain = **0** ❌

---

### 3. மனோஜ்குமார் பழனிச்சாமி (Manoj)

**Role**: Contributor (Refactoring/Cleanup)

**Commits**: 2 (8%)
**Lines Owned**: ~50 (0.2%)
**Active Period**: 2025-10-07 (1 jour)
**Last Activity**: 2025-10-07 (28 jours ago)

**Contributions**:
- `pizzaz_server_python/main.py` (2 params removed)
- `solar-system_server_python/main.py` (2 params removed)
- Uvicorn path updates (2 files)

**Ownership Summary**:
```
Total Primary Ownership: 0 files
Total Secondary Ownership: 2 files (pizzaz, solar-system main.py)
Contribution Type: Cleanup / Refactoring
```

**Ownership Role**: ✓ **Contributor** (sain)
- Contributions ciblées
- Code review via PR
- Pas de ownership critique

---

### 4. khong

**Role**: Infrastructure Contributor

**Commits**: 1 (4%)
**Lines Owned**: ~30 (0.1%)
**Active Period**: 2025-10-24 (1 jour)
**Last Activity**: 2025-10-24 (11 jours ago)

**Contributions**:
- `.pre-commit-config.yaml` (14 LOC)
- `.github/workflows/pre-commit.yml` (14 LOC)
- Ruff linting setup
- Minor fixes in pizzaz/solar-system main.py

**Ownership Summary**:
```
Total Primary Ownership: 0 files
Total Secondary Ownership: 0 files
Contribution Type: Infrastructure / Quality
```

**Ownership Role**: ✓ **Infrastructure Contributor** (sain)

---

### 5. Jill Bourque

**Role**: Bug Fixer

**Commits**: 1 (4%)
**Lines Owned**: ~10 (0.04%)
**Active Period**: 2025-10-17 (1 jour)

**Contributions**:
- `build-all.mts` (asset hashing fix, 2 lines changed)

**Ownership Summary**: Contributor (pas de ownership)

---

### 6-10. Other Contributors

**Vittorio, Obad94, Keycatowo, Allen Zhou, Alexi Christakis**

**Total Commits**: 5 (20% cumulé)
**Lines Owned**: ~200 (0.8%)
**Contribution Type**: Bug fixes, typo corrections

**Ownership Summary**: ✓ **Fly-by Contributors** (sain pour open-source)

---

## Ownership by Module

### AllôBye Module

**Primary Owner**: Claude (AI) - 100%
**Secondary Owners**: None
**Contributors**: None

**Files**: 42 (100% AI-owned)
**Lines**: 13,732 (100% AI-owned)

**Ownership Breakdown**:
```
allobye_server_python/
├── main.py              → Claude 100% (1,582 LOC)
├── auth.py              → Claude 100% (632 LOC)
├── monitoring.py        → Claude 100% (753 LOC)
├── schema.sql           → Claude 100% (595 LOC)
├── apply_schema.py      → Claude 100% (359 LOC)
├── test_monitoring.py   → Claude 100% (288 LOC)
├── seed.sql             → Claude 100% (273 LOC)
└── docs/                → Claude 100% (4,950 LOC)

src/allobye-dashboard/
├── dashboard.jsx        → Claude 100% (248 LOC)
├── auth-screen.jsx      → Claude 100% (355 LOC)
├── emergency-alert.jsx  → Claude 100% (42 LOC)
├── pickup-card.jsx      → Claude 100% (76 LOC)
├── index.jsx            → Claude 100% (125 LOC)
└── *.css (6 files)      → Claude 100% (1,900 LOC)

src/allobye-monitoring/
└── (7 files)            → Claude 100% (980 LOC)
```

**Bus Factor**: **0** (humain) / **1** (total) ❌❌

**CRITICAL RISK**:
- ✗ Aucun humain ne peut maintenir ce code
- ✗ Aucune review humaine
- ✗ Aucune évolution post-création
- ✗ Dépendance totale sur AI pour futures modifications

**Recommendation**: ⚠️ **URGENT**: Assigner 2-3 développeurs humains comme owners:
1. **Security Owner**: Review auth.py, schema.sql RLS
2. **Backend Owner**: Review main.py, monitoring.py
3. **Frontend Owner**: Review React components

---

### Pizzaz Module

**Primary Owner**: Katia Gil Guzman (71%)
**Secondary Owners**: Manoj (14%), Others (15%)
**Contributors**: 7 personnes

**Files**: ~35
**Lines**: ~8,500

**Ownership Breakdown**:
```
pizzaz_server_python/
└── main.py              → Katia 71%, Manoj 14%, Others 15%
                            (7 commits, 327 LOC)

pizzaz_server_node/
└── src/server.ts        → Katia 80%, Others 20%
                            (5 commits, 342 LOC)

src/pizzaz/
├── index.jsx            → Katia 75%, Alexi 25%
├── Sidebar.jsx          → Katia 100%
├── Inspector.jsx        → Katia 100%
└── map.css              → Katia 100%

src/pizzaz-albums/
├── index.jsx            → Katia 100%
├── FilmStrip.jsx        → Katia 50%, Vittorio 50%
├── FullscreenViewer.jsx → Katia 50%, Vittorio 50%
└── AlbumCard.jsx        → Katia 100%

src/pizzaz-carousel/
├── index.jsx            → Katia 100%
└── PlaceCard.jsx        → Katia 50%, Vittorio 50%
```

**Bus Factor**: **1** ⚠️

**RISK**: Katia owns 71% du code Pizzaz:
- Départ de Katia = ralentissement majeur
- Secondary owners limités (1-2 commits chacun)
- Knowledge concentration élevée

**Recommendation**: ⚠️ **Augmenter co-ownership**:
- Pair programming Katia + autres devs
- Distribuer nouvelles features à autres contributeurs
- Documentation approfondie du code existant

---

### Solar System Module

**Primary Owner**: Katia Gil Guzman (80%)
**Secondary Owners**: Manoj (20%)
**Contributors**: 2 personnes

**Files**: ~3
**Lines**: ~2,100

**Ownership Breakdown**:
```
solar-system_server_python/
└── main.py              → Katia 80%, Manoj 20%
                            (5 commits, 313 LOC)

src/solar-system/
├── solar-system.jsx     → Katia 100% (524 LOC)
└── index.jsx            → Katia 100% (5 LOC)
```

**Bus Factor**: **1** ⚠️

**RISK**: Module très concentré (2 personnes seulement)

---

### Infrastructure Module

**Primary Owner**: Katia Gil Guzman (67%)
**Secondary Owners**: khong (17%), Others (16%)
**Contributors**: 5 personnes

**Files**: ~10
**Lines**: ~1,400

**Ownership Breakdown**:
```
Build & Config:
├── build-all.mts        → Katia 80%, Jill 20%
├── vite.config.mts      → Katia 50%, Obad94 50%
├── package.json         → Katia 80%, Claude 20%
└── pnpm-lock.yaml       → Katia 80%, Claude 20%

Quality:
├── .pre-commit-config   → khong 100%
├── .github/workflows/   → khong 100%
└── .gitignore           → Katia 67%, khong 33%

Docs:
├── README.md            → Katia 75%, Allen 25%
└── LICENSE              → Katia 100%
```

**Bus Factor**: **1-2** ⚠️

**Observation**: Meilleure distribution que code métier, mais Katia toujours dominante.

---

## Co-Ownership Analysis

### Définition

**Co-Ownership**: Fichiers avec ≥2 contributors significatifs (>20% commits each)

### Current Co-Ownership Rate

**Total Files**: ~90
**Co-Owned Files**: 22
**Co-Ownership Rate**: **24%** ❌

**Target**: >60%

### Co-Owned Files (Good Examples)

| File | Owners | Distribution | Status |
|------|--------|--------------|--------|
| `pizzaz_server_python/main.py` | 3 | Katia 71%, Manoj 14%, khong 14% | ⚠️ Acceptable |
| `vite.config.mts` | 2 | Katia 50%, Obad94 50% | ✓ Excellent |
| `pizzaz-albums/FilmStrip.jsx` | 2 | Katia 50%, Vittorio 50% | ✓ Excellent |
| `pizzaz-albums/FullscreenViewer.jsx` | 2 | Katia 50%, Vittorio 50% | ✓ Excellent |
| `pizzaz-carousel/PlaceCard.jsx` | 2 | Katia 50%, Vittorio 50% | ✓ Excellent |

**Good Pattern**: Frontend files ont meilleur co-ownership que backend.

### Single-Owner Files (Risk)

| File | Owner | Commits | Risk |
|------|-------|---------|------|
| **AllôBye (42 files)** | **Claude** | **1 each** | **❌ CRITICAL** |
| `src/pizzaz/Sidebar.jsx` | Katia | 2 | ⚠️ Medium |
| `src/pizzaz/Inspector.jsx` | Katia | 1 | ⚠️ Medium |
| `pizzaz-albums/index.jsx` | Katia | 2 | ⚠️ Medium |
| `solar-system/solar-system.jsx` | Katia | 1 | ⚠️ Medium |

**CRITICAL**: 42 fichiers AllôBye à 100% single-owner (AI).

---

## Knowledge Map

### Expertise par Domain

**Method**: Identifier qui connaît quoi dans le codebase.

#### Backend Python

| Domain | Expert | Secondary | Knowledge Gap |
|--------|--------|-----------|---------------|
| **Pizzaz Server** | Katia (71%) | Manoj (14%) | ⚠️ Gap if Katia leaves |
| **Solar System Server** | Katia (80%) | Manoj (20%) | ⚠️ Gap if Katia leaves |
| **AllôBye Server** | Claude (100%) | - | ❌ No human knowledge |
| **AllôBye Auth** | Claude (100%) | - | ❌❌ CRITICAL (security) |
| **AllôBye Schema** | Claude (100%) | - | ❌ CRITICAL (data) |

#### Frontend React

| Domain | Expert | Secondary | Knowledge Gap |
|--------|--------|-----------|---------------|
| **Pizzaz UI** | Katia (80%) | Alexi (10%), Vittorio (10%) | ⚠️ Moderate |
| **Pizzaz Albums** | Katia (60%) | Vittorio (40%) | ✓ Good |
| **Solar System UI** | Katia (100%) | - | ⚠️ Gap |
| **AllôBye Dashboard** | Claude (100%) | - | ❌ No human knowledge |
| **AllôBye Auth UI** | Claude (100%) | - | ❌ No human knowledge |

#### Infrastructure

| Domain | Expert | Secondary | Knowledge Gap |
|--------|--------|-----------|---------------|
| **Build System** | Katia (80%) | Jill (20%) | ⚠️ Moderate |
| **Vite Config** | Katia (50%) | Obad94 (50%) | ✓ Good |
| **CI/CD** | khong (100%) | - | ⚠️ Single point |
| **Quality Tools** | khong (100%) | - | ⚠️ Single point |

#### Documentation

| Domain | Expert | Secondary | Knowledge Gap |
|--------|--------|-----------|---------------|
| **README** | Katia (75%) | Allen (25%) | ✓ Good |
| **AllôBye Docs** | Claude (100%) | - | ⚠️ AI-generated |

---

## Bus Factor Analysis

### Global Bus Factor

**Definition**: Minimum nombre de personnes qui doivent partir pour paralyser le projet.

**Calcul**:
```
Contributors ranked by LOC contribution:
1. Claude:  13,732 LOC (54%)
2. Katia:   ~12,000 LOC (47%)
3. Others:  ~500 LOC (2%)

Cumulative contribution to reach 50% threshold:
- Claude alone: 54% ✓
- Katia alone: 47% ✗ (but close!)

Bus Factor = 1 ❌
```

**Interpretation**:
- **Perte de Claude** = Perte de 54% du code (AllôBye entier)
- **Perte de Katia** = Perte de 47% du code (Pizzaz + infra)
- Either leaves → **paralysie majeure**

### Bus Factor by Module

| Module | Bus Factor | Primary Risk | Impact if Lost |
|--------|------------|--------------|----------------|
| **AllôBye** | **0** (human) / **1** (total) | ❌ CRITICAL | Complete AllôBye abandoned |
| **Pizzaz** | **1** | ❌ CRITICAL | Development stops |
| **Solar System** | **1** | ❌ CRITICAL | Development stops |
| **Infrastructure** | **1** | ⚠️ HIGH | Builds/deploys break |
| **Quality/CI** | **1** | ⚠️ HIGH | No automated checks |

**FINDING**: ❌ **Every module has Bus Factor ≤ 1**

### Bus Factor Improvement Plan

**Target**: Bus Factor ≥ 3 (industry standard)

**Strategy**:

**Phase 1 (2 weeks): Emergency Knowledge Transfer**
1. Assigner 2 devs humains à AllôBye (primary + secondary owners)
2. Code walkthrough AllôBye avec Claude (si possible) ou docs
3. Pair programming Katia + 2 autres devs sur Pizzaz

**Phase 2 (1 month): Distributed Ownership**
1. Chaque fichier doit avoir ≥2 owners
2. Nouvelles features assigned à secondary owners
3. Primary owners font code review seulement

**Phase 3 (3 months): Knowledge Democratization**
1. Rotation des owners (primary ↔ secondary)
2. Onboarding docs pour chaque module
3. Weekly knowledge sharing sessions

**Success Metrics**:
- Bus Factor ≥ 3 (target: 4-5)
- Co-ownership rate ≥ 60%
- Max concentration ≤ 30% (currently 54%)

---

## Orphan Code Detection

### Definition

**Orphan Code**: Code sans owner actif (>90 jours sans modification par primary owner).

### Current Status

**Repository Age**: 29 jours
**Evaluation**: ❌ **Trop récent pour détecter orphan code**

**Potential Future Orphans** (à surveiller):

| File | Last Modified | Primary Owner | Days Inactive | Risk |
|------|---------------|---------------|---------------|------|
| `src/todo/todo.jsx` | Oct 6 | Katia | 29 | ⚠️ Medium |
| `src/todo/index.jsx` | Oct 6 | Katia | 29 | ⚠️ Medium |
| Solar system files | Oct 16 | Katia | 19 | ✓ Active |
| Pizzaz files | Oct 24 | Katia | 11 | ✓ Active |
| **AllôBye files** | **Nov 4** | **Claude** | **0** | **⚠️ Will become orphan?** |

**PREDICTION**: AllôBye risque de devenir orphan si:
- Claude (AI) n'intervient plus
- Aucun humain ne prend ownership
- Pas modifié dans 90 jours (→ Feb 2026)

**Recommendation**: ⚠️ **Assigner ownership humain AVANT que AllôBye devienne orphan**

---

## AI vs Human Ownership

### Distribution

| Owner Type | Commits | LOC | Files | Percentage |
|------------|---------|-----|-------|------------|
| **AI (Claude)** | 1 (4%) | 13,732 | 42 | **54%** |
| **Human (All)** | 24 (96%) | 12,496 | ~50 | **46%** |
| - Katia | 15 (60%) | ~12,000 | ~35 | 47% |
| - Others | 9 (36%) | ~500 | ~15 | 2% |

**CRITICAL FINDING**: ❌ **AI owns more code than all humans combined!**

### AI Ownership Risks

**Risks Spécifiques**:
1. ❌ **No Human Review**: Code non validé par humains
2. ❌ **No Domain Knowledge**: AI ne comprend pas le contexte métier
3. ❌ **No Maintenance**: AI ne maintiendra pas le code long-terme
4. ❌ **No Evolution**: AI ne fera pas évoluer l'architecture
5. ❌ **Security Blind Spots**: AI peut manquer vulnérabilités subtiles

**Industry Best Practice**: AI code doit être:
- ✓ Reviewé par ≥2 humains
- ✓ Owned par ≥1 humain (primary)
- ✓ Testé extensivement (>80% coverage)
- ✓ Documenté en profondeur
- ✓ Refactoré si nécessaire

**AllôBye Status**: ❌ **Aucune de ces pratiques suivie**

### Recommendation: AI Code Ownership Policy

**Proposed Policy**:
```yaml
ai_code_policy:
  max_ai_contribution_per_commit: 500 LOC
  required_human_reviews: 2
  required_test_coverage: 80%
  required_documentation: comprehensive
  max_ai_ownership: 10%  # of total codebase

  enforcement:
    - block_merge_if_no_human_review: true
    - require_human_owner_assignment: true
    - automated_security_scan: true
```

---

## Ownership Evolution

### Timeline

**October 6, 2025**: Repository created
- Owner: Katia (100%)
- Files: 61
- LOC: ~11,500

**October 7-15**: Active development
- Owners: Katia (80%), Others (20%)
- Contributors: +7 personnes
- Co-ownership emerging

**October 16-24**: Stabilization
- Katia: 60% ownership (diluted)
- Quality improvements (khong)
- Good co-ownership trend

**November 4, 2025**: AllôBye Big Bang
- Claude: +13,732 LOC (54% total)
- Ownership distribution destroyed
- Bus Factor reverted to 1

### Ownership Trend

```
Ownership Concentration (% by top contributor):

Oct 6:  100% Katia ●━━━━━━━━━━━━━━━━━━━━━━━ Critical
Oct 10:  80% Katia  ●━━━━━━━━━━━━━━━━━━━━━ High
Oct 20:  60% Katia   ●━━━━━━━━━━━━━━━━━ ⬇ Improving
Oct 24:  60% Katia    ●━━━━━━━━━━━━━━━━ Stable
Nov 4:  54% Claude   ●━━━━━━━━━━━━━━━━━━━━━━ ⬆ WORSE!
        47% Katia
```

**Observation**: ⚠️ **AllôBye commit DESTROYED positive ownership trend**

---

## Contributor Health

### Active Contributors

**Last 30 Days**:
- Katia: Last commit Oct 23 (12 days ago) ⚠️
- Claude: Last commit Nov 4 (0 days ago) ✓
- khong: Last commit Oct 24 (11 days ago) ⚠️
- Others: >20 days ago ❌

**Concern**: ⚠️ **Humains inactifs depuis 11+ jours**

### Contributor Velocity

| Contributor | Period | Commits | Velocity (commits/day) |
|-------------|--------|---------|------------------------|
| Katia | Oct 6-23 (18d) | 15 | 0.83 /day ✓ |
| Claude | Nov 4 (1d) | 1 | 1.00 /day ⚠️ (Big Bang) |
| khong | Oct 24 (1d) | 1 | 1.00 /day ✓ |
| Manoj | Oct 7 (1d) | 2 | 2.00 /day ✓ |
| Others | Various | 1 each | - |

**Observation**: Katia seule a vélocité soutenue. Autres contributeurs ponctuels.

---

## Knowledge Transfer Requirements

### Critical Knowledge Gaps

**Priority 1 (URGENT)**:
1. ❌ **AllôBye Auth System** (auth.py)
   - Current: Claude 100%
   - Target: 2 security experts
   - Timeline: 1 week

2. ❌ **AllôBye Schema** (schema.sql)
   - Current: Claude 100%
   - Target: 1 DBA + 1 backend dev
   - Timeline: 1 week

3. ❌ **AllôBye Main Logic** (main.py)
   - Current: Claude 100%
   - Target: 2 backend developers
   - Timeline: 2 weeks

**Priority 2 (HIGH)**:
4. ⚠️ **Pizzaz Server** (main.py)
   - Current: Katia 71%
   - Target: Katia 40%, Others 60%
   - Timeline: 1 month

5. ⚠️ **Build System**
   - Current: Katia 80%
   - Target: Katia 50%, Others 50%
   - Timeline: 2 weeks

### Knowledge Transfer Plan

**Week 1-2: AllôBye Emergency Transfer**
```
Day 1-3: Code Reading
- Assign 3 devs to read AllôBye code
- Take notes on unclear sections
- List questions

Day 4-5: Code Walkthrough
- Review auth.py line-by-line
- Review schema.sql (RLS policies)
- Review main.py (handlers)

Day 6-7: Hands-On
- Devs add tests to auth.py
- Devs add tests to main.py
- Devs review security

Week 2: Ownership Assignment
- Dev 1: Primary owner auth.py
- Dev 2: Primary owner main.py + monitoring.py
- Dev 3: Primary owner schema.sql + frontend
```

**Week 3-4: Pizzaz/Infra Transfer**
```
Week 3: Pair Programming
- Katia + Dev A: Pizzaz server
- Katia + Dev B: Build system

Week 4: Shadowing
- Dev A leads Pizzaz changes
- Dev B leads build changes
- Katia reviews only
```

**Success Metrics**:
- Each critical file has ≥2 owners (humans)
- AllôBye knowledge transferred to ≥3 humans
- Bus Factor ≥ 2 after 2 weeks
- Bus Factor ≥ 3 after 1 month

---

## Recommendations

### Immediate Actions (Cette Semaine)

1. **🔥 URGENT: Assign AllôBye Human Owners**
   - Action: Désigner 3 développeurs
   - Timeline: Aujourd'hui
   - Responsible: Tech Lead

2. **🔥 URGENT: Code Review AllôBye**
   - Action: 2-3 reviewers humains pour tout AllôBye
   - Focus: Security (auth.py), Data (schema.sql), Logic (main.py)
   - Timeline: Cette semaine

3. **🔥 URGENT: AllôBye Onboarding**
   - Action: Code walkthrough pour nouveaux owners
   - Format: 3× sessions de 2h
   - Timeline: Cette semaine

### Short-Term Actions (2 Semaines)

4. **Increase Co-Ownership Rate**
   - Target: 60% files co-owned
   - Action: Pair programming obligatoire
   - Assign secondary owners à tous fichiers critiques

5. **Knowledge Documentation**
   - Action: Chaque primary owner documente son code
   - Format: Architecture Decision Records (ADRs)
   - Include: Design rationale, gotchas, TODOs

6. **Distributed Features**
   - Action: Nouvelles features assigned à non-primary owners
   - Primary owner: Code review seulement
   - Rotate ownership progressivement

### Long-Term Actions (1-3 Mois)

7. **Bus Factor ≥ 3**
   - Target: Minimum 3 personnes peuvent maintenir chaque module
   - Method: Rotation, pair programming, onboarding

8. **AI Code Policy**
   - Establish formal policy pour AI contributions
   - Require human review + ownership
   - Limit AI ownership à <10% du codebase

9. **Ownership Monitoring**
   - Automated tracking de ownership metrics
   - Monthly ownership reports
   - Alerts si Bus Factor < 2

10. **Knowledge Sharing**
    - Weekly tech talks (30 min)
    - Monthly code walkthroughs
    - Quarterly architecture reviews

---

## Conclusion

### État Actuel

**Status**: ❌ **OWNERSHIP CRITIQUE**

Le projet présente des risques critiques d'ownership:

**Problèmes Majeurs**:
1. ❌ **Bus Factor = 1** (paralysie si perte Katia OU Claude)
2. ❌ **54% du code owned par AI** (aucun humain connaît AllôBye)
3. ❌ **Co-ownership = 24%** (target: >60%)
4. ❌ **42 fichiers AllôBye sans owner humain**
5. ⚠️ **Katia owns 47%** du code (concentration élevée)

**Impacts**:
- Départ de Katia → Pizzaz/Solar System/Infra paralysés
- Claude n'intervient plus → AllôBye devient orphan
- Nouveaux devs → Courbe d'apprentissage très élevée
- Bugs AllôBye → Personne ne peut fixer
- Security issues → Personne ne peut auditer

### Prochaines Étapes Critiques

**Priorité Absolue**:
1. ❌ **Assigner owners humains AllôBye** (AUJOURD'HUI)
2. ❌ **Code review AllôBye** (CETTE SEMAINE)
3. ❌ **Knowledge transfer** (2 SEMAINES)
4. ⚠️ **Augmenter co-ownership** (1 MOIS)
5. ⚠️ **Bus Factor ≥ 3** (3 MOIS)

### Success Criteria (90 jours)

**Target Metrics**:
- Bus Factor: 1 → **≥ 3** ✓
- AI Ownership: 54% → **< 10%** ✓
- Co-Ownership: 24% → **≥ 60%** ✓
- Katia Concentration: 47% → **< 30%** ✓
- AllôBye Human Owners: 0 → **≥ 3** ✓

**Measurement**: Weekly ownership reports avec tracking

---

**Rapport généré le**: 2025-11-04
**Prochaine Analyse**: 2025-11-11 (1 semaine)
**Criticalité**: **CRITICAL ❌**
