"""Palette specs: the 11 roles a theme is authored in, and how to derive them."""

from __future__ import annotations

from .color import from_hls, to_hls

# The authoring vocabulary. Everything downstream is generated from these.
SPEC_KEYS = (
    "mode",   # dark | light
    "bg",     # deepest background
    "bg1",    # panels, statusline
    "bg2",    # selection
    "fg",     # body text
    "dim",    # comments, line numbers
    "a1",     # primary accent
    "a2",     # secondary accent
    "a3",     # tertiary accent
    "warn",
    "err",
    "about",  # one-line description
)

HEX_KEYS = tuple(k for k in SPEC_KEYS if k not in ("mode", "about"))

# The roles that carry text. Surfaces are bg, bg1 and bg2.
TEXT_ROLES = ("fg", "dim", "a1", "a2", "a3", "warn", "err")


def is_monochrome(spec: dict) -> bool:
    """True when one ink carries every text role.

    Monochrome is read off the spec rather than stored as a flag: it is a fact
    about the colours, so it cannot drift out of date, and a theme becomes
    monochrome the moment it is authored that way. A third colour placed in a
    surface role - the splash in `lemon-moon` - does not break it, because the
    surfaces were never part of the claim.
    """
    try:
        return len({spec[role].lower() for role in TEXT_ROLES}) == 1
    except (KeyError, AttributeError):
        return False


def derive(seed: str, mode: str = "dark", about: str = "") -> dict:
    """Build a full spec from a single seed colour.

    Hue comes from the seed and carries across the accents; lightness and
    saturation are laid on a ramp suited to the mode. Contrast correction
    happens at generation time, so the seed only has to look right - it does
    not have to be legible.
    """
    hue, _light, sat = to_hls(seed)
    sat = max(0.25, min(0.95, sat))
    neighbour = (hue + 0.08) % 1.0

    if mode == "dark":
        spec = dict(
            bg=from_hls(hue, 0.05, sat * 0.45),
            bg1=from_hls(hue, 0.11, sat * 0.42),
            bg2=from_hls(hue, 0.19, sat * 0.40),
            fg=from_hls(hue, 0.86, sat * 0.25),
            dim=from_hls(hue, 0.48, sat * 0.35),
            a1=from_hls(hue, 0.65, sat),
            a2=from_hls(hue, 0.82, sat * 0.70),
            a3=from_hls(neighbour, 0.58, sat * 0.85),
            warn=from_hls(0.12, 0.65, 0.90),
            err=from_hls(0.00, 0.66, 0.85),
        )
    else:
        spec = dict(
            bg=from_hls(hue, 0.965, sat * 0.28),
            bg1=from_hls(hue, 0.915, sat * 0.30),
            bg2=from_hls(hue, 0.825, sat * 0.32),
            fg=from_hls(hue, 0.12, sat * 0.35),
            dim=from_hls(hue, 0.38, sat * 0.35),
            a1=from_hls(hue, 0.30, sat),
            a2=from_hls(hue, 0.20, sat * 0.80),
            a3=from_hls(neighbour, 0.34, sat * 0.85),
            warn=from_hls(0.12, 0.28, 0.95),
            err=from_hls(0.00, 0.36, 0.85),
        )

    spec["mode"] = mode
    spec["about"] = about or f"derived from {seed}"
    return {k: spec[k] for k in SPEC_KEYS}


def validate(spec: dict) -> list[str]:
    """Return a list of human-readable problems; empty means valid."""
    import re

    problems = []
    missing = [k for k in SPEC_KEYS if k not in spec]
    if missing:
        problems.append(f"missing keys: {', '.join(missing)}")
    if spec.get("mode") not in ("dark", "light"):
        problems.append("mode must be 'dark' or 'light'")
    for key in HEX_KEYS:
        value = spec.get(key)
        if value is not None and not re.fullmatch(r"#[0-9a-fA-F]{6}", str(value)):
            problems.append(f"{key} must be #rrggbb, got {value!r}")
    return problems
