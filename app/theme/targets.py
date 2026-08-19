"""Reading and writing the three configs that actually hold a theme.

Each layer has its own theme system and its own spelling for the same palette:

    Ghostty   the ANSI palette everything else sits on
    herdr     its own TUI chrome (sidebar, tabs)
    Helix     the editor

zsh's prompt and yazi both render with the terminal's ANSI colours, so they
follow Ghostty automatically and need no config of their own.
"""

from __future__ import annotations

import os
import re
import subprocess

from .catalog import (
    GHOSTTY_CONFIG,
    GHOSTTY_SYSTEM_THEMES,
    GHOSTTY_USER_THEMES,
    HELIX_CONFIG,
    HERDR_CONFIG,
)

# Kanagawa's dim tokens are very low contrast, which is what makes herdr's tab
# and workspace names hard to read. These lift the muted greys toward
# Kanagawa's own lighter palette and put a high-contrast carpYellow on the
# accent. Every value is a real Kanagawa colour, so it stays on-theme.
KANAGAWA_HERDR_CUSTOM = """[theme.custom]
text = "#dcd7ba"
subtext0 = "#c8c093"
overlay0 = "#a6a08c"
overlay1 = "#b8b0c8"
surface0 = "#2a2a37"
surface1 = "#43435a"
accent = "#e6c384"
blue = "#7fb4ca"
green = "#98bb6c"
yellow = "#e6c384"
red = "#e82424"
teal = "#7aa89f"
mauve = "#957fb8"
peach = "#ffa066"
"""


def read(path: str) -> str:
    try:
        with open(path) as handle:
            return handle.read()
    except FileNotFoundError:
        return ""


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        handle.write(text)


def palette_of(ghostty_name: str) -> tuple[dict, str | None, str | None]:
    """Parse palette 0-15 plus background/foreground from a Ghostty theme file.

    User themes shadow system ones, so a generated or remediated palette is
    found before the stock file of the same name.
    """
    path = os.path.join(GHOSTTY_USER_THEMES, ghostty_name)
    if not os.path.exists(path):
        path = os.path.join(GHOSTTY_SYSTEM_THEMES, ghostty_name)

    palette: dict[int, str] = {}
    background = foreground = None
    for line in read(path).splitlines():
        match = re.match(r"\s*palette\s*=\s*(\d+)\s*=\s*(#[0-9a-fA-F]{6})", line)
        if match:
            palette[int(match.group(1))] = match.group(2).lower()
            continue
        match = re.match(r"\s*background\s*=\s*#?([0-9a-fA-F]{6})", line)
        if match:
            background = "#" + match.group(1).lower()
        match = re.match(r"\s*foreground\s*=\s*#?([0-9a-fA-F]{6})", line)
        if match:
            foreground = "#" + match.group(1).lower()
    return palette, background, foreground


def current(themes: dict) -> str | None:
    """Which theme key is active, read back out of Ghostty's config."""
    match = re.search(r"^theme\s*=\s*(.+)$", read(GHOSTTY_CONFIG), re.M)
    if not match:
        return None
    name = match.group(1).strip()
    for key, (ghostty, *_rest) in themes.items():
        if ghostty == name:
            return key
    return None


def set_ghostty(name: str) -> None:
    text = read(GHOSTTY_CONFIG)
    if re.search(r"^theme\s*=", text, re.M):
        text = re.sub(r"^theme\s*=.*$", f"theme = {name}", text, count=1, flags=re.M)
    else:
        text += f"\ntheme = {name}\n"
    write(GHOSTTY_CONFIG, text)


def set_helix(name: str) -> None:
    text = read(HELIX_CONFIG)
    if re.search(r"^theme\s*=", text, re.M):
        text = re.sub(r"^theme\s*=.*$", f'theme = "{name}"', text, count=1, flags=re.M)
    else:
        text = f'theme = "{name}"\n' + text
    write(HELIX_CONFIG, text)


def set_herdr(name: str, kanagawa_custom: bool) -> None:
    """Rewrite herdr's [theme] name, and manage the Kanagawa contrast block.

    Those overrides are hex values tuned to one palette, so they are written
    only for Kanagawa and stripped when switching away - otherwise they would
    clash with every other theme.
    """
    text = read(HERDR_CONFIG)

    def replace_name(match: re.Match) -> str:
        body = re.sub(r"^name\s*=.*$", f'name = "{name}"', match.group(2), count=1, flags=re.M)
        return match.group(1) + body

    text = re.sub(r"(^\[theme\][^\n]*\n)((?:(?!^\[).*\n)*)", replace_name, text, count=1, flags=re.M)
    text = re.sub(r"^\[theme\.custom\]\n(?:(?!^\[).*\n)*", "", text, flags=re.M)
    text = text.rstrip("\n") + "\n"
    if kanagawa_custom:
        text += "\n" + KANAGAWA_HERDR_CUSTOM
    write(HERDR_CONFIG, text)


def reload_herdr() -> bool:
    try:
        done = subprocess.run(
            ["herdr", "server", "reload-config"], capture_output=True, text=True
        )
        return done.returncode == 0
    except OSError:
        return False


def apply(key: str, themes: dict) -> dict:
    """Write the theme into all three configs. Returns what happened."""
    ghostty, helix, herdr, mode = themes[key]
    set_ghostty(ghostty)
    set_helix(helix)
    set_herdr(herdr, kanagawa_custom=key.startswith("kanagawa"))
    return {
        "key": key,
        "mode": mode,
        "ghostty": ghostty,
        "helix": helix,
        "herdr": herdr,
        "herdr_reloaded": reload_herdr(),
    }
