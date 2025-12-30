"""arxiv-to-ereader: Convert arXiv HTML papers to EPUB and Kindle formats."""

__version__ = "0.1.0"

from arxiv_to_ereader.converter import OutputFormat, convert_to_epub
from arxiv_to_ereader.fetcher import fetch_paper, normalize_arxiv_id
from arxiv_to_ereader.parser import Paper, parse_paper

__all__ = [
    "__version__",
    "convert_to_epub",
    "fetch_paper",
    "normalize_arxiv_id",
    "OutputFormat",
    "Paper",
    "parse_paper",
]
