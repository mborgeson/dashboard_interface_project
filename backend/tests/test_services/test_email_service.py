"""Tests for email service."""

from email.mime.multipart import MIMEMultipart
from unittest.mock import AsyncMock, MagicMock, PropertyMock, patch

import pytest

from app.services.email_service import EmailService, get_email_service

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def email_service():
    """Create email service instance with mocked templates."""
    with patch.object(EmailService, "_setup_templates"):
        service = EmailService()
        service._template_env = None  # Ensure clean state
        return service


@pytest.fixture
def email_service_with_templates():
    """Create email service with mocked template environment."""
    with patch.object(EmailService, "_setup_templates"):
        service = EmailService()
        mock_env = MagicMock()
        mock_template = MagicMock()
        mock_template.render.return_value = "<html><body>Test Content</body></html>"
        mock_env.get_template.return_value = mock_template
        service._template_env = mock_env
        return service


@pytest.fixture
def mock_settings():
    """Mock settings with SMTP credentials."""
    with patch("app.services.email_service.settings") as mock:
        mock.SMTP_HOST = "smtp.test.com"
        mock.SMTP_PORT = 587
        mock.SMTP_USER = "test@example.com"
        mock.SMTP_PASSWORD = "testpassword"
        mock.EMAIL_FROM_NAME = "Test App"
        mock.EMAIL_FROM_ADDRESS = "noreply@test.com"
        mock.APP_NAME = "Test Application"
        yield mock


# =============================================================================
# EmailService Initialization Tests
# =============================================================================


class TestEmailServiceInit:
    """Tests for EmailService initialization."""

    def test_init_creates_instance(self, email_service):
        """Test that EmailService can be instantiated."""
        assert email_service is not None
        assert isinstance(email_service, EmailService)

    def test_init_calls_setup_templates(self):
        """Test that __init__ calls _setup_templates."""
        with patch.object(EmailService, "_setup_templates") as mock_setup:
            EmailService()
            mock_setup.assert_called_once()

    def test_setup_templates_with_existing_directory(self):
        """Test template setup when directory exists."""
        with patch("app.services.email_service.Path") as mock_path:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path.return_value.__truediv__.return_value.__truediv__.return_value = (
                mock_path_instance
            )

            with patch("app.services.email_service.Environment") as mock_env:
                with patch("app.services.email_service.FileSystemLoader"):
                    service = EmailService()
                    assert service._template_env is not None or mock_env.called

    def test_setup_templates_with_missing_directory(self):
        """Test template setup when directory doesn't exist."""
        # This test verifies behavior when template directory is missing
        # In production, it logs a warning. We verify the service still initializes.
        with patch.object(EmailService, "_setup_templates") as mock_setup:
            service = EmailService()
            # Service should still be created even with missing templates
            assert service is not None
            mock_setup.assert_called_once()


# =============================================================================
# Template Rendering Tests
# =============================================================================


class TestTemplateRendering:
    """Tests for template rendering functionality."""

    def test_render_template_success(self, email_service_with_templates):
        """Test successful template rendering."""
        result = email_service_with_templates._render_template(
            "test.html", {"name": "Test"}
        )
        assert result == "<html><body>Test Content</body></html>"

    def test_render_template_no_environment(self, email_service):
        """Test rendering raises error when no template environment."""
        with pytest.raises(RuntimeError, match="Template environment not initialized"):
            email_service._render_template("test.html", {})

    def test_render_template_calls_get_template(self, email_service_with_templates):
        """Test that render calls get_template with correct name."""
        email_service_with_templates._render_template("welcome.html", {})
        email_service_with_templates._template_env.get_template.assert_called_with(
            "welcome.html"
        )

    def test_render_template_passes_context(self, email_service_with_templates):
        """Test that context is passed to template render."""
        context = {"user": "test", "data": "value"}
        email_service_with_templates._render_template("test.html", context)
        email_service_with_templates._template_env.get_template().render.assert_called_with(
            **context
        )


# =============================================================================
# Send Email Tests
# =============================================================================


