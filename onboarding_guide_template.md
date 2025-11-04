# Guide d'Onboarding - AllôBye School Pickup System

**Bienvenue dans l'équipe AllôBye!** 🎉

Ce guide vous accompagnera durant vos premiers jours sur le projet. Suivez les étapes dans l'ordre et cochez-les au fur et à mesure.

---

## 📋 Vue d'ensemble

**Qu'est-ce qu'AllôBye?**

AllôBye est un système de coordination de ramassage scolaire pour les écoles du Québec. Le système permet aux parents de planifier les ramassages via ChatGPT, tandis que le personnel scolaire visualise la file d'attente sur des tablettes.

**Architecture en 3 mots**: ChatGPT → MCP Server → School Tablets

**Stack technique**:
- **Backend**: Python 3.11+, FastMCP, Supabase (PostgreSQL + Auth)
- **Frontend**: React 19, Vite 7, Tailwind CSS
- **Monitoring**: Prometheus, structured logging
- **Deployment**: Railway, Render, ou Fly.io

**Votre rôle**: [À compléter par le manager]

---

## Day 0: Pre-Onboarding (À faire avant votre 1er jour)

### ✅ Accès & Comptes

- [ ] **GitHub**: Accès au repo `openai-apps-sdk-examples`
- [ ] **Supabase**: Compte créé et accès au projet
- [ ] **Slack/Teams**: Ajouté aux channels pertinents
- [ ] **Email**: Accès à la liste de distribution de l'équipe
- [ ] **Calendar**: Invitations aux meetings récurrents

**Contacts Clés**:
- Team Lead: [Nom] - [Email]
- Backend Lead: [Nom] - [Email]
- Frontend Lead: [Nom] - [Email]
- DevOps/SRE: [Nom] - [Email]

---

## Day 1: Setup & Environment

### Morning (9am - 12pm): Local Environment Setup

#### ✅ Task 1.1: Clone Repository (15 min)

```bash
# Clone repo
git clone https://github.com/your-org/openai-apps-sdk-examples.git
cd openai-apps-sdk-examples

# Check branch
git status
# Should show main or development branch

# Check recent commits
git log --oneline -10
```

**Expected**: Repository cloned successfully

---

#### ✅ Task 1.2: Install Node.js Dependencies (10 min)

```bash
# Ensure Node.js 18+ is installed
node --version  # Should be v18.x.x or higher

# Install pnpm if needed
npm install -g pnpm

# Install dependencies
pnpm install

# Verify installation
pnpm list | head -20
```

**Expected**: Dependencies installed without errors

**Troubleshooting**: If `pnpm install` fails, check Node.js version and network proxy settings.

---

#### ✅ Task 1.3: Install Python Dependencies (10 min)

```bash
# Ensure Python 3.11+ is installed
python3 --version  # Should be 3.11.x or higher

# Create virtual environment
cd allobye_server_python
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # Mac/Linux
# or
.venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Verify key packages
pip list | grep -E "(fastmcp|supabase|pydantic)"
```

**Expected**: All packages installed successfully

**Troubleshooting**: If pip fails, try `pip install --upgrade pip` first.

---

#### ✅ Task 1.4: Setup Environment Variables (15 min)

```bash
# Copy example env file
cp .env.example .env

# Open .env and fill in values
nano .env  # or your preferred editor
```

**Required Variables** (ask Team Lead for values):
```env
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGci...
SUPABASE_SERVICE_ROLE_KEY=eyJhbGci...
DATABASE_URL=postgresql://postgres:...
ENVIRONMENT=development
LOG_LEVEL=DEBUG
```

**Verification**:
```bash
# Check env variables loaded
source .env
echo $SUPABASE_URL
```

**Expected**: URL printed to console

---

#### ✅ Task 1.5: Setup Database Schema (20 min)

```bash
# Ensure you're in allobye_server_python directory
cd allobye_server_python

# Apply schema (creates all tables)
python apply_schema.py

# Apply seed data (sample data for development)
python apply_schema.py --seed

# Verify schema
python apply_schema.py --verify
```

**Expected Output**:
```
✓ Table 'schools' exists (2 rows)
✓ Table 'children' exists (4 rows)
✓ Table 'delegates' exists (3 rows)
✓ Table 'pickups' exists (5 rows)
...
✓ Schema verification complete
```

**Troubleshooting**: If connection fails, verify DATABASE_URL in `.env`.

