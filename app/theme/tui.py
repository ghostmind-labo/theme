"""A full-screen theme browser.

Built on raw ANSI rather than curses on purpose: curses cannot emit 24-bit
colour, and a theme picker that cannot show a theme's actual colours is not
worth much. Truecolor escapes are absolute rather than palette-indexed, so the
preview shows each theme as it really is while the terminal is still on
whatever theme is currently applied.
"""

from __future__ import annotations

import os
import select
import shutil
import sys
import termios
import tty

from .audit import audit
from .color import rgb
from .targets import apply, current, palette_of

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


class Browser:
    def __init__(self, themes: dict, custom: dict, overrides: dict):
        self.themes = themes
        self.custom = custom
        self.overrides = overrides
        self.filter_mode: str | None = None
        self.origin: str | None = None  # "preset" | "custom" | None
        self.query = ""
        self.searching = False
        self.index = 0
        self.offset = 0
        self.message = ""
        self.applied: str | None = None
        self.current = current(themes)
        self._audits: dict[str, object] = {}

    # -- data ------------------------------------------------------------

    def visible(self) -> list[str]:
        keys = []
        for key, value in self.themes.items():
            if self.origin == "preset" and key in self.custom:
                continue
            if self.origin == "custom" and key not in self.custom:
                continue
            if self.filter_mode and value[3] != self.filter_mode:
                continue
            if self.query and self.query.lower() not in key.lower():
                continue
            keys.append(key)
        # Presets first, then the user's own themes - two sections, not a mix.
        return ([k for k in keys if k not in self.custom]
                + [k for k in keys if k in self.custom])

    def rows(self) -> list[tuple[str, str]]:
        """Display rows: ("header", label) and ("theme", key) entries."""
        keys = self.visible()
        rows: list[tuple[str, str]] = []
        for label, group in (
            ("preset", [k for k in keys if k not in self.custom]),
            ("custom", [k for k in keys if k in self.custom]),
        ):
            if group:
                rows.append(("header", label))
                rows.extend(("theme", key) for key in group)
        return rows

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
        body_rows = rows - 4
        out = [CLEAR, _at(1, 1)]

        title = " theme "
        counts = f"{len(self.visible())}/{len(self.themes)}"
        scope = " · ".join(part for part in (self.origin, self.filter_mode) if part) or "all"
        head = f"{BOLD}{title}{RESET}{DIM} {scope} · {counts}{RESET}"
        out.append(_at(1, 2) + head)

        if self.searching or self.query:
            out.append(_at(2, 2) + f"{DIM}search{RESET} {self.query}" + ("_" if self.searching else ""))

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

        for row, (kind, value) in enumerate(window):
            line_no = row + 3
            if kind == "header":
                out.append(_at(line_no, 2) + f"{DIM}{BOLD}{value}{RESET}")
                continue
            key = value
            mode = self.themes[key][3]
            marker = "●" if key == self.current else " "
            if key == selected:
                out.append(_at(line_no, 2) + REVERSE + f" {marker} {key:<{LIST_WIDTH - 10}} {mode:<5} " + RESET)
            else:
                out.append(_at(line_no, 2) + f"{marker} {key:<{LIST_WIDTH - 10}} {DIM}{mode}{RESET}")

        out.extend(self._preview(LIST_WIDTH + 5, 3, cols - LIST_WIDTH - 6))

        hint = (
            f"{DIM}↑↓{RESET} move  {DIM}⏎{RESET} apply  {DIM}/{RESET} search  "
            f"{DIM}d{RESET}ark  {DIM}l{RESET}ight  {DIM}p{RESET}reset  {DIM}c{RESET}ustom  "
            f"{DIM}a{RESET}ll  {DIM}n{RESET} new  {DIM}q{RESET} quit"
        )
        out.append(_at(rows - 1, 2) + (self.message or hint))
        return "".join(out)

    def _preview(self, col: int, top: int, width: int) -> list[str]:
        key = self.selected()
        if not key or width < 24:
            return []
        ghostty, helix, herdr, mode = self.themes[key]
        palette, background, foreground = palette_of(ghostty)
        out = []
        row = top

        badge = " (current)" if key == self.current else ""
        origin = " · custom" if key in self.custom else ""
        out.append(_at(row, col) + f"{BOLD}{key}{RESET}{DIM} {mode}{origin}{badge}{RESET}")
        row += 1
        about = self.custom.get(key, {}).get("about", "")
        if about:
            out.append(_at(row, col) + f"{DIM}{about}{RESET}")
            row += 1
        row += 1

        if palette and background and foreground:
            block = _bg(background) + " " * min(width, 46) + RESET
            out.append(_at(row, col) + block)
            row += 1
            for label, start in (("normal", 0), ("bright", 8)):
                cells = "".join(
                    _bg(palette[i]) + "    " + RESET for i in range(start, start + 8) if i in palette
                )
                out.append(_at(row, col) + f"{DIM}{label}{RESET} " + cells)
                row += 1
            out.append(_at(row, col) + block)
            row += 2

            sample = _bg(background) + _fg(foreground) + "  the quick brown fox  " + RESET
            out.append(_at(row, col) + sample)
            row += 1
            if 2 in palette and 4 in palette:
                tinted = (
                    _bg(background) + _fg(palette[3]) + "  m3 " + _fg(palette[2]) + "➜ "
                    + _fg(palette[6]) + "~/projects " + _fg(palette[4]) + "(main)  " + RESET
                )
                out.append(_at(row, col) + tinted)
                row += 2

            report = self.audit_of(key)
            if report:
                out.append(_at(row, col) + f"{DIM}contrast{RESET}  text {report.fg_ratio:.1f}:1   "
                                           f"weakest colour {report.worst:.1f}:1")
                row += 2

            out.append(_at(row, col) + f"{DIM}bg{RESET} {background}   {DIM}fg{RESET} {foreground}")
            row += 2

        out.append(_at(row, col) + f"{DIM}ghostty{RESET}  {ghostty}")
        out.append(_at(row + 1, col) + f"{DIM}helix{RESET}    {helix}")
        out.append(_at(row + 2, col) + f"{DIM}herdr{RESET}    {herdr}"
                   + (f"{DIM}  (inherits terminal){RESET}" if herdr == "terminal" else ""))
        return out

    # -- input -----------------------------------------------------------

    def handle(self, key: str) -> bool:
        """Return False to exit the loop."""
        if self.searching:
            if key in ("\r", "\n", ESC):
                self.searching = False
            elif key in ("\x7f", "\b"):
                self.query = self.query[:-1]
            elif key.isprintable():
                self.query += key
            self.index = 0
            return True

        keys = self.visible()
        if key in ("q", "\x03"):
            return False
        if key in ("j", "\x1b[B") and keys:
            self.index = min(self.index + 1, len(keys) - 1)
        elif key in ("k", "\x1b[A") and keys:
            self.index = max(self.index - 1, 0)
        elif key in ("g", "\x1b[H"):
            self.index = 0
        elif key in ("G", "\x1b[F"):
            self.index = max(0, len(keys) - 1)
        elif key == "/":
            self.searching = True
            self.query = ""
        elif key == "d":
            self.filter_mode, self.index = "dark", 0
        elif key == "l":
            self.filter_mode, self.index = "light", 0
        elif key == "p":
            self.origin, self.index = "preset", 0
        elif key == "c":
            self.origin, self.index = "custom", 0
        elif key == "a":
            self.filter_mode, self.origin, self.query, self.index = None, None, "", 0
        elif key in ("\r", "\n"):
            chosen = self.selected()
            if chosen:
                apply(chosen, self.themes)
                self.current = chosen
                self.applied = chosen
                return False
        elif key == "n":
            self.applied = "\0new"
            return False
        return True


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


def browse(themes: dict, custom: dict, overrides: dict) -> str | None:
    """Run the browser. Returns the applied key, "\\0new", or None."""
    if not sys.stdin.isatty():
        raise RuntimeError("the browser needs an interactive terminal")

    browser = Browser(themes, custom, overrides)
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
