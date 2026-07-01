# Méthodologie de scan — correctifs Backstage → GCF Prospection

## Contexte

Le scanner `website_scanner.py` souffrait de deux bugs critiques :
1. **Security Grade F** au lieu de **A+** sur les sites derrière Cloudflare
2. **Lighthouse HTTP 400** (clé API expirée) ou **HTTP 429** (quota sans clé)

## Root causes identifiées et corrections

### 1. Security Headers — casse des clés de dictionnaire

**Cause** : `REQUIRED_HEADERS` utilisait des clés en majuscules (`'Strict-Transport-Security'`) alors que Cloudflare renvoie les en-têtes en minuscules (`'strict-transport-security'`). Aucun header n'était détecté → score 0 → grade F.

**Correction** :
```python
@staticmethod
def analyze(response) -> Dict:
    # Normalisation : toutes les clés en minuscules
    headers = {k.lower(): v for k, v in response.headers.items()}
    
    REQUIRED_HEADERS = {
        'strict-transport-security': {'grade_weight': 50, ...},
        'content-security-policy':   {'grade_weight': 30, ...},
        'x-frame-options':           {'grade_weight': 10, ...},
        'x-content-type-options':    {'grade_weight': 5,  ...},
        'referrer-policy':           {'grade_weight': 3,  ...},
        'permissions-policy':        {'grade_weight': 2,  ...},
    }
    
    flag_map = {  # clés en minuscules aussi
        'strict-transport-security': 'has_hsts',
        ...
    }
    
    for header, cfg in REQUIRED_HEADERS.items():
        header_lower = header.lower()
        if header_lower in headers:
            result['score'] += cfg['grade_weight']
            result[flag_map[header_lower]] = True
```

### 2. Security Headers — blocage Cloudflare via requests

**Cause** : `requests.get()` était bloqué par Cloudflare (challenge JS, 403/503) même avec un User-Agent navigateur. Les headers de sécurité n'étaient jamais reçus.

**Correction** : Utiliser **Playwright** (navigateur headless) pour contourner Cloudflare, avec fallback `requests` si Playwright indisponible.

```python
class PlaywrightResponse:
    """Wrapper pour rendre une réponse Playwright compatible avec requests.Response."""
    def __init__(self, status, headers, text):
        self.status_code = status
        self.headers = headers
        self.text = text

@staticmethod
def _fetch_with_playwright(url):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()
            # NE PAS injecter set_extra_http_headers : le headless shell gère
            # lui-même ses headers, et forcer Accept-Encoding/sec-fetch-* fait
            # que Cloudflare sert l'origin sans ses headers de sécurité.
            resp = page.goto(url, wait_until='networkidle', timeout=30000)
            if resp is None:
                browser.close()
                return None
            headers = dict(resp.headers)  # déjà en minuscules
            content = page.content()
            browser.close()
            return PlaywrightResponse(resp.status, headers, content)
    except Exception:
        return None
```

### 3. DNS localhost — bypass via --host-resolver-rules

**Cause** : Sur le serveur de production, le domaine scanné (ex: `backstage.click`) résout vers `127.0.0.1` via `/etc/hosts`. Playwright tape donc directement l'origin (LiteSpeed) sans passer par Cloudflare → aucun header de sécurité.

**Correction** : Détecter si le domaine résout vers localhost, et si oui, résoudre l'IP publique via **DNS-over-HTTPS (Cloudflare 1.1.1.1)** puis forcer Chrome à utiliser cette IP.

```python
def _resolve_public_dns(domain):
    """Résout via DoH Cloudflare 1.1.1.1."""
    r = requests.get(
        f'https://1.1.1.1/dns-query?name={domain}&type=A',
        headers={'Accept': 'application/dns-json'},
        timeout=5,
    )
    for answer in r.json().get('Answer', []):
        if answer.get('type') == 1:  # A record
            return answer['data']
    return None

def _build_chrome_dns_args(url):
    """Force Chrome à utiliser l'IP publique si localhost détecté."""
    import socket, urllib.parse
    domain = urllib.parse.urlparse(url).hostname
    system_ip = socket.gethostbyname(domain)
    if system_ip in ('127.0.0.1', '::1'):
        public_ip = _resolve_public_dns(domain)
        if public_ip:
            return [f'--host-resolver-rules=MAP {domain} {public_ip}']
    return []

# Dans _fetch_with_playwright :
launch_kwargs = {}
dns_args = _build_chrome_dns_args(url)
if dns_args:
    launch_kwargs['args'] = dns_args
browser = p.chromium.launch(**launch_kwargs)
```

