-- AI Job Matcher — Full DB Bootstrap
-- This file runs automatically on first docker compose up (empty pgdata volume).
-- It creates ALL tables so the backend can start immediately.

-- ──────────────────────────────────────────────────────────────────────
-- 1. Jobs table (core)
-- ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS jobs (
    id                SERIAL PRIMARY KEY,
    job_id            TEXT UNIQUE,
    job_url           TEXT,
    job_title         TEXT,
    company_name      TEXT,
    location          TEXT,
    work_type         TEXT,            -- remote / hybrid / on-site
    employment_type   TEXT,            -- full-time / contract / etc
    seniority_level   TEXT,
    salary_info       TEXT,
    job_description   TEXT,
    score             INTEGER,
    justification     TEXT,
    status            TEXT NOT NULL DEFAULT 'new',
    posted_date       TIMESTAMP,
    scraped_at        TIMESTAMP,
    scored_at         TIMESTAMP,
    processed_at      TIMESTAMP,
    created_at        TIMESTAMP DEFAULT now(),
    updated_at        TIMESTAMP DEFAULT now(),
    version           INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score);

-- ──────────────────────────────────────────────────────────────────────
-- 2. CV versions table (enhancement history)
-- ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS cv_versions (
    id              SERIAL PRIMARY KEY,
    job_id          INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    version_number  INTEGER NOT NULL DEFAULT 1,
    content         TEXT,
    enhanced_content TEXT,
    skills_matched  JSONB DEFAULT '[]'::jsonb,
    skills_missing  JSONB DEFAULT '[]'::jsonb,
    fit_score       INTEGER,
    drive_url       TEXT,
    created_at      TIMESTAMP DEFAULT now(),
    CONSTRAINT uq_cv_version UNIQUE (job_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_cv_versions_job_id ON cv_versions(job_id);

-- ──────────────────────────────────────────────────────────────────────
-- 3. Audit log table (change tracking)
-- ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_log (
    id          SERIAL PRIMARY KEY,
    job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    action      VARCHAR(100) NOT NULL,
    field       VARCHAR(100),
    old_value   TEXT,
    new_value   TEXT,
    created_at  TIMESTAMP DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_job_id ON audit_log(job_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);

-- ──────────────────────────────────────────────────────────────────────
-- 4. Candidates table
-- ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    id          SERIAL PRIMARY KEY,
    name        TEXT NOT NULL DEFAULT 'Unnamed',
    email       TEXT DEFAULT '',
    resume_text TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at  TIMESTAMP DEFAULT now()
);

-- ──────────────────────────────────────────────────────────────────────
-- 5. App settings table (API keys, preferences)
-- ──────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
