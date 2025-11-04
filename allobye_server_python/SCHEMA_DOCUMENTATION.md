# AllôBye Database Schema Documentation

## Overview

This document provides comprehensive documentation for the AllôBye database schema, designed for managing school pickup scheduling across multiple Quebec schools.

## Architecture

The schema is designed to support:

- **Multi-school coordination** - Children can be at different schools
- **Delegate authorization** - Multiple people can be authorized to pick up children
- **Emergency notifications** - Real-time alerts for delays, illness, etc.
- **Real-time updates** - School dashboards update live via Supabase real-time
- **Secure access** - Row Level Security (RLS) ensures data privacy

## Database Tables

### Core Tables

#### `schools`

Stores information about participating Quebec schools.

```sql
CREATE TABLE schools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    address TEXT,
    phone TEXT,
    email TEXT,
    timezone TEXT DEFAULT 'America/Montreal',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Fields:**
- `email` - Used for school staff authentication in RLS policies
- `timezone` - Ensures proper time handling across Quebec

**Indexes:**
- `idx_schools_name` - Fast school lookups by name

---

#### `children`

Enrolled children with parent information.

```sql
CREATE TABLE children (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    school_id UUID NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
    grade TEXT,
    parent_email TEXT NOT NULL,
    parent_name TEXT,
    parent_phone TEXT,
    medical_info TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Fields:**
- `parent_email` - Used for parent authentication in RLS policies
- `medical_info` - Important health information (allergies, conditions)
- `school_id` - Foreign key to schools table

**Indexes:**
- `idx_children_school_id` - Fast queries by school
- `idx_children_parent_email` - Quick parent lookups

---

#### `delegates`

Authorized persons who can pick up children.

```sql
CREATE TABLE delegates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    phone TEXT,
    permissions TEXT[] DEFAULT ARRAY['pickup']::TEXT[],
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Key Fields:**
- `permissions` - Array of permissions: `pickup`, `emergency_contact`, `medical_decisions`
- `is_active` - Soft delete capability
- `email` - Unique identifier and auth key

**Indexes:**
- `idx_delegates_email` - Fast delegate lookups
- `idx_delegates_is_active` - Filter active delegates

---

#### `pickups`

Scheduled pickup requests.

```sql
CREATE TABLE pickups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    pickup_person_id UUID NOT NULL REFERENCES delegates(id) ON DELETE CASCADE,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    actual_time TIMESTAMP WITH TIME ZONE,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'in_progress', 'completed', 'cancelled', 'late')),
    notes TEXT,
    eta_minutes INTEGER,
    delay_minutes INTEGER DEFAULT 0,
    cancellation_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Status Values:**
- `pending` - Pickup scheduled but not confirmed
- `confirmed` - Pickup confirmed by school
- `in_progress` - Delegate is on the way
- `completed` - Child has been picked up
- `cancelled` - Pickup cancelled
- `late` - Delegate is running late

**Key Fields:**
- `eta_minutes` - Estimated time of arrival
- `delay_minutes` - How late the delegate is
- `actual_time` - When pickup actually happened

**Indexes:**
- `idx_pickups_scheduled_time` - Fast time-based queries
- `idx_pickups_status` - Filter by status
- `idx_pickups_status_scheduled_time` - Composite index for dashboard queries

---

### Junction Tables

#### `pickup_children`

Many-to-many relationship between pickups and children (one pickup can include multiple children).

```sql
CREATE TABLE pickup_children (
    pickup_id UUID NOT NULL REFERENCES pickups(id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    checked_out BOOLEAN DEFAULT FALSE,
    checked_out_at TIMESTAMP WITH TIME ZONE,
    checked_out_by TEXT,
    PRIMARY KEY (pickup_id, child_id)
);
```

**Key Fields:**
- `checked_out` - Whether child has been released
- `checked_out_by` - Staff member who released the child

**Indexes:**
- `idx_pickup_children_child_id` - Fast child lookups
- `idx_pickup_children_checked_out` - Filter by checkout status

---

#### `delegate_children`

Many-to-many authorization relationship (delegates can pick up multiple children, children can have multiple delegates).

```sql
CREATE TABLE delegate_children (
    delegate_id UUID NOT NULL REFERENCES delegates(id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    authorized_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    authorized_by TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (delegate_id, child_id)
);
```

**Key Fields:**
- `expires_at` - Optional expiration for temporary authorizations
- `authorized_by` - Who granted the authorization
- `is_active` - Can be deactivated without deleting

**Indexes:**
- `idx_delegate_children_child_id` - Fast child lookups
- `idx_delegate_children_is_active` - Filter active authorizations

