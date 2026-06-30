"""
Scan Worker — Backstage
=======================
Cron job : dépile scan_queue, scanne, envoie le rapport par email.

Crontab recommandé :
    */5 * * * * /www/wwwroot/backstage.click/scanner/venv/bin/python \
                /www/wwwroot/backstage.click/scanner/scan_worker.py \
                >> /www/wwwroot/backstage.click/scanner/logs/worker.log 2>&1
"""

import sys
import os
import logging
from datetime import datetime

import pymysql
import pymysql.cursors

# Ajoute le dossier scanner/ au path pour les imports locaux
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from db_config import BACKSTAGE_DB
from website_scanner import WebsiteScanner
from report_generator import ReportGenerator
from scan_mailer import ScanMailer

# ── Clé API Lighthouse ─────────────────────────────────────────
try:
    from db_config import LIGHTHOUSE_API_KEY as _LH_KEY
except ImportError:
    _LH_KEY = None

# ── Logging ─────────────────────────────────────────────────────
LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs', 'worker.log')
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
log = logging.getLogger(__name__)


def _get_conn():
    return pymysql.connect(
        **BACKSTAGE_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def fetch_pending(conn) -> list:
    with conn.cursor() as cursor:
        cursor.execute('''
            SELECT id, url, email
            FROM scan_queue
            WHERE status = 'pending'
            ORDER BY created_at ASC
            LIMIT 5
        ''')
        return cursor.fetchall()


def mark_processing(conn, queue_id: int):
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE scan_queue SET status = 'processing' WHERE id = %s",
            (queue_id,)
        )
    conn.commit()


def mark_done(conn, queue_id: int):
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE scan_queue SET status = 'done', processed_at = %s WHERE id = %s",
            (datetime.now(), queue_id)
        )
    conn.commit()


def mark_error(conn, queue_id: int, error_msg: str):
    with conn.cursor() as cursor:
        cursor.execute(
            "UPDATE scan_queue SET status = 'error', processed_at = %s, error_msg = %s WHERE id = %s",
            (datetime.now(), error_msg[:1000], queue_id)
        )
    conn.commit()


def process_job(job: dict):
    queue_id = job['id']
    url      = job['url']
    email    = job['email']

    log.info(f"Traitement #{queue_id} : {url} → {email}")

    conn = _get_conn()
    mark_processing(conn, queue_id)

    scanner   = WebsiteScanner(lighthouse_api_key=_LH_KEY)
    reporter  = ReportGenerator()
    mailer    = ScanMailer()

    try:
        # 1. Scanner le site
        scan_data = scanner.scan_url(url, contact_email=email)

        if scan_data.get('error'):
            raise RuntimeError(f"Scan failed: {scan_data['error']}")

        domain = scan_data['domain']

        # 2. Récupérer les détails depuis la base
        details = reporter.get_site_details(domain)

        # 3. Envoyer le rapport
        sent = mailer.send_report(
            to_email        = email,
            domain          = domain,
            site            = details['site'],
            scan            = details['latest_scan'],
            recommendations = details['recommendations'],
            vulnerabilities = details['vulnerabilities'],
        )

        if not sent:
            raise RuntimeError("Échec de l'envoi email")

        mark_done(conn, queue_id)
        log.info(f"✅ #{queue_id} terminé : {domain}")

    except Exception as e:
        error_msg = str(e)
        log.error(f"❌ #{queue_id} erreur : {error_msg}")
        mark_error(conn, queue_id, error_msg)

    finally:
        scanner.close()
        reporter.close()
        conn.close()


def main():
    log.info("=== Scan Worker démarré ===")

    conn = _get_conn()
    jobs = fetch_pending(conn)
    conn.close()

    if not jobs:
        log.info("Aucun job en attente.")
        return

    log.info(f"{len(jobs)} job(s) à traiter.")

    for job in jobs:
        try:
            process_job(job)
        except Exception as e:
            log.error(f"Erreur inattendue sur job #{job['id']} : {e}")

    log.info("=== Scan Worker terminé ===")


if __name__ == '__main__':
    main()
