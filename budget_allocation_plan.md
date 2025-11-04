# Budget Allocation Plan - AllôBye Technical Debt Remediation

**Date**: 2025-11-04
**Analyste**: Prioriseur de Risques
**Budget Total Recommandé**: $120K - $150K
**Timeline**: 12 semaines (3 mois)
**Équipe**: 2-4 développeurs + 1 security expert (part-time)

---

## Executive Summary

### Budget Breakdown par Catégorie

| Catégorie | Budget | Pourcentage | Timeline | Priorité |
|-----------|--------|-------------|----------|----------|
| **Security** | $48K - $69K | 40% | Weeks 1-4 | 🔥 CRITICAL |
| **Quality & Testing** | $40K - $57K | 33% | Weeks 2-8 | 🔥 CRITICAL |
| **Performance** | $6K - $9K | 5% | Weeks 1-3 | 🟠 HIGH |
| **Architecture** | $18K - $27K | 15% | Weeks 5-12 | 🟠 HIGH |
| **Process & Documentation** | $8K - $12K | 7% | Weeks 1-12 | 🟡 MEDIUM |
| **TOTAL** | **$120K - $174K** | **100%** | **12 weeks** | |

**Budget Optimal Recommandé**: **$135K** (moyenne)

---

## Phase 1: BLOCKERS (Week 1) - $8K - $12K

### Objectif: Éliminer les blockers critiques empêchant le déploiement

**Budget**: $10,000 (moyenne)
**Timeline**: 5 jours ouvrables
**Équipe**: 2 devs senior + 1 security expert (2 jours)
**Outcome**: Score 49 → 63 (+14 points, +29%)

### Allocation Détaillée

| Task | Priority | Effort | Hourly Rate | Cost | Resources |
|------|----------|--------|-------------|------|-----------|
| **Fix service role key** (VULN-004) | 🔥 P0 | 3h | $150/h | $450 | 1 senior dev |
| **Fix N+1 queries** (BOTTLENECK-01) | 🔥 P0 | 2.5h | $150/h | $375 | 1 senior dev |
| **Fix memory leak** (BOTTLENECK-02) | 🔥 P0 | 1h | $150/h | $150 | 1 dev |
| **Add CSRF protection** (VULN-007) | 🔥 P0 | 10h | $150/h | $1,500 | 1 senior dev |
| **Human code review** (retroactive) | 🔥 P0 | 50h | $150/h | $7,500 | 2 devs + security expert |
| **TOTAL WEEK 1** | | **66.5h** | | **$9,975** | |

### Breakdown par Jour

#### Jour 1 (Lundi): Quick Wins
- **9:00-10:00**: Fix service role key (VULN-004) - $150
- **10:00-11:00**: Fix memory leak (BOTTLENECK-02) - $150
- **11:00-13:30**: Fix N+1 queries (BOTTLENECK-01) - $375
- **14:00-17:00**: Add missing indexes (BOTTLENECK-05) - $0 (15 min, trivial)
- **Daily Cost**: $675

#### Jour 2 (Mardi): Security Hardening
- **9:00-13:00**: Add CSRF tokens (backend) - $600
- **14:00-18:00**: CSRF integration (frontend) - $600
- **Daily Cost**: $1,200

#### Jours 3-5 (Mercredi-Vendredi): Code Review
- **3 devs × 16h/jour × 3 jours**: 144h
- **Focus**: Security, architecture, business logic
- **Cost**: $7,500 (includes security expert 2 days @ $200/h)
- **Daily Cost**: $2,500/jour

**Total Week 1**: $9,975

---

## Phase 2: ESSENTIAL (Weeks 2-4) - $44K - $61K

### Objectif: Atteindre minimum production readiness

**Budget**: $52,500 (moyenne)
**Timeline**: 3 semaines (15 jours)
**Équipe**: 3 devs (2 senior + 1 mid-level)
**Outcome**: Score 63 → 76 (+13 points, +21%)

### Allocation par Semaine

#### Week 2: Security Critical ($16K)

| Task | Effort | Cost | Priority | Assignee |
|------|--------|------|----------|----------|
| **Encrypt medical data** (VULN-001) | 30h | $4,500 | 🔥 P1 | Senior dev |
| **Fix XSS cluster** (VULN-002, 003) | 10h | $1,500 | 🔥 P1 | Senior dev |
| **Add CSP + HSTS headers** (VULN-010, 011) | 3h | $450 | 🔥 P1 | Mid-level |
| **Critical path tests (→30%)** | 80h | $12,000 | 🔥 P1 | All 3 devs |
| **Week 2 Total** | **123h** | **$18,450** | | |

