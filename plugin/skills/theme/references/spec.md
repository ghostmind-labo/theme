# The palette spec

A theme is authored as eleven values. Everything else — the 16 ANSI slots, the
Helix scope map, the herdr target — is generated from them.

## The roles

| Key | Role | Notes |
|---|---|---|
| `mode` | `dark` or `light` | Decides which direction contrast correction moves. |
| `bg` | deepest background | The reference every other colour is measured against. |
| `bg1` | panels, statusline, popups | One step off `bg`. Keep it close; large jumps read as banding. |
| `bg2` | selection, indent guides | Two steps off `bg`. Must stay distinguishable from `bg1`. |
| `fg` | body text | Corrected to 7:1, a stricter floor than the accents. |
| `dim` | comments, line numbers, punctuation | Deliberately quiet, but still corrected to 4.5:1. |
| `a1` | primary accent | Keywords, operators, cursor, the statusline in normal mode. |
| `a2` | secondary accent | Strings, functions, constants. Usually lighter than `a1` on dark. |
| `a3` | tertiary accent | Types, namespaces, links. A neighbouring hue reads well here. |
| `warn` | warnings, attributes, macros | Keep contrasting; do not fold into the theme's hue. |
| `err` | errors, diff removals | Same. |
| `about` | one-line description | Shown in the picker and written into the generated files. |

`warn` and `err` are the deliberate exception to a single-hue palette. A
monochrome theme whose errors are the same hue as everything else cannot signal
failure. Keep them contrasting even when the brief says "all green".

## JSON contract

All eleven keys plus `about` are required. Colours must be `#rrggbb` — three-
digit shorthand and named colours are rejected.

```json
{
  "mode": "dark",
  "bg":   "#04141a",
  "bg1":  "#0a2430",
  "bg2":  "#123846",
  "fg":   "#cfe9f2",
  "dim":  "#5b8494",
  "a1":   "#3fc1d9",
  "a2":   "#a8ecf7",
  "a3":   "#2a8fa8",
  "warn": "#e6c384",
  "err":  "#e05252",
  "about": "deep ocean, bioluminescent accents"
}
```

Pipe it in:

```bash
cat spec.json | theme new deepsea
```

The validator reports every problem at once rather than stopping at the first,
so a rejected spec can be fixed in one pass.

## How roles map onto ANSI slots

This mapping is why a themed prompt reads as tinted rather than rainbow.
Accents are reused across the slots a shell actually paints with, so a
single-hue theme stays single-hue in the prompt.

| Slot | Source | Slot | Source |
|---|---|---|---|
| 0 black | `bg2` | 8 bright black | `dim` |
| 1 red | `err` | 9 bright red | `err` |
| 2 green | `a1` | 10 bright green | `a2` |
| 3 yellow | `warn` | 11 bright yellow | `warn` |
| 4 blue | `a3` | 12 bright blue | `a1` |
| 5 magenta | `a2` | 13 bright magenta | `a2` |
| 6 cyan | `a1` | 14 bright cyan | `a2` |
| 7 white | `fg` | 15 bright white | `fg` |

Slots 0, 7, 8 and 15 back UI chrome; the rest carry glyphs and are the ones
corrected for contrast.

A typical zsh prompt paints slot 3 (the host marker), 2 (the success arrow), 6
(the working directory) and 4 (the git branch). Those resolve to `warn`, `a1`,
`a1` and `a3` — so choosing those four roles well is what makes a prompt look
deliberate.

## What correction does

At write time each glyph-carrying colour is measured against `bg`. Anything
below 4.5:1 has its lightness bisected — darker on a light background, lighter
on a dark one — while hue and saturation are held fixed. `fg` is held to a
stricter 7:1.

The consequence for authoring: **saturation and hue survive correction,
lightness does not**. A spec that expresses its intent through hue and
saturation comes out looking as intended. A spec that relies on a precise
lightness value may be moved.

## Where things live

| Path | Contents |
|---|---|
| `~/.config/theme/custom.json` | the specs — the source of truth, and what makes themes persist |
| `~/.config/theme/overrides.json` | internal bookkeeping for corrected catalog themes |
| `~/.config/ghostty/themes/<name>` | generated, overwritten on regenerate |
| `~/.config/helix/themes/<name>.toml` | generated, overwritten on regenerate |

Only the first file is authored. Editing the generated files is always wrong;
they are rewritten by `theme generate`.
