# theme

One command to recolour the whole terminal stack, with legibility enforced
rather than eyeballed.

```
theme                     browse in a full-screen picker
theme kanagawa            apply directly
theme new sunset --from '#ff6b35'
```

## Why it exists

A terminal "theme" is really three configs that know nothing about each other,
each with its own spelling for the same palette:

| Layer | Themed by | |
|---|---|---|
| **Ghostty** | `theme = ...` | the ANSI palette everything sits on |
| **herdr** | `[theme] name` | its own TUI chrome (sidebar, tabs) |
| **Helix** | `theme = "..."` | the editor |
| zsh prompt | ANSI slot numbers | follows Ghostty automatically |
| yazi | ANSI slot numbers | follows Ghostty automatically |

The prompt emits `\033[33m` - "paint me slot 3" - and never says what slot 3
is. Ghostty decides. That is why changing one setting recolours the shell, the
file manager and the editor at once, and why this tool only has to write three
files.

herdr ships ~17 named themes. Anything it does not know is set to `terminal`,
which makes it inherit Ghostty's palette - that is what lets the catalog run
well past herdr's own list.

## Contrast is enforced, not assumed

Most light themes are broken. They invert the background but keep the saturated
accents from their dark sibling, so a mid-blue that reads fine on `#1f1f28`
lands at 2:1 on near-white. Measured against WCAG AA (4.5:1), several shipped
light themes failed on **every** text slot.

`theme fix` corrects a palette by bisecting on lightness while holding hue and
saturation fixed, so a corrected Gruvbox still reads as Gruvbox - it is just
legible. Corrected palettes are written beside the originals; upstream files are
never modified, and `theme revert` is a delete.

Generated themes get the same treatment at write time, so a custom theme is
legible by construction.

```
theme contrast            audit everything
theme fix --light         correct the light themes
theme fix --all           correct everything below the floor
```

## Creating themes

Three ways in, all landing in the same store:

```bash
theme new sunset --from '#ff6b35'    # derive a palette from one colour
theme new sunset                     # wizard, previews before writing
cat spec.json | theme new sunset     # full 11-role spec (how an agent drives it)
```

A spec is eleven roles - `bg bg1 bg2 fg dim a1 a2 a3 warn err` plus `mode` and
`about`. Seed derivation spreads a lightness/saturation ramp from a single hue,
then contrast-corrects, so the seed only has to look right; it does not have to
be legible.

Custom themes live in `~/.config/theme/custom.json` as **data, not code**, so
anything added survives an upgrade of the package.

## Layout

```
app/theme/
  color.py      contrast measurement, hue-preserving remediation
  palette.py    the 11-role spec and seed derivation
  catalog.py    theme map + the on-disk stores
  targets.py    reading/writing Ghostty, herdr, Helix
  generate.py   emitting theme files from a spec
  audit.py      measuring and correcting a theme
  tui.py        the full-screen browser
  cli.py        command dispatch
```

The TUI is raw ANSI rather than curses on purpose: curses cannot emit 24-bit
colour, and a theme picker that cannot show a theme's real colours is not worth
much. Truecolor escapes are absolute, so the preview shows each theme as it
actually is while the terminal is still on whatever is currently applied.

## Install

```bash
run routine install      # shim into ~/.local/bin, no venv, no build
run routine check        # compile + resolve every theme
run routine test         # contrast audit
```

Zero third-party dependencies, so the shim points straight at `app/` and edits
take effect immediately.

## One manual step

Applying a theme reloads herdr automatically and Helix picks it up on next
launch. **Ghostty needs `cmd+shift+,`** - it has no CLI reload.

## Claude Code plugin

`plugin/` ships a skill so Claude can drive all of this conversationally -
"make me a theme that looks like a sunset", "this one is hard to read",
"what themes do I have".

```
plugin/
├── .claude-plugin/plugin.json
└── skills/theme/
    ├── SKILL.md                      when to reach for the CLI, and how
    ├── references/spec.md            the 11 roles, JSON contract, ANSI slot map
    ├── references/palette-design.md  turning a brief into a palette
    └── examples/*.json               complete specs, ready to pipe in
```

Load it with `claude --plugin-dir /Volumes/Projects/labo/theme/plugin`.

Themes Claude creates persist the same way any other custom theme does - they
are written to `~/.config/theme/custom.json`, not held in the conversation.