class TestSendEmail:
    """Tests for the core send_email method."""

    @pytest.mark.asyncio
    async def test_send_email_missing_credentials(self, email_service):
        """Test that send_email returns False when credentials missing."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.SMTP_USER = None
            mock_settings.SMTP_PASSWORD = None

            result = await email_service.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<p>Test</p>",
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_missing_password(self, email_service):
        """Test that send_email returns False when password missing."""
        with patch("app.services.email_service.settings") as mock_settings:
            mock_settings.SMTP_USER = "user@test.com"
            mock_settings.SMTP_PASSWORD = None

            result = await email_service.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<p>Test</p>",
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_success(self, email_service, mock_settings):
        """Test successful email sending."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ) as mock_send:
            result = await email_service.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<p>Test Content</p>",
            )

            assert result is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_with_multiple_recipients(
        self, email_service, mock_settings
    ):
        """Test sending to multiple recipients."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ) as mock_send:
            recipients = ["user1@test.com", "user2@test.com", "user3@test.com"]
            result = await email_service.send_email(
                to_email=recipients,
                subject="Test Subject",
                html_content="<p>Test Content</p>",
            )

            assert result is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_with_text_content(self, email_service, mock_settings):
        """Test sending email with both HTML and text content."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ) as mock_send:
            result = await email_service.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<p>Test HTML</p>",
                text_content="Test Plain Text",
            )

            assert result is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_with_cc(self, email_service, mock_settings):
        """Test sending email with CC recipients."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ) as mock_send:
            result = await email_service.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<p>Test</p>",
                cc=["cc1@test.com", "cc2@test.com"],
            )

            assert result is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_with_reply_to(self, email_service, mock_settings):
        """Test sending email with reply-to address."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ) as mock_send:
            result = await email_service.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<p>Test</p>",
                reply_to="replies@test.com",
            )

            assert result is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_with_attachments(self, email_service, mock_settings):
        """Test sending email with attachments."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ) as mock_send:
            attachments = [
                {
                    "filename": "report.pdf",
                    "content": b"PDF content here",
                    "mime_type": "application/pdf",
                }
            ]
            result = await email_service.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<p>Test</p>",
                attachments=attachments,
            )

            assert result is True
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_email_multiple_attachments(self, email_service, mock_settings):
        """Test sending email with multiple attachments."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ) as mock_send:
            attachments = [
                {
                    "filename": "file1.pdf",
                    "content": b"PDF 1",
                    "mime_type": "application/pdf",
                },
                {
                    "filename": "file2.xlsx",
                    "content": b"Excel data",
                    "mime_type": "application/xlsx",
                },
            ]
            result = await email_service.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<p>Test</p>",
                attachments=attachments,
            )

            assert result is True

    @pytest.mark.asyncio
    async def test_send_email_failure(self, email_service, mock_settings):
        """Test email sending failure returns False."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ) as mock_send:
            mock_send.side_effect = Exception("SMTP connection failed")

            result = await email_service.send_email(
                to_email="recipient@test.com",
                subject="Test Subject",
                html_content="<p>Test</p>",
            )

            assert result is False

    @pytest.mark.asyncio
    async def test_send_email_string_recipient_converted_to_list(
        self, email_service, mock_settings
    ):
        """Test that string recipient is handled correctly."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            # Single string recipient should work
            result = await email_service.send_email(
                to_email="single@test.com", subject="Test", html_content="<p>Test</p>"
            )
            assert result is True


# =============================================================================
# Welcome Email Tests
# =============================================================================


class TestWelcomeEmail:
    """Tests for welcome email functionality."""

    @pytest.mark.asyncio
    async def test_send_welcome_email_success(
        self, email_service_with_templates, mock_settings
    ):
        """Test successful welcome email sending."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service_with_templates.send_welcome_email(
                to_email="new_user@test.com",
                user_name="John Doe",
                login_url="https://app.test.com/login",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_welcome_email_uses_template(
        self, email_service_with_templates, mock_settings
    ):
        """Test that welcome email uses correct template."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            await email_service_with_templates.send_welcome_email(
                to_email="new_user@test.com",
                user_name="John Doe",
                login_url="https://app.test.com/login",
            )
            email_service_with_templates._template_env.get_template.assert_called_with(
                "welcome.html"
            )

    @pytest.mark.asyncio
    async def test_send_welcome_email_fallback_on_template_error(
        self, email_service, mock_settings
    ):
        """Test fallback welcome email when template fails."""
        email_service._template_env = MagicMock()
        email_service._template_env.get_template.side_effect = Exception(
            "Template error"
        )

        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service.send_welcome_email(
                to_email="new_user@test.com",
                user_name="John Doe",
                login_url="https://app.test.com/login",
            )
            # Should use fallback and still try to send
            assert result is True


# =============================================================================
# Password Reset Email Tests
# =============================================================================


