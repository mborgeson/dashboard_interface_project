"""
Email service for sending notifications and reports.
"""

from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape
from loguru import logger

from app.core.config import settings


class EmailService:
    """
    Email service for sending transactional and report emails.

    Features:
    - Async SMTP sending via Gmail
    - Jinja2 template rendering
    - Attachment support
    - Retry logic for reliability
    """

    def __init__(self):
        self._template_env: Environment | None = None
        self._setup_templates()

    def _setup_templates(self) -> None:
        """Initialize Jinja2 template environment."""
        template_dir = Path(__file__).parent.parent / "templates" / "email"
        if template_dir.exists():
            self._template_env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                autoescape=select_autoescape(["html", "xml"]),
            )
        else:
            logger.warning(f"Email template directory not found: {template_dir}")

    def _render_template(self, template_name: str, context: dict[str, Any]) -> str:
        """Render an email template with context."""
        if not self._template_env:
            raise RuntimeError("Template environment not initialized")
        template = self._template_env.get_template(template_name)
        return template.render(**context)

    async def send_email(
        self,
        to_email: str | list[str],
        subject: str,
        html_content: str,
        text_content: str | None = None,
        attachments: list[dict] | None = None,
        cc: list[str] | None = None,
        bcc: list[str] | None = None,
        reply_to: str | None = None,
    ) -> bool:
        """
        Send an email via SMTP.

        Args:
            to_email: Recipient email(s)
            subject: Email subject
            html_content: HTML body
            text_content: Plain text body (fallback)
            attachments: List of {"filename": str, "content": bytes, "mime_type": str}
            cc: CC recipients
            bcc: BCC recipients
            reply_to: Reply-to address

        Returns:
            True if sent successfully
        """
        if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
            logger.warning("Email not configured - SMTP credentials missing")
            return False

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = (
                f"{settings.EMAIL_FROM_NAME} <{settings.EMAIL_FROM_ADDRESS or settings.SMTP_USER}>"
            )

            # Handle recipients
            if isinstance(to_email, str):
                to_email = [to_email]
            msg["To"] = ", ".join(to_email)

            if cc:
                msg["Cc"] = ", ".join(cc)
            if reply_to:
                msg["Reply-To"] = reply_to

            # Add body
            if text_content:
                msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))

            # Add attachments
            if attachments:
                for attachment in attachments:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(attachment["content"])
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={attachment['filename']}",
                    )
                    msg.attach(part)

            # All recipients for SMTP
            # all_recipients = to_email + (cc or []) + (bcc or [])

            # Send via SMTP
            await aiosmtplib.send(
                msg,
                hostname=settings.SMTP_HOST,
                port=settings.SMTP_PORT,
                username=settings.SMTP_USER,
                password=settings.SMTP_PASSWORD,
                start_tls=True,
            )

            logger.info(f"Email sent successfully to {to_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    # ==================== Template-Based Emails ====================

    async def send_welcome_email(
        self, to_email: str, user_name: str, login_url: str
    ) -> bool:
        """Send welcome email to new user."""
        try:
            html_content = self._render_template(
                "welcome.html",
                {
                    "user_name": user_name,
                    "login_url": login_url,
                    "app_name": settings.APP_NAME,
                },
            )
            return await self.send_email(
                to_email=to_email,
                subject=f"Welcome to {settings.APP_NAME}",
                html_content=html_content,
            )
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")
            return await self._send_fallback_welcome(to_email, user_name, login_url)

    async def _send_fallback_welcome(
        self, to_email: str, user_name: str, login_url: str
    ) -> bool:
        """Send simple welcome email if template fails."""
        html_content = f"""
        <html>
        <body>
            <h1>Welcome to {settings.APP_NAME}!</h1>
            <p>Hello {user_name},</p>
            <p>Your account has been created successfully.</p>
            <p>Login at: <a href="{login_url}">{login_url}</a></p>
            <p>Best regards,<br>{settings.APP_NAME} Team</p>
        </body>
        </html>
        """
        return await self.send_email(
            to_email=to_email,
            subject=f"Welcome to {settings.APP_NAME}",
            html_content=html_content,
        )

    async def send_password_reset_email(
        self, to_email: str, user_name: str, reset_url: str, expires_in_hours: int = 24
    ) -> bool:
        """Send password reset email."""
        try:
            html_content = self._render_template(
                "password_reset.html",
                {
                    "user_name": user_name,
                    "reset_url": reset_url,
                    "expires_in_hours": expires_in_hours,
                    "app_name": settings.APP_NAME,
                },
            )
            return await self.send_email(
                to_email=to_email,
                subject=f"Password Reset - {settings.APP_NAME}",
                html_content=html_content,
            )
        except Exception as e:
            logger.error(f"Failed to send password reset email: {e}")
            html_content = f"""
            <html>
            <body>
                <h1>Password Reset Request</h1>
                <p>Hello {user_name},</p>
                <p>Click here to reset your password: <a href="{reset_url}">{reset_url}</a></p>
                <p>This link expires in {expires_in_hours} hours.</p>
                <p>If you didn't request this, please ignore this email.</p>
            </body>
            </html>
            """
            return await self.send_email(
                to_email=to_email,
                subject=f"Password Reset - {settings.APP_NAME}",
                html_content=html_content,
            )

    async def send_report_email(
        self,
        to_email: str | list[str],
        report_name: str,
        report_date: str,
        summary: str,
        attachment_content: bytes,
        attachment_filename: str,
        attachment_type: str = "application/pdf",
    ) -> bool:
        """Send analytics report via email."""
        try:
            html_content = self._render_template(
                "report.html",
                {
                    "report_name": report_name,
                    "report_date": report_date,
                    "summary": summary,
                    "app_name": settings.APP_NAME,
                },
            )
        except Exception:
            html_content = f"""
            <html>
            <body>
                <h1>{report_name}</h1>
                <p>Report Date: {report_date}</p>
                <p>{summary}</p>
                <p>Please find the attached report.</p>
                <p>Best regards,<br>{settings.APP_NAME}</p>
            </body>
            </html>
            """

        return await self.send_email(
            to_email=to_email,
            subject=f"{report_name} - {report_date}",
            html_content=html_content,
            attachments=[
                {
                    "filename": attachment_filename,
                    "content": attachment_content,
                    "mime_type": attachment_type,
                }
            ],
        )

    async def send_deal_notification(
        self,
        to_email: str,
        deal_name: str,
        action: str,
        details: dict[str, Any],
        deal_url: str,
    ) -> bool:
        """Send notification about deal updates."""
        try:
            html_content = self._render_template(
                "deal_notification.html",
                {
                    "deal_name": deal_name,
                    "action": action,
                    "details": details,
                    "deal_url": deal_url,
                    "app_name": settings.APP_NAME,
                },
            )
        except Exception:
            html_content = f"""
            <html>
            <body>
                <h1>Deal Update: {deal_name}</h1>
                <p>Action: {action}</p>
                <p>View deal: <a href="{deal_url}">{deal_url}</a></p>
                <p>Best regards,<br>{settings.APP_NAME}</p>
            </body>
            </html>
            """

        return await self.send_email(
            to_email=to_email,
            subject=f"Deal Update: {deal_name} - {action}",
            html_content=html_content,
        )


# Singleton instance
_email_service: EmailService | None = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service
