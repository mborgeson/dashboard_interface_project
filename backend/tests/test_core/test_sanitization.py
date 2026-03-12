"""
Tests for HTML/XSS input sanitization utilities.
"""

import pytest

from app.core.sanitization import (
    sanitize_string,
    sanitize_string_list,
    strip_html_tags,
)
from app.schemas.deal import DealCreate, DealUpdate
from app.schemas.document import DocumentCreate, DocumentUpdate
from app.schemas.property import PropertyCreate, PropertyUpdate
from app.schemas.user import UserCreate, UserUpdate


class TestStripHtmlTags:
    """Tests for the strip_html_tags function."""

    def test_plain_text_unchanged(self) -> None:
        assert strip_html_tags("Hello World") == "Hello World"

    def test_text_with_numbers_and_punctuation(self) -> None:
        assert strip_html_tags("Deal #123 - $5,000,000") == "Deal #123 - $5,000,000"

    def test_text_with_ampersand(self) -> None:
        assert strip_html_tags("B&R Capital") == "B&R Capital"

    def test_strips_simple_tags(self) -> None:
        assert strip_html_tags("<b>bold</b>") == "bold"

    def test_strips_paragraph_tags(self) -> None:
        assert strip_html_tags("<p>paragraph</p>") == "paragraph"

    def test_strips_div_tags(self) -> None:
        assert strip_html_tags("<div class='foo'>content</div>") == "content"

    def test_strips_nested_tags(self) -> None:
        result = strip_html_tags("<div><p><b>nested</b></p></div>")
        assert result == "nested"

    def test_strips_self_closing_tags(self) -> None:
        assert strip_html_tags("before<br/>after") == "beforeafter"

    def test_strips_tags_with_attributes(self) -> None:
        result = strip_html_tags('<a href="http://evil.com">click</a>')
        assert result == "click"
        assert "href" not in result

    def test_strips_img_tag(self) -> None:
        result = strip_html_tags('<img src="x" onerror="alert(1)">')
        assert "img" not in result
        assert "onerror" not in result

    def test_multiline_html(self) -> None:
        html_input = """<div>
            <p>Line 1</p>
            <p>Line 2</p>
        </div>"""
        result = strip_html_tags(html_input)
        assert "<div>" not in result
        assert "<p>" not in result
        assert "Line 1" in result
        assert "Line 2" in result


class TestScriptTagRemoval:
    """Tests specifically for script tag and XSS payload removal."""

    def test_strips_script_tags(self) -> None:
        result = strip_html_tags("<script>alert('xss')</script>")
        assert "<script>" not in result
        assert "</script>" not in result

    def test_strips_script_with_src(self) -> None:
        result = strip_html_tags('<script src="http://evil.com/xss.js"></script>')
        assert "script" not in result
        assert "evil.com" not in result

    def test_strips_event_handlers(self) -> None:
        result = strip_html_tags("<img src=x onerror=alert(1)>")
        assert "onerror" not in result

    def test_strips_onclick(self) -> None:
        result = strip_html_tags('<div onclick="alert(1)">click me</div>')
        assert "onclick" not in result
        assert "click me" in result

    def test_strips_javascript_uri(self) -> None:
        result = strip_html_tags('<a href="javascript:alert(1)">link</a>')
        assert "javascript" not in result.lower()

    def test_strips_encoded_script(self) -> None:
        # HTML-encoded script tag — after unescaping, tags should be stripped.
        # The text content "alert(1)" is harmless as plain text.
        result = strip_html_tags("&lt;script&gt;alert(1)&lt;/script&gt;")
        assert "<script>" not in result
        assert "</script>" not in result

    def test_strips_mixed_case_script(self) -> None:
        result = strip_html_tags("<ScRiPt>alert('xss')</ScRiPt>")
        assert "<ScRiPt>" not in result.lower()

    def test_strips_vbscript_uri(self) -> None:
        result = strip_html_tags('<a href="vbscript:MsgBox(1)">link</a>')
        assert "vbscript" not in result.lower()

    def test_strips_data_uri(self) -> None:
        result = strip_html_tags(
            '<a href="data:text/html,<script>alert(1)</script>">link</a>'
        )
        assert "data:" not in result.lower()

    def test_svg_onload(self) -> None:
        result = strip_html_tags('<svg onload="alert(1)">')
        assert "onload" not in result
        assert "svg" not in result

    def test_iframe_injection(self) -> None:
        result = strip_html_tags('<iframe src="http://evil.com"></iframe>')
        assert "iframe" not in result
        assert "evil.com" not in result

    def test_style_expression(self) -> None:
        result = strip_html_tags(
            '<div style="background:url(javascript:alert(1))">test</div>'
        )
        assert "javascript" not in result.lower()


class TestSanitizeString:
    """Tests for the sanitize_string function."""

    def test_none_returns_none(self) -> None:
        assert sanitize_string(None) is None

    def test_empty_string_returns_empty(self) -> None:
        assert sanitize_string("") == ""

    def test_whitespace_only_returns_whitespace(self) -> None:
        assert sanitize_string("   ") == "   "

    def test_normal_string_passes_through(self) -> None:
        assert sanitize_string("Normal text") == "Normal text"

    def test_html_is_stripped(self) -> None:
        assert sanitize_string("<b>bold</b>") == "bold"

    def test_script_is_stripped(self) -> None:
        result = sanitize_string("<script>alert('xss')</script>")
        assert "<script>" not in result


