"""Integration tests for end-to-end conversion."""

import tempfile
from pathlib import Path

import pytest
import respx
from httpx import Response

from arxiv_to_ereader import convert_to_pdf, fetch_paper, parse_paper
from arxiv_to_ereader.fetcher import ArxivFetchError, ArxivHTMLNotAvailable

# Realistic arXiv HTML sample
REALISTIC_ARXIV_HTML = """
<!DOCTYPE html>
<html lang="en" xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta charset="utf-8"/>
    <meta name="citation_title" content="Attention Is All You Need"/>
    <meta name="citation_author" content="Vaswani, Ashish"/>
    <meta name="citation_author" content="Shazeer, Noam"/>
    <meta name="citation_author" content="Parmar, Niki"/>
    <meta name="citation_date" content="2017-06-12"/>
    <meta name="description" content="The dominant sequence transduction models are based on complex recurrent or convolutional neural networks."/>
    <title>[1706.03762] Attention Is All You Need</title>
</head>
<body>
<article class="ltx_document">
    <h1 class="ltx_title ltx_title_document">Attention Is All You Need</h1>
    <div class="ltx_authors">
        <span class="ltx_personname">Ashish Vaswani</span>
        <span class="ltx_personname">Noam Shazeer</span>
        <span class="ltx_personname">Niki Parmar</span>
    </div>
    <div class="ltx_abstract">
        <p>The dominant sequence transduction models are based on complex recurrent or
        convolutional neural networks that include an encoder and a decoder. The best
        performing models also connect the encoder and decoder through an attention mechanism.</p>
    </div>
    <section class="ltx_section" id="S1">
        <h2 class="ltx_title ltx_title_section">1 Introduction</h2>
        <div class="ltx_para">
            <p>Recurrent neural networks, long short-term memory and gated recurrent neural
            networks in particular, have been firmly established as state of the art approaches
            in sequence modeling and transduction problems such as language modeling and
            machine translation.</p>
        </div>
    </section>
    <section class="ltx_section" id="S2">
        <h2 class="ltx_title ltx_title_section">2 Background</h2>
        <div class="ltx_para">
            <p>The goal of reducing sequential computation also forms the foundation of the
            Extended Neural GPU, ByteNet and ConvS2S, all of which use convolutional neural
            networks as basic building block.</p>
        </div>
        <section class="ltx_subsection" id="S2.SS1">
            <h3 class="ltx_title ltx_title_subsection">2.1 Self-Attention</h3>
            <div class="ltx_para">
                <p>Self-attention, sometimes called intra-attention is an attention mechanism
                relating different positions of a single sequence.</p>
            </div>
        </section>
    </section>
    <section class="ltx_section" id="S3">
        <h2 class="ltx_title ltx_title_section">3 Model Architecture</h2>
        <div class="ltx_para">
            <p>Most competitive neural sequence transduction models have an encoder-decoder
            structure. Here, the encoder maps an input sequence of symbol representations.</p>
        </div>
        <figure class="ltx_figure" id="fig1">
            <img src="/html/1706.03762/transformer.png" alt="Transformer architecture"/>
            <figcaption class="ltx_caption">Figure 1: The Transformer model architecture.</figcaption>
        </figure>
    </section>
    <section class="ltx_section" id="S4">
        <h2 class="ltx_title ltx_title_section">4 Conclusion</h2>
        <div class="ltx_para">
            <p>In this work, we presented the Transformer, the first sequence transduction
            model based entirely on attention.</p>
        </div>
    </section>
    <section class="ltx_bibliography" id="bib">
        <h2 class="ltx_title ltx_title_bibliography">References</h2>
        <ul class="ltx_biblist">
            <li class="ltx_bibitem" id="bib1">
                [1] Bahdanau et al. Neural machine translation by jointly learning to align
                and translate. ICLR 2015.
            </li>
            <li class="ltx_bibitem" id="bib2">
                [2] Gehring et al. Convolutional sequence to sequence learning. ICML 2017.
            </li>
        </ul>
    </section>
</article>
</body>
</html>
"""


class TestEndToEndConversion:
    """End-to-end integration tests."""

    @respx.mock
    def test_fetch_parse_convert_pipeline(self) -> None:
        """Test the complete fetch -> parse -> convert pipeline."""
        paper_id = "1706.03762"
        respx.get(f"https://arxiv.org/html/{paper_id}").mock(
            return_value=Response(200, text=REALISTIC_ARXIV_HTML)
        )

        # Fetch
        fetched_id, html = fetch_paper(paper_id)
        assert fetched_id == paper_id
        assert "Attention Is All You Need" in html

        # Parse
        paper = parse_paper(html, fetched_id)
        assert paper.title == "Attention Is All You Need"
        assert len(paper.authors) == 3
        assert "Ashish Vaswani" in paper.authors
        assert len(paper.sections) >= 4

        # Convert
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "transformer.pdf"
            result = convert_to_pdf(paper, output_path, download_images=False)

            assert result.exists()
            # Check it's a valid PDF
            with open(result, "rb") as f:
                header = f.read(8)
            assert header.startswith(b"%PDF-")

    @respx.mock
    def test_fetch_404_raises_not_available(self) -> None:
        """Test that 404 raises ArxivHTMLNotAvailable."""
        paper_id = "0000.00000"
        respx.get(f"https://arxiv.org/html/{paper_id}").mock(
            return_value=Response(404)
        )

        with pytest.raises(ArxivHTMLNotAvailable):
            fetch_paper(paper_id)

    @respx.mock
    def test_fetch_500_raises_fetch_error(self) -> None:
        """Test that 500 raises ArxivFetchError."""
        paper_id = "1234.56789"
        respx.get(f"https://arxiv.org/html/{paper_id}").mock(
            return_value=Response(500)
        )

        with pytest.raises(ArxivFetchError):
            fetch_paper(paper_id)

    @respx.mock
    def test_batch_conversion(self) -> None:
        """Test converting multiple papers."""
        papers = ["1706.03762", "1234.56789"]

        for paper_id in papers:
            respx.get(f"https://arxiv.org/html/{paper_id}").mock(
                return_value=Response(200, text=REALISTIC_ARXIV_HTML)
            )

        with tempfile.TemporaryDirectory() as tmpdir:
            for paper_id in papers:
                _, html = fetch_paper(paper_id)
                paper = parse_paper(html, paper_id)
                output_path = Path(tmpdir) / f"{paper_id}.pdf"
                result = convert_to_pdf(paper, output_path, download_images=False)
                assert result.exists()


