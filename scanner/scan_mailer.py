"""
Scan Mailer — Backstage
=======================
Formate le rapport de scan et l'envoie par email via SMTP OVH.
"""

import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
from typing import Dict, List

from db_config import SMTP_CONFIG


class ScanMailer:

    def send_report(
        self,
        to_email:        str,
        domain:          str,
        site:            Dict,
        scan:            Dict,
        recommendations: List[Dict],
        vulnerabilities: List[Dict],
    ) -> bool:
        """
        Formate et envoie le rapport de scan par email.
        Retourne True si succès, False sinon.
        """
        subject = f"Diagnostic backstage.click — {domain}"
        body    = self._format_report(
            domain, site, scan, recommendations, vulnerabilities
        )

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"{SMTP_CONFIG['from_name']} <{SMTP_CONFIG['from']}>"
        msg['To']      = to_email
        msg['Reply-To'] = SMTP_CONFIG['from']

        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(
                SMTP_CONFIG['host'],
                SMTP_CONFIG['port'],
                context=context
            ) as server:
                server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
                server.sendmail(
                    SMTP_CONFIG['from'],
                    to_email,
                    msg.as_string()
                )
            print(f"   ✅ Rapport envoyé à {to_email}")
            return True

        except Exception as e:
            print(f"   ❌ Erreur envoi email : {e}")
            return False

    def _format_report(
        self,
        domain:          str,
        site:            Dict,
        scan:            Dict,
        recommendations: List[Dict],
        vulnerabilities: List[Dict],
    ) -> str:

        scan_date = scan.get('scan_date', datetime.now())
        if hasattr(scan_date, 'strftime'):
            date_str = scan_date.strftime('%d/%m/%Y à %H:%M')
        else:
            date_str = str(scan_date)

        sep = '━' * 40

        lines = [
            f"Bonjour,",
            f"",
            f"Voici le résultat du diagnostic de {domain},",
            f"effectué le {date_str}.",
            f"",
            sep,
            "SCORES LIGHTHOUSE (mobile)",
            sep,
            f"Performance      : {scan.get('performance_score', 'N/A')}/100",
            f"Accessibilité    : {scan.get('accessibility_score', 'N/A')}/100",
            f"Bonnes pratiques : {scan.get('best_practices_score', 'N/A')}/100",
            f"SEO              : {scan.get('seo_score', 'N/A')}/100",
            f"",
            sep,
            "SÉCURITÉ",
            sep,
            f"Grade            : {scan.get('security_grade', 'N/A')}",
        ]

        # Détail headers sécurité
        headers_status = []
        for label, key in [
            ('HSTS',              'has_hsts'),
            ('CSP',               'has_csp'),
            ('X-Frame-Options',   'has_x_frame_options'),
            ('X-Content-Type',    'has_x_content_type_options'),
            ('Referrer-Policy',   'has_referrer_policy'),
            ('Permissions-Policy','has_permissions_policy'),
        ]:
            val = scan.get(key)
            status = '✓' if val else '✗'
            headers_status.append(f"  {status} {label}")
        lines += headers_status

        lines += [
            f"",
            sep,
            "STACK TECHNIQUE",
            sep,
        ]

        if scan.get('is_wordpress'):
            wp_line = f"WordPress        : {scan.get('wp_version', 'N/A')}"
            if scan.get('wp_version_outdated'):
                wp_line += " ⚠️  (obsolète)"
            lines.append(wp_line)

        if scan.get('php_version'):
            php_line = f"PHP              : {scan.get('php_version')}"
            if scan.get('php_eol_date'):
                try:
                    eol = datetime.strptime(scan['php_eol_date'], '%Y-%m-%d')
                    if datetime.now() > eol:
                        php_line += f" ⚠️  (EOL depuis {scan['php_eol_date']})"
                except Exception:
                    pass
            lines.append(php_line)

        lines.append(
            f"Serveur          : {scan.get('server_software', 'N/A')}"
        )

        if vulnerabilities:
            lines += [
                f"",
                sep,
                f"VULNÉRABILITÉS ({len(vulnerabilities)})",
                sep,
            ]
            for v in vulnerabilities[:5]:
                severity = (v.get('severity') or '').upper()
                lines.append(f"[{severity}] {v.get('title', '')}")
                if v.get('recommendation'):
                    lines.append(f"  → {v['recommendation']}")

        if recommendations:
            lines += [
                f"",
                sep,
                f"RECOMMANDATIONS ({len(recommendations)})",
                sep,
            ]
            for rec in recommendations[:5]:
                lines += [
                    f"",
                    f"{rec.get('title', '')}",
                    f"  → {rec.get('description', '')}",
                    f"  → Gain estimé  : {rec.get('estimated_gain', 'N/A')}",
                    f"  → Effort       : {rec.get('estimated_effort', 'N/A')}",
                    f"  → Coût estimé  : {rec.get('estimated_cost_min', '?')}"
                    f"–{rec.get('estimated_cost_max', '?')} €",
                ]

        opp_score = site.get('opportunity_score', 'N/A')
        lines += [
            f"",
            sep,
            f"SCORE D'OPPORTUNITÉ : {opp_score}/100",
            sep,
            f"",
            f"Ce diagnostic est fourni à titre indicatif.",
            f"Pour aller plus loin, réservez un créneau de 30 minutes :",
            f"https://cal.com/pascal-cescato/30min",
            f"",
            f"Pascal Cescato",
            f"pascal.cescato@backstage.click",
            f"https://backstage.click",
        ]

        return "\n".join(lines)
