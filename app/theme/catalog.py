"""The theme catalog and the on-disk stores.

Two kinds of theme live here:

* **catalog** - names that already exist in Ghostty's and Helix's own theme
  sets. We only map the three spellings of the same palette.
* **custom** - palettes this tool generates itself, authored as an 11-role
  spec. These live in `themes.json` beside this file - data, not code, but
  inside the repo, so every theme kept is committed and shipped with it.

herdr only ships ~17 named themes. Anything it does not know is set to
"terminal", which makes it inherit Ghostty's palette - that is what lets the
catalog run well past herdr's own list.
"""

from __future__ import annotations

import json
import os

HOME = os.path.expanduser("~")

GHOSTTY_CONFIG = f"{HOME}/.config/ghostty/config"
HERDR_CONFIG = f"{HOME}/.config/herdr/config.toml"
HELIX_CONFIG = f"{HOME}/.config/helix/config.toml"

GHOSTTY_BIN = "/Applications/Ghostty.app/Contents/MacOS/ghostty"
GHOSTTY_SYSTEM_THEMES = "/Applications/Ghostty.app/Contents/Resources/ghostty/themes"
GHOSTTY_USER_THEMES = f"{HOME}/.config/ghostty/themes"
HELIX_USER_THEMES = f"{HOME}/.config/helix/themes"

# Authored themes ship with the package. Per-machine state - pins and which
# catalog themes were corrected - stays under ~/.config.
CUSTOM_STORE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "themes.json")
STORE_DIR = f"{HOME}/.config/theme"
OVERRIDE_STORE = f"{STORE_DIR}/overrides.json"
FAVORITES_STORE = f"{STORE_DIR}/favorites.json"

# Remediated palettes are written beside the originals under this suffix, so
# upstream theme files are never modified in place.
A11Y_SUFFIX = "-a11y"

# key -> (ghostty name, helix name, herdr name, mode)
CATALOG = {
    "kanagawa":             ("Kanagawa Wave",           "kanagawa",              "kanagawa",          "dark"),
    "kanagawa-dragon":      ("Kanagawa Dragon",         "kanagawa-dragon",       "kanagawa",          "dark"),
    "catppuccin-mocha":     ("Catppuccin Mocha",        "catppuccin_mocha",      "catppuccin",        "dark"),
    "catppuccin-macchiato": ("Catppuccin Macchiato",    "catppuccin_macchiato",  "catppuccin",        "dark"),
    "catppuccin-frappe":    ("Catppuccin Frappe",       "catppuccin_frappe",     "catppuccin",        "dark"),
    "tokyonight":           ("TokyoNight",              "tokyonight",            "tokyo-night",       "dark"),
    "tokyonight-storm":     ("TokyoNight Storm",        "tokyonight_storm",      "tokyo-night",       "dark"),
    "tokyonight-moon":      ("TokyoNight Moon",         "tokyonight_moon",       "tokyo-night",       "dark"),
    "gruvbox":              ("Gruvbox Dark",            "gruvbox",               "gruvbox",           "dark"),
    "nord":                 ("Nord",                    "nord",                  "nord",              "dark"),
    "dracula":              ("Dracula",                 "dracula",               "dracula",           "dark"),
    "rose-pine":            ("Rose Pine",               "rose_pine",             "rose-pine",         "dark"),
    "rose-pine-moon":       ("Rose Pine Moon",          "rose_pine_moon",        "rose-pine",         "dark"),
    "onedark":              ("Atom One Dark",           "onedark",               "one-dark",          "dark"),
    "solarized-dark":       ("iTerm2 Solarized Dark",   "solarized_dark",        "solarized",         "dark"),
    "everforest":           ("Everforest Dark Hard",    "everforest_dark",       "terminal",          "dark"),
    "ayu":                  ("Ayu",                     "ayu_dark",              "terminal",          "dark"),
    "github-dark":          ("GitHub Dark",             "github_dark",           "terminal",          "dark"),
    "monokai-pro":          ("Monokai Pro",             "monokai_pro",           "terminal",          "dark"),
    "nightfox":             ("Nightfox",                "nightfox",              "terminal",          "dark"),
    "carbonfox":            ("Carbonfox",               "carbonfox",             "terminal",          "dark"),
    "vesper":               ("Vesper",                  "vesper",                "vesper",            "dark"),
    "zenburn":              ("Zenburn",                 "zenburn",               "terminal",          "dark"),
    "sonokai":              ("Sonokai",                 "sonokai",               "terminal",          "dark"),
    "snazzy":               ("Snazzy",                  "snazzy",                "terminal",          "dark"),
    "flexoki-dark":         ("Flexoki Dark",            "flexoki_dark",          "terminal",          "dark"),
    "catppuccin-latte":     ("Catppuccin Latte",        "catppuccin_latte",      "catppuccin-latte",  "light"),
    "gruvbox-light":        ("Gruvbox Light",           "gruvbox_light",         "gruvbox-light",     "light"),
    "rose-pine-dawn":       ("Rose Pine Dawn",          "rose_pine_dawn",        "rose-pine-dawn",    "light"),
    "solarized-light":      ("iTerm2 Solarized Light",  "solarized_light",       "solarized-light",   "light"),
    "tokyonight-day":       ("TokyoNight Day",          "tokyonight_day",        "tokyo-night-day",   "light"),
    "ayu-light":            ("Ayu Light",               "ayu_light",             "terminal",          "light"),
    "github-light":         ("GitHub Light Default",    "github_light",          "terminal",          "light"),
    "everforest-light":     ("Everforest Light Med",    "everforest_light",      "terminal",          "light"),
    "flexoki-light":        ("Flexoki Light",           "flexoki_light",         "terminal",          "light"),
}

