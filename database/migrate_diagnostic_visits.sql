-- Migration: Create diagnostic_visits table
-- Database: backstage_scans
-- Purpose: Track when prospects visit the diagnostic page

CREATE TABLE IF NOT EXISTS diagnostic_visits (
  id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  site        VARCHAR(255) NOT NULL,
  email       VARCHAR(255) NOT NULL DEFAULT '',
  source      VARCHAR(100) NULL COMMENT 'prospect_id base64',
  visited_at  DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  ip          VARCHAR(45) NULL,
  INDEX idx_email  (email),
  INDEX idx_site   (site),
  INDEX idx_source (source),
  INDEX idx_date   (visited_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
  COLLATE=utf8mb4_unicode_ci;

-- RGPD: automatic purge after 90 days
-- Execute via monthly cron:
-- DELETE FROM diagnostic_visits
--   WHERE visited_at < NOW() - INTERVAL 90 DAY;
