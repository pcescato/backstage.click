-- Recréation des tables pour la base de données backstage_scans
-- Base: MariaDB 10.11.10 / MySQL
-- Date: 2026-07-01

-- S'assurer qu'on utilise la bonne base de données
USE `backstage_scans`;

-- ========================================
-- Supprimer les contraintes d'abord (au cas où)
-- ========================================
SET FOREIGN_KEY_CHECKS = 0;

-- Lâcher les tables si elles existent (au cas où elles soient partiellement recréées)
DROP TABLE IF EXISTS `recommendations`;
DROP TABLE IF EXISTS `vulnerabilities`;
DROP TABLE IF EXISTS `scan_queue`;
DROP TABLE IF EXISTS `scans`;
DROP TABLE IF EXISTS `sites`;

SET FOREIGN_KEY_CHECKS = 1;

-- ========================================
-- 1. Table: sites
-- ========================================
CREATE TABLE `sites` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `domain` varchar(255) NOT NULL,
  `url` text NOT NULL,
  `first_scan_date` datetime DEFAULT NULL,
  `last_scan_date` datetime DEFAULT NULL,
  `scan_count` int(11) DEFAULT 0,
  `status` varchar(50) DEFAULT 'active',
  `contact_email` varchar(255) DEFAULT NULL,
  `opportunity_score` int(11) DEFAULT NULL,
  `priority` varchar(20) DEFAULT NULL,
  `notes` text DEFAULT NULL,
  `created_at` datetime DEFAULT current_timestamp(),
  PRIMARY KEY (`id`),
  UNIQUE KEY `domain` (`domain`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ========================================
-- 2. Table: scans
-- ========================================
CREATE TABLE `scans` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `site_id` int(11) NOT NULL,
  `scan_date` datetime NOT NULL,
  `performance_score` int(11) DEFAULT NULL,
  `accessibility_score` int(11) DEFAULT NULL,
  `best_practices_score` int(11) DEFAULT NULL,
  `seo_score` int(11) DEFAULT NULL,
  `fcp` float DEFAULT NULL,
  `lcp` float DEFAULT NULL,
  `tbt` float DEFAULT NULL,
  `cls` float DEFAULT NULL,
  `speed_index` float DEFAULT NULL,
  `is_wordpress` tinyint(1) DEFAULT NULL,
  `wp_version` varchar(20) DEFAULT NULL,
  `wp_version_outdated` tinyint(1) DEFAULT NULL,
  `wp_latest_version` varchar(20) DEFAULT NULL,
  `wp_theme` varchar(255) DEFAULT NULL,
  `php_version` varchar(20) DEFAULT NULL,
  `php_version_outdated` tinyint(1) DEFAULT NULL,
  `php_eol_date` varchar(20) DEFAULT NULL,
  `php_latest_version` varchar(20) DEFAULT NULL,
  `server_software` varchar(255) DEFAULT NULL,
  `server_type` varchar(50) DEFAULT NULL,
  `https_enabled` tinyint(1) DEFAULT NULL,
  `ssl_valid` tinyint(1) DEFAULT NULL,
  `security_grade` varchar(5) DEFAULT NULL,
  `security_score` int(11) DEFAULT NULL,
  `has_hsts` tinyint(1) DEFAULT NULL,
  `has_csp` tinyint(1) DEFAULT NULL,
  `has_x_frame_options` tinyint(1) DEFAULT NULL,
  `has_x_content_type_options` tinyint(1) DEFAULT NULL,
  `has_referrer_policy` tinyint(1) DEFAULT NULL,
  `has_permissions_policy` tinyint(1) DEFAULT NULL,
  `exposes_server_version` tinyint(1) DEFAULT NULL,
  `exposes_php_version` tinyint(1) DEFAULT NULL,
  `raw_data` mediumtext DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `site_id` (`site_id`),
  CONSTRAINT `scans_ibfk_1` FOREIGN KEY (`site_id`) REFERENCES `sites` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ========================================
-- 3. Table: vulnerabilities
-- ========================================
CREATE TABLE `vulnerabilities` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `scan_id` int(11) NOT NULL,
  `type` varchar(100) DEFAULT NULL,
  `severity` varchar(20) DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `recommendation` text DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `scan_id` (`scan_id`),
  CONSTRAINT `vulnerabilities_ibfk_1` FOREIGN KEY (`scan_id`) REFERENCES `scans` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ========================================
-- 4. Table: recommendations
-- ========================================
CREATE TABLE `recommendations` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `scan_id` int(11) NOT NULL,
  `type` varchar(100) DEFAULT NULL,
  `title` varchar(255) DEFAULT NULL,
  `description` text DEFAULT NULL,
  `estimated_gain` varchar(255) DEFAULT NULL,
  `estimated_effort` varchar(100) DEFAULT NULL,
  `estimated_cost_min` int(11) DEFAULT NULL,
  `estimated_cost_max` int(11) DEFAULT NULL,
  `priority` varchar(20) DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `scan_id` (`scan_id`),
  CONSTRAINT `recommendations_ibfk_1` FOREIGN KEY (`scan_id`) REFERENCES `scans` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ========================================
-- 5. Table: scan_queue
-- ========================================
CREATE TABLE `scan_queue` (
  `id` int(11) NOT NULL AUTO_INCREMENT,
  `url` varchar(500) NOT NULL,
  `email` varchar(255) NOT NULL,
  `message` text NOT NULL,
  `source` varchar(64) DEFAULT NULL,
  `status` enum('pending','processing','done','error') DEFAULT 'pending',
  `created_at` datetime DEFAULT current_timestamp(),
  `processed_at` datetime DEFAULT NULL,
  `error_msg` text DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- ========================================
-- Vérification finale
-- ========================================
COMMIT;
SELECT 'Tables recréées avec succès !' AS status;
SHOW TABLES;