class TestUnicodeHandling:
    """Tests for Unicode and special character handling."""

    def test_unicode_in_title(self) -> None:
        """Test parsing titles with Unicode characters."""
        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1 class="ltx_title ltx_title_document">Uber die Losung von Gleichungen mit a, b, g</h1>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        assert "Uber" in paper.title

    def test_unicode_in_authors(self) -> None:
        """Test parsing authors with Unicode names."""
        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <div class="ltx_authors">
                <span class="ltx_personname">Jose Garcia</span>
                <span class="ltx_personname">Francois Muller</span>
            </div>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        assert "Jose Garcia" in paper.authors

    def test_unicode_pdf_generation(self) -> None:
        """Test that Unicode content survives PDF generation."""
        from arxiv_to_ereader.parser import Paper, Section

        paper = Paper(
            id="0000.00000",
            title="Equations differentielles avec alpha et beta",
            authors=["Jose Garcia", "Francois Muller"],
            abstract="For all epsilon > 0, there exists delta > 0",
            sections=[
                Section(
                    id="S1",
                    title="Introduction",
                    level=1,
                    content="<p>Content here.</p>",
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "unicode.pdf"
            result = convert_to_pdf(paper, output_path, download_images=False)
            assert result.exists()
            # PDF should be valid
            with open(result, "rb") as f:
                header = f.read(8)
            assert header.startswith(b"%PDF-")


class TestMalformedHTML:
    """Tests for handling malformed or unusual HTML."""

    def test_missing_closing_tags(self) -> None:
        """Test handling HTML with missing closing tags."""
        html = """
        <html>
        <head><title>Test
        <body>
            <h1 class="ltx_title ltx_title_document">Paper Title
            <div class="ltx_abstract">
                <p>Abstract content
        """
        # Should not raise, BeautifulSoup handles this
        paper = parse_paper(html, "0000.00000")
        assert "Paper Title" in paper.title

    def test_deeply_nested_content(self) -> None:
        """Test handling deeply nested HTML."""
        nested = "<div>" * 50 + "Content" + "</div>" * 50
        html = f"""
        <html>
        <head><title>Test</title></head>
        <body>
            <h1 class="ltx_title ltx_title_document">Title</h1>
            <section class="ltx_section" id="S1">
                <h2 class="ltx_title ltx_title_section">Section</h2>
                {nested}
            </section>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        assert len(paper.sections) > 0

    def test_empty_html(self) -> None:
        """Test handling empty HTML."""
        html = ""
        paper = parse_paper(html, "0000.00000")
        assert paper.id == "0000.00000"
        # Should have fallback title
        assert paper.title is not None

    def test_html_with_script_tags(self) -> None:
        """Test that script tags don't cause issues."""
        html = """
        <html>
        <head>
            <title>Test</title>
            <script>alert('xss')</script>
        </head>
        <body>
            <h1 class="ltx_title ltx_title_document">Title</h1>
            <script type="text/javascript">
                var x = 1;
            </script>
            <div class="ltx_abstract"><p>Abstract</p></div>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        assert paper.title == "Title"
        assert "Abstract" in paper.abstract


class TestPdfValidity:
    """Tests for PDF structural validity."""

    def test_pdf_has_valid_header(self) -> None:
        """Test that PDF has valid header."""
        from arxiv_to_ereader.parser import Paper

        paper = Paper(
            id="test.00001",
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(paper, output_path, download_images=False)

            with open(result, "rb") as f:
                header = f.read(8)
            assert header.startswith(b"%PDF-")

    def test_pdf_has_eof_marker(self) -> None:
        """Test that PDF has EOF marker."""
        from arxiv_to_ereader.parser import Paper

        paper = Paper(
            id="test.00001",
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(paper, output_path, download_images=False)

            with open(result, "rb") as f:
                f.seek(-100, 2)  # Read last 100 bytes
                tail = f.read()
            assert b"%%EOF" in tail

    def test_pdf_with_pypdf(self) -> None:
        """Test that PDF can be parsed by pypdf."""
        pypdf = pytest.importorskip("pypdf")
        from pypdf import PdfReader
        from arxiv_to_ereader.parser import Paper

        paper = Paper(
            id="test.00001",
            title="Test Paper Title",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.pdf"
            result = convert_to_pdf(paper, output_path, download_images=False)

            reader = PdfReader(result)
            assert len(reader.pages) > 0
