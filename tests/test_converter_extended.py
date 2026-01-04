"""Extended converter tests."""

import tempfile
from pathlib import Path

import pytest
import respx
from httpx import Response

from arxiv_to_ereader.converter import (
    _download_image,
    convert_to_pdf,
)
from arxiv_to_ereader.parser import Figure, Footnote, Paper, Section


class TestImageDownload:
    """Tests for image download functionality."""

    @respx.mock
    def test_download_image_success(self) -> None:
        """Test successful image download."""
        image_url = "https://arxiv.org/html/1234.56789/figure1.png"
        image_content = b"\x89PNG\r\n\x1a\n fake png data"

        respx.get(image_url).mock(
            return_value=Response(
                200,
                content=image_content,
                headers={"content-type": "image/png"},
            )
        )

        result = _download_image(image_url)
        assert result is not None
        data, media_type = result
        assert data == image_content
        assert media_type == "image/png"

    @respx.mock
    def test_download_image_jpeg(self) -> None:
        """Test downloading JPEG image."""
        image_url = "https://arxiv.org/html/1234.56789/figure1.jpg"
        image_content = b"\xff\xd8\xff fake jpeg"

        respx.get(image_url).mock(
            return_value=Response(
                200,
                content=image_content,
                headers={"content-type": "image/jpeg; charset=utf-8"},
            )
        )

        result = _download_image(image_url)
        assert result is not None
        _, media_type = result
        assert media_type == "image/jpeg"

    @respx.mock
    def test_download_image_failure(self) -> None:
        """Test failed image download returns None."""
        image_url = "https://arxiv.org/html/1234.56789/missing.png"

        respx.get(image_url).mock(return_value=Response(404))

        result = _download_image(image_url)
        assert result is None

    @respx.mock
    def test_download_image_timeout(self) -> None:
        """Test image download timeout returns None."""
        import httpx

        image_url = "https://arxiv.org/html/1234.56789/slow.png"

        respx.get(image_url).mock(side_effect=httpx.TimeoutException("timeout"))

        result = _download_image(image_url)
        assert result is None


