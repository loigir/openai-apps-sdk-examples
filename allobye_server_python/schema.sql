-- ═══════════════════════════════════════════════════════════════
-- AllôBye Database Schema
-- Supabase database schema for school pickup scheduling system
-- ═══════════════════════════════════════════════════════════════

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Enable pgcrypto for gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ═══════════════════════════════════════════════════════════════
-- DROP EXISTING TABLES (for clean migrations)
-- ═══════════════════════════════════════════════════════════════

DROP TABLE IF EXISTS emergencies CASCADE;
DROP TABLE IF EXISTS pickup_children CASCADE;
DROP TABLE IF EXISTS delegate_children CASCADE;
DROP TABLE IF EXISTS pickups CASCADE;
DROP TABLE IF EXISTS delegates CASCADE;
DROP TABLE IF EXISTS children CASCADE;
DROP TABLE IF EXISTS schools CASCADE;

-- ═══════════════════════════════════════════════════════════════
-- CORE TABLES
-- ═══════════════════════════════════════════════════════════════

-- Schools table
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

-- Children table
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

-- Delegates (authorized pickup persons)
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

-- Pickups table
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

-- Pickup-Children junction table (many-to-many)
CREATE TABLE pickup_children (
    pickup_id UUID NOT NULL REFERENCES pickups(id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    checked_out BOOLEAN DEFAULT FALSE,
    checked_out_at TIMESTAMP WITH TIME ZONE,
    checked_out_by TEXT,
    PRIMARY KEY (pickup_id, child_id)
);

-- Delegate-Children authorization table (many-to-many)
CREATE TABLE delegate_children (
    delegate_id UUID NOT NULL REFERENCES delegates(id) ON DELETE CASCADE,
    child_id UUID NOT NULL REFERENCES children(id) ON DELETE CASCADE,
    authorized_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    authorized_by TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT TRUE,
    PRIMARY KEY (delegate_id, child_id)
);

-- Emergencies table
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

-- ═══════════════════════════════════════════════════════════════
-- INDEXES FOR PERFORMANCE
-- ═══════════════════════════════════════════════════════════════

-- Schools indexes
CREATE INDEX idx_schools_name ON schools(name);

-- Children indexes
CREATE INDEX idx_children_school_id ON children(school_id);
CREATE INDEX idx_children_parent_email ON children(parent_email);

-- Delegates indexes
CREATE INDEX idx_delegates_email ON delegates(email);
CREATE INDEX idx_delegates_is_active ON delegates(is_active);

-- Pickups indexes
CREATE INDEX idx_pickups_scheduled_time ON pickups(scheduled_time);
CREATE INDEX idx_pickups_status ON pickups(status);
CREATE INDEX idx_pickups_pickup_person_id ON pickups(pickup_person_id);
CREATE INDEX idx_pickups_status_scheduled_time ON pickups(status, scheduled_time);

-- PERFORMANCE OPTIMIZATION: Add composite index for time-range queries
CREATE INDEX idx_pickups_time_range ON pickups(scheduled_time DESC, status) WHERE status NOT IN ('completed', 'cancelled');

-- Pickup-Children indexes
CREATE INDEX idx_pickup_children_child_id ON pickup_children(child_id);
CREATE INDEX idx_pickup_children_checked_out ON pickup_children(checked_out);
-- PERFORMANCE OPTIMIZATION: Add index on pickup_id for faster joins
CREATE INDEX idx_pickup_children_pickup_id ON pickup_children(pickup_id);

-- Delegate-Children indexes
CREATE INDEX idx_delegate_children_child_id ON delegate_children(child_id);
CREATE INDEX idx_delegate_children_is_active ON delegate_children(is_active);
-- PERFORMANCE OPTIMIZATION: Add composite index for active delegate lookups
CREATE INDEX idx_delegate_children_delegate_active ON delegate_children(delegate_id, is_active) WHERE is_active = TRUE;
-- PERFORMANCE OPTIMIZATION: Add index on delegate_id for reverse lookups
CREATE INDEX idx_delegate_children_delegate_id ON delegate_children(delegate_id);

-- Emergencies indexes
CREATE INDEX idx_emergencies_child_id ON emergencies(child_id);
CREATE INDEX idx_emergencies_created_at ON emergencies(created_at);
CREATE INDEX idx_emergencies_resolved ON emergencies(resolved);
CREATE INDEX idx_emergencies_type_resolved ON emergencies(emergency_type, resolved);

-- PERFORMANCE OPTIMIZATION: Add covering index for common queries
-- This index includes all columns typically needed for dashboard queries
CREATE INDEX idx_pickups_dashboard_covering ON pickups(scheduled_time, status, pickup_person_id, id, notes, eta_minutes, delay_minutes)
WHERE status NOT IN ('completed', 'cancelled');

-- ═══════════════════════════════════════════════════════════════
-- TRIGGERS AND FUNCTIONS
-- ═══════════════════════════════════════════════════════════════

-- Function: Update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Auto-update updated_at for schools
CREATE TRIGGER update_schools_updated_at
    BEFORE UPDATE ON schools
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Auto-update updated_at for children
CREATE TRIGGER update_children_updated_at
    BEFORE UPDATE ON children
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Auto-update updated_at for delegates
CREATE TRIGGER update_delegates_updated_at
    BEFORE UPDATE ON delegates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Auto-update updated_at for pickups
CREATE TRIGGER update_pickups_updated_at
    BEFORE UPDATE ON pickups
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Trigger: Auto-update updated_at for emergencies
CREATE TRIGGER update_emergencies_updated_at
    BEFORE UPDATE ON emergencies
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Function: Notify on emergency insert
CREATE OR REPLACE FUNCTION notify_emergency()
RETURNS TRIGGER AS $$
DECLARE
    school_id UUID;
    school_name TEXT;
BEGIN
    -- Get school information for the affected child
    SELECT c.school_id, s.name INTO school_id, school_name
    FROM children c
    JOIN schools s ON c.school_id = s.id
    WHERE c.id = NEW.child_id;

    -- Send notification via pg_notify
    PERFORM pg_notify(
        'emergency_alert',
        json_build_object(
            'emergency_id', NEW.id,
            'child_id', NEW.child_id,
            'school_id', school_id,
            'school_name', school_name,
            'type', NEW.emergency_type,
            'severity', NEW.severity,
            'context', NEW.context,
            'created_at', NEW.created_at
        )::text
    );

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Notify on emergency insert
CREATE TRIGGER emergency_notification
    AFTER INSERT ON emergencies
    FOR EACH ROW
    EXECUTE FUNCTION notify_emergency();

-- Function: Cascade pickup status changes
CREATE OR REPLACE FUNCTION cascade_pickup_status()
RETURNS TRIGGER AS $$
BEGIN
    -- If pickup is cancelled, mark all children as not checked out
    IF NEW.status = 'cancelled' AND OLD.status != 'cancelled' THEN
        UPDATE pickup_children
        SET checked_out = FALSE,
            checked_out_at = NULL,
            checked_out_by = NULL
        WHERE pickup_id = NEW.id;
    END IF;

    -- If pickup is completed, ensure all children are checked out
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        UPDATE pickup_children
        SET checked_out = TRUE,
            checked_out_at = COALESCE(checked_out_at, NOW())
        WHERE pickup_id = NEW.id AND checked_out = FALSE;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger: Cascade pickup status changes
CREATE TRIGGER pickup_status_cascade
    AFTER UPDATE ON pickups
    FOR EACH ROW
    WHEN (OLD.status IS DISTINCT FROM NEW.status)
    EXECUTE FUNCTION cascade_pickup_status();

-- ═══════════════════════════════════════════════════════════════
-- ROW LEVEL SECURITY (RLS) POLICIES
-- ═══════════════════════════════════════════════════════════════

-- Enable RLS on all tables
ALTER TABLE schools ENABLE ROW LEVEL SECURITY;
ALTER TABLE children ENABLE ROW LEVEL SECURITY;
ALTER TABLE delegates ENABLE ROW LEVEL SECURITY;
ALTER TABLE pickups ENABLE ROW LEVEL SECURITY;
ALTER TABLE pickup_children ENABLE ROW LEVEL SECURITY;
ALTER TABLE delegate_children ENABLE ROW LEVEL SECURITY;
ALTER TABLE emergencies ENABLE ROW LEVEL SECURITY;

-- ═══════════════════════════════════════════════════════════════
-- RLS POLICIES: Schools
-- ═══════════════════════════════════════════════════════════════

-- Allow public read access to schools
CREATE POLICY "Schools are viewable by everyone"
    ON schools FOR SELECT
    USING (true);

-- Allow service role to manage schools
CREATE POLICY "Service role can manage schools"
    ON schools FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- ═══════════════════════════════════════════════════════════════
-- RLS POLICIES: Children
-- ═══════════════════════════════════════════════════════════════

-- Parents can view their own children
CREATE POLICY "Parents can view their own children"
    ON children FOR SELECT
    USING (parent_email = auth.jwt()->>'email');

-- School staff can view children at their school
CREATE POLICY "School staff can view children at their school"
    ON children FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM schools
            WHERE schools.id = children.school_id
            AND schools.email = auth.jwt()->>'email'
        )
    );

