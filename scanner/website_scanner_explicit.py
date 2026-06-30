#!/usr/bin/env python3
"""
Website Scanner — Diagnostic explicite
======================================
Script standalone à lancer en ligne de commande pour déboguer :
    python3 website_scanner_explicit.py https://example.com

Affiche étape par étape : Playwright, headers, security grade, Lighthouse.
Aucune connexion DB requise.
"""

import sys
import os
import re
import json
import requests

# ── Chargement de db_config (pour LIGHTHOUSE_API_KEY) ───────────
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

LIGHTHOUSE_API_KEY = None
try:
    from db_config import LIGHTHOUSE_API_KEY as _KEY
    LIGHTHOUSE_API_KEY = _KEY
    print(f"[db_config] LIGHTHOUSE_API_KEY chargée : {(_KEY[:8] + '...') if _KEY else '(vide)'}")
except ImportError:
    print("[db_config] Module non trouvé — LIGHTHOUSE_API_KEY=None")
except Exception as e:
    print(f"[db_config] Erreur import LIGHTHOUSE_API_KEY : {e}")

try:
    from db_config import BACKSTAGE_DB
    print(f"[db_config] BACKSTAGE_DB : host={BACKSTAGE_DB.get('host')} db={BACKSTAGE_DB.get('database', BACKSTAGE_DB.get('db'))}")
except Exception:
    print("[db_config] BACKSTAGE_DB non disponible (sans gravité pour ce diagnostic)")


# ── Constantes ───────────────────────────────────────────────────
BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/149.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
    'Accept-Encoding': 'gzip, deflate, br, zstd',
    'sec-ch-ua': '"Google Chrome";v="149", "Chromium";v="149", "Not)A;Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'none',
    'sec-fetch-user': '?1',
    'upgrade-insecure-requests': '1',
}

# Détection dynamique du binaire Chromium (plusieurs versions possibles)
def _find_chromium():
    """Cherche le binaire chromium parmi toutes les versions installées."""
    base = os.path.expanduser('~/.cache/ms-playwright')
    if not os.path.isdir(base):
        return None
    # Chercher chromium-XXXX/chrome-linux/chrome
    for entry in sorted(os.listdir(base), reverse=True):
        if entry.startswith('chromium-'):
            path = os.path.join(base, entry, 'chrome-linux', 'chrome')
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        if entry.startswith('chromium_headless_shell-'):
            path = os.path.join(base, entry, 'chrome-headless-shell-linux64', 'chrome-headless-shell')
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
    return None


class PlaywrightResponse:
    def __init__(self, status, headers, text):
        self.status_code = status
        self.headers = headers
        self.text = text


# ── Étape 1 : Playwright ─────────────────────────────────────────
def fetch_with_playwright(url):
    print("\n" + "=" * 60)
    print("ÉTAPE 1 — Fetch via Playwright (navigateur headless)")
    print("=" * 60)

    try:
        from playwright.sync_api import sync_playwright
        print("[OK] Module playwright importé")
    except ImportError:
        print("[FAIL] playwright non installé → pip install playwright")
        return None

    # Trouver le binaire Chromium
    chrome_path = _find_chromium()

    if chrome_path:
        print(f"[OK] Chromium trouvé : {chrome_path}")
    else:
        print("[WARN] Chromium non trouvé → lancez: playwright install chromium")
        print("       Tentative de lancement auto...")

    try:
        with sync_playwright() as p:
            kwargs = {}
            if chrome_path:
                kwargs['executable_path'] = chrome_path
            browser = p.chromium.launch(**kwargs)
            print("[OK] Navigateur lancé")

            page = browser.new_page()
            # Ne PAS injecter BROWSER_HEADERS via set_extra_http_headers :
            # le headless shell gère lui-même ses headers (Accept-Encoding, etc.)
            # et forcer certains headers fait que Cloudflare sert l'origin
            # au lieu de ses headers de sécurité.
            print(f"[...] Navigation vers {url}")

            resp = page.goto(url, wait_until='networkidle', timeout=30000)
            if resp is None:
                print("[FAIL] page.goto() a retourné None")
                browser.close()
                return None

            status = resp.status
            headers = dict(resp.headers)
            content = page.content()
            browser.close()

            print(f"[OK] HTTP {status}")
            print(f"[OK] {len(headers)} headers reçus")
            print(f"[OK] {len(content)} chars de contenu")

            return PlaywrightResponse(status, headers, content)

    except Exception as e:
        print(f"[FAIL] Playwright error : {e}")
        return None


