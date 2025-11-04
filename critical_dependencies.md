# Critical Dependencies Analysis - AllôBye System

**Project**: AllôBye - Système de coordination de ramassage scolaire
**Analysis Date**: 2025-11-04
**Analyzer**: Cartographe de Dépendances Agent

---

## Executive Summary

The AllôBye system has **10 critical dependencies** that, if broken, would result in complete or major system failure. The dependency graph is **acyclic** (no circular dependencies), with a **maximum depth of 3 levels** and **strong cohesion** within modules.

### Risk Level: **MEDIUM-HIGH**

- ✅ **Strengths**: Clean architecture, no circular dependencies, highly modular
- ⚠️ **Concerns**: Heavy reliance on external MCP ecosystem (fastmcp, mcp)
- ❌ **Risks**: Supabase is a single point of failure for both backend and frontend

---

## 1. Critical Dependencies - Tier 1 (Complete System Failure)

These dependencies are **non-negotiable**. Their removal or failure would render the entire system inoperable.

### 1.1 Python Backend

#### `fastmcp` (>=0.8.0)
- **Impact**: 🔴 **CRITICAL - Complete System Failure**
- **Usage**: Core MCP protocol implementation, server framework
- **Breaking Scenario**: Unable to expose MCP tools to ChatGPT
- **Dependents**: `main.py` (central orchestrator)
- **Alternatives**: ❌ None (protocol-specific)
- **Mitigation**: Pin version in requirements.txt, monitor for breaking changes
- **Current Version**: 0.8.0+

#### `mcp` (>=1.3.0)
- **Impact**: 🔴 **CRITICAL - Complete System Failure**
- **Usage**: MCP types, interfaces (CallToolRequest, ServerResult, etc.)
- **Breaking Scenario**: Type mismatches, protocol incompatibility
- **Dependents**: `main.py` (all tool handlers)
- **Alternatives**: ❌ None (protocol-specific)
- **Mitigation**: Lock to stable version, extensive integration tests
- **Current Version**: 1.3.0+

#### `uvicorn` (>=0.32.1)
- **Impact**: 🔴 **CRITICAL - Complete System Failure**
- **Usage**: ASGI HTTP server for MCP endpoints
- **Breaking Scenario**: Server cannot start, no HTTP interface
- **Dependents**: `main.py` (entry point)
- **Alternatives**: ✅ Hypercorn, Daphne (both ASGI-compliant)
- **Mitigation**: Use standard ASGI interface, easy to swap
- **Current Version**: 0.32.1+

#### `starlette` (>=0.41.3)
- **Impact**: 🔴 **CRITICAL - Complete System Failure**
- **Usage**: ASGI framework for `/health`, `/metrics` endpoints
- **Breaking Scenario**: HTTP endpoints fail, monitoring unavailable
- **Dependents**: `main.py` (middleware, routing)
- **Alternatives**: ✅ FastAPI (includes Starlette), raw ASGI
- **Mitigation**: Minimal usage, low breaking risk
- **Current Version**: 0.41.3+

#### `pydantic` (>=2.10.3)
- **Impact**: 🟠 **HIGH - Input Validation Failure**
- **Usage**: Input schema validation for all MCP tools
- **Breaking Scenario**: Invalid inputs pass through, data corruption
- **Dependents**: `main.py` (all tool input models)
- **Alternatives**: ✅ marshmallow, dataclasses + custom validation
- **Mitigation**: Extensive input validation tests
- **Current Version**: 2.10.3+

#### `supabase` (>=2.10.0)
- **Impact**: 🔴 **CRITICAL - Data Persistence Failure**
- **Usage**: Database client, authentication service
- **Breaking Scenario**: Cannot read/write data, auth fails
- **Dependents**: `main.py`, `auth.py`, `dashboard.jsx` (frontend)
- **Alternatives**: ⚠️ Direct PostgreSQL (psycopg2) + custom auth layer
- **Mitigation**:
  - Implement database abstraction layer (DAL)
  - Add mock mode for development/testing
  - Consider multi-region Supabase setup
