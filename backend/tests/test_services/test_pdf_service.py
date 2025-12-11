"""
Unit tests for the PDF report service.

Tests PDFReportService functionality including:
- Property report generation
- Deal report generation
- Portfolio reports
- Style and formatting
"""
import pytest
from io import BytesIO
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

# Test with or without reportlab
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


class TestPDFReportService:
    """Tests for the PDFReportService class."""

    @pytest.fixture
    def service(self):
        """Create PDFReportService instance."""
        from app.services.pdf_service import PDFReportService
        return PDFReportService()

    @pytest.fixture
    def sample_property(self):
        """Sample property data for testing."""
        return {
            "id": 1,
            "name": "Phoenix Garden Apartments",
            "property_type": "multifamily",
            "address": "123 Garden Lane",
            "city": "Phoenix",
            "state": "AZ",
            "market": "Phoenix Metro",
            "total_units": 150,
            "total_sf": 125000,
            "year_built": 2018,
            "occupancy_rate": 96.5,
            "cap_rate": 5.75,
            "noi": 1850000,
            "avg_rent_per_unit": 1650,
            "avg_rent_per_sf": None,
        }

    @pytest.fixture
    def sample_deal(self):
        """Sample deal data for testing."""
        return {
            "id": 1,
            "name": "Phoenix Garden Acquisition",
            "deal_type": "acquisition",
            "stage": "underwriting",
            "priority": "high",
            "source": "CBRE",
            "broker_name": "John Smith",
            "hold_period_years": 5,
            "asking_price": 28000000,
            "offer_price": 26500000,
            "projected_irr": 18.5,
            "projected_coc": 8.2,
            "projected_equity_multiple": 2.15,
        }

    @pytest.fixture
    def sample_dashboard_metrics(self):
        """Sample dashboard metrics."""
        return {
            "portfolio_summary": {
                "total_properties": 30,
                "total_units": 3500,
                "total_sf": 2800000,
                "total_value": 350000000,
                "avg_occupancy": 95.2,
                "avg_cap_rate": 5.8,
            },
            "kpis": {
                "ytd_noi_growth": 4.5,
                "ytd_rent_growth": 3.2,
                "deals_in_pipeline": 15,
                "deals_closed_ytd": 6,
                "capital_deployed_ytd": 65000000,
            },
        }

    @pytest.fixture
    def sample_portfolio_analytics(self):
        """Sample portfolio analytics."""
        return {
            "performance": {
                "total_return": 14.2,
                "income_return": 7.5,
                "appreciation_return": 6.7,
                "benchmark_return": 11.5,
                "alpha": 2.7,
            },
        }

    # ==================== Initialization Tests ====================

    def test_service_initialization(self, service):
        """Test PDFReportService initializes correctly."""
        if REPORTLAB_AVAILABLE:
            assert service._styles is not None
            assert service.COLORS  # Colors should be initialized
        else:
            assert service._styles is None

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_colors_initialized(self, service):
        """Test branding colors are properly initialized."""
        assert "primary" in service.COLORS
        assert "secondary" in service.COLORS
        assert "success" in service.COLORS
        assert "danger" in service.COLORS
        assert "white" in service.COLORS

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_stage_colors_initialized(self, service):
        """Test stage colors are properly initialized."""
        assert "lead" in service.STAGE_COLORS
        assert "underwriting" in service.STAGE_COLORS
        assert "closed" in service.STAGE_COLORS
        assert "dead" in service.STAGE_COLORS

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_custom_styles_created(self, service):
        """Test custom paragraph styles are created."""
        assert "ReportTitle" in service._styles
        assert "SectionHeader" in service._styles
        assert "SubSectionHeader" in service._styles
        assert "BodyText" in service._styles
        assert "MetricValue" in service._styles
        assert "Footer" in service._styles

    # ==================== Formatting Helper Tests ====================

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_format_currency_millions(self, service):
        """Test currency formatting for millions."""
        assert service._format_currency(5000000) == "$5.0M"
        assert service._format_currency(12500000) == "$12.5M"

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_format_currency_thousands(self, service):
        """Test currency formatting for thousands."""
        assert service._format_currency(500000) == "$500K"
        assert service._format_currency(1500) == "$2K"

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_format_currency_small(self, service):
        """Test currency formatting for small amounts."""
        assert service._format_currency(999) == "$999.00"
        assert service._format_currency(50.5) == "$50.50"

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_format_percent_whole(self, service):
        """Test percent formatting for whole numbers."""
        assert service._format_percent(15) == "15.0%"
        assert service._format_percent(100) == "100.0%"

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_format_percent_decimal(self, service):
        """Test percent formatting for decimals."""
        assert service._format_percent(0.15) == "15.0%"
        assert service._format_percent(0.055) == "5.5%"

    # ==================== Property Report Tests ====================

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_generate_property_report_returns_bytesio(self, service, sample_property):
        """Test property report returns BytesIO."""
        result = service.generate_property_report(sample_property)
        assert isinstance(result, BytesIO)
        assert result.getvalue()  # Should have content

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_generate_property_report_valid_pdf(self, service, sample_property):
        """Test property report generates valid PDF."""
        result = service.generate_property_report(sample_property)

        # PDF files start with %PDF
        content = result.getvalue()
        assert content[:4] == b'%PDF'

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_generate_property_report_with_analytics(self, service, sample_property):
        """Test property report with analytics data."""
        analytics = {
            "metrics": {
                "ytd_rent_growth": 3.5,
                "ytd_noi_growth": 4.2,
                "avg_occupancy_12m": 95.0,
                "rent_vs_market": 1.05,
            }
        }

        result = service.generate_property_report(sample_property, analytics=analytics)
        assert isinstance(result, BytesIO)
        assert result.getvalue()

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_property_report_handles_missing_fields(self, service):
        """Test property report handles missing optional fields."""
        minimal_property = {
            "name": "Minimal Property",
            "property_type": "land",
        }

        # Should not raise
        result = service.generate_property_report(minimal_property)
        assert result.getvalue()

    # ==================== Deal Report Tests ====================

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_generate_deal_report_returns_bytesio(self, service, sample_deal):
        """Test deal report returns BytesIO."""
        result = service.generate_deal_report(sample_deal)
        assert isinstance(result, BytesIO)
        assert result.getvalue()

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_generate_deal_report_valid_pdf(self, service, sample_deal):
        """Test deal report generates valid PDF."""
        result = service.generate_deal_report(sample_deal)

        content = result.getvalue()
        assert content[:4] == b'%PDF'

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_generate_deal_report_with_property(self, service, sample_deal, sample_property):
        """Test deal report with associated property."""
        result = service.generate_deal_report(sample_deal, property_data=sample_property)
        assert isinstance(result, BytesIO)
        assert result.getvalue()

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_deal_report_stage_colors(self, service, sample_deal):
        """Test deal report handles different stages."""
        stages = ["lead", "underwriting", "due_diligence", "closed", "dead", "unknown"]

        for stage in stages:
            deal = {**sample_deal, "stage": stage}
            result = service.generate_deal_report(deal)
            assert result.getvalue()

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_deal_report_handles_missing_financials(self, service):
        """Test deal report handles missing financial data."""
        minimal_deal = {
            "name": "Simple Deal",
            "deal_type": "acquisition",
            "stage": "lead",
            "asking_price": 1000000,
        }

        result = service.generate_deal_report(minimal_deal)
        assert result.getvalue()

    # ==================== Portfolio Report Tests ====================

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_generate_portfolio_report(
        self,
        service,
        sample_dashboard_metrics,
        sample_portfolio_analytics,
        sample_property,
        sample_deal,
    ):
        """Test portfolio report generation."""
        result = service.generate_portfolio_report(
            sample_dashboard_metrics,
            sample_portfolio_analytics,
            [sample_property],
            [sample_deal],
        )

        assert isinstance(result, BytesIO)
        assert result.getvalue()

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_portfolio_report_valid_pdf(
        self,
        service,
        sample_dashboard_metrics,
        sample_portfolio_analytics,
    ):
        """Test portfolio report generates valid PDF."""
        result = service.generate_portfolio_report(
            sample_dashboard_metrics,
            sample_portfolio_analytics,
            [],  # Empty properties
            [],  # Empty deals
        )

        content = result.getvalue()
        assert content[:4] == b'%PDF'

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_portfolio_report_limits_items(
        self,
        service,
        sample_dashboard_metrics,
        sample_portfolio_analytics,
        sample_property,
        sample_deal,
    ):
        """Test portfolio report limits properties/deals to 10."""
        # Create 15 properties and 15 deals
        properties = [
            {**sample_property, "id": i, "name": f"Property {i}"}
            for i in range(15)
        ]
        deals = [
            {**sample_deal, "id": i, "name": f"Deal {i}"}
            for i in range(15)
        ]

        # Should not error - will show first 10 with "and X more" message
        result = service.generate_portfolio_report(
            sample_dashboard_metrics,
            sample_portfolio_analytics,
            properties,
            deals,
        )
        assert result.getvalue()

    # ==================== Table Style Tests ====================

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_create_table_style_default_color(self, service):
        """Test table style creation with default color."""
        style = service._create_table_style()
        assert style is not None

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_create_table_style_custom_color(self, service):
        """Test table style creation with custom color."""
        custom_color = service.COLORS["success"]
        style = service._create_table_style(header_color=custom_color)
        assert style is not None

    # ==================== Error Handling Tests ====================

    def test_generate_report_without_reportlab_raises(self, service):
        """Test report generation raises ImportError when reportlab unavailable."""
        with patch('app.services.pdf_service.REPORTLAB_AVAILABLE', False):
            from app.services.pdf_service import PDFReportService
            svc = PDFReportService()

            with pytest.raises(ImportError, match="reportlab"):
                svc.generate_property_report({"name": "Test"})

    def test_deal_report_without_reportlab_raises(self, service):
        """Test deal report raises ImportError when reportlab unavailable."""
        with patch('app.services.pdf_service.REPORTLAB_AVAILABLE', False):
            from app.services.pdf_service import PDFReportService
            svc = PDFReportService()

            with pytest.raises(ImportError, match="reportlab"):
                svc.generate_deal_report({"name": "Test"})

    def test_portfolio_report_without_reportlab_raises(self, service):
        """Test portfolio report raises ImportError when reportlab unavailable."""
        with patch('app.services.pdf_service.REPORTLAB_AVAILABLE', False):
            from app.services.pdf_service import PDFReportService
            svc = PDFReportService()

            with pytest.raises(ImportError, match="reportlab"):
                svc.generate_portfolio_report({}, {}, [], [])

    # ==================== Edge Cases ====================

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_property_report_with_zero_values(self, service):
        """Test property report handles zero values."""
        property_data = {
            "name": "Empty Land",
            "property_type": "land",
            "occupancy_rate": 0,
            "cap_rate": 0,
            "noi": 0,
        }

        result = service.generate_property_report(property_data)
        assert result.getvalue()

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_deal_report_with_zero_values(self, service):
        """Test deal report handles zero values."""
        deal_data = {
            "name": "Early Stage Deal",
            "deal_type": "acquisition",
            "stage": "lead",
            "asking_price": 0,
            "offer_price": 0,
            "projected_irr": 0,
        }

        result = service.generate_deal_report(deal_data)
        assert result.getvalue()

    # ==================== Resource Cleanup Tests ====================

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_property_report_returns_seekable_buffer(self, service, sample_property):
        """Test property report returns buffer positioned at start."""
        result = service.generate_property_report(sample_property)

        # Buffer should be at start
        assert result.tell() == 0

        # Should be readable
        content = result.read()
        assert len(content) > 0

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_deal_report_returns_seekable_buffer(self, service, sample_deal):
        """Test deal report returns buffer positioned at start."""
        result = service.generate_deal_report(sample_deal)

        # Buffer should be at start
        assert result.tell() == 0

        # Should be readable and valid PDF
        content = result.read()
        assert content[:4] == b'%PDF'

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_portfolio_report_returns_seekable_buffer(
        self, service, sample_dashboard_metrics, sample_portfolio_analytics
    ):
        """Test portfolio report returns buffer positioned at start."""
        result = service.generate_portfolio_report(
            sample_dashboard_metrics,
            sample_portfolio_analytics,
            [],
            [],
        )

        # Buffer should be at start
        assert result.tell() == 0

        # Should be readable
        content = result.read()
        assert len(content) > 0

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_property_report_with_special_characters(self, service):
        """Test property report handles special characters."""
        property_data = {
            "name": "Test & Property <with> \"special\" chars",
            "property_type": "office",
            "address": "123 Main St, Suite #5",
            "city": "San José",
            "state": "CA",
            "market": "Bay Area / Silicon Valley",
        }

        result = service.generate_property_report(property_data)
        assert result.getvalue()

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_multiple_reports_same_service(self, service, sample_property, sample_deal):
        """Test generating multiple reports with same service instance."""
        # Generate several reports
        result1 = service.generate_property_report(sample_property)
        result2 = service.generate_deal_report(sample_deal)
        result3 = service.generate_property_report({
            "name": "Another Property",
            "property_type": "retail",
        })

        # All should be valid PDFs
        assert result1.getvalue()[:4] == b'%PDF'
        assert result2.getvalue()[:4] == b'%PDF'
        assert result3.getvalue()[:4] == b'%PDF'

    @pytest.mark.skipif(not REPORTLAB_AVAILABLE, reason="reportlab not installed")
    def test_report_with_unicode_content(self, service):
        """Test report handles unicode content properly."""
        property_data = {
            "name": "Ñoño Properties™ — 日本語テスト",
            "property_type": "multifamily",
            "address": "北京路 123号",
            "city": "São Paulo",
            "state": "BR",
            "market": "Latin America",
        }

        # Should not raise encoding errors
        result = service.generate_property_report(property_data)
        assert result.getvalue()


class TestPDFServiceSingleton:
    """Tests for the get_pdf_service singleton."""

    def test_get_pdf_service_returns_instance(self):
        """Test get_pdf_service returns PDFReportService instance."""
        from app.services.pdf_service import get_pdf_service, PDFReportService

        service = get_pdf_service()
        assert isinstance(service, PDFReportService)

    def test_get_pdf_service_returns_same_instance(self):
        """Test get_pdf_service returns singleton."""
        from app.services.pdf_service import get_pdf_service

        service1 = get_pdf_service()
        service2 = get_pdf_service()
        assert service1 is service2
