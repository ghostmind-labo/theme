"""The theme catalog and the on-disk stores.

Two kinds of theme live here:

* **catalog** - names that already exist in Ghostty's and Helix's own theme
  sets. We only map the three spellings of the same palette.
* **custom** - palettes this tool generates itself, authored as an 11-role
  spec. These live in a JSON store rather than in this file, so a theme added
  by `theme new` survives an upgrade of the package.

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

STORE_DIR = f"{HOME}/.config/theme"
CUSTOM_STORE = f"{STORE_DIR}/custom.json"
OVERRIDE_STORE = f"{STORE_DIR}/overrides.json"

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

# Seeded into the custom store on first run.
SEED_CUSTOM = {
    "amber": {
        "mode": "dark",
        "bg": "#140d00",
        "bg1": "#241a03",
        "bg2": "#3d2c06",
        "fg": "#ffb000",
        "dim": "#8a6212",
        "a1": "#ffcc4d",
        "a2": "#ffe6a3",
        "a3": "#cc8800",
        "warn": "#fff07a",
        "err": "#ff5f4d",
        "about": "amber CRT monitor",
    },
    "blueprint": {
        "mode": "dark",
        "bg": "#0a1b2e",
        "bg1": "#12293f",
        "bg2": "#1d3d59",
        "fg": "#cfe3f5",
        "dim": "#6b8ba8",
        "a1": "#7fb6e8",
        "a2": "#a8d4ff",
        "a3": "#4a86c4",
        "warn": "#ffd479",
        "err": "#ff8080",
        "about": "drafting blueprint navy",
    },
    "cyanotype": {
        "mode": "dark",
        "bg": "#041418",
        "bg1": "#08262c",
        "bg2": "#0d3d47",
        "fg": "#a8ecf5",
        "dim": "#4a8c96",
        "a1": "#52d6e8",
        "a2": "#b8f5ff",
        "a3": "#2ba3b5",
        "warn": "#ffe27a",
        "err": "#ff7b7b",
        "about": "cyan photographic print",
    },
    "daylight": {
        "mode": "light",
        "bg": "#ffffff",
        "bg1": "#f2f4f7",
        "bg2": "#dfe4ea",
        "fg": "#1b1f26",
        "dim": "#585f6b",
        "a1": "#0f6b3f",
        "a2": "#8a3d00",
        "a3": "#1a4fa8",
        "warn": "#6b5300",
        "err": "#a4161a",
        "about": "pure white, maximum legibility",
    },
    "hotline": {
        "mode": "dark",
        "bg": "#14060f",
        "bg1": "#240b1a",
        "bg2": "#3d132c",
        "fg": "#f5c2e0",
        "dim": "#a05c85",
        "a1": "#ff6bc4",
        "a2": "#ffb3e0",
        "a3": "#d13d99",
        "warn": "#ffd166",
        "err": "#ff5555",
        "about": "magenta neon on near-black",
    },
    "ice": {
        "mode": "dark",
        "bg": "#0d1418",
        "bg1": "#16232a",
        "bg2": "#223540",
        "fg": "#dbeef5",
        "dim": "#7896a3",
        "a1": "#a3d9e8",
        "a2": "#ffffff",
        "a3": "#6fb3c9",
        "warn": "#ffe0a3",
        "err": "#ff8f8f",
        "about": "pale ice on cold slate",
    },
    "matrix": {
        "mode": "dark",
        "bg": "#000000",
        "bg1": "#071a07",
        "bg2": "#0d330d",
        "fg": "#00ff41",
        "dim": "#128c2a",
        "a1": "#39ff77",
        "a2": "#b3ffcc",
        "a3": "#00c633",
        "warn": "#ccff00",
        "err": "#ff3131",
        "about": "pure black, high-voltage green",
    },
    "papyrus": {
        "mode": "light",
        "bg": "#f4ecd8",
        "bg1": "#e8dcc0",
        "bg2": "#d3c19c",
        "fg": "#2e2114",
        "dim": "#6b5940",
        "a1": "#8a4a1a",
        "a2": "#4a3418",
        "a3": "#7a5a12",
        "warn": "#6b5200",
        "err": "#a01818",
        "about": "sepia paper, brown ink",
    },
    "parchment": {
        "mode": "light",
        "bg": "#faf6ed",
        "bg1": "#efe8d8",
        "bg2": "#ddd2bb",
        "fg": "#26211a",
        "dim": "#5f574a",
        "a1": "#1f5f4a",
        "a2": "#7a3a12",
        "a3": "#31508f",
        "warn": "#6a5000",
        "err": "#992222",
        "about": "warm white, high-contrast ink",
    },
    "phosphor": {
        "mode": "dark",
        "bg": "#071206",
        "bg1": "#0e2410",
        "bg2": "#1a3d1c",
        "fg": "#9ff29f",
        "dim": "#4e8a52",
        "a1": "#6ee06e",
        "a2": "#b7ffb7",
        "a3": "#3fbf50",
        "warn": "#d8ff6b",
        "err": "#ff6b6b",
        "about": "P1 green CRT phosphor",
    },
    "rust": {
        "mode": "dark",
        "bg": "#150c06",
        "bg1": "#26150c",
        "bg2": "#3d2415",
        "fg": "#f0c9a8",
        "dim": "#a07850",
        "a1": "#e08a4d",
        "a2": "#ffd9b3",
        "a3": "#b35f28",
        "warn": "#ffcf70",
        "err": "#ff6b5b",
        "about": "oxidised copper",
    },
    "ultraviolet": {
        "mode": "dark",
        "bg": "#100a1c",
        "bg1": "#1c1230",
        "bg2": "#2e1f4d",
        "fg": "#d9c7f5",
        "dim": "#7a6199",
        "a1": "#b18aeb",
        "a2": "#e5d4ff",
        "a3": "#8a5cd1",
        "warn": "#ffd47a",
        "err": "#ff7ab0",
        "about": "deep violet monochrome",
    },
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
    """Custom palettes. Seeds the store on first run, then the store wins."""
    if not os.path.exists(CUSTOM_STORE):
        _write_json(CUSTOM_STORE, SEED_CUSTOM)
        return dict(SEED_CUSTOM)
    return _read_json(CUSTOM_STORE, dict(SEED_CUSTOM))


def save_custom(custom: dict) -> None:
    _write_json(CUSTOM_STORE, custom)


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