# ── Étape 1b : Fallback requests ─────────────────────────────────
def fetch_with_requests(url):
    print("\n" + "=" * 60)
    print("ÉTAPE 1b — Fallback via requests")
    print("=" * 60)

    session = requests.Session()
    session.headers.update(BROWSER_HEADERS)

    try:
        resp = session.get(url, timeout=15, verify=True, allow_redirects=True)
        print(f"[OK] HTTP {resp.status_code}")
        print(f"[OK] {len(resp.headers)} headers reçus")
        print(f"[OK] {len(resp.text)} chars de contenu")
        return resp
    except Exception as e:
        print(f"[FAIL] requests error : {e}")
        return None


# ── Étape 2 : Affichage de tous les headers ──────────────────────
def dump_headers(response):
    print("\n" + "=" * 60)
    print("ÉTAPE 2 — Headers reçus (dump complet)")
    print("=" * 60)

    # Normalisation minuscules
    headers_lower = {k.lower(): v for k, v in response.headers.items()}

    for key in sorted(headers_lower.keys()):
        val = headers_lower[key]
        # Tronquer les valeurs très longues (ex: CSP)
        if len(val) > 120:
            val = val[:120] + f"... (+{len(val)-120} chars)"
        print(f"  {key}: {val}")

    # Détection Cloudflare
    if 'cf-ray' in headers_lower or 'cloudflare' in headers_lower.get('server', '').lower():
        print("\n  [INFO] Réponse servie par Cloudflare")
    else:
        print("\n  [INFO] Pas de Cloudflare détecté")

    return headers_lower


# ── Étape 3 : Security Headers Analyzer ───────────────────────────
REQUIRED_HEADERS = {
    'strict-transport-security': {'grade_weight': 50, 'label': 'HSTS'},
    'content-security-policy':   {'grade_weight': 30, 'label': 'CSP'},
    'x-frame-options':           {'grade_weight': 10, 'label': 'X-Frame-Options'},
    'x-content-type-options':    {'grade_weight': 5,  'label': 'X-Content-Type-Options'},
    'referrer-policy':           {'grade_weight': 3,  'label': 'Referrer-Policy'},
    'permissions-policy':        {'grade_weight': 2,  'label': 'Permissions-Policy'},
}


def analyze_security_headers(headers_lower):
    print("\n" + "=" * 60)
    print("ÉTAPE 3 — Security Headers Analyzer")
    print("=" * 60)

    score = 0
    max_score = sum(cfg['grade_weight'] for cfg in REQUIRED_HEADERS.values())

    for header, cfg in REQUIRED_HEADERS.items():
        present = header in headers_lower
        poids = cfg['grade_weight']
        label = cfg['label']
        if present:
            score += poids
            val = headers_lower[header]
            if len(val) > 80:
                val = val[:80] + "..."
            print(f"  [✓] {label:25s} ({poids:>2} pts)  → {val}")
        else:
            print(f"  [✗] {label:25s} ({poids:>2} pts)  → MANQUANT")

    pourcentage = round((score / max_score) * 100) if max_score else 0

    if pourcentage >= 97:   grade = 'A+'
    elif pourcentage >= 85: grade = 'A'
    elif pourcentage >= 70: grade = 'B'
    elif pourcentage >= 50: grade = 'C'
    elif pourcentage >= 30: grade = 'D'
    elif pourcentage >= 10: grade = 'E'
    else:                   grade = 'F'

    print(f"\n  Score brut      : {score}/{max_score}")
    print(f"  Score normalisé : {pourcentage}/100")
    print(f"  GRADE           : {grade}")

    # Server version exposure
    server = headers_lower.get('server', '')
    if server and re.search(r'[0-9]+\.[0-9]+', server):
        print(f"  [⚠] Version serveur exposée : {server}")
    else:
        print(f"  [✓] Pas de version serveur exposée : {server or '(absent)'}")

    powered_by = headers_lower.get('x-powered-by', '')
    if powered_by:
        print(f"  [⚠] X-Powered-By exposé : {powered_by}")
    else:
        print(f"  [✓] Pas de X-Powered-By")

    return grade, score, pourcentage


