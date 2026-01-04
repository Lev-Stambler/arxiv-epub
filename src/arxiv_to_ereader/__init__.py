"""arxiv-ereader: Convert arXiv HTML papers to PDF optimized for e-readers."""

__version__ = "0.2.0"

from arxiv_to_ereader.converter import convert_to_pdf
from arxiv_to_ereader.fetcher import fetch_paper, normalize_arxiv_id
from arxiv_to_ereader.parser import Paper, parse_paper
from arxiv_to_ereader.screen_presets import SCREEN_PRESETS, ScreenPreset, get_preset

__all__ = [
    "__version__",
    "convert_to_pdf",
    "fetch_paper",
    "normalize_arxiv_id",
    "Paper",
    "parse_paper",
    "SCREEN_PRESETS",
    "ScreenPreset",
    "get_preset",
]
