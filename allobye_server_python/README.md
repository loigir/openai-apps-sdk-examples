# AllôBye × ChatGPT Apps SDK - MCP Server

**Pickup scheduling, delegate authorization, and emergency notifications for Quebec schools**

## Architecture Overview

```
Parent (ChatGPT) → MCP Tools → Supabase Backend → School Dashboards (React)
                       ↓
            Multi-School Coordination (A2A)
```

### Components

- **Parent Agent**: ChatGPT conversation (mobile/desktop)
- **Orchestrator**: ChatGPT reasoning + MCP tools (this server)
- **Display Agent**: React widget (fullscreen school tablets)

## MCP Tools Provided

### 1. `pickup-schedule-create`
Schedule pickups for one or more children. Automatically handles multi-school coordination.

**Input:**
```json
{
  "childIds": ["child_123", "child_456"],
  "pickupPersonId": "delegate_789",
  "scheduledTime": "2025-11-04T15:00:00-05:00",
  "notes": "Dentist appointment"
}
```

**Example Conversation:**
```
Parent: "Ma mère va chercher Sophie et Thomas à 15h aujourd'hui"
ChatGPT: ✓ Ramassage confirmé pour 2 enfants à 15:00
```

### 2. `delegate-authorize`
Authorize a person to pick up children. Auto-syncs across all affected schools.

**Input:**
```json
{
  "delegateEmail": "grandmaman@example.com",
  "childIds": ["child_123"],
  "permissions": ["pickup", "emergency_contact"],
  "schools": null  // Auto-inferred from children
}
```

### 3. `emergency-declare`
Declare an emergency affecting pickup. Cascades to all delegates and schools.

**Input:**
```json
{
  "childId": "child_123",
  "emergencyType": "late",  // late | illness | cancel | other
  "context": "20 minutes de retard - traffic",
  "notifyAllDelegates": true
}
```

### 4. `school-dashboard-fetch`
Fetch current pickup queue for school tablet display. Returns React widget.

**Input:**
```json
{
  "schoolId": "school_1",
  "date": null,  // Defaults to today
  "timeWindow": "current"  // current (30min) | today | custom
}
```

## Setup

### 1. Install Dependencies

```bash
cd allobye_server_python
pip install -r requirements.txt
```

### 2. Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required variables:
```env
SUPABASE_URL=https://uiuyivgbpallzgqzlatb.supabase.co
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
DATABASE_URL=postgresql://postgres:password@db.supabase.co:5432/postgres
```

### 3. Database Schema

AllôBye uses a complete Supabase schema with Row Level Security (RLS), triggers, and real-time support.

#### Quick Setup

```bash
# Apply schema and seed data
python apply_schema.py --seed

# Apply schema only
python apply_schema.py

# Verify existing schema
python apply_schema.py --verify

# Enable real-time replication
python apply_schema.py --enable-realtime
```

#### Schema Overview

The database consists of 7 main tables with proper relationships:

**Core Tables:**
- `schools` - Quebec schools in the system
- `children` - Enrolled children with parent info
- `delegates` - Authorized pickup persons
- `pickups` - Scheduled pickup requests
- `emergencies` - Emergency notifications

**Junction Tables:**
- `pickup_children` - Links pickups to multiple children
- `delegate_children` - Links delegates to authorized children

#### Key Features

**1. Row Level Security (RLS)**

All tables have RLS policies to ensure data privacy:

- Parents can only see their own children's data
- School staff can see all data for their school
- Delegates can see pickups where they're authorized
- Service role has full access for backend operations

**2. Automatic Triggers**

- `updated_at` auto-updates on all tables
- Emergency notifications via `pg_notify`
- Cascade updates when pickup status changes

**3. Real-time Support**

Tables enabled for Supabase real-time:
- `pickups` - Live pickup queue updates
- `emergencies` - Instant emergency alerts
- `pickup_children` - Check-out status changes

**4. Performance Indexes**

Optimized queries with indexes on:
- `scheduled_time` - Fast pickup lookups
- `status` - Quick filtering
- `school_id` - Efficient school queries

#### Schema Files

- `schema.sql` - Complete database schema (760 lines)
- `seed.sql` - Sample data for development
- `apply_schema.py` - Python script to apply schema