---

#### ✅ Task 1.6: Build React Widgets (15 min)

```bash
# Return to root directory
cd ..

# Build all widgets
pnpm run build

# Verify build output
ls -la assets/allobye-*.html
```

**Expected Output**:
```
allobye-dashboard.html (generated)
allobye-monitoring.html (generated)
```

**Troubleshooting**: If build fails, check Node.js version and try `rm -rf node_modules && pnpm install`.

---

#### ✅ Task 1.7: Start MCP Server (10 min)

```bash
# Ensure virtual environment is activated
cd allobye_server_python
source .venv/bin/activate

# Start server
python main.py
```

**Expected Output**:
```json
{
  "timestamp": "2025-11-04T...",
  "level": "INFO",
  "message": "AllôBye MCP Server starting up"
}
{
  "level": "INFO",
  "message": "Supabase client initialized successfully"
}
```

Server should start on `http://localhost:8000`

---

#### ✅ Task 1.8: Verify Server Health (5 min)

**In another terminal**:
```bash
# Test health endpoint
curl http://localhost:8000/health | jq .

# Test metrics endpoint
curl http://localhost:8000/metrics | head -20
```

**Expected Health Response**:
```json
{
  "status": "healthy",
  "uptime_seconds": 10,
  "total_requests": 0,
  "database_healthy": true
}
```

**✅ Checkpoint**: If health check succeeds, your environment is ready!

---

### Afternoon (1pm - 5pm): Codebase Tour

#### ✅ Task 1.9: Read Core Documentation (60 min)

Read these documents in order:

1. **Overview** (10 min):
   - [ ] `README.md` - High-level overview
   - [ ] `QUICKSTART.md` - 15-minute quick start

2. **Architecture** (20 min):
   - [ ] `architecture_analysis.md` - Architecture patterns
   - [ ] Review ER diagram in `docs/architecture/er-diagram.png`

3. **Business Logic** (15 min):
   - [ ] `business_logic_map.md` - Business rules

4. **Technical Docs** (15 min):
   - [ ] `allobye_server_python/README.md` - MCP server details
   - [ ] `allobye_server_python/SCHEMA_DOCUMENTATION.md` - Database schema

**Quiz** (self-check understanding):
1. What are the 3 main actors in AllôBye?
2. What are the 4 main MCP tools?
3. What database is used and why?
4. What is RLS and why is it important?

<details>
<summary>Answers</summary>

1. Parent (ChatGPT user), School Staff (tablet user), Delegate (pickup person)
2. pickup-schedule-create, delegate-authorize, emergency-declare, school-dashboard-fetch
3. PostgreSQL via Supabase - for RLS, real-time, auth integration
4. Row-Level Security - ensures parents only see their data, schools only see their pickups
</details>

---

#### ✅ Task 1.10: Explore Codebase Structure (45 min)

**Use your IDE to explore** (VS Code, PyCharm, etc.):

**Backend Files**:
```bash
allobye_server_python/
├── main.py           # MCP server + tool handlers (1583 lines) - START HERE
├── auth.py           # Authentication logic (633 lines)
├── monitoring.py     # Observability system (753 lines)
├── apply_schema.py   # Database setup tool (264 lines)
├── schema.sql        # PostgreSQL schema (596 lines)
└── seed.sql          # Sample data
```

**Action Items**:
- [ ] Open `main.py` and find the `get_supabase()` function
- [ ] Find all MCP tool handlers (functions starting with `_handle_`)
- [ ] Locate the `_list_tools()` function that registers MCP tools
- [ ] Open `auth.py` and find `signup_user()` function
- [ ] Review `schema.sql` and identify the 7 core tables

**Frontend Files**:
```bash
src/
├── allobye-dashboard/
│   ├── index.jsx           # App wrapper
│   ├── dashboard.jsx       # Main dashboard (229 lines)
│   ├── pickup-card.jsx     # Pickup card component (98 lines)
│   ├── emergency-alert.jsx # Emergency banner (73 lines)
│   └── auth-screen.jsx     # Login/signup (152 lines)
└── allobye-monitoring/
    ├── dashboard.jsx       # Monitoring dashboard
    ├── metrics-grid.jsx    # Metrics display
    └── ...
```

**Action Items**:
- [ ] Open `src/allobye-dashboard/dashboard.jsx`
- [ ] Find the `useEffect` hook that sets up Supabase real-time subscription
- [ ] Locate the `getUrgencyColor()` function in `pickup-card.jsx`
- [ ] Review state management in `dashboard.jsx` (useState)

