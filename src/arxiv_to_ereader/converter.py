"""Convert parsed papers to PDF format optimized for e-readers using Playwright."""

import base64
import tempfile
from pathlib import Path

import httpx
from playwright.sync_api import sync_playwright

from arxiv_to_ereader.parser import Paper
from arxiv_to_ereader.screen_presets import ScreenPreset, custom_preset, get_preset
from arxiv_to_ereader.styles import get_pdf_stylesheet


def _download_image(url: str, timeout: float = 30.0) -> tuple[bytes, str] | None:
    """Download an image and return its content and media type."""
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


def _build_html_document(
    paper: Paper,
    image_map: dict[str, str],
    preset: ScreenPreset,
) -> str:
    """Build a complete HTML document from the Paper object.

    Args:
        paper: Parsed Paper object
        image_map: Map of original image URLs to base64 data URIs
        preset: Screen preset for styling

    Returns:
        Complete HTML document as string
    """
    # Build sections HTML
    sections_html = ""
    for section in paper.sections:
        content = section.content

        # Replace image URLs with base64 data URIs
        for old_url, new_src in image_map.items():
            content = content.replace(f'src="{old_url}"', f'src="{new_src}"')
            content = content.replace(f"src='{old_url}'", f"src='{new_src}'")

        level = min(section.level + 1, 6)
        sections_html += f"""
        <section id="{section.id}">
            <h{level}>{section.title}</h{level}>
            {content}
        </section>
        """

    # Build complete document
    authors_html = ", ".join(paper.authors) if paper.authors else "Unknown"
    date_html = f'<p class="date">{paper.date}</p>' if paper.date else ""

    abstract_html = ""
    if paper.abstract:
        abstract_html = f"""
        <div class="abstract">
            <p class="abstract-title">Abstract</p>
            <p>{paper.abstract}</p>
        </div>
        """

    references_html = ""
    if paper.references_html:
        refs_content = paper.references_html
        for old_url, new_src in image_map.items():
            refs_content = refs_content.replace(f'src="{old_url}"', f'src="{new_src}"')
        references_html = f"""
        <section class="references">
            <h2>References</h2>
            {refs_content}
        </section>
        """

    footnotes_html = ""
    if paper.footnotes:
        footnotes_items = []
        for fn in paper.footnotes:
            footnotes_items.append(
                f'<li id="{fn.id}">{fn.content} <a href="#fnref-{fn.index}" class="footnote-back">^</a></li>'
            )
        footnotes_list = "\n".join(footnotes_items)
        footnotes_html = f"""
        <section class="footnotes-section">
            <h2>Notes</h2>
            <ol>{footnotes_list}</ol>
        </section>
        """

    # Get CSS
    css_content = get_pdf_stylesheet(preset)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8"/>
    <title>{paper.title}</title>
    <style>
{css_content}
    </style>
</head>
<body>
    <div class="cover">
        <h1>{paper.title}</h1>
        <p class="authors">{authors_html}</p>
        {date_html}
        <p class="paper-id">arXiv:{paper.id}</p>
    </div>

    {abstract_html}

    {sections_html}

    {references_html}

    {footnotes_html}
</body>
</html>
"""
    return html


def convert_to_pdf(
    paper: Paper,
    output_path: Path | str | None = None,
    screen_preset: str = "kindle-paperwhite",
    custom_width_mm: float | None = None,
    custom_height_mm: float | None = None,
    download_images: bool = True,
) -> Path:
    """Convert a parsed paper to PDF format optimized for e-readers.

    Uses Playwright (headless Chromium) for rendering, which provides native
    MathML support for math equations - the same rendering as viewing arXiv
    HTML in a browser.

    Args:
        paper: Parsed Paper object
        output_path: Output file path (defaults to {paper_id}.pdf)
        screen_preset: Screen size preset name
        custom_width_mm: Custom page width in mm (overrides preset)
        custom_height_mm: Custom page height in mm (overrides preset)
        download_images: Whether to download and embed images

    Returns:
        Path to the created PDF file
    """
    # Get screen preset
    if custom_width_mm and custom_height_mm:
        preset = custom_preset(custom_width_mm, custom_height_mm)
    else:
        preset = get_preset(screen_preset)

    # Download images and create base64 data URI map
    image_map: dict[str, str] = {}
    if download_images and paper.all_images:
        for original_src, absolute_url in paper.all_images.items():
            result = _download_image(absolute_url)
            if result:
                img_data, media_type = result
                b64_data = base64.b64encode(img_data).decode("ascii")
                data_uri = f"data:{media_type};base64,{b64_data}"
                image_map[original_src] = data_uri
                image_map[absolute_url] = data_uri

    # Build HTML document
    html_content = _build_html_document(paper, image_map, preset)

    # Determine output path
    if output_path is None:
        output_path = Path(f"{paper.id.replace('/', '_')}.pdf")
    else:
        output_path = Path(output_path)
        if output_path.suffix.lower() != ".pdf":
            output_path = output_path.with_suffix(".pdf")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert mm to inches for Playwright (1 inch = 25.4 mm)
    width_inches = preset.width_mm / 25.4
    height_inches = preset.height_mm / 25.4

    # Write HTML to temp file and render with Playwright
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        f.write(html_content)
        temp_html_path = f.name

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page()

            # Load the HTML file
            page.goto(f"file://{temp_html_path}")

            # Wait for any async content to load
            page.wait_for_load_state("networkidle")

            # Generate PDF with custom page size
            page.pdf(
                path=str(output_path),
                width=f"{width_inches}in",
                height=f"{height_inches}in",
                margin={
                    "top": "8mm",
                    "bottom": "10mm",
                    "left": "6mm",
                    "right": "6mm",
                },
                print_background=True,
            )

            browser.close()
    finally:
        # Clean up temp file
        Path(temp_html_path).unlink(missing_ok=True)

    return output_path
