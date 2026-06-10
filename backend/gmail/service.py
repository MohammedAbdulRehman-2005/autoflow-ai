import os
import smtplib

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_test_email(receiver_email: str):

    sender_email = os.getenv("EMAIL_ADDRESS")
    sender_password = os.getenv("EMAIL_PASSWORD")

    try:

        msg = MIMEMultipart()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = "AutoFlow AI Test Email"

        body = """
Hello,

This is a real email sent from AutoFlow AI.

Your Gmail integration is working successfully.

Regards,
AutoFlow AI Team
"""

        msg.attach(MIMEText(body, "plain"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()

        server.login(
            sender_email,
            sender_password
        )

        server.send_message(msg)
        server.quit()

        return {
            "status": "success",
            "message": f"Email sent to {receiver_email}"
        }

    except Exception as e:

        return {
            "status": "error",
            "message": str(e)
        }
