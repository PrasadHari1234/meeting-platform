"""
Notification Agent
──────────────────
Sends a clean email summary to meeting participants after processing.
Uses Supabase's built-in email OR a simple SMTP setup.
Phase 1: logs to console. Hook up SMTP/Resend in production.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os


class NotificationAgent:

    async def process(self, meeting: dict, recipient_email: str, app_url: str) -> bool:
        """
        Send meeting notes summary email.
        Returns True if sent, False if skipped/failed.
        """
        smtp_host = os.getenv("SMTP_HOST", "")
        if not smtp_host:
            # No SMTP configured — skip silently
            print(f"[NotificationAgent] SMTP not configured, skipping email to {recipient_email}")
            return False

        subject = f"Meeting Notes: {meeting.get('title', 'Your Meeting')}"
        body    = self._build_email(meeting, app_url)

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"]    = os.getenv("SMTP_FROM", "noreply@meetingagent.app")
            msg["To"]      = recipient_email
            msg.attach(MIMEText(body, "html"))

            with smtplib.SMTP_SSL(smtp_host, int(os.getenv("SMTP_PORT", "465"))) as server:
                server.login(os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASSWORD", ""))
                server.sendmail(msg["From"], recipient_email, msg.as_string())

            print(f"[NotificationAgent] Email sent to {recipient_email}")
            return True
        except Exception as e:
            print(f"[NotificationAgent] Email failed: {e}")
            return False

    def _build_email(self, meeting: dict, app_url: str) -> str:
        actions = meeting.get("action_items", [])
        action_rows = "".join(
            f"<tr><td style='padding:8px;border-bottom:1px solid #eee'>{a['item']}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #eee'>{a['owner']}</td>"
            f"<td style='padding:8px;border-bottom:1px solid #eee'>{a['priority']}</td></tr>"
            for a in actions
        )

        return f"""
        <div style="font-family:sans-serif;max-width:600px;margin:0 auto;color:#1f2937">
          <div style="background:#1e3a8a;padding:24px;border-radius:12px 12px 0 0">
            <h1 style="color:white;margin:0;font-size:22px">🎙️ Meeting Notes</h1>
            <p style="color:#93c5fd;margin:4px 0 0">{meeting.get('title','')}</p>
          </div>
          <div style="background:#f8fafc;padding:24px;border-radius:0 0 12px 12px;border:1px solid #e2e8f0">
            <h2 style="color:#1e3a8a;font-size:14px;text-transform:uppercase;letter-spacing:2px">Summary</h2>
            <p style="color:#374151">{meeting.get('summary','')}</p>

            {'<h2 style="color:#1e3a8a;font-size:14px;text-transform:uppercase;letter-spacing:2px">Action Items</h2><table style="width:100%;border-collapse:collapse"><tr style="background:#dbeafe"><th style="padding:8px;text-align:left">Task</th><th style="padding:8px;text-align:left">Owner</th><th style="padding:8px;text-align:left">Priority</th></tr>' + action_rows + '</table>' if actions else ''}

            <div style="margin-top:24px;text-align:center">
              <a href="{app_url}/meetings/{meeting.get('id','')}"
                 style="background:#1d4ed8;color:white;padding:12px 24px;border-radius:8px;text-decoration:none;font-weight:bold">
                View Full Notes →
              </a>
            </div>
          </div>
        </div>
        """
