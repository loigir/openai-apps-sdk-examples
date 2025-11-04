-- ═══════════════════════════════════════════════════════════════
-- AllôBye Seed Data
-- Sample data for development and testing
-- ═══════════════════════════════════════════════════════════════

-- Clear existing data (in reverse order of dependencies)
DELETE FROM emergencies;
DELETE FROM pickup_children;
DELETE FROM delegate_children;
DELETE FROM pickups;
DELETE FROM delegates;
DELETE FROM children;
DELETE FROM schools;

-- ═══════════════════════════════════════════════════════════════
-- SCHOOLS
-- ═══════════════════════════════════════════════════════════════

INSERT INTO schools (id, name, address, phone, email, timezone) VALUES
(
    '11111111-1111-1111-1111-111111111111',
    'École Primaire Saint-Jean-Baptiste',
    '123 Rue Principale, Montréal, QC H1A 1A1',
    '514-555-0101',
    'direction@stjb.qc.ca',
    'America/Montreal'
),
(
    '22222222-2222-2222-2222-222222222222',
    'École Primaire Notre-Dame-de-Grâce',
    '456 Avenue du Parc, Montréal, QC H4A 3B3',
    '514-555-0102',
    'admin@ndg.qc.ca',
    'America/Montreal'
);

-- ═══════════════════════════════════════════════════════════════
-- CHILDREN
-- ═══════════════════════════════════════════════════════════════

INSERT INTO children (id, name, school_id, grade, parent_email, parent_name, parent_phone, medical_info) VALUES
-- School 1 children
(
    'c1111111-1111-1111-1111-111111111111',
    'Sophie Tremblay',
    '11111111-1111-1111-1111-111111111111',
    '3e année',
    'marie.tremblay@example.com',
    'Marie Tremblay',
    '514-555-1001',
    'Allergies: arachides'
),
(
    'c2222222-2222-2222-2222-222222222222',
    'Thomas Tremblay',
    '11111111-1111-1111-1111-111111111111',
    '1re année',
    'marie.tremblay@example.com',
    'Marie Tremblay',
    '514-555-1001',
    NULL
),
-- School 2 children
(
    'c3333333-3333-3333-3333-333333333333',
    'Émilie Gagnon',
    '22222222-2222-2222-2222-222222222222',
    '4e année',
    'jean.gagnon@example.com',
    'Jean Gagnon',
    '514-555-2001',
    'Asthme - inhalateur disponible'
),
(
    'c4444444-4444-4444-4444-444444444444',
    'Lucas Gagnon',
    '22222222-2222-2222-2222-222222222222',
    '2e année',
    'jean.gagnon@example.com',
    'Jean Gagnon',
    '514-555-2001',
    NULL
);

-- ═══════════════════════════════════════════════════════════════
-- DELEGATES
-- ═══════════════════════════════════════════════════════════════

INSERT INTO delegates (id, email, name, phone, permissions, is_active) VALUES
(
    'd1111111-1111-1111-1111-111111111111',
    'grandmaman.tremblay@example.com',
    'Louise Tremblay',
    '514-555-3001',
    ARRAY['pickup', 'emergency_contact']::TEXT[],
    TRUE
),
(
    'd2222222-2222-2222-2222-222222222222',
    'papa.gagnon@example.com',
    'Jean Gagnon',
    '514-555-2001',
    ARRAY['pickup', 'emergency_contact', 'medical_decisions']::TEXT[],
    TRUE
),
(
    'd3333333-3333-3333-3333-333333333333',
    'tante.marie@example.com',
    'Marie-Claire Bouchard',
    '514-555-4001',
    ARRAY['pickup']::TEXT[],
    TRUE
);

-- ═══════════════════════════════════════════════════════════════
-- DELEGATE-CHILDREN AUTHORIZATIONS
-- ═══════════════════════════════════════════════════════════════

INSERT INTO delegate_children (delegate_id, child_id, authorized_by, is_active) VALUES
-- Grandmaman can pick up Sophie and Thomas
('d1111111-1111-1111-1111-111111111111', 'c1111111-1111-1111-1111-111111111111', 'marie.tremblay@example.com', TRUE),
('d1111111-1111-1111-1111-111111111111', 'c2222222-2222-2222-2222-222222222222', 'marie.tremblay@example.com', TRUE),
-- Papa can pick up Émilie and Lucas
('d2222222-2222-2222-2222-222222222222', 'c3333333-3333-3333-3333-333333333333', 'jean.gagnon@example.com', TRUE),
('d2222222-2222-2222-2222-222222222222', 'c4444444-4444-4444-4444-444444444444', 'jean.gagnon@example.com', TRUE),
-- Tante Marie can pick up Sophie only
('d3333333-3333-3333-3333-333333333333', 'c1111111-1111-1111-1111-111111111111', 'marie.tremblay@example.com', TRUE);

-- ═══════════════════════════════════════════════════════════════
-- PICKUPS
-- ═══════════════════════════════════════════════════════════════

-- Helper function to generate times relative to now
DO $$
DECLARE
    now_time TIMESTAMP WITH TIME ZONE := NOW();
