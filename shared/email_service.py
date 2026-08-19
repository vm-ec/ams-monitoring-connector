"""
shared/email_service.py

Generic email notification service using SendGrid.
Decoupled from any specific domain — can be reused across the application.

Usage:
    from shared.email_service import send_email
    send_email(
        subject="Your Subject",
        body="Your message body",
        to_emails="team@example.com"
    )
"""
import sendgrid
from sendgrid.helpers.mail import Mail
from config import Config
from shared.logger import get_logger

logger = get_logger("shared.email_service")


def send_email(
    subject: str,
    body: str,
    to_emails: str = None
):
    """
    Sends a plain text email via SendGrid.

    Args:
        subject     - Email subject line
        body        - Plain text email body
        to_emails   - Recipient email(s), defaults to Config.EMAIL_TO
    """
    api_key = Config.SENDGRID_API_KEY
    from_email = Config.EMAIL_FROM
    recipient = to_emails or Config.EMAIL_TO

    if not api_key or not from_email or not recipient:
        logger.warning("[EMAIL] Missing config (SENDGRID_API_KEY / EMAIL_FROM / EMAIL_TO), skipping")
        return

    message = Mail(
        from_email=from_email,
        to_emails=recipient,
        subject=subject,
        plain_text_content=body
    )

    try:
        sg = sendgrid.SendGridAPIClient(api_key=api_key)
        response = sg.send(message)
        logger.info(f"[EMAIL] Sent successfully | To: {recipient} | Subject: {subject} | Status: {response.status_code}")
    except Exception as e:
        logger.error(f"[EMAIL] Failed to send email | To: {recipient} | Subject: {subject} | Reason: {e}")