**Daily Breakdown Week 2**:
- 3 devs × 8h/jour × 5 jours = 120h
- Average cost: $3,690/jour

---

#### Week 3: Quality Foundation ($18K)

| Task | Effort | Cost | Priority | Assignee |
|------|--------|------|----------|----------|
| **Core logic tests (30%→60%)** | 100h | $15,000 | 🔥 P1 | All 3 devs |
| **Fix transaction safety** (DATA-002) | 20h | $3,000 | 🔥 P1 | Senior dev |
| **Week 3 Total** | **120h** | **$18,000** | | |

**Daily Breakdown Week 3**:
- 3 devs × 8h/jour × 5 jours = 120h
- Average cost: $3,600/jour

---

#### Week 4: Performance + Architecture ($16K)

| Task | Effort | Cost | Priority | Assignee |
|------|--------|------|----------|----------|
| **Optimize RLS policies** (BOTTLENECK-03) | 10h | $1,500 | 🟠 P2 | Senior dev |
| **Fix React re-renders** (BOTTLENECK-04) | 2h | $300 | 🟠 P2 | Mid-level |
| **Reduce JSON payloads** (BOTTLENECK-06) | 2h | $300 | 🟠 P2 | Mid-level |
| **WebSocket reconnection** (BOTTLENECK-07) | 7h | $1,050 | 🟠 P2 | Senior dev |
| **Edge case tests + QA** | 99h | $14,850 | 🟡 P3 | All 3 devs |
| **Week 4 Total** | **120h** | **$18,000** | | |

**Daily Breakdown Week 4**:
- 3 devs × 8h/jour × 5 jours = 120h
- Average cost: $3,600/jour

**Total Weeks 2-4**: $54,450

---

## Phase 3: QUALITY (Weeks 5-8) - $36K - $48K

### Objectif: Atteindre standards de l'industrie (60% → 80% test coverage)

**Budget**: $42,000 (moyenne)
**Timeline**: 4 semaines
**Équipe**: 3 devs (peut réduire à 2)
**Outcome**: Score 76 → 82 (+6 points, +8%)

### Allocation par Semaine

#### Week 5: Architecture Refactoring ($12K)

| Task | Effort | Cost | Priority | Assignee |
|------|--------|------|----------|----------|
| **Refactor main.py (part 1)** | 40h | $6,000 | 🟠 P3 | Senior dev |
| **Refactor auth.py (part 1)** | 20h | $3,000 | 🟠 P3 | Mid-level |
| **Comprehensive tests (60%→70%)** | 60h | $9,000 | 🟡 P3 | All 3 devs |
| **Week 5 Total** | **120h** | **$18,000** | | |

---

#### Week 6: TypeScript Migration ($9K)

| Task | Effort | Cost | Priority | Assignee |
|------|--------|------|----------|----------|
| **TypeScript setup + config** | 8h | $1,200 | 🟠 P3 | Senior dev |
| **.jsx → .tsx migration** | 32h | $4,800 | 🟠 P3 | Mid-level |
| **Type definitions + interfaces** | 10h | $1,500 | 🟠 P3 | Senior dev |
| **Tests update (types)** | 10h | $1,500 | 🟡 P3 | Mid-level |
| **Week 6 Total** | **60h** | **$9,000** | | |
| **Note**: Reduced to 2 devs this week | | | | |

---

#### Week 7: Testing Excellence ($12K)

| Task | Effort | Cost | Priority | Assignee |
|------|--------|------|----------|----------|
| **Frontend component tests** | 40h | $6,000 | 🟡 P3 | 2 devs |
| **Integration tests** | 30h | $4,500 | 🟡 P3 | Senior dev |
| **Performance tests** | 10h | $1,500 | 🟡 P4 | Mid-level |
| **Week 7 Total** | **80h** | **$12,000** | | |

---

#### Week 8: CI/CD + Documentation ($9K)

| Task | Effort | Cost | Priority | Assignee |
|------|--------|------|----------|----------|
| **CI/CD pipeline setup** | 24h | $3,600 | 🟡 P3 | Senior dev |
| **Coverage enforcement** | 8h | $1,200 | 🟡 P3 | Mid-level |
| **Architecture docs + ADRs** | 20h | $3,000 | 🟡 P4 | Senior dev |
| **Runbooks + incident response** | 8h | $1,200 | 🟡 P4 | Senior dev |
| **Week 8 Total** | **60h** | **$9,000** | | |

