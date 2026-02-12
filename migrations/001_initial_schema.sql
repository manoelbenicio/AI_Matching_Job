-- ============================================================
-- AI Job Matcher - Database Schema
-- PostgreSQL Migration Script
-- Run: psql -U job_matcher -d job_matcher -f 001_initial_schema.sql
-- ============================================================

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- For text search

-- ============================================================
-- JOBS TABLE: All scraped job postings
-- ============================================================
CREATE TABLE IF NOT EXISTS jobs (
    id SERIAL PRIMARY KEY,
    job_id VARCHAR(100) UNIQUE NOT NULL,  -- LinkedIn/source job ID
    
    -- Job Details
    job_title VARCHAR(500),
    company_name VARCHAR(500),
    job_description TEXT,
    location VARCHAR(500),
    salary_info VARCHAR(255),
    
    -- Job Attributes
    seniority_level VARCHAR(100),
    employment_type VARCHAR(100),
    work_type VARCHAR(100),
    contract_type VARCHAR(100),
    sector VARCHAR(255),
    
    -- URLs
    job_url TEXT,
    apply_url TEXT,
    company_url TEXT,
    
    -- Timing
    time_posted VARCHAR(100),
    posted_date TIMESTAMP,
    
    -- Counts
    num_applicants VARCHAR(100),
    applicants_count INTEGER DEFAULT 0,
    
    -- Recruiter Info
    recruiter_name VARCHAR(255),
    recruiter_url TEXT,
    
    -- Processing Status
    status VARCHAR(30) DEFAULT 'pending' 
        CHECK (status IN ('pending', 'processing', 'qualified', 'low_score', 'enhanced', 'error', 'skipped')),
    
    -- AI Results (stored after processing)
    score INTEGER DEFAULT NULL CHECK (score IS NULL OR (score >= 0 AND score <= 100)),
    justification TEXT,
    score_justification TEXT,
    
    -- Custom Resume (for qualified jobs)
    custom_resume_url TEXT,
    
    -- Error Handling
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    
    -- Optimistic concurrency
    version INTEGER DEFAULT 1,

    -- Timestamps
    scraped_at TIMESTAMP DEFAULT NOW(),
    scored_at TIMESTAMP,
    processed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- CANDIDATES TABLE: Resume/Profile Storage
-- ============================================================
CREATE TABLE IF NOT EXISTS candidates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255),
    phone VARCHAR(50),
    
    -- Resume Content
    resume_text TEXT,
    resume_url TEXT,
    resume_doc_id VARCHAR(100),
    
    -- Skills & Experience (JSONB for flexibility)
    skills JSONB DEFAULT '[]'::jsonb,
    experience JSONB DEFAULT '[]'::jsonb,
    education JSONB DEFAULT '[]'::jsonb,
    
    -- Preferences
    target_roles TEXT[],
    preferred_locations TEXT[],
    min_salary INTEGER,
    
    -- Status
    is_active BOOLEAN DEFAULT true,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- MATCH_RESULTS TABLE: AI Scoring History
-- ============================================================
CREATE TABLE IF NOT EXISTS match_results (
    id SERIAL PRIMARY KEY,
    job_id INTEGER REFERENCES jobs(id) ON DELETE CASCADE,
    candidate_id INTEGER REFERENCES candidates(id) ON DELETE CASCADE,
    
    -- Scoring
    match_score INTEGER CHECK (match_score >= 0 AND match_score <= 100),
    is_qualified BOOLEAN GENERATED ALWAYS AS (match_score >= 75) STORED,
    
    -- AI Output
    ai_reasoning TEXT,
    score_breakdown JSONB,  -- {"skills": 25, "experience": 30, ...}
    
    -- Token Usage Tracking
    tokens_used INTEGER DEFAULT 0,
    ai_model VARCHAR(50) DEFAULT 'gpt-4o-mini',
    processing_time_ms INTEGER,
    
    -- Resume (if generated)
    custom_resume_url TEXT,
    resume_doc_id VARCHAR(100),
    
    -- Timestamps
    processed_at TIMESTAMP DEFAULT NOW(),
    
    UNIQUE(job_id, candidate_id)
);

-- ============================================================
-- PROCESSING_LOGS TABLE: Audit Trail
-- ============================================================
CREATE TABLE IF NOT EXISTS processing_logs (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100),
    job_id INTEGER REFERENCES jobs(id) ON DELETE SET NULL,
    
    -- Event Details
    event_type VARCHAR(50) NOT NULL,  -- 'scoring_started', 'scoring_completed', 'error', 'resume_generated'
    details JSONB DEFAULT '{}'::jsonb,
    
    -- Performance Tracking
    duration_ms INTEGER,
    tokens_used INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW()
);