---

#### ✅ Task 1.11: Run Your First Manual Test (30 min)

**Test 1: Health Check**
```bash
curl http://localhost:8000/health | jq .
```

**Test 2: Test Auth Signup** (via curl):
```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "auth-signup",
      "arguments": {
        "email": "your.name@example.com",
        "password": "testpass123",
        "name": "Your Name",
        "role": "parent"
      }
    }
  }' | jq .
```

**Expected**: Success response with `access_token`

**Test 3: Test Auth Login**:
```bash
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "auth-login",
      "arguments": {
        "email": "your.name@example.com",
        "password": "testpass123"
      }
    }
  }' | jq .
```

**Expected**: Success with user profile + access_token

**Save this token** for next tests!

---

#### ✅ Task 1.12: Meet the Team (45 min)

**Scheduled Meeting**: 1:1 with Team Lead

**Agenda**:
- [ ] Introduction and background
- [ ] Current sprint goals
- [ ] Your first task assignment
- [ ] Questions about the codebase
- [ ] Setup access to additional tools (Jira, Figma, etc.)

**Prepare Questions**:
- What are the team's top priorities right now?
- What areas of the codebase need the most attention?
- What's the code review process?
- What's the deployment process?
- Are there any known bugs I should be aware of?

---

## Day 2: Deep Dive

### Morning (9am - 12pm): Backend Deep Dive

#### ✅ Task 2.1: Understand MCP Tool Flow (60 min)

**Goal**: Trace a complete MCP tool call from ChatGPT to database and back.

**Example**: `pickup-schedule-create` tool

**Step 1**: Find tool definition in `main.py`
```python
# In _list_tools() function (line ~743)
types.Tool(
    name="pickup-schedule-create",
    description="Planifie un ramassage...",
    inputSchema={...}
)
```

**Step 2**: Find handler
```python
# Function: _handle_pickup_schedule_create() (line ~1023)
async def _handle_pickup_schedule_create(arguments):
    # 1. Validate input (Pydantic)
    # 2. Authenticate user
    # 3. Authorize (parent owns children?)
    # 4. Detect multi-school scenario
    # 5. Call business logic
    # 6. Return MCP response
```

**Step 3**: Find business logic
```python
# Function: create_pickup_request() (line ~426)
# OR coordinate_cross_school_pickup() (line ~475)
```

**Step 4**: Trace database call
```python
# Uses Supabase client
supabase.table("pickups").insert({...}).execute()
```

**Exercise**: Draw a flow diagram on paper:
```
ChatGPT → MCP Protocol → _handle_pickup_schedule_create()
  → get_current_user() → validate_session() → Supabase Auth
  → verify_parent_owns_child() → Supabase DB query
  → create_pickup_request() → Supabase DB insert
  → Return MCP response → ChatGPT displays result
```

**✅ Checkpoint**: Can you explain the flow to someone else?

---

#### ✅ Task 2.2: Understand Authentication (45 min)

**Read**: `allobye_server_python/AUTHENTICATION.md`

**Code Exploration**:
1. Open `auth.py`
2. Find `signup_user()` function
3. Find `login_user()` function
4. Find `validate_session()` function

**Key Concepts to Understand**:
- [ ] What is Supabase Auth?
- [ ] How are JWTs used?
- [ ] What are the different user roles?
- [ ] How does RLS work with authentication?

**Exercise**: Test authentication flow
```bash
# 1. Signup (if not done)
# 2. Login (get token)
# 3. Call protected tool with token
# 4. Call protected tool without token (should fail)
```

---

#### ✅ Task 2.3: Understand Database Schema (45 min)

**Read**: `allobye_server_python/SCHEMA_DOCUMENTATION.md`

**Open**: `allobye_server_python/schema.sql`

**Tables to Study**:
1. **schools** - School information
2. **children** - Child profiles
3. **delegates** - Authorized pickup persons
4. **pickups** - Pickup requests
5. **pickup_children** - Many-to-many junction
6. **delegate_children** - Authorization junction
7. **emergencies** - Emergency notifications

**Exercise**: Answer these questions (check answers in schema.sql):
1. What's the primary key of `children`?
2. What foreign key links `children` to `schools`?
3. What are the possible values for `pickups.status`?
4. What triggers are defined on `emergencies` table?
5. What RLS policies exist on `pickups` table?

