"""Colour maths: contrast measurement and hue-preserving remediation.

Everything here is pure and dependency-free so the rest of the package can
treat legibility as a computed property rather than a matter of taste.
"""

from __future__ import annotations

import colorsys

# WCAG AA for normal text. Terminal glyphs are small; this is the right bar.
CONTRAST_TARGET = 4.5

# Slots that actually carry glyphs. 0/8 (blacks) and 7/15 (whites) are
# structural - they back UI chrome rather than render text.
TEXT_SLOTS = (1, 2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14)


def rgb(value: str) -> tuple[int, int, int]:
    h = value.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def to_hex(triple) -> str:
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(v)))) for v in triple)


def luminance(value: str) -> float:
    def channel(v: float) -> float:
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(v) for v in rgb(value))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    """WCAG contrast ratio, 1.0 (identical) to 21.0 (black on white)."""
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def to_hls(value: str) -> tuple[float, float, float]:
    r, g, b = (v / 255 for v in rgb(value))
    return colorsys.rgb_to_hls(r, g, b)


def from_hls(hue: float, light: float, sat: float) -> str:
    r, g, b = colorsys.hls_to_rgb(hue, max(0.0, min(1.0, light)), sat)
    return to_hex((r * 255, g * 255, b * 255))


def remediate(
    color: str,
    background: str,
    target: float = CONTRAST_TARGET,
    darken: bool | None = None,
) -> str:
    """Move a colour's lightness until it clears `target` against `background`.

    Hue and saturation are held fixed and lightness moves only as far as it
    must, so a remediated Gruvbox still reads as Gruvbox. Direction follows the
    background unless `darken` overrides it - which callers must do when
    correcting against several surfaces, because a mid-tone surface can sit on
    the wrong side of the midpoint and flip the direction against the theme.
    """
    if contrast(color, background) >= target:
        return color
    hue, light, sat = to_hls(color)
    if darken is None:
        darken = luminance(background) > 0.5
    low, high = (0.0, light) if darken else (light, 1.0)
    best = from_hls(hue, 0.0 if darken else 1.0, sat)
    # 24 rounds of bisection resolves far finer than 8-bit colour can express.
    for _ in range(24):
        mid = (low + high) / 2
        candidate = from_hls(hue, mid, sat)
        if contrast(candidate, background) >= target:
            best = candidate
            low, high = (mid, high) if darken else (low, mid)
        else:
            low, high = (low, mid) if darken else (mid, high)
    return best


def remediate_against(
    color: str,
    backgrounds,
    target: float = CONTRAST_TARGET,
    darken: bool | None = None,
) -> str:
    """Clear `target` against *every* background the colour may be drawn on.

    Text is not only drawn on `bg`. Panels, statuslines and selection
    highlights use `bg1`/`bg2`, and a colour that reads well on the base can
    disappear on a highlight - which is exactly how a selected sidebar row
    becomes unreadable. Correcting against the single worst surface fixes all
    of them at once.

    Direction is taken from `backgrounds[0]` - the theme's own background -
    rather than from the worst surface. A panel or selection tint can land on
    the far side of the luminance midpoint from the theme it belongs to, and
    deciding per-surface then drives text away from the theme entirely: on a
    solid yellow theme it lightened every failing colour to white.
    """
    if darken is None:
        darken = luminance(backgrounds[0]) > 0.5
    # The binding surface is the one nearest the direction of travel - the
    # darkest when darkening, the lightest when lightening - not whichever the
    # *uncorrected* colour happens to sit closest to. A pale tint starts out
    # nearest the pale panels, but once darkened it is the base ground that
    # limits it, and correcting against the panel left it failing there.
    binding = (min if darken else max)(backgrounds, key=luminance)
    return remediate(color, binding, target, darken=darken)


def swatch(color: str, width: int = 4) -> str:
    """A truecolor block.

    24-bit escapes are absolute rather than palette-indexed, so a swatch shows
    the theme's real colour even while the terminal is on a different palette.
    """
    r, g, b = rgb(color)
    return f"\033[48;2;{r};{g};{b}m{' ' * width}\033[0m"
