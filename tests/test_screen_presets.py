"""Tests for the screen presets module."""

import pytest

from arxiv_to_ereader.screen_presets import (
    SCREEN_PRESETS,
    ScreenPreset,
    custom_preset,
    get_preset,
)


class TestScreenPresets:
    """Tests for screen presets."""

    def test_presets_exist(self) -> None:
        """Test that expected presets exist."""
        expected_presets = [
            "kindle-paperwhite",
            "kindle-paperwhite-6",
            "kindle-scribe",
            "kobo-clara",
            "kobo-libra",
            "remarkable",
            "a5",
        ]
        for preset_name in expected_presets:
            assert preset_name in SCREEN_PRESETS

    def test_preset_properties(self) -> None:
        """Test that presets have required properties."""
        for name, preset in SCREEN_PRESETS.items():
            assert isinstance(preset, ScreenPreset)
            assert preset.name
            assert preset.width_mm > 0
            assert preset.height_mm > 0
            assert preset.ppi > 0
            assert preset.base_font_pt > 0
            assert preset.description

    def test_get_preset(self) -> None:
        """Test get_preset function."""
        preset = get_preset("kindle-paperwhite")
        assert preset.name == "Kindle Paperwhite 6.8\""
        assert preset.width_mm == 105
        assert preset.height_mm == 140

    def test_get_preset_invalid(self) -> None:
        """Test get_preset with invalid name."""
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset("invalid-preset")

    def test_custom_preset(self) -> None:
        """Test custom_preset function."""
        preset = custom_preset(100, 150)
        assert preset.name == "Custom"
        assert preset.width_mm == 100
        assert preset.height_mm == 150
        assert preset.base_font_pt == 11  # default

    def test_custom_preset_with_font(self) -> None:
        """Test custom_preset with custom font size."""
        preset = custom_preset(100, 150, base_font_pt=12)
        assert preset.base_font_pt == 12


class TestKindlePresets:
    """Tests specific to Kindle device presets."""

    def test_kindle_paperwhite_dimensions(self) -> None:
        """Test Kindle Paperwhite 6.8\" dimensions."""
        preset = get_preset("kindle-paperwhite")
        # 6.8" at 300ppi should be roughly 105x140mm
        assert 100 < preset.width_mm < 110
        assert 135 < preset.height_mm < 145

    def test_kindle_scribe_dimensions(self) -> None:
        """Test Kindle Scribe dimensions."""
        preset = get_preset("kindle-scribe")
        # 10.2" at 300ppi should be roughly 158x210mm
        assert 155 < preset.width_mm < 165
        assert 205 < preset.height_mm < 215

    def test_kindle_scribe_larger_font(self) -> None:
        """Test that Kindle Scribe has larger base font for larger screen."""
        paperwhite = get_preset("kindle-paperwhite")
        scribe = get_preset("kindle-scribe")
        assert scribe.base_font_pt >= paperwhite.base_font_pt