-- Service role can manage all children
CREATE POLICY "Service role can manage children"
    ON children FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- ═══════════════════════════════════════════════════════════════
-- RLS POLICIES: Delegates
-- ═══════════════════════════════════════════════════════════════

-- Delegates can view their own profile
CREATE POLICY "Delegates can view their own profile"
    ON delegates FOR SELECT
    USING (email = auth.jwt()->>'email');

-- Parents can view delegates authorized for their children
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

-- Service role can manage delegates
CREATE POLICY "Service role can manage delegates"
    ON delegates FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- ═══════════════════════════════════════════════════════════════
-- RLS POLICIES: Pickups
-- ═══════════════════════════════════════════════════════════════

-- Parents can view pickups for their children
CREATE POLICY "Parents can view their children's pickups"
    ON pickups FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pickup_children pc
            JOIN children c ON pc.child_id = c.id
            WHERE pc.pickup_id = pickups.id
            AND c.parent_email = auth.jwt()->>'email'
        )
    );

-- Delegates can view pickups where they are the pickup person
CREATE POLICY "Delegates can view their assigned pickups"
    ON pickups FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM delegates
            WHERE delegates.id = pickups.pickup_person_id
            AND delegates.email = auth.jwt()->>'email'
        )
    );

-- School staff can view all pickups for children at their school
CREATE POLICY "School staff can view school pickups"
    ON pickups FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM pickup_children pc
            JOIN children c ON pc.child_id = c.id
            JOIN schools s ON c.school_id = s.id
            WHERE pc.pickup_id = pickups.id
            AND s.email = auth.jwt()->>'email'
        )
    );