- **Current Version**: 2.10.0+
- **⚠️ Single Point of Failure**: Used in both backend AND frontend

### 1.2 React Frontend

#### `react` (^19.1.1)
- **Impact**: 🔴 **CRITICAL - Complete UI Failure**
- **Usage**: Core UI framework for all components
- **Breaking Scenario**: Application cannot render
- **Dependents**: All `.jsx` components
- **Alternatives**: ❌ None (complete rewrite required)
- **Mitigation**:
  - Pin to minor version
  - Monitor React 19 stability (recently released)
  - Avoid experimental features
- **Current Version**: 19.1.1
- **⚠️ Risk**: React 19 is new, potential for breaking changes

#### `react-dom` (^19.1.1)
- **Impact**: 🔴 **CRITICAL - Complete UI Failure**
- **Usage**: DOM rendering layer
- **Breaking Scenario**: Cannot mount React components to DOM
- **Dependents**: `index.jsx` (both dashboards)
- **Alternatives**: ❌ None (React-specific)
- **Mitigation**: Always upgrade with `react` core
- **Current Version**: 19.1.1

#### `@supabase/supabase-js` (^2.48.1)
- **Impact**: 🔴 **CRITICAL - Real-time Updates Failure**
- **Usage**: Real-time database subscriptions (pickups, emergencies)
- **Breaking Scenario**: Dashboard stops updating in real-time
- **Dependents**: `dashboard.jsx` (allobye-dashboard)
- **Alternatives**: ✅ WebSocket + custom real-time logic
- **Mitigation**:
  - Implement fallback polling mechanism
  - Add connection state management
  - Test WebSocket resilience
- **Current Version**: 2.48.1

---

## 2. High-Priority Dependencies - Tier 2 (Major Feature Loss)

These dependencies are critical for specific features but the system could degrade gracefully.

### 2.1 Python Backend

#### `psycopg2-binary` (>=2.9.9)
- **Impact**: 🟠 **HIGH - Schema Migration Failure**
- **Usage**: PostgreSQL adapter for `apply_schema.py`
- **Breaking Scenario**: Cannot initialize or migrate database
- **Dependents**: `apply_schema.py` (standalone script)
- **Alternatives**: ✅ psycopg3, asyncpg
- **Mitigation**: Keep migrations in SQL files for portability
- **Current Version**: 2.9.9+

### 2.2 React Frontend

#### `vite` (^7.1.1)
- **Impact**: 🟠 **HIGH - Build Failure**
- **Usage**: Build tool and dev server
- **Breaking Scenario**: Cannot build production assets
- **Dependents**: Build pipeline only (not runtime)
- **Alternatives**: ✅ webpack, esbuild, rollup
- **Mitigation**: Lock to stable version, maintain build scripts
- **Current Version**: 7.1.1

---

## 3. Medium-Priority Dependencies - Tier 3 (Configuration/Utilities)

These dependencies are important but have easy alternatives or graceful degradation paths.

#### `dotenv` (>=1.0.0)
- **Impact**: 🟡 **MEDIUM - Configuration Failure**
- **Usage**: Load environment variables from `.env`
- **Breaking Scenario**: Manual environment config required
- **Dependents**: `main.py`, `auth.py`, `apply_schema.py`
- **Alternatives**: ✅ Manual `os.environ`, system env vars
- **Mitigation**: Document all required environment variables
- **Current Version**: 1.0.0+

#### `httpx` (>=0.28.1)
- **Impact**: 🟡 **MEDIUM - HTTP Client Failure**
- **Usage**: HTTP client for external API calls (if any)
- **Breaking Scenario**: External integrations fail
- **Dependents**: Not explicitly used in analyzed files
- **Alternatives**: ✅ requests, urllib
- **Mitigation**: Verify actual usage, consider removal if unused
- **Current Version**: 0.28.1+
- **⚠️ Potentially Unused**: Requires full codebase verification

---

