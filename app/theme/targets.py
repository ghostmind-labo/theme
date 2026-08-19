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
    HOME,
)


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


def set_herdr(name: str, custom_block: str | None = None) -> None:
    """Rewrite herdr's [theme] name and its [theme.custom] override block.

    herdr draws its sidebar on its own surfaces. Left to inherit, it picks
    pairings nothing has checked, which is how a selected workspace row ends up
    with an unreadable subtitle. The block is regenerated per theme and always
    replaced, never merged - a stale block from another palette is worse than
    none.
    """
    text = read(HERDR_CONFIG)

    def replace_name(match: re.Match) -> str:
        body = re.sub(r"^name\s*=.*$", f'name = "{name}"', match.group(2), count=1, flags=re.M)
        return match.group(1) + body

    text = re.sub(r"(^\[theme\][^\n]*\n)((?:(?!^\[).*\n)*)", replace_name, text, count=1, flags=re.M)
    text = re.sub(r"^\[theme\.custom\]\n(?:(?!^\[).*\n)*", "", text, flags=re.M)
    text = text.rstrip("\n") + "\n"
    if custom_block:
        text += "\n" + custom_block
    write(HERDR_CONFIG, text)


CLAUDE_SETTINGS = f"{HOME}/.claude/settings.json"


def sync_claude_code(mode: str) -> bool:
    """Match Claude Code's own theme to the terminal's light/dark mode.

    Claude Code picks its syntax colours for one polarity. Under the opposite
    one its inline code and dim text wash out - which looks like a broken
    terminal theme but is not one. Returns True if the setting changed.
    """
    import json

    try:
        with open(CLAUDE_SETTINGS) as handle:
            settings = json.load(handle)
    except (FileNotFoundError, ValueError):
        return False
    if settings.get("theme") == mode:
        return False
    settings["theme"] = mode
    with open(CLAUDE_SETTINGS, "w") as handle:
        json.dump(settings, handle, indent=2)
        handle.write("\n")
    return True


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
    from .herdr_theme import herdr_custom

    ghostty, helix, herdr, mode = themes[key]
    palette, background, foreground = palette_of(ghostty)
    block = herdr_custom(palette, background, foreground) if (palette and background and foreground) else None

    set_ghostty(ghostty)
    set_helix(helix)
    set_herdr(herdr, custom_block=block)
    return {
        "key": key,
        "mode": mode,
        "ghostty": ghostty,
        "helix": helix,
        "herdr": herdr,
        "herdr_chrome": bool(block),
        "claude_synced": sync_claude_code(mode),
        "herdr_reloaded": reload_herdr(),
    }
