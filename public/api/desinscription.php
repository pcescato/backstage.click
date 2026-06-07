<?php

declare(strict_types=1);

require_once '/www/wwwroot/backstage.click/api/config.php';

$email = isset($_GET['email']) ? trim((string) $_GET['email']) : '';
$action = isset($_POST['action']) ? trim((string) $_POST['action']) : '';
$postedEmail = isset($_POST['email']) ? trim((string) $_POST['email']) : '';

$isValidEmail = $email !== '' && filter_var($email, FILTER_VALIDATE_EMAIL);
$isPostRequest = $_SERVER['REQUEST_METHOD'] === 'POST';
$showConfirmation = !$isPostRequest && $isValidEmail;
$showThankYou = $isPostRequest && !empty($postedEmail) && !empty($action);
$showError = (!$isValidEmail && ($email !== '' || $isPostRequest));

$logoUrl = 'https://backstage.click/backstage-logo.png';

if ($showThankYou && ($action === 'jamais' || $action === 'limite')) {
    try {
        $pdo = new PDO(
            'mysql:host=' . DB_HOST . ';dbname=' . DB_NAME . ';charset=utf8mb4',
            DB_USER,
            DB_PASS,
            [PDO::ATTR_ERRMODE => PDO::ERRMODE_EXCEPTION]
        );
        
        $ipAddr = isset($_SERVER['REMOTE_ADDR']) ? $_SERVER['REMOTE_ADDR'] : null;
        
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
    } catch (PDOException $e) {
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
    <title>Gestion des préférences email</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: system-ui, -apple-system, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 20px;
        }
        .card {
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
            max-width: 480px;
            width: 100%;
            padding: 40px;
            text-align: center;
        }
        .logo {
            margin-bottom: 24px;
        }
        .logo img {
            width: 80px;
            height: auto;
            display: block;
            margin: 0 auto;
        }
        h1 {
            font-size: 24px;
            margin-bottom: 16px;
            color: #111827;
        }
        .subtitle {
            font-size: 14px;
            color: #6b7280;
            margin-bottom: 24px;
            line-height: 1.6;
        }
        .email-display {
            background: #f3f4f6;
            padding: 12px;
            border-radius: 4px;
            margin-bottom: 24px;
            font-weight: 500;
            color: #374151;
            word-break: break-all;
        }
        .button-group {
            display: flex;
            gap: 12px;
            flex-direction: column;
        }
        button {
            padding: 12px 20px;
            border: none;
            border-radius: 4px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            transition: opacity 0.2s ease;
        }
        button:hover {
            opacity: 0.9;
        }
        .btn-never {
            background-color: #ef4444;
            color: white;
        }
        .btn-limited {
            background-color: #10b981;
            color: white;
        }
        .thank-you {
            padding: 20px;
            background: #f0fdf4;
            border-left: 4px solid #10b981;
            text-align: left;
            margin-bottom: 16px;
            border-radius: 4px;
        }
        .thank-you p {
            color: #374151;
            line-height: 1.6;
        }
        .error {
            padding: 20px;
            background: #fef2f2;
            border-left: 4px solid #ef4444;
            text-align: left;
            margin-bottom: 16px;
            border-radius: 4px;
        }
        .error p {
            color: #374151;
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
                <p>Lien invalide.</p>
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