BEGIN
    -- Pickup 1: Pending - Grandmaman picking up Sophie in 15 minutes
    INSERT INTO pickups (id, pickup_person_id, scheduled_time, status, notes, eta_minutes, delay_minutes)
    VALUES (
        'p1111111-1111-1111-1111-111111111111',
        'd1111111-1111-1111-1111-111111111111',
        now_time + INTERVAL '15 minutes',
        'pending',
        'Rendez-vous chez le dentiste',
        15,
        0
    );

    -- Pickup 2: Confirmed - Papa picking up both kids in 45 minutes
    INSERT INTO pickups (id, pickup_person_id, scheduled_time, status, notes, eta_minutes, delay_minutes)
    VALUES (
        'p2222222-2222-2222-2222-222222222222',
        'd2222222-2222-2222-2222-222222222222',
        now_time + INTERVAL '45 minutes',
        'confirmed',
        'Fin de journée normale',
        45,
        0
    );

    -- Pickup 3: Late - Tante Marie is running late
    INSERT INTO pickups (id, pickup_person_id, scheduled_time, status, notes, eta_minutes, delay_minutes)
    VALUES (
        'p3333333-3333-3333-3333-333333333333',
        'd3333333-3333-3333-3333-333333333333',
        now_time + INTERVAL '5 minutes',
        'late',
        'Retard dû au trafic',
        25,
        20
    );

    -- Pickup 4: Completed - From earlier today
    INSERT INTO pickups (id, pickup_person_id, scheduled_time, actual_time, status, notes)
    VALUES (
        'p4444444-4444-4444-4444-444444444444',
        'd1111111-1111-1111-1111-111111111111',
        now_time - INTERVAL '2 hours',
        now_time - INTERVAL '2 hours',
        'completed',
        'Ramassage du midi'
    );

    -- Pickup 5: Cancelled - Was supposed to happen but cancelled
    INSERT INTO pickups (id, pickup_person_id, scheduled_time, status, notes, cancellation_reason)
    VALUES (
        'p5555555-5555-5555-5555-555555555555',
        'd2222222-2222-2222-2222-222222222222',
        now_time - INTERVAL '30 minutes',
        'cancelled',
        'Annulé',
        'Enfant malade - restera à l''école'
    );
END $$;

-- ═══════════════════════════════════════════════════════════════
-- PICKUP-CHILDREN RELATIONSHIPS
-- ═══════════════════════════════════════════════════════════════

INSERT INTO pickup_children (pickup_id, child_id, checked_out, checked_out_at, checked_out_by) VALUES
-- Pickup 1: Sophie only
('p1111111-1111-1111-1111-111111111111', 'c1111111-1111-1111-1111-111111111111', FALSE, NULL, NULL),

-- Pickup 2: Both Gagnon children
('p2222222-2222-2222-2222-222222222222', 'c3333333-3333-3333-3333-333333333333', FALSE, NULL, NULL),
('p2222222-2222-2222-2222-222222222222', 'c4444444-4444-4444-4444-444444444444', FALSE, NULL, NULL),

-- Pickup 3: Sophie (late)
('p3333333-3333-3333-3333-333333333333', 'c1111111-1111-1111-1111-111111111111', FALSE, NULL, NULL),

-- Pickup 4: Thomas (completed)
('p4444444-4444-4444-4444-444444444444', 'c2222222-2222-2222-2222-222222222222', TRUE, NOW() - INTERVAL '2 hours', 'Mme Lafleur'),

-- Pickup 5: Émilie (cancelled)
('p5555555-5555-5555-5555-555555555555', 'c3333333-3333-3333-3333-333333333333', FALSE, NULL, NULL);

-- ═══════════════════════════════════════════════════════════════
-- EMERGENCIES
-- ═══════════════════════════════════════════════════════════════

-- Active emergency: Tante Marie is late
INSERT INTO emergencies (id, child_id, emergency_type, context, severity, resolved) VALUES
(
    'e1111111-1111-1111-1111-111111111111',
    'c1111111-1111-1111-1111-111111111111',
    'late',
    'Tante Marie prise dans le trafic sur le pont Jacques-Cartier. Délai estimé: 20 minutes.',
    'medium',
    FALSE
);

-- Resolved emergency: Lucas had a fever (from earlier)
INSERT INTO emergencies (id, child_id, emergency_type, context, severity, resolved, resolved_at) VALUES
(
    'e2222222-2222-2222-2222-222222222222',
    'c4444444-4444-4444-4444-444444444444',
    'illness',
    'Fièvre de 38.5°C. Infirmière a contacté les parents.',
    'high',
    TRUE,
    NOW() - INTERVAL '1 hour'
);

-- ═══════════════════════════════════════════════════════════════
-- VERIFICATION QUERIES
-- ═══════════════════════════════════════════════════════════════

-- Display summary of seeded data
DO $$
DECLARE
    school_count INTEGER;
    children_count INTEGER;
    delegate_count INTEGER;
    pickup_count INTEGER;
    emergency_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO school_count FROM schools;
    SELECT COUNT(*) INTO children_count FROM children;
    SELECT COUNT(*) INTO delegate_count FROM delegates;
    SELECT COUNT(*) INTO pickup_count FROM pickups;
    SELECT COUNT(*) INTO emergency_count FROM emergencies;

    RAISE NOTICE '════════════════════════════════════════════════════════';
    RAISE NOTICE 'AllôBye Seed Data Summary';
    RAISE NOTICE '════════════════════════════════════════════════════════';
    RAISE NOTICE 'Schools:     %', school_count;
    RAISE NOTICE 'Children:    %', children_count;
    RAISE NOTICE 'Delegates:   %', delegate_count;
    RAISE NOTICE 'Pickups:     %', pickup_count;
    RAISE NOTICE 'Emergencies: %', emergency_count;
    RAISE NOTICE '════════════════════════════════════════════════════════';
END $$;
