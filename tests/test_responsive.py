"""Tests for PDF styling and screen presets."""

import tempfile
from pathlib import Path

import pytest

from arxiv_to_ereader.converter import convert_to_pdf
from arxiv_to_ereader.parser import Paper, Section
from arxiv_to_ereader.screen_presets import SCREEN_PRESETS, get_preset
from arxiv_to_ereader.styles import get_pdf_stylesheet


class TestPdfStylesheet:
    """Tests for PDF stylesheet generation."""

    def test_stylesheet_contains_page_rule(self) -> None:
        """Test that stylesheet includes @page CSS rule."""
        preset = get_preset("kindle-paperwhite")
        css = get_pdf_stylesheet(preset)
        assert "@page" in css

    def test_stylesheet_sets_page_size(self) -> None:
        """Test that stylesheet sets page size in mm."""
        preset = get_preset("kindle-paperwhite")
        css = get_pdf_stylesheet(preset)
        assert f"{preset.width_mm}mm" in css
        assert f"{preset.height_mm}mm" in css

    def test_stylesheet_uses_base_font(self) -> None:
        """Test that stylesheet uses preset's base font size."""
        preset = get_preset("kindle-paperwhite")
        css = get_pdf_stylesheet(preset)
        assert f"{preset.base_font_pt}pt" in css

    def test_images_responsive(self) -> None:
        """Test that images use responsive sizing."""
        preset = get_preset("kindle-paperwhite")
        css = get_pdf_stylesheet(preset)
        assert "max-width: 100%" in css or "max-width:100%" in css

    def test_different_presets_different_sizes(self) -> None:
        """Test that different presets have different page sizes."""
        paperwhite = get_preset("kindle-paperwhite")
        scribe = get_preset("kindle-scribe")

        css_pw = get_pdf_stylesheet(paperwhite)
        css_sc = get_pdf_stylesheet(scribe)

        # Kindle Scribe is larger
        assert f"{scribe.width_mm}mm" in css_sc
        assert f"{paperwhite.width_mm}mm" in css_pw
        assert scribe.width_mm > paperwhite.width_mm


class TestScreenPresets:
    """Tests for screen preset configurations."""

    def test_paperwhite_optimization(self) -> None:
        """Test Kindle Paperwhite preset."""
        preset = get_preset("kindle-paperwhite")
        # 6.8" screen should be around 105x140mm
        assert 100 < preset.width_mm < 110
        assert 135 < preset.height_mm < 145
        assert preset.ppi == 300

    def test_scribe_optimization(self) -> None:
        """Test Kindle Scribe preset."""
        preset = get_preset("kindle-scribe")
        # 10.2" screen should be around 158x210mm
        assert 155 < preset.width_mm < 165
        assert 200 < preset.height_mm < 215
        assert preset.ppi == 300

    def test_remarkable_optimization(self) -> None:
        """Test reMarkable preset."""
        preset = get_preset("remarkable")
        # 10.3" screen should be around 158x210mm
        assert 155 < preset.width_mm < 165
        assert preset.ppi == 226  # reMarkable has lower PPI

    def test_larger_screens_have_larger_fonts(self) -> None:
        """Test that larger screens get slightly larger base fonts."""
        paperwhite = get_preset("kindle-paperwhite")
        scribe = get_preset("kindle-scribe")
        # Larger screen can use larger font
        assert scribe.base_font_pt >= paperwhite.base_font_pt


class TestPdfGeneration:
    """Tests for PDF generation with different presets."""

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

    def test_pdf_with_default_preset(self, sample_paper: Paper) -> None:
        """Test PDF generation with default preset."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(sample_paper, output_path, download_images=False)

            assert result.exists()
            # Check it's a valid PDF
            with open(result, "rb") as f:
                header = f.read(8)
            assert header.startswith(b"%PDF-")

    def test_pdf_with_all_presets(self, sample_paper: Paper) -> None:
        """Test PDF generation with all available presets."""
        with tempfile.TemporaryDirectory() as tmpdir:
            for preset_name in SCREEN_PRESETS:
                output_path = Path(tmpdir) / f"test_{preset_name}.pdf"
                result = convert_to_pdf(
                    sample_paper,
                    output_path,
                    screen_preset=preset_name,
                    download_images=False,
                )
                assert result.exists()


class TestTextHandling:
    """Tests for text styling in PDFs."""

    def test_stylesheet_uses_relative_units(self) -> None:
        """Test that stylesheet uses pt for fonts (appropriate for PDF)."""
        preset = get_preset("kindle-paperwhite")
        css = get_pdf_stylesheet(preset)
        # PDF should use pt for fonts
        assert "pt" in css

    def test_tables_responsive(self) -> None:
        """Test that tables use full width."""
        preset = get_preset("kindle-paperwhite")
        css = get_pdf_stylesheet(preset)
        assert "width: 100%" in css or "width:100%" in css

    def test_preformatted_text_wraps(self) -> None:
        """Test that preformatted text wraps properly."""
        preset = get_preset("kindle-paperwhite")
        css = get_pdf_stylesheet(preset)
        assert "white-space: pre-wrap" in css or "pre-wrap" in css
        assert "word-wrap: break-word" in css or "break-word" in css

    def test_page_break_controls(self) -> None:
        """Test that page break controls are in place."""
        preset = get_preset("kindle-paperwhite")
        css = get_pdf_stylesheet(preset)
        assert "page-break" in css
        assert "orphans" in css or "widows" in css
