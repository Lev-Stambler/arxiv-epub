"""Tests for responsive CSS and screen size handling."""

import tempfile
import zipfile
from pathlib import Path

import pytest

from arxiv_to_ereader.converter import convert_to_epub
from arxiv_to_ereader.parser import Paper, Section
from arxiv_to_ereader.styles import (
    BASE_CSS,
    KINDLE_MEDIA_QUERIES,
    STYLE_PRESETS,
    get_stylesheet,
)


class TestResponsiveCSS:
    """Tests for responsive CSS stylesheet."""

    def test_stylesheet_contains_base_css(self) -> None:
        """Test that stylesheet includes base CSS."""
        css = get_stylesheet()
        assert "font-family" in css
        assert "line-height" in css

    def test_stylesheet_contains_kindle_media_queries(self) -> None:
        """Test that stylesheet includes Kindle-specific media queries."""
        css = get_stylesheet()
        # KF8 format query for Kindle
        assert "@media amzn-kf8" in css

    def test_stylesheet_contains_screen_size_queries(self) -> None:
        """Test that stylesheet includes screen size media queries."""
        css = get_stylesheet()
        # Should have queries for different screen sizes
        assert "max-width: 600px" in css or "max-width:600px" in css
        assert "min-width:" in css

    def test_images_responsive(self) -> None:
        """Test that images use responsive sizing."""
        css = get_stylesheet()
        assert "max-width: 100%" in css or "max-width:100%" in css

    def test_kindle_fire_specific_query(self) -> None:
        """Test that Kindle Fire specific query exists."""
        css = get_stylesheet()
        # Kindle Fire aspect ratio query
        assert "device-aspect-ratio" in css or "1280" in css

    def test_style_preset_default(self) -> None:
        """Test default style preset."""
        css = get_stylesheet("default")
        # Should contain base CSS
        assert "body {" in css or "body{" in css

    def test_style_preset_compact(self) -> None:
        """Test compact style preset."""
        css = get_stylesheet("compact")
        # Compact has smaller font size
        assert "0.9em" in css

    def test_style_preset_large_text(self) -> None:
        """Test large-text style preset."""
        css = get_stylesheet("large-text")
        # Large text has bigger font size
        assert "1.2em" in css


class TestKindleDeviceQueries:
    """Tests for Kindle device-specific CSS."""

    def test_paperwhite_optimization(self) -> None:
        """Test CSS works for Kindle Paperwhite (6\" screen)."""
        css = get_stylesheet()
        # Small screen optimizations should be present
        assert "@media" in css
        # Paperwhite is typically < 600px
        assert "600px" in css

    def test_oasis_optimization(self) -> None:
        """Test CSS works for Kindle Oasis (7\" screen)."""
        css = get_stylesheet()
        # Medium screen range
        assert "601px" in css or "1024px" in css

    def test_fire_tablet_optimization(self) -> None:
        """Test CSS works for Kindle Fire tablets."""
        css = get_stylesheet()
        # KF8 format support
        assert "amzn-kf8" in css


class TestViewportConfiguration:
    """Tests for viewport and sizing configuration in EPUBs."""

    @pytest.fixture
    def sample_paper(self) -> Paper:
        """Create a sample paper for testing."""
        return Paper(
            id="test.00001",
            title="Test Paper",
            authors=["Test Author"],
            abstract="Test abstract.",
            sections=[
                Section(
                    id="S1",
                    title="Test Section",
                    level=1,
                    content="<p>Test content.</p>",
                )
            ],
        )

    def test_epub_includes_responsive_css(self, sample_paper: Paper) -> None:
        """Test that generated EPUB includes responsive CSS."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                css_files = [n for n in zf.namelist() if n.endswith(".css")]
                assert css_files

                css_content = zf.read(css_files[0]).decode("utf-8")

                # Should have media queries
                assert "@media" in css_content
                # Should have Kindle-specific
                assert "amzn-kf8" in css_content

    def test_epub_css_has_image_responsive(self, sample_paper: Paper) -> None:
        """Test that EPUB CSS makes images responsive."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(sample_paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                css_files = [n for n in zf.namelist() if n.endswith(".css")]
                css_content = zf.read(css_files[0]).decode("utf-8")

                # Images should have max-width: 100%
                assert "max-width: 100%" in css_content or "max-width:100%" in css_content


class TestScreenSizeHandling:
    """Tests for handling different screen sizes."""

    def test_base_css_uses_relative_units(self) -> None:
        """Test that base CSS uses relative units for scalability."""
        css = BASE_CSS
        # Should use em for font sizes
        assert "1em" in css or "1.0em" in css

    def test_no_fixed_pixel_fonts(self) -> None:
        """Test that CSS doesn't use fixed pixel font sizes."""
        css = get_stylesheet()
        # Font sizes should be in em, not px
        # Note: px is okay for borders, margins in some cases
        lines = css.split("\n")
        for line in lines:
            if "font-size:" in line:
                # Should use em, not px
                assert "em" in line or "%" in line, f"Fixed pixel font found: {line}"

    def test_tables_responsive(self) -> None:
        """Test that tables use responsive styling."""
        css = get_stylesheet()
        assert "width: 100%" in css or "width:100%" in css

    def test_preformatted_text_wraps(self) -> None:
        """Test that preformatted text wraps properly."""
        css = get_stylesheet()
        assert "white-space: pre-wrap" in css or "pre-wrap" in css
        assert "word-wrap: break-word" in css or "break-word" in css
