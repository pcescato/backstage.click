<?php

declare(strict_types=1);

require_once '/www/wwwroot/backstage.click/api/config.php';

$email = isset($_GET['email']) ? trim((string) $_GET['email']) : '';
$action = isset($_POST['action']) ? trim((string) $_POST['action']) : '';
$postedEmail = isset($_POST['email']) ? trim((string) $_POST['email']) : '';

$isValidEmail = $email !== '' && filter_var($email, FILTER_VALIDATE_EMAIL);
$isPostRequest = $_SERVER['REQUEST_METHOD'] === 'POST';
$showConfirmation = !$isPostRequest && $isValidEmail;
$showThankYou = $isPostRequest 
    && filter_var($postedEmail, FILTER_VALIDATE_EMAIL) 
    && in_array($action, ['jamais', 'limite']);
$showError = $isPostRequest 
    ? (empty($postedEmail) || !filter_var($postedEmail, FILTER_VALIDATE_EMAIL) || !in_array($action, ['jamais', 'limite']))
    : ($email !== '' && !$isValidEmail);

$logoUrl = 'https://backstage.click/backstage-logo.webp';

if ($showThankYou && ($action === 'jamais' || $action === 'limite')) {
    try {
        $pdo = new PDO(
            'mysql:host=' . TRACK_DB_HOST . ';dbname=' . TRACK_DB_NAME . ';charset=utf8mb4',
            TRACK_DB_USER,
            TRACK_DB_PASS,
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
        );
        
        $pdo->beginTransaction();

        $ipAddr = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : null;
        
        // 1. On logue la désinscription quoi qu'il arrive
        $stmt = $pdo->prepare(
            'INSERT INTO desinscription (email, preference, ip) 
             VALUES (:email, :preference, :ip) 
             ON DUPLICATE KEY UPDATE 
               preference = VALUES(preference),
               confirmed_at = NOW(),
               ip = VALUES(ip)'
        );
        
        $stmt->execute([
            ':email' => $postedEmail,
            ':preference' => $action,
            ':ip' => $ipAddr
        ]);

        // 2. Si et seulement si le choix est 'jamais', on nettoie les tables de prospection
        if ($action === 'jamais') {
            $stmtDeleteProspection = $pdo->prepare('DELETE FROM prospection WHERE email = :email');
            $stmtDeleteProspection->execute([':email' => $postedEmail]);

            $stmtDeleteProspectsWeb = $pdo->prepare('DELETE FROM prospects_web WHERE email = :email');
            $stmtDeleteProspectsWeb->execute([':email' => $postedEmail]);
        }

        $pdo->commit();

    } catch (PDOException $e) {
        if ($pdo->inTransaction()) {
            $pdo->rollBack();
        }
        error_log('Desinscription error: ' . $e->getMessage());
        $showError = true;
        $showThankYou = false;
    }
}

?><!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="robots" content="noindex">
    <title>Gestion des préférences email</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #f0f4f8 0%, #e8eef4 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: white;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
            max-width: 480px;
            width: 100%;
            padding: 48px 40px;
            text-align: center;
        }
        .logo {
            margin-bottom: 24px;
        }
        .logo img {
            width: 300px;
            height: auto;
            display: block;
            margin: 0 auto;
        }
        h1 {
            font-size: 22px;
            font-weight: 700;
            color: #31556f;
            margin-bottom: 8px;
        }
        .subtitle {
            font-size: 14px;
            color: #6b7280;
            line-height: 1.6;
            margin-bottom: 24px;
        }
        .email-display {
            background: #f3f6f9;
            border-radius: 8px;
            padding: 12px 16px;
            margin-bottom: 32px;
            font-weight: 600;
            color: #31556f;
            text-align: center;
            font-size: 15px;
            word-break: break-all;
        }
        button {
            width: 100%;
            border-radius: 8px;
            padding: 14px;
            font-size: 15px;
            font-weight: 600;
            border: none;
            cursor: pointer;
            transition: opacity 0.2s;
            margin-bottom: 12px;
        }
        button:hover {
            opacity: 0.88;
        }
        .btn-never {
            background-color: #dc2626;
            color: white;
        }
        .btn-limited {
            background-color: #16a34a;
            color: white;
        }
        .thank-you {
            text-align: center;
        }
        .thank-you-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background-color: #56bee4;
            color: white;
            font-size: 28px;
            margin: 0 auto 16px;
        }
        .thank-you-message {
            color: #374151;
            font-size: 15px;
            line-height: 1.6;
        }
        .error {
            text-align: center;
        }
        .error-icon {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            background-color: #fecaca;
            color: #dc2626;
            font-size: 28px;
            margin: 0 auto 16px;
        }
        .error-message {
            color: #374151;
            font-size: 15px;
            line-height: 1.6;
        }
        form {
            display: contents;
        }
        input[type="hidden"] {
            display: none;
        }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">
            <img src="<?php echo htmlspecialchars($logoUrl, ENT_QUOTES, 'UTF-8'); ?>" alt="Backstage Logo">
        </div>
        
        <h1>Gestion des préférences email</h1>
        
        <?php if ($showError): ?>
            <div class="error">
                <div class="error-icon">✕</div>
                <div class="error-message">Lien invalide</div>
            </div>
        <?php elseif ($showThankYou): ?>
            <?php
                $preferenceLabel = $action === 'jamais' 
                    ? 'Vous ne serez plus contacté. Votre choix a été enregistré.'
                    : 'Vous ne recevrez pas plus de 2 emails par an. Votre choix a été enregistré.';
            ?>
            <div class="thank-you">
                <p><?php echo htmlspecialchars($preferenceLabel, ENT_QUOTES, 'UTF-8'); ?></p>
            </div>
            <p style="margin-top:24px;font-size:2rem;color:#9ca3af;">
                <a href="https://backstage.click" 
                style="color:#56bee4;text-decoration:none;font-weight:500;">
                    ← Retour à l'accueil
                </a>
            </p>
        <?php elseif ($showConfirmation): ?>
            <p class="subtitle">
                Vous avez demandé à ne plus être contacté par Pascal Cescato - Backstage.<br>
                Veuillez choisir votre préférence :
            </p>
            
            <div class="email-display">
                <?php echo htmlspecialchars($email, ENT_QUOTES, 'UTF-8'); ?>
            </div>
            
            <form method="POST">
                <input type="hidden" name="email" value="<?php echo htmlspecialchars($email, ENT_QUOTES, 'UTF-8'); ?>">
                <input type="hidden" name="action" value="jamais">
                <button type="submit" class="btn-never">Je ne veux plus être contacté</button>
            </form>
            
            <form method="POST" style="margin-top: 12px;">
                <input type="hidden" name="email" value="<?php echo htmlspecialchars($email, ENT_QUOTES, 'UTF-8'); ?>">
                <input type="hidden" name="action" value="limite">
                <button type="submit" class="btn-limited">Pas plus de 2 emails par an</button>
            </form>
        <?php endif; ?>
    </div>
</body>
</html>
