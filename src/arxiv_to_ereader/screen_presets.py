"""E-reader screen size presets for PDF generation."""

from dataclasses import dataclass


@dataclass
class ScreenPreset:
    """E-reader screen preset configuration."""

    name: str
    width_mm: float
    height_mm: float
    ppi: int
    base_font_pt: float
    description: str


SCREEN_PRESETS: dict[str, ScreenPreset] = {
    "kindle-paperwhite": ScreenPreset(
        name="Kindle Paperwhite 6.8\"",
        width_mm=105,
        height_mm=140,
        ppi=300,
        base_font_pt=11,
        description="Kindle Paperwhite 6.8-inch (2021+)",
    ),
    "kindle-paperwhite-6": ScreenPreset(
        name="Kindle Paperwhite 6\"",
        width_mm=91,
        height_mm=123,
        ppi=300,
        base_font_pt=10,
        description="Kindle Paperwhite 6-inch (older models)",
    ),
    "kindle-scribe": ScreenPreset(
        name="Kindle Scribe",
        width_mm=158,
        height_mm=210,
        ppi=300,
        base_font_pt=12,
        description="Kindle Scribe 10.2-inch",
    ),
    "kobo-clara": ScreenPreset(
        name="Kobo Clara",
        width_mm=91,
        height_mm=123,
        ppi=300,
        base_font_pt=10,
        description="Kobo Clara 6-inch",
    ),
    "kobo-libra": ScreenPreset(
        name="Kobo Libra",
        width_mm=107,
        height_mm=142,
        ppi=300,
        base_font_pt=11,
        description="Kobo Libra 7-inch",
    ),
    "remarkable": ScreenPreset(
        name="reMarkable 2",
        width_mm=158,
        height_mm=210,
        ppi=226,
        base_font_pt=12,
        description="reMarkable 2 10.3-inch",
    ),
    "a5": ScreenPreset(
        name="A5 Paper",
        width_mm=148,
        height_mm=210,
        ppi=300,
        base_font_pt=11,
        description="A5 paper size (148x210mm)",
    ),
}


def get_preset(name: str) -> ScreenPreset:
    """Get a screen preset by name.

    Args:
        name: Preset name (e.g., "kindle-paperwhite", "kindle-scribe")

    Returns:
        ScreenPreset configuration

    Raises:
        ValueError: If preset name is not found
    """
    if name not in SCREEN_PRESETS:
        available = ", ".join(SCREEN_PRESETS.keys())
        raise ValueError(f"Unknown preset '{name}'. Available: {available}")
    return SCREEN_PRESETS[name]


def custom_preset(
    width_mm: float,
    height_mm: float,
    base_font_pt: float = 11,
) -> ScreenPreset:
    """Create a custom screen preset.

    Args:
        width_mm: Page width in millimeters
        height_mm: Page height in millimeters
        base_font_pt: Base font size in points (default: 11)

    Returns:
        Custom ScreenPreset configuration
    """
    return ScreenPreset(
        name="Custom",
        width_mm=width_mm,
        height_mm=height_mm,
        ppi=300,
        base_font_pt=base_font_pt,
        description=f"Custom {width_mm}x{height_mm}mm",
    )
