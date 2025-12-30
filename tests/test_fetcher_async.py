"""Tests for async fetcher functions."""

import pytest
import respx
from httpx import Response

from arxiv_epub.fetcher import (
    ArxivHTMLNotAvailable,
    fetch_paper_async,
    fetch_papers_batch,
)


class TestAsyncFetcher:
    """Tests for async fetcher functions."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_paper_async_success(self) -> None:
        """Test async fetch succeeds."""
        paper_id = "2402.08954"
        html_content = "<html><body>Test content</body></html>"
        respx.get(f"https://arxiv.org/html/{paper_id}").mock(
            return_value=Response(200, text=html_content)
        )

        result_id, result_html = await fetch_paper_async(paper_id)
        assert result_id == paper_id
        assert "Test content" in result_html

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_paper_async_404(self) -> None:
        """Test async fetch raises on 404."""
        paper_id = "0000.00000"
        respx.get(f"https://arxiv.org/html/{paper_id}").mock(
            return_value=Response(404)
        )

        with pytest.raises(ArxivHTMLNotAvailable):
            await fetch_paper_async(paper_id)

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_papers_batch_mixed(self) -> None:
        """Test batch fetch with mixed success/failure."""
        papers = ["2402.08954", "0000.00000", "1234.56789"]

        respx.get("https://arxiv.org/html/2402.08954").mock(
            return_value=Response(200, text="<html>Paper 1</html>")
        )
        respx.get("https://arxiv.org/html/0000.00000").mock(
            return_value=Response(404)
        )
        respx.get("https://arxiv.org/html/1234.56789").mock(
            return_value=Response(200, text="<html>Paper 3</html>")
        )

        results = await fetch_papers_batch(papers)

        assert len(results) == 3

        # First should succeed
        assert results[0][0] == "2402.08954"
        assert isinstance(results[0][1], str)

        # Second should be an exception
        assert results[1][0] == "0000.00000"
        assert isinstance(results[1][1], Exception)

        # Third should succeed
        assert results[2][0] == "1234.56789"
        assert isinstance(results[2][1], str)

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_papers_batch_all_success(self) -> None:
        """Test batch fetch with all successes."""
        papers = ["1111.11111", "2222.22222"]

        for paper_id in papers:
            respx.get(f"https://arxiv.org/html/{paper_id}").mock(
                return_value=Response(200, text=f"<html>{paper_id}</html>")
            )

        results = await fetch_papers_batch(papers)

        assert len(results) == 2
        for paper_id, result in results:
            assert isinstance(result, str)
            assert paper_id in result

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_papers_batch_all_failure(self) -> None:
        """Test batch fetch with all failures."""
        papers = ["0000.00001", "0000.00002"]

        for paper_id in papers:
            respx.get(f"https://arxiv.org/html/{paper_id}").mock(
                return_value=Response(404)
            )

        results = await fetch_papers_batch(papers)

        assert len(results) == 2
        for _, result in results:
            assert isinstance(result, Exception)
