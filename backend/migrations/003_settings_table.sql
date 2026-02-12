-- Migration 003: Create app_settings table for API key storage
-- This allows the Settings UI to save/retrieve API keys without .env files

CREATE TABLE IF NOT EXISTS app_settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