class TestSanitizeStringList:
    """Tests for the sanitize_string_list function."""

    def test_none_returns_none(self) -> None:
        assert sanitize_string_list(None) is None

    def test_empty_list_returns_empty(self) -> None:
        assert sanitize_string_list([]) == []

    def test_normal_strings_pass_through(self) -> None:
        result = sanitize_string_list(["tag1", "tag2", "tag3"])
        assert result == ["tag1", "tag2", "tag3"]

    def test_html_stripped_from_list_items(self) -> None:
        result = sanitize_string_list(["<b>bold</b>", "normal", "<script>x</script>"])
        assert result is not None
        assert result[0] == "bold"
        assert result[1] == "normal"
        assert "<script>" not in result[2]


class TestDealSchemaSanitization:
    """Tests that sanitization is applied via Pydantic schema validation."""

    def test_deal_create_sanitizes_name(self) -> None:
        deal = DealCreate(
            name="<script>alert('xss')</script>Test Deal",
            deal_type="acquisition",
        )
        assert "<script>" not in deal.name
        assert "Test Deal" in deal.name

    def test_deal_create_sanitizes_notes(self) -> None:
        deal = DealCreate(
            name="Test Deal",
            deal_type="acquisition",
            notes="<b>Bold notes</b> with <script>evil</script>",
        )
        assert deal.notes is not None
        assert "<b>" not in deal.notes
        assert "<script>" not in deal.notes
        assert "Bold notes" in deal.notes

    def test_deal_create_sanitizes_broker_name(self) -> None:
        deal = DealCreate(
            name="Test Deal",
            deal_type="acquisition",
            broker_name="John <img src=x onerror=alert(1)> Doe",
        )
        assert deal.broker_name is not None
        assert "<img" not in deal.broker_name
        assert "onerror" not in deal.broker_name

    def test_deal_create_sanitizes_tags(self) -> None:
        deal = DealCreate(
            name="Test Deal",
            deal_type="acquisition",
            tags=["<b>tag1</b>", "normal-tag"],
        )
        assert deal.tags is not None
        assert deal.tags[0] == "tag1"
        assert deal.tags[1] == "normal-tag"

    def test_deal_create_none_fields_preserved(self) -> None:
        deal = DealCreate(
            name="Clean Deal",
            deal_type="acquisition",
        )
        assert deal.notes is None
        assert deal.broker_name is None
        assert deal.tags is None

    def test_deal_update_sanitizes_fields(self) -> None:
        deal = DealUpdate(
            name="<em>Updated</em> Deal",
            notes="Notes with <a href='javascript:alert(1)'>link</a>",
            version=1,
        )
        assert deal.name is not None
        assert "<em>" not in deal.name
        assert deal.notes is not None
        assert "javascript" not in deal.notes.lower()


class TestPropertySchemaSanitization:
    """Tests that PropertyCreate/Update sanitize text fields."""

    def test_property_create_sanitizes_name(self) -> None:
        prop = PropertyCreate(
            name="<b>Hayden</b> Park Apartments",
            property_type="multifamily",
            address="123 Main St",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
        )
        assert "<b>" not in prop.name
        assert "Hayden" in prop.name

    def test_property_create_sanitizes_description(self) -> None:
        prop = PropertyCreate(
            name="Test Property",
            property_type="multifamily",
            address="123 Main St",
            city="Phoenix",
            state="AZ",
            zip_code="85001",
            description="<script>alert('xss')</script>Nice property",
        )
        assert prop.description is not None
        assert "<script>" not in prop.description

    def test_property_update_sanitizes_fields(self) -> None:
        prop = PropertyUpdate(
            name="<em>Updated</em> Name",
            description="<b>Description</b>",
        )
        assert prop.name is not None
        assert "<em>" not in prop.name
        assert prop.description is not None
        assert "<b>" not in prop.description


class TestDocumentSchemaSanitization:
    """Tests that Document schemas sanitize text fields."""

    def test_document_create_sanitizes_name(self) -> None:
        doc = DocumentCreate(
            name="<script>evil</script>Report.pdf",
            type="financial",
            description="<b>Bold</b> description",
        )
        assert "<script>" not in doc.name
        assert doc.description is not None
        assert "<b>" not in doc.description

    def test_document_update_sanitizes_fields(self) -> None:
        doc = DocumentUpdate(
            name="<em>Updated</em> Doc",
            description="<img src=x onerror=alert(1)>desc",
        )
        assert doc.name is not None
        assert "<em>" not in doc.name
        assert doc.description is not None
        assert "onerror" not in doc.description


class TestUserSchemaSanitization:
    """Tests that User schemas sanitize text fields."""

    def test_user_create_sanitizes_name(self) -> None:
        user = UserCreate(
            email="test@example.com",
            full_name="<script>alert('xss')</script>John Doe",
            password="Secure@pass1",
        )
        assert "<script>" not in user.full_name
        assert "John Doe" in user.full_name

    def test_user_update_sanitizes_department(self) -> None:
        user = UserUpdate(
            department="<b>Acquisitions</b>",
        )
        assert user.department is not None
        assert "<b>" not in user.department
        assert "Acquisitions" in user.department
