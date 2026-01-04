"""Command-line interface for arxiv-ereader."""

import asyncio
import re
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from arxiv_to_ereader import __version__
from arxiv_to_ereader.converter import convert_to_pdf
from arxiv_to_ereader.fetcher import (
    ArxivFetchError,
    ArxivHTMLNotAvailable,
    fetch_paper,
    fetch_papers_batch,
    normalize_arxiv_id,
)
from arxiv_to_ereader.parser import parse_paper
from arxiv_to_ereader.screen_presets import SCREEN_PRESETS


def sanitize_filename(title: str, max_length: int = 80) -> str:
    """Convert a paper title to a safe filename.

    Args:
        title: The paper title
        max_length: Maximum length for the filename (default 80)

    Returns:
        A sanitized filename-safe string (Linux/macOS/Windows compatible)
    """
    filename = title.replace(":", "-")
    filename = filename.replace("/", "-").replace("\\", "-")
    filename = re.sub(r'[<>"|?*\x00-\x1f]', "", filename)
    filename = re.sub(r"[\s]+", "_", filename)
    filename = re.sub(r"[-]+", "-", filename)
    filename = re.sub(r"[_]+", "_", filename)
    filename = re.sub(r"[-_]{2,}", "_", filename)
    filename = filename.strip("_-")
    if len(filename) > max_length:
        filename = filename[:max_length].rsplit("_", 1)[0].strip("_-")
    return filename or "paper"


app = typer.Typer(
    name="arxiv-ereader",
    help="Convert arXiv HTML papers to PDF optimized for e-readers.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"arxiv-ereader version {__version__}")
        raise typer.Exit()


def list_screens_callback(value: bool) -> None:
    """List available screen presets and exit."""
    if value:
        console.print("[bold]Available screen presets:[/bold]")
        for name, preset in SCREEN_PRESETS.items():
            console.print(f"  [cyan]{name}[/cyan]: {preset.description} ({preset.width_mm}x{preset.height_mm}mm)")
        raise typer.Exit()


@app.command()
def convert(
    papers: Annotated[
        list[str],
        typer.Argument(
            help="arXiv paper IDs or URLs (e.g., 2402.08954 or https://arxiv.org/abs/2402.08954)"
        ),
    ],
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            "-o",
            help="Output directory for PDF files",
        ),
    ] = None,
    screen: Annotated[
        str,
        typer.Option(
            "--screen",
            "-s",
            help="E-reader screen preset (use --list-screens to see options)",
        ),
    ] = "kindle-paperwhite",
    width: Annotated[
        float | None,
        typer.Option(
            "--width",
            help="Custom page width in mm (requires --height)",
        ),
    ] = None,
    height: Annotated[
        float | None,
        typer.Option(
            "--height",
            help="Custom page height in mm (requires --width)",
        ),
    ] = None,
    no_images: Annotated[
        bool,
        typer.Option(
            "--no-images",
            help="Skip downloading images (faster, smaller files)",
        ),
    ] = False,
    no_math_images: Annotated[
        bool,
        typer.Option(
            "--no-math-images",
            help="Don't render math equations as images",
        ),
    ] = False,
    math_dpi: Annotated[
        int,
        typer.Option(
            "--math-dpi",
            help="DPI resolution for rendered math images (default 200)",
        ),
    ] = 200,
    use_id: Annotated[
        bool,
        typer.Option(
            "--use-id",
            help="Use arXiv ID for filename instead of paper title",
        ),
    ] = False,
    list_screens: Annotated[
        bool | None,
        typer.Option(
            "--list-screens",
            callback=list_screens_callback,
            is_eager=True,
            help="List available screen presets and exit",
        ),
    ] = None,
    version: Annotated[
        bool | None,
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show version and exit",
        ),
    ] = None,
) -> None:
    """Convert arXiv papers to PDF format optimized for e-readers.

    Examples:

        arxiv-ereader 2402.08954

        arxiv-ereader 2402.08954 2401.12345 -o ~/papers/

        arxiv-ereader https://arxiv.org/abs/2402.08954 --screen kindle-scribe

        arxiv-ereader 2402.08954 --width 150 --height 200
    """
    # Validate screen preset or custom dimensions
    if (width is not None) != (height is not None):
        console.print("[red]Error:[/red] Both --width and --height must be specified together")
        raise typer.Exit(1)

    if width is None and screen not in SCREEN_PRESETS:
        available = ", ".join(SCREEN_PRESETS.keys())
        console.print(f"[red]Error:[/red] Unknown screen preset '{screen}'.")
        console.print(f"Available presets: {available}")
        console.print("Use --list-screens to see details, or specify --width and --height for custom size.")
        raise typer.Exit(1)

    # Create output directory if specified
    if output:
        output.mkdir(parents=True, exist_ok=True)

    # Process single paper or batch
    if len(papers) == 1:
        _convert_single(
            papers[0], output, screen, width, height,
            not no_images, not no_math_images, math_dpi, use_id
        )
    else:
        _convert_batch(
            papers, output, screen, width, height,
            not no_images, not no_math_images, math_dpi, use_id
        )


