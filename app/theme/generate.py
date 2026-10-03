"""Emitting Ghostty and Helix theme files from an 11-role spec.

Every colour that carries text is pushed through `remediate` on the way out, so
a generated theme is legible by construction rather than by review.
"""

from __future__ import annotations

import os

from .catalog import GHOSTTY_USER_THEMES, HELIX_USER_THEMES
from .color import CONTRAST_TARGET, TEXT_SLOTS, contrast, pair, remediate, remediate_against, rgb, to_hex
from .targets import write


def _mix(a: str, b: str, t: float) -> str:
    return to_hex(tuple(x + (y - x) * t for x, y in zip(rgb(a), rgb(b))))


def _raised(surface: str, toward: str, ink: str, target: float = CONTRAST_TARGET) -> str:
    """Blend `surface` as far toward `toward` as `ink` on it still clears `target`."""
    if contrast(ink, surface) < target:
        return surface
    low, high = 0.0, 1.0
    for _ in range(20):
        mid = (low + high) / 2
        low, high = (mid, high) if contrast(ink, _mix(surface, toward, mid)) >= target else (low, mid)
    return _mix(surface, toward, low)


# Claude Code's suggestion list draws the selected row in the accent (12) and
# every other row in brightBlack (8). If the two inks are close in lightness the
# selection cannot be found, whatever their hues: a monochrome theme makes them
# identical, and a pair like green and brown on the same ground only differs in
# hue. So slot 8 is moved until it is at least `SEPARATION` from slot 12 while
# still clearing the text floor on every surface - lighter toward the ground or
# deeper toward black, whichever needs the smaller move. When the ink is so
# close to the floor that neither reaches it, the widest legal gap wins.
SEPARATION = 2.5
_DIM_FLOOR = 4.6


def _set_apart(dim: str, ink: str, surfaces: list[str], ground_to: str = "#000000") -> str:
    def legal(color: str) -> bool:
        return min(contrast(color, s) for s in surfaces) >= _DIM_FLOOR

    if contrast(dim, ink) >= SEPARATION:
        return dim
    candidates = []
    for toward in (surfaces[0], ground_to):
        for step in range(0, 51):
            color = _mix(dim, toward, step / 50)
            if legal(color):
                candidates.append((step, contrast(color, ink), color))
    if not candidates:
        return dim
    reaching = [c for c in candidates if c[1] >= SEPARATION]
    if reaching:
        return min(reaching, key=lambda c: c[0])[2]
    return max(candidates, key=lambda c: c[1])[2]


# ANSI slots are kept inside the theme's own hue family so a tinted prompt
# reads as tinted rather than rainbow. warn/err stay contrasting on purpose -
# diagnostics have to survive a monochrome palette.
#
# The black/white slots (0, 7, 8, 15) are not text-only: programs paint
# *surfaces* with them, and which ones depends on polarity. Claude Code's ANSI
# themes are the sharpest case - light draws body text in 0 and the submitted-
# message bar in 7; dark draws text in 15 and that bar in 8. Filling them the
# same way for both modes put ink text on an ink bar in a monochrome theme.
def _slots(spec: dict) -> dict[int, str]:
    slots = {
        1: spec["err"], 2: spec["a1"],  3: spec["warn"], 4: spec["a3"],
        5: spec["a2"],  6: spec["a1"],  9: spec["err"],  10: spec["a2"],
        11: spec["warn"], 12: spec["a1"], 13: spec["a2"], 14: spec["a2"],
    }
    if spec["mode"] == "light":
        # black = ink, white = the light surfaces a bar or card is drawn on.
        # The bar is a paler tint of the ground - a lit card with ink on it -
        # unless the ground is already near white, where only the darker
        # selection tint can stand apart.
        bar = _mix(spec["bg"], "#ffffff", 0.45)
        if contrast(bar, spec["bg"]) < 1.3:
            # A pale ground leaves no lighter tint to use, and the selection
            # tint alone can sit almost on the ground. Deepen it toward the ink
            # while the ink on it still reads at 8:1, so the bar is visible
            # without costing legibility.
            bar = _raised(spec["bg2"], spec["fg"], spec["fg"], 8.0)
        dim = _set_apart(spec["dim"], spec["a1"], [spec["bg"], spec["bg1"]])
        if contrast(dim, slots[12]) < SEPARATION:
            # Slot 8 had no room left. Deepening the accent is always legal
            # on a light ground, so spend the rest of the gap there.
            for step in range(1, 41):
                deeper = _mix(spec["a1"], "#000000", step / 50)
                slots[12] = deeper
                if contrast(dim, deeper) >= SEPARATION:
                    break
        slots.update({0: spec["fg"], 7: bar, 8: dim, 15: spec["bg1"]})
    else:
        # brightBlack is both the message bar and the dim-text colour shells
        # use, so it is lifted toward `dim` only as far as body text on it
        # still reads. On a mid-tone ground whose dim is the ink itself, that
        # lift walks straight back onto the ground; the selection tint stands
        # apart better there, so keep whichever is more distinct.
        raised = _raised(spec["bg2"], spec["dim"], spec["fg"])
        bar = max((raised, spec["bg2"]), key=lambda c: contrast(c, spec["bg"]))
        slots.update({0: spec["bg2"], 7: spec["fg"], 8: bar, 15: spec["fg"]})
    return slots


