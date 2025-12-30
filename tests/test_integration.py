"""Integration tests for end-to-end conversion."""

import tempfile
import zipfile
from pathlib import Path

import pytest
import respx
from httpx import Response

from arxiv_to_ereader import convert_to_epub, fetch_paper, parse_paper
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
        """Test the complete fetch → parse → convert pipeline."""
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
            output_path = Path(tmpdir) / "transformer.epub"
            result = convert_to_epub(paper, output_path, download_images=False)

            assert result.exists()
            assert zipfile.is_zipfile(result)

            # Verify EPUB contents
            with zipfile.ZipFile(result, "r") as zf:
                names = zf.namelist()
                assert any("cover" in n for n in names)
                assert any("abstract" in n for n in names)
                assert any("section" in n for n in names)

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
                output_path = Path(tmpdir) / f"{paper_id}.epub"
                result = convert_to_epub(paper, output_path, download_images=False)
                assert result.exists()


class TestUnicodeHandling:
    """Tests for Unicode and special character handling."""

    def test_unicode_in_title(self) -> None:
        """Test parsing titles with Unicode characters."""
        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <h1 class="ltx_title ltx_title_document">Über die Lösung von Gleichungen mit α, β, γ</h1>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        assert "Über" in paper.title
        assert "α" in paper.title

    def test_unicode_in_authors(self) -> None:
        """Test parsing authors with Unicode names."""
        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <div class="ltx_authors">
                <span class="ltx_personname">José García</span>
                <span class="ltx_personname">François Müller</span>
                <span class="ltx_personname">北野 武</span>
            </div>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        assert "José García" in paper.authors
        assert "François Müller" in paper.authors
        assert "北野 武" in paper.authors

    def test_unicode_in_abstract(self) -> None:
        """Test parsing abstracts with math symbols."""
        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <div class="ltx_abstract">
                <p>We prove that ∀ε > 0, ∃δ such that |x - x₀| < δ implies |f(x) - L| < ε.</p>
            </div>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        assert "∀ε" in paper.abstract
        assert "∃δ" in paper.abstract

    def test_unicode_epub_generation(self) -> None:
        """Test that Unicode content survives EPUB generation."""
        from arxiv_to_ereader.parser import Paper, Section

        paper = Paper(
            id="0000.00000",
            title="Équations différentielles avec α et β",
            authors=["José García", "François Müller"],
            abstract="∀ε > 0, ∃δ > 0",
            sections=[
                Section(
                    id="S1",
                    title="Введение",  # Russian "Introduction"
                    level=1,
                    content="<p>中文内容</p>",  # Chinese content
                )
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "unicode.epub"
            result = convert_to_epub(paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                # Check cover has Unicode title
                cover_files = [n for n in zf.namelist() if "cover" in n.lower()]
                cover_content = zf.read(cover_files[0]).decode("utf-8")
                assert "Équations" in cover_content
                assert "José García" in cover_content


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


class TestEpubValidation:
    """Tests for EPUB structural validity."""

    def test_epub_mimetype_first(self) -> None:
        """Test that mimetype is the first file in the ZIP (EPUB requirement)."""
        from arxiv_to_ereader.parser import Paper

        paper = Paper(
            id="test.00001",
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                # mimetype should be first entry
                assert zf.namelist()[0] == "mimetype"

    def test_epub_container_xml_exists(self) -> None:
        """Test that META-INF/container.xml exists."""
        from arxiv_to_ereader.parser import Paper

        paper = Paper(
            id="test.00001",
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                assert "META-INF/container.xml" in zf.namelist()

    def test_epub_has_opf_file(self) -> None:
        """Test that the EPUB has a .opf package file."""
        from arxiv_to_ereader.parser import Paper

        paper = Paper(
            id="test.00001",
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                opf_files = [n for n in zf.namelist() if n.endswith(".opf")]
                assert len(opf_files) == 1

    def test_epub_has_ncx_toc(self) -> None:
        """Test that the EPUB has NCX table of contents."""
        from arxiv_to_ereader.parser import Paper

        paper = Paper(
            id="test.00001",
            title="Test",
            authors=["Author"],
            abstract="Abstract",
            sections=[],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "test.epub"
            result = convert_to_epub(paper, output_path, download_images=False)

            with zipfile.ZipFile(result, "r") as zf:
                ncx_files = [n for n in zf.namelist() if n.endswith(".ncx")]
                assert len(ncx_files) == 1