## 4. Shared/Internal Critical Modules

These are **internal dependencies** that, if broken, would cascade failures across the system.

### 4.1 Python Backend

#### `monitoring.py`
- **Impact**: 🟠 **HIGH - Observability Loss**
- **Usage**: Structured logging, metrics, alerting
- **Breaking Scenario**: Cannot debug issues, no performance insights
- **Dependents**: `main.py`, `test_monitoring.py`
- **Coupling**: ✅ **Very Low** (stdlib only)
- **Strengths**:
  - Highly portable (no external deps)
  - Could be extracted to separate package
  - Easy to test and maintain
- **Mitigation**: Keep as decoupled as possible

#### `auth.py`
- **Impact**: 🔴 **CRITICAL - Authentication Failure**
- **Usage**: User signup, login, session management
- **Breaking Scenario**: No access control, security breach
- **Dependents**: `main.py` (all protected tools)
- **Coupling**: 🟠 **Medium** (depends on Supabase)
- **Mitigation**:
  - Add fallback auth mechanism
  - Implement JWT validation without Supabase
  - Add extensive security tests

### 4.2 React Frontend

#### `use-openai-global.jsx` (Shared Hook)
- **Impact**: 🔴 **CRITICAL - MCP Integration Failure**
- **Usage**: Bridge to ChatGPT Apps SDK, tool invocation
- **Breaking Scenario**: Cannot call MCP tools from UI
- **Dependents**: `dashboard.jsx` (allobye-dashboard)
- **Coupling**: 🔴 **High** (ChatGPT Apps SDK)
- **Mitigation**:
  - Document hook API thoroughly
  - Add error handling and retry logic
  - Implement mock mode for testing

#### `use-widget-state.jsx` (Shared Hook)
- **Impact**: 🟡 **MEDIUM - State Persistence Loss**
- **Usage**: Persist widget state across sessions
- **Breaking Scenario**: User preferences reset on reload
- **Dependents**: `dashboard.jsx` (allobye-dashboard)
- **Coupling**: 🟢 **Low**
- **Mitigation**: Keep logic simple, localStorage fallback

---

## 5. Dependency Chain Analysis

### Critical Chain #1: MCP Protocol Stack
```
main.py → fastmcp → mcp → uvicorn → starlette
```
**Risk**: Entire chain must work for system to function
**Mitigation**: Pin all versions, extensive integration tests
**Fallback**: ❌ None (complete rewrite required)

### Critical Chain #2: Data Persistence
```
main.py → supabase (Python) ← → dashboard.jsx → @supabase/supabase-js
```
**Risk**: Supabase is single point of failure for both backend and frontend
**Mitigation**:
- Implement database abstraction layer
- Add connection pooling and retry logic
- Consider read replicas for high availability
**Fallback**: ✅ Direct PostgreSQL + REST API

### Critical Chain #3: Real-time Updates
```
dashboard.jsx → @supabase/supabase-js → Supabase Real-time
```
**Risk**: Loss of real-time updates breaks core UX
**Mitigation**:
- Implement polling fallback
- Add WebSocket health checks
- Show connection status to users
**Fallback**: ✅ HTTP polling (degraded UX)

---

## 6. Breaking Change Scenarios & Recovery Plans

### Scenario 1: Supabase Outage
**Probability**: Low (managed service with SLA)
**Impact**: 🔴 Complete data layer failure

**Recovery Plan**:
1. Activate mock mode in `main.py` (already implemented)
2. Use in-memory data for demo/testing
3. Implement connection retry with exponential backoff
4. Long-term: Deploy read replicas, multi-region setup

**Estimated Recovery Time**:
- With mock mode: 0 minutes (automatic)
- With replica: 5-15 minutes (manual failover)

### Scenario 2: MCP Protocol Breaking Change
**Probability**: Medium (evolving protocol)
**Impact**: 🔴 All tools stop working

**Recovery Plan**:
1. Pin fastmcp and mcp versions in requirements.txt
2. Monitor MCP protocol changelog
3. Test against new versions in staging
4. Maintain compatibility layer

