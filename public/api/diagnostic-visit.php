<?php
declare(strict_types=1);

/**
 * Diagnostic visit tracking endpoint
 * 
 * Receives GET requests with: site, mail, source
 * Logs diagnostic page visits to backstage_scans.diagnostic_visits
 * 
 * Returns JSON: {success: true|false}
 */

require_once __DIR__ . '/config.php';

// Suppress output for JSON response only
ob_start();

try {
    // Get parameters from query string
    $site   = isset($_GET['site']) ? trim((string)$_GET['site']) : '';
    $mail   = isset($_GET['mail']) ? trim((string)$_GET['mail']) : '';
    $source = isset($_GET['source']) ? trim((string)$_GET['source']) : '';
    
    // Validate: at least site or mail must be provided
    if ($site === '' && $mail === '') {
        throw new Exception('site or mail parameter is required');
    }
    
    // Connect to backstage_scans database
    $dsn = sprintf(
        'mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4',
        DB_HOST,
        DB_PORT,
        DB_NAME
    );
    
    $pdo = new PDO($dsn, DB_USER, DB_PASS);
    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    
    // Insert diagnostic visit
    $stmt = $pdo->prepare(
        'INSERT INTO diagnostic_visits (site, email, source, ip)
         VALUES (:site, :email, :source, :ip)'
    );
    
    $stmt->execute([
        ':site'   => $site,
        ':email'  => $mail,
        ':source' => $source !== '' ? $source : null,
        ':ip'     => $_SERVER['REMOTE_ADDR'] ?? null,
    ]);
    
    ob_end_clean();
    
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['success' => true]);
    exit;
    
} catch (Exception $e) {
    error_log('Diagnostic visit tracking error: ' . $e->getMessage());
    ob_end_clean();
    
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode(['success' => false, 'error' => $e->getMessage()]);
    exit;
}
