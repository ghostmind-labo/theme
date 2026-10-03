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

## Favorites

The picker and `theme list` show two sections: **favorites**, then every other
theme in one alphabetical **themes** list. Whether a theme shipped with Ghostty
or was authored here is not something you browse by. There is nothing to set
up for favorites — the section appears with the first pin and disappears with
the last.

```bash
theme fav fieldnote       # pin it; run again to unpin
theme fav                 # what is pinned, in pin order
```

In the picker, `f` pins or unpins the highlighted theme and `p`
narrows the list to pinned ones. Any theme can be pinned, and a pinned theme is
listed once rather than repeated in the themes list.

Pins live in `~/.config/theme/favorites.json` as a plain list of names.

## Monochrome

A theme is monochrome when one ink carries every text role — `fg`, `dim`, the
three accents, `warn` and `err` all the same hex, so warnings and errors look
like ordinary text. Those themes are lifted into their own **monochrome**
section in `theme list` and the picker, between favorites and the rest, and `m`
in the picker narrows to them.

Nothing declares it. It is read off the spec, so a theme joins the section the
moment it is authored that way and can never carry a stale flag. A third colour
placed in a surface role — the citron selection in `lemon-moon` — does not break
it, because surfaces were never part of the claim: the splash is a splash
precisely because the text stays one colour.

## Archiving

A theme you are done with can be put out of sight without being deleted. The
list and the picker hide archived themes; everything else about them is
untouched, so restoring is instant and an archived theme still applies if you
name it outright.

```bash
theme archive gruvbox     # put it away
theme archive             # what is archived
theme unarchive gruvbox   # bring it back
theme list --all          # list with the archived section shown
```

In the picker, `x` archives or restores the highlighted theme and `v` opens the
vault — the archive as its own scope, where `x` puts one back. The applied
theme cannot be archived, and archiving a pinned theme unpins it: a pin lifts a
theme up, an archive hides it, and holding both has no coherent display.

Archived names live in `~/.config/theme/archive.json`. Deleting for good is
still `theme rm <name>`, which also drops the name from the archive.

## Creating themes

Four ways in, all landing in the same store:

```bash
theme new sunset --from '#ff6b35'    # derive a palette from one colour
theme new sunset                     # wizard, previews before writing
cat spec.json | theme new sunset     # full 11-role spec (how an agent drives it)
```

Or press `n` in the picker: the bottom bar asks for a name, a seed colour
and dark/light, then the cursor lands on the new theme with its preview
showing.

Every theme carries `created` and `updated` timestamps, written on store, so
the picker can sort by newest rather than by name alone.

Lowercase letters command, shifted letters search. `V` jumps to `vermilion`
without a prefix key, while `d`/`l` limit to dark or light, `j`/`k` move,
`g`/`b` go to the ends, `f` pins, `p` shows pins only, `s` cycles the sort
(name, created, updated), `a` clears everything, `⏎` applies and `q` quits.
Names that *start* with the query lead the list; the rest still match below.

A spec is eleven roles - `bg bg1 bg2 fg dim a1 a2 a3 warn err` plus `mode` and
`about`. Seed derivation spreads a lightness/saturation ramp from a single hue,
then contrast-corrects, so the seed only has to look right; it does not have to
be legible.

Authored themes live in `app/theme/themes.json` as **data, not code**, inside
the repo: every theme you keep is committed and shipped with the tool, and a
fresh clone has them all (`theme generate` writes their Ghostty and Helix
files). Pins and correction bookkeeping are per-machine and stay under
`~/.config/theme/`.

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
uv tool install "git+https://github.com/ghostmind-labo/theme#subdirectory=app"
# or: pipx install "git+https://github.com/ghostmind-labo/theme#subdirectory=app"
theme
```

Zero third-party dependencies. Themes you author are kept in
`~/.config/theme/themes.json` (set `THEME_STORE` to use another file); a bundled
set seeds it on first use.

### Developing

```bash
run routine install      # shim into ~/.local/bin pointing at app/, no venv
run routine check        # compile + resolve every theme
run routine test         # contrast audit
```

The shim points straight at `app/`, so edits take effect immediately.

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

### Installing

The plugin only teaches Claude to drive the `theme` CLI - **install the CLI
first** (above). The repo root is a marketplace:

```bash
claude plugin marketplace add ghostmind-labo/theme
claude plugin install theme@ghostmind-theme
```

Or load it without installing, for a single session:

```bash
claude --plugin-dir /Volumes/Projects/labo/theme/plugin
```

Both manifests pass `claude plugin validate`.

Themes Claude creates persist the same way any other authored theme does - they
are written to `~/.config/theme/themes.json`, not held in the conversation.