def _read_json(path, default):
    try:
        with open(path) as handle:
            return json.load(handle)
    except (FileNotFoundError, ValueError):
        return default


def _write_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as handle:
        json.dump(data, handle, indent=2, sort_keys=True)
        handle.write("\n")


def load_custom() -> dict:
    """Authored palettes, from the package's own `themes.json`."""
    return _read_json(CUSTOM_STORE, {})


def save_custom(custom: dict) -> None:
    _write_json(CUSTOM_STORE, custom)


def stamp(spec: dict, previous: dict | None = None) -> dict:
    """Date a spec on its way into the store.

    `created` survives a rewrite - editing a theme does not make it new - while
    `updated` moves every time. Both are plain local ISO strings: the store is
    read by humans and diffed in git, so a timestamp should be legible in both.
    """
    import datetime

    now = datetime.datetime.now().replace(microsecond=0).isoformat()
    spec = dict(spec)
    spec["created"] = (previous or {}).get("created", now)
    spec["updated"] = now
    return spec


def load_favorites() -> list:
    """Theme keys the user has pinned, in the order they pinned them.

    Kept as a plain list rather than folded into the custom store, because a
    favourite is a view preference and may point at a catalog theme the tool
    does not own. A key that no longer resolves is dropped on read.
    """
    data = _read_json(FAVORITES_STORE, [])
    return [k for k in data if isinstance(k, str)] if isinstance(data, list) else []


def save_favorites(favorites) -> None:
    _write_json(FAVORITES_STORE, list(favorites))


def load_overrides() -> dict:
    """Which catalog themes have had their contrast remediated.

    Internal bookkeeping - deliberately not surfaced in the UI. A corrected
    theme should simply look correct; the user has no reason to care that we
    rewrote a palette to get there.
    """
    return _read_json(OVERRIDE_STORE, {})


def save_overrides(overrides: dict) -> None:
    _write_json(OVERRIDE_STORE, overrides)


def resolve() -> tuple[dict, dict, dict]:
    """Return (themes, custom, overrides).

    `themes` maps every key - catalog and custom alike - to the target names to
    write, with remediated entries already pointing at their corrected files.
    """
    custom = load_custom()
    overrides = load_overrides()

    themes = dict(CATALOG)
    for key, spec in custom.items():
        themes[key] = (key, key, "terminal", spec.get("mode", "dark"))

    for key in overrides:
        if key in themes:
            _g, _h, herdr, mode = themes[key]
            themes[key] = (key + A11Y_SUFFIX, key + A11Y_SUFFIX, herdr, mode)

    return themes, custom, overrides
