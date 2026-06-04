"""
Website Scanner V2 — Backstage Edition
=======================================
Adapté depuis website_scanner_v2_mysql.py.
Supprimé : fetch_urls_from_prospection(), main(), PROSPECTION_CONFIG.
Usage : from website_scanner import WebsiteScanner
"""

import pymysql
import pymysql.cursors
import requests
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import urllib.parse
from bs4 import BeautifulSoup
import warnings
warnings.filterwarnings('ignore')

from db_config import BACKSTAGE_DB


def _get_conn(config: dict) -> pymysql.connections.Connection:
    return pymysql.connect(
        **config,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


class DatabaseManager:

    def __init__(self, config: dict = None):
        self.config = config or BACKSTAGE_DB
        self.conn = None
        self.init_database()

    def _connect(self):
        self.conn = _get_conn(self.config)

    def _cursor(self):
        try:
            self.conn.ping(reconnect=True)
        except Exception:
            self._connect()
        return self.conn.cursor()

    def init_database(self):
        self._connect()
        cursor = self.conn.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sites (
                id               INT AUTO_INCREMENT PRIMARY KEY,
                domain           VARCHAR(255) NOT NULL UNIQUE,
                url              TEXT NOT NULL,
                first_scan_date  DATETIME,
                last_scan_date   DATETIME,
                scan_count       INT DEFAULT 0,
                status           VARCHAR(50) DEFAULT 'active',
                contact_email    VARCHAR(255),
                opportunity_score INT,
                priority          VARCHAR(20),
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS scans (
                id          INT AUTO_INCREMENT PRIMARY KEY,
                site_id     INT NOT NULL,
                scan_date   DATETIME NOT NULL,
                performance_score    INT,
                accessibility_score  INT,
                best_practices_score INT,
                seo_score            INT,
                fcp         FLOAT, lcp FLOAT, tbt FLOAT, cls FLOAT,
                speed_index FLOAT,
                is_wordpress        TINYINT(1),
                wp_version          VARCHAR(20),
                wp_version_outdated TINYINT(1),
                wp_latest_version   VARCHAR(20),
                wp_theme            VARCHAR(255),
                php_version          VARCHAR(20),
                php_version_outdated TINYINT(1),
                php_eol_date         VARCHAR(20),
                php_latest_version   VARCHAR(20),
                server_software VARCHAR(255),
                server_type     VARCHAR(50),
                https_enabled   TINYINT(1),
                ssl_valid       TINYINT(1),
                security_grade   VARCHAR(5),
                security_score   INT,
                has_hsts                  TINYINT(1),
                has_csp                   TINYINT(1),
                has_x_frame_options       TINYINT(1),
                has_x_content_type_options TINYINT(1),
                has_referrer_policy       TINYINT(1),
                has_permissions_policy    TINYINT(1),
                exposes_server_version    TINYINT(1),
                exposes_php_version       TINYINT(1),
                raw_data MEDIUMTEXT,
                FOREIGN KEY (site_id) REFERENCES sites(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vulnerabilities (
                id             INT AUTO_INCREMENT PRIMARY KEY,
                scan_id        INT NOT NULL,
                type           VARCHAR(100),
                severity       VARCHAR(20),
                title          VARCHAR(255),
                description    TEXT,
                recommendation TEXT,
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS recommendations (
                id                 INT AUTO_INCREMENT PRIMARY KEY,
                scan_id            INT NOT NULL,
                type               VARCHAR(100),
                title              VARCHAR(255),
                description        TEXT,
                estimated_gain     VARCHAR(255),
                estimated_effort   VARCHAR(100),
                estimated_cost_min INT,
                estimated_cost_max INT,
                priority           VARCHAR(20),
                FOREIGN KEY (scan_id) REFERENCES scans(id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        ''')

        self.conn.commit()

    def add_site(self, domain: str, url: str, contact_email: str = None) -> int:
        cursor = self._cursor()
        cursor.execute(
            'INSERT IGNORE INTO sites (domain, url, first_scan_date, contact_email) VALUES (%s, %s, %s, %s)',
            (domain, url, datetime.now(), contact_email)
        )
        self.conn.commit()
        cursor.execute('SELECT id FROM sites WHERE domain = %s', (domain,))
        row = cursor.fetchone()
        return row['id']

    def add_scan(self, site_id: int, scan_data: Dict) -> int:
        cursor = self._cursor()
        cursor.execute('''
            INSERT INTO scans (
                site_id, scan_date,
                performance_score, accessibility_score, best_practices_score, seo_score,
                fcp, lcp, tbt, cls, speed_index,
                is_wordpress, wp_version, wp_version_outdated, wp_latest_version, wp_theme,
                php_version, php_version_outdated, php_eol_date, php_latest_version,
                server_software, server_type,
                https_enabled,
                security_grade, security_score,
                has_hsts, has_csp, has_x_frame_options, has_x_content_type_options,
                has_referrer_policy, has_permissions_policy,
                exposes_server_version, exposes_php_version,
                raw_data
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s
            )
        ''', (
            site_id, datetime.now(),
            scan_data.get('performance_score'),
            scan_data.get('accessibility_score'),
            scan_data.get('best_practices_score'),
            scan_data.get('seo_score'),
            scan_data.get('fcp'),
            scan_data.get('lcp'),
            scan_data.get('tbt'),
            scan_data.get('cls'),
            scan_data.get('speed_index'),
            scan_data.get('is_wordpress'),
            scan_data.get('wp_version'),
            scan_data.get('wp_version_outdated'),
            scan_data.get('wp_latest_version'),
            scan_data.get('wp_theme'),
            scan_data.get('php_version'),
            scan_data.get('php_version_outdated'),
            scan_data.get('php_eol_date'),
            scan_data.get('php_latest_version'),
            scan_data.get('server_software'),
            scan_data.get('server_type'),
            scan_data.get('https_enabled'),
            scan_data.get('security_grade'),
            scan_data.get('security_score'),
            scan_data.get('has_hsts'),
            scan_data.get('has_csp'),
            scan_data.get('has_x_frame_options'),
            scan_data.get('has_x_content_type_options'),
            scan_data.get('has_referrer_policy'),
            scan_data.get('has_permissions_policy'),
            scan_data.get('exposes_server_version'),
            scan_data.get('exposes_php_version'),
            json.dumps(scan_data.get('raw_data', {}))
        ))
        self.conn.commit()
        return cursor.lastrowid

    def update_site_scores(self, site_id: int, opportunity_score: int, priority: str):
        cursor = self._cursor()
        cursor.execute('''
            UPDATE sites
            SET opportunity_score = %s,
                priority          = %s,
                last_scan_date    = %s,
                scan_count        = scan_count + 1
            WHERE id = %s
        ''', (opportunity_score, priority, datetime.now(), site_id))
        self.conn.commit()

    def add_vulnerability(self, scan_id: int, vuln_data: Dict):
        cursor = self._cursor()
        cursor.execute('''
            INSERT INTO vulnerabilities
                (scan_id, type, severity, title, description, recommendation)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (
            scan_id,
            vuln_data.get('type'),
            vuln_data.get('severity'),
            vuln_data.get('title'),
            vuln_data.get('description'),
            vuln_data.get('recommendation'),
        ))
        self.conn.commit()

    def add_recommendation(self, scan_id: int, rec_data: Dict):
        cursor = self._cursor()
        cursor.execute('''
            INSERT INTO recommendations
                (scan_id, type, title, description, estimated_gain,
                 estimated_effort, estimated_cost_min, estimated_cost_max, priority)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ''', (
            scan_id,
            rec_data.get('type'),
            rec_data.get('title'),
            rec_data.get('description'),
            rec_data.get('estimated_gain'),
            rec_data.get('estimated_effort'),
            rec_data.get('estimated_cost_min'),
            rec_data.get('estimated_cost_max'),
            rec_data.get('priority'),
        ))
        self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()


class WordPressDetector:

    WP_LATEST_VERSION = "7.0"

    @staticmethod
    def detect(url: str) -> Dict:
        result = {
            'is_wordpress': False,
            'version':      None,
            'version_outdated': False,
            'latest_version': WordPressDetector.WP_LATEST_VERSION,
            'theme':  None,
            'theme_version': None,
            'detection_confidence': 'unknown',
        }

        base = url.rstrip('/')
        session_headers = {'User-Agent': 'Mozilla/5.0 (Scanner/2.0)'}

        try:
            response = requests.get(url, timeout=10,
                                    headers=session_headers, verify=False)
            content = response.text

            m = re.search(
                r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']WordPress ([0-9.]+)',
                content, re.IGNORECASE
            )
            if not m:
                m = re.search(
                    r'<meta[^>]+content=["\']WordPress ([0-9.]+)["\'][^>]+name=["\']generator',
                    content, re.IGNORECASE
                )
            if m:
                result['is_wordpress'] = True
                result['version'] = m.group(1)
                result['detection_confidence'] = 'high'

            if '/wp-content/' in content or '/wp-includes/' in content:
                result['is_wordpress'] = True
                if not result['version']:
                    result['detection_confidence'] = 'medium'

            if not result['is_wordpress']:
                try:
                    r = requests.head(f"{base}/wp-login.php", timeout=5,
                                      headers=session_headers, verify=False,
                                      allow_redirects=True)
                    if r.status_code in (200, 302):
                        result['is_wordpress'] = True
                        result['detection_confidence'] = 'high'
                except Exception:
                    pass

            if not result['version']:
                try:
                    r = requests.get(f"{base}/wp-json/", timeout=5,
                                     headers=session_headers, verify=False)
                    if r.status_code == 200:
                        result['is_wordpress'] = True
                        if result['detection_confidence'] == 'unknown':
                            result['detection_confidence'] = 'high'
                except Exception:
                    pass

            if not result['version']:
                try:
                    r = requests.get(f"{base}/readme.html", timeout=5,
                                     headers=session_headers, verify=False)
                    if r.status_code == 200:
                        vm = re.search(r'Version ([0-9.]+)', r.text)
                        if vm:
                            result['version'] = vm.group(1)
                            result['is_wordpress'] = True
                            result['detection_confidence'] = 'high'
                except Exception:
                    pass

            tm = re.search(r'/wp-content/themes/([^/\'"]+)', content)
            if tm:
                result['theme'] = tm.group(1)

            if result['version']:
                try:
                    cur = tuple(map(int, result['version'].split('.')))
                    lat = tuple(map(int, WordPressDetector.WP_LATEST_VERSION.split('.')))
                    result['version_outdated'] = cur < lat
                except Exception:
                    pass

        except Exception as e:
            print(f"   ⚠️  WordPress detection error: {e}")

        return result


class PHPDetector:

    PHP_EOL_DATES = {
        '5.6': '2018-12-31', '7.0': '2019-01-10', '7.1': '2019-12-01',
        '7.2': '2020-11-30', '7.3': '2021-12-06', '7.4': '2022-11-28',
        '8.0': '2023-11-26', '8.1': '2025-11-25', '8.2': '2026-12-08',
        '8.3': '2027-12-31', '8.4': '2027-12-31',
    }
    PHP_LATEST_VERSION = "8.3"

    @staticmethod
    def detect(response) -> Dict:
        result = {
            'version': None, 'version_outdated': False,
            'eol_date': None, 'latest_version': PHPDetector.PHP_LATEST_VERSION,
            'major_version': None, 'is_eol': False,
        }
        headers = response.headers
        for header_name in ('X-Powered-By', 'Server'):
            if header_name in headers:
                m = re.search(r'PHP/([0-9.]+)', headers[header_name])
                if m:
                    result['version'] = m.group(1)
                    break
        if result['version']:
            parts = result['version'].split('.')
            if len(parts) >= 2:
                major_minor = f"{parts[0]}.{parts[1]}"
                result['major_version'] = major_minor
                if major_minor in PHPDetector.PHP_EOL_DATES:
                    eol_str = PHPDetector.PHP_EOL_DATES[major_minor]
                    result['eol_date'] = eol_str
                    result['is_eol'] = datetime.now() > datetime.strptime(eol_str, '%Y-%m-%d')
                try:
                    cur = tuple(map(int, parts[:2]))
                    lat = tuple(map(int, PHPDetector.PHP_LATEST_VERSION.split('.')))
                    result['version_outdated'] = cur < lat
                except Exception:
                    pass
        return result


class SecurityHeadersAnalyzer:

    REQUIRED_HEADERS = {
        'Strict-Transport-Security': {'grade_weight': 50, 'purpose': 'Force HTTPS'},
        'Content-Security-Policy':   {'grade_weight': 30, 'purpose': 'Prevent XSS'},
        'X-Frame-Options':           {'grade_weight': 10, 'purpose': 'Prevent clickjacking'},
        'X-Content-Type-Options':    {'grade_weight': 5,  'purpose': 'Prevent MIME sniffing'},
        'Referrer-Policy':           {'grade_weight': 3,  'purpose': 'Control referrer'},
        'Permissions-Policy':        {'grade_weight': 2,  'purpose': 'Disable unused features'},
    }

    @staticmethod
    def analyze(response) -> Dict:
        headers = response.headers
        result = {
            'grade': 'F', 'score': 0,
            'has_hsts': False, 'has_csp': False,
            'has_x_frame_options': False, 'has_x_content_type_options': False,
            'has_referrer_policy': False, 'has_permissions_policy': False,
            'exposes_server_version': False, 'exposes_php_version': False,
        }
        flag_map = {
            'Strict-Transport-Security': 'has_hsts',
            'Content-Security-Policy':   'has_csp',
            'X-Frame-Options':           'has_x_frame_options',
            'X-Content-Type-Options':    'has_x_content_type_options',
            'Referrer-Policy':           'has_referrer_policy',
            'Permissions-Policy':        'has_permissions_policy',
        }
        for header, cfg in SecurityHeadersAnalyzer.REQUIRED_HEADERS.items():
            if header in headers:
                result['score'] += cfg['grade_weight']
                result[flag_map[header]] = True

        if 'Server' in headers and re.search(r'[0-9]+\.[0-9]+', headers['Server']):
            result['exposes_server_version'] = True
        if 'X-Powered-By' in headers:
            result['exposes_php_version'] = True

        score = result['score']
        if score >= 90:   result['grade'] = 'A+'
        elif score >= 75: result['grade'] = 'A'
        elif score >= 50: result['grade'] = 'B'
        elif score >= 30: result['grade'] = 'C'
        elif score >= 10: result['grade'] = 'D'
        else:             result['grade'] = 'F'

        return result


class LighthouseScanner:

    API_URL = "https://www.googleapis.com/pagespeedonline/v5/runPagespeed"

    def __init__(self, api_key: str = None):
        self.api_key = api_key

    def scan(self, url: str) -> Dict:
        params = {'url': url, 'strategy': 'mobile', 'category': [
            'performance', 'accessibility', 'best-practices', 'seo'
        ]}
        if self.api_key:
            params['key'] = self.api_key
        try:
            r = requests.get(self.API_URL, params=params, timeout=60)
            if r.status_code != 200:
                return {'success': False, 'error': f"HTTP {r.status_code}"}
            data = r.json()
            cats   = data.get('lighthouseResult', {}).get('categories', {})
            audits = data.get('lighthouseResult', {}).get('audits', {})

            def score(key):
                v = cats.get(key, {}).get('score')
                return int(v * 100) if v is not None else None

            def metric(key):
                v = audits.get(key, {}).get('numericValue')
                return round(v / 1000, 2) if v is not None else None

            return {
                'success': True,
                'scores': {
                    'performance':    score('performance'),
                    'accessibility':  score('accessibility'),
                    'best_practices': score('best-practices'),
                    'seo':            score('seo'),
                },
                'metrics': {
                    'fcp':         metric('first-contentful-paint'),
                    'lcp':         metric('largest-contentful-paint'),
                    'tbt':         metric('total-blocking-time'),
                    'cls':         audits.get('cumulative-layout-shift', {}).get('numericValue'),
                    'speed_index': metric('speed-index'),
                },
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}


class OpportunityScorer:

    @staticmethod
    def calculate(scan_data: Dict) -> Tuple[int, str, List[Dict]]:
        score = 0
        quick_wins = []

        if scan_data.get('is_wordpress') and scan_data.get('wp_version_outdated'):
            wp = scan_data.get('wp_version', '')
            try:
                major = int(wp.split('.')[0]) if wp else 99
                if major < 6:
                    score += 25
                elif wp.startswith('6.') and int(wp.split('.')[1]) <= 3:
                    score += 20
                else:
                    score += 10
                quick_wins.append({
                    'type': 'wp_update',
                    'title': 'Mise à jour WordPress',
                    'description': f'Mettre à jour WordPress {wp} → {scan_data.get("wp_latest_version")}',
                    'estimated_gain': '+10-15 points Lighthouse',
                    'estimated_effort': '1-2 heures',
                    'estimated_cost_min': 200,
                    'estimated_cost_max': 500,
                    'priority': 'high',
                })
            except Exception:
                pass

        if scan_data.get('php_version') and scan_data.get('php_eol_date'):
            eol = datetime.strptime(scan_data['php_eol_date'], '%Y-%m-%d')
            if datetime.now() > eol:
                score += 35
                quick_wins.append({
                    'type': 'php_upgrade',
                    'title': 'Mise à jour PHP (CRITIQUE)',
                    'description': f"Mettre à jour PHP {scan_data.get('php_version')} → 8.2+ (EOL depuis {scan_data['php_eol_date']})",
                    'estimated_gain': '+25-35% performances, correctifs sécurité',
                    'estimated_effort': '2-4 heures',
                    'estimated_cost_min': 400,
                    'estimated_cost_max': 800,
                    'priority': 'critical',
                })
            elif scan_data.get('php_version_outdated'):
                score += 20
                quick_wins.append({
                    'type': 'php_upgrade',
                    'title': 'Mise à jour PHP',
                    'description': f"Mettre à jour PHP {scan_data.get('php_version')} → {scan_data.get('php_latest_version')}",
                    'estimated_gain': '+15-25% performances',
                    'estimated_effort': '2-4 heures',
                    'estimated_cost_min': 300,
                    'estimated_cost_max': 600,
                    'priority': 'high',
                })

        perf = scan_data.get('performance_score', 100)
        if perf is not None:
            if perf < 40:    score += 25
            elif perf < 50:  score += 20
            elif perf < 65:  score += 15

        grade = scan_data.get('security_grade', 'A')
        if grade == 'F':
            score += 15
            quick_wins.append({
                'type': 'security_headers',
                'title': 'Correction des headers de sécurité',
                'description': 'Ajout des headers manquants (Grade F → A+)',
                'estimated_gain': 'Protection XSS, clickjacking, MITM',
                'estimated_effort': '30 minutes',
                'estimated_cost_min': 150,
                'estimated_cost_max': 300,
                'priority': 'high',
            })
        elif grade in ('D', 'C'):
            score += 10
            quick_wins.append({
                'type': 'security_headers',
                'title': 'Amélioration des headers de sécurité',
                'description': f'Améliorer les headers (Grade {grade} → A)',
                'estimated_gain': 'Sécurité renforcée',
                'estimated_effort': '20 minutes',
                'estimated_cost_min': 100,
                'estimated_cost_max': 200,
                'priority': 'medium',
            })

        if scan_data.get('exposes_server_version') or scan_data.get('exposes_php_version'):
            score += 5

        score = min(score, 100)
        if score >= 80:   priority = 'critical'
        elif score >= 60: priority = 'high'
        elif score >= 40: priority = 'medium'
        else:             priority = 'low'

        return score, priority, quick_wins


class WebsiteScanner:

    def __init__(self, db_config: dict = None, lighthouse_api_key: str = None):
        self.db = DatabaseManager(db_config)
        self.lighthouse = LighthouseScanner(lighthouse_api_key)

    def scan_url(self, url: str, contact_email: str = None) -> Dict:
        print(f"\n{'='*60}")
        print(f"🌐 Scanning: {url}")
        print(f"{'='*60}")

        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        domain = url.split('//')[1].split('/')[0]
        site_id = self.db.add_site(domain, url, contact_email=contact_email)

        scan_data = {
            'url': url,
            'domain': domain,
            'scan_date': datetime.now().isoformat(),
        }

        try:
            print("   🔍 Fetching page...")
            response = requests.get(
                url, timeout=10,
                headers={'User-Agent': 'Mozilla/5.0 (Scanner/2.0)'},
                verify=False
            )
            scan_data['https_enabled'] = url.startswith('https://')

            print("   🔍 Checking WordPress...")
            wp = WordPressDetector.detect(url)
            scan_data.update({
                'is_wordpress':        wp['is_wordpress'],
                'wp_version':          wp['version'],
                'wp_version_outdated': wp['version_outdated'],
                'wp_latest_version':   wp['latest_version'],
                'wp_theme':            wp['theme'],
            })

            print("   🔍 Checking PHP...")
            php = PHPDetector.detect(response)
            scan_data.update({
                'php_version':          php['version'],
                'php_version_outdated': php['version_outdated'],
                'php_eol_date':         php['eol_date'],
                'php_latest_version':   php['latest_version'],
            })

            server = response.headers.get('Server', 'Unknown')
            scan_data['server_software'] = server
            sl = server.lower()
            scan_data['server_type'] = (
                'nginx'     if 'nginx'     in sl else
                'apache'    if 'apache'    in sl else
                'litespeed' if 'litespeed' in sl else
                'unknown'
            )

            print("   🔒 Analyzing security headers...")
            sec = SecurityHeadersAnalyzer.analyze(response)
            scan_data.update({
                'security_grade':             sec['grade'],
                'security_score':             sec['score'],
                'has_hsts':                   sec['has_hsts'],
                'has_csp':                    sec['has_csp'],
                'has_x_frame_options':        sec['has_x_frame_options'],
                'has_x_content_type_options': sec['has_x_content_type_options'],
                'has_referrer_policy':        sec['has_referrer_policy'],
                'has_permissions_policy':     sec['has_permissions_policy'],
                'exposes_server_version':     sec['exposes_server_version'],
                'exposes_php_version':        sec['exposes_php_version'],
            })
            print(f"   🔒 Security Grade: {sec['grade']}")

            print("   ⚡ Running Lighthouse audit...")
            lh = self.lighthouse.scan(url)
            if lh['success']:
                scan_data.update({
                    'performance_score':    lh['scores']['performance'],
                    'accessibility_score':  lh['scores']['accessibility'],
                    'best_practices_score': lh['scores']['best_practices'],
                    'seo_score':            lh['scores']['seo'],
                    'fcp':                  lh['metrics']['fcp'],
                    'lcp':                  lh['metrics']['lcp'],
                    'tbt':                  lh['metrics']['tbt'],
                    'cls':                  lh['metrics']['cls'],
                    'speed_index':          lh['metrics']['speed_index'],
                })
                print(f"   ⚡ Performance: {lh['scores']['performance']}/100")
            else:
                print(f"   ⚠️  Lighthouse failed: {lh.get('error')}")

            print("   📊 Calculating opportunity score...")
            opp_score, priority, quick_wins = OpportunityScorer.calculate(scan_data)
            print(f"   🎯 Opportunity Score: {opp_score}/100 ({priority.upper()})")

            scan_id = self.db.add_scan(site_id, scan_data)
            for qw in quick_wins:
                self.db.add_recommendation(scan_id, qw)
            self.db.update_site_scores(site_id, opp_score, priority)

            vulns = self._identify_vulnerabilities(scan_data)
            for v in vulns:
                self.db.add_vulnerability(scan_id, v)

            scan_data.update({
                'opportunity_score': opp_score,
                'priority':          priority,
                'quick_wins':        quick_wins,
                'vulnerabilities':   vulns,
            })
            return scan_data

        except Exception as e:
            print(f"   ❌ Scan error: {e}")
            return {'url': url, 'error': str(e)}

    def _identify_vulnerabilities(self, scan_data: Dict) -> List[Dict]:
        vulns = []
        if scan_data.get('php_eol_date'):
            if datetime.now() > datetime.strptime(scan_data['php_eol_date'], '%Y-%m-%d'):
                vulns.append({
                    'type': 'php_eol', 'severity': 'critical',
                    'title': 'PHP en fin de vie',
                    'description': f"PHP {scan_data['php_version']} EOL depuis {scan_data['php_eol_date']}.",
                    'recommendation': f"Mettre à jour vers PHP {scan_data.get('php_latest_version', '8.2')}.",
                })
        if scan_data.get('wp_version_outdated'):
            vulns.append({
                'type': 'wordpress_outdated', 'severity': 'high',
                'title': 'WordPress obsolète',
                'description': f"WP {scan_data['wp_version']} < {scan_data.get('wp_latest_version')}",
                'recommendation': 'Mettre à jour WordPress.',
            })
        if not scan_data.get('has_hsts') and scan_data.get('https_enabled'):
            vulns.append({
                'type': 'missing_hsts', 'severity': 'medium',
                'title': 'Header HSTS manquant',
                'description': 'Vulnérable aux attaques de downgrade.',
                'recommendation': 'Ajouter le header HSTS avec max-age=31536000',
            })
        if not scan_data.get('has_csp'):
            vulns.append({
                'type': 'missing_csp', 'severity': 'medium',
                'title': 'Content-Security-Policy manquant',
                'description': 'Pas de CSP, vulnérable aux XSS.',
                'recommendation': 'Implémenter un header CSP.',
            })
        if scan_data.get('exposes_php_version') or scan_data.get('exposes_server_version'):
            vulns.append({
                'type': 'information_disclosure', 'severity': 'low',
                'title': 'Exposition des versions logicielles',
                'description': 'Les headers exposent les versions du serveur.',
                'recommendation': 'Masquer les versions dans Server/X-Powered-By.',
            })
        return vulns

    def close(self):
        self.db.close()
