"""Tests for the CLI module."""

from typer.testing import CliRunner

from arxiv_to_ereader import __version__
from arxiv_to_ereader.cli import app

runner = CliRunner()


class TestCLI:
    """Tests for CLI commands."""

    def test_version_flag(self) -> None:
        """Test --version flag."""
        result = runner.invoke(app, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_version_short_flag(self) -> None:
        """Test -v flag."""
        result = runner.invoke(app, ["-v"])
        assert result.exit_code == 0
        assert __version__ in result.stdout

    def test_help(self) -> None:
        """Test --help flag."""
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "arXiv" in result.stdout
        assert "PDF" in result.stdout

    def test_list_screens(self) -> None:
        """Test --list-screens flag."""
        result = runner.invoke(app, ["--list-screens"])
        assert result.exit_code == 0
        assert "kindle-paperwhite" in result.stdout
        assert "kindle-scribe" in result.stdout
        assert "kobo" in result.stdout

    def test_invalid_screen(self) -> None:
        """Test that invalid screen preset is rejected."""
        result = runner.invoke(app, ["2402.08954", "--screen", "invalid-screen"])
        assert result.exit_code == 1
        assert "Unknown screen preset" in result.stdout

    def test_custom_dimensions_require_both(self) -> None:
        """Test that --width requires --height and vice versa."""
        result = runner.invoke(app, ["2402.08954", "--width", "100"])
        assert result.exit_code == 1
        assert "Both --width and --height" in result.stdout

        result = runner.invoke(app, ["2402.08954", "--height", "150"])
        assert result.exit_code == 1
        assert "Both --width and --height" in result.stdout

    def test_no_papers_provided(self) -> None:
        """Test that no arguments shows help or error."""
        result = runner.invoke(app, [])
        # Should show missing argument error
        assert result.exit_code != 0


class TestCLIArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_single_paper_id(self) -> None:
        """Test parsing single paper ID."""
        # This test requires mocking HTTP - just test it doesn't crash on parse
        result = runner.invoke(app, ["invalid-not-real-id"])
        # Should fail to extract ID
        assert result.exit_code == 1
        assert "Could not extract arXiv ID" in result.stdout

    def test_output_option(self) -> None:
        """Test -o/--output option is accepted."""
        result = runner.invoke(app, ["--help"])
        assert "--output" in result.stdout or "-o" in result.stdout

    def test_screen_option(self) -> None:
        """Test --screen option is accepted."""
        result = runner.invoke(app, ["--help"])
        assert "--screen" in result.stdout

    def test_no_images_option(self) -> None:
        """Test --no-images option is accepted."""
        result = runner.invoke(app, ["--help"])
        assert "--no-images" in result.stdout

    def test_width_height_options(self) -> None:
        """Test --width and --height options are accepted."""
        result = runner.invoke(app, ["--help"])
        assert "--width" in result.stdout
        assert "--height" in result.stdout