**Estimated Recovery Time**:
- With pinned versions: 0 minutes (no impact)
- With breaking change: 4-8 hours (code updates)

### Scenario 3: React 19 Breaking Changes
**Probability**: Medium (new major version)
**Impact**: 🔴 UI components fail to render

**Recovery Plan**:
1. Use React 19 in strict mode to catch issues early
2. Avoid experimental features
3. Maintain automated UI tests
4. Keep components simple and idiomatic

**Estimated Recovery Time**:
- With good tests: 2-4 hours (fix components)
- Without tests: 8-16 hours (manual testing)

---

## 7. Recommendations

### Immediate Actions (Week 1)
1. ✅ Pin all critical dependencies to exact versions
2. ✅ Add dependency update monitoring (Dependabot, Renovate)
3. ⚠️ Verify `httpx` usage or remove from requirements.txt
4. ⚠️ Implement database abstraction layer (DAL) to decouple Supabase
5. ✅ Add integration tests for MCP tool chain

### Short-term (Month 1)
1. ⚠️ Add polling fallback for real-time subscriptions
2. ⚠️ Implement connection health checks for all external services
3. ✅ Document shared hooks (`use-openai-global`, `use-widget-state`)
4. ⚠️ Add end-to-end tests for critical user flows
5. ✅ Set up monitoring alerts for dependency failures

### Long-term (Quarter 1)
1. ⚠️ Consider multi-region Supabase deployment
2. ⚠️ Evaluate alternatives to Supabase for critical features
3. ✅ Extract `monitoring.py` to separate reusable package
4. ⚠️ Implement feature flags for graceful degradation
5. ✅ Establish dependency update cadence (monthly reviews)

---

## 8. Dependency Update Policy

### Version Pinning Strategy
```python
# requirements.txt (recommended format)
fastmcp==0.8.0      # Pin exact version (critical)
mcp==1.3.0          # Pin exact version (critical)
pydantic>=2.10.3,<3.0  # Allow minor updates
supabase>=2.10.0,<3.0  # Allow minor updates
dotenv>=1.0.0       # Allow any version (stable API)
```

### Update Cadence
- **Critical dependencies**: Review weekly, update monthly
- **High-priority dependencies**: Review monthly, update quarterly
- **Medium-priority dependencies**: Review quarterly, update as needed

### Testing Requirements
- All updates must pass CI/CD pipeline
- Integration tests required for critical dependencies
- Manual QA required for major version updates

---

## 9. Metrics & Monitoring

### Dependency Health Indicators
- **Uptime**: Monitor external service availability (Supabase)
- **Latency**: Track database query times
- **Error Rate**: Alert on elevated dependency-related errors
- **Version Drift**: Alert when running >2 versions behind latest

### Alerting Thresholds
- 🔴 **Critical**: Dependency failure, immediate paging
- 🟠 **High**: Degraded performance, alert within 15 minutes
- 🟡 **Medium**: Version drift detected, daily digest

---

## 10. Conclusion

The AllôBye system has a **clean, well-architected dependency graph** with:

### ✅ Strengths
1. **No circular dependencies** - Excellent modularity
2. **Low coupling** in monitoring.py - Highly reusable
3. **Clear separation** between backend and frontend
4. **Pure presentation components** - Easy to test
5. **Mock modes** already implemented - Good testability

### ⚠️ Areas for Improvement
1. **Supabase is a SPOF** - Need abstraction layer
2. **MCP ecosystem risk** - Protocol is evolving
3. **React 19 stability** - New major version
4. **Shared hooks undocumented** - Need explicit contracts

### 🎯 Priority Focus
1. **Decouple Supabase** - Most critical architectural risk
2. **Pin MCP versions** - Protect against breaking changes
3. **Add fallback mechanisms** - Enable graceful degradation

**Overall Risk Assessment**: **MEDIUM-HIGH** (manageable with recommended actions)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Next Review**: 2025-11-18