**Total Weeks 5-8**: $48,000

---

## Phase 4: EXCELLENCE (Weeks 9-12) - Optional ($30K)

### Objectif: Bus Factor increase + Advanced quality (80%+ test coverage)

**Budget**: $30,000
**Timeline**: 4 semaines
**Équipe**: 2-3 devs
**Outcome**: Score 82 → 85 (+3 points, +4%)

**Note**: Cette phase est **optionnelle** si budget limité

### Allocation

#### Weeks 9-10: Knowledge Transfer ($15K)

| Task | Effort | Cost | Priority | Notes |
|------|--------|------|----------|-------|
| **Pair programming sessions** | 80h | $12,000 | 🟡 P4 | 2 devs, knowledge spread |
| **Comprehensive documentation** | 20h | $3,000 | 🟡 P4 | Architecture, decisions |
| **Total** | **100h** | **$15,000** | | |

---

#### Weeks 11-12: Polish + Advanced Features ($15K)

| Task | Effort | Cost | Priority | Notes |
|------|--------|------|----------|-------|
| **Refactor remaining God Objects** | 40h | $6,000 | 🟡 P4 | Complete refactoring |
| **Advanced test coverage (→85%)** | 60h | $9,000 | 🟡 P4 | Edge cases, E2E |
| **Total** | **100h** | **$15,000** | | |

**Total Weeks 9-12**: $30,000 (OPTIONAL)

---

## Budget Scenarios Comparatifs

### Scenario A: Budget Minimal ($50K)

**Focus**: Sécurité + Tests critiques uniquement

| Phase | Budget | Timeline | Scope | Score |
|-------|--------|----------|-------|-------|
| Week 1: BLOCKERS | $10K | 1 week | Critical fixes | 49 → 58 |
| Weeks 2-3: SECURITY | $25K | 2 weeks | Security hardening | 58 → 68 |
| Week 4: TESTS (critical) | $15K | 1 week | 30% coverage | 68 → 72 |
| **TOTAL** | **$50K** | **4 weeks** | **Minimum viable** | **72/100 (C)** |

**Statut**: CONDITIONAL GO - Risque résiduel élevé
**Équipe**: 2 devs
**Risques**: Pas de refactoring, architecture debt reste

---

### Scenario B: Budget Modéré ($100K)

**Focus**: Sécurité + Quality + Architecture partiel

| Phase | Budget | Timeline | Scope | Score |
|-------|--------|----------|-------|-------|
| Week 1: BLOCKERS | $10K | 1 week | Critical fixes | 49 → 58 |
| Weeks 2-4: ESSENTIAL | $54K | 3 weeks | Security + tests 60% | 58 → 76 |
| Weeks 5-7: REFACTORING | $36K | 3 weeks | Arch + TypeScript | 76 → 80 |
| **TOTAL** | **$100K** | **7 weeks** | **Production ready** | **80/100 (B-)** |

**Statut**: GO WITH MONITORING - Risque acceptable
**Équipe**: 2-3 devs
**Bénéfices**: Prod-ready, standards minimaux atteints

---

### Scenario C: Budget Optimal ($135K) ⭐ RECOMMANDÉ

**Focus**: Remédiation complète + Industry standards

| Phase | Budget | Timeline | Scope | Score |
|-------|--------|----------|-------|-------|
| Week 1: BLOCKERS | $10K | 1 week | Critical fixes | 49 → 58 |
| Weeks 2-4: ESSENTIAL | $54K | 3 weeks | Security + tests 60% | 58 → 76 |
| Weeks 5-8: QUALITY | $48K | 4 weeks | Arch + TS + tests 80% | 76 → 82 |
| Weeks 9-10: EXCELLENCE | $23K | 2 weeks | Bus Factor + polish | 82 → 85 |
| **TOTAL** | **$135K** | **10 weeks** | **Industry standards** | **85/100 (B)** |

**Statut**: PRODUCTION READY - Standards de l'industrie
**Équipe**: 3 devs (réduction à 2 après Week 8)
**Bénéfices**: Maintenable, scalable, conforme

---

### Scenario D: Budget Maximum ($174K)

**Focus**: Excellence complète + Documentation extensive

