<?php
declare(strict_types=1);

require_once __DIR__ . '/config.php';

$prospectId = isset($_GET['p']) 
  ? (int) $_GET['p'] : 0;
$email  = isset($_GET['e']) 
  ? trim((string) $_GET['e']) : '';
$domain = isset($_GET['d']) 
  ? trim((string) $_GET['d']) : '';

if ($prospectId > 0 
    && $email !== '' 
    && filter_var($email, FILTER_VALIDATE_EMAIL)) {
  try {
    $dsn = sprintf(
      'mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4',
      TRACK_DB_HOST,
      TRACK_DB_PORT,
      TRACK_DB_NAME
    );
    $pdo = new PDO($dsn, TRACK_DB_USER, TRACK_DB_PASS);
    $stmt = $pdo->prepare(
      'REPLACE INTO email_tracking_rgpd
       (prospect_id, email, domain, opened_at)
       VALUES (:pid, :email, :domain, :opened)'
    );
    $stmt->execute([
      ':pid'    => $prospectId,
      ':email'  => $email,
      ':domain' => $domain,
      ':opened' => date('Y-m-d'),
    ]);
  } catch (Exception $e) {
    error_log('Track error: ' . $e->getMessage());
  }
}

// Always serve the transparent pixel
header('Content-Type: image/gif');
header('Cache-Control: no-store, no-cache');
header('Pragma: no-cache');
echo base64_decode(
  'R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAAL'
  . 'AAAAAABAAEAAAIBRAA7'
);
exit;