**Visual Aid**: Open ER diagram at `docs/architecture/er-diagram.png`

---

#### ✅ Task 2.4: Code Reading Session with Mentor (30 min)

**Scheduled**: 1:1 with Backend Lead or Senior Developer

**Agenda**:
- Walk through `main.py` together
- Ask questions about confusing parts
- Discuss design decisions
- Review error handling patterns

**Prepare Questions**:
- Why is the SERVICE_ROLE_KEY used instead of ANON_KEY?
- How does the mock mode work?
- Why is coordinate_cross_school_pickup() separate from create_pickup_request()?
- How are A2A messages simulated?

---

### Afternoon (1pm - 5pm): Frontend Deep Dive

#### ✅ Task 2.5: Understand React Dashboard (60 min)

**Open**: `src/allobye-dashboard/dashboard.jsx`

**Key Concepts**:
1. **State Management**: `useState` for pickup data
2. **Real-time Subscriptions**: Supabase `channel().on()`
3. **Auto-refresh**: `setInterval` every 30 seconds
4. **Filtering**: Filter by view (all, next_30min, delays)
5. **View Modes**: Timeline, List, Grid

**Exercise**: Trace data flow
```
1. Component mounts
2. useEffect runs
3. Fetches initial pickup data via MCP tool
4. Sets up Supabase real-time subscription
5. On INSERT/UPDATE/DELETE event:
   - Updates state
   - UI re-renders automatically
```

**Task**: Add a `console.log` to see real-time updates
```jsx
.on("postgres_changes", { event: "*", table: "pickups" }, (payload) => {
  console.log("Real-time update:", payload);
  // Existing merge logic
})
```

**Test**: Create a pickup via curl and watch console

---

#### ✅ Task 2.6: Understand Widget Rendering (45 min)

**Question**: How does ChatGPT render the dashboard widget?

**Answer**: Via `_meta.openai/outputTemplate` in MCP response

**Code Location**: `main.py:_embedded_widget_resource()` (line ~724)

**How it works**:
1. MCP tool returns response with `_meta` object
2. `_meta.openai/outputTemplate` contains:
   - `type: "embedded-html"`
   - `outputName: "allobye-dashboard"`
   - `resources: [{uri: "file:///path/to/dashboard.html"}]`
3. ChatGPT fetches HTML from `resources.uri`
4. Renders HTML in iframe
5. Passes `structuredContent` to widget as `window.openaiData`

**Exercise**: Trace the code
```python
# In _handle_school_dashboard_fetch():
return types.CallToolResult(
    content=[...],
    structuredContent={...},  # Data passed to widget
    _meta=_tool_meta(
        widget=AllobyeWidget.DASHBOARD  # Triggers widget rendering
    )
)
```

---

#### ✅ Task 2.7: Build & Test Widget Locally (45 min)

**Modify Dashboard**: Add a simple change

**Example**: Change header text
```jsx
// In dashboard.jsx
<h1 className="dashboard-title">
  Mon Dashboard AllôBye (Modified!) {/* <-- Add this */}
</h1>
```

**Rebuild**:
```bash
cd /path/to/repo
pnpm run build
```

**Restart MCP Server**:
```bash
cd allobye_server_python
python main.py
```

**Test**: Call `school-dashboard-fetch` tool
```bash
# Use access_token from earlier
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "school-dashboard-fetch",
      "arguments": {
        "schoolId": "school-id-from-seed",
        "accessToken": "YOUR_TOKEN_HERE"
      }
    }
  }' | jq .
```

**Expected**: Response contains widget HTML with your modification

---

#### ✅ Task 2.8: Code Review Session (30 min)

**Scheduled**: 1:1 with Frontend Lead

**Agenda**:
- Walk through dashboard.jsx
- Explain real-time subscription setup
- Discuss React best practices in this project
- Review state management approach

**Questions to Ask**:
- Why Supabase real-time instead of WebSocket from MCP?
- How is authentication handled in widgets?
- What's the render performance with 50+ pickups?
- Are there any known UI bugs?

---

## Day 3: Hands-On Development

### Morning (9am - 12pm): Your First Bug Fix

#### ✅ Task 3.1: Bug Assignment (15 min)

**Meet with Team Lead** to get assigned a starter bug.