| Phase | Budget | Timeline | Scope | Score |
|-------|--------|----------|-------|-------|
| Week 1: BLOCKERS | $12K | 1 week | Critical fixes | 49 → 58 |
| Weeks 2-4: ESSENTIAL | $61K | 3 weeks | Security + tests 60% | 58 → 76 |
| Weeks 5-8: QUALITY | $57K | 4 weeks | Arch + TS + tests 80% | 76 → 82 |
| Weeks 9-12: EXCELLENCE | $44K | 4 weeks | Bus Factor + 85% tests | 82 → 87 |
| **TOTAL** | **$174K** | **12 weeks** | **Excellence complète** | **87/100 (B+)** |

**Statut**: BEST IN CLASS - Au-dessus des standards
**Équipe**: 3-4 devs
**Bénéfices**: Documentation exemplaire, Bus Factor 3+

---

## Allocation par Type de Ressource

### Team Composition

#### Scenario Optimal ($135K)

| Role | Rate | Weeks | Hours/Week | Total Hours | Cost |
|------|------|-------|------------|-------------|------|
| **Senior Dev #1** | $150/h | 10 | 40h | 400h | $60,000 |
| **Senior Dev #2** | $150/h | 8 | 40h | 320h | $48,000 |
| **Mid-Level Dev** | $120/h | 10 | 40h | 400h | $48,000 |
| **Security Expert** (part-time) | $200/h | 2 | 40h | 80h | $16,000 |
| **QA Engineer** (part-time) | $100/h | 3 | 20h | 60h | $6,000 |
| **TOTAL** | | | | **1,260h** | **$178K** |

**Note**: Budget $135K = réduction d'heures ou négociation rates

**Optimization Suggestions**:
- Utiliser des devs locaux (rate plus bas)
- Offshore certaines tâches simples (tests simples)
- Security expert en consultation (16h au lieu de 80h)

---

### Revised Team for $135K Budget

| Role | Rate | Weeks | Hours/Week | Total Hours | Cost |
|------|------|-------|------------|-------------|------|
| **Senior Dev #1** | $150/h | 10 | 40h | 400h | $60,000 |
| **Senior Dev #2** | $140/h | 7 | 40h | 280h | $39,200 |
| **Mid-Level Dev** | $110/h | 9 | 40h | 360h | $39,600 |
| **Security Expert** (consulting) | $200/h | - | - | 16h | $3,200 |
| **TOTAL** | | | | **1,056h** | **$142K** |

**Négociation**: Rates moyens légèrement réduits → $135K achievable

---

## Breakdown par Catégorie (Budget $135K)

### 1. Security: $48K (36%)

| Item | Budget | Justification |
|------|--------|---------------|
| Service role key fix | $450 | Quick fix |
| XSS cluster remediation | $3,000 | Sanitization + CSP |
| Medical data encryption | $4,500 | Field-level + migration |
| CSRF protection | $1,500 | Tokens implementation |
| Security code review | $7,500 | Retroactive audit |
| Security testing | $12,000 | Test suite security |
| PII encryption | $4,800 | Additional fields |
| HSTS + CSP headers | $450 | Headers config |
| Rate limiting | $1,800 | Endpoint protection |
| Security documentation | $3,000 | Threat model + ADRs |
| Security expert consulting | $3,200 | 16h @ $200/h |
| Penetration testing | $5,800 | External audit |
| **TOTAL SECURITY** | **$48,000** | |

---

### 2. Quality & Testing: $46K (34%)

| Item | Budget | Justification |
|------|--------|---------------|
| Critical path tests (30%) | $12,000 | Week 2 |
| Core logic tests (60%) | $15,000 | Week 3 |
| Edge cases + QA (80%) | $9,000 | Weeks 7-8 |
| Frontend component tests | $6,000 | Week 7 |
| Integration tests | $4,500 | Week 7 |
| Performance tests | $1,500 | Week 7 |
| CI/CD pipeline | $3,600 | Week 8 |
| Coverage enforcement | $1,200 | Pre-commit hooks |
| Test infrastructure | $2,400 | Fixtures, mocks, factories |
| E2E testing setup | $1,800 | Playwright/Cypress |
| **TOTAL QUALITY** | **$46,000** | |

---

### 3. Architecture & Refactoring: $27K (20%)

