"""
Scan Mailer – Backstage
=======================
Formate le rapport de scan et l'envoie par email (Multipart: Plain + HTML).
Intègre un bloc de conclusion commercial dynamique basé sur la sévérité des failles.
"""

import smtplib
import ssl
import re
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
        
        # Génération des deux versions
        body_plain = self._format_report_plain(domain, site, scan, recommendations, vulnerabilities)
        body_html  = self._format_report_html(domain, site, scan, recommendations, vulnerabilities)

        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From']    = f"{SMTP_CONFIG['from_name']} <{SMTP_CONFIG['from']}>"
        msg['To']      = to_email
        msg['Reply-To'] = SMTP_CONFIG['from']

        msg.attach(MIMEText(body_plain, 'plain', 'utf-8'))
        msg.attach(MIMEText(body_html, 'html', 'utf-8'))

        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(SMTP_CONFIG['host'], SMTP_CONFIG['port']) as server:
                server.starttls(context=context)
                server.login(SMTP_CONFIG['user'], SMTP_CONFIG['password'])
                server.sendmail(
                    SMTP_CONFIG['from'],
                    to_email,
                    msg.as_string()
                )
            print(f"      Rapport envoyé à {to_email}")
            return True
        except Exception as e:
            print(f"      Erreur envoi email : {e}")
            return False

    def _format_report_plain(
        self, domain: str, site: Dict, scan: Dict, recommendations: List[Dict], vulnerabilities: List[Dict]
    ) -> str:
        """Version texte brut (Fallback)"""
        scan_date = scan.get('scan_date', datetime.now())
        date_str = scan_date.strftime('%d/%m/%Y à %H:%M') if hasattr(scan_date, 'strftime') else str(scan_date)
        sep = '—' * 40

        lines = [
            f"Bonjour,", f"", f"Voici le résultat du diagnostic de {domain},", f"effectué le {date_str}.", f"",
            sep, "SCORES LIGHTHOUSE (mobile)", sep,
            f"Performance      : {scan.get('performance_score', 'N/A')}/100",
            f"Accessibilité    : {scan.get('accessibility_score', 'N/A')}/100",
            f"Bonnes pratiques : {scan.get('best_practices_score', 'N/A')}/100",
            f"SEO              : {scan.get('seo_score', 'N/A')}/100", f"",
            sep, "SÉCURITÉ", sep, f"Grade            : {scan.get('security_grade', 'N/A')}"
        ]

        for label, key in [('HSTS', 'has_hsts'), ('CSP', 'has_csp'), ('X-Frame-Options', 'has_x_frame_options'), 
                           ('X-Content-Type', 'has_x_content_type_options'), ('Referrer-Policy', 'has_referrer_policy'), 
                           ('Permissions-Policy', 'has_permissions_policy')]:
            lines.append(f"  {'✓' if scan.get(key) else '✗'} {label}")

        lines += [f"", sep, "STACK TECHNIQUE", sep]
        if scan.get('is_wordpress'):
            lines.append(f"WordPress        : {scan.get('wp_version', 'N/A')}{' (obsolète)' if scan.get('wp_version_outdated') else ''}")
        if scan.get('php_version'):
            lines.append(f"PHP              : {scan.get('php_version')}")
        lines.append(f"Serveur          : {scan.get('server_software', 'N/A')}")

        grade = scan.get('security_grade', 'A')
        is_critical = grade in ['F', 'E', 'D'] or scan.get('wp_version_outdated')

        lines += [f"", sep, "CONCLUSION", sep]
        if is_critical:
            lines += [
                "⚠️ ATTENTION : Votre site présente des failles de sécurité critiques.",
                "L'absence de protections standard ou un CMS obsolète vous expose à des risques immédiats.",
                "👉 Répondez à ce mail si vous souhaitez que je sécurise ces points pour vous."
            ]
        else:
            lines += ["🎉 FÉLICITATIONS : Votre site possède une configuration saine et sécurisée."]

        lines += [f"", f"Réserver un créneau de 30 min : https://cal.com/pascal-cescato/30min", f"", f"Pascal Cescato"]
        return "\n".join(lines)

    def _format_report_html(
        self, domain: str, site: Dict, scan: Dict, recommendations: List[Dict], vulnerabilities: List[Dict]
    ) -> str:
        """Version HTML propre avec conclusion dynamique"""
        scan_date = scan.get('scan_date', datetime.now())
        date_str = scan_date.strftime('%d/%m/%Y à %H:%M') if hasattr(scan_date, 'strftime') else str(scan_date)
        
        # Logique de couleur pour le score Lighthouse
        def get_score_colors(score):
            if score is None: return '#F3F4F6', '#111827', '#5F5E5A'
            if score >= 90:   return '#E1F5EE', '#0F6E56', '#1D9E75'
            if score >= 50:   return '#FAEEDA', '#854F0B', '#BA7517'
            return '#FCEBEB', '#A32D2D', '#E24B4A'

        perf_bg, perf_fg, perf_lbl = get_score_colors(scan.get('performance_score'))
        acc_bg, acc_fg, acc_lbl = get_score_colors(scan.get('accessibility_score'))
        bp_bg, bp_fg, bp_lbl = get_score_colors(scan.get('best_practices_score'))
        seo_bg, seo_fg, seo_lbl = get_score_colors(scan.get('seo_score'))

        # Sécurité Grade couleur
        grade = scan.get('security_grade', 'N/A')
        is_critical = grade in ['F', 'E', 'D'] or scan.get('wp_version_outdated')
        grade_bg, grade_fg = ('#FCEBEB', '#A32D2D') if is_critical else ('#E1F5EE', '#0F6E56')

        # Construction des lignes de vulnérabilités
        vuln_html = ""
        if vulnerabilities:
            vuln_html = '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:#888780;border-bottom:0.5px solid #e5e7eb;padding-bottom:8px;margin-bottom:12px;">Vulnérabilités (' + str(len(vulnerabilities)) + ')</div>'
            for v in vulnerabilities[:5]:
                vuln_html += f'<div style="background:#FCEBEB;border-left:3px solid #E24B4A;border-radius:0 8px 8px 0;padding:10px 14px;margin-bottom:8px;"><div style="font-weight:500;font-size:13px;color:#A32D2D">[{v.get("severity", "").upper()}] {v.get("title", "")}</div></div>'
            vuln_html += '</div>'

        # Construction des recommandations
        rec_html = ""
        if recommendations:
            rec_html = '<div style="margin-bottom:24px;"><div style="font-size:11px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:#888780;border-bottom:0.5px solid #e5e7eb;padding-bottom:8px;margin-bottom:12px;">Recommandations (' + str(len(recommendations)) + ')</div>'
            for rec in recommendations[:5]:
                rec_html += f'<div style="border-bottom:0.5px solid #e5e7eb;padding:10px 0;"><div style="font-weight:500;font-size:13px">{rec.get("title", "")}</div><div style="font-size:12px;color:#5F5E5A;margin-top:2px">{rec.get("description", "")}</div><div style="font-size:12px;color:#1D9E75;margin-top:2px">Gain : {rec.get("estimated_gain", "N/A")}</div></div>'
            rec_html += '</div>'

        # INTEGRATION DU BLOC DE CONCLUSION COMMERCIALE DYNAMIQUE
        if is_critical:
            conclusion_table = f"""
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0">
              <tr>
                <td style="background:#A32D2D;border-radius:12px;padding:24px 28px;text-align:center">
                  <p style="color:#FCEBEB;margin:0 0 12px;font-size:14px;font-weight:600;">
                    ⚠️ Attention : Les failles détectées (notamment le retard de version) représentent un risque immédiat d'anomalie ou de piratage pour votre activité.
                  </p>
                  <p style="color:#FCEBEB;margin:0 0 20px;font-size:13px;line-height:1.4;">
                    Ces points critiques doivent être corrigés rapidement. Si vous n'avez pas de support technique actif sous la main, je peux sécuriser votre plateforme et planifier sa mise à niveau.
                  </p>
                  <a href="https://cal.com/pascal-cescato/30min" style="display:inline-block;background:#fff;color:#A32D2D;font-weight:600;font-size:14px;padding:12px 28px;border-radius:99px;text-decoration:none;white-space:nowrap">
                    Planifier une intervention rapide →
                  </a>
                </td>
              </tr>
            </table>
            """
        else:
            conclusion_table = f"""
            <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:24px 0">
              <tr>
                <td style="background:#1a3a4a;border-radius:12px;padding:24px 28px;text-align:center">
                  <p style="color:#e0f0f8;margin:0 0 12px;font-size:14px;font-weight:600;">
                    🎉 Félicitations ! Votre site présente une configuration solide et sécurisée.
                  </p>
                  <p style="color:#e0f0f8;margin:0 0 20px;font-size:13px;line-height:1.4;">
                    C'est excellent pour la pérennité de votre vitrine. Gardez ce diagnostic de côté si vous prévoyez de futures optimisations de performances.
                  </p>
                  <a href="https://cal.com/pascal-cescato/30min" style="display:inline-block;background:#fff;color:#1a3a4a;font-weight:500;font-size:14px;padding:12px 28px;border-radius:99px;text-decoration:none;white-space:nowrap">
                    Échanger 15 minutes →
                  </a>
                </td>
              </tr>
            </table>
            """

        html = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:16px;background:#f3f4f6;font-family:Verdana,Arial,sans-serif;color:#111827">
