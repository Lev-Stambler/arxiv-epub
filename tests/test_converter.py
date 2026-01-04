"""Tests for the converter module."""

import tempfile
from pathlib import Path

import pytest

from arxiv_to_ereader.converter import convert_to_pdf
from arxiv_to_ereader.parser import Paper, Section


@pytest.fixture
def sample_paper() -> Paper:
    """Create a sample Paper object for testing."""
    return Paper(
        id="2402.08954",
        title="A Sample Paper on Machine Learning",
        authors=["John Doe", "Jane Smith"],
        abstract="This is the abstract of the paper.",
        date="2024-02-15",
        sections=[
            Section(
                id="S1",
                title="Introduction",
                level=1,
                content="<p>Introduction content here.</p>",
            ),
            Section(
                id="S2",
                title="Methods",
                level=1,
                content="<p>Methods content here.</p>",
            ),
            Section(
                id="S3",
                title="Results",
                level=1,
                content="<p>Results content here.</p>",
            ),
        ],
        figures=[],
        references_html="<ul><li>[1] A reference</li></ul>",
    )


class TestConvertToPdf:
    """Tests for convert_to_pdf function."""

    def test_creates_pdf_file(self, sample_paper: Paper) -> None:
        """Test that a PDF file is created."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(sample_paper, output_path, download_images=False)

            assert result.exists()
            assert result.suffix == ".pdf"

    def test_pdf_is_valid(self, sample_paper: Paper) -> None:
        """Test that the PDF is valid (starts with PDF header)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(sample_paper, output_path, download_images=False)

            with open(result, "rb") as f:
                header = f.read(8)
            assert header.startswith(b"%PDF-"), "File does not have PDF header"

    def test_pdf_has_content(self, sample_paper: Paper) -> None:
        """Test that the PDF has reasonable size (not empty)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(sample_paper, output_path, download_images=False)

            # PDF should be at least a few KB
            assert result.stat().st_size > 1000, "PDF seems too small"

    def test_default_output_path(self, sample_paper: Paper) -> None:
        """Test default output path uses paper ID."""
        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = convert_to_pdf(sample_paper, download_images=False)
                assert result.name == "2402.08954.pdf"
            finally:
                os.chdir(original_cwd)

    def test_screen_presets(self, sample_paper: Paper) -> None:
        """Test different screen presets produce valid PDFs."""
        presets = ["kindle-paperwhite", "kindle-scribe", "kobo-clara", "remarkable"]
        for preset in presets:
            with tempfile.TemporaryDirectory() as tmpdir:
                output_path = Path(tmpdir) / f"test_{preset}.pdf"
                result = convert_to_pdf(
                    sample_paper,
                    output_path,
                    screen_preset=preset,
                    download_images=False,
                )
                assert result.exists()
                assert result.stat().st_size > 1000

    def test_custom_dimensions(self, sample_paper: Paper) -> None:
        """Test custom page dimensions work."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_custom.pdf"
            result = convert_to_pdf(
                sample_paper,
                output_path,
                custom_width_mm=150,
                custom_height_mm=200,
                download_images=False,
            )
            assert result.exists()
            assert result.stat().st_size > 1000


class TestPdfContent:
    """Tests for PDF content correctness."""

    def test_pdf_readable_by_pypdf(self, sample_paper: Paper) -> None:
        """Test that the PDF can be read by pypdf (if available)."""
        pytest.importorskip("pypdf")
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(sample_paper, output_path, download_images=False)

            reader = PdfReader(result)
            assert len(reader.pages) > 0, "PDF has no pages"

    def test_title_in_pdf(self, sample_paper: Paper) -> None:
        """Test that the title appears in the PDF (check with pypdf if available)."""
        pypdf = pytest.importorskip("pypdf")
        from pypdf import PdfReader

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(sample_paper, output_path, download_images=False)

            reader = PdfReader(result)
            # Check first page for title (normalize whitespace for comparison)
            first_page_text = " ".join(reader.pages[0].extract_text().split())
            normalized_title = " ".join(sample_paper.title.split())
            assert normalized_title in first_page_text, "Title not found in PDF"


class TestMathRendering:
    """Tests for math equation rendering in PDF (native MathML via browser)."""

    def test_math_rendering(self) -> None:
        """Test that MathML renders correctly in PDF."""
        paper_with_math = Paper(
            id="test.math",
            title="Math Test",
            authors=["Test Author"],
            abstract="Abstract with no math",
            date="2024-01-01",
            sections=[
                Section(
                    id="S1",
                    title="Math Section",
                    level=1,
                    content='<p>Here is math: <math alttext="x^2"><mi>x</mi><msup><mn>2</mn></msup></math> in text.</p>',
                )
            ],
            figures=[],
            footnotes=[],
            references_html=None,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(
                paper_with_math, output_path, download_images=False
            )

            assert result.exists()
            assert result.stat().st_size > 1000


class TestRealPaperIntegration:
    """Integration tests with real arXiv papers (requires network)."""

    @pytest.mark.integration
    def test_real_paper_conversion(self) -> None:
        """Test converting a real arXiv paper to PDF."""
        from arxiv_to_ereader import fetch_paper, parse_paper

        # Use a paper known to have math (Mamba paper)
        paper_id = "2312.00752"

        try:
            fetched_id, html = fetch_paper(paper_id)
        except Exception as e:
            pytest.skip(f"Could not fetch paper (network issue?): {e}")

        paper = parse_paper(html, fetched_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(
                paper, output_path, download_images=False
            )

            assert result.exists()
            assert result.stat().st_size > 10000  # Should be substantial

            # Verify it's a valid PDF
            with open(result, "rb") as f:
                header = f.read(8)
            assert header.startswith(b"%PDF-")

    @pytest.mark.integration
    def test_real_paper_with_images(self) -> None:
        """Test converting a real arXiv paper with images to PDF."""
        from arxiv_to_ereader import fetch_paper, parse_paper

        paper_id = "2312.00752"

        try:
            fetched_id, html = fetch_paper(paper_id)
        except Exception as e:
            pytest.skip(f"Could not fetch paper (network issue?): {e}")

        paper = parse_paper(html, fetched_id)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test_with_images.pdf"
            result = convert_to_pdf(
                paper, output_path, download_images=True
            )

            assert result.exists()
            # With images should be larger
            assert result.stat().st_size > 50000