**Recommended starter bugs**:
- [ ] Fix typo in French error message
- [ ] Improve error handling in a specific tool
- [ ] Add missing docstring to a function
- [ ] Fix spacing issue in React component

**Example Bug**: "Add docstring to `get_authorized_delegates()` function"

---

#### ✅ Task 3.2: Create Feature Branch (5 min)

```bash
# Ensure you're on main/development
git checkout main
git pull origin main

# Create feature branch
git checkout -b fix/add-docstring-get-authorized-delegates

# Verify branch
git branch
```

**Branch Naming Convention**:
- `fix/description` for bug fixes
- `feat/description` for new features
- `docs/description` for documentation
- `refactor/description` for refactoring

---

#### ✅ Task 3.3: Implement Fix (60 min)

**Example**: Add docstring to `get_authorized_delegates()`

**Before**:
```python
async def get_authorized_delegates(child_id: str) -> List[Dict[str, Any]]:
    supabase = get_supabase()
    # ... implementation
```

**After**:
```python
async def get_authorized_delegates(child_id: str) -> List[Dict[str, Any]]:
    """Fetch all active delegates authorized for a specific child.

    Returns delegates who have been granted pickup permissions for the child
    via the delegate-authorize tool. Only includes active delegates (is_active=True).

    Args:
        child_id: UUID of the child to lookup

    Returns:
        List of delegate dictionaries, each containing:
            - id (str): Delegate UUID
            - email (str): Delegate email
            - name (str): Delegate name
            - phone (str): Delegate phone number
            - permissions (List[str]): Granted permissions
            - is_active (bool): Always True (filtered)

    Raises:
        DatabaseError: If database query fails

    Example:
        >>> delegates = await get_authorized_delegates("child-uuid")
        >>> len(delegates)
        3
        >>> delegates[0]["email"]
        'grandmere@example.com'

    Note:
        This function only returns active delegates. Expired or deactivated
        delegates are excluded even if they have a record in delegate_children.
    """
    supabase = get_supabase()
    # ... existing implementation unchanged
```

**Test Your Change**:
```bash
# Run the server
python main.py

# Verify no syntax errors
# Verify function still works as expected
```

---

#### ✅ Task 3.4: Write Tests (if applicable) (30 min)

**Example**: If adding new functionality, write tests

**For docstring-only changes**: No tests needed, but verify existing functionality

**Run existing tests**:
```bash
cd allobye_server_python
python test_monitoring.py
```

---

#### ✅ Task 3.5: Commit Your Changes (15 min)

```bash
# Check status
git status

# Stage changes
git add allobye_server_python/main.py

# Commit with clear message
git commit -m "docs: add comprehensive docstring to get_authorized_delegates()

- Added full docstring with Args, Returns, Raises, Example, Note sections
- Documented return structure (dict keys and types)
- Explained is_active filtering behavior
- Added note about expired delegates exclusion

Resolves: #123 (if there's a GitHub issue)"

# Push to remote
git push origin fix/add-docstring-get-authorized-delegates
```

**Commit Message Format**:
```
<type>: <short description>

<longer description if needed>
<bullet points explaining changes>

Resolves: #<issue-number>
```

**Types**: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

---

#### ✅ Task 3.6: Create Pull Request (30 min)

**On GitHub**:
1. Navigate to repository
2. Click "Pull Requests"
3. Click "New Pull Request"
4. Select your branch
5. Fill in PR template:

```markdown
## Description

Added comprehensive docstring to `get_authorized_delegates()` function.

## Changes Made

- Added full docstring with standard sections (Args, Returns, Raises, Example, Note)
- Documented dict structure returned
- Explained filtering behavior (is_active delegates only)

## Testing

- [x] Code compiles without errors
- [x] Existing tests still pass
- [x] Function behavior unchanged
- [x] Docstring follows project template

## Screenshots (if UI change)

N/A

## Checklist

- [x] Code follows project style guide
- [x] Documentation updated
- [x] Tests pass
- [x] No new warnings
```

6. Request review from team members
7. Link to any related issues

---

### Afternoon (1pm - 5pm): Code Review & Iteration

#### ✅ Task 3.7: Address Code Review Feedback (variable time)

**When reviewer leaves comments**:
1. Read all comments thoroughly
2. Ask clarifying questions if needed
3. Make requested changes
4. Commit and push updates
5. Re-request review

**Example Feedback**:
> "Can you add an example showing what happens when no delegates are found?"

