"""Tests for the parser module."""

from arxiv_to_ereader.parser import parse_paper


class TestParsePaper:
    """Tests for parse_paper function."""

    def test_parse_title(self, sample_html: str, sample_paper_id: str) -> None:
        """Test extracting paper title."""
        paper = parse_paper(sample_html, sample_paper_id)
        assert paper.title == "A Sample Paper on Machine Learning"

    def test_parse_authors(self, sample_html: str, sample_paper_id: str) -> None:
        """Test extracting authors."""
        paper = parse_paper(sample_html, sample_paper_id)
        assert len(paper.authors) == 2
        assert "John Doe" in paper.authors
        assert "Jane Smith" in paper.authors

    def test_parse_abstract(self, sample_html: str, sample_paper_id: str) -> None:
        """Test extracting abstract."""
        paper = parse_paper(sample_html, sample_paper_id)
        assert "main contributions" in paper.abstract

    def test_parse_date(self, sample_html: str, sample_paper_id: str) -> None:
        """Test extracting date."""
        paper = parse_paper(sample_html, sample_paper_id)
        assert paper.date == "2024-02-15"

    def test_parse_sections(self, sample_html: str, sample_paper_id: str) -> None:
        """Test extracting sections."""
        paper = parse_paper(sample_html, sample_paper_id)

        # Should have main sections
        section_titles = [s.title for s in paper.sections]
        assert any("Introduction" in t for t in section_titles)
        assert any("Methods" in t for t in section_titles)
        assert any("Results" in t for t in section_titles)

    def test_parse_subsections(self, sample_html: str, sample_paper_id: str) -> None:
        """Test extracting subsections with correct levels."""
        paper = parse_paper(sample_html, sample_paper_id)

        # Find the subsection
        subsections = [s for s in paper.sections if s.level == 2]
        assert len(subsections) > 0
        assert any("Data Collection" in s.title for s in subsections)

    def test_parse_figures(self, sample_html: str, sample_paper_id: str) -> None:
        """Test extracting figures."""
        paper = parse_paper(sample_html, sample_paper_id)

        assert len(paper.figures) == 1
        fig = paper.figures[0]
        assert fig.id == "fig1"
        assert "Results comparison" in fig.caption
        assert fig.image_url is not None

    def test_parse_references(self, sample_html: str, sample_paper_id: str) -> None:
        """Test extracting references section."""
        paper = parse_paper(sample_html, sample_paper_id)

        assert paper.references_html is not None
        assert "Author A" in paper.references_html

    def test_paper_id_preserved(self, sample_html: str, sample_paper_id: str) -> None:
        """Test that paper ID is preserved."""
        paper = parse_paper(sample_html, sample_paper_id)
        assert paper.id == sample_paper_id

    def test_base_url_set(self, sample_html: str, sample_paper_id: str) -> None:
        """Test that base URL is set correctly."""
        paper = parse_paper(sample_html, sample_paper_id)
        assert paper.base_url == f"https://arxiv.org/html/{sample_paper_id}/"

    def test_minimal_html(self, minimal_html: str) -> None:
        """Test parsing minimal HTML without LaTeXML structure."""
        paper = parse_paper(minimal_html, "0000.00000")

        # Should fall back to basic extraction
        assert "Minimal Paper" in paper.title
        assert paper.id == "0000.00000"


class TestParserEdgeCases:
    """Edge case tests for the parser."""

    def test_empty_authors(self) -> None:
        """Test handling HTML with no authors."""
        html = """
        <html>
        <head><title>No Authors Paper</title></head>
        <body>
            <h1 class="ltx_title ltx_title_document">Paper Without Authors</h1>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        assert paper.authors == []

    def test_authors_with_email(self) -> None:
        """Test extracting authors when email is embedded in personname."""
        html = """
        <html>
        <head><title>Test</title></head>
        <body>
            <div class="ltx_authors">
                <span class="ltx_personname">Test Team
                    <br/><span class="ltx_text">team@example.com</span>
                </span>
            </div>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        assert len(paper.authors) == 1
        assert paper.authors[0] == "Test Team"
        assert "@" not in paper.authors[0]

    def test_empty_abstract(self) -> None:
        """Test handling HTML with no abstract."""
        html = """
        <html>
        <head><title>No Abstract</title></head>
        <body>
            <h1 class="ltx_title ltx_title_document">Paper Without Abstract</h1>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        assert paper.abstract == ""

    def test_no_sections(self) -> None:
        """Test handling HTML with no sections."""
        html = """
        <html>
        <head><title>No Sections</title></head>
        <body>
            <article class="ltx_document">
                <h1>Title</h1>
                <p>Just a paragraph.</p>
            </article>
        </body>
        </html>
        """
        paper = parse_paper(html, "0000.00000")
        # Should either have no sections or a main content section
        assert isinstance(paper.sections, list)