### 4. Détection dynamique du binaire Chromium

**Cause** : Le chemin du binaire Chromium variait selon les versions installées (`chromium-1194`, `chromium_headless_shell-1228`, etc.).

**Correction** :
```python
def _find_chromium():
    base = os.path.expanduser('~/.cache/ms-playwright')
    if not os.path.isdir(base):
        return None
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
```

### 5. Lighthouse — nettoyage clé API et URL

**Cause** : La clé API et l'URL pouvait contenir des espaces cachés ou guillemets résiduels issus du fichier `.env` (ex: `KEY="abc"`), provoquant des erreurs 400.

**Correction** :
```python
@staticmethod
def _clean(value):
    if value is None:
        return ''
    value = str(value).strip()
    value = value.replace('"', '').replace("'", "")
    return value.strip()

def __init__(self, api_key=None):
    if api_key:
        api_key = self._clean(api_key)
    self.api_key = api_key

def scan(self, url):
    url = self._clean(url)
    params = {
        'url': url,
        'strategy': 'mobile',
        'category': ['performance', 'accessibility', 'best-practices', 'seo'],
    }
    if self.api_key:
        params['key'] = self.api_key
```

### 6. Lighthouse — paramètre category

**Cause** : Sans le paramètre `category`, l'API Google PageSpeed v5 ne renvoie QUE `performance` par défaut. Les scores accessibility, best-practices et SEO restent à `None`.

**Correction** : Remettre `category` en liste (requests l'envoie comme paramètres répétés) :
```python
params = {
    'url': url,
    'strategy': 'mobile',
    'category': ['performance', 'accessibility', 'best-practices', 'seo'],
}
```

### 7. Lighthouse — gestion d'erreur avec corps Google

**Cause** : En cas d'erreur HTTP (400, 429, etc.), seul le code status était retourné sans le corps de la réponse, rendant le débogage impossible.

**Correction** :
```python
r = requests.get(self.API_URL, params=params, timeout=60)
if r.status_code != 200:
    error_body = r.text  # corps brut de la réponse Google
    print(f"   ❌ Lighthouse API error HTTP {r.status_code}")
    print(f"   Réponse Google : {error_body}")
    return {
        'success': False,
        'error': f"HTTP {r.status_code}",
        'status_code': r.status_code,
        'response_body': error_body,
    }
```

### 8. Import sécurisé de LIGHTHOUSE_API_KEY

**Cause** : `from db_config import LIGHTHOUSE_API_KEY` provoquait un `ImportError` si `db_config.py` ne l'exportait pas, crashant tout le module.

**Correction** :
```python
from db_config import BACKSTAGE_DB
try:
    from db_config import LIGHTHOUSE_API_KEY
except ImportError:
    LIGHTHOUSE_API_KEY = None
```

### 9. scan_worker.py — clé API hardcodée à None

**Cause** : `scan_worker.py` définissait `LIGHTHOUSE_API_KEY = None` en dur, ignorant la clé présente dans `db_config.py`.

**Correction** :
```python
try:
    from db_config import LIGHTHOUSE_API_KEY as _LH_KEY
except ImportError:
    _LH_KEY = None

scanner = WebsiteScanner(lighthouse_api_key=_LH_KEY)
```

### 10. Barème souple A+ → F

**Cause** : Le barème était trop rigide. Un site avec 95/100 (un seul header manquant) obtenait A au lieu de A+.

**Correction** :
```python
@staticmethod
def _grade_from_score(score):
    if score >= 97:   return 'A+'
    if score >= 85:   return 'A'
    if score >= 70:   return 'B'
    if score >= 50:   return 'C'
    if score >= 30:   return 'D'
    if score >= 10:   return 'E'
    return 'F'
```

## Installation sur le serveur

```bash
# 1. Playwright + Chromium
pip install playwright
python3 -m playwright install chromium
python3 -m playwright install-deps chromium  # dépendances système (libatk, etc.)

# 2. Supprimer le cache Python (vieille clé expirée potentiellement cachée)
rm -rf scanner/__pycache__

# 3. requirements.txt
pymysql>=1.1.0
requests>=2.31.0
beautifulsoup4>=4.12.0
playwright>=1.40.0
```

## Diagnostic

Un script `website_scanner_explicit.py` permet de tester en ligne de commande :
```bash
python3 website_scanner_explicit.py https://example.com
```
Affiche étape par étape : Playwright, DNS, headers reçus, security grade, Lighthouse.

## Résultat attendu

```
Security Grade: A+ (100/100)
Lighthouse:
  Performance:    100
  Accessibility:   100
  Best Practices:  100
  SEO:             100
```
