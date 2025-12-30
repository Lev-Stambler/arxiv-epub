"""Playwright tests for the Streamlit web interface."""

import subprocess
import time
from typing import Generator

import pytest
from playwright.sync_api import Page, expect

# Sample HTML for mocking
SAMPLE_HTML = """
<!DOCTYPE html>
<html>
<head><title>Test Paper</title></head>
<body>
<article class="ltx_document">
    <h1 class="ltx_title ltx_title_document">Test Paper Title</h1>
    <div class="ltx_authors">
        <span class="ltx_personname">Test Author</span>
    </div>
    <div class="ltx_abstract"><p>Test abstract content.</p></div>
    <section class="ltx_section" id="S1">
        <h2 class="ltx_title ltx_title_section">1 Introduction</h2>
        <div class="ltx_para"><p>Introduction content.</p></div>
    </section>
</article>
</body>
</html>
"""


@pytest.fixture(scope="module")
def streamlit_server() -> Generator[str, None, None]:
    """Start Streamlit server for testing."""
    # Start the Streamlit app
    process = subprocess.Popen(
        [
            "uv",
            "run",
            "streamlit",
            "run",
            "src/arxiv_to_ereader/web.py",
            "--server.port",
            "8501",
            "--server.headless",
            "true",
            "--browser.gatherUsageStats",
            "false",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Wait for server to start
    time.sleep(5)

    yield "http://localhost:8501"

    # Cleanup
    process.terminate()
    process.wait(timeout=5)


class TestStreamlitUI:
    """Tests for Streamlit UI elements."""

    def test_page_title(self, page: Page, streamlit_server: str) -> None:
        """Test that page has correct title."""
        page.goto(streamlit_server)
        expect(page).to_have_title("arXiv to E-Reader")

    def test_main_header_visible(self, page: Page, streamlit_server: str) -> None:
        """Test that main header is visible."""
        page.goto(streamlit_server)
        header = page.locator("h1").first
        expect(header).to_contain_text("arXiv to E-Reader")

    def test_input_method_radio_buttons(self, page: Page, streamlit_server: str) -> None:
        """Test that input method radio buttons are present."""
        page.goto(streamlit_server)
        # Wait for Streamlit to fully load
        page.wait_for_load_state("networkidle")

        # Check for radio button options
        single_paper = page.get_by_text("Single paper")
        multiple_papers = page.get_by_text("Multiple papers")

        expect(single_paper).to_be_visible()
        expect(multiple_papers).to_be_visible()

    def test_paper_input_field(self, page: Page, streamlit_server: str) -> None:
        """Test that paper input field is present."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Check for input field placeholder
        input_field = page.get_by_placeholder("e.g., 2402.08954")
        expect(input_field).to_be_visible()

    def test_style_preset_dropdown(self, page: Page, streamlit_server: str) -> None:
        """Test that style preset dropdown exists."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Look for the selectbox label
        style_label = page.get_by_text("Style preset")
        expect(style_label).to_be_visible()

    def test_include_images_checkbox(self, page: Page, streamlit_server: str) -> None:
        """Test that include images checkbox exists."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        checkbox_label = page.get_by_text("Include images")
        expect(checkbox_label).to_be_visible()

    def test_convert_button_present(self, page: Page, streamlit_server: str) -> None:
        """Test that convert button is present."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        convert_button = page.get_by_role("button", name="Convert to EPUB")
        expect(convert_button).to_be_visible()

    def test_convert_button_disabled_without_input(
        self, page: Page, streamlit_server: str
    ) -> None:
        """Test that convert button is disabled without input."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        convert_button = page.get_by_role("button", name="Convert to EPUB")
        expect(convert_button).to_be_disabled()

    def test_footer_links(self, page: Page, streamlit_server: str) -> None:
        """Test that footer links are present."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        github_link = page.get_by_role("link", name="GitHub")
        arxiv_link = page.get_by_role("link", name="arXiv")

        expect(github_link).to_be_visible()
        expect(arxiv_link).to_be_visible()


class TestStreamlitInteraction:
    """Tests for Streamlit UI interactions."""

    def test_switch_to_multiple_papers(self, page: Page, streamlit_server: str) -> None:
        """Test switching to multiple papers input mode."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Click on "Multiple papers" radio option
        multiple_option = page.get_by_text("Multiple papers")
        multiple_option.click()

        # Wait for the textarea to appear
        page.wait_for_timeout(500)

        # Verify textarea appears (multiple papers mode uses text_area)
        textarea = page.get_by_placeholder("2402.08954")
        expect(textarea).to_be_visible()

    def test_enter_paper_id_enables_button(
        self, page: Page, streamlit_server: str
    ) -> None:
        """Test that entering a paper ID enables the convert button."""
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Enter a paper ID
        input_field = page.get_by_placeholder("e.g., 2402.08954")
        input_field.fill("2402.08954")
        input_field.press("Enter")

        # Wait for Streamlit to process the input
        page.wait_for_timeout(1000)

        # Button should now be enabled
        convert_button = page.get_by_role("button", name="Convert to EPUB")
        expect(convert_button).to_be_enabled()


class TestStreamlitResponsive:
    """Tests for responsive design of the Streamlit interface."""

    def test_mobile_viewport(self, page: Page, streamlit_server: str) -> None:
        """Test that UI works on mobile viewport."""
        page.set_viewport_size({"width": 375, "height": 667})
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        # Main elements should still be visible
        header = page.locator("h1").first
        expect(header).to_be_visible()

        convert_button = page.get_by_role("button", name="Convert to EPUB")
        expect(convert_button).to_be_visible()

    def test_tablet_viewport(self, page: Page, streamlit_server: str) -> None:
        """Test that UI works on tablet viewport."""
        page.set_viewport_size({"width": 768, "height": 1024})
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        header = page.locator("h1").first
        expect(header).to_be_visible()

    def test_desktop_viewport(self, page: Page, streamlit_server: str) -> None:
        """Test that UI works on desktop viewport."""
        page.set_viewport_size({"width": 1920, "height": 1080})
        page.goto(streamlit_server)
        page.wait_for_load_state("networkidle")

        header = page.locator("h1").first
        expect(header).to_be_visible()
