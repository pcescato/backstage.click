<?php
declare(strict_types=1);

/**
 * Diagnostic visit tracking endpoint
 * 
 * Receives GET requests with: site, mail, source
 * Logs diagnostic page visits to gfc_prospects.diagnostic_visits
 * and immediately updates diagnostic_clicked on prospection or prospects_web.
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
        TRACK_DB_HOST,
        TRACK_DB_PORT,
        TRACK_DB_NAME
    );
    
    $pdo = new PDO($dsn, TRACK_DB_USER, TRACK_DB_PASS);
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

    // Update diagnostic_clicked on the prospect table immediately.
    // source is base64-encoded with prefix: 'of:<id>' (prospection)
    // or 'web:<id>' (prospects_web). Legacy plain integer (no prefix)
    // uses email as discriminant to avoid cross-table id collision.
    if ($source !== '') {
        $decoded = base64_decode($source, true);

        if ($decoded !== false && trim($decoded) !== '') {
            // $table is set from two controlled string values only — no SQL injection risk
            if (str_starts_with($decoded, 'web:')) {
                // Prefixed format — route directly to prospects_web
                $table      = 'prospects_web';
                $prospectId = (int) substr($decoded, 4);

                if ($prospectId > 0) {
                    $updateStmt = $pdo->prepare(
                        "UPDATE {$table}
                         SET diagnostic_clicked = 1,
                             diagnostic_clicked_at = NOW()
                         WHERE id = :id
                         AND diagnostic_clicked = 0"
                    );
                    $updateStmt->execute([':id' => $prospectId]);
                }

            } elseif (str_starts_with($decoded, 'of:')) {
                // Prefixed format — route directly to prospection
                $table      = 'prospection';
                $prospectId = (int) substr($decoded, 3);

                if ($prospectId > 0) {
                    $updateStmt = $pdo->prepare(
                        "UPDATE {$table}
                         SET diagnostic_clicked = 1,
                             diagnostic_clicked_at = NOW()
                         WHERE id = :id
                         AND diagnostic_clicked = 0"
                    );
                    $updateStmt->execute([':id' => $prospectId]);
                }

            } else {
                // Legacy plain-numeric format — use email as discriminant
                // to avoid updating the wrong table when the same id
                // exists in both prospection and prospects_web.
                $prospectId = (int) $decoded;

                if ($prospectId > 0 && $mail !== '') {
                    $updateStmt = $pdo->prepare(
                        'UPDATE prospection
                         SET diagnostic_clicked = 1,
                             diagnostic_clicked_at = NOW()
                         WHERE id = :id
                         AND email = :email
                         AND diagnostic_clicked = 0'
                    );
                    $updateStmt->execute([':id' => $prospectId, ':email' => $mail]);

                    if ($updateStmt->rowCount() === 0) {
                        $updateStmt = $pdo->prepare(
                            'UPDATE prospects_web
                             SET diagnostic_clicked = 1,
                                 diagnostic_clicked_at = NOW()
                             WHERE id = :id
                             AND email = :email
                             AND diagnostic_clicked = 0'
                        );
                        $updateStmt->execute([':id' => $prospectId, ':email' => $mail]);
                    }
                }
            }
        }
    }

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