**Your Response**:
```python
    Example:
        >>> # Child with delegates
        >>> delegates = await get_authorized_delegates("child-uuid")
        >>> len(delegates)
        3

        >>> # Child with no delegates
        >>> delegates = await get_authorized_delegates("other-child")
        >>> len(delegates)
        0
        >>> # Returns empty list, not None
```

---

#### ✅ Task 3.8: Learn from Other PRs (60 min)

**Browse recent PRs** in the repo:
1. Look at 5-10 recent merged PRs
2. Note code style patterns
3. Note commit message patterns
4. Note PR description patterns
5. Note common review comments

**Questions to Consider**:
- How thorough are code reviews?
- What mistakes are commonly caught?
- How long does approval typically take?
- Are there automated checks (CI)?

---

#### ✅ Task 3.9: Pair Programming Session (optional) (60 min)

**If available**: Schedule pairing with a senior developer

**Topics**:
- Work on a feature together
- Debug an issue together
- Refactor code together
- Learn team practices

---

## Day 4-5: Independent Work

### ✅ Task 4.1: Pick Up Your First Real Task (Day 4-5)

**Options** (discuss with Team Lead):
1. **Small Feature**: Add a new MCP tool
2. **Bug Fix**: Fix a reported bug from backlog
3. **Refactoring**: Improve code quality in a module
4. **Documentation**: Write a missing guide

**Expectations**:
- Work independently but ask questions
- Commit regularly (small commits)
- Write tests for new functionality
- Update documentation

---

### ✅ Task 4.2: Daily Standups

**Attend daily standup** (typically 15 min each morning):

**Format**:
1. What did I do yesterday?
2. What will I do today?
3. Any blockers?

**Your First Standup** (Day 2):
- Yesterday: Setup environment, read documentation
- Today: Continue codebase exploration, fix first bug
- Blockers: None yet

---

### ✅ Task 4.3: Weekly Team Meeting

**Attend weekly team meeting** (typically 60 min):

**Topics**:
- Sprint planning
- Demo completed work
- Discuss roadblocks
- Prioritize upcoming work

**Your Role**:
- Listen and learn
- Ask questions
- Share progress on your onboarding

---

## Week 2: Ramp Up

### ✅ Task 5.1: Take on Larger Tasks

**By end of Week 2, you should be able to**:
- [ ] Implement a new MCP tool end-to-end
- [ ] Fix bugs independently
- [ ] Review other developers' PRs (junior level)
- [ ] Answer questions from newer team members
- [ ] Contribute to architecture discussions

---

### ✅ Task 5.2: Deep Dive into Your Area

**Choose an area to specialize** (discuss with Team Lead):
- [ ] **Backend**: MCP tools, business logic, database
- [ ] **Frontend**: React widgets, UI/UX
- [ ] **DevOps**: Deployment, monitoring, CI/CD
- [ ] **Security**: Authentication, authorization, RLS

**Become the expert** in that area

---

## Ongoing: Best Practices

### ✅ Communication

- [ ] **Ask Questions**: No question is stupid
- [ ] **Document Learnings**: Keep notes for yourself
- [ ] **Share Knowledge**: Help others when you can
- [ ] **Give Feedback**: Suggest improvements

---

### ✅ Code Quality

- [ ] **Write Tests**: For all new functionality
- [ ] **Write Docstrings**: For all new functions
- [ ] **Follow Style Guide**: Consistent with team
- [ ] **Review Your Own Code**: Before requesting review
- [ ] **Keep PRs Small**: Easier to review

---

### ✅ Continuous Learning

**Resources to Explore**:
- [ ] **MCP Protocol**: https://modelcontextprotocol.io
- [ ] **FastMCP**: https://github.com/jlowin/fastmcp
- [ ] **Supabase Docs**: https://supabase.com/docs
- [ ] **React 19 Docs**: https://react.dev
- [ ] **PostgreSQL Docs**: https://www.postgresql.org/docs/

**Weekly Learning**:
- [ ] Read one guide from `docs/guides/`
- [ ] Watch one tech talk related to stack
- [ ] Experiment with one new tool/library

---

## Appendix: Common Commands Cheatsheet

### Git

```bash
# Update your branch with main
git checkout main
git pull origin main
git checkout your-branch
git merge main

# Squash commits before merging
git rebase -i HEAD~3  # Interactive rebase last 3 commits

# Undo last commit (keep changes)
git reset --soft HEAD~1

# Stash changes temporarily
git stash
git stash pop
```