| Item | Budget | Justification |
|------|--------|---------------|
| Refactor main.py | $9,000 | God Object split |
| Refactor auth.py | $4,500 | Modularization |
| TypeScript migration | $7,500 | .jsx → .tsx + types |
| Dual access pattern fix | $4,500 | Architecture cleanup |
| RLS policy optimization | $1,500 | Materialized views |
| **TOTAL ARCHITECTURE** | **$27,000** | |

---

### 4. Performance: $6K (4%)

| Item | Budget | Justification |
|------|--------|---------------|
| N+1 queries fix | $375 | Batch queries |
| Memory leak fix | $150 | Deque implementation |
| Missing indexes | $38 | 15 min work |
| React re-renders | $300 | Memoization |
| JSON payload reduction | $300 | Field selection |
| WebSocket reconnection | $1,050 | Retry logic |
| Bundle size optimization | $300 | Lazy loading |
| Request deduplication | $450 | Cache layer |
| Auto-refresh optimization | $600 | Adaptive rate |
| Performance monitoring | $2,437 | APM setup |
| **TOTAL PERFORMANCE** | **$6,000** | |

---

### 5. Process & Documentation: $8K (6%)

| Item | Budget | Justification |
|------|--------|---------------|
| Architecture documentation | $3,000 | Diagrams + ADRs |
| Runbooks + incident response | $1,200 | Operational docs |
| Knowledge transfer sessions | $2,400 | Pair programming |
| Commit standards enforcement | $300 | Pre-commit config |
| Security documentation | $1,100 | Threat model |
| **TOTAL PROCESS** | **$8,000** | |

**GRAND TOTAL**: **$135,000**

---

## Cashflow par Mois

### Month 1 (Weeks 1-4): $72,450

| Week | Phase | Budget | Cumul | Burn Rate |
|------|-------|--------|-------|-----------|
| Week 1 | BLOCKERS | $9,975 | $9,975 | $9,975/week |
| Week 2 | ESSENTIAL | $18,450 | $28,425 | $18,450/week |
| Week 3 | ESSENTIAL | $18,000 | $46,425 | $18,000/week |
| Week 4 | ESSENTIAL | $18,000 | $64,425 | $18,000/week |

**Monthly Burn Rate**: ~$65K/mois

---

### Month 2 (Weeks 5-8): $48,000

| Week | Phase | Budget | Cumul | Burn Rate |
|------|-------|--------|-------|-----------|
| Week 5 | QUALITY | $18,000 | $82,425 | $18,000/week |
| Week 6 | QUALITY | $9,000 | $91,425 | $9,000/week |
| Week 7 | QUALITY | $12,000 | $103,425 | $12,000/week |
| Week 8 | QUALITY | $9,000 | $112,425 | $9,000/week |

**Monthly Burn Rate**: ~$48K/mois

---

### Month 3 (Weeks 9-10): $22,575 (OPTIONAL)

| Week | Phase | Budget | Cumul | Burn Rate |
|------|-------|--------|-------|-----------|
| Week 9 | EXCELLENCE | $11,500 | $123,925 | $11,500/week |
| Week 10 | EXCELLENCE | $11,075 | $135,000 | $11,075/week |

**Monthly Burn Rate**: ~$23K/mois (2 semaines seulement)

---

## Payment Milestones

### Milestone 1: Week 1 Complete ($10K)

**Deliverables**:
- ✅ Service role key fixed + tested
- ✅ N+1 queries fixed + verified
- ✅ Memory leak fixed
- ✅ CSRF protection implemented
- ✅ Code review report (50h audit)

**Acceptance Criteria**:
- No CRITICAL blockers remain
- All Week 1 tests pass
- Security scan shows improvement

**Payment**: $10,000 upon acceptance

---

### Milestone 2: Week 4 Complete ($54K)

**Deliverables**:
- ✅ Medical data encrypted
- ✅ XSS vulnerabilities fixed
- ✅ Test coverage → 60%
- ✅ Transaction safety implemented
- ✅ Performance bottlenecks fixed

**Acceptance Criteria**:
- Security score > 70
- Test coverage ≥ 60%
- No CRITICAL or HIGH vulns
- Score ≥ 76/100

**Payment**: $54,000 upon acceptance

---

### Milestone 3: Week 8 Complete ($48K)

**Deliverables**:
- ✅ God Objects refactored
- ✅ TypeScript migration complete
- ✅ Test coverage → 80%
- ✅ CI/CD pipeline operational
- ✅ Documentation complete