---

#### `emergencies`

Emergency notifications affecting pickups.

```sql
CREATE TABLE emergencies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    emergency_type TEXT NOT NULL CHECK (emergency_type IN ('late', 'illness', 'cancel', 'injury', 'other')),
    context TEXT NOT NULL,
    severity TEXT DEFAULT 'medium' CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    resolved BOOLEAN DEFAULT FALSE,
    resolved_at TIMESTAMP WITH TIME ZONE,
    notified_delegates UUID[],
    notified_schools UUID[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Emergency Types:**
- `late` - Delegate running late
- `illness` - Child is sick
- `cancel` - Pickup cancelled
- `injury` - Child injured
- `other` - Other emergency

**Severity Levels:**
- `low` - Minor delay
- `medium` - Standard emergency
- `high` - Urgent situation
- `critical` - Immediate attention needed

**Indexes:**
- `idx_emergencies_child_id` - Fast child lookups
- `idx_emergencies_created_at` - Time-based queries
- `idx_emergencies_resolved` - Filter active emergencies
- `idx_emergencies_type_resolved` - Composite for dashboard

---

## Row Level Security (RLS)

All tables have RLS enabled with the following access patterns:

### Parents
- Can view their own children (matched by `parent_email`)
- Can view pickups for their children
- Can view emergencies for their children
- Can view authorized delegates for their children

### School Staff
- Can view all children at their school (matched by school's `email`)
- Can view all pickups for children at their school
- Can view all emergencies at their school

### Delegates
- Can view their own profile
- Can view pickups where they are assigned
- Can view emergencies for children they're authorized for

### Service Role
- Full access to all tables (used by backend MCP server)

---

## Triggers and Automation

### 1. Auto-update `updated_at`

All tables have triggers that automatically update the `updated_at` field on every update.

```sql
CREATE TRIGGER update_pickups_updated_at
    BEFORE UPDATE ON pickups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();
```

### 2. Emergency Notifications

When an emergency is created, automatically sends a notification via `pg_notify`:

```sql
CREATE TRIGGER emergency_notification
    AFTER INSERT ON emergencies
    FOR EACH ROW
    EXECUTE FUNCTION notify_emergency();
```

The notification includes:
- Emergency ID
- Child ID
- School information
- Emergency type and severity
- Context

### 3. Pickup Status Cascade

When a pickup status changes, automatically updates related children:

```sql
CREATE TRIGGER pickup_status_cascade
    AFTER UPDATE ON pickups
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION cascade_pickup_status();
```

**Behavior:**
- `cancelled` → Uncheck all children
- `completed` → Check out any unchecked children

---

## Utility Functions

### `get_upcoming_pickups(school_id, hours_ahead)`

Get upcoming pickups for a school.

```sql
SELECT * FROM get_upcoming_pickups(
    '11111111-1111-1111-1111-111111111111',  -- school_id
    24  -- hours ahead
);
```

**Returns:**
- `pickup_id` - Pickup UUID
- `child_name` - Child's name
- `pickup_person_name` - Delegate's name
- `pickup_person_email` - Delegate's email
- `scheduled_time` - When pickup is scheduled
- `status` - Current status
- `notes` - Any notes

### `get_active_emergencies(school_id)`

Get unresolved emergencies for a school.

```sql
SELECT * FROM get_active_emergencies(
    '11111111-1111-1111-1111-111111111111'
);
```

**Returns:**
- `emergency_id` - Emergency UUID
- `child_name` - Child's name
- `emergency_type` - Type of emergency
- `severity` - Severity level
- `context` - Description
- `created_at` - When it was created

---

## Real-time Subscriptions

The following tables are configured for Supabase real-time:

### `pickups`
Subscribe to live pickup updates:

```javascript
supabase
  .channel('pickups')
  .on('postgres_changes',
      { event: '*', schema: 'public', table: 'pickups' },
      (payload) => console.log('Pickup changed:', payload)
  )
  .subscribe()
```

### `emergencies`
Subscribe to emergency alerts:

```javascript
supabase
  .channel('emergencies')
  .on('postgres_changes',
      { event: 'INSERT', schema: 'public', table: 'emergencies' },
      (payload) => alert('Emergency:', payload.new)
  )
  .subscribe()
```

### `pickup_children`
Subscribe to checkout status:

```javascript
supabase
  .channel('pickup_children')
  .on('postgres_changes',
      { event: 'UPDATE', schema: 'public', table: 'pickup_children' },
      (payload) => console.log('Checkout:', payload)
  )
  .subscribe()