#### Utility Functions

The schema includes helper functions:

```sql
-- Get upcoming pickups for a school
SELECT * FROM get_upcoming_pickups('school-id', 24);

-- Get active emergencies
SELECT * FROM get_active_emergencies('school-id');
```

#### Sample Data

The seed includes:
- 2 schools (Saint-Jean-Baptiste, Notre-Dame-de-Grâce)
- 4 children (2 per school)
- 3 delegates (grandmaman, papa, tante)
- 5 pickups (various states)
- 2 emergencies (1 active, 1 resolved)

See `seed.sql` for complete data.

### 4. Run the Server

```bash
# Development mode (auto-reload)
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Server will be available at: `http://localhost:8000`

### 5. Build React Widgets

```bash
cd ..
pnpm install
pnpm run build
```

This generates the school dashboard widget HTML in `assets/allobye-dashboard.html`.

## Connecting to ChatGPT

### Option 1: Local Development

1. Run the server: `python main.py`
2. Use ngrok or similar for HTTPS tunnel:
   ```bash
   ngrok http 8000
   ```
3. In ChatGPT, go to Settings > Connectors
4. Add MCP URL: `https://your-ngrok-url.ngrok.io/mcp`

### Option 2: Production Deployment

Deploy to:
- **Railway**: `railway up`
- **Render**: Connect GitHub repo
- **Fly.io**: `fly deploy`

Then add production URL to ChatGPT connectors.

## Usage Examples

### Example 1: Schedule Pickup

```
User: "Mon conjoint va chercher les enfants à 16h30 demain"

ChatGPT calls:
- Identifies children from context
- Resolves "conjoint" to delegate ID
- Calls pickup-schedule-create
- Confirms across all schools

Response: "✓ Ramassage confirmé pour 2 enfants à 16:30"
```

### Example 2: Emergency Late

```
User: "Je suis pogné dans le trafic, je vais être en retard de 15 minutes"

ChatGPT calls:
- Identifies active pickup
- Calls emergency-declare
- Notifies all delegates + schools

Response: "🚨 Urgence déclarée. 3 délégués et 1 école notifiés."
```

### Example 3: School Dashboard

```
School tablet requests dashboard:

ChatGPT calls:
- school-dashboard-fetch
- Returns React widget with:
  - Real-time pickup queue
  - Next 30 min schedule
  - Emergency alerts

Widget auto-refreshes every 30s via Supabase realtime.
```

## Real-time Features

The school dashboard widget subscribes to Supabase real-time for:

1. **Pickup Changes**: New pickups, status updates, cancellations
2. **Emergency Alerts**: Instant notifications with visual/audio alerts
3. **Auto-refresh**: 30-second polling fallback

## Development Mode

When Supabase is not configured, the server returns mock data:

- Sample schools, children, delegates
- Simulated pickup queue
- Mock A2A coordination responses

This allows frontend development without backend dependencies.

## Troubleshooting

### "Supabase client initialization failed"

Ensure environment variables are set:
```bash
echo $SUPABASE_URL
echo $SUPABASE_SERVICE_ROLE_KEY
```

### "Widget not built yet"

Run the build:
```bash
pnpm run build
```

### CORS errors

The server includes CORS middleware. For production, restrict origins:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://chatgpt.com"],  # Restrict to ChatGPT
    ...
)
```

## Architecture: A2A Integration

The MCP tools wrap Agent-to-Agent (A2A) calls internally:

```python
async def coordinate_cross_school_pickup(...):
    # Group children by school
    schools_map = group_children_by_school(child_ids)

    # Broadcast via A2A (future: NATS)
    for school_id, children in schools_map.items():
        message = {
            "type": "multi_school_pickup_request",
            ...
        }
        response = await a2a_bus.request(f"orchestrator.{school_id}", message)

    return aggregate_results(results)
```

## Security

- ✅ Service role key used server-side only
- ✅ RLS policies on Supabase tables
- ✅ Email-based authentication (Supabase Auth)
- ✅ HTTPS required for production
- ⚠️ Add rate limiting for production

## License

MIT - See LICENSE file

## Support

Issues: https://github.com/your-org/allobye/issues
Docs: https://docs.allobye.ca
