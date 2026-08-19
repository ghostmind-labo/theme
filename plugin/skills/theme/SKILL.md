---
name: theme
description: This skill should be used when the user asks to "change my terminal theme", "switch to a dark/light theme", "what themes do I have", "make me a theme", "create a theme that looks like X", "build a theme from this colour", "delete that theme", or says the terminal is "hard to read", "too dim", or "low contrast". It covers driving the `theme` CLI to apply, author, audit and correct terminal colour schemes that persist across sessions.
version: 0.1.0
---

# Theme

Drive the `theme` CLI to recolour the terminal stack and to author new palettes
on request. Themes created this way persist: they are stored as data on disk
and survive upgrades of the tool.

## What the tool actually controls

A terminal theme is three configs that know nothing about each other:

| Layer | Themed by | |
|---|---|---|
| Ghostty | `theme = ...` | the ANSI palette everything sits on |
| herdr | `[theme] name` | its own TUI chrome (sidebar, tabs) |
| Helix | `theme = "..."` | the editor |
| zsh prompt, yazi | ANSI slot numbers | follow Ghostty automatically |

The CLI writes all three. The shell prompt and file manager need no
configuration because they emit slot numbers (`\033[33m` means "paint me slot
3") and Ghostty decides what slot 3 is.

**Always tell the user to press `cmd+shift+,` in Ghostty after applying.**
herdr reloads automatically and Helix picks the theme up on next launch, but
Ghostty has no CLI reload. Omitting this leaves the user thinking the command
failed.

## Applying and inspecting

```bash
theme list                  # every theme, current one marked
theme current               # what is applied now
theme <name>                # apply
theme contrast [name]       # WCAG audit
```

Run `theme list` before guessing a name. Invoking bare `theme` opens a
full-screen interactive picker — suggest that when the user wants to browse
rather than name a specific theme, but do not launch it from a non-interactive
context.

## Creating a theme (the main task)

Three paths. Choose by how much the user specified.

**1. A mood, a colour, or a vague brief → derive from one seed colour.**

```bash
theme new sunset --from '#ff6b35' --mode dark --about 'warm dusk orange'
```

Use this when the user says "something warm", "like the ocean", "purple-ish".
Pick a representative hex for the mood and let the ramp do the rest.

**2. A detailed brief, or a palette that needs deliberate role assignment →
write a full spec as JSON.**

```bash
cat <<'JSON' | theme new deepsea
{"mode":"dark","bg":"#04141a","bg1":"#0a2430","bg2":"#123846",
 "fg":"#cfe9f2","dim":"#5b8494","a1":"#3fc1d9","a2":"#a8ecf7",
 "a3":"#2a8fa8","warn":"#e6c384","err":"#e05252",
 "about":"deep ocean, bioluminescent accents"}
JSON
```

This is the path to prefer when authoring on the user's behalf, because it
gives control over every role. See `references/spec.md` for the full contract
and `references/palette-design.md` for how to choose the eleven values.

**3. The user wants to drive it themselves → tell them to run `theme new
<name>` with no flags**, which opens a wizard. Do not run this path directly;
it blocks on interactive input.

After creating, report the storage path and the applied contrast, then offer to
apply it.

## Contrast is handled automatically

Every generated colour is corrected to WCAG 4.5:1 against its own background at
write time, by moving lightness while holding hue and saturation fixed.

**This changes how to author.** Choose colours for *mood*, not legibility — a
seed only has to look right, it does not have to be readable. Do not
pre-darken accents to make them legible; that fights the corrector and produces
muddy results. Pick the colour that expresses the brief and let correction
handle the floor.

When the user reports a theme is hard to read:

```bash
theme contrast <name>       # measure first, do not guess
theme fix <name>            # correct one theme
theme fix --light           # correct every light theme
theme fix --all             # correct everything below the floor
theme revert <name>         # undo
```

`fix` writes a corrected palette beside the original and repoints the theme;
upstream files are never modified. Report what was measured, not just that a
fix ran.

## Managing what exists

```bash
theme edit <name>           # print a custom theme's spec as JSON
theme rm <name>             # delete a custom theme
theme generate              # rebuild every custom theme from the store
theme doctor                # verify every theme resolves to real files
```

To modify an existing custom theme, run `theme edit <name>`, adjust the JSON,
and pipe it back through `theme new <name>` — that overwrites in place.

## Rules that prevent broken output

- **Never hand-edit files in `~/.config/ghostty/themes/` or
  `~/.config/helix/themes/`.** They are generated and overwritten. Edit the
  spec and regenerate.
- **The store is the source of truth.** Custom themes live in
  `~/.config/theme/custom.json`. That is what makes them persist.
- **Names are lowercase letters, digits and dashes.** A name that collides with
  a catalog theme is rejected; pick another rather than forcing it.
- **Custom themes always set herdr to `terminal`**, so herdr inherits Ghostty's
  palette. This is why custom themes work at all — herdr only knows ~17 names.
- **Run `theme doctor` after bulk changes** to confirm every theme still
  resolves.

## Additional resources

### Reference files

- **`references/spec.md`** — the eleven-role spec, the JSON contract, how roles
  map onto ANSI slots, and what the validator rejects.
- **`references/palette-design.md`** — choosing colours for a brief: monochrome
  versus duotone, why pure monochrome hurts readability, how to keep a prompt
  tinted rather than rainbow, and worked examples from brief to spec.

### Examples

- **`examples/mono-dark.json`** — single-hue dark theme with contrasting
  diagnostics.
- **`examples/duotone-light.json`** — light theme with a second accent hue.

Both are complete specs, ready to pipe into `theme new <name>`.