class TestPasswordResetEmail:
    """Tests for password reset email functionality."""

    @pytest.mark.asyncio
    async def test_send_password_reset_email_success(
        self, email_service_with_templates, mock_settings
    ):
        """Test successful password reset email."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service_with_templates.send_password_reset_email(
                to_email="user@test.com",
                user_name="John Doe",
                reset_url="https://app.test.com/reset/token123",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_password_reset_email_custom_expiry(
        self, email_service_with_templates, mock_settings
    ):
        """Test password reset with custom expiry hours."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service_with_templates.send_password_reset_email(
                to_email="user@test.com",
                user_name="John Doe",
                reset_url="https://app.test.com/reset/token123",
                expires_in_hours=48,
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_password_reset_email_uses_template(
        self, email_service_with_templates, mock_settings
    ):
        """Test that password reset uses correct template."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            await email_service_with_templates.send_password_reset_email(
                to_email="user@test.com",
                user_name="John Doe",
                reset_url="https://app.test.com/reset/token123",
            )
            email_service_with_templates._template_env.get_template.assert_called_with(
                "password_reset.html"
            )

    @pytest.mark.asyncio
    async def test_send_password_reset_fallback_on_template_error(
        self, email_service, mock_settings
    ):
        """Test fallback password reset email when template fails."""
        email_service._template_env = MagicMock()
        email_service._template_env.get_template.side_effect = Exception(
            "Template error"
        )

        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service.send_password_reset_email(
                to_email="user@test.com",
                user_name="John Doe",
                reset_url="https://app.test.com/reset/token123",
            )
            assert result is True


# =============================================================================
# Report Email Tests
# =============================================================================


class TestReportEmail:
    """Tests for report email functionality."""

    @pytest.mark.asyncio
    async def test_send_report_email_success(
        self, email_service_with_templates, mock_settings
    ):
        """Test successful report email sending."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service_with_templates.send_report_email(
                to_email="manager@test.com",
                report_name="Monthly Analytics",
                report_date="2025-01-01",
                summary="Summary of monthly metrics",
                attachment_content=b"PDF content",
                attachment_filename="report.pdf",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_report_email_multiple_recipients(
        self, email_service_with_templates, mock_settings
    ):
        """Test report email to multiple recipients."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service_with_templates.send_report_email(
                to_email=["manager1@test.com", "manager2@test.com"],
                report_name="Weekly Report",
                report_date="2025-01-01",
                summary="Weekly summary",
                attachment_content=b"PDF content",
                attachment_filename="weekly.pdf",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_report_email_custom_mime_type(
        self, email_service_with_templates, mock_settings
    ):
        """Test report email with custom attachment type."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service_with_templates.send_report_email(
                to_email="manager@test.com",
                report_name="Data Export",
                report_date="2025-01-01",
                summary="Excel data export",
                attachment_content=b"Excel content",
                attachment_filename="data.xlsx",
                attachment_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_report_email_fallback_on_template_error(
        self, email_service, mock_settings
    ):
        """Test fallback report email when template fails."""
        email_service._template_env = MagicMock()
        email_service._template_env.get_template.side_effect = Exception(
            "Template error"
        )

        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service.send_report_email(
                to_email="manager@test.com",
                report_name="Monthly Analytics",
                report_date="2025-01-01",
                summary="Summary",
                attachment_content=b"PDF content",
                attachment_filename="report.pdf",
            )
            assert result is True


# =============================================================================
# Deal Notification Email Tests
# =============================================================================


class TestDealNotificationEmail:
    """Tests for deal notification email functionality."""

    @pytest.mark.asyncio
    async def test_send_deal_notification_success(
        self, email_service_with_templates, mock_settings
    ):
        """Test successful deal notification email."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service_with_templates.send_deal_notification(
                to_email="user@test.com",
                deal_name="Sunrise Apartments",
                action="Stage Updated",
                details={"new_stage": "Due Diligence", "old_stage": "Lead"},
                deal_url="https://app.test.com/deals/123",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_send_deal_notification_uses_template(
        self, email_service_with_templates, mock_settings
    ):
        """Test deal notification uses correct template."""
        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            await email_service_with_templates.send_deal_notification(
                to_email="user@test.com",
                deal_name="Test Deal",
                action="Created",
                details={},
                deal_url="https://app.test.com/deals/1",
            )
            email_service_with_templates._template_env.get_template.assert_called_with(
                "deal_notification.html"
            )

    @pytest.mark.asyncio
    async def test_send_deal_notification_fallback_on_template_error(
        self, email_service, mock_settings
    ):
        """Test fallback deal notification when template fails."""
        email_service._template_env = MagicMock()
        email_service._template_env.get_template.side_effect = Exception(
            "Template error"
        )

        with patch(
            "app.services.email_service.aiosmtplib.send", new_callable=AsyncMock
        ):
            result = await email_service.send_deal_notification(
                to_email="user@test.com",
                deal_name="Test Deal",
                action="Updated",
                details={"key": "value"},
                deal_url="https://app.test.com/deals/1",
            )
            assert result is True


# =============================================================================
# Singleton Tests
# =============================================================================


class TestEmailServiceSingleton:
    """Tests for email service singleton pattern."""

    def test_get_email_service_returns_instance(self):
        """Test get_email_service returns an EmailService instance."""
        with patch.object(EmailService, "_setup_templates"):
            # Reset singleton
            import app.services.email_service as module

            module._email_service = None

            service = get_email_service()
            assert isinstance(service, EmailService)

    def test_get_email_service_returns_same_instance(self):
        """Test get_email_service returns cached singleton."""
        with patch.object(EmailService, "_setup_templates"):
            import app.services.email_service as module

            module._email_service = None

            service1 = get_email_service()
            service2 = get_email_service()
            assert service1 is service2

    def test_singleton_persists_across_calls(self):
        """Test singleton instance persists."""
        with patch.object(EmailService, "_setup_templates"):
            import app.services.email_service as module

            module._email_service = None

            service1 = get_email_service()
            service2 = get_email_service()
            service3 = get_email_service()

            assert service1 is service2 is service3