-- ============================================================
-- BATCH_RUNS TABLE: Batch Processing History
-- ============================================================
CREATE TABLE IF NOT EXISTS batch_runs (
    id SERIAL PRIMARY KEY,
    batch_id VARCHAR(100) UNIQUE NOT NULL,
    
    -- Batch Stats
    total_jobs INTEGER DEFAULT 0,
    processed_jobs INTEGER DEFAULT 0,
    qualified_jobs INTEGER DEFAULT 0,
    failed_jobs INTEGER DEFAULT 0,
    
    -- Token/Cost Tracking
    total_tokens INTEGER DEFAULT 0,
    estimated_cost DECIMAL(10,4) DEFAULT 0,
    
    -- Timing
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    
    -- Status
    status VARCHAR(20) DEFAULT 'running' CHECK (status IN ('running', 'completed', 'failed', 'cancelled'))
);

-- ============================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_jobs_status ON jobs(status);
CREATE INDEX IF NOT EXISTS idx_jobs_score ON jobs(score);
CREATE INDEX IF NOT EXISTS idx_jobs_company ON jobs(company_name);
CREATE INDEX IF NOT EXISTS idx_jobs_scraped_at ON jobs(scraped_at);
CREATE INDEX IF NOT EXISTS idx_jobs_job_id ON jobs(job_id);

CREATE INDEX IF NOT EXISTS idx_results_qualified ON match_results(is_qualified);
CREATE INDEX IF NOT EXISTS idx_results_score ON match_results(match_score);
CREATE INDEX IF NOT EXISTS idx_results_processed ON match_results(processed_at);

CREATE INDEX IF NOT EXISTS idx_logs_batch ON processing_logs(batch_id);
CREATE INDEX IF NOT EXISTS idx_logs_event ON processing_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_logs_created ON processing_logs(created_at);

-- Text search index for job descriptions
CREATE INDEX IF NOT EXISTS idx_jobs_desc_trgm ON jobs USING gin (job_description gin_trgm_ops);

-- ============================================================
-- USEFUL VIEWS FOR DASHBOARD
-- ============================================================

-- Daily Processing Summary
CREATE OR REPLACE VIEW daily_processing_summary AS
SELECT 
    DATE(processed_at) as date,
    COUNT(*) as total_processed,
    COUNT(*) FILTER (WHERE status = 'qualified') as qualified,
    COUNT(*) FILTER (WHERE status = 'low_score') as rejected,
    COUNT(*) FILTER (WHERE status = 'enhanced') as enhanced,
    COUNT(*) FILTER (WHERE status = 'error') as errors,
    AVG(score) as avg_score
FROM jobs
WHERE processed_at IS NOT NULL
GROUP BY DATE(processed_at)
ORDER BY date DESC;

-- Top Companies by Qualified Jobs
CREATE OR REPLACE VIEW company_qualified_ranking AS
SELECT 
    company_name,
    COUNT(*) as total_jobs,
    COUNT(*) FILTER (WHERE status = 'qualified' OR status = 'enhanced') as qualified_jobs,
    ROUND(AVG(score)::numeric, 1) as avg_score
FROM jobs
WHERE score IS NOT NULL
GROUP BY company_name
HAVING COUNT(*) >= 2
ORDER BY qualified_jobs DESC, avg_score DESC;

-- Score Distribution
CREATE OR REPLACE VIEW score_distribution AS
SELECT 
    CASE 
        WHEN score >= 90 THEN '90-100 (Excellent)'
        WHEN score >= 75 THEN '75-89 (Qualified)'
        WHEN score >= 50 THEN '50-74 (Maybe)'
        WHEN score >= 25 THEN '25-49 (Low)'
        ELSE '0-24 (Not Fit)'
    END as score_range,
    COUNT(*) as count
FROM jobs
WHERE score IS NOT NULL
GROUP BY 1
ORDER BY 1 DESC;

-- ============================================================
-- TRIGGER: Auto-update updated_at timestamp
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE OR REPLACE TRIGGER update_jobs_updated_at
    BEFORE UPDATE ON jobs
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

CREATE OR REPLACE TRIGGER update_candidates_updated_at
    BEFORE UPDATE ON candidates
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- SAMPLE DATA: Insert default candidate (your profile)
-- ============================================================
INSERT INTO candidates (name, email, resume_text, is_active)
VALUES ('Default Candidate', 'user@example.com', 'Paste your resume text here', true)
ON CONFLICT DO NOTHING;

-- ============================================================
-- Grant permissions for metabase
-- ============================================================
-- Note: Metabase creates its own database/tables automatically
GRANT ALL PRIVILEGES ON DATABASE job_matcher TO job_matcher;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO job_matcher;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO job_matcher;
