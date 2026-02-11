-- Sprint 3: CV versions and audit trail tables
-- Run:  psql -U job_matcher -d job_matcher -f migrations/001_cv_audit_tables.sql

-- Stores each AI-enhanced CV version per job
CREATE TABLE IF NOT EXISTS cv_versions (
    id               SERIAL PRIMARY KEY,
    job_id           INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    version_number   INTEGER NOT NULL DEFAULT 1,
    content          TEXT NOT NULL,                     -- original resume text
    enhanced_content TEXT,                              -- AI-enhanced CV
    skills_matched   JSONB DEFAULT '[]'::jsonb,          -- skills extracted from JD
    skills_missing   JSONB DEFAULT '[]'::jsonb,          -- gaps identified
    fit_score        INTEGER,                            -- 0-100
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(job_id, version_number)
);

-- Tracks all state changes per job for audit trail
CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    action      VARCHAR(100) NOT NULL,                 -- 'status_change', 'cv_enhanced', etc.
    field       VARCHAR(100),                           -- which field changed
    old_value   TEXT,
    new_value   TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_cv_versions_job_id ON cv_versions(job_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_job_id   ON audit_log(job_id);
