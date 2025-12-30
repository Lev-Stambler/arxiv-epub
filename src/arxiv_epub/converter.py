"""Convert parsed papers to EPUB format."""

from pathlib import Path

import httpx
from ebooklib import epub

from arxiv_epub.parser import Paper
from arxiv_epub.styles import get_cover_css, get_stylesheet


def _create_cover_chapter(paper: Paper) -> epub.EpubHtml:
    """Create a cover/title page chapter."""
    authors_html = ", ".join(paper.authors) if paper.authors else "Unknown Authors"
    date_html = f"<p class='date'>{paper.date}</p>" if paper.date else ""

    content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{paper.title}</title>
    <style>{get_cover_css()}</style>
</head>
<body>
    <h1>{paper.title}</h1>
    <p class="authors">{authors_html}</p>
    {date_html}
    <p class="paper-id">arXiv:{paper.id}</p>
</body>
</html>"""

    chapter = epub.EpubHtml(title="Cover", file_name="cover.xhtml", lang="en")
    chapter.content = content.encode("utf-8")
    return chapter


def _create_abstract_chapter(paper: Paper, stylesheet: epub.EpubItem) -> epub.EpubHtml:
    """Create an abstract chapter."""
    content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>Abstract</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <div class="abstract">
        <p class="abstract-title">Abstract</p>
        <p>{paper.abstract}</p>
    </div>
</body>
</html>"""

    chapter = epub.EpubHtml(title="Abstract", file_name="abstract.xhtml", lang="en")
    chapter.content = content.encode("utf-8")
    chapter.add_item(stylesheet)
    return chapter


def _create_section_chapter(
    section_idx: int,
    title: str,
    content: str,
    stylesheet: epub.EpubItem,
) -> epub.EpubHtml:
    """Create a chapter from a paper section."""
    html_content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>{title}</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <h1>{title}</h1>
    {content}
</body>
</html>"""

    chapter = epub.EpubHtml(
        title=title,
        file_name=f"section_{section_idx:02d}.xhtml",
        lang="en",
    )
    chapter.content = html_content.encode("utf-8")
    chapter.add_item(stylesheet)
    return chapter


def _create_references_chapter(
    references_html: str,
    stylesheet: epub.EpubItem,
) -> epub.EpubHtml:
    """Create a references chapter."""
    content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>References</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <h1>References</h1>
    {references_html}
</body>
</html>"""

    chapter = epub.EpubHtml(title="References", file_name="references.xhtml", lang="en")
    chapter.content = content.encode("utf-8")
    chapter.add_item(stylesheet)
    return chapter


def _download_image(url: str, timeout: float = 30.0) -> tuple[bytes, str] | None:
    """Download an image and return its content and media type.

    Returns:
        Tuple of (image_bytes, media_type) or None if download fails
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()

            content_type = response.headers.get("content-type", "image/png")
            if ";" in content_type:
                content_type = content_type.split(";")[0].strip()

            return response.content, content_type
    except Exception:
        return None


def convert_to_epub(
    paper: Paper,
    output_path: Path | str | None = None,
    style_preset: str = "default",
    download_images: bool = True,
) -> Path:
    """Convert a parsed paper to EPUB format.

    Args:
        paper: Parsed Paper object
        output_path: Output file path (defaults to {paper_id}.epub in current directory)
        style_preset: Style preset name ("default", "compact", "large-text")
        download_images: Whether to download and embed images

    Returns:
        Path to the created EPUB file
    """
    # Create EPUB book
    book = epub.EpubBook()

    # Set metadata
    book.set_identifier(f"arxiv:{paper.id}")
    book.set_title(paper.title)
    book.set_language("en")

    for author in paper.authors:
        book.add_author(author)

    if paper.date:
        book.add_metadata("DC", "date", paper.date)

    book.add_metadata("DC", "source", f"https://arxiv.org/abs/{paper.id}")
    book.add_metadata("DC", "publisher", "arXiv")

    # Create stylesheet
    stylesheet = epub.EpubItem(
        uid="style",
        file_name="style.css",
        media_type="text/css",
        content=get_stylesheet(style_preset),
    )
    book.add_item(stylesheet)

    # Create chapters
    chapters = []

    # Cover page
    cover_chapter = _create_cover_chapter(paper)
    book.add_item(cover_chapter)
    chapters.append(cover_chapter)

    # Abstract
    if paper.abstract:
        abstract_chapter = _create_abstract_chapter(paper, stylesheet)
        book.add_item(abstract_chapter)
        chapters.append(abstract_chapter)

    # Download and add images
    image_items = {}
    if download_images and paper.figures:
        for fig in paper.figures:
            if fig.image_url:
                result = _download_image(fig.image_url)
                if result:
                    img_data, media_type = result
                    # Create a safe filename
                    ext = media_type.split("/")[-1]
                    if ext == "jpeg":
                        ext = "jpg"
                    img_filename = f"images/{fig.id}.{ext}"

                    img_item = epub.EpubItem(
                        uid=fig.id,
                        file_name=img_filename,
                        media_type=media_type,
                        content=img_data,
                    )
                    book.add_item(img_item)
                    image_items[fig.image_url] = img_filename

    # Sections
    for i, section in enumerate(paper.sections):
        # Update image URLs in section content
        content = section.content
        for old_url, new_path in image_items.items():
            content = content.replace(old_url, new_path)

        section_chapter = _create_section_chapter(
            i,
            section.title,
            content,
            stylesheet,
        )
        book.add_item(section_chapter)
        chapters.append(section_chapter)

    # References
    if paper.references_html:
        refs_chapter = _create_references_chapter(paper.references_html, stylesheet)
        book.add_item(refs_chapter)
        chapters.append(refs_chapter)

    # Create table of contents
    book.toc = [(chapter, []) for chapter in chapters]

    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Set spine (reading order)
    book.spine = ["nav"] + chapters

    # Determine output path
    if output_path is None:
        output_path = Path(f"{paper.id.replace('/', '_')}.epub")
    else:
        output_path = Path(output_path)

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write EPUB
    epub.write_epub(str(output_path), book, {})

    return output_path
