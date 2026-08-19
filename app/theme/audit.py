"""Measuring a theme's legibility, and correcting it when it falls short."""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from .catalog import A11Y_SUFFIX, GHOSTTY_USER_THEMES, HELIX_USER_THEMES
from .color import CONTRAST_TARGET, TEXT_SLOTS, contrast, remediate
from .generate import helix_theme
from .targets import palette_of, write


@dataclass
class Report:
    key: str
    mode: str
    background: str
    foreground: str
    fg_ratio: float
    worst: float
    failing: list[int] = field(default_factory=list)
    slots: int = 0

    @property
    def clean(self) -> bool:
        return not self.failing


def audit(key: str, themes: dict) -> Report | None:
    ghostty, _helix, _herdr, mode = themes[key]
    palette, background, foreground = palette_of(ghostty)
    if not (palette and background and foreground):
        return None
    present = [i for i in TEXT_SLOTS if i in palette]
    return Report(
        key=key,
        mode=mode,
        background=background,
        foreground=foreground,
        fg_ratio=contrast(background, foreground),
        worst=min((contrast(background, palette[i]) for i in present), default=0.0),
        failing=[i for i in present if contrast(background, palette[i]) < CONTRAST_TARGET],
        slots=len(present),
    )


def remediate_theme(key: str, themes: dict, overrides: dict) -> int:
    """Rewrite a catalog theme's palette to clear the contrast floor.

    Writes a `<key>-a11y` pair beside the originals and records the mapping;
    upstream files are never touched, so `revert` is just a delete.

    Returns the number of slots corrected, or 0 if nothing needed doing.
    """
    source = overrides.get(key, {}).get("from") or themes[key][0]
    helix_source = overrides.get(key, {}).get("helix_from") or themes[key][1]
    palette, background, foreground = palette_of(source)
    if not (palette and background and foreground):
        return 0

    failing = [i for i in TEXT_SLOTS if i in palette and contrast(background, palette[i]) < CONTRAST_TARGET]
    if not failing and contrast(background, foreground) >= CONTRAST_TARGET:
        return 0

    lines = []
    for index in sorted(palette):
        color = palette[index]
        lines.append(f"palette = {index}={remediate(color, background) if index in TEXT_SLOTS else color}")
    lines += [
        f"background = {background}",
        f"foreground = {remediate(foreground, background, 7.0)}",
        f"cursor-color = {remediate(palette.get(3, foreground), background)}",
    ]
    os.makedirs(GHOSTTY_USER_THEMES, exist_ok=True)
    write(os.path.join(GHOSTTY_USER_THEMES, key + A11Y_SUFFIX), "\n".join(lines) + "\n")

    # A matching Helix theme built from the same corrected palette, so the
    # editor and the terminal agree.
    spec = {
        "bg": background,
        "bg1": palette.get(0, background),
        "bg2": palette.get(8, palette.get(0, background)),
        "fg": foreground,
        "dim": palette.get(8, foreground),
        "a1": palette.get(4, foreground),
        "a2": palette.get(2, foreground),
        "a3": palette.get(5, foreground),
        "warn": palette.get(3, foreground),
        "err": palette.get(1, foreground),
        "about": f"{key}, contrast corrected",
    }
    os.makedirs(HELIX_USER_THEMES, exist_ok=True)
    write(os.path.join(HELIX_USER_THEMES, key + A11Y_SUFFIX + ".toml"), helix_theme(spec))

    overrides[key] = {"from": source, "helix_from": helix_source}
    return len(failing)


def revert_theme(key: str, overrides: dict) -> bool:
    if key not in overrides:
        return False
    for path in (
        os.path.join(GHOSTTY_USER_THEMES, key + A11Y_SUFFIX),
        os.path.join(HELIX_USER_THEMES, key + A11Y_SUFFIX + ".toml"),
    ):
        if os.path.exists(path):
            os.remove(path)
    del overrides[key]
    return True