def ghostty_theme(spec: dict) -> str:
    background = spec["bg"]
    # Body text is drawn on the ground and on panels, so it is corrected against
    # both, and the direction follows the theme's polarity - a mid-tone panel on
    # a light theme must never flip a colour toward white.
    #
    # bg2 is deliberately NOT in that set. It is the selection, and both targets
    # paint selected text with their own paired foreground (below, and
    # `ui.selection` in Helix), so the selection never relies on the body ink
    # being legible against it. Including it made the selection the binding
    # surface whenever it was the most extreme one, which is exactly what a
    # splash of a third colour is: a bright teal selection on a near-black
    # ground dragged every ink to pure white to clear 4.5:1 against the splash,
    # erasing the one ink the theme was authored around.
    surfaces = [background, spec["bg1"]]
    darken = spec["mode"] == "light"
    slots = _slots(spec)
    # Light-mode ink slots carry body and dim text; hold them to the text floor.
    ink_slots = (0, 8) if darken else ()
    lines = []
    for index in range(16):
        color = slots[index]
        if index in TEXT_SLOTS or index in ink_slots:
            color = remediate_against(color, surfaces, darken=darken)
        lines.append(f"palette = {index}={color}")
    lines += [
        f"background = {background}",
        f"foreground = {remediate_against(spec['fg'], surfaces, 7.0, darken=darken)}",
        f"cursor-color = {remediate(spec['a1'], background, darken=darken)}",
        f"selection-background = {spec['bg2']}",
        # Direction is left to the selection surface itself rather than the
        # theme's polarity: a splash can be brighter than a dark theme's ground
        # or darker than a light one's, and pairing it the theme's way lightens
        # an ink that needed darkening - on a near-white teal that bottoms out
        # at white on white.
        f"selection-foreground = {pair(spec['fg'], spec['bg2'])}",
    ]
    return "\n".join(lines) + "\n"


