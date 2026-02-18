"""Email sending via Gmail SMTP."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.utils import formataddr
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass

from .config import GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_TO


@dataclass
class EmailAttachment:
    """An image attachment for the email."""
    path: Path
    content_id: str


def send_email(
    subject: str,
    html_content: str,
    attachments: List[EmailAttachment] = None,
    to_addresses: str = None,
    from_address: str = None,
    from_name: str = "BCRA Monitor",
) -> bool:
    """
    Send an HTML email via Gmail SMTP.

    Args:
        subject: Email subject line
        html_content: HTML body of the email
        attachments: List of image attachments with content IDs
        to_addresses: Comma-separated recipient addresses (defaults to EMAIL_TO env var)
        from_address: Sender address (defaults to GMAIL_USER env var)
        from_name: Display name for sender

    Returns:
        True if email was sent successfully, False otherwise
    """
    to_addresses = to_addresses or EMAIL_TO
    from_address = from_address or GMAIL_USER
    password = GMAIL_APP_PASSWORD

    if not all([to_addresses, from_address, password]):
        print("Error: Email credentials not configured.")
        print("Set GMAIL_USER, GMAIL_APP_PASSWORD, and EMAIL_TO environment variables.")
        return False

    try:
        # Create message
        msg = MIMEMultipart("related")
        msg["Subject"] = subject
        msg["From"] = formataddr((from_name, from_address))
        msg["To"] = to_addresses

        # Attach HTML content
        html_part = MIMEText(html_content, "html", "utf-8")
        msg.attach(html_part)

        # Attach images
        if attachments:
            for attachment in attachments:
                if attachment.path.exists():
                    with open(attachment.path, "rb") as f:
                        img_data = f.read()

                    img = MIMEImage(img_data)
                    img.add_header("Content-ID", f"<{attachment.content_id}>")
                    img.add_header(
                        "Content-Disposition",
                        "inline",
                        filename=attachment.path.name
                    )
                    msg.attach(img)

        # Send via Gmail SMTP
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_address, password)
            server.sendmail(
                from_address,
                to_addresses.split(","),
                msg.as_string()
            )

        print(f"Email sent successfully to: {to_addresses}")
        return True

    except smtplib.SMTPAuthenticationError:
        print("Error: Gmail authentication failed.")
        print("Make sure you're using an App Password, not your regular password.")
        print("Enable 2FA and create an App Password at: https://myaccount.google.com/apppasswords")
        return False

    except Exception as e:
        print(f"Error sending email: {e}")
        return False


def send_digest_email(
    html_content: str,
    charts: list,  # List of ChartInfo from digest.py
    date_range: str = "",
) -> bool:
    """
    Send the weekly digest email with embedded charts.

    Args:
        html_content: Rendered HTML digest
        charts: List of ChartInfo objects with chart paths and content IDs
        date_range: Date range string for subject line
    """
    subject = f"BCRA Monitor Semanal - {date_range}"

    # Convert charts to attachments
    attachments = [
        EmailAttachment(path=chart.path, content_id=chart.cid)
        for chart in charts
        if chart.path.exists()
    ]

    return send_email(
        subject=subject,
        html_content=html_content,
        attachments=attachments,
    )


def send_error_email(error_message: str) -> bool:
    """Send an error notification email."""
    subject = "BCRA Monitor - Error en la generación del digest"

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: sans-serif; padding: 20px;">
        <h1 style="color: #c53030;">Error en BCRA Monitor</h1>
        <p>Se produjo un error al generar el digest semanal:</p>
        <pre style="background: #f7fafc; padding: 15px; border-radius: 4px; overflow-x: auto;">
{error_message}
        </pre>
        <p>Por favor, revise los logs para más detalles.</p>
    </body>
    </html>
    """

    return send_email(
        subject=subject,
        html_content=html_content,
    )


def test_email_config() -> bool:
    """Test email configuration by sending a test message."""
    print("Testing email configuration...")
    print(f"  GMAIL_USER: {'[OK]' if GMAIL_USER else '[NOT SET]'}")
    print(f"  GMAIL_APP_PASSWORD: {'[OK]' if GMAIL_APP_PASSWORD else '[NOT SET]'}")
    print(f"  EMAIL_TO: {'[OK]' if EMAIL_TO else '[NOT SET]'}")

    if not all([GMAIL_USER, GMAIL_APP_PASSWORD, EMAIL_TO]):
        print("\nConfiguration incomplete. Set environment variables or .env file.")
        return False

    # Send test email
    html = """
    <html>
    <body style="font-family: sans-serif; padding: 20px;">
        <h1>BCRA Monitor - Test Email</h1>
        <p>If you received this email, your configuration is working correctly!</p>
    </body>
    </html>
    """

    return send_email(
        subject="BCRA Monitor - Test Email",
        html_content=html,
    )


if __name__ == "__main__":
    test_email_config()
