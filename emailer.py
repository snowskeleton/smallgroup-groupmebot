import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List

from bot_secrets import SMTP_SERVER, SMTP_PORT, SMTP_USERNAME, SMTP_PASSWORD, FROM_ADDRESS, DASHBOARD_URL
from exceptions import MailError


def send_email(address_list: List[str], subject: str, body: str):
    try:
        # address_list = ["test1@snowskeleton.net", "test2@snowskeleton.net"]
        msg = MIMEMultipart()
        msg["From"] = FROM_ADDRESS
        msg["To"] = ", ".join(address_list)
        msg["Subject"] = subject

        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.sendmail(FROM_ADDRESS, address_list, msg.as_string())
    except Exception as e:
        raise MailError(f"Failed to send email: {e}") from e


def send_magic_link(email: str, token: str):
    link = f"{DASHBOARD_URL}/dashboard/auth/{token}"
    body = f"""
    <h2>Your login link</h2>
    <p>Click the link below to log in to the GroupMe Bot Dashboard:</p>
    <p><a href="{link}">{link}</a></p>
    <p>If you didn't request this, you can ignore this email.</p>
    """
    send_email([email], "Dashboard Login Link", body)