```

---

## Performance Considerations

### Indexes

The schema includes strategic indexes for common query patterns:

1. **Time-based queries** - `idx_pickups_scheduled_time`
2. **Status filtering** - `idx_pickups_status`
3. **School queries** - `idx_children_school_id`
4. **Composite queries** - `idx_pickups_status_scheduled_time`

### Query Optimization

Use the utility functions instead of raw queries when possible:

❌ **Don't:**
```sql
SELECT * FROM pickups p
JOIN pickup_children pc ON p.id = pc.pickup_id
JOIN children c ON pc.child_id = c.id
WHERE c.school_id = '...' AND ...
```

✅ **Do:**
```sql
SELECT * FROM get_upcoming_pickups('school-id', 24);
```

---

## Migration and Deployment

### Initial Setup

1. **Apply schema:**
   ```bash
   python apply_schema.py
   ```

2. **Add seed data:**
   ```bash
   python apply_schema.py --seed
   ```

3. **Enable real-time:**
   ```bash
   python apply_schema.py --enable-realtime
   ```

### Verify Installation

```bash
python apply_schema.py --verify
```

This will show:
- All existing tables
- Row counts
- Schema version
- Any missing tables

### Schema Versioning

The `schema_version` table tracks migrations:

```sql
SELECT * FROM schema_version ORDER BY version DESC;
```

Current version: **1** (Initial schema)

---

## Security Best Practices

### 1. Never Expose Service Role Key

The service role key bypasses RLS. Only use it server-side:

```python
# ✅ Good - Server-side only
os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# ❌ Bad - Never in frontend
const key = "eyJhbGci..."
```

### 2. Use Anon Key in Frontend

Frontend applications should use the anon key:

```javascript
const supabase = createClient(
  process.env.SUPABASE_URL,
  process.env.SUPABASE_ANON_KEY  // ✅ Safe for public
)
```

### 3. Rely on RLS Policies

Don't implement authorization in application code. Let Supabase RLS handle it:

```javascript
// ✅ Good - RLS filters automatically
const { data } = await supabase.from('children').select('*')

// ❌ Bad - Manual filtering
const { data } = await supabase.from('children').select('*')
const filtered = data.filter(c => c.parent_email === userEmail)
```

### 4. Validate User Identity

Always authenticate users before operations:

```javascript
const { data: { user } } = await supabase.auth.getUser()
if (!user) throw new Error('Not authenticated')
```

---

## Common Queries

### Get all pickups for a parent

```sql
SELECT p.*, c.name as child_name
FROM pickups p
JOIN pickup_children pc ON p.id = pc.pickup_id
JOIN children c ON pc.child_id = c.id
WHERE c.parent_email = 'parent@example.com'
AND p.scheduled_time > NOW()
ORDER BY p.scheduled_time;
```

### Get authorized delegates for a child

```sql
SELECT d.*
FROM delegates d
JOIN delegate_children dc ON d.id = dc.delegate_id
WHERE dc.child_id = 'child-uuid'
AND dc.is_active = TRUE;
```

### Get today's pickups for a school

```sql
SELECT p.*, c.name, d.name as delegate_name
FROM pickups p
JOIN pickup_children pc ON p.id = pc.pickup_id
JOIN children c ON pc.child_id = c.id
JOIN delegates d ON p.pickup_person_id = d.id
WHERE c.school_id = 'school-uuid'
AND p.scheduled_time::date = CURRENT_DATE
ORDER BY p.scheduled_time;
```

---

## Troubleshooting

### RLS Blocking Queries?

Check if you're using the correct auth context:

```sql
-- See current auth context
SELECT current_setting('request.jwt.claims', true);

-- Temporarily disable RLS (admin only)
ALTER TABLE children DISABLE ROW LEVEL SECURITY;
```

### Real-time Not Working?

1. Verify publication exists:
   ```sql
   SELECT * FROM pg_publication WHERE pubname = 'supabase_realtime';
   ```

2. Check table is in publication:
   ```sql
   SELECT * FROM pg_publication_tables WHERE pubname = 'supabase_realtime';
   ```

3. Enable in Supabase dashboard:
   - Go to Database → Replication
   - Enable realtime for tables

### Slow Queries?

Check if indexes are being used:

```sql
EXPLAIN ANALYZE
SELECT * FROM pickups WHERE scheduled_time > NOW();
```

---

## Support

For issues or questions:
- GitHub: https://github.com/your-org/allobye
- Email: support@allobye.ca
- Docs: https://docs.allobye.ca
