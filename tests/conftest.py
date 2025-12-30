"""Pytest fixtures for arxiv-epub tests."""

import pytest

# Sample arXiv HTML content (simplified LaTeXML output structure)
SAMPLE_ARXIV_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <meta name="citation_author" content="John Doe"/>
    <meta name="citation_author" content="Jane Smith"/>
    <meta name="citation_date" content="2024-02-15"/>
    <title>A Sample Paper on Machine Learning</title>
</head>
<body>
<article class="ltx_document">
    <h1 class="ltx_title ltx_title_document">A Sample Paper on Machine Learning</h1>
    <div class="ltx_authors">
        <span class="ltx_personname">John Doe</span>
        <span class="ltx_personname">Jane Smith</span>
    </div>
    <div class="ltx_abstract">
        <p>This is the abstract of the paper. It describes the main contributions.</p>
    </div>
    <section class="ltx_section" id="S1">
        <h2 class="ltx_title ltx_title_section">1 Introduction</h2>
        <div class="ltx_para">
            <p>This is the introduction section with some text.</p>
        </div>
    </section>
    <section class="ltx_section" id="S2">
        <h2 class="ltx_title ltx_title_section">2 Methods</h2>
        <div class="ltx_para">
            <p>This section describes the methods used.</p>
        </div>
        <section class="ltx_subsection" id="S2.SS1">
            <h3 class="ltx_title ltx_title_subsection">2.1 Data Collection</h3>
            <div class="ltx_para">
                <p>Details about data collection.</p>
            </div>
        </section>
    </section>
    <section class="ltx_section" id="S3">
        <h2 class="ltx_title ltx_title_section">3 Results</h2>
        <div class="ltx_para">
            <p>Our results show significant improvements.</p>
        </div>
        <figure class="ltx_figure" id="fig1">
            <img src="/html/2402.08954/figure1.png" alt="Results graph"/>
            <figcaption class="ltx_caption">Figure 1: Results comparison</figcaption>
        </figure>
    </section>
    <section class="ltx_bibliography" id="bib">
        <h2 class="ltx_title ltx_title_bibliography">References</h2>
        <ul class="ltx_biblist">
            <li class="ltx_bibitem">[1] Author A. Title of Paper. Journal, 2023.</li>
            <li class="ltx_bibitem">[2] Author B. Another Paper. Conference, 2024.</li>
        </ul>
    </section>
</article>
</body>
</html>
"""


@pytest.fixture
def sample_html() -> str:
    """Return sample arXiv HTML content."""
    return SAMPLE_ARXIV_HTML


@pytest.fixture
def sample_paper_id() -> str:
    """Return a sample paper ID."""
    return "2402.08954"


# Sample HTML with minimal content for edge case testing
MINIMAL_HTML = """
<!DOCTYPE html>
<html>
<head><title>Minimal Paper</title></head>
<body>
<article>
    <h1>Minimal Paper Title</h1>
    <p>Some content.</p>
</article>
</body>
</html>
"""


@pytest.fixture
def minimal_html() -> str:
    """Return minimal HTML content for edge case testing."""
    return MINIMAL_HTML
