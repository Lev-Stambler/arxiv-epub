"""Parse arXiv HTML papers."""

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag


@dataclass
class Figure:
    """A figure from the paper."""

    id: str
    caption: str
    image_url: str | None = None
    image_data: bytes | None = None
    image_type: str = "image/png"


@dataclass
class Section:
    """A section of the paper."""

    id: str
    title: str
    level: int  # 1 = h1, 2 = h2, etc.
    content: str  # HTML content


@dataclass
class Paper:
    """Parsed arXiv paper."""

    id: str
    title: str
    authors: list[str]
    abstract: str
    date: str | None = None
    sections: list[Section] = field(default_factory=list)
    figures: list[Figure] = field(default_factory=list)
    references_html: str | None = None
    base_url: str | None = None


def _clean_text(text: str) -> str:
    """Clean up text by normalizing whitespace."""
    return re.sub(r"\s+", " ", text).strip()


def _extract_title(soup: BeautifulSoup) -> str:
    """Extract paper title."""
    # Try LaTeXML title class
    title_elem = soup.select_one(".ltx_title.ltx_title_document")
    if title_elem:
        return _clean_text(title_elem.get_text())

    # Fallback to h1
    h1 = soup.find("h1")
    if h1:
        return _clean_text(h1.get_text())

    # Last resort: page title
    title_tag = soup.find("title")
    if title_tag:
        return _clean_text(title_tag.get_text())

    return "Untitled Paper"


def _extract_authors(soup: BeautifulSoup) -> list[str]:
    """Extract author names."""
    authors = []

    # Try LaTeXML author elements
    author_elems = soup.select(".ltx_personname")
    if author_elems:
        for elem in author_elems:
            name = _clean_text(elem.get_text())
            if name and name not in authors:
                authors.append(name)
        return authors

    # Try meta tags
    meta_authors = soup.select('meta[name="citation_author"]')
    for meta in meta_authors:
        content = meta.get("content", "")
        if content:
            authors.append(content)

    return authors


def _extract_abstract(soup: BeautifulSoup) -> str:
    """Extract paper abstract."""
    # Try LaTeXML abstract
    abstract_elem = soup.select_one(".ltx_abstract")
    if abstract_elem:
        # Get text content, skip the "Abstract" heading
        paragraphs = abstract_elem.select("p")
        if paragraphs:
            return " ".join(_clean_text(p.get_text()) for p in paragraphs)
        return _clean_text(abstract_elem.get_text())

    # Try meta description
    meta_desc = soup.select_one('meta[name="description"]')
    if meta_desc:
        return meta_desc.get("content", "")

    return ""


def _extract_date(soup: BeautifulSoup) -> str | None:
    """Extract publication date."""
    # Try meta tag
    meta_date = soup.select_one('meta[name="citation_date"]')
    if meta_date:
        return meta_date.get("content")

    # Try LaTeXML date
    date_elem = soup.select_one(".ltx_date")
    if date_elem:
        return _clean_text(date_elem.get_text())

    return None


def _extract_sections(soup: BeautifulSoup) -> list[Section]:
    """Extract paper sections with their content."""
    sections = []

    # Find all LaTeXML sections
    section_elems = soup.select(".ltx_section, .ltx_subsection, .ltx_subsubsection")

    for i, elem in enumerate(section_elems):
        # Determine section level
        if "ltx_section" in elem.get("class", []):
            level = 1
        elif "ltx_subsection" in elem.get("class", []):
            level = 2
        else:
            level = 3

        # Get section ID
        section_id = elem.get("id", f"section-{i}")

        # Get title
        title_elem = elem.select_one(".ltx_title")
        title = _clean_text(title_elem.get_text()) if title_elem else f"Section {i + 1}"

        # Get content (everything except title)
        content_parts = []
        for child in elem.children:
            if isinstance(child, Tag):
                if "ltx_title" not in child.get("class", []):
                    # Skip nested sections - they'll be processed separately
                    if not any(
                        cls in child.get("class", [])
                        for cls in ["ltx_section", "ltx_subsection", "ltx_subsubsection"]
                    ):
                        content_parts.append(str(child))

        content = "\n".join(content_parts)

        sections.append(
            Section(
                id=section_id,
                title=title,
                level=level,
                content=content,
            )
        )

    # If no LaTeXML sections found, try to get main content
    if not sections:
        main_content = soup.select_one(".ltx_page_main, article, main, .content")
        if main_content:
            sections.append(
                Section(
                    id="main-content",
                    title="Content",
                    level=1,
                    content=str(main_content),
                )
            )

    return sections


def _extract_figures(soup: BeautifulSoup, base_url: str | None = None) -> list[Figure]:
    """Extract figures from the paper."""
    figures = []

    figure_elems = soup.select(".ltx_figure, figure")

    for i, elem in enumerate(figure_elems):
        fig_id = elem.get("id", f"figure-{i}")

        # Get caption
        caption_elem = elem.select_one(".ltx_caption, figcaption")
        caption = _clean_text(caption_elem.get_text()) if caption_elem else ""

        # Get image URL
        img = elem.select_one("img")
        image_url = None
        if img:
            src = img.get("src", "")
            if src:
                if base_url:
                    image_url = urljoin(base_url, src)
                else:
                    image_url = src

        figures.append(
            Figure(
                id=fig_id,
                caption=caption,
                image_url=image_url,
            )
        )

    return figures


def _extract_references(soup: BeautifulSoup) -> str | None:
    """Extract references section HTML."""
    refs = soup.select_one(".ltx_bibliography, #references, .references")
    if refs:
        return str(refs)
    return None


def parse_paper(html: str, paper_id: str, base_url: str | None = None) -> Paper:
    """Parse arXiv HTML into a Paper object.

    Args:
        html: HTML content of the paper
        paper_id: arXiv paper ID
        base_url: Base URL for resolving relative image URLs

    Returns:
        Parsed Paper object
    """
    soup = BeautifulSoup(html, "lxml")

    # Set base URL from paper ID if not provided
    if not base_url:
        base_url = f"https://arxiv.org/html/{paper_id}/"

    return Paper(
        id=paper_id,
        title=_extract_title(soup),
        authors=_extract_authors(soup),
        abstract=_extract_abstract(soup),
        date=_extract_date(soup),
        sections=_extract_sections(soup),
        figures=_extract_figures(soup, base_url),
        references_html=_extract_references(soup),
        base_url=base_url,
    )
