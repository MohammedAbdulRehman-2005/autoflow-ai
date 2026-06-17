import os
import httpx

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")

# Default sender — uses Resend's shared domain (works without domain verification).
# Once you add your own domain in Resend, change this to e.g. "AutoFlow AI <no-reply@yourdomain.com>"
DEFAULT_SENDER = os.getenv("EMAIL_FROM", "AutoFlow AI <onboarding@resend.dev>")


def send_test_email(receiver_email: str):
    """
    Send a test email using the Resend HTTP API.
    Works on Railway (no outbound SMTP port restrictions).
    Requires RESEND_API_KEY env var.
    """
    if not RESEND_API_KEY:
        return {
            "status": "error",
            "message": "RESEND_API_KEY environment variable is not set.",
        }

    payload = {
        "from": DEFAULT_SENDER,
        "to": [receiver_email],
        "subject": "AutoFlow AI — Email Integration Test",
        "html": """
            <div style="font-family:Inter,sans-serif;max-width:480px;margin:0 auto;padding:32px;background:#0f172a;color:#e2e8f0;border-radius:12px">
                <h2 style="color:#22d3ee;margin-top:0">&#9889; AutoFlow AI</h2>
                <p>Hi there,</p>
                <p>This is a test email to confirm your <strong>email integration is working correctly</strong>.</p>
                <div style="background:#1e293b;border-radius:8px;padding:16px;margin:20px 0;border-left:4px solid #22d3ee">
                    <p style="margin:0;font-size:14px">&#x2705; SMTP-less delivery via Resend API<br>
                    &#x2705; Railway-compatible (HTTPS only)<br>
                    &#x2705; Ready for workflow automation</p>
                </div>
                <p style="color:#94a3b8;font-size:12px">Sent by AutoFlow AI &mdash; Your AI Automation Platform</p>
            </div>
        """,
    }

    try:
        response = httpx.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json=payload,
            timeout=15.0,
        )
        data = response.json()

        if response.status_code in (200, 201):
            return {
                "status": "success",
                "message": f"Email sent to {receiver_email}",
                "resend_id": data.get("id"),
            }
        else:
            return {
                "status": "error",
                "message": data.get("message", "Unknown Resend API error"),
                "code": response.status_code,
            }

    except httpx.RequestError as e:
        return {
            "status": "error",
            "message": f"Network error: {str(e)}",
        }