def _convert_single(
    paper_input: str,
    output_dir: Path | None,
    screen: str,
    width: float | None,
    height: float | None,
    download_images: bool,
    render_math: bool,
    math_dpi: int,
    use_id: bool,
) -> None:
    """Convert a single paper."""
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        # Normalize ID
        try:
            paper_id = normalize_arxiv_id(paper_input)
        except ValueError as e:
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        task = progress.add_task(f"Fetching {paper_id}...", total=None)

        # Fetch HTML
        try:
            _, html = fetch_paper(paper_input)
        except ArxivHTMLNotAvailable as e:
            progress.stop()
            console.print(f"[yellow]Warning:[/yellow] {e}")
            raise typer.Exit(1)
        except ArxivFetchError as e:
            progress.stop()
            console.print(f"[red]Error:[/red] {e}")
            raise typer.Exit(1)

        progress.update(task, description=f"Parsing {paper_id}...")

        # Parse HTML
        paper = parse_paper(html, paper_id)

        progress.update(task, description=f"Converting {paper_id} to PDF...")

        # Determine output path
        if use_id:
            filename = paper_id.replace("/", "_")
        else:
            filename = sanitize_filename(paper.title)

        if output_dir:
            output_path = output_dir / f"{filename}.pdf"
        else:
            output_path = Path(f"{filename}.pdf")

        # Convert to PDF
        pdf_path = convert_to_pdf(
            paper,
            output_path=output_path,
            screen_preset=screen,
            custom_width_mm=width,
            custom_height_mm=height,
            download_images=download_images,
            render_math=render_math,
            math_dpi=math_dpi,
        )

        progress.stop()

    console.print(f"[green]Success![/green] Created: {pdf_path}")
    console.print(f"  Title: {paper.title}")
    console.print(f"  Authors: {', '.join(paper.authors)}")


def _convert_batch(
    paper_inputs: list[str],
    output_dir: Path | None,
    screen: str,
    width: float | None,
    height: float | None,
    download_images: bool,
    render_math: bool,
    math_dpi: int,
    use_id: bool,
) -> None:
    """Convert multiple papers."""
    console.print(f"Converting {len(paper_inputs)} papers to PDF...")

    # Fetch all papers concurrently
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Fetching papers...", total=None)
        results = asyncio.run(fetch_papers_batch(paper_inputs))
        progress.stop()

    # Process results
    success_count = 0
    error_count = 0

    for paper_id, result in results:
        if isinstance(result, Exception):
            console.print(f"[red]Error[/red] {paper_id}: {result}")
            error_count += 1
            continue

        html = result
        console.print(f"[dim]Processing {paper_id}...[/dim]")

        try:
            # Parse HTML
            paper = parse_paper(html, paper_id)

            # Determine output path
            if use_id:
                filename = paper_id.replace("/", "_")
            else:
                filename = sanitize_filename(paper.title)

            if output_dir:
                output_path = output_dir / f"{filename}.pdf"
            else:
                output_path = Path(f"{filename}.pdf")

            # Convert to PDF
            pdf_path = convert_to_pdf(
                paper,
                output_path=output_path,
                screen_preset=screen,
                custom_width_mm=width,
                custom_height_mm=height,
                download_images=download_images,
                render_math=render_math,
                math_dpi=math_dpi,
            )

            console.print(f"[green]Created:[/green] {pdf_path}")
            success_count += 1

        except Exception as e:
            console.print(f"[red]Error[/red] converting {paper_id}: {e}")
            error_count += 1

    # Summary
    console.print()
    console.print(f"[bold]Summary:[/bold] {success_count} succeeded, {error_count} failed")


if __name__ == "__main__":
    app()