**Acceptance Criteria**:
- Test coverage ≥ 80%
- CI/CD pipeline passing
- Score ≥ 82/100
- Architecture documented

**Payment**: $48,000 upon acceptance

---

### Milestone 4: Week 10 Complete ($23K) - OPTIONAL

**Deliverables**:
- ✅ Bus Factor ≥ 3
- ✅ Advanced test coverage (85%)
- ✅ All documentation complete
- ✅ Knowledge transfer complete

**Acceptance Criteria**:
- 3+ developers understand codebase
- Test coverage ≥ 85%
- Score ≥ 85/100
- No P0 or P1 issues remain

**Payment**: $23,000 upon acceptance

---

## Contingency Planning

### Budget Overrun Scenarios

#### Scenario 1: Discovery of Additional Issues (+10%)

**Likelihood**: Medium (40%)
**Impact**: +$13.5K
**Mitigation**:
- Reserve 10% contingency budget
- Prioritize newly discovered issues
- Defer low-priority items

**Revised Budget**: $135K + $13.5K = **$148.5K**

---

#### Scenario 2: Extended Testing Required (+15%)

**Likelihood**: Low (20%)
**Impact**: +$20K
**Mitigation**:
- Increase test coverage gradually (70% acceptable)
- Use offshore QA for simple tests
- Automate repetitive tests

**Revised Budget**: $135K + $20K = **$155K**

---

#### Scenario 3: Architecture Complexity (+20%)

**Likelihood**: Low (15%)
**Impact**: +$27K
**Mitigation**:
- Incremental refactoring
- Defer non-critical refactoring
- Focus on hotspots only

**Revised Budget**: $135K + $27K = **$162K**

---

### Budget Reduction Strategies

#### Strategy 1: Reduce Scope (Target: $100K)

**Cuts**:
- ❌ Week 9-10 (Knowledge Transfer): -$23K
- ❌ Advanced testing (80%→70%): -$12K
- **New Budget**: $100K
- **Score**: 80/100 (instead of 85/100)

---

#### Strategy 2: Optimize Resources (Target: $120K)

**Optimizations**:
- Use mid-level devs for simple tasks: -$10K
- Offshore simple tests: -$5K
- Reduce security consulting: -$3.2K
- Self-host CI/CD (no SaaS fees): -$2K
- **New Budget**: $120K
- **Score**: 82/100 (minimal impact)

---

#### Strategy 3: Extended Timeline (Target: $135K, 14 weeks)

**Approach**:
- Reduce team to 2 devs: Same budget, +2 weeks
- Lower weekly burn rate: $9.6K/week instead of $13.5K
- **New Timeline**: 14 weeks
- **Score**: 85/100 (same outcome)

---

## ROI Calculation

### Investment vs. Risk Avoided

| Scenario | Investment | Risk Avoided | Net Benefit | ROI |
|----------|------------|--------------|-------------|-----|
| **Minimal ($50K)** | $50K | $545K | $495K | 990% |
| **Moderate ($100K)** | $100K | $1.2M | $1.1M | 1,100% |
| **Optimal ($135K)** | $135K | $1.5M | $1.36M | **1,010%** |
| **Maximum ($174K)** | $174K | $1.8M | $1.63M | 935% |

**Break-even**: 1 mois (premier incident évité couvre investissement)

---

## Recommendations Finales

### Budget Optimal: $135,000

**Équipe**: 3 développeurs (2 senior + 1 mid) + 1 security expert (consulting)

**Timeline**: 10 semaines

**Outcome**: Score 85/100 (B) - Production ready with industry standards

**Breakdown**:
- **Month 1** (Weeks 1-4): $65K - Security + Essential
- **Month 2** (Weeks 5-8): $48K - Quality + Architecture
- **Month 3** (Weeks 9-10): $22K - Excellence (optional)

**Milestones**:
1. Week 1: $10K - Blockers eliminated
2. Week 4: $54K - Production minimum reached
3. Week 8: $48K - Industry standards achieved
4. Week 10: $23K - Excellence (optional)

**ROI**: 1,010% (10× return)

**Risk Mitigation**:
- 10% contingency budget ($13.5K) recommended
- Milestone-based payments reduce risk
- Incremental delivery ensures value

---

**Rapport généré**: 2025-11-04
**Validité**: Budget estimé pour Q4 2025 rates
**Prochaine révision**: Après Milestone 1 (Week 1)
**Contact**: Prioriseur de Risques - Budget Allocation Team
