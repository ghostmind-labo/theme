"""A full-screen theme browser.

Built on raw ANSI rather than curses on purpose: curses cannot emit 24-bit
colour, and a theme picker that cannot show a theme's actual colours is not
worth much. Truecolor escapes are absolute rather than palette-indexed, so the
preview shows each theme as it really is while the terminal is still on
whatever theme is currently applied.
"""

from __future__ import annotations

import os
import re
import select
import shutil
import sys
import termios
import tty

from .audit import audit
from .catalog import load_custom, save_archive, save_custom, save_favorites, stamp
from .color import rgb
from .generate import write_theme
from .palette import derive, is_monochrome
from .targets import apply, current, palette_of

# The in-picker `n` flow asks these in order, one bottom-bar line at a time.
NEW_FIELDS = ("name", "seed #rrggbb", "mode d/l")

# `s` cycles these. Dates sort newest first; a catalog theme has none and sinks.
SORTS = ("name", "created", "updated")

ESC = "\033"
ALT_SCREEN_ON = f"{ESC}[?1049h"
ALT_SCREEN_OFF = f"{ESC}[?1049l"
HIDE_CURSOR = f"{ESC}[?25l"
SHOW_CURSOR = f"{ESC}[?25h"
CLEAR = f"{ESC}[2J"
RESET = f"{ESC}[0m"
BOLD = f"{ESC}[1m"
DIM = f"{ESC}[2m"
REVERSE = f"{ESC}[7m"

LIST_WIDTH = 30


def _fg(color: str) -> str:
    r, g, b = rgb(color)
    return f"{ESC}[38;2;{r};{g};{b}m"


def _bg(color: str) -> str:
    r, g, b = rgb(color)
    return f"{ESC}[48;2;{r};{g};{b}m"


def _at(row: int, col: int) -> str:
    return f"{ESC}[{row};{col}H"


def _box(top: int, left: int, width: int, height: int, title: str = "", right: str = ""):
    """A framed panel in the terminal's own dim ink, titled like a console readout.

    The chrome deliberately uses the *current* palette, not the previewed one -
    only the window inside the preview is drawn in the candidate's colours.
    """
    inner = width - 2
    right = right[:max(0, inner - 8)]
    tail = f" {right} ─" if right else ""
    title = title[:max(0, inner - 4 - len(tail))]
    fill = "─" * max(0, inner - len(title) - 3 - len(tail))
    yield (_at(top, left) + DIM + "┌─ " + RESET + BOLD + title + RESET + DIM + " " + fill
           + (f" {RESET}{right}{DIM} ─" if right else "") + "┐" + RESET)
    for row in range(top + 1, top + height - 1):
        yield _at(row, left) + DIM + "│" + RESET
        yield _at(row, left + width - 1) + DIM + "│" + RESET
    yield _at(top + height - 1, left) + DIM + "└" + "─" * inner + "┘" + RESET


def _paint(ground: str, segments, width: int) -> str:
    """One row of the mock window: coloured runs of text on a filled ground.

    A segment is (fg, text) or (fg, text, bg). Text is clipped to the row and
    the remainder padded, so every row is exactly `width` cells of the theme.
    """
    out, used = [_bg(ground), " "], 1
    for segment in segments:
        fg, text = segment[0], segment[1][:max(0, width - used)]
        if not text:
            break
        own = segment[2] if len(segment) > 2 else None
        out.append((_bg(own) if own else "") + _fg(fg) + text + (_bg(ground) if own else ""))
        used += len(text)
    out.append(" " * (width - used) + RESET)
    return "".join(out)


