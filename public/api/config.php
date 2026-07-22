<?php
declare(strict_types=1);

/**
 * Configuration centralisée pour les endpoints API
 * 
 * Ce fichier contient les données sensibles (SMTP, BDD).
 * Il ne doit pas être versionné.
 */

// ── Configuration SMTP (pour contact.php) ────────────────────────────
define('SMTP_HOST',       'ssl0.ovh.net');
define('SMTP_PORT',       465);
define('SMTP_ENCRYPTION', 'ssl');
define('SMTP_USER',       'pascal.cescato@backstage.click');
define('SMTP_PASS',       'LE_MOT_DE_PASSE');
define('SMTP_FROM',       'pascal.cescato@backstage.click');
define('SMTP_FROM_NAME',  'Pascal CESCATO - Backstage');
define('MAIL_TO',         'courriel@backstage.click');

// ── Configuration Base de données (pour scan_request.php) ───────────
define('DB_HOST',  getenv('BACKSTAGE_DB_HOST') ?: 'localhost');
define('DB_PORT',  (int)(getenv('BACKSTAGE_DB_PORT') ?: 3306));
define('DB_NAME',  getenv('BACKSTAGE_DB_NAME') ?: 'backstage_scans');
define('DB_USER',  getenv('BACKSTAGE_DB_USER') ?: 'backstage_scans');
define('DB_PASS',  getenv('BACKSTAGE_DB_PASS') ?: 'hxDpPfz5BTs2IYfD');

// ── Configuration générale ───────────────────────────────────────────
const ALLOWED_ORIGIN = 'https://backstage.click';

defined('TRACK_DB_HOST') || define('TRACK_DB_HOST', getenv('TRACK_DB_HOST') ?: '127.0.0.1');
defined('TRACK_DB_PORT') || define('TRACK_DB_PORT', getenv('TRACK_DB_PORT') ?: '3306');
defined('TRACK_DB_NAME') || define('TRACK_DB_NAME', getenv('TRACK_DB_NAME') ?: 'gfc_prospects');
defined('TRACK_DB_CHARSET') || define('TRACK_DB_CHARSET', getenv('TRACK_DB_CHARSET') ?: 'utf8mb4');
defined('TRACK_DB_USER') || define('TRACK_DB_USER', getenv('TRACK_DB_USER') ?: 'gfc_prospects');
defined('TRACK_DB_PASS') || define('TRACK_DB_PASS', getenv('TRACK_DB_PASS') ?: 'hxDpPfz5BTs2IYfD');
