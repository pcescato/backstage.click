<?php
/**
 * scan_request.php — Backstage
 * Reçoit une demande de diagnostic, insère dans scan_queue.
 * Appelé par le formulaire Astro côté client.
 */

declare(strict_types=1);

// Charger la configuration centralisée
$configPath = __DIR__ . '/config.php';
if (!file_exists($configPath)) {
    http_response_code(500);
    header('Content-Type: application/json; charset=UTF-8');
    die(json_encode([
        'success' => false,
        'message' => 'Fichier de configuration manquant. Veuillez copier config.php.sample en config.php.'
    ]));
}
require $configPath;

// ── Headers ──────────────────────────────────────────────────────
header('Content-Type: application/json; charset=UTF-8');
header('Access-Control-Allow-Origin: https://backstage.click');
header('Access-Control-Allow-Methods: POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// ── Méthode ──────────────────────────────────────────────────────
if ($_SERVER['REQUEST_METHOD'] !== 'POST') {
    http_response_code(405);
    echo json_encode(['success' => false, 'message' => 'Méthode non autorisée.']);
    exit;
}

// ── Lecture payload JSON ─────────────────────────────────────────
$raw     = file_get_contents('php://input');
$payload = json_decode($raw ?: '', true);

if (!is_array($payload)) {
    http_response_code(400);
    echo json_encode(['success' => false, 'message' => 'Payload invalide.']);
    exit;
}

// ── Honeypot ─────────────────────────────────────────────────────
if (!empty($payload['website'])) {
    // Faux positif silencieux
    http_response_code(200);
    echo json_encode(['success' => true]);
    exit;
}

// ── Validation ───────────────────────────────────────────────────
$urlSite = trim((string)($payload['url_site'] ?? ''));
$email   = trim((string)($payload['email']    ?? ''));
$message = trim((string)($payload['message']  ?? ''));
$source  = trim((string)($payload['source']   ?? ''));

// Sanitize source: max 64 chars, alphanumeric and base64 chars only
if ($source !== '') {
    $source = substr($source, 0, 64);
    if (!preg_match('/^[A-Za-z0-9+\/=]+$/', $source)) {
        $source = '';
    }
}

$errors = [];

if ($urlSite === '') {
    $errors[] = "L'URL du site est obligatoire.";
} elseif (!filter_var($urlSite, FILTER_VALIDATE_URL)) {
    // Tenter d'ajouter https:// si absent
    $candidate = 'https://' . $urlSite;
    if (filter_var($candidate, FILTER_VALIDATE_URL)) {
        $urlSite = $candidate;
    } else {
        $errors[] = "L'URL du site n'est pas valide.";
    }
}

if ($email === '') {
    $errors[] = "L'adresse email est obligatoire.";
} elseif (!filter_var($email, FILTER_VALIDATE_EMAIL)) {
    $errors[] = "L'adresse email n'est pas valide.";
}

if (strlen($message) > 2000) {
    $errors[] = "Le message ne doit pas dépasser 2000 caractères.";
}

if ($errors) {
    http_response_code(422);
    echo json_encode(['success' => false, 'message' => implode(' ', $errors)]);
    exit;
}

// ── Rate limiting (1 demande / IP / 10 min) ──────────────────────
$ip      = $_SERVER['HTTP_X_FORWARDED_FOR'] ?? $_SERVER['REMOTE_ADDR'] ?? 'unknown';
$ip      = explode(',', $ip)[0];
$rlKey   = 'scan_rl_' . md5($ip);
$rlFile  = sys_get_temp_dir() . DIRECTORY_SEPARATOR . $rlKey;
$rlLimit = 300; // 5 minutes

if (file_exists($rlFile)) {
    $lastTime = (int)file_get_contents($rlFile);
    if (time() - $lastTime < $rlLimit) {
        $remaining = $rlLimit - (time() - $lastTime);
        http_response_code(429);
        echo json_encode([
            'success' => false,
            'message' => "Une demande est déjà en cours pour votre adresse. Veuillez patienter {$remaining} secondes.",
        ]);
        exit;
    }
}

file_put_contents($rlFile, (string)time());

// ── Connexion BDD ────────────────────────────────────────────────
try {
    $dsn = sprintf(
        'mysql:host=%s;port=%d;dbname=%s;charset=utf8mb4',
        DB_HOST, DB_PORT, DB_NAME
    );
    $pdo = new PDO($dsn, DB_USER, DB_PASS, [
        PDO::ATTR_ERRMODE            => PDO::ERRMODE_EXCEPTION,
        PDO::ATTR_DEFAULT_FETCH_MODE => PDO::FETCH_ASSOC,
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Erreur de connexion à la base de données.']);
    exit;
}

// ── Vérifier si la table scan_queue existe ───────────────────────
try {
    $check = $pdo->query("SHOW TABLES LIKE 'scan_queue'");
    if ($check->rowCount() === 0) {
        $pdo->exec("
            CREATE TABLE scan_queue (
                id           INT AUTO_INCREMENT PRIMARY KEY,
                url          VARCHAR(500) NOT NULL,
                email        VARCHAR(255) NOT NULL,
                message      TEXT NULL,
                source       VARCHAR(64) NULL,
                status       ENUM('pending','processing','done','error') DEFAULT 'pending',
                created_at   DATETIME DEFAULT CURRENT_TIMESTAMP,
                processed_at DATETIME NULL,
                error_msg    TEXT NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ");
    }
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Erreur lors de la vérification de la base.']);
    exit;
}

// ── Vérifier les doublons récents (même URL + email dans les 24h) ─
try {
    $stmt = $pdo->prepare("
        SELECT COUNT(*) FROM scan_queue
        WHERE url = :url
          AND email = :email
          AND created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
          AND status != 'error'
    ");
    $stmt->execute([':url' => $urlSite, ':email' => $email]);
    if ((int)$stmt->fetchColumn() > 0) {
        http_response_code(429);
        echo json_encode([
            'success' => false,
            'message' => 'Un diagnostic pour ce site a déjà été demandé récemment. Le rapport vous sera envoyé sous peu.',
        ]);
        exit;
    }
} catch (PDOException $e) {
    // Non bloquant — on continue
}

// ── Insertion dans la file ───────────────────────────────────────
try {
    $stmt = $pdo->prepare("
        INSERT INTO scan_queue (url, email, message, source)
        VALUES (:url, :email, :message, :source)
    ");
    $stmt->execute([
        ':url'     => $urlSite,
        ':email'   => $email,
        ':message' => $message !== '' ? $message : '',
        ':source'  => $source !== '' ? $source : null,
    ]);
} catch (PDOException $e) {
    http_response_code(500);
    echo json_encode(['success' => false, 'message' => 'Erreur lors de l\'enregistrement de la demande.']);
    exit;
}

// ── Succès ───────────────────────────────────────────────────────
http_response_code(200);
echo json_encode([
    'success' => true,
    'message' => 'Votre demande a bien été enregistrée. Le rapport vous sera envoyé par email sous 10 minutes.',
]);
