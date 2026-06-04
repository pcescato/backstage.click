"""
Scanner V2 — Report Generator (Backstage Edition)
==================================================
Adapté depuis report_generator_mysql.py.
Garde uniquement : get_site_details().
Supprimé : export_to_csv(), generate_email_template(),
           print_dashboard(), get_top_opportunities(), main().
"""

import pymysql
import pymysql.cursors
from datetime import datetime
from typing import Dict, List

from db_config import BACKSTAGE_DB


def _get_conn():
    return pymysql.connect(
        **BACKSTAGE_DB,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


class ReportGenerator:

    def __init__(self):
        self.conn = _get_conn()

    def get_site_details(self, domain: str) -> Dict:
        with self.conn.cursor() as cursor:
            cursor.execute('SELECT * FROM sites WHERE domain = %s', (domain,))
            site = cursor.fetchone()
            if not site:
                raise ValueError(f"Site '{domain}' introuvable")

            cursor.execute('''
                SELECT * FROM scans
                WHERE site_id = %s
                ORDER BY scan_date DESC LIMIT 1
            ''', (site['id'],))
            latest_scan = cursor.fetchone() or {}

            recommendations = []
            vulnerabilities = []

            if latest_scan:
                sid = latest_scan['id']
                cursor.execute('''
                    SELECT * FROM recommendations WHERE scan_id = %s
                    ORDER BY
                        CASE priority
                            WHEN 'critical' THEN 1
                            WHEN 'high'     THEN 2
                            WHEN 'medium'   THEN 3
                            WHEN 'low'      THEN 4
                            ELSE 5
                        END
                ''', (sid,))
                recommendations = cursor.fetchall()

                cursor.execute('''
                    SELECT * FROM vulnerabilities WHERE scan_id = %s
                    ORDER BY
                        CASE severity
                            WHEN 'critical' THEN 1
                            WHEN 'high'     THEN 2
                            WHEN 'medium'   THEN 3
                            WHEN 'low'      THEN 4
                            ELSE 5
                        END
                ''', (sid,))
                vulnerabilities = cursor.fetchall()

        return {
            'site':            site,
            'latest_scan':     latest_scan,
            'recommendations': recommendations,
            'vulnerabilities': vulnerabilities,
        }

    def close(self):
        if self.conn:
            self.conn.close()