-- Service role can manage all pickups
CREATE POLICY "Service role can manage pickups"
    ON pickups FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- ═══════════════════════════════════════════════════════════════
-- RLS POLICIES: Pickup Children
-- ═══════════════════════════════════════════════════════════════

-- Follow same patterns as pickups table
CREATE POLICY "Parents can view pickup_children for their children"
    ON pickup_children FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM children c
            WHERE c.id = pickup_children.child_id
            AND c.parent_email = auth.jwt()->>'email'
        )
    );

CREATE POLICY "Service role can manage pickup_children"
    ON pickup_children FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- ═══════════════════════════════════════════════════════════════
-- RLS POLICIES: Delegate Children
-- ═══════════════════════════════════════════════════════════════

-- Parents can view delegate authorizations for their children
CREATE POLICY "Parents can view delegate_children for their children"
    ON delegate_children FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM children c
            WHERE c.id = delegate_children.child_id
            AND c.parent_email = auth.jwt()->>'email'
        )
    );

-- Delegates can view their authorizations
CREATE POLICY "Delegates can view their authorizations"
    ON delegate_children FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM delegates d
            WHERE d.id = delegate_children.delegate_id
            AND d.email = auth.jwt()->>'email'
        )
    );

CREATE POLICY "Service role can manage delegate_children"
    ON delegate_children FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- ═══════════════════════════════════════════════════════════════
-- RLS POLICIES: Emergencies
-- ═══════════════════════════════════════════════════════════════

-- Parents can view emergencies for their children
CREATE POLICY "Parents can view emergencies for their children"
    ON emergencies FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM children c
            WHERE c.id = emergencies.child_id
            AND c.parent_email = auth.jwt()->>'email'
        )
    );

-- Authorized delegates can view emergencies for children they're authorized for
CREATE POLICY "Delegates can view emergencies for authorized children"
    ON emergencies FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM delegate_children dc
            JOIN delegates d ON dc.delegate_id = d.id
            WHERE dc.child_id = emergencies.child_id
            AND d.email = auth.jwt()->>'email'
            AND dc.is_active = TRUE
        )
    );