### Python (MCP Server)

```bash
# Activate virtual environment
source allobye_server_python/.venv/bin/activate

# Start server with debug logging
LOG_LEVEL=DEBUG python main.py

# Run tests
python test_monitoring.py

# Check Python syntax
python -m py_compile main.py

# Apply database schema
python apply_schema.py --verify
```

### Node.js (React Widgets)

```bash
# Install dependencies
pnpm install

# Build all widgets
pnpm run build

# Build specific widget
pnpm run build -- --filter allobye-dashboard

# Development mode (watch for changes)
pnpm run dev

# Lint code
pnpm run lint

# Format code
pnpm run format
```

### Supabase (Database)

```bash
# Connect to database
psql $DATABASE_URL

# List tables
\dt

# Describe table structure
\d pickups

# Run query
SELECT * FROM pickups LIMIT 10;

# Check RLS policies
SELECT * FROM pg_policies WHERE tablename = 'pickups';
```

### Testing

```bash
# Health check
curl http://localhost:8000/health | jq .

# Test MCP tool
curl -X POST http://localhost:8000/mcp/tools/call \
  -H "Content-Type: application/json" \
  -d '{"method": "tools/call", "params": {...}}' | jq .

# Watch logs in real-time
tail -f allobye_server_python/logs/app.log
```

---

## Appendix: Troubleshooting Common Issues

### Issue: `pnpm install` fails

**Solution**:
```bash
# Clear cache
rm -rf node_modules
rm pnpm-lock.yaml

# Reinstall
pnpm install
```

---

### Issue: Python import errors

**Solution**:
```bash
# Ensure virtual environment is activated
which python  # Should show path in .venv

# Reinstall dependencies
pip install -r requirements.txt --force-reinstall
```

---

### Issue: Database connection fails

**Solution**:
1. Check `.env` file has correct `DATABASE_URL`
2. Test connection: `psql $DATABASE_URL -c "SELECT 1;"`
3. Verify Supabase project is not paused
4. Check firewall/VPN settings

---

### Issue: Widget not rendering

**Solution**:
1. Check widget was built: `ls assets/allobye-dashboard.html`
2. Rebuild: `pnpm run build`
3. Restart MCP server: `python main.py`
4. Check MCP response has `_meta.openai/outputTemplate`

---

### Issue: Real-time updates not working

**Solution**:
1. Verify Supabase Realtime is enabled (in Supabase dashboard)
2. Check browser console for WebSocket connection
3. Verify table is in Realtime publication
4. Check RLS policies allow SELECT for your user

---

## Appendix: Who to Ask for Help

| Question Type | Contact |
|---------------|---------|
| Environment setup issues | DevOps or Team Lead |
| Python/Backend questions | Backend Lead or Senior Backend Dev |
| React/Frontend questions | Frontend Lead or Senior Frontend Dev |
| Database/SQL questions | Backend Lead or DBA |
| Authentication issues | Backend Lead (auth.py owner) |
| Deployment questions | DevOps/SRE |
| Product/business questions | Product Owner or Team Lead |
| Process questions | Team Lead |
| Urgent blockers | Team Lead (Slack) |

---

## Appendix: Success Checklist

### End of Week 1

- [ ] Environment fully setup and working
- [ ] Can run MCP server locally
- [ ] Can build React widgets
- [ ] Understand architecture at high level
- [ ] Read all core documentation
- [ ] Completed first bug fix or small task
- [ ] Created first PR
- [ ] Attended daily standups

### End of Week 2

- [ ] Can implement new MCP tool independently
- [ ] Can modify React components confidently
- [ ] Understand authentication flow deeply
- [ ] Understand database schema thoroughly
- [ ] Contributing to code reviews
- [ ] Asking fewer questions (becoming self-sufficient)

### End of Month 1

- [ ] Expert in chosen area (Backend, Frontend, DevOps)
- [ ] Can mentor newer team members
- [ ] Contributing to architecture decisions
- [ ] Fully integrated into team
- [ ] Delivering consistently on sprint commitments

---

**Welcome again to the team! 🚀**

If you have any questions during onboarding, don't hesitate to ask. Everyone started where you are now.

---

**Document Version**: 1.0
**Last Updated**: 2025-11-04
**Maintained By**: Team Lead
**Feedback**: Please suggest improvements to this guide!