def _window(key: str, mode: str, palette: dict, background: str, foreground: str, width: int, height: int):
    """A miniature terminal session rendered in a theme's real colours.

    Every run of text uses the ANSI slot a real program would pick - git's
    red/green, a prompt's green, Helix-style keywords in magenta, Claude Code's
    submitted-message bar - so what the window shows is what the shell, git,
    the editor and Claude will actually look like.
    """
    def slot(index: int) -> str:
        return palette.get(index, foreground)

    # Claude Code's -ansi themes: light puts text in 0 on a bar in 7, dark puts
    # text in 15 on a bar in 8. The window chrome reuses that bar surface.
    bar, bar_ink = (slot(7), slot(0)) if mode == "light" else (slot(8), slot(15))
    chrome = bar
    title_ink = bar_ink
    lines = [
        (chrome, [(slot(1), "●"), (chrome, " "), (slot(3), "●"), (chrome, " "), (slot(2), "●"),
                  (title_ink, f"   ~/projects — {key}")]),
        (background, []),
        (bar, [(bar_ink, "❯ make the sidebar clearer")]),
        (background, [(slot(2), "❯ "), (foreground, "ls")]),
        (background, [(slot(4), "app/  docker/  "), (slot(2), "run.sh  "), (foreground, "meta.json")]),
        (background, [(slot(2), " M "), (foreground, "app/theme/tui.py")]),
        (background, [(slot(3), "warning: "), (foreground, "2 files unstaged")]),
        (background, [(slot(2), "❯ "), (foreground, "hx tui.py")]),
        (background, [(slot(8), " 1 "), (slot(5), "def "), (slot(4), "render"),
                      (foreground, "(self, width: "), (slot(3), "int"), (foreground, "):")]),
        (background, [(slot(8), " 2 "), (slot(8), "    # draw the preview")]),
        (background, [(slot(8), " 3 "), (slot(5), "    return "), (slot(2), '"ready"'),
                      (foreground, " + "), (slot(6), "42")]),
        (chrome, [(background, " NOR ", slot(4)), (bar_ink, " tui.py [+]  "), (slot(1), "● 1 error")]),
        (background, [(slot(2), "❯ "), (background, " ", foreground)]),
    ]
    # Keep the prompt-with-cursor last line; drop body rows from the middle.
    if height < len(lines):
        lines = lines[:height - 1] + lines[-1:]
    for ground, segments in lines:
        yield _paint(ground, segments, width)


