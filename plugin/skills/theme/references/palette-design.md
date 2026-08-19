# Designing a palette from a brief

Contrast is corrected automatically, so the job is expressing a mood, not
achieving legibility. What follows is about making a theme *feel* right.

## Start from the background

Pick `bg` first; everything is measured against it. A background carries the
theme's identity more than any accent does.

- **Dark**: lightness 0.03–0.10. Tint it slightly toward the theme hue rather
  than using pure `#000000` — a hue-tinted near-black reads as intentional
  where pure black reads as absent. Reserve `#000000` for a deliberately
  extreme look.
- **Light**: lightness 0.93–0.98. Pure `#ffffff` is harsh for long sessions;
  a warm off-white (`#faf6ed`) or cool off-white (`#f2f4f7`) is easier.

Then `bg1` and `bg2` step away from `bg` by roughly 0.06 and 0.14 lightness.
Too close and panels vanish; too far and the UI looks striped.

## Monochrome versus duotone

A pure single-hue palette is striking and hard to read — every token looks the
same, so structure disappears. Prefer **duotone**: one dominant hue across
`a1`/`a2`, a neighbouring hue (roughly +0.08 around the wheel) for `a3`, and
contrasting `warn`/`err`.

That is enough variation for code to parse visually while still reading as "the
green one".

## Accent ordering

On a dark background, order accents by lightness: `a3` darkest, `a1` mid,
`a2` lightest. Invert on light. This makes keywords (`a1`) sit visually between
types (`a3`) and strings (`a2`), which matches how code is usually scanned.

Keep `dim` genuinely dim — around 0.45 lightness on dark, 0.40 on light. It
will be lifted to the 4.5:1 floor if it falls under, but starting near the
floor keeps comments quiet.

## Keeping diagnostics visible

`warn` and `err` should not share the theme's hue. In a green theme, a green
error is invisible as an error. Amber (`~#e6c384`) and red (`~#e05252`) work
against nearly every palette and are safe defaults when the brief does not
speak to them.

## Hue separation is on the author

Contrast correction moves lightness, never hue — so two roles that land on the
same hue stay indistinguishable no matter how legible each one is. Before
writing a spec, check the hue angles:

- Keep `a1`, `a2`, `a3`, `warn` and `err` roughly **40° apart**. Two roles
  within ~15° of each other (an olive `a3` at 46° next to an amber `warn` at
  45°) make types and warnings read as the same thing.
- Warm backgrounds are the trap: a yellow or orange field invites warm accents,
  and three of them bunched within ~20° turn code into mush. Push at least one
  accent to the cool side.

## Sibling themes

To make "the same theme in a different colour", do not eyeball new values.
Pull the original spec (`theme edit <name>`), rotate every colour's **hue**
while preserving its exact lightness and saturation, and keep any deliberate
hue offsets between roles (if `a3` sits 8° off `a1`, keep it 8° off). That is
what makes the result feel like a sibling rather than a new theme that happens
to be a different colour.

## Worked examples

**Brief: "something like an old amber terminal"**

Hue is fixed by the brief (~35°). Dark mode. Background near-black with an
amber tint, foreground the classic amber phosphor, accents as lightness
variations of the same hue, diagnostics contrasting.

```json
{"mode":"dark","bg":"#140d00","bg1":"#241a03","bg2":"#3d2c06",
 "fg":"#ffb000","dim":"#8a6212","a1":"#ffcc4d","a2":"#ffe6a3",
 "a3":"#cc8800","warn":"#fff07a","err":"#ff5f4d",
 "about":"amber CRT monitor"}
```

**Brief: "a light theme that doesn't hurt my eyes"**

Warm off-white rather than pure white. Very dark neutral text. Accents dark
enough to sit on a light background without correction having to move them far.

```json
{"mode":"light","bg":"#faf6ed","bg1":"#efe8d8","bg2":"#ddd2bb",
 "fg":"#26211a","dim":"#5f574a","a1":"#1f5f4a","a2":"#7a3a12",
 "a3":"#31508f","warn":"#6a5000","err":"#992222",
 "about":"warm white, high-contrast ink"}
```

Note the accents are already dark. On light backgrounds, authoring dark accents
directly produces better colour than letting correction darken a bright one —
correction preserves hue and saturation but a very light colour dragged down
can look washed.

**Brief: "surprise me, something moody and purple"**

No fixed values in the brief, so seed derivation is the faster path:

```bash
theme new dusk --from '#8a5cd1' --mode dark --about 'moody violet'
```

Reach for a full spec only when the brief names specific relationships that a
single-hue ramp cannot express.

## When to derive versus author

| Situation | Path |
|---|---|
| Mood, adjective, or a single colour named | `--from '#rrggbb'` |
| Multiple colours named, or specific roles requested | full JSON spec |
| Recreating an existing look (a brand, a screenshot) | full JSON spec |
| The user wants to fiddle themselves | tell them to run `theme new <name>` |

Derivation produces a coherent theme in one command. A hand-authored spec is
worth the extra effort only when the brief carries detail derivation would
discard.
