<?php
declare(strict_types=1);

// Charger la configuration centralisée
$configPath = __DIR__ . '/config.php';
if (!file_exists($configPath)) {
    http_response_code(500);
    die(json_encode([
        'success' => false,
        'error' => 'Fichier de configuration manquant. Veuillez copier config.php.sample en config.php.'
    ]));
}
require $configPath;

const RATE_LIMIT_WINDOW = 60;

require __DIR__ . '/vendor/autoload.php';

use PHPMailer\PHPMailer\Exception;
use PHPMailer\PHPMailer\PHPMailer;

function respond(int $status, array $payload, array $headers = []): never
{
    http_response_code($status);
    header('Content-Type: application/json; charset=UTF-8');

    foreach ($headers as $name => $value) {
        header($name . ': ' . $value);
    }

    $json = json_encode($payload, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    echo $json !== false ? $json : '{"success":false,"error":"Réponse JSON invalide."}';
    exit;
}

function applyCorsHeaders(): void
{
    $origin = $_SERVER['HTTP_ORIGIN'] ?? '';

    if ($origin === ALLOWED_ORIGIN) {
        header('Access-Control-Allow-Origin: ' . ALLOWED_ORIGIN);
        header('Access-Control-Allow-Methods: POST, OPTIONS');
        header('Access-Control-Allow-Headers: Content-Type');
        header('Vary: Origin');
    }
}

function getJsonPayload(): array
{
    $contentType = $_SERVER['CONTENT_TYPE'] ?? '';
    if (stripos($contentType, 'application/json') !== 0) {
        respond(422, [
            'success' => false,
            'errors' => [
                'body' => 'Le endpoint accepte uniquement du JSON.',
            ],
        ]);
    }

    $rawBody = file_get_contents('php://input');
    if ($rawBody === false || trim($rawBody) === '') {
        respond(422, [
            'success' => false,
            'errors' => [
                'body' => 'Le corps JSON est obligatoire.',
            ],
        ]);
    }

    $payload = json_decode($rawBody, true);
    if (!is_array($payload) || json_last_error() !== JSON_ERROR_NONE) {
        respond(422, [
            'success' => false,
            'errors' => [
                'body' => 'Le JSON envoyé est invalide.',
            ],
        ]);
    }

    return $payload;
}

function enforceRateLimit(string $ipAddress, int $windowInSeconds): void
{
    $path = sys_get_temp_dir() . '/backstage-contact-' . hash('sha256', $ipAddress) . '.tmp';
    $handle = fopen($path, 'c+');

    if ($handle === false) {
        respond(500, [
            'success' => false,
            'error' => 'Impossible de vérifier la limite d’envoi.',
        ]);
    }

    if (!flock($handle, LOCK_EX)) {
        fclose($handle);
        respond(500, [
            'success' => false,
            'error' => 'Impossible de verrouiller la limite d’envoi.',
        ]);
    }

    $lastSentRaw = stream_get_contents($handle);
    $lastSentAt = $lastSentRaw === false ? 0 : (int) trim($lastSentRaw);
    $now = time();

    if ($lastSentAt > 0 && ($now - $lastSentAt) < $windowInSeconds) {
        flock($handle, LOCK_UN);
        fclose($handle);

        respond(429, [
            'success' => false,
            'error' => 'Veuillez patienter avant de renvoyer un message.',
        ]);
    }

    ftruncate($handle, 0);
    rewind($handle);
    fwrite($handle, (string) $now);
    fflush($handle);
    flock($handle, LOCK_UN);
    fclose($handle);
}

function validatePayload(array $payload): array
{
    $nom = trim((string) ($payload['nom'] ?? ''));
    $email = trim((string) ($payload['email'] ?? ''));
    $urlSite = trim((string) ($payload['url_site'] ?? ''));
    $message = trim((string) ($payload['message'] ?? ''));
    $website = trim((string) ($payload['website'] ?? ''));

    if ($website !== '') {
        respond(200, ['success' => true]);
    }

    $errors = [];

    if ($nom === '') {
        $errors['nom'] = 'Le nom est obligatoire.';
    }

    if ($email === '') {
        $errors['email'] = 'L’email est obligatoire.';
    } elseif (filter_var($email, FILTER_VALIDATE_EMAIL) === false) {
        $errors['email'] = 'L’email est invalide.';
    }

    if ($urlSite !== '' && filter_var($urlSite, FILTER_VALIDATE_URL) === false) {
        $errors['url_site'] = 'L’URL du site est invalide.';
    }

    if ($message === '') {
        $errors['message'] = 'Le message est obligatoire.';
    } elseif (mb_strlen($message) > 5000) {
        $errors['message'] = 'Le message ne doit pas dépasser 5000 caractères.';
    }

    if ($errors !== []) {
        respond(422, [
            'success' => false,
            'errors' => $errors,
        ]);
    }

    return [
        'nom' => $nom,
        'email' => $email,
        'url_site' => $urlSite,
        'message' => $message,
    ];
}

applyCorsHeaders();

$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($origin !== '' && $origin !== ALLOWED_ORIGIN) {
    respond(422, [
        'success' => false,
        'errors' => [
            'origin' => 'Origine non autorisée.',
        ],
    ]);
}

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
if ($method === 'OPTIONS') {
    respond(200, ['success' => true]);
}

if ($method !== 'POST') {
    respond(422, [
        'success' => false,
        'errors' => [
            'method' => 'Le endpoint accepte uniquement les requêtes POST.',
        ],
    ]);
}

$data = validatePayload(getJsonPayload());
enforceRateLimit($_SERVER['REMOTE_ADDR'] ?? 'unknown', RATE_LIMIT_WINDOW);

$safeNom = trim(preg_replace('/[\r\n]+/', ' ', $data['nom']) ?? $data['nom']);
$escapedNom = htmlspecialchars($data['nom'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
$escapedEmail = htmlspecialchars($data['email'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8');
$escapedUrlSite = $data['url_site'] !== ''
    ? htmlspecialchars($data['url_site'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8')
    : 'Non renseigné';
$escapedMessage = nl2br(htmlspecialchars($data['message'], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8'));

$htmlBody = <<<HTML
<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="UTF-8">
  <title>Contact Backstage</title>
</head>
<body style="margin:0;padding:24px;background:#f5f5f5;font-family:Arial,sans-serif;color:#111827;">
  <div style="max-width:720px;margin:0 auto;background:#ffffff;border:1px solid #e5e7eb;border-radius:12px;overflow:hidden;">
    <div style="padding:24px 24px 16px;background:#111827;color:#ffffff;">
      <h1 style="margin:0;font-size:24px;">Nouveau message de contact</h1>
      <p style="margin:8px 0 0;font-size:14px;opacity:0.9;">Formulaire Backstage</p>
    </div>
    <div style="padding:24px;">
      <table style="width:100%;border-collapse:collapse;">
        <tr>
          <th align="left" style="padding:12px 0;border-bottom:1px solid #e5e7eb;width:180px;">Nom</th>
          <td style="padding:12px 0;border-bottom:1px solid #e5e7eb;">{$escapedNom}</td>
        </tr>
        <tr>
          <th align="left" style="padding:12px 0;border-bottom:1px solid #e5e7eb;">Email</th>
          <td style="padding:12px 0;border-bottom:1px solid #e5e7eb;">{$escapedEmail}</td>
        </tr>
        <tr>
          <th align="left" style="padding:12px 0;border-bottom:1px solid #e5e7eb;">URL du site</th>
          <td style="padding:12px 0;border-bottom:1px solid #e5e7eb;">{$escapedUrlSite}</td>
        </tr>
        <tr>
          <th align="left" style="padding:12px 0;vertical-align:top;">Message</th>
          <td style="padding:12px 0;">{$escapedMessage}</td>
        </tr>
      </table>
    </div>
  </div>
</body>
</html>
HTML;

$plainBody = "Nouveau message de contact Backstage\n\n"
    . "Nom : {$data['nom']}\n"
    . "Email : {$data['email']}\n"
    . 'URL du site : ' . ($data['url_site'] !== '' ? $data['url_site'] : 'Non renseigné') . "\n\n"
    . "Message :\n{$data['message']}\n";

$mailer = new PHPMailer(true);

try {
    $mailer->isSMTP();
    $mailer->Host = SMTP_HOST;
    $mailer->SMTPAuth = true;
    $mailer->Username = SMTP_USER;
    $mailer->Password = SMTP_PASS;
    $mailer->SMTPSecure = PHPMailer::ENCRYPTION_SMTPS;
    $mailer->Port = SMTP_PORT;
    $mailer->CharSet = 'UTF-8';

    $mailer->setFrom(SMTP_FROM, SMTP_FROM_NAME);
    $mailer->addAddress(MAIL_TO);
    $mailer->addReplyTo($data['email'], $data['nom']);

    $mailer->isHTML(true);
    $mailer->Subject = 'Contact Backstage — ' . $safeNom;
    $mailer->Body = $htmlBody;
    $mailer->AltBody = $plainBody;

    $mailer->send();

    respond(200, ['success' => true]);
} catch (Exception $exception) {
    error_log('Contact mail error: ' . $mailer->ErrorInfo);

    respond(500, [
        'success' => false,
        'error' => 'Impossible d’envoyer le message.',
    ]);
}
