-- Migration 005: Add detailed_score JSONB column for 7-section scoring breakdown
-- Applied against: jobs table
-- Stores the full AI scoring analysis with dimensions like Technical Skills, Experience Level, etc.

ALTER TABLE jobs ADD COLUMN IF NOT EXISTS detailed_score JSONB;

-- Index for querying jobs that have detailed scores
CREATE INDEX IF NOT EXISTS idx_jobs_detailed_score ON jobs USING gin (detailed_score) WHERE detailed_score IS NOT NULL;

-- Add skills_matched and skills_missing as proper arrays (currently only in justification text)
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS skills_matched TEXT[] DEFAULT '{}';
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS skills_missing TEXT[] DEFAULT '{}';
