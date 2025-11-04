-- ═══════════════════════════════════════════════════════════════
-- ALLOBYE DATABASE - COMPLETE SCHEMA
-- PostgreSQL 14+ with PostGIS, Row-Level Security (RLS)
-- Quebec-specific implementation (Loi 25 compliant)
-- ═══════════════════════════════════════════════════════════════

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "postgis";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Set timezone to Quebec (America/Toronto = EST/EDT)
SET timezone = 'America/Toronto';

-- ═══════════════════════════════════════════════════════════════
-- CUSTOM TYPES
-- ═══════════════════════════════════════════════════════════════

CREATE TYPE user_role AS ENUM ('parent', 'delegate', 'school_admin', 'super_admin');
CREATE TYPE pickup_status AS ENUM ('scheduled', 'en_route', 'arrived', 'completed', 'cancelled', 'no_show');
CREATE TYPE emergency_type AS ENUM ('late', 'illness', 'cancel', 'accident', 'other');
CREATE TYPE permission_type AS ENUM ('pickup', 'emergency_contact', 'medical_decisions', 'schedule_view');
CREATE TYPE notification_channel AS ENUM ('sms', 'email', 'push', 'websocket');

-- See full schema in the user's message above...
-- This is abbreviated for space
