import sys
sys.path.insert(0, r"C:\Sai\git\ams-monitoring-connector")

from shared.email_service import send_email

send_email(
    subject="AMS Test Email",
    body="This is a test email from AMS Monitoring Connector to verify SendGrid is working.",
    to_emails="saikreddy2003@gmail.com"
)
