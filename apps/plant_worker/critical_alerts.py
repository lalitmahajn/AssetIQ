from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from common_core.config import settings

log = logging.getLogger("assetiq.alerts")

def send_critical_alert(subject: str, body: str) -> None:
    if not settings.smtp_host or not settings.email_it:
        log.error("critical_alert", extra={"subject": subject, "component": "plant_worker"})
        return

    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = settings.email_it
    msg["Subject"] = subject
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
            s.starttls()
            if settings.smtp_user:
                s.login(settings.smtp_user, settings.smtp_pass)
            s.send_message(msg)
    except Exception:
        log.exception("critical_alert_send_failed", extra={"component": "plant_worker"})
