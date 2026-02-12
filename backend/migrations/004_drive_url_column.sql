-- Migration 004: Add drive_url column to cv_versions
-- Tracks which CV versions have been archived to Google Drive

ALTER TABLE cv_versions
  ADD COLUMN IF NOT EXISTS drive_url TEXT;
