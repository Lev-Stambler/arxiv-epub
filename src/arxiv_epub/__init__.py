"""arxiv-epub: Convert arXiv HTML papers to EPUB for Kindle."""

__version__ = "0.1.0"

from arxiv_epub.converter import convert_to_epub
from arxiv_epub.fetcher import fetch_paper, normalize_arxiv_id
from arxiv_epub.parser import Paper, parse_paper

__all__ = [
    "__version__",
    "convert_to_epub",
    "fetch_paper",
    "normalize_arxiv_id",
    "Paper",
    "parse_paper",
]