# ── Étape 4 : Lighthouse ─────────────────────────────────────────
LIGHTHOUSE_API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"


def run_lighthouse(url, api_key):
    print("\n" + "=" * 60)
    print("ÉTAPE 4 — Lighthouse / PageSpeed Insights")
    print("=" * 60)

    # Nettoyage clé et URL
    key = (api_key or '').strip().replace('"', '').replace("'", "").strip()
    clean_url = url.strip().replace('"', '').replace("'", "").strip()

    print(f"  URL    : {clean_url}")
    print(f"  API Key: {'(présente, ' + key[:6] + '...' + key[-4:] + ')' if key else '(AUCUNE — quota public limité)'}")

    # Le paramètre category doit être répété pour chaque catégorie
    # (l'API ne renvoie QUE performance par défaut si absent)
    params = {
        'url': clean_url,
        'strategy': 'mobile',
        'category': ['performance', 'accessibility', 'best-practices', 'seo'],
    }
    if key:
        params['key'] = key

    # Affichage params sans exposer la clé complète
    safe_params = {k: (v if k != 'key' else key[:6] + '...' + key[-4:] if key else '(aucune)') for k, v in params.items()}
    print(f"  Params envoyés : {json.dumps(safe_params, indent=2)[:400]}")

    try:
        print("\n  [...] Appel API Google...")
        r = requests.get(LIGHTHOUSE_API_URL, params=params, timeout=60)
        print(f"  HTTP {r.status_code}")

        if r.status_code != 200:
            print(f"\n  [FAIL] Réponse brute de Google :")
            print(f"  {r.text[:1000]}")
            return

        data = r.json()
        lh = data.get('lighthouseResult', {})

        if not lh:
            print(f"  [FAIL] Pas de lighthouseResult dans la réponse")
            print(f"  Clés disponibles : {list(data.keys())}")
            return

        cats = lh.get('categories', {})
        audits = lh.get('audits', {})

        print("\n  Scores Lighthouse :")
        for cat_key, label in [
            ('performance', 'Performance'),
            ('accessibility', 'Accessibility'),
            ('best-practices', 'Best Practices'),
            ('seo', 'SEO'),
        ]:
            v = cats.get(cat_key, {}).get('score')
            val = int(v * 100) if v is not None else None
            print(f"    {label:20s} : {val}")

        print("\n  Metrics :")
        for metric_key, label in [
            ('first-contentful-paint', 'FCP'),
            ('largest-contentful-paint', 'LCP'),
            ('total-blocking-time', 'TBT'),
            ('cumulative-layout-shift', 'CLS'),
            ('speed-index', 'Speed Index'),
        ]:
            v = audits.get(metric_key, {}).get('numericValue')
            if metric_key == 'cumulative-layout-shift':
                val = v
            elif v is not None:
                val = round(v / 1000, 2)
            else:
                val = None
            print(f"    {label:20s} : {val}")

    except Exception as e:
        print(f"  [FAIL] Exception : {e}")


# ── Main ──────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2:
        print(f"Usage: python3 {sys.argv[0]} <url>")
        print(f"  Ex:  python3 {sys.argv[0]} https://backstage.click/diagnostic/")
        sys.exit(1)

    url = sys.argv[1]
    if not url.startswith(('http://', 'https://')):
        url = 'https://' + url

    print(f"\n{'#' * 60}")
    print(f"#  DIAGNOSTIC EXPLICITE — {url}")
    print(f"{'#' * 60}")

    # Étape 1 : Fetch
    response = fetch_with_playwright(url)
    if response is None:
        print("\n  → Bascule vers requests...")
        response = fetch_with_requests(url)

    if response is None:
        print("\n[ABORT] Impossible de récupérer la page")
        sys.exit(1)

    # Étape 2 : Dump headers
    headers_lower = dump_headers(response)

    # Étape 3 : Security
    grade, score, pct = analyze_security_headers(headers_lower)

    # Étape 4 : Lighthouse
    run_lighthouse(url, LIGHTHOUSE_API_KEY)

    print("\n" + "=" * 60)
    print("DIAGNOSTIC TERMINÉ")
    print("=" * 60)


if __name__ == '__main__':
    main()