def helix_theme(spec: dict) -> str:
    background = spec["bg"]
    surfaces = [background, spec["bg1"]]  # see ghostty_theme: bg2 is paired, not a text ground
    darken = spec["mode"] == "light"

    def fix(color: str, target: float = CONTRAST_TARGET) -> str:
        return remediate_against(color, surfaces, target, darken=darken)

    fg = fix(spec["fg"], 7.0)
    dim = fix(spec["dim"])
    a1, a2, a3 = fix(spec["a1"]), fix(spec["a2"]), fix(spec["a3"])
    warn, err = fix(spec["warn"]), fix(spec["err"])
    bg1, bg2 = spec["bg1"], spec["bg2"]
    sel_ink = pair(spec["fg"], bg2)  # both directions tried; bg2 decides, not the mode

    scopes = {
        '"ui.background"': f'{{ bg = "{background}" }}',
        '"ui.text"': f'"{fg}"',
        '"ui.text.focus"': f'{{ fg = "{a2}", modifiers = ["bold"] }}',
        '"ui.linenr"': f'"{dim}"',
        '"ui.linenr.selected"': f'{{ fg = "{a1}", modifiers = ["bold"] }}',
        '"ui.cursor"': f'{{ fg = "{background}", bg = "{a1}" }}',
        '"ui.cursor.primary"': f'{{ fg = "{background}", bg = "{a2}" }}',
        '"ui.cursorline.primary"': f'{{ bg = "{bg1}" }}',
        # Paired with the selection ground rather than left to the body ink,
        # which is what lets bg2 hold a colour the ink could never sit on.
        '"ui.selection"': f'{{ fg = "{sel_ink}", bg = "{bg2}" }}',
        '"ui.selection.primary"': f'{{ fg = "{sel_ink}", bg = "{bg2}" }}',
        '"ui.statusline"': f'{{ fg = "{fg}", bg = "{bg1}" }}',
        '"ui.statusline.inactive"': f'{{ fg = "{dim}", bg = "{bg1}" }}',
        '"ui.statusline.normal"': f'{{ fg = "{background}", bg = "{a1}" }}',
        '"ui.statusline.insert"': f'{{ fg = "{background}", bg = "{a2}" }}',
        '"ui.statusline.select"': f'{{ fg = "{background}", bg = "{a3}" }}',
        '"ui.popup"': f'{{ fg = "{fg}", bg = "{bg1}" }}',
        '"ui.menu"': f'{{ fg = "{fg}", bg = "{bg1}" }}',
        '"ui.menu.selected"': f'{{ fg = "{background}", bg = "{a1}" }}',
        '"ui.help"': f'{{ fg = "{fg}", bg = "{bg1}" }}',
        '"ui.virtual.whitespace"': f'"{dim}"',
        '"ui.virtual.indent-guide"': f'"{bg2}"',
        '"ui.virtual.ruler"': f'{{ bg = "{bg1}" }}',
        '"ui.window"': f'{{ fg = "{bg2}" }}',
        '"comment"': f'{{ fg = "{dim}", modifiers = ["italic"] }}',
        '"string"': f'"{a2}"',
        '"constant"': f'"{a2}"',
        '"constant.numeric"': f'"{a2}"',
        '"constant.character.escape"': f'"{warn}"',
        '"keyword"': f'{{ fg = "{a1}", modifiers = ["bold"] }}',
        '"keyword.control"': f'{{ fg = "{a1}", modifiers = ["bold"] }}',
        '"function"': f'"{a2}"',
        '"function.macro"': f'"{warn}"',
        '"type"': f'"{a3}"',
        '"constructor"': f'"{a3}"',
        '"namespace"': f'"{a3}"',
        '"variable"': f'"{fg}"',
        '"variable.other.member"': f'"{a2}"',
        '"variable.parameter"': f'{{ fg = "{fg}", modifiers = ["italic"] }}',
        '"label"': f'"{a3}"',
        '"operator"': f'"{a1}"',
        '"punctuation"': f'"{dim}"',
        '"attribute"': f'"{warn}"',
        '"tag"': f'"{a1}"',
        '"markup.heading"': f'{{ fg = "{a1}", modifiers = ["bold"] }}',
        '"markup.bold"': f'{{ fg = "{a2}", modifiers = ["bold"] }}',
        '"markup.italic"': f'{{ fg = "{a2}", modifiers = ["italic"] }}',
        '"markup.link.url"': f'{{ fg = "{a3}", modifiers = ["underlined"] }}',
        '"markup.link.text"': f'"{a1}"',
        '"markup.raw"': f'"{a2}"',
        '"diff.plus"': f'"{a1}"',
        '"diff.minus"': f'"{err}"',
        '"diff.delta"': f'"{warn}"',
        '"error"': f'"{err}"',
        '"warning"': f'"{warn}"',
        '"info"': f'"{a1}"',
        '"hint"': f'"{dim}"',
        '"diagnostic.error"': f'{{ underline = {{ color = "{err}", style = "curl" }} }}',
        '"diagnostic.warning"': f'{{ underline = {{ color = "{warn}", style = "curl" }} }}',
        '"diagnostic.info"': f'{{ underline = {{ color = "{a1}", style = "curl" }} }}',
        '"diagnostic.hint"': f'{{ underline = {{ color = "{dim}", style = "curl" }} }}',
    }

    header = (
        f"# {spec.get('about', '')}\n"
        f"# generated - edits are overwritten by `theme generate`\n"
        f"# colours corrected to WCAG {CONTRAST_TARGET}:1 against every surface they land on\n\n"
    )
    return header + "\n".join(f"{k} = {v}" for k, v in scopes.items()) + "\n"


def write_theme(key: str, spec: dict) -> None:
    os.makedirs(GHOSTTY_USER_THEMES, exist_ok=True)
    os.makedirs(HELIX_USER_THEMES, exist_ok=True)
    write(os.path.join(GHOSTTY_USER_THEMES, key), ghostty_theme(spec))
    write(os.path.join(HELIX_USER_THEMES, key + ".toml"), helix_theme(spec))