class TestConverterWithImages:
    """Tests for converter with image handling."""

    @respx.mock
    def test_convert_with_images(self) -> None:
        """Test conversion with image downloading."""
        image_url = "https://arxiv.org/html/test/figure1.png"
        image_content = b"\x89PNG\r\n\x1a\n fake png"

        respx.get(image_url).mock(
            return_value=Response(
                200,
                content=image_content,
                headers={"content-type": "image/png"},
            )
        )

        paper = Paper(
            id="test.00001",
            title="Test Paper with Images",
            authors=["Author"],
            abstract="Abstract",
            sections=[
                Section(
                    id="S1",
                    title="Results",
                    level=1,
                    content=f'<p>See figure: <img src="{image_url}"/></p>',
                )
            ],
            figures=[
                Figure(
                    id="fig1",
                    caption="Test figure",
                    image_url=image_url,
                )
            ],
            all_images={image_url: image_url},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(paper, output_path, download_images=True)

            assert result.exists()
            # PDF with images should be larger
            assert result.stat().st_size > 1000

    @respx.mock
    def test_convert_with_missing_images(self) -> None:
        """Test conversion continues when images fail to download."""
        image_url = "https://arxiv.org/html/test/missing.png"

        respx.get(image_url).mock(return_value=Response(404))

        paper = Paper(
            id="test.00001",
            title="Test Paper",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
            figures=[
                Figure(
                    id="fig1",
                    caption="Missing figure",
                    image_url=image_url,
                )
            ],
            all_images={image_url: image_url},
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            # Should not raise, just skip the image
            result = convert_to_pdf(paper, output_path, download_images=True)
            assert result.exists()


class TestConverterEdgeCases:
    """Edge case tests for the converter."""

    def test_convert_paper_without_abstract(self) -> None:
        """Test converting paper with no abstract."""
        paper = Paper(
            id="test.00001",
            title="Paper Without Abstract",
            authors=["Author"],
            abstract="",  # Empty abstract
            sections=[
                Section(id="S1", title="Content", level=1, content="<p>Text</p>")
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(paper, output_path, download_images=False)
            assert result.exists()

    def test_convert_paper_without_sections(self) -> None:
        """Test converting paper with no sections."""
        paper = Paper(
            id="test.00001",
            title="Paper Without Sections",
            authors=["Author"],
            abstract="Just an abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(paper, output_path, download_images=False)
            assert result.exists()

    def test_convert_paper_without_references(self) -> None:
        """Test converting paper with no references."""
        paper = Paper(
            id="test.00001",
            title="Paper",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
            references_html=None,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(paper, output_path, download_images=False)
            assert result.exists()

    def test_convert_paper_without_date(self) -> None:
        """Test converting paper with no date."""
        paper = Paper(
            id="test.00001",
            title="Paper",
            authors=["Author"],
            abstract="Abstract",
            date=None,
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(paper, output_path, download_images=False)
            assert result.exists()

    def test_convert_paper_with_old_format_id(self) -> None:
        """Test converting paper with old-format arXiv ID."""
        paper = Paper(
            id="hep-th/9901001",
            title="Old Format Paper",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            import os

            original_cwd = os.getcwd()
            try:
                os.chdir(tmpdir)
                result = convert_to_pdf(paper, download_images=False)
                assert result.exists()
                # Filename should have slash replaced
                assert "hep-th_9901001" in result.name
            finally:
                os.chdir(original_cwd)


class TestMathMLRendering:
    """Tests for native MathML rendering via Playwright."""

    def test_pdf_with_inline_math(self) -> None:
        """Test PDF conversion with inline MathML."""
        paper = Paper(
            id="test.00001",
            title="Math Paper",
            authors=["Author"],
            abstract="A paper about math",
            sections=[
                Section(
                    id="S1",
                    title="Introduction",
                    level=1,
                    content='<p>Consider <math alttext="x"><mi>x</mi></math> in text.</p>',
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "math_test.pdf"
            result = convert_to_pdf(
                paper,
                output_path,
                download_images=False,
            )

            assert result.exists()
            assert result.stat().st_size > 1000

    def test_pdf_with_display_math(self) -> None:
        """Test PDF conversion with display (block) MathML."""
        paper = Paper(
            id="test.00001",
            title="Math Paper",
            authors=["Author"],
            abstract="A paper about math",
            sections=[
                Section(
                    id="S1",
                    title="Introduction",
                    level=1,
                    content='<div><math alttext="\\alpha + \\beta" display="block"><mi>α</mi><mo>+</mo><mi>β</mi></math></div>',
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "math_test.pdf"
            result = convert_to_pdf(
                paper,
                output_path,
                download_images=False,
            )

            assert result.exists()
            assert result.stat().st_size > 1000

    def test_pdf_with_complex_math(self) -> None:
        """Test PDF conversion with complex MathML expressions."""
        paper = Paper(
            id="test.00001",
            title="Complex Math Paper",
            authors=["Author"],
            abstract="A paper with complex math",
            sections=[
                Section(
                    id="S1",
                    title="Equations",
                    level=1,
                    content='''<p>The equation <math display="block">
                        <mrow>
                            <mi>E</mi><mo>=</mo><mi>m</mi><msup><mi>c</mi><mn>2</mn></msup>
                        </mrow>
                    </math> is famous.</p>''',
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "complex_math.pdf"
            result = convert_to_pdf(
                paper,
                output_path,
                download_images=False,
            )

            assert result.exists()
            assert result.stat().st_size > 1000


class TestFootnotesConversion:
    """Tests for footnotes in converter."""

    def test_pdf_with_footnotes(self) -> None:
        """Test PDF generation with footnotes."""
        paper = Paper(
            id="test.00001",
            title="Paper with Footnotes",
            authors=["Author"],
            abstract="Abstract",
            sections=[
                Section(
                    id="S1",
                    title="Content",
                    level=1,
                    content='<p>Text with note.<a href="#fn-1" id="fnref-1" class="footnote-ref"><sup>1</sup></a></p>',
                )
            ],
            footnotes=[
                Footnote(id="fn-1", index=1, content="This is a footnote.")
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "footnotes_test.pdf"
            result = convert_to_pdf(paper, output_path, download_images=False)

            assert result.exists()
            assert result.stat().st_size > 1000
