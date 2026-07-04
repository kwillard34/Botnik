"""
Sends alerts by email, and optionally by "text message" via your phone
carrier's free email-to-SMS gateway (e.g. 5551234567@vtext.com).

This is the lowest-effort option: no third-party service, no signup,
no cost. Downsides: carrier gateways are occasionally slow/unreliable
and some carriers have discontinued theirs — if that's an issue for you,
swap this module out for Twilio later without touching the rest of the code.
"""
import logging
import os
import smtplib
from email.mime.text import MIMEText

log = logging.getLogger(__name__)


def _send_email(subject: str, body: str, to_addr: str) -> None:
    host = os.environ["SMTP_HOST"]
    port = int(os.environ.get("SMTP_PORT", "587"))
    username = os.environ["SMTP_USERNAME"]
    password = os.environ["SMTP_PASSWORD"]

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = to_addr

    with smtplib.SMTP(host, port, timeout=20) as server:
        server.starttls()
        server.login(username, password)
        server.sendmail(username, [to_addr], msg.as_string())


def send_alert(subject: str, body: str) -> None:
    """Send the alert to email, and to SMS gateway if configured."""
    to_email = os.environ.get("ALERT_EMAIL_TO")
    if to_email:
        try:
            _send_email(subject, body, to_email)
            log.info("Alert email sent to %s", to_email)
        except Exception:
            log.exception("Failed to send alert email")
    else:
        log.warning("ALERT_EMAIL_TO not set — no email sent")

    sms_gateway = os.environ.get("ALERT_SMS_GATEWAY", "").strip()
    if sms_gateway:
        try:
            # Keep SMS body short — most gateways truncate around 160 chars.
            short_body = body if len(body) <= 150 else body[:147] + "..."
            _send_email(subject, short_body, sms_gateway)
            log.info("Alert text sent to %s", sms_gateway)
        except Exception:
            log.exception("Failed to send alert text via SMS gateway")
