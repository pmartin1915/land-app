-- Database Migration: Water Features Enhanced Schema
-- Alabama Auction Watcher - Investment Analysis Enhancement
--
-- This migration creates a normalized table for water feature tracking
-- and removes the old simple integer water_features column.

-- Step 1: Create the new table to store individual water features for each property
CREATE TABLE IF NOT EXISTS property_water_features (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    property_id VARCHAR NOT NULL,
    feature_name VARCHAR(255) NOT NULL,
    feature_tier VARCHAR(50) NOT NULL,
    score INTEGER NOT NULL,
    FOREIGN KEY (property_id) REFERENCES properties (id) ON DELETE CASCADE
);

-- Step 2: Create indexes for efficient lookups
CREATE INDEX IF NOT EXISTS idx_property_water_features_property_id
    ON property_water_features (property_id);

CREATE INDEX IF NOT EXISTS idx_property_water_features_feature_name
    ON property_water_features (feature_name);

CREATE INDEX IF NOT EXISTS idx_property_water_features_feature_tier
    ON property_water_features (feature_tier);

-- Step 3: Create index on properties.water_score for efficient filtering/sorting
CREATE INDEX IF NOT EXISTS idx_properties_water_score
    ON properties (water_score);

-- Note: We are NOT dropping the old water_features column yet
-- SQLite doesn't support DROP COLUMN directly in older versions
-- The column will simply remain unused (it's already INT DEFAULT 0)
