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
    if not re.search(r"^minimum-contrast\s*=", text, re.M):
        # The palette only governs programs that use ANSI slots. TUIs that
        # emit their own truecolor assume a near-white or near-black ground
        # and can land unreadable on anything else; this makes Ghostty nudge
        # any such cell up to at least 3:1. Written once - a hand-tuned value
        # is left alone.
        text += (
            "\n# Added by `theme`: floor for truecolor text the palette cannot"
            "\n# reach. Tune or delete freely - `theme` only adds it if absent.\n"
            "minimum-contrast = 3\n"
        )
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
    # Earlier versions wrote the banner above the [theme.custom] header, where
    # the strip above could not reach it, so it accumulated three lines per
    # switch. Clear any that a previous version left behind.
    text = re.sub(r"^# (?:Generated|Written) by `theme`.*\n(?:^#.*\n)*", "", text, flags=re.M)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.rstrip("\n") + "\n"
    if custom_block:
        text += "\n" + custom_block
    write(HERDR_CONFIG, text)


CLAUDE_SETTINGS = f"{HOME}/.claude/settings.json"


def sync_claude_code(mode: str) -> str | None:
    """Match Claude Code's own theme to the terminal's light/dark polarity.

    Claude Code renders its syntax colours in truecolor for one polarity and
    reads the setting once, at session startup. A wrong-polarity value is what
    makes code blocks wash out on a light terminal - it looks like a broken
    terminal theme but is not one, and already-running sessions keep the stale
    polarity until restarted.

    The -ansi variant is the default: it makes Claude Code draw every colour
    from the terminal's ANSI palette, which this tool has already corrected -
    its truecolor palettes assume a near-white or near-black ground and wash
    out on a mid-luminance background (a solid orange, a deep cream). An
    explicit -daltonized choice is preserved, only the polarity flips; "auto"
    and a custom: theme are left alone entirely. Returns the value written,
    or None if nothing changed.
    """
    import json

    try:
        with open(CLAUDE_SETTINGS) as handle:
            settings = json.load(handle)
    except FileNotFoundError:
        settings = {}
    except ValueError:
        return None  # never rewrite a file that did not parse

    current = settings.get("theme", "dark")  # absent means Claude's default, dark
    if current == "auto" or current.startswith("custom:"):
        return None
    _, dash, variant = current.partition("-")
    target = f"{mode}-{variant if dash else 'ansi'}"
    if current == target:
        return None
    settings["theme"] = target
    os.makedirs(os.path.dirname(CLAUDE_SETTINGS), exist_ok=True)
    tmp = CLAUDE_SETTINGS + ".tmp"
    with open(tmp, "w") as handle:
        json.dump(settings, handle, indent=2)
        handle.write("\n")
    os.replace(tmp, CLAUDE_SETTINGS)
    return target


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
