-- Migration 001: Add version column to jobs, create cv_versions and audit_log tables
-- Date: 2026-02-10
-- Purpose: Support optimistic locking, CV version history, and audit trail

BEGIN;

-- ──────────────────────────────────────────────────────────────────────
-- 1. Add version column to jobs for optimistic concurrency control
-- ──────────────────────────────────────────────────────────────────────
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS version INTEGER NOT NULL DEFAULT 1;

-- ──────────────────────────────────────────────────────────────────────
-- 2. Create cv_versions table for CV enhancement history
-- ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cv_versions (
    id              SERIAL PRIMARY KEY,
    job_id          INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL DEFAULT 1,
    content         TEXT,                          -- Original resume text
    enhanced_content TEXT,                         -- AI-enhanced resume text
    skills_matched  JSONB DEFAULT '[]'::jsonb,     -- Skills from job that match candidate
    skills_missing  JSONB DEFAULT '[]'::jsonb,     -- Skills candidate is missing
    fit_score       INTEGER,                       -- AI-computed fit score 0-100
    created_at      TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),

    CONSTRAINT uq_cv_version UNIQUE (job_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_cv_versions_job_id ON cv_versions(job_id);

-- ──────────────────────────────────────────────────────────────────────
-- 3. Create audit_log table for tracking all changes
-- ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    action      VARCHAR(100) NOT NULL,              -- e.g. 'status_change', 'cv_enhanced'
    field       VARCHAR(100),                        -- which field changed
    old_value   TEXT,                                -- previous value (nullable for inserts)
    new_value   TEXT,                                -- new value
    created_at  TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_job_id ON audit_log(job_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);

COMMIT;
