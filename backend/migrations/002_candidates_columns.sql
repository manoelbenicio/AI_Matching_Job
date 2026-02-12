-- Migration 002: Add name, email, is_active columns to candidates table
-- These support the CV Manager UI (M1).
-- The candidates table likely already has id and resume_text.

DO $$
BEGIN
    -- Add name column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'candidates' AND column_name = 'name') THEN
        ALTER TABLE candidates ADD COLUMN name TEXT NOT NULL DEFAULT 'Unnamed';
    END IF;

    -- Add email column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'candidates' AND column_name = 'email') THEN
        ALTER TABLE candidates ADD COLUMN email TEXT DEFAULT '';
    END IF;

    -- Add is_active column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'candidates' AND column_name = 'is_active') THEN
        ALTER TABLE candidates ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;

    -- Add created_at column
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                   WHERE table_name = 'candidates' AND column_name = 'created_at') THEN
        ALTER TABLE candidates ADD COLUMN created_at TIMESTAMP DEFAULT now();
    END IF;
END $$;
