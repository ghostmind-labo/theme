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

At write time each glyph-carrying colour is measured against **every surface it
can be drawn on** — `bg`, the panel `bg1` and the selection `bg2` — and
corrected against the worst of them. Anything below 4.5:1 has its lightness
bisected while hue and saturation are held fixed. `fg` is held to a stricter
7:1.

Correction direction comes from the theme's `mode`, never from an individual
surface: a mid-tone selection tint can sit on the far side of the luminance
midpoint from its own theme, and deciding per-surface would push text away from
the theme entirely (on a solid-yellow light theme it once lightened failing
colours to white).

The consequence for authoring: **saturation and hue survive correction,
lightness does not**. A spec that expresses its intent through hue and
saturation comes out looking as intended. A spec that relies on a precise
lightness value may be moved — and since `bg2` is the harshest surface, a
colour close to `bg2`'s lightness will be moved the furthest.

## Where things live

| Path | Contents |
|---|---|
| `app/theme/themes.json` (in the repo) | the specs — the source of truth, committed and shipped with the code. Each carries `created` and `updated` ISO timestamps, written by the tool on store; do not hand-set them |
| `~/.config/theme/favorites.json` | pinned theme keys, in pin order; may name catalog themes too |
| `~/.config/theme/overrides.json` | internal bookkeeping for corrected catalog themes |
| `~/.config/ghostty/themes/<name>` | generated, overwritten on regenerate |
| `~/.config/helix/themes/<name>.toml` | generated, overwritten on regenerate |

Only the first file is authored. Editing the generated files is always wrong;
they are rewritten by `theme generate`.
