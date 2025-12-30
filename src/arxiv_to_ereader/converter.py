"""Convert parsed papers to EPUB and Kindle formats."""

import shutil
import subprocess
import tempfile
from enum import Enum
from pathlib import Path

import httpx
from ebooklib import epub

from arxiv_to_ereader.parser import Paper
from arxiv_to_ereader.styles import get_cover_css, get_stylesheet


class OutputFormat(str, Enum):
    """Supported output formats."""

    EPUB = "epub"
    MOBI = "mobi"
    AZW3 = "azw3"


def _check_calibre_available() -> bool:
    """Check if Calibre's ebook-convert is available."""
    return shutil.which("ebook-convert") is not None


def _convert_epub_to_kindle(
    epub_path: Path,
    output_path: Path,
    output_format: OutputFormat,
) -> Path:
    """Convert EPUB to Kindle format using Calibre's ebook-convert.

    Args:
        epub_path: Path to the source EPUB file
        output_path: Path for the output file
        output_format: Target format (mobi or azw3)

    Returns:
        Path to the converted file

    Raises:
        RuntimeError: If Calibre is not installed or conversion fails
    """
    if not _check_calibre_available():
        raise RuntimeError(
            "Calibre's ebook-convert not found. Install Calibre to convert to Kindle formats.\n"
            "  - macOS: brew install calibre\n"
            "  - Ubuntu/Debian: sudo apt install calibre\n"
            "  - Or download from: https://calibre-ebook.com/download"
        )

    try:
        result = subprocess.run(
            ["ebook-convert", str(epub_path), str(output_path)],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Calibre conversion failed: {e.stderr}") from e

    return output_path


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


def _create_footnotes_chapter(
    footnotes: list,
    stylesheet: epub.EpubItem,
) -> epub.EpubHtml:
    """Create a footnotes chapter."""
    from arxiv_to_ereader.parser import Footnote

    footnotes_html = ""
    for fn in footnotes:
        if isinstance(fn, Footnote):
            back_link = f'<a href="#fnref-{fn.index}" class="footnote-back">↩</a>'
            footnotes_html += f'<li id="{fn.id}">{fn.content} {back_link}</li>\n'

    content = f"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">
<head>
    <title>Notes</title>
    <link rel="stylesheet" href="style.css" type="text/css"/>
</head>
<body>
    <section class="footnotes-section" epub:type="footnotes">
        <h1>Notes</h1>
        <ol>
            {footnotes_html}
        </ol>
    </section>
</body>
</html>"""

    chapter = epub.EpubHtml(title="Notes", file_name="footnotes.xhtml", lang="en")
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
    output_format: OutputFormat | str = OutputFormat.EPUB,
) -> Path:
    """Convert a parsed paper to EPUB or Kindle format.

    Args:
        paper: Parsed Paper object
        output_path: Output file path (defaults to {paper_id}.{format} in current directory)
        style_preset: Style preset name ("default", "compact", "large-text")
        download_images: Whether to download and embed images
        output_format: Output format ("epub", "mobi", or "azw3")

    Returns:
        Path to the created ebook file
    """
    # Normalize format
    if isinstance(output_format, str):
        output_format = OutputFormat(output_format.lower())
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

    # Download and add ALL images from the paper
    # Maps original src (relative or absolute) -> epub path
    image_url_to_epub_path: dict[str, str] = {}

    if download_images and paper.all_images:
        for i, (original_src, absolute_url) in enumerate(paper.all_images.items()):
            result = _download_image(absolute_url)
            if result:
                img_data, media_type = result
                # Create a safe filename
                ext = media_type.split("/")[-1]
                if ext == "jpeg":
                    ext = "jpg"
                elif ext == "svg+xml":
                    ext = "svg"

                # Use index to ensure unique filenames
                img_filename = f"images/img_{i:04d}.{ext}"

                img_item = epub.EpubItem(
                    uid=f"image_{i}",
                    file_name=img_filename,
                    media_type=media_type,
                    content=img_data,
                )
                book.add_item(img_item)

                # Map both original src and absolute URL to the epub path
                image_url_to_epub_path[original_src] = img_filename
                image_url_to_epub_path[absolute_url] = img_filename

    # Sections
    for i, section in enumerate(paper.sections):
        # Update image URLs in section content
        content = section.content
        for old_url, new_path in image_url_to_epub_path.items():
            # Replace in both quote styles
            content = content.replace(f'src="{old_url}"', f'src="{new_path}"')
            content = content.replace(f"src='{old_url}'", f"src='{new_path}'")

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

    # Footnotes (if any were extracted)
    if paper.footnotes:
        footnotes_chapter = _create_footnotes_chapter(paper.footnotes, stylesheet)
        book.add_item(footnotes_chapter)
        chapters.append(footnotes_chapter)

    # Create table of contents
    book.toc = [(chapter, []) for chapter in chapters]

    # Add navigation files
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # Set spine (reading order)
    book.spine = ["nav"] + chapters

    # Determine output path
    file_ext = output_format.value
    if output_path is None:
        output_path = Path(f"{paper.id.replace('/', '_')}.{file_ext}")
    else:
        output_path = Path(output_path)
        # Update extension if format specified but path has wrong extension
        if output_path.suffix.lower() != f".{file_ext}":
            output_path = output_path.with_suffix(f".{file_ext}")

    # Create parent directories if needed
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # For Kindle formats, we need to first create an EPUB then convert
    if output_format in (OutputFormat.MOBI, OutputFormat.AZW3):
        # Create temporary EPUB
        with tempfile.NamedTemporaryFile(suffix=".epub", delete=False) as tmp:
            tmp_epub_path = Path(tmp.name)

        try:
            epub.write_epub(str(tmp_epub_path), book, {})
            _convert_epub_to_kindle(tmp_epub_path, output_path, output_format)
        finally:
            # Clean up temp file
            tmp_epub_path.unlink(missing_ok=True)
    else:
        # Write EPUB directly
        epub.write_epub(str(output_path), book, {})

    return output_path