class Browser:
    def __init__(self, themes: dict, custom: dict, overrides: dict, favorites=(), archived=()):
        self.themes = themes
        self.custom = custom
        self.overrides = overrides
        # Kept unfiltered: a pin for a theme that does not currently resolve is
        # simply never matched below, but must survive being written back.
        self.favorites = list(favorites)
        self.archived = list(archived)
        self.filter_mode: str | None = None
        self.sort = SORTS[0]
        self.origin: str | None = None  # "favorite" | "archived" | "monochrome" | None
        self.query = ""
        # Answers so far while creating a theme from `n`; None when not creating.
        self.creating: list[str] | None = None
        self.draft = ""
        self.index = 0
        self.offset = 0
        self.message = ""
        self.applied: str | None = None
        self.current = current(themes)
        self._audits: dict[str, object] = {}
        # Open with the cursor on the applied theme. Entering the picker
        # should answer "what am I on?" before anything else - starting at
        # row 0 leaves the ● row scrolled out of view in a long catalog.
        keys = self.visible()
        if self.current in keys:
            self.index = keys.index(self.current)

    # -- data ------------------------------------------------------------

    def visible(self) -> list[str]:
        keys = []
        for key, value in self.themes.items():
            # Archived themes are hidden everywhere except their own scope, so
            # `p` and the mode filters narrow what is on show rather than
            # dragging the archive back into view.
            if (key in self.archived) != (self.origin == "archived"):
                continue
            if self.origin == "favorite" and key not in self.favorites:
                continue
            if self.origin == "monochrome" and not is_monochrome(self.custom.get(key, {})):
                continue
            if self.filter_mode and value[3] != self.filter_mode:
                continue
            if self.query and self.query.lower() not in key.lower():
                continue
            keys.append(key)
        # Flattened in the same order the sections render, so the selection
        # index and the displayed rows cannot disagree.
        return [key for _label, group in self._sections(keys) for key in group]

    def _sections(self, keys) -> list[tuple[str, list[str]]]:
        """Group keys into the sections, in display order.

        A favourite is listed once, under `favorites`, rather than repeated
        below - the point of pinning is to lift it out. Everything else is one
        alphabetical pool: whether a theme shipped with Ghostty or was authored
        here is provenance, not something to browse by.
        """
        # Inside a single-section scope there is nothing to lift out - the whole
        # list is already that one thing - but sorting and search still apply.
        scoped = self.origin in ("archived", "monochrome")
        pinned = [] if scoped else [k for k in self.favorites if k in keys]
        rest = sorted(k for k in keys if k not in pinned)
        if self.sort != "name":
            # Newest first, and a theme the tool does not own has no date at
            # all - those keep their alphabetical order at the bottom.
            rest.sort(key=lambda k: (self.custom.get(k, {}).get(self.sort, ""), k), reverse=True)
            rest = [k for k in rest if k in self.custom] + [k for k in rest if k not in self.custom]
        if self.query:
            # Typing `v` must reach `vermilion`, not `clover`. Names that start
            # with the query lead; the rest still match, listed after.
            starts = [k for k in rest if k.startswith(self.query.lower())]
            rest = starts + [k for k in rest if k not in starts]
        if scoped:
            return [("favorites", pinned), (self.origin, rest)]
        # Monochrome is how this collection is browsed, so it gets lifted out of
        # the pool the way favourites are - and a pin still wins over it.
        mono = [k for k in rest if is_monochrome(self.custom.get(k, {}))]
        return [("favorites", pinned), ("monochrome", mono),
                ("themes", [k for k in rest if k not in mono])]

    def rows(self) -> list[tuple[str, str]]:
        """Display rows: ("header", label) and ("theme", key) entries."""
        rows: list[tuple[str, str]] = []
        for label, group in self._sections(self.visible()):
            if group:
                rows.append(("header", label))
                rows.extend(("theme", key) for key in group)
        return rows

    def toggle_favorite(self) -> None:
        key = self.selected()
        if not key:
            return
        if key in self.favorites:
            self.favorites.remove(key)
            self.message = f"unpinned {key}"
        else:
            self.favorites.append(key)
            self.message = f"pinned {key}"
        save_favorites(self.favorites)
        # The row moved between sections; follow it so the cursor stays put.
        keys = self.visible()
        self.index = keys.index(key) if key in keys else 0

    def toggle_archived(self) -> None:
        key = self.selected()
        if not key:
            return
        if key in self.archived:
            self.archived.remove(key)
            self.message = f"restored {key}"
        elif key == self.current:
            self.message = "cannot archive the applied theme"
            return
        else:
            self.archived.append(key)
            if key in self.favorites:
                self.favorites.remove(key)
                save_favorites(self.favorites)
            self.message = f"archived {key}"
        save_archive(self.archived)
        # The row just left the list it was in; land on its neighbour.
        self.index = min(self.index, max(0, len(self.visible()) - 1))

    def selected(self) -> str | None:
        keys = self.visible()
        if not keys:
            return None
        self.index = max(0, min(self.index, len(keys) - 1))
        return keys[self.index]

    def audit_of(self, key: str):
        if key not in self._audits:
            self._audits[key] = audit(key, self.themes)
        return self._audits[key]

    # -- rendering -------------------------------------------------------

    def render(self) -> str:
        cols, rows = shutil.get_terminal_size((100, 30))
        panel_top, panel_height = 3, max(6, rows - 4)
        body_rows = panel_height - 2
        out = [CLEAR]

        counts = f"{len(self.visible()):02d}/{len(self.themes):02d}"
        scope = " · ".join(part for part in (self.origin, self.filter_mode) if part) or "all"
        now = self.current or "none"
        bar = (f" ◉ THEME CONTROL  │  ACTIVE ● {now}  │  SCOPE {scope.upper()}"
               f"  │  SORT {self.sort.upper()}  │  TRACKS {counts} ")
        out.append(_at(1, 1) + REVERSE + BOLD + bar[:cols].ljust(cols) + RESET)

        # The filter is always live, so the caret always shows: the panel title
        # doubles as the search box.
        title = f"INDEX ▸ {self.query}_" if self.query else "INDEX ▸ SHIFT to search_"
        out.extend(_box(panel_top, 2, LIST_WIDTH + 4, panel_height, title))

        rows_list = self.rows()
        selected = self.selected()
        sel_row = next(
            (i for i, (kind, val) in enumerate(rows_list) if kind == "theme" and val == selected), 0
        )
        if sel_row < self.offset:
            self.offset = sel_row
        if sel_row >= self.offset + body_rows:
            self.offset = sel_row - body_rows + 1
        # Keep a section header visible when the selection sits right under it.
        if sel_row and rows_list[sel_row - 1][0] == "header" and self.offset == sel_row:
            self.offset -= 1
        window = rows_list[self.offset:self.offset + body_rows]

        inner = LIST_WIDTH
        for row, (kind, value) in enumerate(window):
            line_no = panel_top + 1 + row
            if kind == "header":
                label = f"▪ {value.upper()} "
                count = f" {sum(1 for k, v in rows_list if k == 'theme' and self._section_of(v) == value):02d}"
                rule = "·" * max(0, inner - len(label) - len(count))
                out.append(_at(line_no, 4) + f"{BOLD}{label}{RESET}{DIM}{rule}{count}{RESET}")
                continue
            key = value
            tag = "DRK" if self.themes[key][3] == "dark" else "LGT"
            marker = "●" if key == self.current else ("★" if key in self.favorites else " ")
            name = key[:inner - 8]
            if key == selected:
                out.append(_at(line_no, 4) + REVERSE + BOLD + f"▸{marker} {name:<{inner - 8}} {tag} " + RESET)
            elif key == self.current:
                out.append(_at(line_no, 4) + f" {BOLD}{marker} {name:<{inner - 8}}{RESET} {DIM}{tag}{RESET} ")
            else:
                out.append(_at(line_no, 4) + f" {marker} {name:<{inner - 8}} {DIM}{tag}{RESET} ")

        preview_left = LIST_WIDTH + 7
        preview_width = cols - preview_left
        if preview_width >= 30:
            out.extend(self._preview(panel_top, preview_left, preview_width, panel_height))

        if self.creating is not None:
            field = NEW_FIELDS[len(self.creating)]
            done = " ".join(self.creating)
            prompt = f" NEW ▸ {done + ' ▸ ' if done else ''}{field.upper()}: {self.draft}_"
            out.append(_at(rows, 1) + REVERSE + BOLD + prompt[:cols].ljust(min(cols, 60)) + RESET
                       + DIM + "  ⏎ next  esc cancel" + RESET)
            if self.message:
                out.append(_at(rows - 1, 2) + BOLD + f"» {self.message.upper()}"[:cols - 2] + RESET)
        elif self.message:
            status = f" » {self.message.upper()}"
            out.append(_at(rows, 1) + BOLD + status[:cols] + RESET)
        else:
            keys = (("A-Z", "SEARCH"), ("jk", "SCAN"), ("gb", "ENDS"), ("⏎", "ENGAGE"), ("f", "PIN"),
                    ("p", "PINNED"), ("m", "MONO"), ("x", "ARCHIVE"), ("v", "VAULT"),
                    ("d", "DARK"), ("l", "LIGHT"), ("s", "SORT"), ("a", "ALL"),
                    ("n", "NEW"), ("q", "ABORT"))
            # Hints are dropped rather than wrapped: a wrapped bar pushes the
            # frame off the bottom of the screen on a narrow terminal.
            hints, room = [], cols - 3
            for k, v in keys:
                if len(k) + len(v) + 1 > room:
                    break
                hints.append(f"{REVERSE}{k}{RESET}{DIM}{v}{RESET}")
                room -= len(k) + len(v) + 1
            out.append(_at(rows, 2) + " ".join(hints))
        return "".join(out)

    def _section_of(self, key: str) -> str:
        """Which section header a row sits under - read from the sections
        themselves, so a count can never disagree with the display."""
        for label, group in self._sections(self.visible()):
            if key in group:
                return label
        return "themes"

    def _preview(self, top: int, left: int, width: int, height: int) -> list[str]:
        key = self.selected()
        if not key:
            return list(_box(top, left, width, height, "PREVIEW", "NO TARGET"))
        ghostty, helix, herdr, mode = self.themes[key]
        palette, background, foreground = palette_of(ghostty)

        flags = [mode.upper()]
        if key in self.favorites:
            flags.append("★")
        if key == self.current:
            flags.append("● LIVE")
        out = list(_box(top, left, width, height, f"PREVIEW ▸ {key}", " · ".join(flags)))

        col, inner = left + 2, width - 4
        row, bottom = top + 1, top + height - 1  # bottom is the frame row itself
        about = self.custom.get(key, {}).get("about", "")
        if about:
            out.append(_at(row, col) + DIM + about[:inner] + RESET)
            row += 1
        row += 1

        if not (palette and background and foreground):
            out.append(_at(row, col) + BOLD + "NO SIGNAL" + RESET + DIM + " - palette file missing" + RESET)
            return out

        # Four lines of telemetry sit under the window; the window takes the rest.
        window_height = min(15, bottom - row - 5)
        if window_height >= 4:
            window_width = min(inner, 64)
            for line in _window(key, mode, palette, background, foreground, window_width, window_height):
                out.append(_at(row, col) + line)
                row += 1
            row += 1

        if bottom - row >= 1:
            cells = "".join(_bg(palette[i]) + "  " + RESET for i in range(16) if i in palette)
            # 9 label cells + 32 swatch cells; the hex readout only if it fits.
            readout = f"  {DIM}bg{RESET} {background} {DIM}fg{RESET} {foreground}" if inner >= 64 else ""
            out.append(_at(row, col) + f"{DIM}SIGNAL   {RESET}" + cells + readout)
            row += 1
        report = self.audit_of(key)
        if report and bottom - row >= 1:
            verdict = f"{REVERSE} PASS {RESET}" if report.clean else f"{REVERSE}{BOLD} FAIL {RESET}"
            out.append(_at(row, col) + f"{DIM}CONTRAST {RESET}text {report.fg_ratio:4.1f}:1  "
                                       f"{DIM}weakest{RESET} {report.worst:4.1f}:1  " + verdict)
            row += 1
        if bottom - row >= 1:
            route = f"ghostty {ghostty} ▸ helix {helix} ▸ herdr {herdr}"
            out.append(_at(row, col) + f"{DIM}ROUTE    {RESET}" + route[:inner - 9])
            row += 1
        spec = self.custom.get(key, {})
        if spec.get("created") and bottom - row >= 1:
            dates = f"{spec['created'][:10]}   {DIM}updated{RESET} {spec.get('updated', '')[:10]}"
            out.append(_at(row, col) + f"{DIM}AUTHORED {RESET}" + dates)
        return out

    # -- input -----------------------------------------------------------

    def handle(self, key: str) -> bool:
        """Return False to exit the loop."""
        self.message = ""
        if self.creating is not None:
            self._handle_new(key)
            return True
        keys = self.visible()
        # Lowercase letters command, shifted letters search: no chord to reach
        # anything, and `V` still jumps straight to vermilion.
        if key in ("q", "\x03"):
            return False
        if key == ESC:                        # clear the filter, then leave
            if self.query or self.filter_mode or self.origin:
                self.filter_mode = self.origin = None
                self.query, self.index = "", 0
                return True
            return False
        if key in ("j", "\x1b[B") and keys:
            self.index = min(self.index + 1, len(keys) - 1)
        elif key in ("k", "\x1b[A") and keys:
            self.index = max(self.index - 1, 0)
        elif key in ("g", "\x1b[H"):
            self.index = 0
        elif key in ("b", "\x1b[F"):
            self.index = max(0, len(keys) - 1)
        elif key == "d":
            self.filter_mode, self.index = "dark", 0
        elif key == "l":
            self.filter_mode, self.index = "light", 0
        elif key == "f":
            self.toggle_favorite()
        elif key == "p":
            self.origin, self.index = "favorite", 0
        elif key == "v":
            self.origin, self.index = (None if self.origin == "archived" else "archived"), 0
        elif key == "m":
            self.origin, self.index = (None if self.origin == "monochrome" else "monochrome"), 0
        elif key == "x":
            self.toggle_archived()
        elif key == "a":
            self.filter_mode, self.origin, self.query, self.index = None, None, "", 0
        elif key == "n":
            self.creating, self.draft = [], ""
        elif key == "s":
            self.sort = SORTS[(SORTS.index(self.sort) + 1) % len(SORTS)]
            self.index, self.message = 0, f"sorted by {self.sort}"
        elif key in ("\r", "\n"):
            chosen = self.selected()
            if chosen:
                apply(chosen, self.themes)
                self.current = chosen
                self.applied = chosen
                return False
        elif key in ("\x7f", "\b"):
            self.query, self.index = self.query[:-1], 0
        elif len(key) == 1 and (key.isupper() or key.isdigit() or key == "-"):
            # Shift to search. Digits and dashes are unshifted but command
            # nothing, so they extend the query too - `rose-pine-moon` is
            # reachable as `ROSE-PINE-M`.
            self.query, self.index = self.query + key.lower(), 0
        return True

    def _handle_new(self, key: str) -> None:
        """One keypress of the name → seed → mode prompt in the bottom bar."""
        if key == ESC:
            self.creating, self.message = None, "new theme cancelled"
            return
        if key in ("\x7f", "\b"):
            self.draft = self.draft[:-1]
            return
        if key not in ("\r", "\n"):
            if len(key) == 1 and key.isprintable():
                self.draft += key
            return

        value = self.draft.strip().lower()
        field = NEW_FIELDS[len(self.creating)]
        if field == "name":
            if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", value):
                self.message = "name: lowercase letters, digits and dashes"
                return
            if value in self.themes:
                self.message = f"{value} already exists"
                return
        elif field.startswith("seed"):
            value = value if value.startswith("#") else "#" + value
            if not re.fullmatch(r"#[0-9a-f]{6}", value):
                self.message = "seed must be a #rrggbb colour"
                return
        else:
            value = "light" if value.startswith("l") else "dark"
        self.creating.append(value)
        self.draft = ""
        if len(self.creating) < len(NEW_FIELDS):
            return

        name, seed, mode = self.creating
        self.creating = None
        custom = load_custom()
        spec = stamp(derive(seed, mode, f"derived from {seed}"), custom.get(name))
        custom[name] = spec
        save_custom(custom)
        write_theme(name, spec)
        self.custom[name] = spec
        self.themes[name] = (name, name, "terminal", mode)
        # Land on it: clear anything that could hide it, then select it.
        self.filter_mode = self.origin = None
        self.query = ""
        self.index = self.visible().index(name)
        self.message = f"created {name} - ⏎ to engage"


