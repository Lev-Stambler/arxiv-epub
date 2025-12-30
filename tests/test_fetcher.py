"""Tests for the fetcher module."""

import pytest

from arxiv_to_ereader.fetcher import (
    get_abs_url,
    get_html_url,
    normalize_arxiv_id,
)


class TestNormalizeArxivId:
    """Tests for normalize_arxiv_id function."""

    def test_bare_id_new_format(self) -> None:
        """Test normalizing a bare new-format ID."""
        assert normalize_arxiv_id("2402.08954") == "2402.08954"

    def test_bare_id_with_version(self) -> None:
        """Test normalizing an ID with version."""
        assert normalize_arxiv_id("2402.08954v1") == "2402.08954v1"
        assert normalize_arxiv_id("2402.08954v2") == "2402.08954v2"

    def test_bare_id_old_format(self) -> None:
        """Test normalizing old-format IDs (pre-2007)."""
        assert normalize_arxiv_id("hep-th/9901001") == "hep-th/9901001"
        assert normalize_arxiv_id("cond-mat/0001234") == "cond-mat/0001234"

    def test_abs_url(self) -> None:
        """Test normalizing from abstract URL."""
        assert normalize_arxiv_id("https://arxiv.org/abs/2402.08954") == "2402.08954"
        assert normalize_arxiv_id("http://arxiv.org/abs/2402.08954") == "2402.08954"

    def test_html_url(self) -> None:
        """Test normalizing from HTML URL."""
        assert normalize_arxiv_id("https://arxiv.org/html/2402.08954") == "2402.08954"

    def test_pdf_url(self) -> None:
        """Test normalizing from PDF URL."""
        assert normalize_arxiv_id("https://arxiv.org/pdf/2402.08954") == "2402.08954"

    def test_url_with_version(self) -> None:
        """Test normalizing URL with version."""
        assert normalize_arxiv_id("https://arxiv.org/abs/2402.08954v1") == "2402.08954v1"

    def test_with_arxiv_prefix(self) -> None:
        """Test normalizing with arxiv: prefix."""
        assert normalize_arxiv_id("arxiv:2402.08954") == "2402.08954"

    def test_with_whitespace(self) -> None:
        """Test normalizing with surrounding whitespace."""
        assert normalize_arxiv_id("  2402.08954  ") == "2402.08954"

    def test_invalid_input(self) -> None:
        """Test that invalid input raises ValueError."""
        with pytest.raises(ValueError, match="Could not extract arXiv ID"):
            normalize_arxiv_id("not-a-valid-id")

        with pytest.raises(ValueError, match="Could not extract arXiv ID"):
            normalize_arxiv_id("https://example.com/paper")

    def test_five_digit_id(self) -> None:
        """Test normalizing 5-digit paper numbers (newer format)."""
        assert normalize_arxiv_id("2401.12345") == "2401.12345"


class TestGetUrls:
    """Tests for URL generation functions."""

    def test_get_html_url(self) -> None:
        """Test HTML URL generation."""
        assert get_html_url("2402.08954") == "https://arxiv.org/html/2402.08954"
        assert get_html_url("hep-th/9901001") == "https://arxiv.org/html/hep-th/9901001"

    def test_get_abs_url(self) -> None:
        """Test abstract URL generation."""
        assert get_abs_url("2402.08954") == "https://arxiv.org/abs/2402.08954"
        assert get_abs_url("hep-th/9901001") == "https://arxiv.org/abs/hep-th/9901001"
