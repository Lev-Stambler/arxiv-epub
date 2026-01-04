"""Streamlit web interface for arxiv-ereader."""

import tempfile
from pathlib import Path

import streamlit as st

from arxiv_to_ereader.converter import convert_to_pdf
from arxiv_to_ereader.fetcher import (
    ArxivFetchError,
    ArxivHTMLNotAvailable,
    fetch_paper,
    normalize_arxiv_id,
)
from arxiv_to_ereader.parser import parse_paper
from arxiv_to_ereader.screen_presets import SCREEN_PRESETS

st.set_page_config(
    page_title="arXiv to E-Reader",
    page_icon="📚",
    layout="centered",
)

st.title("📚 arXiv to E-Reader Converter")
st.markdown(
    "Convert arXiv papers to PDF format optimized for your e-reader."
)

# Input section
st.subheader("Paper Input")

input_method = st.radio(
    "Input method:",
    ["Single paper", "Multiple papers"],
    horizontal=True,
)

if input_method == "Single paper":
    paper_input = st.text_input(
        "arXiv ID or URL",
        placeholder="e.g., 2402.08954 or https://arxiv.org/abs/2402.08954",
        help="Enter an arXiv paper ID or URL",
    )
    paper_inputs = [paper_input] if paper_input else []
else:
    paper_input = st.text_area(
        "arXiv IDs or URLs (one per line)",
        placeholder="2402.08954\n2401.12345\nhttps://arxiv.org/abs/2312.00001",
        help="Enter multiple arXiv paper IDs or URLs, one per line",
    )
    paper_inputs = [p.strip() for p in paper_input.strip().split("\n") if p.strip()]

# Options
st.subheader("Options")

col1, col2 = st.columns(2)

with col1:
    preset_options = {name: f"{preset.description}" for name, preset in SCREEN_PRESETS.items()}
    screen_preset = st.selectbox(
        "Screen preset",
        options=list(preset_options.keys()),
        format_func=lambda x: f"{x} - {preset_options[x]}",
        help="Choose a screen size preset for your e-reader",
    )

with col2:
    download_images = st.checkbox(
        "Include images",
        value=True,
        help="Download and embed images (unchecked = faster, smaller files)",
    )

# Convert button
if st.button("Convert to PDF", type="primary", disabled=not paper_inputs):
    results = []

    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, paper_input in enumerate(paper_inputs):
        progress = (i + 1) / len(paper_inputs)
        progress_bar.progress(progress)

        try:
            # Normalize ID
            status_text.text(f"Processing {paper_input}...")
            paper_id = normalize_arxiv_id(paper_input)

            # Fetch HTML
            status_text.text(f"Fetching {paper_id}...")
            _, html = fetch_paper(paper_id)

            # Parse HTML
            status_text.text(f"Parsing {paper_id}...")
            paper = parse_paper(html, paper_id)

            # Convert to PDF
            status_text.text(f"Converting {paper_id} to PDF...")

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                output_path = Path(tmp.name)

            pdf_path = convert_to_pdf(
                paper,
                output_path=output_path,
                screen_preset=screen_preset,
                download_images=download_images,
            )

            results.append(
                {
                    "success": True,
                    "paper_id": paper_id,
                    "title": paper.title,
                    "authors": paper.authors,
                    "path": pdf_path,
                }
            )

        except (ArxivHTMLNotAvailable, ArxivFetchError, ValueError) as e:
            results.append(
                {
                    "success": False,
                    "paper_id": paper_input,
                    "error": str(e),
                }
            )

        except Exception as e:
            results.append(
                {
                    "success": False,
                    "paper_id": paper_input,
                    "error": f"Unexpected error: {e}",
                }
            )

    progress_bar.empty()
    status_text.empty()

    # Show results
    st.subheader("Results")

    for result in results:
        if result["success"]:
            st.success(f"✅ {result['paper_id']}: {result['title']}")

            # Read file and provide download
            with open(result["path"], "rb") as f:
                pdf_data = f.read()

            st.download_button(
                label=f"📥 Download {result['paper_id']}.pdf",
                data=pdf_data,
                file_name=f"{result['paper_id'].replace('/', '_')}.pdf",
                mime="application/pdf",
            )

            with st.expander("Paper details"):
                st.write(f"**Authors:** {', '.join(result['authors'])}")

        else:
            st.error(f"❌ {result['paper_id']}: {result['error']}")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style="text-align: center; color: #666; font-size: 0.9em;">
        <p>
            <a href="https://github.com/Lev-Stambler/arxiv-to-ereader" target="_blank">GitHub</a> •
            <a href="https://arxiv.org" target="_blank">arXiv</a>
        </p>
        <p>Made with ❤️ for researchers</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def main() -> None:
    """Entry point for the Streamlit app (called via streamlit run)."""
    pass  # Streamlit runs the module directly


if __name__ == "__main__":
    main()