def _read_key(fd: int) -> str:
    """Read one keypress, including multi-byte escape sequences.

    Reads the raw file descriptor rather than `sys.stdin`. A buffered text
    stream pulls the whole `\x1b[B` burst into Python's own buffer on the first
    read, after which `select` on the fd reports no data - the remaining bytes
    are in userspace, not the kernel - and an arrow key degrades to a bare ESC.
    """
    data = os.read(fd, 1)
    if not data:
        return ""
    if data != b"\x1b":
        return data.decode("utf-8", "ignore")

    # An escape sequence arrives as one burst; drain whatever followed.
    seq = data
    while select.select([fd], [], [], 0.02)[0]:
        more = os.read(fd, 1)
        if not more:
            break
        seq += more
        # CSI sequences terminate on a byte in @-~; stop there rather than
        # swallowing the next keypress.
        if len(seq) > 2 and 0x40 <= seq[-1] <= 0x7E:
            break
        if len(seq) >= 8:
            break
    return seq.decode("utf-8", "ignore")


def browse(themes: dict, custom: dict, overrides: dict, favorites=(), archived=()) -> str | None:
    """Run the browser. Returns the applied key, or None."""
    if not sys.stdin.isatty():
        raise RuntimeError("the browser needs an interactive terminal")

    browser = Browser(themes, custom, overrides, favorites, archived)
    fd = sys.stdin.fileno()
    saved = termios.tcgetattr(fd)
    out = sys.stdout
    try:
        tty.setraw(fd)
        out.write(ALT_SCREEN_ON + HIDE_CURSOR)
        while True:
            out.write(browser.render())
            out.flush()
            if not browser.handle(_read_key(fd)):
                break
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, saved)
        out.write(SHOW_CURSOR + ALT_SCREEN_OFF + RESET)
        out.flush()
    return browser.applied