-- School staff can view emergencies for children at their school
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

CREATE POLICY "Service role can manage emergencies"
    ON emergencies FOR ALL
    USING (auth.jwt()->>'role' = 'service_role')
    WITH CHECK (auth.jwt()->>'role' = 'service_role');

-- ═══════════════════════════════════════════════════════════════
-- REAL-TIME PUBLICATION
-- ═══════════════════════════════════════════════════════════════

-- Enable real-time for pickups and emergencies tables
-- Note: In Supabase dashboard, you need to enable realtime for these tables
-- This is done via: Database > Replication > Enable realtime for table

-- For reference, the SQL command would be:
-- ALTER PUBLICATION supabase_realtime ADD TABLE pickups;
-- ALTER PUBLICATION supabase_realtime ADD TABLE emergencies;
-- ALTER PUBLICATION supabase_realtime ADD TABLE pickup_children;

-- ═══════════════════════════════════════════════════════════════
-- UTILITY FUNCTIONS
-- ═══════════════════════════════════════════════════════════════

-- Function: Get upcoming pickups for a school
CREATE OR REPLACE FUNCTION get_upcoming_pickups(
    p_school_id UUID,
    p_hours_ahead INTEGER DEFAULT 24
)
RETURNS TABLE (
    pickup_id UUID,
    child_name TEXT,
    pickup_person_name TEXT,
    pickup_person_email TEXT,
    scheduled_time TIMESTAMP WITH TIME ZONE,
    status TEXT,
    notes TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        p.id AS pickup_id,
        c.name AS child_name,
        d.name AS pickup_person_name,
        d.email AS pickup_person_email,
        p.scheduled_time,
        p.status,
        p.notes
    FROM pickups p
    JOIN pickup_children pc ON p.id = pc.pickup_id
    JOIN children c ON pc.child_id = c.id
    JOIN delegates d ON p.pickup_person_id = d.id
    WHERE c.school_id = p_school_id
    AND p.scheduled_time BETWEEN NOW() AND NOW() + (p_hours_ahead || ' hours')::INTERVAL
    AND p.status NOT IN ('completed', 'cancelled')
    ORDER BY p.scheduled_time ASC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Function: Get active emergencies for a school
CREATE OR REPLACE FUNCTION get_active_emergencies(p_school_id UUID)
RETURNS TABLE (
    emergency_id UUID,
    child_name TEXT,
    emergency_type TEXT,
    severity TEXT,
    context TEXT,
    created_at TIMESTAMP WITH TIME ZONE
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        e.id AS emergency_id,
        c.name AS child_name,
        e.emergency_type,
        e.severity,
        e.context,
        e.created_at
    FROM emergencies e
    JOIN children c ON e.child_id = c.id
    WHERE c.school_id = p_school_id
    AND e.resolved = FALSE
    ORDER BY e.created_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- ═══════════════════════════════════════════════════════════════
-- COMMENTS AND DOCUMENTATION
-- ═══════════════════════════════════════════════════════════════

COMMENT ON TABLE schools IS 'Quebec schools participating in the AllôBye system';
COMMENT ON TABLE children IS 'Children enrolled in participating schools';
COMMENT ON TABLE delegates IS 'Authorized persons who can pick up children';
COMMENT ON TABLE pickups IS 'Scheduled pickup requests';
COMMENT ON TABLE pickup_children IS 'Many-to-many relationship between pickups and children';
COMMENT ON TABLE delegate_children IS 'Authorization relationship between delegates and children';
COMMENT ON TABLE emergencies IS 'Emergency notifications affecting pickups';

COMMENT ON COLUMN pickups.status IS 'Pickup status: pending, confirmed, in_progress, completed, cancelled, late';
COMMENT ON COLUMN emergencies.emergency_type IS 'Emergency type: late, illness, cancel, injury, other';
COMMENT ON COLUMN emergencies.severity IS 'Severity level: low, medium, high, critical';

-- ═══════════════════════════════════════════════════════════════
-- SCHEMA VERSION
-- ═══════════════════════════════════════════════════════════════

CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    description TEXT
);

INSERT INTO schema_version (version, description)
VALUES (1, 'Initial AllôBye schema with RLS, triggers, and real-time support')
ON CONFLICT (version) DO NOTHING;