<table width="100%" cellpadding="0" cellspacing="0" border="0"><tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px">
  <tr><td style="background:#1a3a4a;padding:20px 24px;border-radius:12px 12px 0 0">
    <h1 style="margin:0;color:#fff;font-size:17px;font-weight:500;word-break:break-all">Diagnostic — {domain}</h1>
    <p style="margin:4px 0 0;color:#a0c4d8;font-size:12px">Effectué le {date_str}</p>
  </td></tr>
  <tr><td style="background:#fff;border:0.5px solid #e5e7eb;padding:20px 24px">
    <p style="margin:0 0 20px;color:#5F5E5A;font-size:14px">Bonjour,<br><br>Voici le résultat du diagnostic de <strong>{domain}</strong>.</p>
    
    <!-- LIGHTHOUSE SCORES -->
    <div style="margin-bottom:24px">
      <div style="font-size:11px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:#888780;border-bottom:0.5px solid #e5e7eb;padding-bottom:8px;margin-bottom:12px">Scores Lighthouse (mobile)</div>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="50%" style="padding:4px"><div style="background:{perf_bg};border-radius:8px;padding:12px 6px;text-align:center"><div style="font-size:20px;font-weight:500;color:{perf_fg};line-height:1">{scan.get('performance_score', 'N/A')}</div><div style="font-size:10px;color:{perf_lbl};margin-top:4px;line-height:1.2">Performance</div></div></td>
          <td width="50%" style="padding:4px"><div style="background:{acc_bg};border-radius:8px;padding:12px 6px;text-align:center"><div style="font-size:20px;font-weight:500;color:{acc_fg};line-height:1">{scan.get('accessibility_score', 'N/A')}</div><div style="font-size:10px;color:{acc_lbl};margin-top:4px;line-height:1.2">Accessibilité</div></div></td>
        </tr>
        <tr>
          <td width="50%" style="padding:4px"><div style="background:{bp_bg};border-radius:8px;padding:12px 6px;text-align:center"><div style="font-size:20px;font-weight:500;color:{bp_fg};line-height:1">{scan.get('best_practices_score', 'N/A')}</div><div style="font-size:10px;color:{bp_lbl};margin-top:4px;line-height:1.2">Bonnes pratiques</div></div></td>
          <td width="50%" style="padding:4px"><div style="background:{seo_bg};border-radius:8px;padding:12px 6px;text-align:center"><div style="font-size:20px;font-weight:500;color:{seo_fg};line-height:1">{scan.get('seo_score', 'N/A')}</div><div style="font-size:10px;color:{seo_lbl};margin-top:4px;line-height:1.2">SEO</div></div></td>
        </tr>
      </table>
    </div>

    <!-- SÉCURITÉ GRADES -->
    <div style="margin-bottom:24px">
      <div style="font-size:11px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:#888780;border-bottom:0.5px solid #e5e7eb;padding-bottom:8px;margin-bottom:12px">Sécurité</div>
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:0.5px solid #e5e7eb;margin-bottom:8px">
        <tr>
          <td style="color:#5F5E5A;font-size:13px;padding:6px 0">Grade global</td>
          <td align="right" style="padding:6px 0"><span style="background:{grade_bg};color:{grade_fg};padding:3px 14px;border-radius:99px;font-size:15px;font-weight:500">{grade}</span></td>
        </tr>
      </table>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td width="50%" style="padding:4px 0;font-size:13px;vertical-align:top"><span style="color:{'#1D9E75' if scan.get('has_hsts') else '#E24B4A'};font-weight:500">{'✓' if scan.get('has_hsts') else '✗'}</span> HSTS</td>
          <td width="50%" style="padding:4px 0;font-size:13px;vertical-align:top"><span style="color:{'#1D9E75' if scan.get('has_csp') else '#E24B4A'};font-weight:500">{'✓' if scan.get('has_csp') else '✗'}</span> CSP</td>
        </tr>
        <tr>
          <td width="50%" style="padding:4px 0;font-size:13px;vertical-align:top"><span style="color:{'#1D9E75' if scan.get('has_x_frame_options') else '#E24B4A'};font-weight:500">{'✓' if scan.get('has_x_frame_options') else '✗'}</span> X-Frame-Options</td>
          <td width="50%" style="padding:4px 0;font-size:13px;vertical-align:top"><span style="color:{'#1D9E75' if scan.get('has_x_content_type_options') else '#E24B4A'};font-weight:500">{'✓' if scan.get('has_x_content_type_options') else '✗'}</span> X-Content-Type</td>
        </tr>
      </table>
    </div>

    <!-- STACK TECHNIQUE -->
    <div style="margin-bottom:24px">
      <div style="font-size:11px;font-weight:500;letter-spacing:.08em;text-transform:uppercase;color:#888780;border-bottom:0.5px solid #e5e7eb;padding-bottom:8px;margin-bottom:12px">Stack technique</div>
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:0.5px solid #e5e7eb">
        <tr>
          <td style="color:#5F5E5A;font-size:13px;padding:6px 0">WordPress</td>
          <td align="right" style="font-weight:500;font-size:13px;padding:6px 0">{scan.get('wp_version', 'None')}{' ⚠️ (obsolète)' if scan.get('wp_version_outdated') else ''}</td>
        </tr>
      </table>
      <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-bottom:0.5px solid #e5e7eb">
        <tr>
          <td style="color:#5F5E5A;font-size:13px;padding:6px 0">PHP</td>
          <td align="right" style="font-weight:500;font-size:13px;padding:6px 0">{scan.get('php_version', 'Non détecté')}{' ⚠️ (obsolète)' if scan.get('php_version_outdated') else ''}</td>
        </tr>
      </table>
      <table width="100%" cellpadding="0" cellspacing="0" border="0">
        <tr>
          <td style="color:#5F5E5A;font-size:13px;padding:6px 0">Serveur</td>
          <td align="right" style="font-weight:500;font-size:13px;padding:6px 0">{scan.get('server_software', 'Inconnu')}</td>
        </tr>
      </table>
    </div>

    {vuln_html}
    {rec_html}
    {conclusion_table}

    <!-- SIGNATURE -->
    <table width="100%" cellpadding="0" cellspacing="0" border="0" style="border-top:0.5px solid #e5e7eb;margin-top:8px">
      <tr>
        <td width="54" valign="top" style="padding-top:16px;padding-right:14px">
          <div style="width:40px;height:40px;border-radius:50%;background:#1a3a4a;text-align:center;line-height:40px;font-weight:500;font-size:13px;color:#fff">PC</div>
        </td>
        <td valign="top" style="padding-top:16px">
          <div style="font-weight:500;font-size:13px">Pascal Cescato</div>
          <div style="font-size:11px;color:#5F5E5A">Consultant web indépendant</div>
          <div style="font-size:11px;color:#5F5E5A;margin-top:2px">
            <a href="mailto:pascal.cescato@backstage.click" style="color:#185FA5;text-decoration:none">pascal.cescato@backstage.click</a>
            · <a href="https://backstage.click" style="color:#185FA5;text-decoration:none">backstage.click</a>
          </div>
        </td>
      </tr>
    </table>

  </td></tr>
</table>
</td></tr></table>
</body></html>"""
        return html