"""Command-line interface for arxiv-epub."""

import asyncio
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from arxiv_epub import __version__
from arxiv_epub.converter import convert_to_epub
from arxiv_epub.fetcher import (
    ArxivFetchError,
    ArxivHTMLNotAvailable,
    fetch_paper,
    fetch_papers_batch,
    normalize_arxiv_id,
)
from arxiv_epub.parser import parse_paper

app = typer.Typer(
    name="arxiv-epub",
    help="Convert arXiv HTML papers to EPUB for Kindle.",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"arxiv-epub version {__version__}")
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
            help="Output directory for EPUB files",
        ),
    ] = None,
    style: Annotated[
        str,
        typer.Option(
            "--style",
            "-s",
            help="Style preset: default, compact, or large-text",
        ),
    ] = "default",
    no_images: Annotated[
        bool,
        typer.Option(
            "--no-images",
            help="Skip downloading images (faster, smaller files)",
        ),
    ] = False,
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
    """Convert arXiv papers to EPUB format.

    Examples:

        arxiv-epub 2402.08954

        arxiv-epub 2402.08954 2401.12345 -o ~/kindle/

        arxiv-epub https://arxiv.org/abs/2402.08954 --style large-text
    """
    if style not in ("default", "compact", "large-text"):
        console.print(f"[red]Error:[/red] Invalid style '{style}'. Use default, compact, or large-text.")
        raise typer.Exit(1)

    # Create output directory if specified
    if output:
        output.mkdir(parents=True, exist_ok=True)

    # Process single paper or batch
    if len(papers) == 1:
        _convert_single(papers[0], output, style, not no_images)
    else:
        _convert_batch(papers, output, style, not no_images)


def _convert_single(
    paper_input: str,
    output_dir: Path | None,
    style: str,
    download_images: bool,
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

        progress.update(task, description=f"Converting {paper_id} to EPUB...")

        # Determine output path
        if output_dir:
            output_path = output_dir / f"{paper_id.replace('/', '_')}.epub"
        else:
            output_path = None

        # Convert to EPUB
        epub_path = convert_to_epub(
            paper,
            output_path=output_path,
            style_preset=style,
            download_images=download_images,
        )

        progress.stop()

    console.print(f"[green]Success![/green] Created: {epub_path}")
    console.print(f"  Title: {paper.title}")
    console.print(f"  Authors: {', '.join(paper.authors)}")


def _convert_batch(
    paper_inputs: list[str],
    output_dir: Path | None,
    style: str,
    download_images: bool,
) -> None:
    """Convert multiple papers."""
    console.print(f"Converting {len(paper_inputs)} papers...")

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
            if output_dir:
                output_path = output_dir / f"{paper_id.replace('/', '_')}.epub"
            else:
                output_path = None

            # Convert to EPUB
            epub_path = convert_to_epub(
                paper,
                output_path=output_path,
                style_preset=style,
                download_images=download_images,
            )

            console.print(f"[green]Created:[/green] {epub_path}")
            success_count += 1

        except Exception as e:
            console.print(f"[red]Error[/red] converting {paper_id}: {e}")
            error_count += 1

    # Summary
    console.print()
    console.print(f"[bold]Summary:[/bold] {success_count} succeeded, {error_count} failed")


if __name__ == "__main__":
    app()
